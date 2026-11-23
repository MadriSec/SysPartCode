# Core Analysis Engine (`analysis/app`)

This component builds the two core C++ static analysis executables — **`syspart`** and **`loops`** — on top of Egalito (`libegalito.so`). It implements interprocedural function call graph (FCG) construction, indirect-call target resolution, address-taken (AT) function pruning, glibc NSS backend resolution, non-return function analysis, natural loop detection, and temporal system call reachability.

## Subcomponents

- [src/scripts/README.md](src/scripts/README.md) — Scalable syscall pipelines, JSON callgraph serializer, BFS reachability, Pin/TypeArmor parsers.
- [src/dlanalysis/README.md](src/dlanalysis/README.md) — Static & dynamic `dlopen()`/`dlsym()` argument resolution.
- [src/pintool/README.md](src/pintool/README.md) — Intel Pin serving-phase loop profiler and server workload generators.

## Build Targets (`Makefile`)

Running `make` in `analysis/app/` produces two binaries in `build_x86_64/` and symlinks them into `analysis/app/`:

| Binary | Entry Point | Linked Sources | Purpose |
| --- | --- | --- | --- |
| `./syspart` | `src/testSyspart.cpp` | `syspart.cpp`, `ipcallgraph.cpp`, `syspartUtility.cpp`, `loopanalysis.cpp`, `nonreturnAnalysis.cpp`, `nss.cpp` | Main static analysis CLI (callgraphs, syscalls, VFA, AT lists, partitioning, etc.). |
| `./loops` | `src/testLoops.cpp` | `loopanalysis.cpp` | Detects natural loops across all modules/functions and outputs loop headers, tails, and exit blocks for the Pin profiler. |

### Standalone Files in `analysis/app/`

- `merge_traces.py` — Small ad-hoc Python utility that iterates over regular files in the current directory and writes a `merged_output.txt` (skips line 1, moves line 2 to the end, strips last 2 lines). **Caution:** Line 17 calls `ref_file.writelines(content)` on a file opened in `'r'` mode, which will raise `io.UnsupportedOperation: not writable` if executed as-is.
- `dlopen_static.txt` — Empty placeholder file.

---

## C++ Module Breakdown (`src/`)

### 1. CLI Driver — `testSyspart.cpp`

Parses flags with GNU `argp`, initializes `EgalitoInterface` with shared library parsing enabled (`egalito.parse(filename, true)`), runs `ResolvePLTPass` and `CollapsePLTPass`, populates the syscall number-to-name map (`sp.populateSyscallMap()`), resolves the start function(s), and dispatches on `-a <mode>[,args...]`. Prints total elapsed seconds to `stderr`.

#### CLI Flags

| Flag | Argument | Behavior |
| --- | --- | --- |
| `-p` | `PROG` | Path to ELF binary to analyze (required). |
| `-s` | `STARTFN` | Root function specification (required). Prefix `0x` -> parsed as hex address; prefix `/` -> treated as **absolute path** to a start-function file (used by modes 23 & 27); otherwise treated as a function name. |
| `-i` | *(none)* | Enables indirect-call refinement: forward dataflow AT pruning + iterative backward VFA indirect-call target resolution. |
| `-g` | *(none)* | Direct-edges-only FCG (`generateDirectCallGraph()` instead of `generate()`). |
| `-t` | `PATH` | Enables TypeArmor indirect-call target filtering using parsed output from `parse_typearmor.sh`. |
| `-l` | *(none)* | Enables Egalito verbose logging. |
| `-a` | `MODE[,ARG...]` | Selects the analysis mode (required). |

#### Complete Analysis Mode Reference (`-a`)

| Mode | Arguments | Method Called | Actual Behavior & Output |
| ---: | --- | --- | --- |
| `1` | *(none)* | `run1` | Generates FCG (with NSS) and prints edges with callsites (`DIRECT` / `INDIRECT` / `INDIRECT_RESOLVED`). |
| `2` | `hex_addr,func_name` | `syscallsOfMainLoop` | Temporal partitioning at `(func_name, hex_addr)`: runs `NonReturnAnalysis`, computes reachable syscalls from partition point (walking forward in CFG & backward to callers until noreturn or `pthread_create` entry), adds `.fini` syscalls. Emits `MAINLOOP`, `JSON [...]`, `MAIN`, `AT`, `PARTITION_SIZE`. |
| `3` | `func_name` | `run7` | Prints `getSyscallInfo` for `STARTFN` and `func_name`, then prints `all - func_name` ("Filtered system calls"). |
| `4` | *(none)* | `run5` | Prints every address-taken site (`SRC_FN_NAME ... SRC_INSTR_ADDR ... AT_FN_NAME ... AT_FN_MODULE`) and count. |
| `5` | *(none)* | `printAICT` | Prints indirect call count, Average Indirect Call Target (overall and application-only), and global AT count. |
| `6` | `func_name,reg_id` | `getArgumentValue` | Backward interprocedural VFA for physical register `reg_id` at callsites of `func_name` (note: does **not** run `resolveNss`). Prints `FUNC ... CALLINGFN ... CALLINGADDR ...`, `TYPE ... SYM ...`, `END`. |
| `7` | `func_name` or `*` | `run2` | For a single `func_name`: prints reachable syscall names (one per line). For `*`: prints a JSON object `{ module: { "func@hexaddr": { "direct_syscalls": [...], "reachable_syscalls": [...] } } }`. |
| `8` | `file_path` | *(inline in `main`)* | **Stub:** Opens `file_path` and echoes whitespace-separated `lib sym` pairs. (Help text describing `no_of_libs,lib1,...` is outdated.) |
| `9` | *(none)* | `run12` | Prints only indirect edges of the FCG. |
| `10` | `func_name` | `run8` | Traces direct-parent call paths from `func_name` upward toward `STARTFN`, noting AT functions and indirect-call holders. (Accepts one function name despite help text.) |
| `11` | `hex_addr,func1,func2` | `isFunctionReachable` | Checks whether `func2` is reachable from instruction `hex_addr` in `func1` (walking forward in CFG and upward through returning non-thread callers). |
| `12` | `dlsym_file` | `getSyscallsFromDlsym` | Reads 4-column records (`caller_fn callsite_hex_addr sym lib_path`), loads extra libraries via `setup->addExtraLibraries()`, adds symbol/global-struct function pointers as roots and AT functions (with forward-DF pruning), and prints `getSyscallInfo` for every FCG node. Note: hardcodes `icanalysis=false`, `typearmor=false`. |
| `13` | *(none)* | `NonReturnAnalysis::run` | Prints count of non-returning functions before and after SysPart's `NonReturnAnalysis`. |
| `14` | *(none)* | `run9` | For each function in `globalATList`, follows only direct edges and prints direct syscalls reachable (`syscall \t direct_invoker \t at_func`). |
| `15` | `startfunc,endfunc` | `ifPathExists` | DFS over the FCG to check whether `endfunc` is reachable from `startfunc`. |
| `16` | `module_substr` | `findDirectSyscallsOfModule` | Prints direct syscalls in the matched module (substring match; keeps last matching module). |
| `17` | `module_substr` | `findCallGraphOfModule` | Builds FCG rooted at all functions of the matched module (with `icanalysis=true`), prints direct edges, AT list, syscall info, and AT sites. |
| `18` | `func_name` | `getPartitionSize` | Counts total instructions across `func_name` and all transitively reachable functions. |
| `19` | *(none)* | `run6` | Reports callers of `fork`/`fork_alias`, `pthread_create`, `pthread_exit`, `pthread_cancel`, plus statically resolved thread start functions. |
| `20` | *(none)* | `printFunctions` | Lists all functions across all modules: `name hex_addr module`. |
| `21` | *(none)* | `printDlArgs("dlopen@")` | Intended to print `dlopen` args. **Bug:** See Known Gotchas below; use mode `6` via `run_dlanalysis.sh` instead. |
| `22` | *(none)* | `printDlArgs("dlsym@")` | Intended to print `dlsym` args. **Bug:** See Known Gotchas below; use mode `6` via `run_dlanalysis.sh` instead. |
| `23` | *(uses `-s /file`)* | `run15(..., 1)` | Builds FCG from all start functions listed in `-s /abs/path` and prints edges with callsites. |
| `24` | *(none)* | `printDirectSyscalls` | Scans every function in every module with Egalito's `FindSyscalls` and prints `func hex_addr module syscall_name syscall_num`. |
| `25` | *(none)* | `printAllFunctions` | Same output format as mode `20` (`name hex_addr module`). |
| `26` | `func_name_or_0xaddr` | `printDisass` | Dumps Egalito disassembly (`ChunkDumper`) of the specified function. |
| `27` | *(uses `-s /file`)* | `run15(..., 2)` | Computes union of reachable syscalls from start functions listed in `-s /abs/path` using iterative bitset propagation (`findDerived4()`). |
| `28` | *(none)* | `run16(..., 2)` | Computes union of reachable syscalls across **all** functions in the binary and its loaded libraries using `findDerived4()`. |
| `100` | `f1,reg1,f2,reg2` | `run_fcg_with_argument_resolution` | *(Undocumented in `--help`)* Prints the full FCG with callsites, then runs mode-6-style backward VFA for `(f1, reg1)` and `(f2, reg2)` delimited by `ARGUMENTRES-BEGIN-FUNC1` and `ARGUMENTRES-BEGIN-FUNC2`. |

---

### 2. Core Orchestrator & Syscall Reachability — `syspart.h`, `syspart.cpp`

`class Syspart` owns an `IPCallGraph`, maps `IPCallGraphNode*` -> `SysNode*`, and resolves syscall numbers to names.

- **Syscall Name Mapping (`populateSyscallMap`):** Parses `#define __NR_<name> <num>` from `/usr/include/asm-generic/unistd.h` and `/usr/include/x86_64-linux-gnu/asm/unistd_64.h`, falling back to `populateDefaultSyscalls()` (hardcoded x86-64 table up to 547).
- **Direct Syscall Extraction (`findDirectSyscalls`):** Runs Egalito's `FindSyscalls` pass on every function in `ip_callgraph.nodeMap`, recording direct syscalls in `SysNode::direct_syscalls`, `SysNode::syscallMap` (per-instruction), a `bitset<600>` in `syscall_info[s]`, and the reverse index `who_invokes_syscalls[sysno]`.
- **Derived Syscall Propagation:**
  - `findDerivedSyscalls(Function*)` — Reverse DFS from each direct syscall invoker up parent edges; populates `derived_syscalls` and per-child bitsets. Used by modes 2, 3, 7, 12, 14.
  - `findDerived4()` — Iterative fixed-point OR of `bitset<600>` over `nodeMap` until convergence; much faster on large binaries. Used by scalable modes 27 & 28.
  - *(Legacy/unused)* `findDerivedSyscalls1` and `findDerivedSyscalls3` (`buildSysCallTree`) remain in the file but are not invoked by any CLI mode.
- **Temporal Partitioning (`syscallsOfMainLoop`, `findSyscallsAccessible`):**
  - Identifies `pthread_create` thread entry functions (`getThreadStartFunction` -> traces 3rd arg `RDX` via `find_thread_function`).
  - Starting at `(func_name, addr)`, collects syscalls from all CFG blocks forward-reachable from `addr`'s block (note: starts from **forward successors** of `start_bl`, not instructions inside `start_bl` itself).
  - If `cur_func->returns()` and `cur_func` is not a thread entry function, pushes every parent callsite `(parent_node, callsite_addr)` onto the worklist so post-return syscalls are included.
  - Unions with `.fini` / `.fini_array` / `.dtors` / `_fini` syscalls.
- **Unused/Experimental Helpers in `syspart.cpp`:** `run3`, `run4`, `run10`, `run11`, `run13`, `run14`, `find_syscalls_in_thread`, `findReachableCode`, `printAllSections`.

---

### 3. Interprocedural Call Graph & Refinement — `ipcallgraph.h`, `ipcallgraph.cpp`

Builds a callsite-aware interprocedural call graph across the executable and all loaded shared libraries.

#### Key Classes

- **`ChildListManager`:** Hash-consing flyweight cache (`unordered_map<vector<IPCallGraphNode*>, shared_ptr<const vector<IPCallGraphNode*>>>`). Dramatically reduces memory when thousands of unresolved indirect callsites share the same `globalATList` target vector.
- **`IPCallGraphNode`:** Stores a `Function*`, `direct_children` & `indirect_children` (keyed by callsite address), `parent` & `parentType` (`true`=direct, `false`=indirect), `indirectCalls` sites, `ATFunctions` (address-taken targets per instruction), `icallResolved` flags, and `atreturns` (AT functions returned via `RAX`).
- **`IPCallGraph`:** Main builder and query interface.

#### `IPCallGraph::generate()` Pipeline

1. **`checkForSymbols()`:** Records which modules have a non-null `.symtab` (`modulesWithSymbols`).
2. **`findData()`:** Scans all regions/data sections; registers functions referenced in `.preinit_array`, `.init_array`, `.ctors`, `_init` (`initFuncs`) and `.fini`, `.fini_array`, `.dtors`, `_fini` (`finiFuncs`) as additional `functionRoots`.
3. **Direct Edge Discovery (`findDirectEdges`):** Worklist BFS over `functionRoots` inspecting `ControlFlowInstruction` targets (local `Function*`, `PLTTrampoline*`, or inter-function `Instruction*`).
4. **Address-Taken & Indirect-Site Discovery (`findATList`):** Worklist over all reachable functions:
   - Inspects `LinkedInstruction` and `DataLinkedControlFlowInstruction`.
   - Direct code references to a `Function*` or `PLTTrampoline*` are added as AT roots; if `-i` is enabled, **`forwardDataFlow()`** (`searchDownDef`) traces the function pointer forward through registers, memory (`MemUse`), calls (`handleArgumentFnPtr`), and returns (`handleReturnInstruction`). If the pointer only reaches resolved/direct uses (or directly resolves an indirect callsite via `handleIcallOrIjump`), it is **pruned** from `globalATList`.
   - References to a `DataSection*` (skipping `MOV`/`CMP` stores to memory) invoke `parseData()` (precise global-variable bounds when the module has symbols) or `parseDataWithNoSymbols()` (conservative scan of all reachable data sections when stripped).
   - Records `IndirectCallInstruction`, non-jump-table `IndirectJumpInstruction`, and `DataLinkedControlFlowInstruction` as indirect callsites.
5. **Iterative Backward Indirect-Call Resolution (if `-i`):** Instantiates `SyspartUtility(program, this, 1)` and loops `findIndirectCallTargets()` over `nodeMap` until a fixed point (no new callsites resolved).
6. **TypeArmor Filtering (if `-t`):** `parseTypeArmor()` loads `fnargs`, `icallargs`, `nonvoidfn`, `nonvoidicall` from `typearmor_parsed.txt`; `generateIndirectEdgesWithTypeArmor()` filters candidate targets where `callee_nargs <= icall_nargs` and void/non-void return matches.
7. **Fallback Indirect Edges (`generateIndirectEdges`):** Any unresolved indirect callsite receives `allAT` (all `globalATList` nodes), optionally filtered by TypeArmor.

#### Callgraph Output Format (`printCallGraphWithCallsites`)

Each line has 8 whitespace-separated fields:
```text
<EDGE_TYPE> <caller_module> <callsite_hex> <caller_fn> <callee_hex_addr> <callee_fn> <callee_module> <caller_hex_addr>
```
Where `<EDGE_TYPE>` is `DIRECT`, `INDIRECT`, or `INDIRECT_RESOLVED`.

*(Note: `writeCallgraphToBinaryFile()` / `buildCallgraphFromBinaryFile()` implement a compact `callgraph.bin` binary format, currently commented out in `run15`/`run16`.)*

---

### 4. Backward Value-Flow & Indirect Call Target Resolution — `syspartUtility.h`, `syspartUtility.cpp`

`class SyspartUtility` performs backward interprocedural register/memory value-flow analysis using Egalito's `DataFlow` / `UseDef` working sets, bounded by `MAX_ITER = 100` recursion depth and memoized via `found_results` (`Inter_result`) and `found_state_results` (`Intra_result`).

- **`UDResult`:** `{ type, addr, desc, func }` where `type` is:
  - `0` — Unknown / unresolvable
  - `1` — Concrete constant or resolved address (e.g., RIP-relative constant or function address)
  - `2` — Dereferenced address (`val(0x...)`)
  - `3` — Complex symbolic expression (`a + b`, `val(base + 0xoff)`)
- **Analysis Modes (`analysisType`):**
  - `0` (Argument resolution, CLI mode `6`/`100`): Prints `FUNC <callee> CALLINGFN <caller> CALLINGADDR <hex>`, each unique `UDResult` (`TYPE ... ADDRESS ... DESC ... FUNC ... MODULE ...`), attempts to read a NUL-terminated string from `.rodata` if `tr.addr` lies within `.rodata` (emitting `SYM <str>`), and ends with `END`.
  - `1` (Indirect call target resolution, `-i`): Resolves register-indirect `call`/`jmp` instructions via `findRegDef()` (also handling callee return values via `IPCallGraphNode::getATReturn()`). If **all** resolved `UDResult`s are known function addresses (`type == 1`, neither unknown nor global), marks the callsite resolved and adds edges. Tracks `FPath` so subsequent fixed-point iterations only re-analyze callsites whose backward slice includes a newly resolved function. Memory-operand indirect calls compute the address expression but currently push an unknown target so they remain unresolved.
- **x86-64 Physical Register IDs (Egalito/SysPart Convention):**
  `0`=`RAX`, `1`=`RCX` (arg 4), `2`=`RDX` (arg 3), `6`=`RSI` (arg 2), `7`=`RDI` (arg 1), `8`=`R8` (arg 5), `9`=`R9` (arg 6).
- **`matchLoadMemoryToStores()`:** Performs backward intra-procedural CFG traversal from a memory load to find the nearest reaching store `UDState`s matching the same `MemLocation`.

---

### 5. Natural Loop Detection — `loopanalysis.h`, `loopanalysis.cpp`, `testLoops.cpp`

`class LoopAnalysis` builds an Egalito `ControlFlowGraph` per function, computes block dominators via an iterative worklist intersection algorithm, identifies back-edges `(tail -> header)` where `header ∈ dom(tail)`, and computes each natural loop body (`naturalLoops`) and exit blocks (`exitBlocks`). Multiple back-edges to the same header are merged into one `Loop` keyed by `(entry_addr, module)`.

- **`./loops <binary>` (`testLoops.cpp`):** Runs `detectLoops` on every function of every module, prints `FUNC <name> <hex_addr>` lines during traversal, then calls `printLoops()`:
  ```text
  <resolved_library_path> <entry_hex> <num_tails> <tail1_last_instr_hex ...> <num_exits> <exit1_hex ...> <func_name>
  ```
  Filter out `^FUNC` lines before passing to the Pin tool (`grep -v '^FUNC' loops_output.out > loops.out`).
- **`findNonLoopParent(func, loop)`:** Used by `enforcement/src/syspart_enforce.cpp` to find CFG predecessors of the loop header that lie outside `loopBody` (for safe filter injection before the loop).

---

### 6. Non-Return Analysis — `nonreturnAnalysis.h`, `nonreturnAnalysis.cpp`

`class NonReturnAnalysis` runs a program-wide fixed-point pass over all modules/functions to identify functions that never return to their caller (improving temporal partitioning precision in mode `2`).

- **Seed List (`knownList`):** `exit`, `_exit`, `abort`, `__libc_fatal`, `__assert_fail`, `__stack_chk_fail`, `__malloc_assert`, `_dl_signal_error`, `__cxa_throw`, and four `libstdc++` throw helpers.
- **Algorithm:** For each function CFG, `isNonReturn()` recursively checks if every control-flow path either hits a non-returning call/jump or loops (cycle returns `-1` and does not taint `ret`); any block with no forward links returns `0` (returning). Functions where `isNonReturn == 1` are marked `func->setNonreturn()`, repeating until no new non-returning functions are discovered.

---

### 7. glibc NSS Resolution — `nss.h`, `nss.cpp`

Adapted from Brown University's Sysfilter (`NSSFuncsPass : public ChunkPass`). Because glibc's Name Service Switch (`getpwnam`, `gethostbyname`, etc.) dynamically `dlopen`s `libnss_<backend>.so.2` at runtime, static callgraphs would otherwise miss NSS syscalls.

- **Configuration:** Reads `/etc/nsswitch.conf` (via `ConductorFilesystem`) and discovers installed `libnss_*.so*` backends in `$USER_LIBRARY_PATH` (colon-separated) or default system library paths (`/lib/x86_64-linux-gnu`, `/usr/lib`, `/lib64`, `/usr/lib64`, `/usr/local/musl/lib`).
- **Callgraph Wiring (`IPCallGraph::resolveNss` & `addNssEdges`):** Scans each module's `ExternalSymbolList` against ~84 known glibc NSS APIs (`setupFuncs()`), adds needed `libnss_<backend>.so.2` dependencies to libc via `ElfDynamic`, re-parses libraries and PLTs, seeds `_nss_<backend>_<sym>` (or `..._r`) as FCG roots, and adds direct call edges from callers of the glibc NSS function to the resolved NSS backend functions.

---

## Known Quirks & Gotchas (Time-Savers)

1. **`-s` start-function file MUST be an absolute path:** `testSyspart.cpp:52` detects file arguments by `arg[0] == '/'`. Relative paths are treated as function names! Always pass `$(realpath file)` for modes 23 and 27.
2. **`-s all` pointer-comparison bug:** `testSyspart.cpp:42` writes `if (arg == "all")` (comparing `char*` pointers instead of `strcmp`). It falls through to `findFunctionByName("all") -> NULL`, which happens to be harmless for mode 28 (`run16`) because `run16` does not use `start_func`.
3. **Modes 21 & 22 (`printDlArgs`) bug:** `testSyspart.cpp` calls `printDlArgs("dlopen@")` and `printDlArgs("dlsym@")`, but `syspart.cpp:2677` checks `if (dlname == "dlopen")` / `else if (dlname == "dlsym")`, leaving `reg` uninitialized. Use mode `6` (`-a 6,<sym>,7` / `-a 6,<sym>,6`) or `src/dlanalysis/static/run_dlanalysis.sh` instead.
4. **Off-by-one bitset loop in modes 27 & 28:** `syspart.cpp:1621` and `1702` iterate `for (int i = 0; i <= combined.size(); i++)` on `std::bitset<600>` (`i == 600` is out-of-bounds). Keep in mind if running under sanitizers or debugging crashes.
5. **Mode 5 (`printAICT`) division by zero:** If a binary has 0 indirect calls (overall or in the executable), `sum / n` or `sumapp / napp` will trigger `SIGFPE`.
6. **Mode 16 & 17 module matching:** Substring search does not `break` on first match, so it analyzes the **last** module whose name contains the substring.
7. **Mode 12 (`getSyscallsFromDlsym`) PLT bug:** At `syspart.cpp:2936`, inside the `PLTTrampoline` branch, `sym_funcs.push_back(global_fun)` references an out-of-scope/unintended variable (likely meant `plt_target`, which is fixed in the second loop at line 3030).
8. **`findSyscallsAccessible` starts after `start_bl`:** Mode 2 collects syscalls starting from the CFG successors of the block containing `partition_point_address`, not earlier instructions in that block.
