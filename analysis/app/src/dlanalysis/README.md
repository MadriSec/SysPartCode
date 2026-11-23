# Dynamic Library & Symbol Analysis (`analysis/app/src/dlanalysis`)

This component resolves shared libraries and symbols loaded dynamically at runtime via `dlopen()` and `dlsym()`. It combines **static value-flow analysis** (using `syspart -a 6`) with heuristic symbol-to-library matching, plus two **dynamic runtime tracers** (`LD_PRELOAD` interposition and `LD_AUDIT` dynamic-linker auditing) to verify observed loads.

## Directory Layout

```text
dlanalysis/
├── dlopen.txt                      # Default symbol name for dlopen (e.g. dlopen@@GLIBC_2.2.5)
├── dlsym.txt                       # Default symbol name for dlsym (e.g. dlsym)
├── pathlist.txt                    # Library search directories for heuristic symbol matching
├── static/
│   ├── run_dlanalysis.sh           # Main static DL analysis pipeline
│   ├── process_result.py           # Parses raw syspart -a 6 output into tabular args
│   ├── generate_libnames.sh        # Enumerates unique *.so files under pathlist.txt
│   ├── match_libs_with_syms.sh     # Matches resolved dlsym() names against exported symbols
│   ├── trace_dlopen-dlsym_fcg.py   # Exports Mermaid call-path graph back to dlopen/dlsym
│   └── find_fcgs_with_dlopen.py    # Standalone helper reading container package lists
└── dynamic/
    ├── fninterposition/            # LD_PRELOAD wrapper (libmydl.so) for dlopen/dlsym
    │   ├── libmydl.c
    │   ├── Makefile
    │   └── process_output.sh
    └── ldaudit/                    # LD_AUDIT tracer (libaudit.so) with libunwind stack traces
        ├── dynamictrack.c
        ├── getstacktrace.c
        ├── Makefile
        └── process_output.sh
```

---

## Configuration Files

- **`dlopen.txt` / `dlsym.txt`:** Fallback dynamic symbol names used if `run_dlanalysis.sh` cannot auto-detect versioned `dlopen`/`dlsym` symbols from `libc.so` via `nm -D`.
- **`pathlist.txt`:** Newline-separated directories scanned by `generate_libnames.sh` (defaults to `/lib/x86_64-linux-gnu`). Add application plugin directories here if `dlopen()` arguments cannot be statically resolved.

---

## 1. Static Analysis (`static/`)

### Main Pipeline — `run_dlanalysis.sh`

```bash
cd analysis/app/src/dlanalysis/static
./run_dlanalysis.sh <BINARY> <OUTPUT_DIR>
```

Step-by-step workflow:
1. Rebuilds `analysis/app` (`USE_LOADER=0 make`).
2. **`resolve_dynsym()`:** Inspects `ldd <BINARY>` for `libc.so` and runs `nm -D` to find the actual exported versioned symbol names for `dlopen` and `dlsym` (falling back to `../dlopen.txt` and `../dlsym.txt`).
3. Runs `syspart` mode `6` (backward interprocedural VFA):
   - `dlopen` 1st argument (`%rdi`, register ID `7`): writes `<OUTPUT_DIR>/dlopen_static.txt`.
   - `dlsym` 2nd argument (`%rsi`, register ID `6`): writes `<OUTPUT_DIR>/dlsym_static.txt`.
4. Runs `process_result.py` on both raw outputs to produce `<OUTPUT_DIR>/dlopen_args.txt` and `<OUTPUT_DIR>/dlsym_args.txt` (`Callsite_func | Callsite_addr | Args`, mapping unresolved/non-type-1 results to `UNKNOWN`).
5. Runs `generate_libnames.sh` -> scans directories in `../pathlist.txt` for `*.so` files and writes `../all_libs.txt` and deduplicated `../unique_libs.txt`.
6. Runs `match_libs_with_syms.sh` on `dlsym_args.txt`: for every resolved symbol (skipping `UNKNOWN` and `NULL` and the 4-line header), checks each `.so` in `unique_libs.txt` via `readelf -s ... | grep -w "$sym" | grep -v 'UND'` and writes matches (`<caller_func> <callsite_addr> <sym> <lib_path>`) to `<OUTPUT_DIR>/libraries_matching_syms.txt`.

> **Feeding Results Back into SysPart:** The 4-column format of `libraries_matching_syms.txt` (`caller_fn callsite_hex_addr sym lib_path`) matches the input expected by `./syspart -p <BINARY> -s main -a 12,<file>` (`Syspart::getSyscallsFromDlsym`).

### Auxiliary Scripts in `static/`

- **`trace_dlopen-dlsym_fcg.py`:** Reads `DIRECT ...` lines from a `syspart -a 1` callgraph on `stdin`, performs backward BFS from any callee whose base name (stripping `@@...`) is `dlopen` or `dlsym` until reaching a function in `module-(executable)`, and prints a `mermaid` (`graph LR`) diagram grouped into module subgraphs.
  ```bash
  grep -E "^DIRECT" fcg.txt | python3 trace_dlopen-dlsym_fcg.py
  ```
- **`find_fcgs_with_dlopen.py`:** Standalone container-environment utility that reads `/var/lib/libsec_tool/container_data/${CONTAINER_NAME}.txt` (`pkg===version` lines) and prints installed packages. Not called by `run_dlanalysis.sh`.

---

## 2. Dynamic Analysis (`dynamic/`)

### Option A: `LD_PRELOAD` Function Interposition (`dynamic/fninterposition/`)

Intercepts `dlopen()` and `dlsym()` directly via `libmydl.so` (which resolves the real functions using glibc's internal `_dl_sym(RTLD_NEXT, ...)` to avoid infinite recursion on `dlsym`).

```bash
cd analysis/app/src/dlanalysis/dynamic/fninterposition
make
mkdir -p output
LD_PRELOAD=$PWD/libmydl.so <APP_RUN_COMMAND>
./process_output.sh output/ <OUTPUT_FOLDER>
```

- **Runtime Output:** Constructor opens `output/fninterp_<pid>.txt` (relative to the target process's working directory!). Logs `mydlopen (<filename>) : <ret_addr>(<handle>)` and `mydlsym (<name>) (<handle>) : <ret_addr>(<addr>)`.
- **Post-Processing (`process_output.sh`):** Extracts unique library names into `<OUTPUT_FOLDER>/fninterp_dlopen.txt`, unique symbol names into `<OUTPUT_FOLDER>/fninterp_dlsym.txt`, and moves `fninterp_*.txt` into `<OUTPUT_FOLDER>`.
- **Quirks:**
  - The `output/` directory must exist in the working directory of the launched application, otherwise `fopen()` returns `NULL` and `fprintf()` segfaults.
  - `Makefile`'s `clean` target says `rm libmydl` instead of `rm -f libmydl.so`.
  - `_dl_sym` is a private glibc symbol and may be unavailable on newer glibc versions (use `ldaudit/` as an alternative).

### Option B: `LD_AUDIT` Dynamic Linker Auditing (`dynamic/ldaudit/`)

Uses glibc's standard rtld-audit interface (`<link.h>`) plus `libunwind` stack traces (`getstacktrace.c`) to trace shared object searches, loads, and `dlsym` symbol bindings without overriding `dlopen`/`dlsym`.

```bash
cd analysis/app/src/dlanalysis/dynamic/ldaudit
make                 # requires libunwind-dev; builds libaudit.so
mkdir -p output
LD_AUDIT=$PWD/libaudit.so <APP_RUN_COMMAND>
./process_output.sh <OUTPUT_FOLDER>
```

- **Audit Callbacks (`dynamictrack.c`):**
  - `la_version`: opens `output/ldout_<pid>.txt` and returns `LAV_CURRENT`.
  - `la_preinit`: marks the boundary between startup (`before`) and runtime (`after`) dynamic loads.
  - `la_objsearch` / `la_objopen`: logs every searched/loaded shared object with its `cookie` and a `libunwind` stack trace (`show_backtrace`).
  - `la_symbind64`: logs bindings where `*flags == LA_SYMB_DLSYM` along with `symname`, `refcook`, `defcook`, and stack trace.
- **Post-Processing (`process_output.sh`):** Parses every `output/*.txt` after `la_preinit`, matches `la_objopen()` cookies to `defcook` in `la_symbind64()` entries, prints `<lib> <sym>` pairs to `stdout`, and moves raw logs to `<OUTPUT_FOLDER>`.
- **Quirk:** Like `fninterposition`, `output/` must exist before running the target binary.
