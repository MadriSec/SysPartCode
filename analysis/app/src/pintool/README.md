# Serving-Phase Loop Profiler (`analysis/app/src/pintool`)

This component uses Intel Pin to dynamically measure execution time and iteration counts of statically detected top-level loops across all threads and forked child processes of a server application. Its output identifies the **dominant serving loop** (`(func_name, entry_addr)`), which defines the temporal partition boundary between initialization and serving.

## Directory Layout

| Path | Role |
| --- | --- |
| `timeofouterloop.cpp` | Intel Pin tool source; instruments statically detected loop entry and exit offsets per image, tracks top-level loop durations via TLS, and writes per-thread/per-process logs. |
| `makefile`, `makefile.rules` | Standard Intel Pin tool build configuration (`TEST_TOOL_ROOTS := timeofouterloop`, links `-lrt`). |
| `server_request_scripts/` | Workload generator scripts used to exercise servers while profiling under Pin. |

---

## Building

1. Extract Intel Pin 3.11 from [analysis/tools/](../../../tools/README.md) and export `PIN_ROOT`:
   ```bash
   export PIN_ROOT="/path/to/SysPartCode/analysis/tools/pin-3.11-97998-g7ecce2dac-gcc-linux"
   ```
2. Build the Pintool (`obj-intel64/timeofouterloop.so`):
   ```bash
   cd analysis/app/src/pintool
   make
   ```

---

## Input & Execution Workflow

### 1. Generate Static Loop Metadata
Run `./loops` from `analysis/app/` and separate function headers from loop entries:
```bash
cd analysis/app
./loops <SERVER_BINARY> > $OUTDIR/loops_output.out
grep -v '^FUNC' $OUTDIR/loops_output.out > $OUTDIR/loops.out
grep '^FUNC' $OUTDIR/loops_output.out > $OUTDIR/functions.out   # needed by parse_pinout.sh
mkdir -p $OUTDIR/pin
```

Expected line format of `loops.out` (parsed in `timeofouterloop.cpp:main()`):
```text
<image_path> <entry_hex> <num_tails> <tail_hex_1 ...> <num_exits> <exit_hex_1 ...> <func_name>
```
*(The pintool extracts the basename of `<image_path>` after the last `/` and matches instruction offsets `INS_Address(ins) - IMG_LowAddress(img)`.)*

### 2. Run the Server Under Pin
```bash
cd analysis/app/src/pintool
sudo $PIN_ROOT/pin -follow_execv \
    -t obj-intel64/timeofouterloop.so \
    -i $OUTDIR/loops.out \
    -p $OUTDIR/pin/ \
    -o pin.out \
    -- <SERVER_COMMAND>
```

#### Pin Knobs (`timeofouterloop.cpp`)
| Knob | Default | Description |
| --- | --- | --- |
| `-i` | `""` | Path to `loops.out` from `./loops`. |
| `-p` | `""` | Directory prefix for per-thread output files (`<filepath><tid>_<pid>`). **Must include a trailing `/`** (concatenated directly with `threadid`). |
| `-o` | `pin.out` | Diagnostic log file (image load addresses, parsed loops, thread/fork lifecycle events). |

### 3. Exercise & Gracefully Stop the Server
Send representative traffic (e.g., using `server_request_scripts/` below) for ~30 seconds, then **gracefully stop** the server (`Ctrl+C` or server-specific stop command) so Pin invokes `ThreadFini()` and flushes loop timings.

### 4. Parse Results
```bash
analysis/app/src/scripts/parse_pinout.sh $OUTDIR/pin
```
Writes `$OUTDIR/pin.out` with `<func_name> <entry_hex> (<func_name>+0x<rel_offset>)` for the longest-running loop in each thread/process.

---

## How `timeofouterloop.cpp` Works

- **Top-level loop tracking (`entry_fun` / `exit_fun`):** Each thread maintains a `thread_data_t` TLS record with `cur_loop`.
  - When `cur_loop == NULL` and execution enters a tracked loop header (`entry_map`), it becomes the active outer loop (`OS_Time(&l->start_time)`, `iterations = 0`).
  - Re-entering the same header increments `iterations`. Nested loops encountered while `cur_loop != NULL` are ignored.
  - Reaching an exit offset matching `cur_loop` (`exit_map`) records `(end_time - start_time, iterations)` in `duration_iterations[tid_pid]`, inserts `cur_loop` into `executed_loops`, and resets `cur_loop = NULL`.
- **Multi-process & Multi-thread Support:** `ThreadStart` and `AfterForkInChild` allocate separate TLS structures and output files named `<filepath><tid>_<pid>`.
- **Output Format (`<tid>_<pid>`):** One line per top-level loop invocation:
  ```text
  <duration_seconds> <iterations> <entry_hex> <func_name>
  ```

---

## Server Request Scripts (`server_request_scripts/`)

Simple workload generators to drive servers into their serving phase while profiled under Pin:

| Script | Target Server | Workload | External Dependency |
| --- | --- | --- | --- |
| `apache2_send_requests.py` | Apache2 (`localhost:80`) | HTTP GET `/10001.html`..`/19999.html` | `requests` |
| `httpd_send_requests.py` | Apache httpd (`localhost:80`) | HTTP GET `/10001.html`..`/49999.html` | `requests` |
| `lighttpd_send_requests.py` | Lighttpd (`localhost:80`) | HTTP GET `/10001.html`..`/19999.html` | `requests` |
| `nginx_send_requests.py` | Nginx (`localhost:80`) | HTTP GET `/10001.html`..`/19999.html` | `requests` |
| `bind_send_requests.py` | BIND DNS | `dig -x x.y.x.y` (`1..99` × `1..99`) | `dig` CLI |
| `memcached_send_requests.py` | Memcached (`localhost`) | 9,999 `set` + `get` pairs | `pymemcache` |
| `redis_send_requests.py` | Redis (`localhost:6379`) | 9,999 `set` + `get` pairs | `redis` (note: line 6 has mixed space+tab indentation in Python 3) |

---

## Known Quirks & Bugs

1. **Trailing slash on `-p` is mandatory:** `filepath` is concatenated directly with `threadid` (`oss << filepath << threadid << "_" << PIN_GetPid()`). Passing `-p $OUTDIR/pin` without `/` writes files named `pin0_1234` in `$OUTDIR` instead of inside `$OUTDIR/pin/`.
2. **Null-dereference bug in `ThreadFini` (line 149):** After setting `tdata->cur_loop = NULL` on line 143, line 149 checks `if (dur_iter != (tdata->cur_loop->duration_iterations).end())` instead of `l->duration_iterations.end()`. Be aware of this if `ThreadFini` segfaults on shutdown when `executed_loops` is non-empty.
3. **Graceful termination required:** `ThreadFini` only writes `<tid>_<pid>` output on normal thread/process exit; `SIGKILL` leaves empty trace files.
4. **Exit instrumentation does not check `image_name`:** Unlike `entry_map` (which verifies `im_name == l->image_name`), `exit_map` matches purely by offset within any valid image.
5. **Hex addresses parsed into `int`:** `main()` reads loop entry/tail/exit hex offsets into 32-bit `int` (sufficient for typical binary offsets `< 2 GB`).
