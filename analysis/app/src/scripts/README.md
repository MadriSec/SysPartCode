# Analysis Orchestration & Post-Processing Scripts (`analysis/app/src/scripts`)

This directory contains shell and Python scripts that wrap `./syspart` for scalable syscall extraction, compress large call graphs, parse Intel Pin and TypeArmor outputs, and perform quick ELF/syscall utility lookups.

> **Working Directory Note:** The `compute_syscalls*.sh` scripts invoke `./syspart` and `src/scripts/...` using relative paths, so they **must** be executed from `analysis/app/` (e.g., `cd analysis/app && src/scripts/compute_syscalls.sh ...`).

## Script Index

| Script | Language | Primary Role |
| --- | --- | --- |
| `compute_syscalls.sh` | Bash | Main scalable pipeline: generates `callgraph.json` + reachable syscalls (with optional call-path logging). |
| `compute_syscalls_updated.sh` | Bash | Fast single-invocation C++ pipeline using `syspart -a 27` (`findDerived4`). |
| `compute_syscalls_allfuncs.sh` | Bash | Computes syscalls reachable from **all** functions in the binary and its libraries (`syspart -a 28`). |
| `parse_callgraph_to_json.py` | Python 3 | Streaming compressor converting raw `syspart` callgraph lines into deduplicated JSON with `callee_groups`. |
| `getsyscalls.py` | Python 3 | BFS reachability over `callgraph.json` + direct syscalls, with optional shortest-path logging. |
| `parse_pinout.sh` | Bash | Post-processes per-thread Pin output files to extract the dominant serving loop and concurrency model. |
| `parse_typearmor.sh` | Bash | Converts TypeArmor `binfo.*` output files into a single `typearmor_parsed.txt` consumed by `syspart -t`. |
| `findmain.sh` | Bash | Recovers the address of `main()` in stripped binaries via `__libc_start_main` relocation + `objdump`. |
| `convert_sysno_to_name.py` | Python 3 | Translates a file of x86-64 syscall numbers (one per line) into syscall names. |

---

## Detailed Component Reference

### 1. Syscall Extraction Pipelines

#### `compute_syscalls.sh`
```bash
cd analysis/app
src/scripts/compute_syscalls.sh <BINARY> <OUT_DIR> <START_FUNCS_FILE> [--log]
```
Runs four steps:
1. `./syspart -p $APP -s <first_func> -a 25` -> `$OUT/allfunctions.txt`
2. `./syspart -p $APP -s <first_func> -a 24` -> `$OUT/syscalls_with_callsites.txt`
3. `./syspart -p $APP -s $(realpath $STARTFILE) -i -a 23 | python3 src/scripts/parse_callgraph_to_json.py - $OUT/callgraph.json`
4. Resolves each start function name to `<name>_<hex_addr>` in `$OUT/startfuncs_with_addr.txt` (by matching against `allfunctions.txt`) and runs `getsyscalls.py` -> `$OUT/syscalls.txt` (and `$OUT/logfile.txt` if `--log` is passed).

- **Note:** The `--help` text mentions `callgraph.txt`, but the script pipes directly into `parse_callgraph_to_json.py` and writes `callgraph.json`.

#### `compute_syscalls_updated.sh`
```bash
cd analysis/app
src/scripts/compute_syscalls_updated.sh <BINARY> <OUT_DIR> <START_FUNCS_FILE>
```
Runs `./syspart -p $APP -s $(realpath $STARTFILE) -i -a 27 > $OUT/syscalls.txt`. Faster and avoids intermediate JSON files, but does **not** emit `callgraph.json` or support `--log` path tracing (the `--log` flag is parsed but unused).

#### `compute_syscalls_allfuncs.sh`
```bash
cd analysis/app
bash src/scripts/compute_syscalls_allfuncs.sh <BINARY> <OUT_DIR>
```
Runs `./syspart -p $APP -s all -i -a 28 > $OUT/syscalls.txt`.
- **Quirks:** Missing a `#!/bin/bash` shebang line (invoke with `bash` explicitly); `--log` is parsed but unused.

---

### 2. Callgraph Serialization & Reachability

#### `parse_callgraph_to_json.py`
```bash
python3 src/scripts/parse_callgraph_to_json.py <input_file_or_-> <output.json>
```
Reads 8-column `syspart` callgraph lines (`EDGE_TYPE caller_mod callsite caller_fn callee_addr callee_fn callee_mod caller_addr`) and writes a compact JSON schema:
```json
{
  "functions": [
    {"id": "func_1", "name": "...", "module": "...", "addr": "..."}
  ],
  "callee_groups": {
    "group_1": ["func_2", "func_3"]
  },
  "call_graph": [
    {"caller_id": "func_1", "callee_type": "group", "callee_ref": "group_1", "edge_type": "INDIRECT", "callsite": "..."},
    {"caller_id": "func_1", "callee_type": "individual", "callee_id": "func_4", "edge_type": "DIRECT", "callsite": "..."}
  ]
}
```
Any `(caller_fn, callsite)` callee set with `len > 1` appearing `>= 2` times (`min_group_occurrences=2`) is factored into `callee_groups`, massively shrinking output for large binaries with many unresolved indirect callsites.
- **Caveat:** Functions are keyed solely by `fn` name (`func_to_id[fn]`), so two distinct static functions sharing a name across modules will share one ID.

#### `getsyscalls.py`
```bash
python3 src/scripts/getsyscalls.py <callgraph.json> <syscalls_with_callsites.txt> <startfuncs_with_addr.txt> [--log <logfile.txt>]
```
Loads the callgraph into a `DirectedGraph` (nodes formatted as `<func_name>_<hex_addr>`), attaches `"syscall"` edges from `syscalls_with_callsites.txt`, and runs BFS from `startfuncs_with_addr.txt`. Prints each reachable syscall name to `stdout`; with `--log`, writes one shortest call path per reachable syscall to `<logfile.txt>`.
- **Quirk:** `main()` calls **both** `generate_callgraph(callgraphfile)` (text parser, silently skips JSON lines with `< 8` tokens) and `generate_callgraph_from_json(callgraphfile)` (strict JSON loader), so the input file must be valid JSON.

---

### 3. Dynamic Profiling & TypeArmor Helpers

#### `parse_pinout.sh`
```bash
analysis/app/src/scripts/parse_pinout.sh <OUTDIR>/pin
```
Iterates over per-thread Pin trace files (`<tid>_<pid>`) inside `<OUTDIR>/pin`:
- Picks the loop with the largest duration (`sort -r -k 1,1 | head -1`) for each thread/process.
- Looks up the function's start address in `<OUTDIR>/functions.out` (3rd column, matching `funcname`) to compute `(<funcname>+0x<rel_offset>)`.
- Appends `<funcname> <entry_hex> (<funcname>+0x<rel_offset>)` to `<OUTDIR>/pin.out`.
- Infers whether the server is single/multi-process and single/multi-threaded from the distinct `pid` and `tid` filenames.
- **Prerequisite & Quirk:** Expects `<OUTDIR>/functions.out` to exist (e.g., generated from `grep '^FUNC' loops_output.out > $OUTDIR/functions.out` — note column 3 of `FUNC <name> <hex_addr>` is the function's hex address). Also, only the single-process/single-threaded summary line is appended to `pin.out`; the other three concurrency messages print to `stdout`.

#### `parse_typearmor.sh`
```bash
analysis/app/src/scripts/parse_typearmor.sh <TYPEARMOR_BINFO_DIR>
```
Reads all `binfo.<lib>` files in `<TYPEARMOR_BINFO_DIR>` and writes `<TYPEARMOR_BINFO_DIR>/typearmor_parsed.txt` with normalized lines consumed by `IPCallGraph::parseTypeArmor()` (`syspart -t`):
- `fnargs <lib> <hex_addr> <nargs>` (from `[args]` and `[varargs]`)
- `icallargs <lib> <hex_addr> <nargs>` (from `[icall-args]`)
- `nonvoidfn <lib> <hex_addr>` (from `[non-voids]`)
- `nonvoidicall <lib> <hex_addr>` (from `[non-void-icalls]`)

---

### 4. Standalone Utilities

#### `findmain.sh`
```bash
analysis/app/src/scripts/findmain.sh <BINARY>
```
Finds the relocation entry for `__libc_start_main` via `readelf -r`, inspects the preceding instruction in `objdump -d` loading `%rdi`, and extracts the address of `main()` (useful for stripped binaries where `-s main` fails and `-s 0x<addr>` is needed).

#### `convert_sysno_to_name.py`
```bash
python3 analysis/app/src/scripts/convert_sysno_to_name.py <syscall_numbers.txt>
```
Reads one decimal x86-64 syscall number per line from `<syscall_numbers.txt>` and prints the corresponding Linux x86-64 syscall name (covers 0–334, 424–435, and x32 512–547).
