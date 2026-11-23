# SysPart Enforcement Component (`enforcement`)

This component enforces a temporal system call policy at the partition boundary identified during analysis. It consists of two stages:

1. **Seccomp-BPF Filter Library Generation (`src/scripts/`, `src/filter/`):** Compiles a JSON list of allowed x86-64 system call numbers into a balanced binary-search Seccomp-BPF filter (`install_filter()`) packaged as a shared library (`libsyspart.so`).
2. **Static Binary Rewriting (`src/syspart_enforce.cpp` -> `./sysenforce`):** Uses Egalito (`SyspartPass`) and SysPart's `LoopAnalysis` to rewrite the target ELF binary so that `install_filter()` is invoked right before entering the serving loop.

> *Note: Only one active filter at a time is currently supported.*

---

## Directory Layout

| Path | Purpose |
| --- | --- |
| `Makefile` | Builds `./sysenforce` (symlinked from `build_x86_64/sysenforce`) by linking `src/syspart_enforce.cpp` with `loopanalysis.cpp`, `ipcallgraph.cpp`, `syspartUtility.cpp`, `nss.cpp`, and `libegalito.so`. |
| `src/syspart_enforce.cpp` | Binary rewriting driver (`./sysenforce`); locates the loop at `(func_name, hex_addr)`, computes non-loop CFG parents, loads the filter shared library, runs `SyspartPass`, and emits the transformed ELF binary. |
| `src/scripts/seccomp.py` | Policy loader (`SeccompFilterContext`) supporting JSON arrays (`[0, 1, ...]`), JSON objects (`{"syscalls": [...]}`), stdin (`-`), and `--spec-allow`. Emits the x86-64 arch guard (`AUDIT_ARCH_X86_64`) and renders `filter_template.c`. |
| `src/scripts/skip_list_filter.py` | Generates a binary-search cBPF decision tree (`BPF_JGE`/`BPF_JEQ`) in chunks of up to 128 sorted syscalls (ensuring jump offsets stay within 256 instructions / 8-bit `jt`/`jf`), allowing matched syscalls (`SECCOMP_RET_ALLOW`) and killing all others (`SECCOMP_RET_KILL`). |
| `src/scripts/filter_template.c` | C template defining `int install_filter(int f_errno)` which calls `prctl(PR_SET_NO_NEW_PRIVS, 1, ...)` followed by `syscall(SYS_seccomp, SECCOMP_SET_MODE_FILTER, SECCOMP_FLAG, &prog)`. |
| `src/filter/Makefile` | Compiles `src/filter/filter.c` into **`enforcement/libsyspart.so`** (`gcc -shared -fPIC -o ../../libsyspart.so filter.c`). |

---

## Requirements

1. Python 3 (originally tested with Python 3.6.9)
2. Built Egalito library in `../analysis/tools/egalito/` (with `SyspartPass`, i.e., from the SysPart Egalito branch)

---

## Building `./sysenforce`

```bash
cd enforcement
make
```

This creates `enforcement/sysenforce` (symlinked to `build_x86_64/sysenforce`) and copies `libegalito.so` into `build_x86_64/`.

---

## Filter Generation and Installation

### Step 1 — Setup

Point `$OUT` to the output directory produced by the analysis phase (containing `syscalls.json` from `./syspart -a 2,...` and `pin.out` from `parse_pinout.sh`):

```bash
export OUT=<SysPart_outputs_directory>
```

### Step 2 — Generate the Seccomp-BPF Shared Library

```bash
cd enforcement/src/scripts
python3 skip_list_filter.py <syscalls_json_file> > ../filter/filter.c
cd ../filter
make
```

Optional flag: pass `--spec-allow` to `skip_list_filter.py` to set `SECCOMP_FILTER_FLAG_SPEC_ALLOW` (disabling Speculative Store Bypass mitigation for lower overhead). You may also pass multiple policy JSON files, and `seccomp.py` will union them.

> **Important Filename Note:** `enforcement/src/filter/Makefile` builds **`enforcement/libsyspart.so`** (not `sysfilter.so`, despite older references). Pass `libsyspart.so` (or copy/rename it) to `./sysenforce` in Step 3.

Example (Redis):

```bash
cd enforcement/src/scripts
python3 skip_list_filter.py $OUT/redis/syscalls1.json > ../filter/filter.c
cd ../filter
make
```

### Step 3 — Insert the Filter into the Target Binary

```bash
cd enforcement
./sysenforce <binary> <func_name> <partition_addr_hex> <output_binary> <filter_so> <filter_fn>
```

| Positional Arg | Description |
| --- | --- |
| `argv[1]` (`binary`) | Path to original ELF binary. |
| `argv[2]` (`func_name`) | Name of the function containing the dominant loop (from `$OUTDIR/pin.out`). |
| `argv[3]` (`partition_addr_hex`) | Hexadecimal loop header address (from `$OUTDIR/pin.out`, parsed with base 16; `0x` prefix optional). |
| `argv[4]` (`output_binary`) | Output path for the rewritten ELF binary. |
| `argv[5]` (`filter_so`) | Shared library containing the filter function (e.g., `libsyspart.so`). |
| `argv[6]` (`filter_fn`) | Symbol name of the filter installer function (`install_filter`). |

Example:

```bash
./sysenforce <redis_dir>/redis-server-alt aeMain 45f30 new_redis libsyspart.so install_filter
```

---

## Internal Mechanics (`src/syspart_enforce.cpp`)

1. **`injectSharedLibFn()`** parses only the main executable (`egalito->parse(filename)`) and searches for `func_name`.
   - If `func_name` is not found in the executable (e.g., the server's main event loop lives inside a shared library), it falls back to **`handleMainLoopInLib()`**, which re-parses with shared libraries enabled (`egalito->parse(filename, true)`).
2. Runs `LoopAnalysis::detectLoops(source_func)` and looks up the `Loop` whose `entry_addr == address` in `loop_mod`.
3. Computes `non_loop_parents = loopAnalysis.findNonLoopParent(source_func, l)` — the CFG predecessor blocks of the loop header that are outside the loop body.
4. Checks whether the layout-preceding block `prev_sibling` is one of `non_loop_parents`:
   - If yes: `special_case = false` (filter call can be inserted on fall-through before the loop header).
   - If no: `special_case = true` (handled specially by `SyspartPass` so the filter executes only on loop entry, not on every back-edge iteration).
5. Parses `<filter_so>` into Egalito, locates `<filter_fn>`, applies `SyspartPass(prog, source_func, address, enforcement_func, special_case, prev_sibling, non_loop_parents)`, and writes `<output_binary>` via `egalito->generate(newelf, false)`.

## Known Quirks & Gotchas

- **No argument count check in `main()`:** Passing fewer than 6 arguments to `./sysenforce` will dereference `NULL` in `argv`.
- **Shared-library matching:** `syspart_enforce.cpp` matches the loaded filter module by substring `mod.find(sharedlib) != npos`, so avoid passing relative paths like `./libsyspart.so` if Egalito names the module `module-libsyspart.so`; pass the bare library filename (`libsyspart.so`) from the `enforcement/` directory.
- **Standalone `seccomp.py`:** Running `python3 seccomp.py <policy>` directly emits a **permissive** (`SECCOMP_RET_ALLOW`) filter template (intended only for testing/benchmarking baseline seccomp overhead); always use `skip_list_filter.py` for real enforcement.
- **`Makefile` has no `clean` target:** To clean `enforcement/`, remove `build_x86_64/`, `.symlinks`, and `sysenforce` manually.
