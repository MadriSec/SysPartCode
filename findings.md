# SysPart Findings

<!-- harness:logic:mode-1:start -->
## Harness logic audit — mode 1

Dispatcher and modules: README.md, analysis/app/README.md, analysis/app/src/testSyspart.cpp, analysis/app/src/syspart.cpp, analysis/app/src/ipcallgraph.cpp, analysis/app/src/syspartUtility.cpp, analysis/app/src/nss.cpp

### TypeArmor filtering dereferences a missing argument-count entry

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/ipcallgraph.cpp:853`
- Invariant: A target without function argument metadata must remain eligible, as the preceding branch intends (analysis/app/src/ipcallgraph.cpp:848-852).
- Mechanism: When functionNargs.find returns end(), the code inserts the target but then dereferences that end iterator (analysis/app/src/ipcallgraph.cpp:848-854). Mode 1 reaches this filter with -t when a callsite has argument metadata (analysis/app/src/syspart.cpp:1538-1550; analysis/app/src/ipcallgraph.cpp:824-847).
- Reproducer: Source-bounded case: a matching icallargs entry and an address-taken target with no fnargs entry (analysis/app/src/ipcallgraph.cpp:602-605; analysis/app/src/ipcallgraph.cpp:824-853).
- Expected: Keep the target with unknown argument count and print its `INDIRECT` edge (analysis/app/src/ipcallgraph.cpp:848-852, analysis/app/src/ipcallgraph.cpp:766-775).
- Actual: The source dereferences `functionNargs.end()`, which is undefined behavior; its runtime outcome is unobserved (analysis/app/src/ipcallgraph.cpp:848-853).
- Evidence: analysis/app/src/testSyspart.cpp:188-190 — mode 1 calls run1; analysis/app/src/syspart.cpp:1540-1550 — TypeArmor is enabled and the non-direct path calls generate; analysis/app/src/ipcallgraph.cpp:1815-1836 — metadata is parsed, address-taken targets populate allAT, and indirect edges are generated; analysis/app/src/ipcallgraph.cpp:664-666, analysis/app/src/ipcallgraph.cpp:685-719 — an unresolved indirect call passes allAT to the TypeArmor filter; analysis/app/src/ipcallgraph.cpp:824-834 — missing callsite metadata returns before filtering, so the test requires an icallargs entry; analysis/app/src/ipcallgraph.cpp:848-853 — missing target metadata reaches the end-iterator dereference.
- Assessment: A tiny test case is a program with one indirect call and one address-taken target, plus a TypeArmor file containing an `icallargs` entry for the callsite and no `fnargs` entry for the target. Run mode `-a 1` with `-t` and leave `-g` unset (analysis/app/src/testSyspart.cpp:64-65, analysis/app/src/testSyspart.cpp:74-86, analysis/app/src/testSyspart.cpp:188-190). The expected output is an `INDIRECT` line naming the target (analysis/app/src/ipcallgraph.cpp:766-775). The missing `fnargs` entry leaves `find` at `end()`; the target is inserted, then that iterator is dereferenced (analysis/app/src/ipcallgraph.cpp:595-605, analysis/app/src/ipcallgraph.cpp:848-853). No runtime output was captured.

### Direct graph traversal stops at a cross-function instruction target

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/ipcallgraph.cpp:914`
- Invariant: Every direct callee added to the graph must also be traversed for its outgoing direct edges (analysis/app/src/ipcallgraph.cpp:1746-1751).
- Mechanism: For a control-flow link to an Instruction in another function, findDirectEdges adds an edge but does not add that function to functionRoots; the Function and PLT branches do add their targets (analysis/app/src/ipcallgraph.cpp:891-917). The traversal consumes only functionRoots (analysis/app/src/ipcallgraph.cpp:1746-1751; analysis/app/src/ipcallgraph.cpp:1770-1775).
- Reproducer: Source-bounded graph: root links to an instruction inside callee, and callee directly calls leaf. The first link enters the Instruction branch; callee is not queued, so its call to leaf is not scanned unless another path queues it (analysis/app/src/ipcallgraph.cpp:908-917; analysis/app/src/ipcallgraph.cpp:1746-1751).
- Expected: Both root-to-callee and callee-to-leaf DIRECT records for the proposed test (analysis/app/src/ipcallgraph.cpp:891-896, analysis/app/src/ipcallgraph.cpp:755-767).
- Actual: The source supports a missing callee-to-leaf record when no other path queues callee; no runtime result was observed (analysis/app/src/ipcallgraph.cpp:908-917, analysis/app/src/ipcallgraph.cpp:1746-1754, analysis/app/src/ipcallgraph.cpp:1770-1783).
- Evidence: analysis/app/src/testSyspart.cpp:188-191 — mode -a 1 calls run1; analysis/app/src/syspart.cpp:1538-1551 — run1 selects direct or full graph generation; analysis/app/src/ipcallgraph.cpp:891-905 — Function and PLT targets are queued; analysis/app/src/ipcallgraph.cpp:908-917 — a cross-function Instruction target gets an edge but is not queued; analysis/app/src/ipcallgraph.cpp:224-247 — addEdge creates graph nodes and edges without queuing; analysis/app/src/ipcallgraph.cpp:1746-1754, analysis/app/src/ipcallgraph.cpp:1770-1783 — both generators scan queued functions, then requeue only functions already visited; analysis/app/src/ipcallgraph.cpp:1345-1348 — later AT processing invokes direct scanning only for functions it receives.
- Assessment: A tiny test case would have root call an instruction inside callee, and callee directly call leaf, with no other path to callee. For mode -a 1, the expected output is two DIRECT records, root-to-callee and callee-to-leaf; the source predicts only root-to-callee because the Instruction branch does not queue callee (analysis/app/src/ipcallgraph.cpp:908-917), while traversal scans queued functions (analysis/app/src/ipcallgraph.cpp:1746-1751, analysis/app/src/ipcallgraph.cpp:1770-1775) and output prints recorded direct edges (analysis/app/src/ipcallgraph.cpp:755-767).

### Direct-only mode expands into address-taken functions

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/ipcallgraph.cpp:1757`
- Invariant: With -g, the printed direct graph should follow direct edges from its selected roots (analysis/app/src/testSyspart.cpp:74-75; analysis/app/src/syspart.cpp:1547-1554).
- Mechanism: After direct traversal, generateDirectCallGraph scans address-taken references. findATList queues referenced functions and calls findDirectEdges for newly queued functions; the printer then emits all resulting direct edges (analysis/app/src/ipcallgraph.cpp:1753-1762; analysis/app/src/ipcallgraph.cpp:1345-1349; analysis/app/src/ipcallgraph.cpp:1370-1375; analysis/app/src/ipcallgraph.cpp:755-765).
- Reproducer: Source-bounded graph: root takes cb's address but never calls cb; cb directly calls leaf. The address reference queues cb, and the later pass can print cb-to-leaf under -g (analysis/app/src/ipcallgraph.cpp:1370-1375; analysis/app/src/ipcallgraph.cpp:1757-1762; analysis/app/src/ipcallgraph.cpp:755-765).
- Expected: No `DIRECT` record from cb to leaf when cb is unreachable by direct edges from the selected roots (analysis/app/src/ipcallgraph.cpp:1746-1751; analysis/app/src/testSyspart.cpp:99-105).
- Actual: The source permits a `DIRECT` record from cb to leaf and incurs address-reference processing plus another instruction scan; neither output nor cost was measured (analysis/app/src/ipcallgraph.cpp:1345-1375,755-765).
- Evidence: analysis/app/src/testSyspart.cpp:74-77,188-190 — `-g -a 1` selects run1; analysis/app/src/syspart.cpp:1540-1554 — run1 sets the root, generates the direct graph, then prints it; analysis/app/src/ipcallgraph.cpp:1746-1762 — after direct traversal, visited functions are queued for address-taken scanning; analysis/app/src/ipcallgraph.cpp:1352-1375 — a linked, non-control-flow reference queues cb; analysis/app/src/ipcallgraph.cpp:1345-1348,872-924 — processing cb scans its direct calls and records cb-to-leaf; analysis/app/src/ipcallgraph.cpp:755-765 — every recorded direct edge is printed. The second pass also scans instructions in visited functions and newly queued targets (analysis/app/src/ipcallgraph.cpp:1352-1359,1746-1762).
- Assessment: Tiny source-bounded test: root contains a non-control-flow instruction linked to cb; cb directly calls leaf; no selected root directly reaches cb. For `-s root -g -a 1`, the expected printed direct edges omit `cb` to `leaf`. The source path instead adds that edge, and the printer has no root-reachability filter (analysis/app/src/ipcallgraph.cpp:1352-1375; analysis/app/src/ipcallgraph.cpp:1345-1348; analysis/app/src/ipcallgraph.cpp:891-895; analysis/app/src/ipcallgraph.cpp:755-765).

### An address root can resolve to the wrong module

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:47`
- Invariant: The hexadecimal -s address must identify the intended root before mode 1 calls setRoot (analysis/app/src/testSyspart.cpp:173-177; analysis/app/src/syspart.cpp:1538-1542).
- Mechanism: findFunctionByAddress searches every module and overwrites its result on each address match; its own comment notes duplicate addresses can make results inaccurate (analysis/app/src/syspart.cpp:42-61).
- Reproducer: Source-bounded case: two parsed modules contain functions at the same supplied address. The function in the later iterated module replaces the earlier match (analysis/app/src/syspart.cpp:47-61; analysis/app/src/testSyspart.cpp:173-177).
- Expected: Reject an ambiguous 0x1000 root and print no graph edges (analysis/app/src/testSyspart.cpp:88-89; analysis/app/src/syspart.cpp:42-44).
- Actual: If B is the later matching module, B becomes the root and mode 1 can print edges from its graph; this outcome is inferred from source, not observed (analysis/app/src/syspart.cpp:47-61; analysis/app/src/syspart.cpp:1538-1554; analysis/app/src/ipcallgraph.cpp:755-775).
- Evidence: analysis/app/src/testSyspart.cpp:45-55 — a 0x-prefixed -s value selects address lookup; analysis/app/src/testSyspart.cpp:156-177 — parsing includes shared libraries and passes the lookup result to setStartFunc; analysis/app/src/syspart.cpp:47-61 — each matching module overwrites the result, with no ambiguity check; analysis/app/src/testSyspart.cpp:188-191 — mode 1 calls run1; analysis/app/src/syspart.cpp:1538-1554 — run1 passes that function to setRoot, generates the graph, and prints it; analysis/app/src/ipcallgraph.cpp:169-177 — setRoot queues the supplied function; analysis/app/src/ipcallgraph.cpp:1742-1750 — direct graph generation processes queued roots.
- Assessment: A tiny test would create two parsed modules, A and B, each with a function at 0x1000, then request mode 1 with -s 0x1000. Expected output: an ambiguity error and no call-graph edges. The current lookup instead retains B's function if B is iterated last; the source itself warns that duplicate addresses can give inaccurate results (analysis/app/src/syspart.cpp:42-61). This is source-supported; no runtime output was observed.

### Indirect calls can be marked resolved with no target edge

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspartUtility.cpp:1379`
- Invariant: A resolved indirect site must retain an edge to every identified target; otherwise it needs the fallback candidate set (analysis/app/src/ipcallgraph.cpp:692-715).
- Mechanism: With -i, resolution skips a target whose function has no graph node, but still marks the site resolved. Graph generation then skips fallback targets at that site (analysis/app/src/syspartUtility.cpp:1360-1381; analysis/app/src/ipcallgraph.cpp:692-705).
- Reproducer: Source-bounded case: a computed call address names a parsed function that has not entered nodeMap through direct or address-taken traversal. getNode returns null, so no edge is inserted (analysis/app/src/ipcallgraph.h:355-369; analysis/app/src/syspartUtility.cpp:1362-1379).
- Expected: Create the hidden target node and print its INDIRECT_RESOLVED edge, or leave the site unresolved for fallback handling (analysis/app/src/syspartUtility.cpp:1375-1379; analysis/app/src/ipcallgraph.cpp:709-715,768-774).
- Actual: Under the stated missing-node condition, no edge is inserted, fallback is skipped, and the printer has no indirect child to print for that site (analysis/app/src/syspartUtility.cpp:1365-1379; analysis/app/src/ipcallgraph.cpp:692-705,766-775). This is source-supported, not runtime-confirmed.
- Evidence: analysis/app/src/syspartUtility.cpp:972-983 — a parsed function's address can supply a name; analysis/app/src/syspartUtility.cpp:1340-1358 — a named target passes the resolution check; analysis/app/src/syspartUtility.cpp:1362-1379 — a missing node skips edge insertion but the site is marked resolved; analysis/app/src/ipcallgraph.cpp:1797-1807,1820-1836 — target resolution precedes indirect edge generation; analysis/app/src/ipcallgraph.cpp:692-705 — a resolved site skips fallback generation.
- Assessment: The guard in getNode can find an existing node with the same name and module, but returns null when neither that node nor the exact Function key exists (analysis/app/src/ipcallgraph.h:355-369). Tiny source-bounded test: give root an indirect call whose resolved address names a parsed function hidden, while hidden has no graph node or same-name node. The expected output is an INDIRECT_RESOLVED line from root to hidden; the traced path produces no indirect edge line (analysis/app/src/syspartUtility.cpp:1362-1379; analysis/app/src/ipcallgraph.cpp:766-775). No runtime output was captured.

### NSS discovery can omit a configured backend in a later search path

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/nss.cpp:249`
- Invariant: A configured, available NSS backend must enter the dependency list used to resolve its functions (analysis/app/src/nss.cpp:269-275; analysis/app/src/nss.cpp:47-59).
- Mechanism: Discovery stops after the first system directory containing any NSS library, and skips system directories entirely if a user directory contains one. Other backend names are then absent from nssModules (analysis/app/src/nss.cpp:235-252).
- Reproducer: Source-bounded case: the first searched directory contains one NSS library, while a configured custom backend exists only in a later directory. The custom name is not added to databaselibs, so resolveNss has no dependency for it (analysis/app/src/nss.cpp:244-275; analysis/app/src/nss.cpp:55-59; analysis/app/src/ipcallgraph.cpp:1909-1920).
- Expected: For the stated test case, mode 1 includes an NSS callgraph edge to `_nss_custom_gethostbyname`, assuming the library and symbol resolve (analysis/app/src/nss.cpp:137, analysis/app/src/ipcallgraph.cpp:1913-1943, analysis/app/src/ipcallgraph.cpp:1972-1976).
- Actual: The source path omits `custom` from databaselibs, so it cannot produce that edge through NSS resolution; no runtime output was observed (analysis/app/src/nss.cpp:244-249, analysis/app/src/nss.cpp:269-279, analysis/app/src/nss.cpp:55-59, analysis/app/src/ipcallgraph.cpp:1909-1913).
- Evidence: analysis/app/src/testSyspart.cpp:77-86, analysis/app/src/testSyspart.cpp:186-191 — `-a 1` calls run1; analysis/app/src/syspart.cpp:1542-1551 — run1 resolves NSS before generating and adding edges; analysis/app/src/nss.cpp:235-249 — discovery skips system paths after a user-path match or the first system-path match; analysis/app/src/nss.cpp:269-279 — only discovered names and listed fallback names enter databaselibs; analysis/app/src/nss.cpp:47-59 — databaselibs supplies each symbol’s needed libraries; analysis/app/src/ipcallgraph.cpp:1909-1943 — resolution iterates only those needed libraries; analysis/app/src/ipcallgraph.cpp:1955-1979 — edges come from resolved functions.
- Assessment: Tiny test case: set /etc/nsswitch.conf to `hosts: files custom`; leave USER_LIBRARY_PATH unset; place a matching NSS library in the first system directory and `libnss_custom.so.2` only in `/usr/lib`. The first match stops system discovery, and `custom` is outside the fixed-name fallback (analysis/app/src/nss.cpp:202-205, analysis/app/src/nss.cpp:240-249, analysis/app/src/nss.cpp:269-279). With a call to gethostbyname and a resolvable custom library, the expected mode 1 output includes an edge to `_nss_custom_gethostbyname`; the source predicts that edge will be absent (analysis/app/src/nss.cpp:137, analysis/app/src/nss.cpp:55-59, analysis/app/src/ipcallgraph.cpp:1913-1943, analysis/app/src/ipcallgraph.cpp:1972-1976). This is a source-supported prediction; no binary was run.

### Intermediate edge lists remain cached and can use quadratic memory

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/ipcallgraph.h:58`
- Invariant: Keeping k targets at one callsite requires storage proportional to the final k-target list (analysis/app/src/ipcallgraph.cpp:34-45).
- Mechanism: Each added target copies the previous vector and caches the new vector. The cache retains every prefix, while cleanupCache has no call in the source tree (analysis/app/src/ipcallgraph.h:47-67; analysis/app/src/ipcallgraph.h:83-100).
- Reproducer: Bounded cost: if -i resolves k distinct targets for one site, its insertion loop creates cached vectors of lengths 1 through k, retaining Θ(k²) pointers (analysis/app/src/syspartUtility.cpp:1360-1376; analysis/app/src/ipcallgraph.cpp:34-45; analysis/app/src/ipcallgraph.h:47-67).
- Expected: Storage proportional to the final k-target list at the callsite (analysis/app/src/ipcallgraph.cpp:34-45).
- Actual: The source retains Θ(k²) pointer slots across cached prefixes; memory use was not measured (analysis/app/src/ipcallgraph.h:47-67; analysis/app/src/ipcallgraph.h:99-100).
- Evidence: analysis/app/src/testSyspart.cpp:68 — -i enables indirect-call analysis; analysis/app/src/testSyspart.cpp:187-191 — -a 1 calls run1; analysis/app/src/syspart.cpp:1538-1551 — run1 passes the flag and generates the graph; analysis/app/src/ipcallgraph.cpp:1797-1810 — generation runs findIndirectCallTargets; analysis/app/src/syspartUtility.cpp:1340-1376 — resolved targets are inserted one at a time; analysis/app/src/ipcallgraph.cpp:34-45 — insertion replaces the callsite list with an appended copy; analysis/app/src/ipcallgraph.h:47-67 — getOrCreate caches each new list; analysis/app/src/ipcallgraph.h:83-100 — cleanup exists, but the cache owns its entries. A source search found no cleanupCache call.
- Assessment: The candidate holds when -i resolves k distinct targets at one callsite: each insertion creates a new prefix list, and the cache retains both a vector key and a shared vector value for every prefix, yielding Θ(k²) pointer slots (analysis/app/src/syspartUtility.cpp:1360-1376; analysis/app/src/ipcallgraph.cpp:34-45; analysis/app/src/ipcallgraph.h:47-67; analysis/app/src/ipcallgraph.h:99-100). The guard requires resolved targets and skips missing graph nodes (analysis/app/src/syspartUtility.cpp:1340-1376); it does not cap k. A tiny proposed test inserts three distinct targets at one address and inspects the cache: expected list lengths are 1, 2, and 3, totaling six pointer slots in keys and six in values, while the final callsite list has length three (analysis/app/src/ipcallgraph.cpp:34-45; analysis/app/src/ipcallgraph.h:47-67; analysis/app/src/ipcallgraph.h:99-100). No test or binary was run.

<!-- harness:logic:mode-1:end -->

<!-- harness:logic:mode-2:start -->
## Harness logic audit — mode 2

Dispatcher and modules: analysis/app/src/testSyspart.cpp, analysis/app/src/syspart.cpp, analysis/app/src/syspart.h, analysis/app/src/ipcallgraph.cpp, analysis/app/src/nonreturnAnalysis.cpp

### Forward scan skips instructions after the partition address in the same block

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:981`
- Invariant: Instructions reachable after the partition address must contribute their syscalls (analysis/app/src/syspart.cpp:951; analysis/app/src/testSyspart.cpp:104).
- Mechanism: The address lookup finds the containing block, but the scan starts from its successors and never scans that block (analysis/app/src/syspart.cpp:956; analysis/app/src/syspart.cpp:981; analysis/app/src/syspart.cpp:997).
- Reproducer: Place a non-control-flow partition instruction and a syscall later in the same block, with no successor containing that syscall (analysis/app/src/syspart.cpp:956; analysis/app/src/syspart.cpp:981). This is a source trace; no runtime output was observed.
- Expected: For the proposed test, `JSON [...]` contains 39 (analysis/app/src/syspart.cpp:92; analysis/app/src/syspart.cpp:2484).
- Actual: The source-traced scan omits the same-block syscall; if no other path contributes 39, `JSON [...]` omits 39 (analysis/app/src/syspart.cpp:981; analysis/app/src/syspart.cpp:997; analysis/app/src/syspart.cpp:2484).
- Evidence: analysis/app/src/testSyspart.cpp:220 — mode 2 calls syscallsOfMainLoop; analysis/app/src/syspart.cpp:2396 — it calls findSyscallsAccessible with the partition address; analysis/app/src/syspart.cpp:956 — address lookup records only the containing block; analysis/app/src/syspart.cpp:981 — the stack is seeded with that block’s successors; analysis/app/src/syspart.cpp:997 — syscall lookup scans only stacked blocks; analysis/app/src/syspart.cpp:2398 — the returned set feeds the JSON set. The later fini-set addition can supply 39 independently but does not scan the omitted block (analysis/app/src/syspart.cpp:2417; analysis/app/src/syspart.cpp:2484).
- Assessment: A tiny test would put a partition-point NOP, `mov $39,%eax`, `syscall`, and `ret` in one function, then run mode 2 with the NOP address and that function. The expected `JSON [...]` output contains 39 (`getpid`), assuming no unrelated path contributes it (analysis/app/src/testSyspart.cpp:193; analysis/app/src/testSyspart.cpp:220; analysis/app/src/syspart.cpp:92; analysis/app/src/syspart.cpp:2484). The disassembler does not split blocks at OS-interrupt instructions, so this same-block case is possible (analysis/tools/egalito/src/disasm/disassemble.cpp:1564; analysis/tools/egalito/src/disasm/disassemble.cpp:1567). No binary was run or output captured.

### A queued CFG block can be scanned twice

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspart.cpp:1047`
- Invariant: Each reachable block should be scanned once for syscalls and counted once in PARTITION_SIZE (analysis/app/src/syspart.cpp:997; analysis/app/src/syspart.cpp:999; analysis/app/src/syspart.cpp:2519).
- Mechanism: The traversal checks only blocks already popped; it does not check blocks already queued. A second path can queue the same destination before its first copy is popped (analysis/app/src/syspart.cpp:989; analysis/app/src/syspart.cpp:993; analysis/app/src/syspart.cpp:1047).
- Reproducer: Use CFG edges A→D, A→B, and B→D. If A queues D then B, B queues another D before either D is popped; both copies scan D (analysis/app/src/syspart.cpp:982; analysis/app/src/syspart.cpp:1041). This is a bounded source example, not an observed run.
- Expected: For the stated test case, PARTITION_SIZE 2: one instruction in B and one in D (analysis/app/src/syspart.cpp:997-999; analysis/app/src/syspart.cpp:2519).
- Actual: The source trace gives PARTITION_SIZE 3 because D is popped and counted twice; this is not runtime-confirmed (analysis/app/src/syspart.cpp:991-999; analysis/app/src/syspart.cpp:1047-1049; analysis/app/src/syspart.cpp:2519).
- Evidence: analysis/app/src/testSyspart.cpp:193-220 — mode -a 2 calls syscallsOfMainLoop; analysis/app/src/syspart.cpp:2396 — it calls findSyscallsAccessible; analysis/app/src/syspart.cpp:981-989 — A's successors are pushed before visited is created; analysis/app/src/syspart.cpp:991-999 — each popped block is scanned and its instructions counted without a pop-time visited guard; analysis/app/src/syspart.cpp:1041-1049 — successor enqueue checks only visited blocks, allowing B to queue an already queued D; analysis/app/src/syspart.cpp:1000-1035 — both scans repeat syscall and callee processing; analysis/app/src/syspart.cpp:2519 — the accumulated count is printed.
- Assessment: A tiny test case is a function with CFG edges A→D, A→B, and B→D, with one instruction each in B and D and the partition point in A. If A's links enumerate D before B, the stack pops B first; B queues D while A's D remains queued. The expected output is PARTITION_SIZE 2, while this source path produces PARTITION_SIZE 3 (analysis/app/src/syspart.cpp:981-989; analysis/app/src/syspart.cpp:991-999; analysis/app/src/syspart.cpp:1041-1049; analysis/app/src/syspart.cpp:2519). The caller's visited check tracks function and address pairs, so it does not prevent duplicate block scans within this call (analysis/app/src/syspart.cpp:2370-2396).

### Unresolved thread start reads an uninitialized address

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:1186`
- Invariant: A failed thread-entry resolution must not supply an arbitrary address to function lookup, because identified thread entries stop mode 2's caller walk (analysis/app/src/syspart.cpp:1202; analysis/app/src/syspart.cpp:2408).
- Mechanism: The local thread_func_addr has no initializer. find_thread_function and findRegDef can return NULL without assigning it, yet the fallback passes it to findFunctionByAddress (analysis/app/src/syspart.cpp:1131; analysis/app/src/syspart.cpp:1162; analysis/app/src/syspart.cpp:1186; analysis/app/src/syspart.cpp:1189).
- Reproducer: Give a pthread_create callsite an RDX definition that matches none of findRegDef's handled forms; it reaches the NULL return without writing the address (analysis/app/src/syspart.cpp:1088; analysis/app/src/syspart.cpp:1129; analysis/app/src/syspart.cpp:1131). No runtime outcome was observed.
- Expected: An unresolved thread entry supplies no lookup address and does not enter the thread-start set (analysis/app/src/syspart.cpp:1132; analysis/app/src/syspart.cpp:1191).
- Actual: The source passes an uninitialized address to function lookup; a coincidental match could enter the thread-start set and stop the caller walk (analysis/app/src/syspart.cpp:1183; analysis/app/src/syspart.cpp:1187; analysis/app/src/syspart.cpp:1191; analysis/app/src/syspart.cpp:2408). This is source-supported, not runtime-confirmed.
- Evidence: analysis/app/src/testSyspart.cpp:193 — mode 2 dispatches to syscallsOfMainLoop at analysis/app/src/testSyspart.cpp:220; analysis/app/src/syspart.cpp:2349 — it obtains thread starts; analysis/app/src/syspart.cpp:1183 — the direct-call address has no initializer; analysis/app/src/syspart.cpp:1156 — find_thread_function forwards it to findRegDef; analysis/app/src/syspart.cpp:1132 — an unhandled definition returns NULL without assigning it; analysis/app/src/syspart.cpp:1185 — NULL selects fallback; analysis/app/src/syspart.cpp:1187 — fallback reads the unset address; analysis/app/src/syspart.cpp:54 — lookup matches function addresses; analysis/app/src/syspart.cpp:1191 — a match enters the thread-start set; analysis/app/src/syspart.cpp:2408 — membership stops the caller walk. The indirect-call path repeats the issue at analysis/app/src/syspart.cpp:1215 and analysis/app/src/syspart.cpp:1219.
- Assessment: The direct and indirect pthread_create paths have the same missing guard: each declares an uninitialized address and uses it for lookup whenever resolution returns NULL (analysis/app/src/syspart.cpp:1183; analysis/app/src/syspart.cpp:1187; analysis/app/src/syspart.cpp:1215; analysis/app/src/syspart.cpp:1219). A tiny test fixture would pass RDX from a stack load, such as `mov -8(%rbp), %rdx`, with no linked function target. That definition matches none of the handled forms, so the expected result is an empty thread-start set and a mode 2 `JSON [...]` result that retains syscalls found by walking to the caller (analysis/app/src/syspart.cpp:1088; analysis/app/src/syspart.cpp:1100; analysis/app/src/syspart.cpp:1117; analysis/app/src/syspart.cpp:1132; analysis/app/src/syspart.cpp:2408; analysis/app/src/syspart.cpp:2410; analysis/app/src/syspart.cpp:2484). No runtime output was captured.

### An invalid partition address still produces a mode 2 result

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:966`
- Invariant: The supplied partition address must identify an instruction in its named function before a result is reported (analysis/app/src/testSyspart.cpp:104; analysis/app/src/syspart.cpp:2353).
- Mechanism: If no instruction matches, findSyscallsAccessible returns an empty set without signalling failure. The caller continues its parent-site walk, adds finalization syscalls, and prints results (analysis/app/src/syspart.cpp:956; analysis/app/src/syspart.cpp:966; analysis/app/src/syspart.cpp:2396; analysis/app/src/syspart.cpp:2417; analysis/app/src/syspart.cpp:2474).
- Reproducer: Supply an address absent from the named function while that function has a returning caller with reachable syscalls (analysis/app/src/syspart.cpp:956; analysis/app/src/syspart.cpp:2404; analysis/app/src/syspart.cpp:2410). This is a source trace; no runtime output was observed.
- Expected: Reject an address absent from the named function before reporting a syscall set (analysis/app/src/testSyspart.cpp:106; analysis/app/src/syspart.cpp:956).
- Actual: The source permits a MAINLOOP and JSON result even when the supplied address matched no instruction; the set may include syscalls found through parent call sites and finalization (analysis/app/src/syspart.cpp:966; analysis/app/src/syspart.cpp:2410; analysis/app/src/syspart.cpp:2417; analysis/app/src/syspart.cpp:2474; analysis/app/src/syspart.cpp:2484).
- Evidence: analysis/app/src/testSyspart.cpp:193 — mode 2 dispatches after checking only that its arguments are present (analysis/app/src/testSyspart.cpp:195; analysis/app/src/testSyspart.cpp:220). analysis/app/src/syspart.cpp:2353 — the caller checks that the function and call-graph node exist (analysis/app/src/syspart.cpp:2354; analysis/app/src/syspart.cpp:2359), then passes the parsed address to findSyscallsAccessible (analysis/app/src/syspart.cpp:2366; analysis/app/src/syspart.cpp:2396). analysis/app/src/syspart.cpp:956 — that function searches instruction addresses and returns an empty set when none matches, without signalling failure (analysis/app/src/syspart.cpp:960; analysis/app/src/syspart.cpp:966). analysis/app/src/syspart.cpp:2402 — the caller continues to returning parent call sites (analysis/app/src/syspart.cpp:2404; analysis/app/src/syspart.cpp:2410), adds finalization syscalls (analysis/app/src/syspart.cpp:2417), and prints MAINLOOP and JSON results (analysis/app/src/syspart.cpp:2474; analysis/app/src/syspart.cpp:2484).
- Assessment: Tiny test: use a binary with a returning target() called by main(), then run mode 2 with target as the function and an address absent from target. The expected behavior is an invalid-partition-address diagnostic and no MAINLOOP or JSON result, because mode 2 specifies an address in the named function (analysis/app/src/testSyspart.cpp:104; analysis/app/src/testSyspart.cpp:106). The source instead reaches the result prints (analysis/app/src/syspart.cpp:2474; analysis/app/src/syspart.cpp:2484). No runtime output was observed.

### Caller sites with the same address overwrite each other

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/ipcallgraph.cpp:122`
- Invariant: Every caller site of a partition function must remain available to the mode 2 backward walk (analysis/app/src/syspart.cpp:2410; analysis/app/src/syspart.cpp:2413).
- Mechanism: The callee stores parents in a map keyed only by callsite address. Inserting a second caller at that address replaces the first, and mode 2 walks the resulting map (analysis/app/src/ipcallgraph.h:114; analysis/app/src/ipcallgraph.cpp:121; analysis/app/src/ipcallgraph.cpp:122; analysis/app/src/syspart.cpp:2410).
- Reproducer: Bounded source case: functions in two modules call the partition function from the same numeric address, and only the first caller can reach syscall X after its call. Insert the second edge last (analysis/app/src/ipcallgraph.cpp:243; analysis/app/src/ipcallgraph.cpp:247; analysis/app/src/ipcallgraph.cpp:122). No runtime output was observed.
- Expected: Both callers are visited and syscall 39 enters the mode 2 JSON set (analysis/app/src/syspart.cpp:2396; analysis/app/src/syspart.cpp:2400; analysis/app/src/syspart.cpp:2490).
- Actual: For the stated insertion order, only caller B remains in the parent map, so this walk cannot collect syscall 39 through caller A (analysis/app/src/ipcallgraph.cpp:122; analysis/app/src/ipcallgraph.h:194; analysis/app/src/syspart.cpp:2410; analysis/app/src/syspart.cpp:2413).
- Evidence: Direct calls pass their instruction address to addEdge (analysis/app/src/ipcallgraph.cpp:893). addEdge inserts the caller into the callee's parent map (analysis/app/src/ipcallgraph.cpp:247). That map has one value per address, so a later caller at the same address replaces the earlier one (analysis/app/src/ipcallgraph.h:114; analysis/app/src/ipcallgraph.cpp:122). A separate map retains caller-qualified entries, but mode 2 reads the address-only map (analysis/app/src/ipcallgraph.cpp:123; analysis/app/src/ipcallgraph.cpp:124; analysis/app/src/ipcallgraph.h:192; analysis/app/src/syspart.cpp:2410). The backward walk pushes only entries returned by that map, subject to the return and thread-start guards (analysis/app/src/syspart.cpp:2404; analysis/app/src/syspart.cpp:2408; analysis/app/src/syspart.cpp:2410; analysis/app/src/syspart.cpp:2413). The source acknowledges that functions can share numeric addresses (analysis/app/src/syspart.cpp:42).
- Assessment: Tiny test case: two returning functions in different modules call the same partition function from numeric address 0x1000. Put syscall 39 in a successor block after caller A's call, leave caller B's path free of syscalls, and insert B's edge last. With no other reachable or finalization syscalls, the mode 2 JSON should be `JSON [39]`; the source trace predicts `JSON []` because A's parent entry is replaced (analysis/app/src/syspart.cpp:981; analysis/app/src/syspart.cpp:1000; analysis/app/src/syspart.cpp:1005; analysis/app/src/ipcallgraph.cpp:122; analysis/app/src/syspart.cpp:2484). No runtime output was captured.

### Syscall lookup can select another module's function

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:168`
- Invariant: A syscall summary requested for a Function pointer must describe that function (analysis/app/src/syspart.cpp:284; analysis/app/src/syspart.cpp:294; analysis/app/src/syspart.cpp:968).
- Mechanism: getSysNode returns the first summary with the same address and name before it necessarily reaches the exact pointer. The lookup does not compare modules (analysis/app/src/syspart.cpp:163; analysis/app/src/syspart.cpp:166; analysis/app/src/syspart.cpp:168).
- Reproducer: Bounded source case: two parsed modules contain functions with the same name and numeric address but different syscalls; the other function's summary appears first in syscall_mapping iteration (analysis/app/src/syspart.cpp:284; analysis/app/src/syspart.cpp:290; analysis/app/src/syspart.cpp:163). No runtime output was observed.
- Expected: The scan uses B's instruction syscall map and MAIN uses the selected start function's syscall sets (analysis/app/src/syspart.cpp:1000; analysis/app/src/syspart.cpp:2495; analysis/app/src/syspart.cpp:2500; analysis/app/src/syspart.cpp:2504).
- Actual: If A's matching entry iterates first, both lookups can select A's summary. Because the scan keys the selected map by instruction pointer, B's instructions can be missed in JSON; differing syscall sets can change MAIN (analysis/app/src/syspart.cpp:168; analysis/app/src/syspart.cpp:1000; analysis/app/src/syspart.cpp:2484; analysis/app/src/syspart.cpp:2495; analysis/app/src/syspart.cpp:2511). These are source-supported effects, not observed output.
- Evidence: Mode -a 2 calls syscallsOfMainLoop (analysis/app/src/testSyspart.cpp:193; analysis/app/src/testSyspart.cpp:220). It creates summaries for callgraph functions and stores each function pointer and instruction syscall map (analysis/app/src/syspart.cpp:284; analysis/app/src/syspart.cpp:290; analysis/app/src/syspart.cpp:293; analysis/app/src/syspart.cpp:294; analysis/app/src/syspart.cpp:321). getSysNode checks pointer identity and then address plus name on each iteration, without a module check or a prior full search for the exact pointer (analysis/app/src/syspart.cpp:163; analysis/app/src/syspart.cpp:166; analysis/app/src/syspart.cpp:168). The partition scan requests that summary for its current function; the callgraph lookup has a module check only in its separate fallback path (analysis/app/src/syspart.cpp:968; analysis/app/src/ipcallgraph.h:355; analysis/app/src/ipcallgraph.h:362).
- Assessment: Tiny test case: put distinct functions A::foo and B::foo at the same numeric address in the syscall map, with A's entry iterating first. Give A direct syscalls {0,2} and B {1}, then print the module of getSysNode(B)->func. Expected output: B. The lookup returns A before reaching B's exact pointer (analysis/app/src/syspart.cpp:163; analysis/app/src/syspart.cpp:166; analysis/app/src/syspart.cpp:168; analysis/app/src/syspart.cpp:170). No runtime output was observed.

### Repeated syscall sites trigger identical derived-summary traversals

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspart.cpp:313`
- Invariant: A function and syscall-number pair needs one backward propagation, regardless of how many instructions invoke that syscall (analysis/app/src/syspart.cpp:301; analysis/app/src/syspart.cpp:408).
- Mechanism: findDirectSyscalls appends the same SysNode once per matching instruction value. findDerivedSyscalls starts a fresh traversal with a fresh processed set for every appended entry (analysis/app/src/syspart.cpp:296; analysis/app/src/syspart.cpp:313; analysis/app/src/syspart.cpp:411; analysis/app/src/syspart.cpp:420).
- Reproducer: Bounded cost: one function with m sites for syscall X and a backward graph of V nodes and E edges causes m equivalent traversals, costing O(m(V+E)) graph visits for that pair (analysis/app/src/syspart.cpp:299; analysis/app/src/syspart.cpp:313; analysis/app/src/syspart.cpp:411; analysis/app/src/syspart.cpp:434). This is a source bound, not a measurement.
- Expected: One backward traversal per function and syscall number, with the same derived syscall set (analysis/app/src/syspart.cpp:448).
- Actual: For m resolved sites of the same syscall in one function, the traced loops perform m equivalent backward traversals. That is O(m(V+E)) graph visits for a backward graph with V nodes and E edges, excluding container-operation costs; result insertion deduplicates only afterward (analysis/app/src/syspart.cpp:296; analysis/app/src/syspart.cpp:411; analysis/app/src/syspart.cpp:420; analysis/app/src/syspart.cpp:428; analysis/app/src/syspart.cpp:434; analysis/app/src/syspart.cpp:448).
- Evidence: analysis/app/src/testSyspart.cpp:193 — `-a 2` dispatches to `syscallsOfMainLoop` at line 220 after checking its arguments. analysis/app/src/syspart.cpp:2343 — that caller invokes `findDirectSyscalls`, then `findDerivedSyscalls` at line 2344. analysis/tools/egalito/src/pass/findsyscalls.cpp:36 — the pass visits instructions and records resolved syscall values by instruction at lines 40–45 and 68–75. analysis/app/src/syspart.cpp:284 — direct discovery iterates call graph nodes; lines 296–315 append the same SysNode for each matching instruction value, while line 301 deduplicates only its direct syscall set. analysis/app/src/ipcallgraph.h:355 — `getNode` finds that function's node in `nodeMap` at lines 357–371. analysis/app/src/syspart.cpp:408 — derived discovery iterates every appended entry; lines 413–420 create a fresh stack and processed set for each, lines 428–438 revisit the backward graph, and line 448 inserts the result into a set. The null-node guard at analysis/app/src/syspart.cpp:416 does not remove duplicate entries for a node obtained from `nodeMap`.
- Assessment: A tiny test would use a call graph with root calling f and two distinct instructions in f both resolved to syscall 1. The expected result after deduplication is `derived(root)={1}, backward_traversals=1`; the current source predicts the same derived set with `backward_traversals=2` (analysis/app/src/syspart.cpp:296; analysis/app/src/syspart.cpp:308; analysis/app/src/syspart.cpp:314; analysis/app/src/syspart.cpp:411; analysis/app/src/syspart.cpp:448). This is a source prediction, not observed output.

### Nonreturn analysis retains a CFG from every scan

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/nonreturnAnalysis.cpp:134`
- Invariant: A CFG needed only for one nonreturn scan should be released after that scan (analysis/app/src/nonreturnAnalysis.cpp:134; analysis/app/src/nonreturnAnalysis.cpp:142).
- Mechanism: Each pass allocates a ControlFlowGraph for every function still marked returning. The pointer is neither deleted on the empty-graph path nor after isNonReturn, and further passes allocate again (analysis/app/src/nonreturnAnalysis.cpp:115; analysis/app/src/nonreturnAnalysis.cpp:134; analysis/app/src/nonreturnAnalysis.cpp:135; analysis/app/src/nonreturnAnalysis.cpp:152).
- Reproducer: Bounded cost: if P stabilization passes each scan R returning functions, this path allocates up to P×R CFG objects without releasing them; mode 2 invokes it before the caller walk (analysis/app/src/syspart.cpp:2346; analysis/app/src/nonreturnAnalysis.cpp:115; analysis/app/src/nonreturnAnalysis.cpp:122; analysis/app/src/nonreturnAnalysis.cpp:134). Memory use was not measured.
- Expected: Completed scans release their CFGs, allowing their memory to be reused in later passes (analysis/app/src/nonreturnAnalysis.cpp:134; analysis/app/src/nonreturnAnalysis.cpp:152).
- Actual: The traced CFG allocations have no release path in run, so completed scans retain avoidable memory (analysis/app/src/nonreturnAnalysis.cpp:134; analysis/app/src/nonreturnAnalysis.cpp:135; analysis/app/src/nonreturnAnalysis.cpp:142; analysis/app/src/nonreturnAnalysis.cpp:152).
- Evidence: analysis/app/src/testSyspart.cpp:193 — mode 2 dispatches to syscallsOfMainLoop at analysis/app/src/testSyspart.cpp:220; analysis/app/src/syspart.cpp:2346 — that method creates NonReturnAnalysis and calls run at analysis/app/src/syspart.cpp:2347; analysis/app/src/nonreturnAnalysis.cpp:124 — already-nonreturning functions are skipped; analysis/app/src/nonreturnAnalysis.cpp:134 — each remaining function gets a new CFG; analysis/app/src/nonreturnAnalysis.cpp:135 — the empty-graph branch continues without deletion; analysis/app/src/nonreturnAnalysis.cpp:142 — the other branch scans without deletion; analysis/app/src/nonreturnAnalysis.cpp:152 — stabilization can repeat the scan; analysis/tools/egalito/src/analysis/controlflow.cpp:35 — CFG cleanup exists in its destructor, which these paths never invoke.
- Assessment: Mode -a 2 calls the nonreturn scan before the caller walk (analysis/app/src/testSyspart.cpp:193; analysis/app/src/testSyspart.cpp:220; analysis/app/src/syspart.cpp:2346; analysis/app/src/syspart.cpp:2372). Each pass allocates a CFG for every function still marked returning, and neither exit path releases it (analysis/app/src/nonreturnAnalysis.cpp:115; analysis/app/src/nonreturnAnalysis.cpp:124; analysis/app/src/nonreturnAnalysis.cpp:134; analysis/app/src/nonreturnAnalysis.cpp:135; analysis/app/src/nonreturnAnalysis.cpp:142; analysis/app/src/nonreturnAnalysis.cpp:152). Tiny proposed test: analyze a program with `int leaf(void){return 0;} int main(void){return leaf();}` using `-a 2,<callsite>,main` under a leak checker; expected output is a direct-leak report pointing to the allocation at analysis/app/src/nonreturnAnalysis.cpp:134. This test was not run.

<!-- harness:logic:mode-2:end -->

<!-- harness:logic:mode-3:start -->
## Harness logic audit — mode 3

Dispatcher and modules: README.md, analysis/app/README.md, analysis/app/src/testSyspart.cpp, analysis/app/src/syspart.h, analysis/app/src/syspart.cpp, analysis/app/src/ipcallgraph.h, analysis/app/src/ipcallgraph.cpp

### An unresolved start function reaches CFG construction

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/testSyspart.cpp:181`
- Invariant: Mode 3 needs a resolved start function before setting the graph root (analysis/app/src/syspart.cpp:2025).
- Mechanism: The driver checks that -s was supplied, but passes a failed name lookup to run7 without checking for null (analysis/app/src/testSyspart.cpp:143, analysis/app/src/testSyspart.cpp:179, analysis/app/src/testSyspart.cpp:181, analysis/app/src/testSyspart.cpp:223). setRoot then requests dataflow for that null pointer, which reaches CFG construction (analysis/app/src/ipcallgraph.cpp:169, analysis/app/src/ipcallgraph.cpp:176, analysis/tools/egalito/src/analysis/dataflow.cpp:29, analysis/tools/egalito/src/analysis/dataflow.cpp:13).
- Reproducer: Source-bounded case: use -s with a name absent from the parsed program and -a 3,foo (analysis/app/src/syspart.cpp:66, analysis/app/src/testSyspart.cpp:181, analysis/app/src/testSyspart.cpp:223).
- Expected: An unresolved start function is rejected before setRoot (analysis/app/src/syspart.cpp:2025).
- Actual: The source path passes null to CFG construction, where it is dereferenced; the runtime outcome is unobserved (analysis/app/src/ipcallgraph.cpp:176, analysis/tools/egalito/src/analysis/controlflow.cpp:55).
- Evidence: analysis/app/src/syspart.cpp:66 — name lookup starts with null and returns it when no function matches; analysis/app/src/testSyspart.cpp:181 — the result is passed to setStartFunc without a guard; analysis/app/src/syspart.cpp:23 — setStartFunc stores it; analysis/app/src/testSyspart.cpp:223 — mode 3 calls run7; analysis/app/src/syspart.cpp:2025 — run7 passes the stored root to setRoot; analysis/app/src/ipcallgraph.cpp:169 — setRoot has no null guard and calls getWorkingSet at line 176; analysis/tools/egalito/src/analysis/dataflow.cpp:29 — an uncached pointer reaches addUseDefFor; analysis/tools/egalito/src/analysis/dataflow.cpp:13 — it constructs a CFG; analysis/tools/egalito/src/analysis/controlflow.cpp:53 — CFG construction dereferences the function at line 55. The later check for the comparison function does not protect the root (analysis/app/src/syspart.cpp:2040).
- Assessment: The presence check requires -s but does not verify that its name resolves (analysis/app/src/testSyspart.cpp:143, analysis/app/src/testSyspart.cpp:181). A tiny proposed test is a parsed program with main, -s __missing_root__, and -a 3,main; it should print "Start(root) function not found" and exit before graph construction (analysis/app/src/testSyspart.cpp:59, analysis/app/src/testSyspart.cpp:223, analysis/app/src/syspart.cpp:2025). No runtime output was captured.

### A comparison function outside the graph produces no difference

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:2053`
- Invariant: A named comparison function must have a syscall summary before mode 3 can print the requested set difference (analysis/app/src/testSyspart.cpp:98, analysis/app/src/syspart.cpp:2058, analysis/app/src/syspart.cpp:2060).
- Mechanism: Graph construction starts from the selected root and other discovered roots; direct traversal scans only queued functions (analysis/app/src/syspart.cpp:2025, analysis/app/src/ipcallgraph.cpp:1742, analysis/app/src/ipcallgraph.cpp:1746). The comparison name is resolved afterward, and run7 returns silently if that function has no graph node (analysis/app/src/syspart.cpp:2040, analysis/app/src/syspart.cpp:2052, analysis/app/src/syspart.cpp:2053).
- Reproducer: Source-bounded graph: root directly invokes syscall 39; a separately named function invokes syscall 1 but has no path or address-taken reference from any graph root. Request -s root -g -a 3,other (analysis/app/src/syspart.cpp:2029, analysis/app/src/ipcallgraph.cpp:1746, analysis/app/src/syspart.cpp:2052).
- Expected: `Filtered system calls : getpid` and `Total system calls of function : 1`, or an explicit message that `other` lacks a summary (analysis/app/src/syspart.cpp:2060, analysis/app/src/syspart.cpp:2064).
- Actual: For the source-bounded case, `run7` returns without printing `Filtered system calls` (analysis/app/src/syspart.cpp:2053, analysis/app/src/syspart.cpp:2061). This is a source trace, not observed output.
- Evidence: analysis/app/src/testSyspart.cpp:223 — mode 3 selects this caller; analysis/app/src/testSyspart.cpp:231 — it passes `other` to `run7`; analysis/app/src/syspart.cpp:2025 — graph construction starts at `root`; analysis/app/src/ipcallgraph.cpp:1746 — direct graph traversal processes queued roots; analysis/app/src/ipcallgraph.cpp:893 — direct callees are queued; analysis/app/src/ipcallgraph.cpp:453 — init and fini references can add roots; analysis/app/src/syspart.cpp:2040 — `other` is resolved only after graph construction and syscall discovery; analysis/app/src/syspart.cpp:282 — syscall discovery scans graph nodes; analysis/app/src/ipcallgraph.h:357 — `getNode` searches existing nodes and returns null if none matches; analysis/app/src/syspart.cpp:2052 — `run7` looks up `other`'s node; analysis/app/src/syspart.cpp:2053 — a missing node causes return before the difference is printed at analysis/app/src/syspart.cpp:2061.
- Assessment: A tiny test case would define `root` with a direct syscall 39 (`getpid`) and an unreferenced, retained function `other` with a direct syscall 1 (`write`), then analyze `-s root -g -a 3,other`. The requested difference is `getpid`, with one syscall in `other` (analysis/app/src/syspart.cpp:90, analysis/app/src/testSyspart.cpp:107). The source supports a silent early return for this case; no binary was run.

### An invalid comparison name is rejected only after full analysis

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspart.cpp:2040`
- Invariant: A name that cannot be compared should be validated before work whose result is discarded (analysis/app/src/syspart.cpp:2040, analysis/app/src/syspart.cpp:2041).
- Mechanism: run7 resolves the comparison name only after NSS resolution, graph generation, direct syscall extraction, derived syscall propagation, and root detail printing (analysis/app/src/syspart.cpp:2026, analysis/app/src/syspart.cpp:2029, analysis/app/src/syspart.cpp:2036, analysis/app/src/syspart.cpp:2037, analysis/app/src/syspart.cpp:2040).
- Reproducer: Bounded cost case: supply a comparison name absent from all M loaded functions. The lookup could reject it after an O(M) scan, but the source first performs graph and syscall analysis over its discovered nodes and edges (analysis/app/src/syspart.cpp:66, analysis/app/src/syspart.cpp:2040, analysis/app/src/ipcallgraph.cpp:1767, analysis/app/src/syspart.cpp:284, analysis/app/src/syspart.cpp:408).
- Expected: For a missing comparison name, reject it after any needed NSS loading and before graph generation and syscall passes (analysis/app/src/ipcallgraph.cpp:1919, analysis/app/src/ipcallgraph.cpp:1921, analysis/app/src/syspart.cpp:2026, analysis/app/src/syspart.cpp:2029, analysis/app/src/syspart.cpp:2040).
- Actual: The source runs those passes before the missing-name return; the cost is inferred, not measured (analysis/app/src/syspart.cpp:2026, analysis/app/src/syspart.cpp:2038, analysis/app/src/syspart.cpp:2041).
- Evidence: analysis/app/src/testSyspart.cpp:225 — mode 3 checks only for a comma; analysis/app/src/testSyspart.cpp:231 — it extracts and passes the name; analysis/app/src/syspart.cpp:2026 — run7 resolves NSS; analysis/app/src/syspart.cpp:2029 — it generates a call graph; analysis/app/src/syspart.cpp:2035 — it adds NSS edges; analysis/app/src/syspart.cpp:2036 — it extracts direct syscalls across graph nodes (analysis/app/src/syspart.cpp:284); analysis/app/src/syspart.cpp:2037 — it propagates derived syscalls through graph parents (analysis/app/src/syspart.cpp:408, analysis/app/src/syspart.cpp:435); analysis/app/src/syspart.cpp:2038 — it prints root details; analysis/app/src/syspart.cpp:2040 — only then does it scan program functions for the comparison name (analysis/app/src/syspart.cpp:66, analysis/app/src/syspart.cpp:69); analysis/app/src/syspart.cpp:2041 — a missing name returns before comparison output.
- Assessment: The caller checks that mode 3 has a comma, then passes the comparison name to run7 without checking whether it exists (analysis/app/src/testSyspart.cpp:223, analysis/app/src/testSyspart.cpp:232). A tiny test case is a program with `int main(void) { return 0; }`, analyzed with `-s main -a 3,__syspart_missing__`. If that name is absent from the loaded functions, the source predicts root syscall details when the root has a syscall node, followed by no `Filtered system calls` line and no missing-name diagnostic (analysis/app/src/syspart.cpp:676, analysis/app/src/syspart.cpp:684, analysis/app/src/syspart.cpp:2040, analysis/app/src/syspart.cpp:2042, analysis/app/src/syspart.cpp:2061). This is a source-supported cost finding; no runtime output was captured.

### The SUMMARY total counts most syscalls twice

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:745`
- Invariant: The SUMMARY total should equal the size of the reported union including init and fini syscalls (analysis/app/src/syspart.cpp:741, analysis/app/src/syspart.cpp:749).
- Mechanism: getSyscallInfo increments ntotal while printing the union with fini syscalls, then increments it again for every member of the expanded union with init syscalls (analysis/app/src/syspart.cpp:724, analysis/app/src/syspart.cpp:728, analysis/app/src/syspart.cpp:741, analysis/app/src/syspart.cpp:745). Mode 3 calls this method for both compared functions (analysis/app/src/syspart.cpp:2038, analysis/app/src/syspart.cpp:2043).
- Reproducer: Source-bounded case: a function has one direct syscall and the init and fini sets are empty. The two printing loops each increment ntotal once, so SUMMARY reports 2 for a one-element union (analysis/app/src/syspart.cpp:688, analysis/app/src/syspart.cpp:724, analysis/app/src/syspart.cpp:728, analysis/app/src/syspart.cpp:741, analysis/app/src/syspart.cpp:745).
- Expected: For the proposed one-syscall case: `SUMMARY f M 1 0 1` (analysis/app/src/syspart.cpp:741, analysis/app/src/syspart.cpp:749).
- Actual: The source computes `SUMMARY f M 1 0 2` for that case; no runtime output was observed (analysis/app/src/syspart.cpp:728, analysis/app/src/syspart.cpp:745, analysis/app/src/syspart.cpp:749).
- Evidence: analysis/app/src/testSyspart.cpp:223 — mode 3 dispatches to run7 at analysis/app/src/testSyspart.cpp:232; analysis/app/src/syspart.cpp:2038 — run7 calls getSyscallInfo for the start function, then for a found comparison function at analysis/app/src/syspart.cpp:2040 and analysis/app/src/syspart.cpp:2043; analysis/app/src/syspart.cpp:678 — getSyscallInfo returns if no SysNode exists; analysis/app/src/syspart.cpp:690 — direct syscalls enter f_syscalls; analysis/app/src/syspart.cpp:720 — fini syscalls enter that set; analysis/app/src/syspart.cpp:725 — the first loop visits the set and increments ntotal at analysis/app/src/syspart.cpp:728; analysis/app/src/syspart.cpp:737 — init syscalls enter the same set; analysis/app/src/syspart.cpp:742 — the second loop visits the expanded set and increments ntotal again at analysis/app/src/syspart.cpp:745; analysis/app/src/syspart.cpp:749 — SUMMARY prints ntotal.
- Assessment: The null-node guard can suppress a SUMMARY, and mode 3 returns before the second function if its name is not found; neither guard changes the count when getSyscallInfo runs (analysis/app/src/syspart.cpp:678, analysis/app/src/syspart.cpp:679, analysis/app/src/syspart.cpp:2040, analysis/app/src/syspart.cpp:2043). Tiny test case: a mapped function f in module M with one direct syscall, no derived syscalls, and empty init and fini sets. Expected output includes `Total syscalls of f including fini and init section(1)` and `SUMMARY f M 1 0 1`; the source instead computes `SUMMARY f M 1 0 2` (analysis/app/src/syspart.cpp:681, analysis/app/src/syspart.cpp:690, analysis/app/src/syspart.cpp:724, analysis/app/src/syspart.cpp:728, analysis/app/src/syspart.cpp:741, analysis/app/src/syspart.cpp:745, analysis/app/src/syspart.cpp:749). This is source-supported, with no runtime output observed.
- Command: `awk 'NR>=620 && NR<=755 {printf "%d:%s\n", NR, $0}' analysis/app/src/syspart.cpp`

### A duplicate comparison name can select another module's function

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:75`
- Invariant: The comparison name must identify the function whose syscalls mode 3 subtracts from the start function's set (analysis/app/src/testSyspart.cpp:231, analysis/app/src/syspart.cpp:2040, analysis/app/src/syspart.cpp:2060).
- Mechanism: findFunctionByName retains a match from each module and returns the last module's match without checking ambiguity. run7 uses that result for the second syscall set (analysis/app/src/syspart.cpp:69, analysis/app/src/syspart.cpp:75, analysis/app/src/syspart.cpp:2040, analysis/app/src/syspart.cpp:2058).
- Reproducer: Source-bounded graph: the root reaches A::foo and B::foo in separate modules, with distinct syscall sets, and B is visited last by the name lookup. Request -a 3,foo; the lookup selects B::foo (analysis/app/src/syspart.cpp:69, analysis/app/src/syspart.cpp:75, analysis/app/src/syspart.cpp:2040).
- Expected: An ambiguous foo is reported before attributing a syscall difference (analysis/app/src/syspart.cpp:42–43, analysis/app/src/syspart.cpp:2040–2061).
- Actual: For the stated module order and reachable graph, the source selects B::foo and subtracts its syscall set; this is a source-supported prediction, not observed output (analysis/app/src/syspart.cpp:69–80, analysis/app/src/syspart.cpp:2052–2064).
- Evidence: analysis/app/src/testSyspart.cpp:223–232 — mode 3 passes the comparison name to run7. analysis/app/src/syspart.cpp:69–80 — each module can replace the match; the outer loop continues and returns the last match. analysis/app/src/syspart.cpp:2040–2058 — run7 checks for a missing function and missing graph or syscall entries, but does not check ambiguity; it obtains the selected function's syscall set. analysis/app/src/ipcallgraph.h:355–371 — graph lookup uses function identity, with a same-module fallback, so it does not resolve cross-module name ambiguity. analysis/app/src/syspart.cpp:2060–2064 — run7 subtracts that set and prints the result. analysis/app/src/syspart.cpp:2024–2040 — graph generation and syscall analysis also precede the ambiguous name lookup, making such a request incur avoidable analysis cost.
- Assessment: Tiny source-bounded test: let root reach A::foo with syscall read and B::foo with syscall write, and have the lookup visit B last. For -a 3,foo, the expected behavior is an ambiguity error with no attributed difference. The source instead selects B::foo and, if these are the only syscalls, predicts "Filtered system calls : read" and "Total system calls of function : 1" (analysis/app/src/syspart.cpp:69–80, analysis/app/src/syspart.cpp:2052–2064). No runtime output was observed.

### A resolved syscall number can exceed the fixed bitset

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:303`
- Invariant: Every index used for the 600-bit syscall summary must be below 600 (analysis/app/src/syspart.cpp:295, analysis/app/src/syspart.cpp:303).
- Mechanism: FindSyscalls records constant register values as unsigned long syscall numbers. Mode 3 scans every graph node and writes each value into the fixed bitset without a range check (analysis/tools/egalito/src/pass/findsyscalls.cpp:40, analysis/tools/egalito/src/pass/findsyscalls.cpp:45, analysis/app/src/syspart.cpp:2036, analysis/app/src/syspart.cpp:284, analysis/app/src/syspart.cpp:303).
- Reproducer: Source-bounded case: a scanned function loads 600 into RAX before a syscall instruction. If FindSyscalls resolves that constant, findDirectSyscalls indexes bit 600 of bitset<600> (analysis/tools/egalito/src/pass/findsyscalls.cpp:40, analysis/tools/egalito/src/pass/findsyscalls.cpp:45, analysis/app/src/syspart.cpp:295, analysis/app/src/syspart.cpp:303).
- Expected: Values of 600 or greater are rejected or handled before indexing the 600-bit summary (analysis/app/src/syspart.cpp:295, analysis/app/src/syspart.cpp:303).
- Actual: For a resolved value of 600, the source evaluates `bs[600]`, outside the valid indices 0–599; the runtime outcome was not observed (analysis/app/src/syspart.cpp:295, analysis/app/src/syspart.cpp:303).
- Evidence: analysis/app/src/testSyspart.cpp:77 — `-a` selects the analysis option; analysis/app/src/testSyspart.cpp:223 — option 3 dispatches to `run7`; analysis/app/src/syspart.cpp:2029 — `run7` builds the call graph; analysis/app/src/syspart.cpp:2036 — it calls `findDirectSyscalls`; analysis/app/src/syspart.cpp:284 — that function scans graph nodes; analysis/app/src/syspart.cpp:291 — each function is passed to `FindSyscalls`; analysis/tools/egalito/src/pass/findsyscalls.cpp:40 — a `syscall` instruction triggers RAX resolution; analysis/tools/egalito/src/pass/findsyscalls.cpp:139 — a constant is inserted into the value set; analysis/tools/egalito/src/pass/findsyscalls.cpp:45 — the set is recorded; analysis/app/src/syspart.cpp:292 — the recorded map is retrieved; analysis/app/src/syspart.cpp:295 — the summary has 600 bits; analysis/app/src/syspart.cpp:303 — each recorded value indexes it without a range check.
- Assessment: A tiny source-bounded test is a reachable function containing `mov $600, %eax` immediately before `syscall`. If the resolver records 600, the expected output from a range-safe analyzer is an out-of-range syscall diagnostic for 600, with no bitset write. The resolver inserts constant register values without a range check, and the summary writes each value into a 600-bit bitset without one (analysis/tools/egalito/src/pass/findsyscalls.cpp:139, analysis/app/src/syspart.cpp:295, analysis/app/src/syspart.cpp:303). No binary was run, so this is code-supported only.

### Direct syscall extraction retains per-function analysis allocations

- Status: **supported**
- Kind: performance
- Location: `analysis/tools/egalito/src/pass/findsyscalls.cpp:28`
- Invariant: Temporary CFG and dataflow objects should be released after a function's syscall scan finishes (analysis/tools/egalito/src/pass/findsyscalls.cpp:21, analysis/tools/egalito/src/pass/findsyscalls.cpp:99).
- Mechanism: For a nonempty CFG, FindSyscalls allocates a CFG, configuration, working set, and UseDef object, then reaches the end of visit without deleting them. Only the empty-CFG branch deletes its CFG (analysis/tools/egalito/src/pass/findsyscalls.cpp:21, analysis/tools/egalito/src/pass/findsyscalls.cpp:25, analysis/tools/egalito/src/pass/findsyscalls.cpp:28, analysis/tools/egalito/src/pass/findsyscalls.cpp:30, analysis/tools/egalito/src/pass/findsyscalls.cpp:99). Mode 3 invokes this pass for every call graph node (analysis/app/src/syspart.cpp:2036, analysis/app/src/syspart.cpp:284, analysis/app/src/syspart.cpp:291).
- Reproducer: Bounded cost: with N graph nodes whose CFGs are nonempty, mode 3 makes N allocations of each object type through this path and has no release in visit; memory use was not measured (analysis/app/src/syspart.cpp:284, analysis/app/src/syspart.cpp:291, analysis/tools/egalito/src/pass/findsyscalls.cpp:21, analysis/tools/egalito/src/pass/findsyscalls.cpp:28, analysis/tools/egalito/src/pass/findsyscalls.cpp:30, analysis/tools/egalito/src/pass/findsyscalls.cpp:99).
- Expected: Completed nonempty-CFG scans release their temporary CFG and dataflow objects (analysis/tools/egalito/src/pass/findsyscalls.cpp:21, analysis/tools/egalito/src/pass/findsyscalls.cpp:30).
- Actual: The nonempty-CFG path has no release before visit returns, so those allocations remain live across successive node scans; this is a source trace, not a measured runtime result (analysis/tools/egalito/src/pass/findsyscalls.cpp:28, analysis/tools/egalito/src/pass/findsyscalls.cpp:103, analysis/app/src/syspart.cpp:284).
- Evidence: analysis/app/src/testSyspart.cpp:232 — option 3 calls run7; analysis/app/src/syspart.cpp:2036 — run7 calls findDirectSyscalls; analysis/app/src/syspart.cpp:284 — it loops over call-graph nodes; analysis/app/src/syspart.cpp:291 — each function accepts a fresh FindSyscalls visitor; analysis/tools/egalito/src/pass/findsyscalls.cpp:19 — libc syscall functions return before allocation; analysis/tools/egalito/src/pass/findsyscalls.cpp:21 — CFG allocated; analysis/tools/egalito/src/pass/findsyscalls.cpp:22 — empty CFG guarded; analysis/tools/egalito/src/pass/findsyscalls.cpp:25 — that branch deletes its CFG; analysis/tools/egalito/src/pass/findsyscalls.cpp:28 — nonempty path allocates configuration, working set, and UseDef; analysis/tools/egalito/src/pass/findsyscalls.cpp:99 — scan ends without deleting them; analysis/tools/egalito/src/pass/findsyscalls.cpp:103 — visit returns.
- Assessment: The allocation retention is supported by the source, with a scope correction: bare `-a 3` stops with `Args(func_name) required`; `-a 3,main` reaches the scan (analysis/app/src/testSyspart.cpp:223, analysis/app/src/testSyspart.cpp:232). Tiny proposed test: scan a one-block `main` containing a syscall instruction and track the four temporary object types. Expected test output after `visit` is `live temporary objects: 0`; the source predicts `live temporary objects: 4` (analysis/tools/egalito/src/pass/findsyscalls.cpp:21, analysis/tools/egalito/src/pass/findsyscalls.cpp:30, analysis/tools/egalito/src/pass/findsyscalls.cpp:103). No runtime output was captured.

<!-- harness:logic:mode-3:end -->

<!-- harness:logic:mode-4:start -->
## Harness logic audit — mode 4

Dispatcher and modules: README.md, analysis/app/README.md, analysis/app/src/testSyspart.cpp, analysis/app/src/syspart.cpp, analysis/app/src/ipcallgraph.cpp, analysis/app/src/ipcallgraph.h

### Mode 4 counts sites but prints source-target pairs

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:1955`
- Invariant: The final count should equal the number of printed source instruction and target function pairs (analysis/app/src/syspart.cpp:1954-1962).
- Mechanism: The AT map stores a set of targets per instruction (analysis/app/src/ipcallgraph.h:148-152). run5 increments count once per instruction, then prints one row per target (analysis/app/src/syspart.cpp:1953-1962).
- Reproducer: Source-bounded case: one instruction references a data object containing pointers to two functions; data parsing adds both targets at that instruction address (analysis/app/src/ipcallgraph.cpp:1615-1643). No workload was run.
- Expected: Two source-target rows and '#GLOBAL AT LIST : 2' for the proposed case (analysis/app/src/syspart.cpp:1950-1966).
- Actual: Source-predicted: two rows and '#GLOBAL AT LIST : 1'; this is not runtime-confirmed (analysis/app/src/syspart.cpp:1955-1966).
- Evidence: analysis/app/src/testSyspart.cpp:235-237 — -a 4 calls run5; analysis/app/src/syspart.cpp:1940-1943 — run5 generates the graph; analysis/app/src/ipcallgraph.cpp:1766-1790 — generation calls findATList; analysis/app/src/ipcallgraph.cpp:1407-1442 — eligible linked DATA references reach parseData; analysis/app/src/ipcallgraph.cpp:1621-1633 — each function pointer in the global adds a target using the same instruction address; analysis/app/src/ipcallgraph.cpp:250-274 — targets enter the source node; analysis/app/src/ipcallgraph.h:118,148-151 — each instruction maps to a set of targets; analysis/app/src/syspart.cpp:1955-1966 — count increments once per instruction while a row prints per target.
- Assessment: A tiny source-bounded test case is one linked instruction at 0x1000 in function src that refers to a DATA global containing pointers to distinct functions f1 and f2. If the module has symbols and the instruction passes the write-to-data guard, parsing adds both targets at 0x1000 (analysis/app/src/ipcallgraph.cpp:1407-1442, analysis/app/src/ipcallgraph.cpp:1599-1633). Expected output is two source-target rows, one for src/0x1000/f1 and one for src/0x1000/f2, followed by '#GLOBAL AT LIST : 2'. The source instead predicts those two rows followed by '#GLOBAL AT LIST : 1' (analysis/app/src/syspart.cpp:1955-1966). No workload was run.

### Mode 4 builds unused indirect-call edges

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspart.cpp:1942`
- Invariant: Producing the AT-site rows requires the AT sets populated during findATList, without indirect-edge construction (analysis/app/src/ipcallgraph.cpp:1783-1790; analysis/app/src/syspart.cpp:1950-1962).
- Mechanism: Without -g, run5 calls generate, which continues after AT discovery into indirect resolution and edge generation (analysis/app/src/syspart.cpp:1939-1943; analysis/app/src/ipcallgraph.cpp:1792-1838). For unresolved sites without TypeArmor, edge generation attaches the global AT target set and records a parent for every target; run5 subsequently reads only AT lists (analysis/app/src/ipcallgraph.cpp:709-715; analysis/app/src/syspart.cpp:1950-1962).
- Reproducer: Bounded cost: with I unresolved indirect sites and A global AT targets, the fallback performs I×A target and parent insertions for data absent from mode 4's rows (analysis/app/src/ipcallgraph.cpp:709-715; analysis/app/src/syspart.cpp:1950-1962). No workload was run.
- Expected: Mode 4 could stop after AT discovery, as the -g generation path does (analysis/app/src/ipcallgraph.cpp:1742-1764; analysis/app/src/syspart.cpp:1950-1966).
- Actual: The default mode 4 path reaches indirect-edge generation before printing AT-site rows (analysis/app/src/syspart.cpp:1940-1966; analysis/app/src/ipcallgraph.cpp:1819-1838).
- Evidence: analysis/app/src/testSyspart.cpp:235-238 — mode 4 calls run5; analysis/app/src/syspart.cpp:1940-1943 — run5 calls generate without -g; analysis/app/src/ipcallgraph.cpp:1786-1790 — generate populates AT lists; analysis/app/src/ipcallgraph.cpp:1796-1838 — it then performs optional resolution and generates indirect edges; analysis/app/src/ipcallgraph.cpp:709-718 — the no-TypeArmor fallback attaches all AT targets and parent records; analysis/app/src/syspart.cpp:1950-1966 — run5 prints AT lists and their count.
- Assessment: A tiny fixture with one function whose address is taken at one instruction and one unresolved indirect call should produce the same AT-site row and `#GLOBAL AT LIST : 1` with `-a 4` and `-a 4 -g`; the row printer reads AT lists, while `-g` selects the path that stops after AT discovery (analysis/app/src/syspart.cpp:1950-1966; analysis/app/src/testSyspart.cpp:74-75; analysis/app/src/ipcallgraph.cpp:1742-1764). Without `-g` or TypeArmor, each unresolved site receives the global AT target set and records a parent for every target, so I such sites and A targets imply I×A parent writes and target-set construction absent from those rows (analysis/app/src/ipcallgraph.cpp:48-60; analysis/app/src/ipcallgraph.cpp:709-718; analysis/app/src/ipcallgraph.cpp:121-125). No runtime cost was measured.

### Mode 4 adds NSS call edges after AT discovery

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspart.cpp:1947`
- Invariant: Mode 4's rows come from each node's AT list; adding call edges after graph generation does not add AT entries (analysis/app/src/syspart.cpp:1940-1962; analysis/app/src/ipcallgraph.cpp:1955-1976).
- Mechanism: run5 calls addNssEdges after generation. That method traverses NSS records, parent callsites and resolved functions, then calls addEdge, which updates call edges and parent records; run5 subsequently reads AT lists (analysis/app/src/syspart.cpp:1940-1959; analysis/app/src/ipcallgraph.cpp:1955-1979; analysis/app/src/ipcallgraph.cpp:224-247).
- Reproducer: Bounded cost: for N NSS records with P parent callsites and F resolved functions each, the nested loops can perform N×P×F edge additions without adding a mode 4 row. No workload was run (analysis/app/src/ipcallgraph.cpp:1957-1976; analysis/app/src/syspart.cpp:1951-1962).
- Expected: Print the AT lists populated during generation (analysis/app/src/ipcallgraph.cpp:1753-1762,1781-1791; analysis/app/src/syspart.cpp:1951-1966).
- Actual: When the NSS guards pass, the source predicts work proportional to parent callsites times resolved functions per record, without adding an AT row (analysis/app/src/ipcallgraph.cpp:1963-1979,224-247; analysis/app/src/syspart.cpp:1951-1966). Runtime cost was not measured.
- Evidence: analysis/app/src/testSyspart.cpp:235-238 — mode 4 calls run5; analysis/app/src/syspart.cpp:1940-1954 — run5 generates the graph, calls addNssEdges, then reads node AT lists; analysis/app/src/ipcallgraph.cpp:1955-1985 — missing NSS functions or nodes skip edge addition, but surviving records iterate parent callsites and resolved functions; analysis/app/src/ipcallgraph.cpp:224-247 — each addEdge call updates call targets and parent records, with no AT insertion; analysis/app/src/ipcallgraph.cpp:1742-1762,1766-1791 — both generation paths populate AT lists before addNssEdges; analysis/app/src/syspart.cpp:1955-1966 — rows and count come from AT lists.
- Assessment: Tiny test case: give run5 one NSS record with one parent callsite and one resolved function, and no AT entries. The AT output should contain its header and `#GLOBAL AT LIST : 0`; adding the NSS edge cannot create an AT entry because addEdge updates call targets and parents, while AT entries use addATFunction (analysis/app/src/syspart.cpp:1949-1966; analysis/app/src/ipcallgraph.cpp:224-274). This is a source-supported cost finding; no workload was run.

### Mode 4 copies AT target sets twice while printing

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspart.cpp:1955`
- Invariant: Printing each AT entry requires iterating its stored target set, without copying that set (analysis/app/src/ipcallgraph.h:148; analysis/app/src/syspart.cpp:1955-1962).
- Mechanism: getATList returns the entire map by value, and run5's by-value site loop copies each map entry, including its target set, again before printing (analysis/app/src/ipcallgraph.cpp:151-153; analysis/app/src/syspart.cpp:1954-1959).
- Reproducer: Bounded cost: a node with S sites containing P total targets incurs a copy of all S map entries and P target pointers on return, followed by copies of the site target sets during iteration. No workload was run (analysis/app/src/ipcallgraph.cpp:151-153; analysis/app/src/syspart.cpp:1954-1959).
- Expected: Iterating the stored AT entries by reference would produce the same rows without copying the map or each target set (analysis/app/src/ipcallgraph.h:118; analysis/app/src/syspart.cpp:1954-1962).
- Actual: The source implies one map copy, including its target sets, followed by another target-set copy for each site during printing; runtime cost was not measured (analysis/app/src/ipcallgraph.cpp:151-153; analysis/app/src/syspart.cpp:1954-1959).
- Evidence: analysis/app/src/ipcallgraph.h:118,148-152 — AT sites store sets of target pointers; analysis/app/src/ipcallgraph.h:205 and analysis/app/src/ipcallgraph.cpp:151-153 — getATList returns the whole map by value; analysis/app/src/syspart.cpp:1952-1962 — run5 calls the getter for each node, then copies each map entry with `auto at` before iterating its target set.
- Assessment: No guard refutes the candidate: mode 4 calls run5, and both call graph generation branches build AT lists before printing (analysis/app/src/testSyspart.cpp:234-239; analysis/app/src/syspart.cpp:1939-1944; analysis/app/src/ipcallgraph.cpp:1742-1790). Tiny proposed test: one source node with one AT site containing two targets. The print loop should emit the header, two target rows, then `#GLOBAL AT LIST : 1`; the count is per site (analysis/app/src/syspart.cpp:1949-1964). This test was not run.

<!-- harness:logic:mode-4:end -->

<!-- harness:logic:mode-5:start -->
## Harness logic audit — mode 5

Dispatcher and modules: README.md, analysis/app/README.md, analysis/app/src/testSyspart.cpp, analysis/app/src/syspart.cpp, analysis/app/src/ipcallgraph.h, analysis/app/src/ipcallgraph.cpp, analysis/app/src/syspartUtility.cpp

### Mode 5 ignores the supplied TypeArmor file

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:2731`
- Invariant: With -t, graph generation must use the path supplied to the CLI (analysis/app/src/testSyspart.cpp:64; analysis/app/src/ipcallgraph.cpp:532).
- Mechanism: The CLI stores the path in Syspart, but printAICT enables TypeArmor without passing that path to IPCallGraph. Generation then attempts to parse its default empty path; failure to open the file is silent (analysis/app/src/testSyspart.cpp:184; analysis/app/src/syspart.cpp:2731; analysis/app/src/ipcallgraph.cpp:1815; analysis/app/src/ipcallgraph.cpp:532).
- Reproducer: Supply -a 5 -t with a valid file containing an icallargs record that would filter a target. The graph receives no file path, so that record is unavailable (analysis/app/src/testSyspart.cpp:240; analysis/app/src/syspart.cpp:2731; analysis/app/src/ipcallgraph.cpp:532; analysis/app/src/ipcallgraph.cpp:821).
- Expected: For the proposed one-call, two-target fixture, #AVERAGE INDIRECT CALL TARGET : 1 (analysis/app/src/ipcallgraph.cpp:854; analysis/app/src/syspart.cpp:2760).
- Actual: The source predicts #AVERAGE INDIRECT CALL TARGET : 2 for that fixture; no runtime output was observed (analysis/app/src/ipcallgraph.cpp:827; analysis/app/src/syspart.cpp:2760).
- Evidence: analysis/app/src/testSyspart.cpp:64 — -t records the path; analysis/app/src/testSyspart.cpp:184 — the path is set only on Syspart; analysis/app/src/testSyspart.cpp:242 — mode 5 calls printAICT; analysis/app/src/syspart.cpp:2731 — printAICT sets the flag but not the graph's path before generate; analysis/app/src/ipcallgraph.h:291 — the graph has its own path string; analysis/app/src/ipcallgraph.h:389 — it has a separate path setter; analysis/app/src/ipcallgraph.cpp:1815 — generation calls parseTypeArmor; analysis/app/src/ipcallgraph.cpp:532 — parsing opens the graph's path and skips records when opening fails; analysis/app/src/ipcallgraph.cpp:824 — absent callsite metadata retains the full address-taken target set; analysis/app/src/syspart.cpp:2760 — mode 5 reports the resulting average.
- Assessment: No guard or caller on the mode 5 path supplies the TypeArmor path to IPCallGraph: the CLI stores it in Syspart, then dispatches directly to printAICT (analysis/app/src/testSyspart.cpp:184; analysis/app/src/testSyspart.cpp:240), which enables TypeArmor and generates the graph without calling setTypeArmorPath (analysis/app/src/syspart.cpp:2725). A tiny proposed test uses one indirect call, exactly two address-taken targets with 0 and 1 arguments, and a TypeArmor file with an icallargs record specifying 0 arguments plus fnargs records for both targets (analysis/app/src/ipcallgraph.cpp:578; analysis/app/src/ipcallgraph.cpp:595; analysis/app/src/ipcallgraph.cpp:602). Run mode 5 with -t and without -i; the expected average is 1, while the source path implies 2 because missing callsite metadata retains both targets (analysis/app/src/ipcallgraph.cpp:692; analysis/app/src/ipcallgraph.cpp:824; analysis/app/src/ipcallgraph.cpp:846; analysis/app/src/ipcallgraph.cpp:854; analysis/app/src/syspart.cpp:2760). This is a source-supported prediction, not observed output.

### Empty site counts cause division by zero

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:2760`
- Invariant: Each denominator must be positive before its average is computed (analysis/app/src/syspart.cpp:2759; analysis/app/src/syspart.cpp:2763).
- Mechanism: The tally initializes both counts to zero, increments them only for stored indirect sites, and divides without checking either count (analysis/app/src/syspart.cpp:2737; analysis/app/src/syspart.cpp:2746; analysis/app/src/syspart.cpp:2760; analysis/app/src/syspart.cpp:2763).
- Reproducer: A graph with no indirect sites leaves n at zero; a graph with an indirect site only in a library leaves napp at zero (analysis/app/src/syspart.cpp:2743; analysis/app/src/syspart.cpp:2746; analysis/app/src/syspart.cpp:2750).
- Expected: An empty group should have a defined or unavailable average (analysis/app/src/syspart.cpp:2759; analysis/app/src/syspart.cpp:2762).
- Actual: The source evaluates integer division by zero when either count remains zero; no runtime outcome was observed (analysis/app/src/syspart.cpp:2737; analysis/app/src/syspart.cpp:2738; analysis/app/src/syspart.cpp:2760; analysis/app/src/syspart.cpp:2763).
- Evidence: analysis/app/src/testSyspart.cpp:240 — mode 5 calls printAICT directly; analysis/app/src/syspart.cpp:2732 — it generates the graph; analysis/app/src/ipcallgraph.cpp:688 — indirect edges are generated only for recorded indirect sites; analysis/app/src/syspart.cpp:2737 — both counts start at zero; analysis/app/src/syspart.cpp:2746 — counts increase only for stored indirect children; analysis/app/src/syspart.cpp:2750 — the application count additionally requires the executable module; analysis/app/src/syspart.cpp:2760 — sum/n has no guard; analysis/app/src/syspart.cpp:2763 — sumapp/napp has no guard.
- Assessment: A tiny test case is an executable whose root function has no calls, linked without shared libraries, analyzed with -a 5. Expected output after handling empty groups: '#INDIRECT CALLS : 0', '#AVERAGE INDIRECT CALL TARGET : N/A', '#APP INDIRECT CALLS : 0', and '#APP AVERAGE INDIRECT CALL TARGET : N/A' (analysis/app/src/syspart.cpp:2759; analysis/app/src/syspart.cpp:2760; analysis/app/src/syspart.cpp:2762; analysis/app/src/syspart.cpp:2763). No binary was run, so the finding is source-supported only.

### Target averages are truncated to integers

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:2760`
- Invariant: An average should retain the fractional part of targets per site (README.md:153; analysis/app/src/syspart.cpp:2748).
- Mechanism: The sums and counts are int, so both divisions use integer arithmetic (analysis/app/src/syspart.cpp:2736; analysis/app/src/syspart.cpp:2739; analysis/app/src/syspart.cpp:2760; analysis/app/src/syspart.cpp:2763).
- Reproducer: Two sites with one and two targets yield sum=3 and n=2 in the tally (analysis/app/src/syspart.cpp:2746; analysis/app/src/syspart.cpp:2748).
- Expected: For the proposed two-site test: both average lines print 1.5 (analysis/app/src/syspart.cpp:2748; analysis/app/src/syspart.cpp:2752; README.md:153).
- Actual: Source arithmetic predicts both average lines print 1; this is not observed program output (analysis/app/src/syspart.cpp:2736; analysis/app/src/syspart.cpp:2739; analysis/app/src/syspart.cpp:2760; analysis/app/src/syspart.cpp:2763).
- Evidence: analysis/app/src/testSyspart.cpp:240 — mode 5 dispatches to printAICT at analysis/app/src/testSyspart.cpp:242; analysis/app/src/syspart.cpp:2736 — sum and n are int; analysis/app/src/syspart.cpp:2738 — napp and sumapp are int; analysis/app/src/syspart.cpp:2743 — getIndirectChildren supplies call-site entries; analysis/app/src/syspart.cpp:2748 — each entry adds its target count and increments n; analysis/app/src/syspart.cpp:2750 — executable-module entries also update the application tally; analysis/app/src/syspart.cpp:2760 — sum/n uses integer division; analysis/app/src/syspart.cpp:2763 — sumapp/napp does likewise.
- Assessment: A tiny test case is an executable-module node with two indirect call sites whose target sets have sizes 1 and 2. The tally gives sum=3, n=2, sumapp=3, and napp=2 (analysis/app/src/syspart.cpp:2740; analysis/app/src/syspart.cpp:2746; analysis/app/src/syspart.cpp:2748; analysis/app/src/syspart.cpp:2753). Expected output includes `#AVERAGE INDIRECT CALL TARGET : 1.5` and `#APP AVERAGE INDIRECT CALL TARGET : 1.5`, consistent with the documented average metric (README.md:153). No guard in the output path preserves the fraction (analysis/app/src/syspart.cpp:2759; analysis/app/src/syspart.cpp:2763).

### Indirect-edge generation copies all targets for every graph node

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/ipcallgraph.cpp:666`
- Invariant: A node with no indirect sites needs no copy of the global target set (analysis/app/src/ipcallgraph.cpp:664; analysis/app/src/ipcallgraph.cpp:690).
- Mechanism: Generation calls generateIndirectEdges for every node, which copies allAT before inspecting that node's instructions or sites (analysis/app/src/ipcallgraph.cpp:1834; analysis/app/src/ipcallgraph.cpp:1835; analysis/app/src/ipcallgraph.cpp:665; analysis/app/src/ipcallgraph.cpp:666).
- Reproducer: For V graph nodes and A address-taken targets, including nodes with no indirect sites, the set copies require O(V×A) element-copy work (analysis/app/src/ipcallgraph.cpp:1834; analysis/app/src/ipcallgraph.cpp:666; analysis/app/src/ipcallgraph.cpp:690).
- Expected: A node with no indirect sites would avoid copying allAT (analysis/app/src/ipcallgraph.cpp:665; analysis/app/src/ipcallgraph.cpp:688).
- Actual: The source initializes a separate set from allAT for every visited node before checking its sites, implying O(V×A) set-copy work for V nodes and A targets; no runtime cost was observed (analysis/app/src/ipcallgraph.cpp:1835; analysis/app/src/ipcallgraph.cpp:666; analysis/app/src/ipcallgraph.h:338).
- Evidence: analysis/app/src/testSyspart.cpp:77 — -a selects the option; analysis/app/src/testSyspart.cpp:240 — option 5 calls printAICT; analysis/app/src/syspart.cpp:2732 — printAICT calls generate; analysis/app/src/ipcallgraph.cpp:1820 — generate populates allAT; analysis/app/src/ipcallgraph.cpp:1835 — generate calls generateIndirectEdges for every nodeMap entry; analysis/app/src/ipcallgraph.cpp:665 — the callee obtains that node's indirect sites; analysis/app/src/ipcallgraph.cpp:666 — it copies allAT without a guard; analysis/app/src/ipcallgraph.cpp:688 — the site check occurs later; analysis/app/src/ipcallgraph.h:338 — allAT is a set of node pointers.
- Assessment: Tiny proposed test: use a graph fixture with two nodes, one with no indirect sites and one with one unresolved indirect site, and one target in allAT. A copy counter at the set initialization should output "copies=2; empty-node copies=1" because generation visits every node and copies allAT before checking sites (analysis/app/src/ipcallgraph.cpp:1832; analysis/app/src/ipcallgraph.cpp:1835; analysis/app/src/ipcallgraph.cpp:665; analysis/app/src/ipcallgraph.cpp:666; analysis/app/src/ipcallgraph.cpp:688). This is a source-supported cost; it was not measured.

### Resolved sites repeatedly copy and scan the same target map

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/ipcallgraph.cpp:695`
- Invariant: Counting targets for one resolved site should require access to that site's entry (analysis/app/src/ipcallgraph.cpp:693-704).
- Mechanism: With -i, each resolved site copies its function's entire indirect-children map and scans every entry to find the current address; the second indirect-site branch repeats the pattern (analysis/app/src/ipcallgraph.cpp:695-704; analysis/app/src/ipcallgraph.cpp:724-735; analysis/app/src/ipcallgraph.h:211-213).
- Reproducer: For one function with S resolved indirect sites and S stored map entries, the site loop performs S map copies and S full scans: O(S²) entry work (analysis/app/src/ipcallgraph.cpp:683-695; analysis/app/src/ipcallgraph.cpp:695-704). This is a source bound; no workload was run.
- Expected: Count a resolved site's targets through its address entry, without copying and scanning every entry (analysis/app/src/ipcallgraph.cpp:693-704; analysis/app/src/ipcallgraph.h:211-213).
- Actual: For S resolved sites and S map entries in one function, the source entails S map copies and S full scans, or O(S²) map-entry work; this cost was not measured (analysis/app/src/ipcallgraph.cpp:685-704; analysis/app/src/ipcallgraph.h:211-213).
- Evidence: analysis/app/src/testSyspart.cpp:240-243 — mode 5 calls printAICT; analysis/app/src/syspart.cpp:2730-2732 — it sets the analysis flag and generates the graph; analysis/app/src/ipcallgraph.cpp:1796-1808 — generation resolves indirect targets when enabled; analysis/app/src/ipcallgraph.cpp:1835-1836 — generation then visits each node; analysis/app/src/ipcallgraph.cpp:685-695 — each resolved indirect-call site reaches getIndirectChildren; analysis/app/src/ipcallgraph.h:211-213 — that getter returns the map by value; analysis/app/src/ipcallgraph.cpp:696-704 — the copied map is scanned without breaking after the matching address; analysis/app/src/ipcallgraph.cpp:724-735 — the second site branch repeats the pattern.
- Assessment: The resolved-site guard is reachable: `-i` enables indirect-call analysis, which can populate a site's target map and mark it resolved before edge generation (analysis/app/src/testSyspart.cpp:68; analysis/app/src/ipcallgraph.cpp:1796; analysis/app/src/syspartUtility.cpp:1375; analysis/app/src/syspartUtility.cpp:1379; analysis/app/src/ipcallgraph.cpp:1835). For a tiny test case with two resolved indirect sites in one executable function, each with one target and no other indirect sites, mode 5 should print `#INDIRECT CALLS : 2` and `#AVERAGE INDIRECT CALL TARGET : 1` (analysis/app/src/syspart.cpp:2740; analysis/app/src/syspart.cpp:2746; analysis/app/src/syspart.cpp:2759; analysis/app/src/syspart.cpp:2760). This test was proposed, not run.

### The mode 5 tally copies data it only reads

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspart.cpp:2743`
- Invariant: The tally needs to iterate stored site entries and read the address-taken set's size (analysis/app/src/syspart.cpp:2743-2749; analysis/app/src/syspart.cpp:2761).
- Mechanism: getIndirectChildren returns its map by value for every graph node, and getGlobalATList returns its set by value before size is read (analysis/app/src/ipcallgraph.h:211-213; analysis/app/src/ipcallgraph.h:408-411; analysis/app/src/syspart.cpp:2743; analysis/app/src/syspart.cpp:2761).
- Reproducer: For I stored indirect-site entries and A address-taken functions, reporting copies I map entries across nodes and A set entries solely to calculate the displayed values (analysis/app/src/syspart.cpp:2740-2761; analysis/app/src/ipcallgraph.h:211-213; analysis/app/src/ipcallgraph.h:408-411). No workload was run.
- Expected: Read the stored map entries and set size without container copies (analysis/app/src/syspart.cpp:2743-2749,2761).
- Actual: The source copies the indirect-site map for each graph node and the address-taken set once per report; the shared target vectors themselves are referenced through shared_ptr values (analysis/app/src/syspart.cpp:2740-2743,2761; analysis/app/src/ipcallgraph.h:45,211-213,408-410). Runtime cost was not measured.
- Evidence: analysis/app/src/testSyspart.cpp:240-243 — mode 5 calls printAICT directly. analysis/app/src/syspart.cpp:2727-2743 — it generates the graph, then calls getIndirectChildren for each node. analysis/app/src/ipcallgraph.h:115-116,211-213 — the getter returns the stored map by value. analysis/app/src/syspart.cpp:2746-2755 — the tally only reads its entries and target-list sizes. analysis/app/src/ipcallgraph.h:327,408-410; analysis/app/src/syspart.cpp:2761 — the address-taken set is returned by value solely for size().
- Assessment: A tiny test case would use one executable-module indirect site with two targets and three address-taken functions. The expected report is five lines: #INDIRECT CALLS : 1; #AVERAGE INDIRECT CALL TARGET : 2; GLOBAL AT LIST : 3; #APP INDIRECT CALLS : 1; #APP AVERAGE INDIRECT CALL TARGET : 2 (analysis/app/src/syspart.cpp:2746-2763). This is a proposed case, not observed output.

### Mode 5 loads a syscall-name map it never uses

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/testSyspart.cpp:167`
- Invariant: Printing indirect-call counts, averages, and the address-taken count does not require syscall names (analysis/app/src/syspart.cpp:2725-2763).
- Mechanism: Before dispatch, the driver calls populateSyscallMap, which reads and parses two syscall header files or builds a default map. Mode 5 then calls printAICT, whose graph and tally path does not read that map (analysis/app/src/testSyspart.cpp:167; analysis/app/src/testSyspart.cpp:240-243; analysis/app/src/syspart.cpp:131-157; analysis/app/src/syspart.cpp:2725-2763).
- Reproducer: Any -a 5 invocation reaches the header-reading call before dispatch; work scales with the lines read and map entries populated, while the mode 5 output uses graph data (analysis/app/src/testSyspart.cpp:167-186; analysis/app/src/testSyspart.cpp:240-243; analysis/app/src/syspart.cpp:131-157; analysis/app/src/syspart.cpp:2740-2763). This is a source trace, not a timing measurement.
- Expected: Mode 5 reports the five graph metrics without populating syscall names (analysis/app/src/syspart.cpp:2725-2763).
- Actual: The source calls populateSyscallMap before mode 5 dispatch, causing header parsing or default-map construction (analysis/app/src/testSyspart.cpp:167; analysis/app/src/testSyspart.cpp:240-243; analysis/app/src/syspart.cpp:131-157).
- Evidence: analysis/app/src/testSyspart.cpp:137-152 — required arguments are checked; analysis/app/src/testSyspart.cpp:167 — the driver unconditionally populates syscall names; analysis/app/src/syspart.cpp:113-157 — population parses two headers and uses a default map if empty; analysis/app/src/testSyspart.cpp:240-243 — mode 5 calls printAICT; analysis/app/src/syspart.cpp:2725-2763 — printAICT generates the call graph and prints metrics without accessing syscall names.
- Assessment: The argument checks run before analysis, but there is no mode-specific guard around populateSyscallMap; mode 5 dispatches to printAICT afterward (analysis/app/src/testSyspart.cpp:137-167; analysis/app/src/testSyspart.cpp:240-243). The map is a Syspart member, while printAICT generates graph data and prints counts without reading it (analysis/app/src/syspart.h:36-43; analysis/app/src/syspart.cpp:2725-2763). Tiny test case: analyze a small executable with one address-taken function called through a function pointer using -a 5, once with syscall headers available and once without them. The expected five metric lines should be identical between runs; the source shows header parsing or fallback-map construction is unnecessary for those lines (analysis/app/src/syspart.cpp:131-157; analysis/app/src/syspart.cpp:2759-2763). This is a source-supported cost finding, not a measured runtime result.

<!-- harness:logic:mode-5:end -->

<!-- harness:logic:mode-6:start -->
## Harness logic audit — mode 6

Dispatcher and modules: analysis/app/src/testSyspart.cpp, analysis/app/src/syspart.cpp, analysis/app/src/ipcallgraph.cpp, analysis/app/src/ipcallgraph.h, analysis/app/src/syspartUtility.cpp, analysis/app/src/syspartUtility.h

### A RIP-relative pointer load is printed as bytes at the pointer's address

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspartUtility.cpp:285`
- Invariant: A type-2 result represents a value stored at an address, so displaying it as a string requires reading that stored value (analysis/app/src/syspartUtility.h:13-16; analysis/app/src/syspartUtility.cpp:470-487).
- Mechanism: RIP-relative dereference tracing records the address as type 2, but the mode-6 printer treats every non-unknown result as a character string starting at that address (analysis/app/src/syspartUtility.cpp:470-487, 259-287).
- Reproducer: Source-bounded case: a caller loads an argument from a RIP-relative, read-only pointer slot and calls the requested function. The trace records the slot's address as type 2; if that address lies in .rodata, printing starts at the pointer bytes (analysis/app/src/syspartUtility.cpp:470-487, 277-287). No runtime output was tested.
- Expected: For the proposed test, report the stored pointer's target `OK` or leave the dereference unresolved (analysis/app/src/syspartUtility.h:13-16; analysis/app/src/syspartUtility.cpp:470-487).
- Actual: Source-predicted: if `slot` lies in .rodata, `SYM` is decoded from the pointer bytes at `slot`, not from `msg` (analysis/app/src/syspartUtility.cpp:277-287). No runtime output was observed.
- Evidence: analysis/app/src/testSyspart.cpp:245-273 — mode 6 calls getArgumentValue; analysis/app/src/syspart.cpp:2641-2644 — it creates a type-0 utility and traces the argument; analysis/app/src/syspartUtility.cpp:235-241 — the caller's register definition enters findRegDef; analysis/app/src/syspartUtility.cpp:645-655 — a RIP-relative dereference selects handleRIPDerefValue; analysis/app/src/syspartUtility.cpp:470-487 — that handler records the slot address as type 2; analysis/app/src/syspartUtility.cpp:259-287 — the printer interprets that address as the start of a character string.
- Assessment: The guards for unresolved calls, unknown results, and addresses outside .rodata limit when this occurs, but none distinguishes type 2 from a direct address (analysis/app/src/syspartUtility.cpp:199-201, 267-287). Tiny unrun test: an x86-64 caller executes `mov slot(%rip), %rdi; call sink`, with `slot: .quad msg` and `msg: .asciz "OK"` in .rodata. The expected symbol is `OK` or an unresolved dereference; the source predicts printing bytes beginning at `slot` (analysis/app/src/syspartUtility.h:13-16; analysis/app/src/syspartUtility.cpp:470-487, 285-287).

### The .rodata end address is accepted as a string start

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspartUtility.cpp:285`
- Invariant: A string start must be inside the section and its terminator must be readable within the section before streaming it (analysis/app/src/syspartUtility.cpp:278-287).
- Mechanism: The range test includes section_end, computed as base plus size, and streams a char pointer without checking for a NUL byte within the section (analysis/app/src/syspartUtility.cpp:280-287).
- Reproducer: Source-bounded case: a traced constant equals the end address of its module's .rodata. Constant tracing can produce that address, and the inclusive test accepts it (analysis/app/src/syspartUtility.cpp:735-750, 280-287). No runtime output was tested.
- Expected: Addresses at or beyond section_end are not decoded as .rodata strings (analysis/app/src/syspartUtility.cpp:280-287).
- Actual: The source predicts streaming from rodata + size when the traced address equals section_end; output or failure is unobserved (analysis/app/src/syspartUtility.cpp:282-287, analysis/tools/egalito/src/elf/elfmap.cpp:224-225).
- Evidence: analysis/app/src/testSyspart.cpp:245-273 — mode -a 6 calls getArgumentValue; analysis/app/src/syspart.cpp:2624-2644 — it creates SyspartUtility with analysisType 0 and traces arguments; analysis/app/src/syspartUtility.cpp:235-241 — register definitions feed collectedResults; analysis/app/src/syspartUtility.cpp:740-744 — a constant becomes a type 1 result; analysis/app/src/syspartUtility.cpp:259-287 — type 1 reaches the .rodata check, which accepts section_end and streams the pointer; analysis/tools/egalito/src/elf/elfmap.cpp:224-225 — conversion yields offset equal to section size at that address; analysis/tools/egalito/src/elf/elfmap.h:119-120 — the read pointer starts at the section read address.
- Assessment: The candidate holds for a traced constant equal to the end of .rodata: constant tracing preserves the address, and the string check accepts the inclusive end without checking for a NUL within the section (analysis/app/src/syspartUtility.cpp:740-744, analysis/app/src/syspartUtility.cpp:280-287). Tiny test case: use a module whose .rodata begins at 0x1000 and contains `A\0` (size 2), then trace a mode -a 6 argument with constant value 0x1002. Expected output: the result may show ADDRESS 1002, but must have no `SYM` string for that address; `END` should follow the results (analysis/app/src/syspartUtility.cpp:264-265, analysis/app/src/syspartUtility.cpp:280-291).

### Argument-result cache can retain values supplied by its caller

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspartUtility.cpp:117`
- Invariant: A cached function/register result must contain only values derived for that function/register pair (analysis/app/src/syspartUtility.cpp:104-117).
- Mechanism: Parent traversal passes its shared, accumulating result set into a recursive query for the caller. That query caches the entire supplied set, including values collected from earlier parent callsites; later cache hits return those values as the caller's results (analysis/app/src/syspartUtility.cpp:191-249, 104-117).
- Reproducer: Source-bounded case: two parent callsites of F are visited in address order. The first contributes A; the second forwards an argument through P. The recursive query for P starts with A and caches A even if P's own callers never supply it (analysis/app/src/syspartUtility.cpp:191-249, 115-117). No runtime output was tested.
- Expected: P's cached result and a subsequent query for P contain only B (analysis/app/src/syspartUtility.cpp:104-117,223-249).
- Actual: The source predicts P's cached result contains A and B, and a later cache hit returns both (analysis/app/src/syspartUtility.cpp:249,104-117). This is code-supported, not runtime-confirmed.
- Evidence: analysis/app/src/testSyspart.cpp:245-273 — mode -a 6 calls getArgumentValue; analysis/app/src/syspart.cpp:2641-2644 — it queries through SyspartUtility; analysis/app/src/ipcallgraph.h:187-190 — parent callsites are returned in an ordered map; analysis/app/src/syspartUtility.cpp:235-249 — an earlier callsite can add A to collectedResults before a later callsite passes that same set into the recursive query for P; analysis/app/src/syspartUtility.cpp:104-117 — P's cache entry copies the whole set, and a later hit inserts it into the result; analysis/app/src/syspartUtility.h:55-69 — cache identity uses function name, address, and register, not the supplied set.
- Assessment: The guards do not refute the candidate: a shallow, non-cyclic trace of a function outside the global AT list passes the depth, AT, and visited checks (analysis/app/src/syspartUtility.cpp:95-100,159-176). Tiny test: make F's lower-address callsite supply A and its next callsite forward an argument through P; make P's own caller supply only B. Query F, then P with the same SyspartUtility instance. A test that prints the second query's result should print only B, but the source predicts A and B (analysis/app/src/ipcallgraph.h:187-190; analysis/app/src/syspartUtility.cpp:191-249,104-117). No runtime output was captured.

### Each parent callsite rescans its entire caller function

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspartUtility.cpp:223`
- Invariant: Locating m recorded callsite addresses in a caller with I instructions should not require m full instruction scans (analysis/app/src/syspartUtility.cpp:191-225).
- Mechanism: For every parent record, mode 6 iterates every block and instruction until it finds the matching address; the loops continue through the function afterward (analysis/app/src/syspartUtility.cpp:191-225, 293-296).
- Reproducer: Bounded complexity case: one caller has I instructions and m calls to the requested function. Its m parent records cause Θ(mI) instruction visits just to locate known addresses (analysis/app/src/ipcallgraph.cpp:120-123; analysis/app/src/syspartUtility.cpp:188-225, 293-296). No timing was measured.
- Expected: For m recorded direct callsites in a caller containing I instructions, locating their addresses should take work proportional to I + m (analysis/app/src/ipcallgraph.cpp:121-124; analysis/app/src/syspartUtility.cpp:223-225).
- Actual: On the uncached path, the location loops visit the caller's I instructions for each of its m parent records, yielding Θ(mI) instruction visits before accounting for value tracing (analysis/app/src/syspartUtility.cpp:188-201; analysis/app/src/syspartUtility.cpp:223-296).
- Evidence: analysis/app/src/testSyspart.cpp:245-274 — mode 6 calls getArgumentValue; analysis/app/src/syspart.cpp:2624-2644 — it generates the call graph and requests argument values; analysis/app/src/ipcallgraph.cpp:891-895 — direct call addresses become edges; analysis/app/src/ipcallgraph.cpp:246-247 and analysis/app/src/ipcallgraph.cpp:121-124 — each edge records a parent callsite; analysis/app/src/syspartUtility.cpp:104-115 and analysis/app/src/syspartUtility.cpp:159-188 — cache and early guards can bypass the helper, but an uncached eligible target reaches its parent records; analysis/app/src/syspartUtility.cpp:191-201 — resolved direct records pass the per-parent guard; analysis/app/src/syspartUtility.cpp:223-296 — each record scans every instruction, with no break after an address match.
- Assessment: A tiny test would use one caller with two direct calls to target and request mode -a 6,target,7. Expected output is two FUNC target CALLINGFN caller CALLINGADDR lines with distinct addresses, each followed by END; the printing paths are at analysis/app/src/syspartUtility.cpp:228-230 and analysis/app/src/syspartUtility.cpp:259-291. The source establishes the repeated scans, but no binary was run or timing measured.

### Address-taken functions lose their known direct-call arguments

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspartUtility.cpp:161`
- Invariant: A known direct caller should remain available for argument tracing even when the callee's address is also taken (analysis/app/src/ipcallgraph.cpp:891-895; analysis/app/src/syspartUtility.cpp:188-249).
- Mechanism: Graph construction adds a direct parent edge, but argument tracing returns unknown for any function in the global address-taken list before inspecting its parents (analysis/app/src/ipcallgraph.cpp:893-895; analysis/app/src/ipcallgraph.cpp:1370-1378; analysis/app/src/syspartUtility.cpp:159-165).
- Reproducer: Source-bounded case: root calls callback directly with a constant argument and also takes callback's address. Without -i, the address reference adds callback to the global list; mode 6 returns unknown before tracing the direct call (analysis/app/src/ipcallgraph.cpp:1370-1378; analysis/app/src/syspartUtility.cpp:159-165). No runtime output was tested.
- Expected: Report the known direct callsite and its traced argument while retaining uncertainty for possible indirect callers (analysis/app/src/syspartUtility.cpp:188-241).
- Actual: The source predicts no `FUNC ... CALLINGFN ...` line or `TYPE ...` value record for that direct callsite: the helper returns before their print paths (analysis/app/src/syspartUtility.cpp:159-165; analysis/app/src/syspartUtility.cpp:223-265).
- Evidence: analysis/app/src/testSyspart.cpp:245-273 — mode 6 calls getArgumentValue; analysis/app/src/syspart.cpp:2632-2644 — it generates the graph and invokes argument tracing with analysisType 0; analysis/app/src/ipcallgraph.cpp:891-895 and analysis/app/src/ipcallgraph.cpp:224-247 — a direct call records a parent edge; analysis/app/src/ipcallgraph.cpp:1352-1359 and analysis/app/src/ipcallgraph.cpp:1370-1378 — a separate linked address reference adds the callee to the global address-taken list when -i is absent; analysis/app/src/syspartUtility.cpp:104-117 — the fresh tracing call proceeds to the helper; analysis/app/src/syspartUtility.cpp:159-165 — the address-taken check inserts unknown and returns before parent traversal at analysis/app/src/syspartUtility.cpp:188-241.
- Assessment: A tiny source-bounded test is `void (* volatile sink)(int); void callback(int x) {} int main(void) { sink = callback; callback(42); }`, compiled so both the address reference and direct call remain. For `-a 6,callback,7` without `-i`, the expected argument report includes the direct caller `main` and, if the constant register definition is recognized, `0x2a` (analysis/app/src/testSyspart.cpp:245-273; analysis/app/src/syspartUtility.cpp:223-241; analysis/app/src/syspartUtility.cpp:727-745). The source instead returns before examining that caller (analysis/app/src/syspartUtility.cpp:159-165). No binary was run.

### A missing .rodata section is dereferenced while printing a value

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspartUtility.cpp:280`
- Invariant: The section must exist before its virtual address and size are read (analysis/tools/egalito/src/elf/elfmap.cpp:168-172; analysis/app/src/syspartUtility.cpp:278-281).
- Mechanism: For a nonzero type-1 or type-2 result, the printer calls findSection(".rodata") and dereferences the result without checking it. findSection returns nullptr when the section is absent (analysis/app/src/syspartUtility.cpp:267-280; analysis/tools/egalito/src/elf/elfmap.cpp:168-172).
- Reproducer: Source-bounded case: a caller in a module without .rodata passes a nonzero constant to the requested function. Constant tracing produces a type-1 result, which reaches the unchecked section dereference (analysis/app/src/syspartUtility.cpp:735-750; analysis/app/src/syspartUtility.cpp:259-280). No runtime output was tested.
- Expected: Print the traced value and END without decoding .rodata when that section is absent (analysis/app/src/syspartUtility.cpp:264-290).
- Actual: For this source-bounded case, section is null and section->getVirtualAddress() dereferences it; runtime behavior is unobserved (analysis/tools/egalito/src/elf/elfmap.cpp:168-172; analysis/app/src/syspartUtility.cpp:278-280).
- Evidence: analysis/app/src/testSyspart.cpp:245-273 — mode 6 calls getArgumentValue; analysis/app/src/syspart.cpp:2641-2644 — it creates an analysisType-0 utility and requests the argument; analysis/app/src/syspartUtility.cpp:223-241 — a caller's register definition is traced; analysis/app/src/syspartUtility.cpp:727-744 — a constant becomes a type-1 result; analysis/app/src/syspartUtility.cpp:259-280 — the printer reaches the unguarded section dereference; analysis/tools/egalito/src/elf/elfmap.cpp:168-172 — findSection returns nullptr when .rodata is absent; analysis/tools/egalito/src/elf/elfmap.h:131-136 — getSectionReadPtr returns null but does not guard the separate section pointer.
- Assessment: A tiny test case is an ELF executable with no .rodata section whose caller passes the constant 1 to target; run mode -a 6,target,7. Expected output is the type-1 value followed by END, with no section decoding. Constant tracing creates a type-1 result, and the printer's guards exclude only types 0 and 3 and the zero description (analysis/app/src/syspartUtility.cpp:727-744; analysis/app/src/syspartUtility.cpp:259-275). This is a source-supported path; no runtime output was captured.

### Repeated argument values disappear from later callsite records

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspartUtility.cpp:261`
- Invariant: Each printed callsite record should include the values found for that callsite (analysis/app/src/syspartUtility.cpp:225-265).
- Mechanism: The alreadyPrinted vector is created once for the requested function, outside the parent-callsite loop. A value printed for one callsite is suppressed at every later callsite, although each gets its own FUNC and END lines (analysis/app/src/syspartUtility.cpp:188-191; analysis/app/src/syspartUtility.cpp:228-230; analysis/app/src/syspartUtility.cpp:259-291).
- Reproducer: Source-bounded case: one caller invokes the requested function twice with the same constant argument. The first record prints the value; the second passes the alreadyPrinted check with no new value and prints only END (analysis/app/src/syspartUtility.cpp:239-241; analysis/app/src/syspartUtility.cpp:259-291). No runtime output was tested.
- Expected: Each matching callsite's FUNC ... CALLINGADDR line is followed by its shared TYPE ... value line and END (analysis/app/src/syspartUtility.cpp:228-230,259-291).
- Actual: For two matching callsites with the same UDResult, the source predicts the shared TYPE line only in the first record; the later record prints FUNC ... CALLINGADDR and END (analysis/app/src/syspartUtility.cpp:188-191,261-262,291).
- Evidence: analysis/app/src/testSyspart.cpp:245-274 — mode 6 calls getArgumentValue; analysis/app/src/syspart.cpp:2624-2644 — it creates a utility with analysisType 0 and requests argument values; analysis/app/src/ipcallgraph.cpp:121-125,246-247 — parent entries retain callsite addresses; analysis/app/src/syspartUtility.cpp:159-185,199-202,223-225 — early exits, unresolved indirect calls, and unmatched addresses can prevent a record; analysis/app/src/syspartUtility.cpp:188-191,235-262 — for matching callsites, results accumulate while alreadyPrinted is shared across the parent loop; analysis/app/src/syspartUtility.cpp:261-291 — a repeated UDResult fails the print check, although END is still printed.
- Assessment: Tiny test: a caller contains two distinct calls to the requested function, each passing the same constant in the selected register. If both callsites resolve to the same UDResult, the expected output is two FUNC records, each containing the shared TYPE value before END. The source predicts that the second record contains FUNC and END but no repeated TYPE value: alreadyPrinted persists across callsites, and UDResult equality compares the value fields rather than the callsite (analysis/app/src/syspartUtility.cpp:188-191; analysis/app/src/syspartUtility.cpp:228-230; analysis/app/src/syspartUtility.cpp:259-291; analysis/app/src/syspartUtility.h:23-28).

### Mode 6 builds use-def analysis for graph nodes outside the trace

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspartUtility.cpp:1450`
- Invariant: Tracing one requested function needs use-def information only for caller functions reached through its parent edges (analysis/app/src/syspartUtility.cpp:188-227; analysis/app/src/syspartUtility.cpp:249).
- Mechanism: After graph generation, mode 6 calls initialize(), which adds use-def analysis for every graph node before tracing the requested function (analysis/app/src/syspart.cpp:2635-2642; analysis/app/src/syspartUtility.cpp:1448-1453).
- Reproducer: Bounded complexity case: the graph has N nodes, but only A nodes lie on parent paths to the requested function, with A much smaller than N. Initialization invokes addUseDefFor N nodes before tracing can visit the A relevant nodes (analysis/app/src/syspartUtility.cpp:1448-1453; analysis/app/src/syspartUtility.cpp:188-227). No timing or memory use was measured.
- Expected: For a valid requested function, prepare use-def state when tracing reaches a caller; getWorkingSet supports this (analysis/app/src/syspartUtility.cpp:188-206; analysis/tools/egalito/src/analysis/dataflow.cpp:29-35).
- Actual: The source makes one addUseDefFor call per graph node before the requested trace, including nodes outside its reached parent paths (analysis/app/src/syspart.cpp:2638-2642; analysis/app/src/syspartUtility.cpp:1448-1453). No runtime cost was measured.
- Evidence: analysis/app/src/testSyspart.cpp:245-273 — mode 6 calls getArgumentValue; analysis/app/src/syspart.cpp:2632-2642 — graph generation precedes unconditional utility initialization and tracing; analysis/app/src/syspartUtility.cpp:1448-1453 — initialization calls addUseDefFor for every nodeMap entry; analysis/tools/egalito/src/analysis/dataflow.cpp:13-25 — each call builds and analyzes use-def state; analysis/app/src/syspartUtility.cpp:188-206 — tracing follows parent edges and requests each caller's working set; analysis/tools/egalito/src/analysis/dataflow.cpp:29-35 — getWorkingSet already creates missing use-def state on demand.
- Assessment: The missing-function guard returns before graph generation, but a valid mode 6 request unconditionally initializes use-def analysis for every graph node before tracing (analysis/app/src/syspart.cpp:2626-2642; analysis/app/src/syspartUtility.cpp:1448-1453). A tiny test would use calls main → caller → target and main → unrelated, then request `-a 6,target,7`. Expected trace output includes `FUNC target CALLINGFN caller` and no call from unrelated; an addUseDefFor call count would include unrelated during initialization (analysis/app/src/syspartUtility.cpp:188-206; analysis/app/src/syspartUtility.cpp:222-229; analysis/app/src/syspartUtility.cpp:1448-1453). This test was not run.

<!-- harness:logic:mode-6:end -->

<!-- harness:logic:mode-7:start -->
## Harness logic audit — mode 7

Dispatcher and modules: README.md, analysis/app/README.md, analysis/app/src/testSyspart.cpp, analysis/app/src/syspart.cpp, analysis/app/src/ipcallgraph.cpp, analysis/app/src/ipcallgraph.h

### Mode 7 ignores the supplied TypeArmor file

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:1720`
- Invariant: When -t supplies a TypeArmor file, mode 7 must pass its path to the callgraph before parsing metadata (analysis/app/src/testSyspart.cpp:64-65; analysis/app/src/ipcallgraph.cpp:532).
- Mechanism: The dispatcher stores the path in Syspart, but run2 sets only the TypeArmor flag before generate; it never calls setTypeArmorPath on the callgraph (analysis/app/src/testSyspart.cpp:184-185; analysis/app/src/syspart.cpp:1716-1724; analysis/app/src/ipcallgraph.h:389-392). generate then parses the callgraph's path, and a callsite without parsed metadata retains the full candidate set (analysis/app/src/ipcallgraph.cpp:1815-1817; analysis/app/src/ipcallgraph.cpp:532; analysis/app/src/ipcallgraph.cpp:824-833).
- Reproducer: Source-bounded case: use -a 7,* -t PATH with a file that gives an indirect callsite zero arguments and an address-taken target one argument (analysis/app/src/testSyspart.cpp:64-65,276-285; analysis/app/src/ipcallgraph.cpp:846-855). No workload was run.
- Expected: With the proposed metadata, caller's mode 7 syscall output excludes getpid (analysis/app/src/ipcallgraph.cpp:846-855; analysis/app/src/syspart.cpp:1744-1748).
- Actual: Source prediction: in the default indirect-call path, the supplied file is not opened, target remains a candidate, and caller's output can include getpid, with avoidable candidate-edge and summary traversal cost (analysis/app/src/syspart.cpp:1716-1724; analysis/app/src/ipcallgraph.cpp:532-534; analysis/app/src/ipcallgraph.cpp:824-831; analysis/app/src/syspart.cpp:405-448).
- Evidence: analysis/app/src/testSyspart.cpp:64-65 — `-t` records the flag and path; analysis/app/src/testSyspart.cpp:184-185 — the dispatcher stores the path in Syspart; analysis/app/src/testSyspart.cpp:276-285 — mode 7 calls run2; analysis/app/src/syspart.h:62-65 — Syspart stores the path separately; analysis/app/src/syspart.cpp:1716-1724 — run2 sets the callgraph flag and calls generate without setting its path; analysis/app/src/ipcallgraph.h:289-291 — the callgraph has its own initially empty path; analysis/app/src/ipcallgraph.cpp:1815-1817 — generate invokes the parser when enabled; analysis/app/src/ipcallgraph.cpp:532-534 — the parser opens the callgraph path; analysis/app/src/ipcallgraph.cpp:664-666,711-719 — unresolved indirect calls use TypeArmor filtering; analysis/app/src/ipcallgraph.cpp:824-833 — missing callsite metadata retains all address-taken candidates; analysis/app/src/syspart.cpp:405-448 — retained parent edges feed derived syscall summaries. The direct-only option and already resolved indirect calls bypass this path (analysis/app/src/syspart.cpp:1721-1724; analysis/app/src/ipcallgraph.cpp:692-705).
- Assessment: A tiny source-bounded test would use a binary where caller has one unresolved indirect call, an address-taken target takes one argument, and only target issues syscall 39 (getpid). Supply `icallargs executable 0xCALL 0` and `fnargs executable 0xTARGET 1` through `-t`, then request `-a 7,caller`. The parser accepts those records, and the argument check would prune target; expected output for caller excludes getpid (analysis/app/src/ipcallgraph.cpp:574-605; analysis/app/src/ipcallgraph.cpp:846-855; analysis/app/src/syspart.cpp:92; analysis/app/src/syspart.cpp:1744-1748). No binary was run.

### A quoted symbol name can invalidate mode 7 JSON

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:1787`
- Invariant: Every module and function key in the all-functions result must be escaped as a JSON string (analysis/app/src/syspart.cpp:1768-1787).
- Mechanism: run2 writes module names and function-name-derived keys between literal quotes without escaping their contents (analysis/app/src/syspart.cpp:1774,1780-1787).
- Reproducer: Source-bounded case: an included function has the name f"q. The emitted key has the form "f"q@ADDRESS", with an unescaped interior quote (analysis/app/src/syspart.cpp:1780-1787). No output was observed.
- Expected: The function key contains an escaped interior quote: "f\"q@1000" (analysis/app/src/syspart.cpp:1768,1787).
- Actual: The source predicts an unescaped interior quote: "f"q@1000" (analysis/app/src/syspart.cpp:1780,1787).
- Evidence: analysis/app/src/testSyspart.cpp:276-285 — mode 7 passes the argument after the comma to run2; analysis/app/src/syspart.cpp:1732-1752 — * selects all-functions output; analysis/app/src/syspart.cpp:1776-1784 — a function is included when getSysNode is non-null; analysis/app/src/syspart.cpp:1780,1787 — its name is appended to the address and written between literal quotes without escaping. Module keys use the same pattern (analysis/app/src/syspart.cpp:1774).
- Assessment: A tiny source-bounded test case is an ELF function symbol named f"q at address 0x1000 with a non-null syscall node. The expected JSON key is "f\"q@1000"; the source predicts "f"q@1000", which is invalid JSON. ELF symbol names are read from the string table without quote filtering, and Function retains the symbol name (analysis/tools/egalito/src/elf/symbol.cpp:373-402; analysis/tools/egalito/src/chunk/function.cpp:34-38). No output was observed.

### All-functions output repeatedly scans the syscall mapping

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspart.cpp:1761`
- Invariant: Enumerating F parsed functions with G syscall graph nodes should not require a fresh G-entry lookup for each function during both counting and emission (analysis/app/src/syspart.cpp:1755-1765,1770-1784).
- Mechanism: getSysNode linearly scans syscall_mapping; run2 calls it once per function to count output entries and again per function to emit them (analysis/app/src/syspart.cpp:161-172,1759-1765,1776-1784).
- Reproducer: Bounded cost: with F parsed functions and G graph nodes, the two passes can perform Θ(FG) mapping checks even though each graph node already has a Function pointer (analysis/app/src/syspart.cpp:161-172,1755-1765,1770-1784; analysis/app/src/syspart.cpp:290-321). No timing was measured.
- Expected: Count and emit mapped functions using a reusable index while preserving the matching behavior at analysis/app/src/syspart.cpp:166-170.
- Actual: The source performs two linear mapping searches per parsed function in the all-functions branch (analysis/app/src/syspart.cpp:1759-1762,1776-1784). This is a source-supported cost bound, not a measured runtime result.
- Evidence: analysis/app/src/testSyspart.cpp:77-87 — -a selects the analysis number; analysis/app/src/testSyspart.cpp:276-285 — case 7 passes the argument to run2; analysis/app/src/syspart.cpp:1716-1730 — run2 builds the call graph and syscall mapping; analysis/app/src/syspart.cpp:282-294,321 — one SysNode is stored per call-graph node and holds its Function pointer; analysis/app/src/syspart.h:34 — the mapping is keyed by call-graph node; analysis/app/src/syspart.cpp:161-173 — getSysNode linearly scans it; analysis/app/src/syspart.cpp:1755-1765,1770-1784 — both all-functions passes call getSysNode for every parsed function.
- Assessment: For mode -a 7,*, the comma is required and * selects the all-functions branch (analysis/app/src/testSyspart.cpp:276-285; analysis/app/src/syspart.cpp:1732-1752). The null checks skip unmatched functions but do not avoid either lookup; each lookup can inspect all G mapping entries, so the two passes can perform Θ(FG) comparisons (analysis/app/src/syspart.cpp:161-173,1755-1765,1770-1784). Tiny proposed test: one module named toy with parsed functions a@100 and b@200, both mapped to graph nodes with empty syscall sets. Expected output, ignoring whitespace: {"toy":{"a@100":{"direct_syscalls":[],"reachable_syscalls":[]},"b@200":{"direct_syscalls":[],"reachable_syscalls":[]}}} (analysis/app/src/syspart.cpp:1774-1787,1788-1813). Preserve the lookup's address-and-name fallback when indexing (analysis/app/src/syspart.cpp:166-170). No runtime output or timing was observed.

### An unknown named function completes analysis without a result

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:1735`
- Invariant: A named mode 7 request should report that its requested function does not exist before producing a syscall result (analysis/app/src/testSyspart.cpp:276-285; analysis/app/src/syspart.cpp:1732-1749).
- Mechanism: run2 builds the graph and computes syscall summaries before looking up the requested name. If findFunctionByName returns null, the guarded output block is skipped with no diagnostic (analysis/app/src/syspart.cpp:1716-1735,1749; analysis/app/src/syspart.cpp:66-80).
- Reproducer: Source-bounded request: -a 7,no_such_function with a valid root and no matching parsed function (analysis/app/src/testSyspart.cpp:276-285; analysis/app/src/syspart.cpp:66-80). No output was observed.
- Expected: Report the missing requested function before graph generation and syscall computation (analysis/app/src/syspart.cpp:1716-1735).
- Actual: Source predicts no named-function result or missing-name diagnostic, despite the graph and syscall work; the caller still prints analysis time to stderr (analysis/app/src/syspart.cpp:1716-1750; analysis/app/src/testSyspart.cpp:596-599). No runtime output was observed.
- Evidence: analysis/app/src/testSyspart.cpp:276-285 — mode 7 checks only for a comma, then passes the requested name to run2; analysis/app/src/syspart.cpp:1716-1730 — run2 generates the call graph and computes direct and derived syscalls before name lookup; analysis/app/src/syspart.cpp:66-80 — lookup returns null when no parsed function matches; analysis/app/src/syspart.cpp:1732-1750 — null skips the named-function output block without a diagnostic; analysis/app/src/testSyspart.cpp:596-599 — the caller then prints an analysis-time message to stderr and returns.
- Assessment: Tiny proposed test: run mode 7 with a valid binary, a valid root, and a requested name absent from the parsed program, such as `-p <valid-binary> -s main -a 7,no_such_function`. Expected stdout: `Function not found\n`, consistent with the missing-function diagnostic elsewhere in the source (analysis/app/src/syspart.cpp:1405-1409). This test was not run.

### Mode 7 omits unreferenced functions from its all-functions result

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:1761`
- Invariant: The `*` request promises syscall information for all functions, including functions outside the graph rooted at `-s` (README.md:155,318-321).
- Mechanism: Graph generation traverses queued roots and discovered functions; syscall summaries are then created only for graph nodes. The `*` output skips every parsed function for which getSysNode returns null (analysis/app/src/ipcallgraph.cpp:1766-1791; analysis/app/src/syspart.cpp:1721-1729,282-284,1755-1765,1776-1784).
- Reproducer: Source-bounded case: retain a function `hidden` containing a direct syscall, with no call or address reference to it from the selected root or other discovered roots; request `-s main -a 7,*` (analysis/app/src/ipcallgraph.cpp:1766-1791; analysis/app/src/syspart.cpp:1755-1765). No workload was run.
- Expected: `hidden` appears with its direct syscall (README.md:155,318-321).
- Actual: The source predicts that `hidden` is omitted from the all-functions result (analysis/app/src/syspart.cpp:282-284,1761-1762,1782-1784). This is not observed output.
- Evidence: analysis/app/src/testSyspart.cpp:276-285 — mode 7 passes `*` to run2; analysis/app/src/syspart.cpp:1716-1729 — run2 builds the graph before scanning syscalls; analysis/app/src/ipcallgraph.cpp:169-178,1766-1791 — graph construction starts from queued roots; analysis/app/src/ipcallgraph.cpp:453-483,891-904,1370-1378 — init, fini, call, and address references can add roots, but the proposed `hidden` has none; analysis/app/src/syspart.cpp:282-284,288-321 — syscall summaries are created only for graph nodes; analysis/app/src/syspart.cpp:161-174,1755-1765,1776-1786 — both `*` passes skip a function without a SysNode.
- Assessment: A tiny test would retain a uniquely named `hidden` function containing an inline `syscall` instruction, leave it uncalled and unreferenced, and run `./syspart -p test -i -s main -a 7,*`. The expected result includes `hidden` and its syscall because `*` is documented as covering all functions (README.md:155,318-321). No binary was run.

### Mode 7 prints an empty name for a syscall absent from the name map

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:1747`
- Invariant: A detected syscall number must remain identifiable in named and `*` output when the loaded headers do not name it (analysis/app/src/syspart.cpp:291-303,1744-1748,1791-1793,1804-1806).
- Mechanism: The name map is populated only from available numeric header definitions, with defaults loaded only if the map is entirely empty. Syscall extraction can retain a number absent from that map; output uses `system_calls[number]`, whose missing-key value is an empty string (analysis/app/src/syspart.cpp:113-157,291-303,1744-1748,1791-1793,1804-1806).
- Reproducer: Source-bounded case: the readable headers define syscall 0 but omit syscall 39, while a graph function invokes syscall 39. The nonempty map prevents default loading, and extraction retains 39 (analysis/app/src/syspart.cpp:122-157,291-303). No workload was run.
- Expected: The output identifies syscall 39 by number or name (analysis/app/src/syspart.cpp:1744-1748,1802-1806).
- Actual: Source-predicted: a blank line for `foo`, and `""` in the `*` direct and reachable arrays; no runtime output was observed (analysis/app/src/syspart.cpp:1745-1748,1791-1793,1804-1806).
- Evidence: analysis/app/src/testSyspart.cpp:167,274-285 — populates the map before dispatching mode 7 to run2; analysis/app/src/syspart.cpp:113-157 — headers populate numeric names and any nonempty map prevents default loading; analysis/tools/egalito/src/pass/findsyscalls.cpp:35-42,136-137 — a resolved syscall constant enters numberMap without a name-map check; analysis/app/src/syspart.cpp:291-303,176-183 — the number enters direct_syscalls and getSyscalls retains it; analysis/app/src/syspart.cpp:1744-1748,1791-1793,1804-1806 — named and `*` output index the name map, producing an empty string for a missing key.
- Assessment: Tiny source-bounded test: provide readable syscall headers containing only `#define __NR_read 0`, and a function `foo` whose syscall instruction has number 39. The header map is nonempty, so the default entry for 39 is not loaded (analysis/app/src/syspart.cpp:92,113-157). The extractor can retain 39 without checking that map (analysis/tools/egalito/src/pass/findsyscalls.cpp:35-42,136-137; analysis/app/src/syspart.cpp:291-303). Expected output for mode 7's named request is `39\n` (or `getpid\n`); the source predicts only `\n` (analysis/app/src/testSyspart.cpp:274-285; analysis/app/src/syspart.cpp:1744-1748). No binary was run.

<!-- harness:logic:mode-7:end -->

<!-- harness:logic:mode-8:start -->
## Harness logic audit — mode 8

Dispatcher and modules: analysis/app/src/testSyspart.cpp, analysis/app/src/syspart.cpp

### Mode 8 does not compute the documented syscall result

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/testSyspart.cpp:288`
- Invariant: Mode 8 should include the specified libraries and print their reachable system calls (README.md:156).
- Mechanism: The branch treats everything after the first comma as a file path, echoes whitespace-separated pairs, and calls no syscall analysis method (analysis/app/src/testSyspart.cpp:290-303).
- Reproducer: Source-bounded case: pass the documented argument `8,1,libfoo.so`; the branch attempts to open `1,libfoo.so` as one path (README.md:156; analysis/app/src/testSyspart.cpp:290-299).
- Expected: Syscall output including getpid for the proposed reachable-library test (README.md:156).
- Actual: For `8,1,libfoo.so`, the source attempts to open `1,libfoo.so` and prints pairs only if that file supplies them; no runtime result was observed (analysis/app/src/testSyspart.cpp:296-303).
- Evidence: analysis/app/src/testSyspart.cpp:77-86 — `-a` stores the argument and parses mode 8; analysis/app/src/testSyspart.cpp:137-152 — required CLI arguments are checked; analysis/app/src/testSyspart.cpp:156-167 — parsing and setup precede dispatch; analysis/app/src/testSyspart.cpp:288-303 — mode 8 takes everything after the first comma as a path, echoes whitespace-separated pairs, and calls no syscall analysis method; analysis/app/src/testSyspart.cpp:596-599 — only elapsed time is printed afterward.
- Assessment: Mode 8 promises syscall output for a library list in README.md:156 and the CLI help at analysis/app/src/testSyspart.cpp:112. Its implementation only opens a path and echoes pairs (analysis/app/src/testSyspart.cpp:296-303); analysis/app/README.md:56 also describes it as a stub. Tiny test: use a valid binary and a libfoo.so whose reachable function invokes getpid, then pass `-a 8,1,libfoo.so`. The documented result should include getpid (README.md:156), but the branch treats `1,libfoo.so` as a filename (analysis/app/src/testSyspart.cpp:290-299). Parsing and setup still run before this branch, adding avoidable cost for that output (analysis/app/src/testSyspart.cpp:156-167). This is source-supported; no runtime output was captured.

### Mode 8 silently accepts an unreadable pair file

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/testSyspart.cpp:297`
- Invariant: A file-based request needs a readable input file or an error, so an empty result is distinguishable from failed input (analysis/app/src/testSyspart.cpp:296-303).
- Mechanism: The branch never checks whether `ifstream` opened successfully; a failed stream skips the extraction loop, and main returns zero (analysis/app/src/testSyspart.cpp:297-303,599).
- Reproducer: Source-bounded case: use `-a 8,/nonexistent/pairs` with the required `-p` and `-s` arguments (analysis/app/src/testSyspart.cpp:138-152,296-303).
- Expected: A pair-file read error and nonzero exit status (analysis/app/src/testSyspart.cpp:296-303).
- Actual: For a failed open, the source path skips pair output, reports no pair-file error, and returns zero, assuming earlier program parsing completes (analysis/app/src/testSyspart.cpp:153-167,297-303,599). No runtime output was observed.
- Evidence: analysis/app/src/testSyspart.cpp:77-87 — parses `-a 8,/nonexistent/pairs` as mode 8; analysis/app/src/testSyspart.cpp:138-152 — checks for `-p`, `-s`, and `-a`, with no pair-file guard; analysis/app/src/testSyspart.cpp:288-303 — opens the pair file, reads pairs only while extraction succeeds, then breaks without reporting a failed open; analysis/app/src/testSyspart.cpp:596-599 — prints timing and returns zero.
- Assessment: Tiny test: use a valid program and start function with `-a 8,/nonexistent/pairs` (analysis/app/src/testSyspart.cpp:138-158,288-297). Expected: a pair-file read error and a nonzero exit status. The source instead has no stream-open check before the extraction loop and reaches `return 0` (analysis/app/src/testSyspart.cpp:297-303,599).

### Mode 8 performs binary analysis setup before its file echo

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/testSyspart.cpp:156`
- Invariant: Work needed only for binary analysis should be avoided when the selected branch uses only a pair file (analysis/app/src/testSyspart.cpp:288-303).
- Mechanism: Before dispatch, every mode 8 request parses the binary and shared libraries, runs two PLT passes, populates the syscall map, and may scan functions to resolve `-s` (analysis/app/src/testSyspart.cpp:156-181; analysis/app/src/syspart.cpp:47-80,154-157). The mode 8 branch uses none of those results (analysis/app/src/testSyspart.cpp:288-303).
- Reproducer: Bounded source argument: for a binary with F functions and libraries requiring parsing, the unconditional setup runs before reading even a one-pair file; named-root lookup alone scans up to F functions (analysis/app/src/testSyspart.cpp:156-181,296-301; analysis/app/src/syspart.cpp:65-80).
- Expected: A one-pair echo needs only the pair-file read (analysis/app/src/testSyspart.cpp:296-301).
- Actual: The source schedules binary analysis setup before that read, and mode 8 does not use its results (analysis/app/src/testSyspart.cpp:156-186,288-303).
- Evidence: analysis/app/src/testSyspart.cpp:156-167 — binary parsing with shared libraries, two PLT passes and syscall-map population precede dispatch; analysis/app/src/syspart.cpp:131-157 — syscall-map population reads headers or uses defaults; analysis/app/src/testSyspart.cpp:169-186 — root setup can call a function lookup; analysis/app/src/syspart.cpp:66-80 — named lookup iterates module functions; analysis/app/src/testSyspart.cpp:288-303 — mode 8 only reads and echoes pairs from the file.
- Assessment: The argument guards require -p, -s and -a, but none bypass setup for mode 8 (analysis/app/src/testSyspart.cpp:138-167). Tiny test: put `libfoo.so symfoo` in a one-pair file and invoke mode 8 with a valid binary and `-s main`; if setup succeeds, the branch prints `libfoo.so symfoo` (analysis/app/src/testSyspart.cpp:179-182,288-303). This is source-supported; no runtime output or cost was measured.

### Mode 8 flushes stdout for every echoed pair

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/testSyspart.cpp:301`
- Invariant: Echoing N pairs does not require N explicit stdout flushes (analysis/app/src/testSyspart.cpp:299-301).
- Mechanism: `std::endl` writes a newline and flushes on each loop iteration (analysis/app/src/testSyspart.cpp:299-301).
- Reproducer: Bounded source argument: a pair file containing N records reaches the output statement N times, causing N flushes (analysis/app/src/testSyspart.cpp:299-301).
- Expected: N echoed lines without an explicit flush after each record (analysis/app/src/testSyspart.cpp:299-301).
- Actual: The source requests one flush for each pair through `endl`; this is source-supported, not runtime-confirmed (analysis/app/src/testSyspart.cpp:299-301).
- Evidence: analysis/app/src/testSyspart.cpp:77-87 — -a selects mode 8; analysis/app/src/testSyspart.cpp:138-152 — -p, -s, and -a are required; analysis/app/src/testSyspart.cpp:288-297 — case 8 takes the path after the comma and opens it; analysis/app/src/testSyspart.cpp:299-303 — the unbounded pair loop writes each pair with `endl` and then exits the case.
- Assessment: Tiny test case: with valid -p and -s arguments, use a pair file containing `libA symA\nlibB symB\n` and pass its path as `-a 8,<path>` (analysis/app/src/testSyspart.cpp:138-152,288-299). The echo portion of stdout should be `libA symA\nlibB symB\n` (analysis/app/src/testSyspart.cpp:299-301). Each echoed pair uses `endl`, which requests a stdout flush; no runtime cost was measured (analysis/app/src/testSyspart.cpp:301).

### Mode 8 silently drops an incomplete final pair

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/testSyspart.cpp:299`
- Invariant: A readable pair file with an unmatched final token must report incomplete input so it cannot be mistaken for a complete result (analysis/app/src/testSyspart.cpp:297-303).
- Mechanism: The loop prints only when extraction of both `lib` and `sym` succeeds. It does not check for an unmatched token after extraction fails, and main returns zero (analysis/app/src/testSyspart.cpp:299-303,599).
- Reproducer: Source-bounded case: a readable file containing `libA symA` followed by `libB` reaches the output statement for the first pair, then exits the loop when no symbol follows `libB` (analysis/app/src/testSyspart.cpp:299-303).
- Expected: The proposed test reports the incomplete `libB` pair and exits nonzero (analysis/app/src/testSyspart.cpp:297-303).
- Actual: For the proposed input, the source path prints `libA symA`, omits `libB`, and returns zero; this is source-supported, not observed runtime output (analysis/app/src/testSyspart.cpp:299-303,596-599).
- Evidence: analysis/app/src/testSyspart.cpp:137-152 — main checks required command-line arguments before dispatch; analysis/app/src/testSyspart.cpp:288-297 — mode 8 requires a comma and opens the named file; analysis/app/src/testSyspart.cpp:299-303 — output occurs only after both tokens are extracted, then the case ends without checking an unmatched token; analysis/app/src/testSyspart.cpp:596-599 — main prints timing and returns zero.
- Assessment: Tiny test: with valid -p and -s arguments, use -a 8,/tmp/pairs and a readable file containing `libA symA\nlibB\n`. Expect `libA symA` followed by an incomplete-pair diagnostic for `libB` and a nonzero exit status. The source has no such check after the pair-reading loop (analysis/app/src/testSyspart.cpp:297-303).

<!-- harness:logic:mode-8:end -->

<!-- harness:logic:mode-9:start -->
## Harness logic audit — mode 9

Dispatcher and modules: README.md, analysis/app/README.md, analysis/app/src/testSyspart.cpp, analysis/app/src/syspart.cpp, analysis/app/src/ipcallgraph.cpp, analysis/app/src/ipcallgraph.h, analysis/app/src/nss.cpp

### A data-linked call ignores its site-specific targets

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/ipcallgraph.cpp:1468`
- Invariant: When a data-linked call's referenced data identifies targets, its indirect edges should use those targets (analysis/app/src/ipcallgraph.cpp:1468-1482; analysis/app/src/ipcallgraph.cpp:1615-1637).
- Mechanism: The data parser records targets for the callsite, but unresolved-edge generation supplies the global address-taken set instead; the -i resolver examines only indirect call and jump instructions (analysis/app/src/ipcallgraph.cpp:1615-1637; analysis/app/src/ipcallgraph.cpp:664-719; analysis/app/src/syspartUtility.cpp:1140-1157).
- Reproducer: Source-bounded case: one data-linked call references a data entry containing A, while an unrelated reference makes B globally address-taken; run -a 9 without -g (analysis/app/src/ipcallgraph.cpp:1468-1482; analysis/app/src/ipcallgraph.cpp:1633-1637; analysis/app/src/ipcallgraph.cpp:711-719; analysis/app/src/syspart.cpp:2541-2546).
- Expected: For the proposed single-call test: caller -> A only (analysis/app/src/ipcallgraph.cpp:1633-1637; analysis/app/src/ipcallgraph.cpp:366-380).
- Actual: Source-predicted output: caller -> A and caller -> B, assuming both are in allAT; no runtime output was observed (analysis/app/src/ipcallgraph.cpp:1820-1836; analysis/app/src/ipcallgraph.cpp:740-749; analysis/app/src/ipcallgraph.cpp:366-380).
- Evidence: analysis/app/src/testSyspart.cpp:306-309 — -a 9 calls run12; analysis/app/src/syspart.cpp:2541-2548 — without -g, run12 generates and prints indirect edges; analysis/tools/egalito/src/instr/linked-x86_64.h:111-118 — DataLinkedControlFlowInstruction is separate from the ControlFlowInstruction class skipped at analysis/app/src/ipcallgraph.cpp:1355-1358; analysis/app/src/ipcallgraph.cpp:1457-1483 — a linked data target registers the instruction as an indirect site and invokes the data parser; analysis/app/src/ipcallgraph.cpp:1633-1637 — the parser records A for that site; analysis/app/src/ipcallgraph.cpp:1820-1836 — global address-taken functions become allAT before edge generation; analysis/app/src/ipcallgraph.cpp:664-666 and analysis/app/src/ipcallgraph.cpp:720-749 — the data-linked site's fallback inserts allAT, without reading its recorded targets; analysis/app/src/ipcallgraph.cpp:366-380 — the resulting indirect targets are printed.
- Assessment: A tiny source-bounded test would use a data-linked call through a data entry containing A, plus a separate reachable reference that makes B globally address-taken. With -a 9 and without -g, -i, or -t, the expected indirect-edge output is caller -> A only; the source predicts caller -> A and caller -> B. The parser records A for the callsite, but edge generation uses the global address-taken set instead (analysis/app/src/ipcallgraph.cpp:1633-1637; analysis/app/src/ipcallgraph.cpp:664-666; analysis/app/src/ipcallgraph.cpp:740-749).

### Default mode 9 eagerly builds unused use-def analyses

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/ipcallgraph.cpp:176`
- Invariant: Without -i, graph-node creation need not run use-def analysis when producing indirect edges (analysis/app/src/ipcallgraph.cpp:1797-1810; analysis/app/src/ipcallgraph.cpp:1820-1836).
- Mechanism: Creating roots and edge endpoints calls getWorkingSet regardless of -i; a cache miss constructs a CFG and runs use-def analysis, retaining its objects until DataFlow destruction (analysis/app/src/ipcallgraph.cpp:164-176,224-245; analysis/tools/egalito/src/analysis/dataflow.cpp:13-35,166-177).
- Reproducer: Bounded cost: with V newly discovered graph functions and -a 9 without -i, these calls can trigger V CFG constructions and use-def analyses although the -i resolution stage is skipped (analysis/app/src/ipcallgraph.cpp:164-176,224-245,1797-1810; analysis/tools/egalito/src/analysis/dataflow.cpp:13-35).
- Expected: With -a 9 and no -i, graph-node creation should add nodes without constructing use-def analyses solely for those nodes (analysis/app/src/ipcallgraph.cpp:164-176,224-245,1797-1811).
- Actual: On a cache miss, graph-node creation constructs a CFG and runs use-def analysis; the resulting objects remain cached until DataFlow destruction. Time and memory impact were not measured (analysis/app/src/ipcallgraph.cpp:164-176,224-245; analysis/tools/egalito/src/analysis/dataflow.cpp:13-35,166-177).
- Evidence: analysis/app/src/testSyspart.cpp:306-308 — mode 9 calls run12; analysis/app/src/syspart.cpp:2534-2548 — run12 sets the flags, calls generate by default, then prints indirect edges; analysis/app/src/ipcallgraph.cpp:169-176,224-245 — root and new edge endpoints call getWorkingSet without an -i guard; analysis/app/src/ipcallgraph.cpp:1377-1401,1797-1811 — use-def consumers in address-taken filtering and indirect resolution are gated by -i; analysis/tools/egalito/src/analysis/dataflow.cpp:13-35,166-177 — each cache miss builds and analyzes a CFG, with objects retained until destruction; analysis/app/src/ipcallgraph.cpp:1820-1836 — indirect edges are generated after resolution is skipped.
- Assessment: No guard refutes the candidate: without -i, the flag remains false, yet mode 9 still creates graph nodes that request working sets (analysis/app/src/testSyspart.cpp:26,68,306-308; analysis/app/src/ipcallgraph.cpp:164-176,224-245). A tiny test would use a root function with one indirect call and one address-taken target; expected mode 9 output includes a root-to-target indirect edge, while graph-node creation requires no use-def analysis (analysis/app/src/ipcallgraph.cpp:366-381,1820-1836). This is source-supported; no runtime output or cost measurement was captured.

### NSS resolution rescans the library list for repeated backends

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/ipcallgraph.cpp:1920`
- Invariant: Once an NSS backend is parsed, resolving another symbol from that backend should reuse its module without another library-list scan (analysis/app/src/ipcallgraph.cpp:1920-1924).
- Mechanism: NSS discovery creates one entry per matching external symbol; resolution calls parseLibraries for each entry–backend pair before checking for the backend's module. parseLibraries iterates the full library list even when every library is already parsed (analysis/app/src/nss.cpp:47-68; analysis/app/src/ipcallgraph.cpp:1909-1924; analysis/tools/egalito/src/conductor/conductor.cpp:96-107).
- Reproducer: Bounded cost: M NSS symbols sharing one available backend and L loaded libraries cause M library-list scans, or O(M×L) inspections, instead of one scan followed by module reuse (analysis/app/src/nss.cpp:47-68; analysis/app/src/ipcallgraph.cpp:1909-1924; analysis/tools/egalito/src/conductor/conductor.cpp:96-107).
- Expected: After the backend is parsed, later symbols reuse its module without another library-list scan (analysis/app/src/ipcallgraph.cpp:1921-1926).
- Actual: For M discovered symbols sharing an available backend, the source calls parseLibraries M times and inspects the library list on each call; already parsed modules are skipped (analysis/app/src/nss.cpp:47-65; analysis/app/src/ipcallgraph.cpp:1909-1923; analysis/tools/egalito/src/conductor/conductor.cpp:96-107).
- Evidence: analysis/app/src/nss.cpp:47-65 — discovery appends an entry for each matching external symbol; analysis/app/src/ipcallgraph.cpp:1909-1923 — each entry and backend reaches parseLibraries before looking up the backend module, subject to the missing-libc and missing-file guards at lines 1903-1905 and 1915-1917; analysis/tools/egalito/src/elf/elfdynamic.cpp:243-246 — an existing library is reused; analysis/tools/egalito/src/conductor/conductor.cpp:96-107 — every call still traverses the library list, while already parsed modules are skipped.
- Assessment: A tiny test case is a mode -a 9 input with external symbols getpwnam and getpwuid, a passwd configuration selecting one available backend, and L loaded libraries. Both symbols map to passwd (analysis/app/src/nss.cpp:123-124); mode 9 calls run12, which calls resolveNss (analysis/app/src/testSyspart.cpp:306-309; analysis/app/src/syspart.cpp:2534-2538). Expected counter output from the current source is `parseLibraries calls: 2` and at least `2 × L library inspections`, provided both symbols and the backend are discovered (analysis/app/src/nss.cpp:47-65; analysis/app/src/ipcallgraph.cpp:1909-1920; analysis/tools/egalito/src/conductor/conductor.cpp:96-103). This is a source-supported prediction; no runtime output was captured.

### Mode 9 repeatedly copies an unused data-section list

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/ipcallgraph.cpp:414`
- Invariant: Graph construction should not repeatedly copy a list that has no reads; dsInModule is declared at analysis/app/src/ipcallgraph.h:303 and its only source references are the writes at analysis/app/src/ipcallgraph.cpp:411-419.
- Mechanism: Mode 9 calls generate, which calls findData (analysis/app/src/syspart.cpp:2544; analysis/app/src/ipcallgraph.cpp:1766-1768). For each data section, findData copies the existing module vector, appends one pointer, then copies the vector back (analysis/app/src/ipcallgraph.cpp:409-419).
- Reproducer: Bounded cost: a module with D data sections causes copies of vectors of lengths 0 through D−1, twice per section, for O(D²) pointer copying (analysis/app/src/ipcallgraph.cpp:409-419).
- Expected: For the proposed three-section test, retain the three isModuleVisited entries needed by later parsing without copying or retaining the unused dsInModule vector (analysis/app/src/ipcallgraph.cpp:418-419,1508-1525).
- Actual: The source predicts quadratic pointer copying across D data sections and retention of D pointers in dsInModule; runtime cost has not been measured (analysis/app/src/ipcallgraph.cpp:409-419; analysis/app/src/ipcallgraph.h:303).
- Evidence: analysis/app/src/testSyspart.cpp:74-86 — -a selects the option and -g enables the direct flag; analysis/app/src/testSyspart.cpp:306-309 — option 9 calls run12; analysis/app/src/syspart.cpp:2534-2544 — run12 calls generate by default or generateDirectCallGraph with -g; analysis/app/src/ipcallgraph.cpp:1742-1744,1766-1768 — both paths call findData; analysis/app/src/ipcallgraph.cpp:409-419 — each data section copies the existing vector, appends a pointer, and copies it back; analysis/app/src/ipcallgraph.h:303-304 — dsInModule and isModuleVisited are separate fields; analysis/app/src/ipcallgraph.cpp:1508-1525 — later parsing reads isModuleVisited; analysis/app/src/ipcallgraph.cpp:411-419 — the only source references to dsInModule are its lookup and update.
- Assessment: The isData() guard limits the work to data sections, but no guard prevents the repeated vector assignments (analysis/app/src/ipcallgraph.cpp:409-419). A tiny proposed test is one module with three data sections: instrument the two vector assignments and expect the output "copied pointer elements: 9; retained data-section pointers: 3"—copies of 1+2 elements into the local vector and 1+2+3 back into the map (analysis/app/src/ipcallgraph.cpp:411-419). This is a source prediction, not observed runtime output. The candidate's stated copy count omits the newly appended pointer copied back on each iteration (analysis/app/src/ipcallgraph.cpp:417-419).

<!-- harness:logic:mode-9:end -->

<!-- harness:logic:mode-10:start -->
## Harness logic audit — mode 10

Dispatcher and modules: README.md, analysis/app/README.md, analysis/app/src/testSyspart.cpp, analysis/app/src/syspart.cpp, analysis/app/src/syspart.h, analysis/app/src/ipcallgraph.cpp, analysis/app/src/ipcallgraph.h

### A shared ancestor truncates an alternate parent chain

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:2212`
- Invariant: Each direct-parent chain should be traced to its end independently (analysis/app/README.md:86; analysis/app/src/syspart.cpp:2200-2212).
- Mechanism: getCallPath shares one visited set across recursive branches and returns immediately when a node was visited through an earlier branch (analysis/app/src/syspart.cpp:2183-2187,2212).
- Reproducer: Source-bounded graph: root calls C; C calls A and B; A and B both call target. Trace target (analysis/app/src/syspart.cpp:2199-2212).
- Expected: Both branches include C <- main (analysis/app/README.md:58; analysis/app/src/syspart.cpp:2200-2212).
- Actual: Source inference: the second branch prints its edge to C, but its recursive call returns at C, so C <- main appears only once (analysis/app/src/syspart.cpp:2185-2187,2211-2212).
- Evidence: analysis/app/src/ipcallgraph.cpp:893-895 — direct calls become graph edges; analysis/app/src/ipcallgraph.cpp:246-247 — each edge records a parent and its direct flag; analysis/app/src/ipcallgraph.h:187-189 — getParentWithType returns those entries; analysis/app/src/syspart.cpp:2199-2212 — getCallPath prints each direct-parent edge and recurses with the same visited set; analysis/app/src/syspart.cpp:2185-2187 — a previously visited parent returns before expanding its parents.
- Assessment: Tiny test case: main calls C; C calls A and B; A and B each call target. Trace target with mode -a 10,target. The expected trace contains both target <- A <- C <- main and target <- B <- C <- main, in either branch order. Mode 10 calls run8, which creates one visited set for the entire trace (analysis/app/src/testSyspart.cpp:311-322; analysis/app/src/syspart.cpp:2257-2258). No runtime output was captured.

### The trace can include a chain outside the selected root

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:2199`
- Invariant: A chain described as leading back to the selected start function should belong to that root's call graph (analysis/app/README.md:86; analysis/app/src/syspart.cpp:2227-2228).
- Mechanism: Graph construction adds initialization functions as independent roots, while getCallPath follows every direct parent without checking whether it leads to the selected start function (analysis/app/src/ipcallgraph.cpp:455-462,1770-1775; analysis/app/src/syspart.cpp:2199-2212).
- Reproducer: Source-bounded graph: main calls target, and an .init_array constructor independently calls target. Both functions are graph roots or reachable from one (analysis/app/src/ipcallgraph.cpp:455-462,1770-1775).
- Expected: For the proposed test, a path through main only: target <- main (analysis/app/README.md:58; analysis/app/src/syspart.cpp:2211).
- Actual: Source-supported inference: both target <- main and target <- ctor are printed, in unspecified order, if both direct edges are present (analysis/app/src/ipcallgraph.cpp:891-895,224-247; analysis/app/src/syspart.cpp:2199-2212).
- Evidence: analysis/app/src/testSyspart.cpp:311-322 — mode 10 calls run8; analysis/app/src/syspart.cpp:2227-2258 — run8 sets the selected root, generates the graph, then calls getCallPath for target; analysis/app/src/ipcallgraph.cpp:400-401,455-462 — findData scans program modules and adds .init_array targets as roots; analysis/app/src/ipcallgraph.cpp:1766-1775 — generate processes queued roots through findDirectEdges; analysis/app/src/ipcallgraph.cpp:891-895,224-247 — direct calls create parent entries; analysis/app/src/syspart.cpp:2199-2212 — getCallPath prints and follows every direct parent without checking STARTFN.
- Assessment: The selected start function is queued as a root, but .init_array functions are also queued independently (analysis/app/src/ipcallgraph.cpp:169-177; analysis/app/src/ipcallgraph.cpp:455-462). No selected-root check appears in the direct-parent walk (analysis/app/src/syspart.cpp:2183-2212). Tiny test case: an ELF with main() calling target() and an .init_array constructor ctor() also calling target(); invoke mode 10 with -s main and target as its argument (analysis/app/src/testSyspart.cpp:311-322). The intended path output should include target <- main and exclude target <- ctor, consistent with the documented trace toward STARTFN (analysis/app/README.md:58).

### An indirect-only parent suppresses the no-direct-call message

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:2216`
- Invariant: The no-direct-call message should depend on whether a direct parent exists (analysis/app/src/syspart.cpp:2200-2202,2214-2218).
- Mechanism: The loop skips parents marked indirect, but the final condition checks the size of the unfiltered parent map (analysis/app/src/syspart.cpp:2199-2202,2216; analysis/app/src/ipcallgraph.cpp:711-715).
- Reproducer: Source-bounded case: an address-taken target has one unresolved indirect caller and no direct callers (analysis/app/src/ipcallgraph.cpp:711-715).
- Expected: For an indirect-only target, print `No direct call to function target` (analysis/app/src/syspart.cpp:2200-2202,2216-2218).
- Actual: The false-typed parent is skipped by the loop but keeps `parents.size()` nonzero, so the message is omitted; inferred from source (analysis/app/src/ipcallgraph.cpp:711-715; analysis/app/src/syspart.cpp:2199-2202,2216-2218).
- Evidence: analysis/app/src/ipcallgraph.cpp:1820-1836 — address-taken functions become indirect targets; analysis/app/src/ipcallgraph.cpp:690-715 — an unresolved indirect call adds each target as a false-typed parent; analysis/app/src/ipcallgraph.cpp:121-125 — insertParent stores that type; analysis/app/src/ipcallgraph.h:187-190 — getParentWithType returns the full map; analysis/app/src/syspart.cpp:2199-2218 — traversal accepts only true-typed parents, but the message checks whether the unfiltered map is empty.
- Assessment: Mode -a 10 passes the named function to run8, which generates the full call graph by default and calls getCallPath if the function and node exist (analysis/app/src/testSyspart.cpp:28,311-323; analysis/app/src/syspart.cpp:2232-2258). A tiny test case is `void target(void) {} void (*volatile fp)(void) = target; int main(void) { fp(); }`. If the indirect call remains unresolved and target is in the address-taken set, the expected relevant output is `No direct call to function target` (analysis/app/src/ipcallgraph.cpp:1820-1836,690-715; analysis/app/src/syspart.cpp:2216-2218). This is a source-supported prediction; no runtime output was observed.

### Recursive tracing repeatedly copies the global address-taken set

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspart.cpp:2212`
- Invariant: Reading address-taken membership during a trace need not duplicate the entire set at each depth (analysis/app/src/syspart.cpp:2192-2195; analysis/app/src/syspart.h:58).
- Mechanism: run8 obtains the global set by value; getCallPath also takes it by value and passes it by value on every recursive call (analysis/app/src/ipcallgraph.h:408-411; analysis/app/src/syspart.cpp:2240,2258,2183,2212).
- Reproducer: Bounded cost: for a direct-parent chain of depth d and a global address-taken set of size A, recursive calls copy Θ(dA) set entries in total and can retain Θ(dA) entries across active stack frames (analysis/app/src/syspart.cpp:2183,2212,2258).
- Expected: A shared set could serve every membership check without a per-depth copy (analysis/app/src/syspart.cpp:2194-2195).
- Actual: For a direct-parent chain of depth d and a set of A entries, the by-value calls copy Θ(dA) entries in total and can retain Θ(dA) entries in active frames (analysis/app/src/syspart.cpp:2183,2202-2212). Runtime cost was not measured.
- Evidence: analysis/app/src/testSyspart.cpp:311-322 — mode 10 calls run8; analysis/app/src/ipcallgraph.h:408-411 — getGlobalATList returns the set by value; analysis/app/src/syspart.cpp:2240,2258 — run8 stores it and calls getCallPath; analysis/app/src/syspart.h:57 and analysis/app/src/syspart.cpp:2183 — getCallPath takes the set by value; analysis/app/src/syspart.cpp:2194-2195,2212 — it checks membership and passes the set by value recursively.
- Assessment: The visited guard and direct-parent filter limit traversal, but neither prevents a copy on each reached recursive call (analysis/app/src/syspart.cpp:2183-2187,2199-2212). Tiny test case: a direct chain main → mid → leaf, with leaf and one unrelated function in the global address-taken set. For mode -a 10,leaf, the expected trace includes "Function leaf", "AT leaf", the leaf-to-mid and mid-to-main parent lines, and "No direct call to function main" (analysis/app/src/testSyspart.cpp:311-322; analysis/app/src/syspart.cpp:2194-2196,2211-2218,2242-2258).

### NSS expansion can turn an indirect caller into a direct parent

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/ipcallgraph.cpp:1974`
- Invariant: Mode 10 follows only parents marked direct (analysis/app/src/syspart.cpp:2199-2202), so an indirect callsite must not become a direct-parent chain.
- Mechanism: Indirect-edge generation records callers in the NSS function's parent map (analysis/app/src/ipcallgraph.cpp:711-715; analysis/app/src/ipcallgraph.cpp:121-124). NSS expansion reads that map without checking edge type and adds an edge to each resolved backend marked direct (analysis/app/src/ipcallgraph.cpp:1963-1974). Mode 10 expands these edges after graph generation (analysis/app/src/syspart.cpp:2234-2239).
- Reproducer: Source-bounded graph: root has an unresolved indirect call; the global address-taken set includes an NSS libc function with a resolved backend. The indirect caller becomes a parent candidate, then NSS expansion adds a direct edge from that caller to the backend (analysis/app/src/ipcallgraph.cpp:711-715; analysis/app/src/ipcallgraph.cpp:1963-1974).
- Expected: No direct-parent chain from the backend through root (analysis/app/src/syspart.cpp:2199-2212).
- Actual: For the specified fixture, the source predicts a printed backend-to-root direct-parent line (analysis/app/src/ipcallgraph.cpp:1967-1975; analysis/app/src/syspart.cpp:2202-2212).
- Evidence: analysis/app/src/testSyspart.cpp:311-322 — mode 10 calls run8; analysis/app/src/syspart.cpp:2227-2239 — run8 generates the indirect graph when direct is false, then expands NSS edges; analysis/app/src/ipcallgraph.cpp:711-715 — an unresolved indirect call records the NSS target's parent with type false; analysis/app/src/ipcallgraph.h:187-195 — parent callsites and edge types have separate accessors; analysis/app/src/ipcallgraph.cpp:1963-1975 — NSS expansion reads untyped parent callsites and adds a backend edge with type true; analysis/app/src/ipcallgraph.cpp:224-247 — addEdge records that true type on the backend parent; analysis/app/src/syspart.cpp:2199-2212 — tracing prints and follows true parents.
- Assessment: A tiny source-level test fixture would give root one unresolved indirect callsite, put the libc NSS entry getpwnam in the global address-taken set, and resolve one backend such as _nss_files_getpwnam (analysis/app/src/nss.cpp:59; analysis/app/src/nss.cpp:123; analysis/app/src/ipcallgraph.cpp:1820-1836; analysis/app/src/ipcallgraph.cpp:1924-1943). With mode -a 10 and the default indirect-graph setting, the expected trace contains no direct-parent line from that backend to root; the source predicts a line of the form '_nss_files_getpwnam libnss_files.so.2 <- root app' (analysis/app/src/testSyspart.cpp:28; analysis/app/src/testSyspart.cpp:311-322; analysis/app/src/syspart.cpp:2199-2212). This is source-supported only; no runtime output was captured.

### Mode 10 does not pass the supplied TypeArmor path to the graph

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:2231`
- Invariant: When -t supplies a TypeArmor file, graph generation should parse that file before filtering indirect targets (analysis/app/src/testSyspart.cpp:64-65; analysis/app/src/ipcallgraph.cpp:1815-1817).
- Mechanism: The CLI stores the path in Syspart (analysis/app/src/testSyspart.cpp:184-185), but run8 sets only the graph's TypeArmor flag before generate (analysis/app/src/syspart.cpp:2225-2235). The parser opens the graph's separate path field (analysis/app/src/ipcallgraph.h:389-392; analysis/app/src/ipcallgraph.cpp:532-534). Without parsed callsite metadata, filtering keeps the full address-taken set (analysis/app/src/ipcallgraph.cpp:824-833).
- Reproducer: Supply -t with a file that excludes an address-taken NSS libc function from an indirect callsite, then trace a resolved NSS backend in mode 10. The missing graph path leaves the callsite metadata absent; the full candidate set can feed NSS expansion (analysis/app/src/ipcallgraph.cpp:824-833; analysis/app/src/ipcallgraph.cpp:1963-1974).
- Expected: The supplied TypeArmor records populate callsite and function argument counts, excluding the one-argument candidate at the zero-argument callsite before NSS expansion (analysis/app/src/ipcallgraph.cpp:573-605; analysis/app/src/ipcallgraph.cpp:854-855; analysis/app/src/ipcallgraph.cpp:1963-1975).
- Actual: The mode 10 source does not pass the supplied path to the graph; an unopened TypeArmor file leaves callsite metadata absent, so the candidate remains eligible for NSS expansion (analysis/app/src/syspart.cpp:2231-2239; analysis/app/src/ipcallgraph.cpp:532-534; analysis/app/src/ipcallgraph.cpp:824-833; analysis/app/src/ipcallgraph.cpp:1963-1975). No runtime output was observed.
- Evidence: analysis/app/src/testSyspart.cpp:64-65 — -t stores the path; analysis/app/src/testSyspart.cpp:184-185 — the path is passed to Syspart; analysis/app/src/testSyspart.cpp:311-323 — mode 10 calls run8; analysis/app/src/syspart.cpp:2227-2235 — run8 sets the TypeArmor flag and generates the graph without passing the path; analysis/app/src/syspart.cpp:1512-1518 — another mode explicitly passes the path; analysis/app/src/ipcallgraph.h:385-392 — graph flag and path have separate setters; analysis/app/src/ipcallgraph.cpp:1815-1816 — generate calls the parser when the flag is set; analysis/app/src/ipcallgraph.cpp:532-534 — the parser opens the graph path; analysis/app/src/ipcallgraph.cpp:824-833 — absent callsite metadata retains all candidates. The -g branch uses direct graph generation, so this finding concerns the default indirect-edge branch (analysis/app/src/syspart.cpp:2232-2235; analysis/app/src/ipcallgraph.cpp:1742-1764).
- Assessment: A tiny test would use one unresolved indirect callsite with zero arguments, an address-taken NSS function with one argument, and TypeArmor records for both addresses. Run mode 10 with -t and without -g or -i, tracing a backend that the NSS function resolves. Expected output has no backend direct-parent line from that callsite; the source predicts that the missing graph path leaves the candidate eligible, allowing NSS expansion to produce such a line (analysis/app/src/ipcallgraph.cpp:824-833; analysis/app/src/ipcallgraph.cpp:854-855; analysis/app/src/ipcallgraph.cpp:1963-1975; analysis/app/src/syspart.cpp:2199-2212). This is a source-supported prediction, not an observed result.

### An unknown trace target is rejected only after graph construction

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspart.cpp:2245`
- Invariant: A name that matches no parsed function needs no call graph to produce the missing-function result (analysis/app/src/syspart.cpp:66-80; analysis/app/src/syspart.cpp:2244-2249).
- Mechanism: The dispatcher passes the requested name to run8 (analysis/app/src/testSyspart.cpp:311-322). run8 resolves NSS, generates the graph, and adds NSS edges before looking up that name (analysis/app/src/syspart.cpp:2229-2245). Full generation scans direct edges and address-taken sites and may process indirect targets (analysis/app/src/ipcallgraph.cpp:1770-1836).
- Reproducer: Use a valid -s root and -a 10,__syspart_missing__ where the requested name is absent. The name lookup returns null only after the graph work; with I unresolved indirect sites and A address-taken candidates, fallback edge generation can additionally write up to I×A parent entries (analysis/app/src/syspart.cpp:66-80; analysis/app/src/syspart.cpp:2245-2249; analysis/app/src/ipcallgraph.cpp:711-715).
- Expected: A name absent from the parsed functions can be identified by findFunctionByName without graph construction for that request (analysis/app/src/syspart.cpp:66-80; analysis/app/src/syspart.cpp:2244-2249).
- Actual: Both graph branches run before the missing-name check; in full mode, unresolved indirect sites can add parent entries for address-taken targets (analysis/app/src/syspart.cpp:2232-2249; analysis/app/src/ipcallgraph.cpp:711-715). Time and memory were not measured.
- Evidence: analysis/app/src/testSyspart.cpp:311-322 — mode 10 passes the requested name to run8; analysis/app/src/syspart.cpp:2227-2240 — run8 resolves NSS and generates the graph before iterating over names; analysis/app/src/ipcallgraph.cpp:1742-1762 — even direct mode scans edges and address-taken sites; analysis/app/src/ipcallgraph.cpp:1766-1836 — full mode also processes indirect targets; analysis/app/src/syspart.cpp:2244-2249 — the missing-name lookup and message occur afterward.
- Assessment: The caller checks for a comma but does not check whether the requested function exists before calling run8 (analysis/app/src/testSyspart.cpp:311-322). Tiny proposed test: analyze a program containing main with -s main -a 10,__syspart_missing__. Expected stdout includes `Function __syspart_missing__` followed by `No function with name __syspart_missing__` (analysis/app/src/syspart.cpp:2242-2249). No binary was run, so the cost is source-supported, not runtime-confirmed.

<!-- harness:logic:mode-10:end -->

<!-- harness:logic:mode-11:start -->
## Harness logic audit — mode 11

Dispatcher and modules: README.md, analysis/app/README.md, analysis/app/src/testSyspart.cpp, analysis/app/src/syspart.cpp, analysis/app/src/ipcallgraph.cpp, analysis/app/src/ipcallgraph.h

### A failed reachability search falls off a bool function

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:864`
- Invariant: A search with no path to func2 must return false to its caller (analysis/app/src/syspart.cpp:924).
- Mechanism: After both search stacks empty, findFunctionsReachable reaches its closing brace without returning; isFunctionReachable then uses that indeterminate result (analysis/app/src/syspart.cpp:841; analysis/app/src/syspart.cpp:864; analysis/app/src/syspart.cpp:924).
- Reproducer: Use a valid addr in func1 whose successor blocks and transitive callees have no path to func2 (analysis/app/src/syspart.cpp:779; analysis/app/src/syspart.cpp:842). This is a source trace, not observed output.
- Expected: For a failed search, return false and print `bar is not reachable from foo` (analysis/app/src/syspart.cpp:924-947).
- Actual: The failed-search path falls off the end of a bool function, so reading its result has undefined behavior; no runtime result was observed (analysis/app/src/syspart.cpp:842-864; analysis/app/src/syspart.cpp:924-925).
- Evidence: analysis/app/src/testSyspart.cpp:325-365 — mode 11 calls isFunctionReachable; analysis/app/src/syspart.cpp:878-891 — missing call-graph nodes cause an early return; analysis/app/src/syspart.cpp:893-895 — a present start node enters the search; analysis/app/src/syspart.cpp:757-772 — a valid address passes the only false-return guard; analysis/app/src/syspart.cpp:779-840 — successor blocks are searched, with true returned only for a matching direct or indirect child; analysis/app/src/syspart.cpp:841-864 — transitive callees are searched, then the bool function ends without returning when the stack empties; analysis/app/src/syspart.cpp:924-947 — the caller reads that result to choose its reachability message.
- Assessment: The invalid-address guard returns false, but it does not cover a valid address with no path to func2 (analysis/app/src/syspart.cpp:768-772). A tiny test case is `volatile int x; void bar(void){x=1;} void foo(void){x=2;} int main(void){bar(); foo();}`: analyze a valid instruction address in `foo` with `-s main -a 11,<hex_addr>,foo,bar`. The expected final line is `bar is not reachable from foo` (analysis/app/src/syspart.cpp:946-947). This is a source-supported test proposal; no runtime output was captured.

### Mode 11 skips calls after addr in the same block

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:780`
- Invariant: A call after addr in func1 must count toward reachability from that instruction (README.md:159; analysis/app/src/testSyspart.cpp:115).
- Mechanism: The address lookup retains only its containing block, then seeds the scan with that block's successors; the containing block's later instructions are never scanned (analysis/app/src/syspart.cpp:757; analysis/app/src/syspart.cpp:780; analysis/app/src/syspart.cpp:794).
- Reproducer: Put addr on a non-control-flow instruction followed by a call to func2 in the same terminal block (analysis/app/src/syspart.cpp:761; analysis/app/src/syspart.cpp:780). This is a source-bounded case.
- Expected: For the proposed test, `func2 is reachable from func1` (analysis/app/src/syspart.cpp:804; analysis/app/src/syspart.cpp:927).
- Actual: The source path skips the call in addr's containing block (analysis/app/src/syspart.cpp:780; analysis/app/src/syspart.cpp:794). No runtime output was observed; the missing return also prevents a reliable prediction of the final message (analysis/app/src/syspart.cpp:864; analysis/app/src/syspart.cpp:924; analysis/app/src/syspart.cpp:946).
- Evidence: analysis/app/src/syspart.cpp:757 — lookup saves only addr's containing block; analysis/app/src/syspart.cpp:780 — scanning starts with that block's successors; analysis/app/src/syspart.cpp:794 — call-site lookup examines instructions only in popped successor blocks; analysis/app/src/ipcallgraph.cpp:893 — direct calls are keyed by their instruction address; analysis/app/src/syspart.cpp:864 — the helper has no return after exhausting its searches.
- Assessment: The mode 11 caller passes the instruction address to the reachability check (analysis/app/src/testSyspart.cpp:325; analysis/app/src/testSyspart.cpp:364). No guard requires the address to be the last instruction in its block (analysis/app/src/syspart.cpp:757; analysis/app/src/syspart.cpp:761). Tiny proposed test: make func1 contain a non-control-flow instruction at addr immediately followed by a direct call to func2 in the same block, with no other path to func2. The expected result is `func2 is reachable from func1` (README.md:159; analysis/app/src/syspart.cpp:804; analysis/app/src/syspart.cpp:927). No binary was run.

### Mode 11 enables TypeArmor without supplying its file path

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:873`
- Invariant: With -t PATH, indirect targets should be filtered using metadata from PATH (analysis/app/src/testSyspart.cpp:64; analysis/app/src/README.md:41).
- Mechanism: The dispatcher stores PATH in Syspart, but isFunctionReachable sets only the TypeArmor flag before generate; parseTypeArmor opens the graph's typeArmorPath, which this mode never sets (analysis/app/src/testSyspart.cpp:64; analysis/app/src/testSyspart.cpp:181; analysis/app/src/syspart.cpp:873; analysis/app/src/ipcallgraph.cpp:532).
- Reproducer: Supply -t with callsite and target argument metadata that would exclude one address-taken target, then query that target through the indirect site (analysis/app/src/ipcallgraph.cpp:814; analysis/app/src/ipcallgraph.cpp:846; analysis/app/src/syspart.cpp:812). This is a source trace.
- Expected: For the proposed fixture, "target is not reachable from caller" (analysis/app/src/ipcallgraph.cpp:853; analysis/app/src/syspart.cpp:946).
- Actual: Code-supported prediction: the missing graph path leaves the metadata unavailable, so an unresolved site retains the address-taken target and can report "target is reachable from caller" (analysis/app/src/syspart.cpp:873; analysis/app/src/ipcallgraph.cpp:532; analysis/app/src/ipcallgraph.cpp:827; analysis/app/src/syspart.cpp:927). This is not runtime-confirmed.
- Evidence: analysis/app/src/testSyspart.cpp:64 — -t stores PATH; analysis/app/src/testSyspart.cpp:184 — the dispatcher gives it to Syspart; analysis/app/src/syspart.h:62 — that setter stores it only in Syspart. analysis/app/src/testSyspart.cpp:325 — mode 11 dispatches to isFunctionReachable at analysis/app/src/testSyspart.cpp:364. analysis/app/src/syspart.cpp:869 — the method configures the graph through analysis/app/src/syspart.cpp:874 without setting its path. The graph has a separate path member and setter (analysis/app/src/ipcallgraph.h:291; analysis/app/src/ipcallgraph.h:389); another mode explicitly forwards the path (analysis/app/src/syspart.cpp:2336). generate calls parseTypeArmor when enabled (analysis/app/src/ipcallgraph.cpp:1815), but parsing opens the graph's path (analysis/app/src/ipcallgraph.cpp:532); without loaded callsite metadata, filtering retains the address-taken set (analysis/app/src/ipcallgraph.cpp:824).
- Assessment: A tiny test would use an ELF fixture with an address-taken target requiring two arguments and a zero-argument indirect call in a successor block of caller. Supply a TypeArmor file containing matching icallargs and fnargs records, then query from the preceding branch with -s caller -t PATH -a 11,BRANCH_ADDR,caller,target. The expected result is "target is not reachable from caller": the argument-count check excludes it (analysis/app/src/ipcallgraph.cpp:574; analysis/app/src/ipcallgraph.cpp:595; analysis/app/src/ipcallgraph.cpp:602; analysis/app/src/ipcallgraph.cpp:853). The source instead predicts an unfiltered indirect edge and "target is reachable from caller" (analysis/app/src/ipcallgraph.cpp:824; analysis/app/src/ipcallgraph.cpp:827; analysis/app/src/syspart.cpp:812; analysis/app/src/syspart.cpp:820; analysis/app/src/syspart.cpp:927). No runtime output was observed.

### An unknown function name is dereferenced before validation

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:880`
- Invariant: Unknown func1 or func2 must be rejected before dereferencing its Function pointer (analysis/app/src/syspart.cpp:882; analysis/app/src/syspart.cpp:887).
- Mechanism: findFunctionByName can return NULL; getNode is called before the null-node checks, and getNode dereferences a missing Function while attempting its fallback lookup (analysis/app/src/syspart.cpp:67; analysis/app/src/syspart.cpp:880; analysis/app/src/ipcallgraph.h:355; analysis/app/src/ipcallgraph.h:360).
- Reproducer: Use a valid root and -a 11,addr,__missing_func__,target, or an unknown target name (analysis/app/src/testSyspart.cpp:350; analysis/app/src/testSyspart.cpp:364). This is a source-bounded case.
- Expected: Print `Node for __missing_func__ doesn't exist` and return (analysis/app/src/syspart.cpp:882; analysis/app/src/syspart.cpp:884; analysis/app/src/syspart.cpp:885).
- Actual: For an unknown name with no NULL map entry, the source dereferences NULL before that diagnostic (analysis/app/src/syspart.cpp:880; analysis/app/src/ipcallgraph.h:357; analysis/app/src/ipcallgraph.h:360). Runtime output was not observed.
- Evidence: analysis/app/src/testSyspart.cpp:364 — mode 11 passes the names without checking whether they resolve; analysis/app/src/syspart.cpp:68 — name lookup starts with NULL and returns it when no function matches (analysis/app/src/syspart.cpp:73; analysis/app/src/syspart.cpp:80); analysis/app/src/syspart.cpp:878 — the unknown start name yields NULL; analysis/app/src/syspart.cpp:880 — that pointer is passed to getNode before the missing-node check at analysis/app/src/syspart.cpp:882; analysis/app/src/ipcallgraph.h:357 — getNode searches the map, then dereferences an absent key through f->getName() at analysis/app/src/ipcallgraph.h:360. No caller guard on this path refutes the candidate.
- Assessment: A tiny test case is `./syspart -p <valid-binary> -s main -a 11,0,__missing_func__,main`, with a binary containing `main`. The parser accepts both nonempty names and calls `isFunctionReachable` (analysis/app/src/testSyspart.cpp:350; analysis/app/src/testSyspart.cpp:357; analysis/app/src/testSyspart.cpp:364). The expected diagnostic is `Node for __missing_func__ doesn't exist` (analysis/app/src/syspart.cpp:882; analysis/app/src/syspart.cpp:884). This was assessed from source only; no binary was run.

### An invalid addr can still lead to a reachable result

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:924`
- Invariant: The supplied addr must identify an instruction in func1 before any reachability result is reported (analysis/app/src/testSyspart.cpp:115; analysis/app/src/syspart.cpp:761).
- Mechanism: A missing instruction returns false from findFunctionsReachable, but isFunctionReachable then walks returning callers and checks their callsite successors (analysis/app/src/syspart.cpp:768; analysis/app/src/syspart.cpp:924; analysis/app/src/syspart.cpp:933; analysis/app/src/syspart.cpp:937).
- Reproducer: Give func1 an invalid addr and a returning caller whose later block calls func2 (analysis/app/src/syspart.cpp:768; analysis/app/src/syspart.cpp:937; analysis/app/src/syspart.cpp:797). This is a source trace.
- Expected: For an address absent from func1: "Invalid start address ..." and no reachability verdict (analysis/app/src/syspart.cpp:768; analysis/app/src/testSyspart.cpp:115).
- Actual: Source-supported possibility: after "Invalid start address ...", the caller search can print "func2 is reachable from func1" (analysis/app/src/syspart.cpp:770; analysis/app/src/syspart.cpp:937; analysis/app/src/syspart.cpp:927).
- Evidence: analysis/app/src/testSyspart.cpp:338 — mode 11 checks that addr is nonempty; analysis/app/src/testSyspart.cpp:364 — passes it to isFunctionReachable; analysis/app/src/syspart.cpp:882 — guards function nodes, not instruction membership; analysis/app/src/syspart.cpp:761 — looks for the instruction in func1; analysis/app/src/syspart.cpp:768 — a miss prints an error and returns false; analysis/app/src/syspart.cpp:924 — the caller receives that false; analysis/app/src/syspart.cpp:933 — returning functions proceed to parent search; analysis/app/src/syspart.cpp:937 — obtains parent call sites; analysis/app/src/ipcallgraph.cpp:246 — call-graph edges record their call-site address; analysis/app/src/syspart.cpp:942 — queues the caller with that address; analysis/app/src/syspart.cpp:779 — searches successor blocks from the caller's call-site block; analysis/app/src/syspart.cpp:797 — checks calls there; analysis/app/src/syspart.cpp:927 — reports reachable if func2 is found.
- Assessment: A tiny test would give func1 a valid returning body, have a caller call func1 and then call func2 in a successor block, and query mode -a 11 with a hexadecimal address absent from func1 (analysis/app/src/testSyspart.cpp:115; analysis/app/src/syspart.cpp:757; analysis/app/src/syspart.cpp:779; analysis/app/src/syspart.cpp:933). Expected output is "Invalid start address ..." with no reachability verdict; the source permits a later "func2 is reachable from func1" verdict (analysis/app/src/syspart.cpp:770; analysis/app/src/syspart.cpp:937; analysis/app/src/syspart.cpp:927). No runtime output was observed.

### Thread-entry analysis runs before a direct reachability answer

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspart.cpp:897`
- Invariant: A query answerable from func1's successor blocks need not analyze thread entries across the entire graph (analysis/app/src/syspart.cpp:804; analysis/app/src/syspart.cpp:925).
- Mechanism: isFunctionReachable calls getThreadStartFunction before its first reachability check; that routine scans graph nodes and runs CFG and use-def analysis for matching pthread_create sites (analysis/app/src/syspart.cpp:897; analysis/app/src/syspart.cpp:1169; analysis/app/src/syspart.cpp:1180; analysis/app/src/syspart.cpp:1134).
- Reproducer: For a graph with N nodes and P matching pthread_create sites, place a direct func2 call in func1's first successor block. The precheck still scans N nodes and performs up to P thread-site analyses before finding that direct edge (analysis/app/src/syspart.cpp:897; analysis/app/src/syspart.cpp:1169; analysis/app/src/syspart.cpp:804).
- Expected: The direct-call test reports "func2 is reachable from func1" without needing thread discovery (analysis/app/src/syspart.cpp:804-807; analysis/app/src/syspart.cpp:925-928).
- Actual: Source order requires thread discovery first, including analysis at matching pthread_create sites; elapsed time and memory are unmeasured (analysis/app/src/syspart.cpp:897; analysis/app/src/syspart.cpp:1169-1184; analysis/app/src/syspart.cpp:1134-1142).
- Evidence: analysis/app/src/testSyspart.cpp:325-364 — mode 11 calls isFunctionReachable. analysis/app/src/syspart.cpp:897 — it completes getThreadStartFunction before the reachability check at analysis/app/src/syspart.cpp:924. analysis/app/src/syspart.cpp:1169-1216 — discovery scans graph nodes and examines direct and indirect call targets; matching pthread_create sites call find_thread_function. analysis/app/src/syspart.cpp:1134-1142 — that call constructs a CFG and runs use-def analysis. analysis/app/src/syspart.cpp:779-807 — the later check can return true on a direct call in a successor block.
- Assessment: The only guards before thread discovery reject missing start or end graph nodes; neither checks reachability (analysis/app/src/syspart.cpp:878-897). Tiny test case: use a graph where the queried address is in func1's block B0, successor B1 directly calls func2, and an unrelated function calls pthread_create (analysis/app/src/syspart.cpp:779-785; analysis/app/src/syspart.cpp:1169-1184). Expected output includes "func2 is reachable from func1" (analysis/app/src/syspart.cpp:804-807; analysis/app/src/syspart.cpp:924-928). No runtime output or cost was measured.

### A thread entry also called normally blocks a valid caller path

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:935`
- Invariant: Mode 11 must consider a normal caller's continuation when checking reachability from a returning function (README.md:159; analysis/app/src/syspart.cpp:933; analysis/app/src/syspart.cpp:937).
- Mechanism: Thread discovery records a function used as a pthread_create entry (analysis/app/src/syspart.cpp:1180; analysis/app/src/syspart.cpp:1191). The backward search then skips every parent of that function, including an ordinary direct caller recorded by addEdge (analysis/app/src/syspart.cpp:935; analysis/app/src/ipcallgraph.cpp:246; analysis/app/src/ipcallgraph.cpp:247).
- Reproducer: Have main both call worker normally and pass worker to pthread_create. Query an address near worker's return, with a call to func2 after main's normal call to worker (analysis/app/src/syspart.cpp:897; analysis/app/src/syspart.cpp:924; analysis/app/src/syspart.cpp:935). This is a source trace.
- Expected: The normal worker-to-main return path is considered and mode 11 reports "func2 is reachable from worker" (analysis/app/src/syspart.cpp:937; analysis/app/src/syspart.cpp:942; analysis/app/src/syspart.cpp:804; analysis/app/src/syspart.cpp:927).
- Actual: The thread-entry guard prevents main's callsite from being queued (analysis/app/src/syspart.cpp:935; analysis/app/src/syspart.cpp:937). The exact reported result cannot be established from source alone: findFunctionsReachable also exits its false path without a return statement (analysis/app/src/syspart.cpp:862; analysis/app/src/syspart.cpp:864).
- Evidence: analysis/app/src/ipcallgraph.cpp:891 — a direct call to worker is recognized; analysis/app/src/ipcallgraph.cpp:246 — its target edge is inserted; analysis/app/src/ipcallgraph.cpp:247 — main is recorded as worker's parent. analysis/app/src/syspart.cpp:1180 — pthread_create is recognized; analysis/app/src/syspart.cpp:1191 — worker can be recorded as a thread entry. analysis/app/src/syspart.cpp:924 — mode 11 first checks reachability within worker; analysis/app/src/syspart.cpp:935 — the thread-entry check skips worker's parent search; analysis/app/src/syspart.cpp:937 — main's normal callsite is therefore never read. analysis/app/src/syspart.cpp:780 — a caller search would enter successor blocks; analysis/app/src/syspart.cpp:804 — it would recognize a direct edge to func2.
- Assessment: Tiny test: main calls pthread_create with worker, calls worker normally, then calls func2 in a successor block; worker returns. Query the return instruction with mode 11 as addr,worker,func2. Expected output is "func2 is reachable from worker" because mode 11 checks callers after a returning function (README.md:159; analysis/app/src/syspart.cpp:933; analysis/app/src/syspart.cpp:937). This is a source-supported finding; no runtime output was observed.

### Mode 11 analyzes every thread start before checking an immediate answer

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspart.cpp:897`
- Invariant: A reachability answer found in the first forward search does not require thread-start classification, which is used only when walking callers (analysis/app/src/syspart.cpp:924; analysis/app/src/syspart.cpp:925; analysis/app/src/syspart.cpp:935).
- Mechanism: Mode 11 calls getThreadStartFunction before its first reachability check (analysis/app/src/syspart.cpp:897; analysis/app/src/syspart.cpp:924). That function scans graph nodes and callsite targets; each matching pthread_create site constructs a CFG and use-def analysis of its caller (analysis/app/src/syspart.cpp:1169; analysis/app/src/syspart.cpp:1174; analysis/app/src/syspart.cpp:1180; analysis/app/src/syspart.cpp:1136; analysis/app/src/syspart.cpp:1142).
- Reproducer: For a graph with P pthread_create sites, query an address whose successor block directly calls func2. The answer is found in the first scan, yet thread discovery first performs P caller analyses (analysis/app/src/syspart.cpp:897; analysis/app/src/syspart.cpp:1184; analysis/app/src/syspart.cpp:804; analysis/app/src/syspart.cpp:925). This is a bounded source cost argument.
- Expected: Defer getThreadStartFunction until a failed forward search reaches the caller-walk decision (analysis/app/src/syspart.cpp:924; analysis/app/src/syspart.cpp:933; analysis/app/src/syspart.cpp:935).
- Actual: For each matching pthread_create callsite entry, discovery invokes caller use-def analysis before an immediate reachable result can be returned (analysis/app/src/syspart.cpp:897; analysis/app/src/syspart.cpp:1180; analysis/app/src/syspart.cpp:1206; analysis/app/src/syspart.cpp:1142; analysis/app/src/syspart.cpp:925).
- Evidence: analysis/app/src/syspart.cpp:897 — classifies thread starts before the loop; analysis/app/src/syspart.cpp:1169 — scans call-graph nodes; analysis/app/src/syspart.cpp:1174 — scans direct callsite targets; analysis/app/src/syspart.cpp:1180 — invokes find_thread_function for a pthread_create match; analysis/app/src/syspart.cpp:1206 — does the same for indirect matches; analysis/app/src/syspart.cpp:1136 — constructs a caller CFG and use-def objects; analysis/app/src/syspart.cpp:1142 — runs the analysis; analysis/app/src/syspart.cpp:924 — only then searches for reachability; analysis/app/src/syspart.cpp:804 — a direct target call returns true; analysis/app/src/syspart.cpp:925 — success ends the caller walk; analysis/app/src/syspart.cpp:935 — thread-start classification is consulted only after a failed search.
- Assessment: The node-existence guards can return before thread discovery, but a valid mode 11 query reaches getThreadStartFunction before its first reachability search (analysis/app/src/syspart.cpp:885; analysis/app/src/syspart.cpp:891; analysis/app/src/syspart.cpp:897; analysis/app/src/syspart.cpp:924). Tiny test case: put a direct call to target in the successor block of an address in start, and a separate pthread_create call in a function present in the call graph. Query mode 11 with that address, start, and target (analysis/app/src/testSyspart.cpp:325; analysis/app/src/testSyspart.cpp:364). The expected result line is "target is reachable from start" (analysis/app/src/syspart.cpp:804; analysis/app/src/syspart.cpp:927). The source shows thread discovery runs first; no timing or runtime output was captured (analysis/app/src/syspart.cpp:897).

<!-- harness:logic:mode-11:end -->

<!-- harness:logic:mode-12:start -->
## Harness logic audit — mode 12

Dispatcher and modules: README.md, analysis/app/README.md, analysis/app/src/testSyspart.cpp, analysis/app/src/syspart.cpp, analysis/app/src/ipcallgraph.cpp, analysis/app/src/ipcallgraph.h

### A PLT-linked global symbol adds a null function root

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:2936`
- Invariant: A resolved global symbol must add its PLT target as a valid function root (analysis/app/src/syspart.cpp:2931-2961).
- Mechanism: The PLT branch pushes `global_fun`, which is null when the preceding Function cast fails, instead of `plt_target`; `addFunctionRoot` then passes that pointer to dataflow analysis (analysis/app/src/syspart.cpp:2925-2937; analysis/app/src/ipcallgraph.cpp:155-165).
- Reproducer: Source-bounded case: a named global contains a data link to a PLT trampoline whose target is a Function (analysis/app/src/syspart.cpp:2906-2919,2931-2937).
- Expected: Queue the PLT target as a valid root and reach "Generation done" (analysis/app/src/syspart.cpp:2933; analysis/app/src/syspart.cpp:2961; analysis/app/src/syspart.cpp:2969).
- Actual: The source queues null and passes it toward a Function dereference before generation; a runtime failure or its output was not observed (analysis/app/src/syspart.cpp:2925; analysis/app/src/syspart.cpp:2936; analysis/app/src/ipcallgraph.cpp:164; analysis/tools/egalito/src/analysis/controlflow.cpp:55).
- Evidence: analysis/app/src/syspart.cpp:2890 — a same-named Function bypasses the global search; analysis/app/src/syspart.cpp:2925 — the failed Function cast leaves global_fun null; analysis/app/src/syspart.cpp:2931 — the PLT branch requires a Function target; analysis/app/src/syspart.cpp:2936 — it pushes global_fun instead of plt_target; analysis/app/src/syspart.cpp:2959 — the queued pointer becomes a function root; analysis/app/src/ipcallgraph.cpp:155 — addFunctionRoot has no null guard; analysis/app/src/ipcallgraph.cpp:164 — it requests dataflow for that pointer; analysis/tools/egalito/src/analysis/dataflow.cpp:29 — dataflow constructs a CFG; analysis/tools/egalito/src/analysis/controlflow.cpp:55 — CFG construction dereferences the Function; analysis/app/src/syspart.cpp:3030 — the later lookup uses plt_target, but follows the earlier root construction.
- Assessment: A tiny test fixture would give mode -a 12 a named global whose data link points to a PLT trampoline targeting a Function, with no same-named Function found in the initial lookup (analysis/app/src/testSyspart.cpp:367; analysis/app/src/syspart.cpp:2890; analysis/app/src/syspart.cpp:2900; analysis/app/src/syspart.cpp:2906; analysis/app/src/syspart.cpp:2931). Expected output includes "Link to PLT <target>" followed by "Generation done", with the target available for syscall analysis (analysis/app/src/syspart.cpp:2935; analysis/app/src/syspart.cpp:2966; analysis/app/src/syspart.cpp:2969; analysis/app/src/syspart.cpp:3103). The source instead queues a null root and passes it to CFG construction before generation; no runtime output was captured (analysis/app/src/syspart.cpp:2925; analysis/app/src/syspart.cpp:2936; analysis/app/src/syspart.cpp:2961; analysis/app/src/ipcallgraph.cpp:155; analysis/app/src/ipcallgraph.cpp:164; analysis/tools/egalito/src/analysis/controlflow.cpp:55).

### Late indirect targets lack reverse edges for syscall propagation

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:3096`
- Invariant: Every added caller-to-target edge must also appear in the target's parent set before backward syscall propagation (analysis/app/src/ipcallgraph.cpp:246-247; analysis/app/src/syspart.cpp:434-448).
- Mechanism: Mode 12 adds `moreAT` targets to indirect child sets after graph generation, but `updateIndirectChildren` only replaces the child vector and does not insert parents (analysis/app/src/syspart.cpp:3063-3068,3076-3096; analysis/app/src/ipcallgraph.h:215-219).
- Reproducer: Source-bounded graph: caller has one indirect site, newly loaded target invokes syscall 39, and `forwardDataFlow` returns false. The target enters `moreAT` after the initial indirect-edge pass (analysis/app/src/syspart.cpp:3062-3068; analysis/app/src/ipcallgraph.cpp:1835-1836).
- Expected: For the stated test case, the caller's derived syscall set contains 39 (analysis/app/src/syspart.cpp:434-448).
- Actual: Source prediction: the caller gains the target as an indirect child but is not reached from that target during backward propagation, so its derived set omits 39 (analysis/app/src/syspart.cpp:3091-3105,434-448; analysis/app/src/ipcallgraph.h:215-219).
- Evidence: analysis/app/src/testSyspart.cpp:367-378 — mode 12 calls getSyscallsFromDlsym; analysis/app/src/syspart.cpp:2964-2967 — graph generation precedes the late symbol pass; analysis/app/src/ipcallgraph.cpp:1832-1836,713-715 — initial indirect edges and their reverse parents use the then-current target set; analysis/app/src/syspart.cpp:3054-3068 — missing nodes are skipped, and a false data-flow result adds an existing node to moreAT; analysis/app/src/ipcallgraph.cpp:250-275 — addATFunction records an address-taken function but adds no parent; analysis/app/src/syspart.cpp:3076-3096; analysis/app/src/ipcallgraph.h:215-219 — moreAT is merged into indirect children without adding parents; analysis/app/src/syspart.cpp:3103-3105,434-448; analysis/app/src/ipcallgraph.h:177-185 — subsequent syscall propagation traverses parents.
- Assessment: Tiny test case: a caller has one indirect call site; a target added through the mode 12 symbol input invokes syscall 39; forwardDataFlow returns false; and the target had no earlier edge from the caller. Expected output includes `Derived : caller : getpid` and 39 in the caller's numeric total. The source predicts both will omit it because propagation walks target parents, while the late update changes only caller children (analysis/app/src/syspart.cpp:3062-3068,3091-3105,434-448,695-713; analysis/app/src/ipcallgraph.h:215-219). No binary was run.

### NSS edges are added before their caller nodes exist

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:2884`
- Invariant: NSS expansion needs the external libc function's callgraph node and parent callsites (analysis/app/src/ipcallgraph.cpp:1963-1975).
- Mechanism: Mode 12 calls `addNssEdges` before `generate`; direct traversal creates caller edges later, and mode 12 does not call `addNssEdges` again (analysis/app/src/syspart.cpp:2882-2884,2965-2966,3101-3111; analysis/app/src/ipcallgraph.cpp:1770-1775).
- Reproducer: Source-bounded case: a root calls an NSS-using libc function that has no graph node before direct traversal (analysis/app/src/ipcallgraph.cpp:1963-1968,1770-1775).
- Expected: For the stated fixture, `Derived : main : openat` appears (analysis/app/src/syspart.cpp:405-449,695-699).
- Actual: For the stated fixture, the early call adds no NSS backend edge, so that derived entry is predicted to be absent (analysis/app/src/ipcallgraph.cpp:1963-1980; analysis/app/src/syspart.cpp:2884,2966,3103-3109). No runtime output was observed.
- Evidence: analysis/app/src/testSyspart.cpp:367-377 — mode 12 calls getSyscallsFromDlsym; analysis/app/src/syspart.cpp:2878-2884 — resolveNss and addNssEdges run before generate; analysis/app/src/ipcallgraph.cpp:1963-1980 — addNssEdges silently skips a missing node and requires its parent callsites; analysis/app/src/syspart.cpp:2959-2966 — generate runs later; analysis/app/src/ipcallgraph.cpp:1770-1775,891-905 — direct traversal creates caller edges; analysis/app/src/syspart.cpp:3101-3109 — syscall propagation and output follow without another addNssEdges call. Other paths place addNssEdges after generate (analysis/app/src/syspart.cpp:1248-1255).
- Assessment: The guard does not refute the candidate: resolveNss creates roots for resolved backend functions, but does not add a node or caller edge for the NSS-using libc function (analysis/app/src/ipcallgraph.cpp:1937-1943). setRoot creates only the start node, and getNode returns NULL when the libc function has no matching node (analysis/app/src/ipcallgraph.cpp:169-178; analysis/app/src/ipcallgraph.h:355-371). Tiny test: have main call an NSS-using libc function whose resolved backend is the only path to openat. Expected output after syscall propagation includes `Derived : main : openat`; with the early expansion, that entry is absent (analysis/app/src/syspart.cpp:405-449,695-707). This is a source-supported prediction; no runtime output was observed.

### An incomplete dlsym record reaches unchecked address conversion

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:2813`
- Invariant: A usable record supplies an address before hexadecimal conversion (analysis/app/src/syspart.cpp:2793-2807,2813).
- Mechanism: The parser never checks the number of fields; a line containing only a caller name leaves `addr` empty and reaches `stol` (analysis/app/src/syspart.cpp:2795-2813).
- Reproducer: Source-bounded input file containing one line, `main` (analysis/app/src/syspart.cpp:2791-2813).
- Expected: Reject or skip the incomplete record before address conversion (analysis/app/src/syspart.cpp:2793-2813).
- Actual: The source calls stol with an empty addr; its runtime outcome was not observed (analysis/app/src/syspart.cpp:2795-2813).
- Evidence: analysis/app/src/testSyspart.cpp:367-378 — mode 12 passes the supplied filename to getSyscallsFromDlsym. analysis/app/src/syspart.cpp:2786-2795 — the function reads each line and initializes addr empty. analysis/app/src/syspart.cpp:2796-2809 — `main` fills fn but supplies no address. analysis/app/src/syspart.cpp:2810-2813 — the UNKNOWN-symbol guard does not apply, so empty addr reaches stol.
- Assessment: Tiny test: pass a file containing only `main\n` to mode 12. Expected output: a diagnostic such as `Malformed dlsym record: missing address`, followed by skipping the record. The source has no field-count guard before conversion (analysis/app/src/syspart.cpp:2791-2813). This is code-supported; no runtime output was observed.

### Mode 12 builds an unused use-def analysis for every function

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspart.cpp:2783`
- Invariant: Analysis work should serve record processing or callgraph generation (analysis/app/src/syspart.cpp:2778-2786,2966).
- Mechanism: A local `DataFlow df` analyzes every existing function before opening the record file, but mode 12 never reads that local object; the callgraph obtains working sets through its own dataflow member (analysis/app/src/syspart.cpp:2778-2786; analysis/app/src/ipcallgraph.cpp:163-165,1333-1339).
- Reproducer: Bounded cost: with F parsed functions and an empty or unreadable record file, this loop still constructs and analyzes F CFGs before file validation (analysis/app/src/syspart.cpp:2778-2789,2872-2875; analysis/tools/egalito/src/analysis/dataflow.cpp:13-26).
- Expected: No local use-def analysis without a consumer (analysis/app/src/syspart.cpp:2778-2786).
- Actual: The source performs one avoidable use-def analysis per parsed function before file validation; time and memory cost were not measured (analysis/app/src/syspart.cpp:2778-2789; analysis/tools/egalito/src/analysis/dataflow.cpp:13-26).
- Evidence: analysis/app/src/syspart.cpp:2778-2786 — local DataFlow analyzes every parsed function before opening the record file; analysis/app/src/syspart.cpp:2789-2875 — file validation and record processing occur afterward; analysis/app/src/syspart.cpp:2778-2783 — the local df has no use beyond this loop; analysis/app/src/ipcallgraph.h:331 — the callgraph owns a separate DataFlow; analysis/app/src/ipcallgraph.cpp:163-176,1333-1336 — callgraph operations obtain working sets through that member; analysis/tools/egalito/src/analysis/dataflow.cpp:13-26 — each eager call builds a CFG and runs use-def analysis.
- Assessment: Mode 12 calls getSyscallsFromDlsym after checking that a filename argument is present, but does not check whether the file can be opened (analysis/app/src/testSyspart.cpp:367-377). Tiny test: use a binary with one parsed function and pass a nonexistent record file. Expected output includes `Error file`; an instrumented call count should show zero local use-def analyses before that message. The source instead calls addUseDefFor once before opening the file (analysis/app/src/syspart.cpp:2778-2789,2872-2875). No runtime output was captured.

### Each symbol is resolved twice around graph generation

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspart.cpp:2986`
- Invariant: A record's resolved functions should be reusable when processing that same record after graph generation (analysis/app/src/syspart.cpp:2885-2962,2975-3052).
- Mechanism: The first pass searches functions and, if needed, global data for every record; the second pass repeats the same search instead of retaining `sym_funcs` in the record (analysis/app/src/syspart.cpp:2889-2952,2984-3046).
- Reproducer: Bounded cost: R records naming globals in a module with G inspected global/data entries cause up to two R-by-G searches, including repeated scans for identical symbol-library pairs (analysis/app/src/syspart.cpp:2902-2952,2997-3046).
- Expected: Retain each record’s resolved targets for use after graph generation, subject to correcting the PLT target discrepancy (analysis/app/src/syspart.cpp:2959-2966,2931-2938,3025-3032,3052-3062).
- Actual: Eligible records incur two function searches and, when no function name matches, two global scans. This is a source-supported cost bound, not a measured runtime result (analysis/app/src/syspart.cpp:2889-2952,2977-3046).
- Evidence: analysis/app/src/testSyspart.cpp:367-378 — mode 12 calls getSyscallsFromDlsym; analysis/app/src/syspart.cpp:2810-2813,2839-2869 — UNKNOWN symbols and missing callers are excluded, and accepted records are stored; analysis/app/src/syspart.cpp:2885-2966 — first lookup adds resolved functions as graph roots before generation; analysis/app/src/syspart.cpp:2975-3054 — a caller-node guard precedes an independent lookup after generation.
- Assessment: For a record whose caller has a graph node, both passes search its module for the symbol; if no function matches, both scan the module’s globals (analysis/app/src/syspart.cpp:2885-2952,2975-3046). The record stores the module and symbol but no resolved targets (analysis/app/src/syspart.cpp:2768-2776,2866-2869). A tiny test would use one valid caller and callsite with one library function symbol; expected output includes one `Value <symbol> <library>`, then `Going to generate` and `Generation done`, while a lookup counter would report two function searches (analysis/app/src/syspart.cpp:2885-2899,2965-2969,2975-2994). Reuse needs care for PLT targets: the first pass appends `global_fun` where the second appends `plt_target` (analysis/app/src/syspart.cpp:2931-2938,3025-3032).

### A function can print another module's syscall summary

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:167`
- Invariant: Each function printed by mode 12 must use its own SysNode (analysis/app/src/syspart.cpp:3107-3109,678-684).
- Mechanism: getSysNode scans syscall_mapping and accepts a matching name and address before it reaches an exact pointer match later in the map (analysis/app/src/syspart.cpp:161-174). Direct syscall extraction creates a separate SysNode for each graph function (analysis/app/src/syspart.cpp:280-303).
- Reproducer: Source-bounded case: two graph functions in different modules have the same name and address but different syscalls; the other function's mapping entry is visited first (analysis/app/src/syspart.cpp:161-174,280-303).
- Expected: B's summary uses B's direct and derived syscall sets (analysis/app/src/syspart.cpp:284-321,684-710).
- Actual: If A's mapping entry is visited first, B's summary uses A's SysNode and syscall sets; this is a source prediction (analysis/app/src/syspart.cpp:161-172,678-710).
- Evidence: analysis/app/src/testSyspart.cpp:367-378 — -a 12 calls getSyscallsFromDlsym; analysis/app/src/syspart.cpp:3103-3109 — that path extracts syscalls and prints every graph function; analysis/app/src/syspart.cpp:284-321 — extraction creates a separate SysNode for each graph function; analysis/app/src/syspart.cpp:161-173 — getSysNode can return an earlier name-and-address match before reaching the exact pointer; analysis/app/src/syspart.cpp:678-710 — the returned node supplies the printed sets. The graph retains functions by pointer, and its fallback lookup checks module identity, so neither guards this lookup (analysis/app/src/ipcallgraph.h:340,355-371).
- Assessment: A tiny test case would place distinct graph functions named foo at address 0x1000 in modules A and B, with A directly invoking read (0) and B directly invoking write (1); arrange for A's syscall_mapping entry to be visited first (analysis/app/src/ipcallgraph.h:340; analysis/app/src/syspart.cpp:284-321). The expected B summary is Direct: foo: write, Total: foo: write, followed by 1,; the source predicts read and 0, instead (analysis/app/src/syspart.cpp:90-92,161-172,684-712). No runtime output was observed.

### Printing all nodes repeatedly scans the entire syscall map

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspart.cpp:163`
- Invariant: Printing N graph nodes should not require a fresh linear search through N syscall mappings for each node (analysis/app/src/syspart.cpp:3107-3109,298-303).
- Mechanism: Mode 12 calls getSyscallInfo for every graph node; each call invokes getSysNode, which iterates syscall_mapping instead of using its IPCallGraphNode key (analysis/app/src/syspart.cpp:3107-3109,678-684,161-174,301-303).
- Reproducer: Bounded cost: with N graph nodes and one mapping per node, the N lookups collectively inspect Θ(N²) entries; init and fini lookups inside each print add further scans (analysis/app/src/syspart.cpp:161-174,639-668,715-732,3107-3109).
- Expected: Use the existing IPCallGraphNode key to retrieve each node's mapping while printing (analysis/app/src/syspart.cpp:282-287,321,3107-3109).
- Actual: The source performs a linear mapping scan for each printed node, yielding quadratic lookup work when all N nodes have distinct mappings; runtime cost was not measured (analysis/app/src/syspart.cpp:161-174,282-294,321,3107-3109).
- Evidence: analysis/app/src/testSyspart.cpp:367-378 — mode 12 calls getSyscallsFromDlsym after the filename guard; analysis/app/src/syspart.cpp:3102-3109 — it populates mappings and prints every graph node; analysis/app/src/syspart.cpp:282-294,321 — each graph node receives a mapping keyed by its IPCallGraphNode; analysis/app/src/syspart.cpp:676-680,161-174 — each print scans that mapping to find its Function; analysis/app/src/syspart.cpp:715-732,636-673 — each print also requests fini and init syscall sets, whose function lookups use the same scan.
- Assessment: Mode 12 requires a comma-separated filename, but after that guard its printing loop runs without a per-node lookup guard (analysis/app/src/testSyspart.cpp:367-378; analysis/app/src/syspart.cpp:3101-3110). For a tiny test, use a graph with three distinct functions and no init, fini, or syscall entries. Expected output includes one “Total syscalls of <function> : 0” line for each function (analysis/app/src/syspart.cpp:676-684,3107-3109). The three lookups would inspect 1+2+3=6 mapping entries in some order, versus three direct key lookups; this count follows from the insertion and scan code, and has not been measured (analysis/app/src/syspart.cpp:282-294,321,161-174).

### Each dlsym record rescans every loaded instruction

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspart.cpp:2817`
- Invariant: Matching R records to parsed callsites should reuse an address lookup instead of traversing the program for every record (analysis/app/src/syspart.cpp:2813-2835).
- Mechanism: For each record, mode 12 traverses all modules and functions, then every block and instruction of each function whose name matches the recorded caller. A match does not stop the outer traversals (analysis/app/src/syspart.cpp:2817-2835).
- Reproducer: Bounded cost: R records naming one large caller with I instructions cause Θ(R×I) instruction visits in that caller, including when every record has an unmatched address (analysis/app/src/syspart.cpp:2791-2793,2817-2839).
- Expected: Reuse a lookup keyed by caller name and instruction address, so repeated records resolve without repeating the instruction scan (analysis/app/src/syspart.cpp:2813-2838).
- Actual: For R records naming one I-instruction caller, the source implies Θ(R×I) instruction visits when their addresses are unmatched; runtime cost was not measured (analysis/app/src/syspart.cpp:2791-2813,2817-2843).
- Evidence: analysis/app/src/testSyspart.cpp:367-377 — mode 12 requires a filename argument and calls getSyscallsFromDlsym; analysis/app/src/syspart.cpp:2778-2785 — use-def setup runs before record processing; analysis/app/src/syspart.cpp:2786-2813 — an open file is read line by line, with UNKNOWN symbols skipped; analysis/app/src/syspart.cpp:2817-2838 — each remaining record scans modules and functions, then instructions in every same-named function; the match break exits only the innermost instruction loop; analysis/app/src/syspart.cpp:2839-2843 — unmatched addresses produce a diagnostic.
- Assessment: Tiny test case: use a parsed caller named main with three instructions, none at 0xdeadbeef, and a mode 12 input file containing two identical lines: `main deadbeef foo /tmp/libfoo.so`. Expect two `Function main with addr deadbeef not found` diagnostics. The source implies six visits to main’s instructions: each non-UNKNOWN line enters the search, and an unmatched address exhausts its instruction loops (analysis/app/src/syspart.cpp:2791-2813,2817-2843). This is a source-supported cost prediction; no runtime output was captured. The title overstates the scope: instruction traversal is limited to functions whose name matches the record, although every module and function is considered (analysis/app/src/syspart.cpp:2817-2825).

<!-- harness:logic:mode-12:end -->

<!-- harness:logic:mode-13:start -->
## Harness logic audit — mode 13

Dispatcher and modules: analysis/app/src/testSyspart.cpp, analysis/app/src/syspart.cpp, analysis/app/src/nonreturnAnalysis.cpp, analysis/app/src/nonreturnAnalysis.h, analysis/tools/egalito/src/analysis/controlflow.cpp, analysis/tools/egalito/src/analysis/controlflow.h, analysis/tools/egalito/src/chunk/function.h, analysis/tools/egalito/src/instr/linked-x86_64.h

### A conditional jump through an unresolved PLT can hide a returning path

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/nonreturnAnalysis.cpp:84`
- Invariant: A function must remain classified as returning when any reachable branch returns [analysis/app/src/nonreturnAnalysis.cpp:94-106].
- Mechanism: An unresolved PLT link named abort is marked nonreturning [analysis/app/src/nonreturnAnalysis.cpp:18-25]. Its target is a PLT trampoline, so the Function-target branch does not stop the scan; the instruction then causes an immediate return of 1, before the CFG fallthrough is visited [analysis/tools/egalito/src/chunk/link.cpp:26-28] [analysis/app/src/nonreturnAnalysis.cpp:75-87]. The CFG does represent fallthrough for a conditional jump [analysis/tools/egalito/src/analysis/controlflow.cpp:72-80,200-212].
- Reproducer: Source-bounded fixture: a conditional jump through an unresolved PLT entry named abort, with its untaken branch reaching ret. CollapsePLTPass preserves a PLT link when its trampoline has no target [analysis/tools/egalito/src/pass/collapseplt.cpp:71-107]. No binary was run.
- Expected: For the proposed isolated case, `Before: N After: N` [analysis/app/src/nonreturnAnalysis.cpp:94-106] [analysis/app/src/testSyspart.cpp:380-386].
- Actual: Source-predicted `Before: N After: N+1`; no runtime output was observed [analysis/app/src/nonreturnAnalysis.cpp:84-87] [analysis/app/src/nonreturnAnalysis.cpp:142-146] [analysis/app/src/testSyspart.cpp:380-386].
- Evidence: Mode 13 invokes NonReturnAnalysis after PLT resolution and collapse [analysis/app/src/testSyspart.cpp:162-166] [analysis/app/src/testSyspart.cpp:380-386]. A direct control flow instruction can receive a PLTLink [analysis/tools/egalito/src/pass/externalcalls.cpp:8-23]. An unresolved PLTLink targets its trampoline, so the Function-target guard does not apply [analysis/tools/egalito/src/chunk/link.cpp:26-28] [analysis/app/src/nonreturnAnalysis.cpp:75-82]. The name `abort` makes hasLinkToNeverReturn true; setNonreturn makes returns false, causing an immediate return of 1 [analysis/app/src/nonreturnAnalysis.cpp:7-8] [analysis/app/src/nonreturnAnalysis.cpp:18-25] [analysis/app/src/nonreturnAnalysis.cpp:71-87] [analysis/tools/egalito/src/instr/linked-x86_64.h:98-99]. The CFG adds fallthrough for a conditional jump, but that immediate return skips the forward-link scan; a reached terminal ret block would yield 0 [analysis/tools/egalito/src/analysis/controlflow.cpp:72-80] [analysis/tools/egalito/src/analysis/controlflow.cpp:189-212] [analysis/app/src/nonreturnAnalysis.cpp:91-106]. A result of 1 marks the function nonreturning, and mode 13 counts that flag [analysis/app/src/nonreturnAnalysis.cpp:142-146] [analysis/app/src/syspart.cpp:3113-3126].
- Assessment: A tiny test case is a function whose final branch is `jne abort@PLT`, with `ret` on the untaken path, and whose abort PLT trampoline remains unresolved. If this is the only function whose classification changes, mode 13 should print `Before: N After: N`; the source predicts `Before: N After: N+1`. The conditional case is narrower than an ordinary resolved PLT call: resolution or collapse can replace the PLT link, but collapse preserves it when the trampoline has no target [analysis/tools/egalito/src/pass/resolveplt.cpp:22-32] [analysis/tools/egalito/src/pass/collapseplt.cpp:95-107]. No binary was run.

### Trap-terminated functions are counted as returning

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/nonreturnAnalysis.cpp:105`
- Invariant: A path ending in a trap with no normal return should not be treated like a return instruction [analysis/tools/egalito/src/pass/fallthrough.cpp:90-98] [analysis/app/src/nonreturnAnalysis.cpp:105-106].
- Mechanism: The parser treats x86 UD2 as an isolated instruction, and the fallthrough pass explicitly treats UD2 as terminating [analysis/tools/egalito/src/disasm/makesemantic.cpp:22-48,105-109] [analysis/tools/egalito/src/pass/fallthrough.cpp:90-98]. NonReturnAnalysis checks only ControlFlowInstruction semantics, then assigns 0 to any CFG node without forward links [analysis/app/src/nonreturnAnalysis.cpp:66-89,105-106].
- Reproducer: Source-bounded fixture: a one-block function ending in UD2. Its CFG has no successor because it is the last block [analysis/tools/egalito/src/analysis/controlflow.cpp:195-212]. No binary was run.
- Expected: The UD2-only function contributes one additional nonreturning function to the mode 13 after count [analysis/tools/egalito/src/pass/fallthrough.cpp:90-98] [analysis/app/src/testSyspart.cpp:380-386].
- Actual: The source predicts no increase from that function: its terminal node evaluates to 0, leaving its return flag set [analysis/app/src/nonreturnAnalysis.cpp:105-109,143-149] [analysis/tools/egalito/src/chunk/function.h:48-49].
- Evidence: analysis/tools/egalito/src/disasm/makesemantic.cpp:22-48,105-108 — x86 semantic construction has no UD2 case; analysis/tools/egalito/src/disasm/disassemble.cpp:255-271 — unmatched instructions become IsolatedInstruction; analysis/tools/egalito/src/pass/fallthrough.cpp:90-98 — UD2 prevents function fallthrough; analysis/tools/egalito/src/analysis/controlflow.cpp:195-212 — an isolated final instruction gets no successor when its block is last; analysis/app/src/nonreturnAnalysis.cpp:66-89,91-109 — only ControlFlowInstruction can trigger the early nonreturn result, and a node with no forward links returns 0; analysis/app/src/nonreturnAnalysis.cpp:134-149 — only result 1 marks the function nonreturning; analysis/app/src/syspart.cpp:3113-3126 — the count uses that flag. The parser's earlier nonreturn pass applies the same terminal-node rule [analysis/tools/egalito/src/conductor/passes.cpp:71-87] [analysis/tools/egalito/src/pass/nonreturn.cpp:123-165], so it does not refute the candidate.
- Assessment: Tiny test case: an x86-64 ELF function whose sole instruction is `ud2`. For mode `-a 13`, the expected output is `<file> Before: N After: N+1` if this function is newly recognized as nonreturning; the source predicts `<file> Before: N After: N` for this function. This is a source-supported prediction, not observed output [analysis/app/src/testSyspart.cpp:380-386].

### Every scanned CFG is copied for an emptiness check

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/nonreturnAnalysis.cpp:135`
- Invariant: Checking whether a CFG is empty needs only its node count [analysis/tools/egalito/src/analysis/controlflow.h:75-79].
- Mechanism: Each scan calls getGraph().size(); getGraph returns the entire node vector by value [analysis/app/src/nonreturnAnalysis.cpp:134-135] [analysis/tools/egalito/src/analysis/controlflow.cpp:48-50].
- Reproducer: Bounded cost: for a returning function with V blocks and E CFG links, each fixed-point pass constructs its CFG and then makes an additional O(V+E) vector copy for this check [analysis/app/src/nonreturnAnalysis.cpp:115-135,152] [analysis/tools/egalito/src/analysis/controlflow.cpp:53-64] [analysis/tools/egalito/src/analysis/controlflow.h:69-79]. No cost was measured.
- Expected: Use getCount() for the emptiness check, avoiding a node-vector copy [analysis/tools/egalito/src/analysis/controlflow.h:75-79].
- Actual: The check copies the graph's nodes and their link-reference vectors, adding O(V+E) source-implied work per scanned CFG; this cost was not measured [analysis/app/src/nonreturnAnalysis.cpp:134-135] [analysis/tools/egalito/src/analysis/controlflow.cpp:48-50] [analysis/tools/egalito/src/analysis/controlflow.h:34-43,69-79] [analysis/tools/egalito/src/analysis/graph.h:14-25].
- Evidence: analysis/app/src/testSyspart.cpp:380-386 — mode 13 calls NonReturnAnalysis::run; analysis/app/src/nonreturnAnalysis.cpp:120-135 — the loop skips functions whose returns() is false, constructs a CFG for each remaining function, then calls getGraph().size(); analysis/tools/egalito/src/analysis/controlflow.cpp:30-32,48-64 — construction fills the graph and getGraph returns its vector by value; analysis/tools/egalito/src/analysis/graph.h:14-25 — copied nodes contain vectors of link references; analysis/tools/egalito/src/analysis/controlflow.h:75-79 — getCount directly returns graph.size().
- Assessment: The guard skips functions already marked nonreturning, but every still-returning function reaches the copy-producing check on each fixed-point pass [analysis/app/src/nonreturnAnalysis.cpp:115-135,152]. Tiny proposed test: build a one-block returning function, reset an instrumented ControlFlowNode copy counter immediately before the check, then print getGraph().size(), getCount(), and the counter; expected output is "1 1 1" [analysis/app/src/nonreturnAnalysis.cpp:134-135] [analysis/tools/egalito/src/analysis/controlflow.h:69-79] [analysis/tools/egalito/src/analysis/controlflow.cpp:48-50]. The test was not run.

### Path traversal copies the visited set at every CFG edge

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/nonreturnAnalysis.cpp:50`
- Invariant: A traversal of a linear CFG should require work proportional to its blocks and edges, apart from instruction scanning [analysis/app/src/nonreturnAnalysis.cpp:66-100].
- Mechanism: The visited set is passed by value, and each successor call copies the current path's set [analysis/app/src/nonreturnAnalysis.cpp:50,64,94-100].
- Reproducer: Bounded cost: a chain of N blocks makes copies of sets with sizes 0 through N−1, yielding Θ(N²) copied set elements before instruction costs [analysis/app/src/nonreturnAnalysis.cpp:50,64,94-100]. Mode 13 invokes this traversal for each eligible function [analysis/app/src/testSyspart.cpp:380-385] [analysis/app/src/nonreturnAnalysis.cpp:122-142]. No cost was measured.
- Expected: Linear visited-state work for a linear CFG, apart from instruction scanning [analysis/app/src/nonreturnAnalysis.cpp:59-64,94-100].
- Actual: Source-supported Θ(N²) visited-set copying on that chain; runtime cost is unconfirmed [analysis/app/src/nonreturnAnalysis.cpp:50,64,100].
- Evidence: analysis/app/src/testSyspart.cpp:380-386 — mode 13 calls run; analysis/app/src/nonreturnAnalysis.cpp:122-142 — run traverses each returning function with a nonempty CFG and clears the cache; analysis/app/src/nonreturnAnalysis.cpp:54-64 — cache and cycle guards precede insertion into a by-value set; analysis/app/src/nonreturnAnalysis.cpp:94-100 — each successor call copies that set. On an N-block chain, the copied set sizes are 1 through N−1, totaling Θ(N²) elements [analysis/app/src/nonreturnAnalysis.cpp:50,64,94-100].
- Assessment: The guards do not refute the candidate for a linear CFG: each block is new to both the path and the per-function cache, and ordinary jumps can reach the successor traversal [analysis/app/src/nonreturnAnalysis.cpp:54-64] [analysis/app/src/nonreturnAnalysis.cpp:66-100] [analysis/tools/egalito/src/instr/linked-x86_64.h:72-75] [analysis/tools/egalito/src/instr/linked-x86_64.h:98-99]. Tiny proposed test: a returning function with B0 jumping to B1, B1 jumping to B2, and B2 returning. Instrument recursive-entry set copies; expected output is copy sizes 1 and 2 (three elements total) and traversal result 0 [analysis/app/src/nonreturnAnalysis.cpp:50-64] [analysis/app/src/nonreturnAnalysis.cpp:94-109]. No cost was measured.

### A redundant membership scan runs for returning call targets

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/nonreturnAnalysis.cpp:32`
- Invariant: Every function inserted into nonReturnList is already marked nonreturning [analysis/app/src/nonreturnAnalysis.cpp:124-129,143-146].
- Mechanism: The preceding returns() check handles every such target, so inList cannot succeed here. It nevertheless uses a linear std::find over nonReturnList [analysis/app/src/nonreturnAnalysis.cpp:28-32,41-47].
- Reproducer: Bounded cost: with K functions in nonReturnList and E visited control-flow instructions targeting returning functions, this adds O(EK) membership work per fixed-point pass [analysis/app/src/nonreturnAnalysis.cpp:28-32,41-43,115-152]. No workload was run.
- Expected: Skip inList(target) while preserving classification [analysis/app/src/nonreturnAnalysis.cpp:31-34,124-129,143-146].
- Actual: Each visited linked Function target that passes returns() incurs a full scan of K nonreturn-list entries, giving O(EK) membership work per pass for E such visits [analysis/app/src/nonreturnAnalysis.cpp:28-32,41-47,66-71,115-152].
- Evidence: Mode -a 13 calls run() [analysis/app/src/testSyspart.cpp:380-386]. Its first insertion path requires !func->returns(); its second calls setNonreturn() before insertion [analysis/app/src/nonreturnAnalysis.cpp:124-129,143-146]. returns() reads that flag [analysis/tools/egalito/src/chunk/function.h:48-49]. For a linked Function target, hasLinkToNeverReturn() checks !target->returns() before calling inList(), so the scan cannot find a member under those insertion paths [analysis/app/src/nonreturnAnalysis.cpp:28-32]. inList() uses std::find over the set; repeated visits occur during the fixed-point loop [analysis/app/src/nonreturnAnalysis.h:14; analysis/app/src/nonreturnAnalysis.cpp:41-47,66-71,115-152].
- Assessment: A tiny test could use a program containing only a returning leaf function and a caller that calls it, then returns. Both functions should still report returns() == true, and the nonreturn list should be empty after analysis [analysis/app/src/nonreturnAnalysis.cpp:31-34,71-87,124-146; analysis/tools/egalito/src/chunk/function.h:48-49]. The source supports redundant linear work, but no runtime output was captured [analysis/app/src/nonreturnAnalysis.cpp:32,41-47].

### Existing nonreturn flags force an unnecessary stabilization pass

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/nonreturnAnalysis.cpp:130`
- Invariant: A fixed-point pass needs to repeat when it changes a Function return flag that callers may depend on [analysis/app/src/nonreturnAnalysis.cpp:143-152].
- Mechanism: Adding an already marked function to the pass-local set also clears the loop flag, although it changes no Function return flag [analysis/app/src/nonreturnAnalysis.cpp:124-132]. Parsing can mark functions before mode 13 starts [analysis/tools/egalito/src/conductor/passes.cpp:70-72,86-87; analysis/app/src/testSyspart.cpp:158,380-384].
- Reproducer: Source-bounded fixture: a parsed program has one already marked nonreturning function and R returning functions, none newly classified. The first pass clears flag solely while seeding the set, so the loop builds and scans those R CFGs again [analysis/app/src/nonreturnAnalysis.cpp:118-148,152]. No workload was run.
- Expected: With no Function return flag changed, one scan of the returning Function [analysis/app/src/nonreturnAnalysis.cpp:143-152].
- Actual: For the stated fixture, the source schedules two scans of the returning Function while the count stays unchanged [analysis/app/src/nonreturnAnalysis.cpp:124-135,143-152; analysis/app/src/syspart.cpp:3113-3126]. This is a source prediction, not observed runtime output.
- Evidence: analysis/app/src/testSyspart.cpp:383-384 — mode 13 creates a fresh NonReturnAnalysis and runs it after parsing at line 158; analysis/tools/egalito/src/conductor/passes.cpp:70-72,86-87 and analysis/tools/egalito/src/pass/nonreturn.cpp:99-103 — parsing can mark a Function nonreturning; analysis/app/src/nonreturnAnalysis.cpp:118-132 — the first pass inserts that already marked Function into the initially empty local set and clears flag without changing its return flag; analysis/app/src/nonreturnAnalysis.cpp:134-142,152 — each pass constructs and scans the returning Function's CFG, so the cleared flag causes a second scan; analysis/app/src/nonreturnAnalysis.cpp:143-148 — newly classified Functions separately justify another pass.
- Assessment: A tiny test fixture would contain one Function already marked nonreturning and one returning Function with a nonempty CFG and an ordinary return. A test counter around ControlFlowGraph construction should report 1 construction; the traced code predicts 2. Mode 13 would print `Before: 1 After: 1` either way, because it counts Function return flags [analysis/app/src/testSyspart.cpp:380-386; analysis/app/src/syspart.cpp:3113-3126]. No workload was run.

### Mode 13 initializes an unused syscall map

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/testSyspart.cpp:167`
- Invariant: Mode 13's count and analysis consume Function return flags and the parsed Program [analysis/app/src/testSyspart.cpp:380-386; analysis/app/src/syspart.cpp:3113-3127].
- Mechanism: Before dispatch, the driver reads and parses two syscall header files into a map, or builds a default map; the mode 13 branch does not use that map [analysis/app/src/testSyspart.cpp:167,380-386; analysis/app/src/syspart.cpp:131-157].
- Reproducer: Bounded cost: for header files containing H lines and S accepted definitions, mode 13 processes H lines and stores up to S map entries before its count-only branch [analysis/app/src/syspart.cpp:113-125,131-157; analysis/app/src/testSyspart.cpp:167,380-386]. No cost was measured.
- Expected: Mode 13 can produce its count line without populating the syscall map [analysis/app/src/testSyspart.cpp:380-386; analysis/app/src/syspart.cpp:3113-3127].
- Actual: For a mode 13 invocation that passes argument checks and reaches dispatch, the source first reads both syscall headers and processes their lines, with a default-map fallback when no entries were found [analysis/app/src/testSyspart.cpp:137-167; analysis/app/src/syspart.cpp:131-157].
- Evidence: analysis/app/src/testSyspart.cpp:137-152 — required arguments are checked before initialization; analysis/app/src/testSyspart.cpp:156-167 — parsing and passes precede an unconditional populateSyscallMap call; analysis/app/src/syspart.cpp:113-157 — that call processes lines from two headers, inserts accepted definitions, or constructs the default map; analysis/app/src/testSyspart.cpp:380-387 — mode 13 calls only the count method and NonReturnAnalysis; analysis/app/src/syspart.cpp:3113-3127 — the count reads Function return flags; analysis/app/src/nonreturnAnalysis.cpp:112-152 — the analysis operates on the Program without the syscall map.
- Assessment: A tiny test case is a target binary built from `int main(){return 0;}`, invoked with `-p tiny -s main -a 13`. The expected count line is `tiny Before: <B> After: <A>`; changing syscall header definitions should leave B and A unchanged because the branch counts Function return flags and runs NonReturnAnalysis on the Program [analysis/app/src/testSyspart.cpp:380-386; analysis/app/src/syspart.cpp:3113-3127; analysis/app/src/nonreturnAnalysis.cpp:112-152]. This is a source-supported expectation; no output or cost was measured.

<!-- harness:logic:mode-13:end -->

<!-- harness:logic:mode-14:start -->
## Harness logic audit — mode 14

Dispatcher and modules: analysis/app/src/testSyspart.cpp, analysis/app/src/syspart.cpp, analysis/app/src/syspart.h, analysis/app/src/ipcallgraph.cpp, analysis/app/src/ipcallgraph.h

### Repeated syscall sites print identical rows

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:2310`
- Invariant: Each reported syscall, direct invoker, and address-taken root triple should appear once; the row contains no syscall-site address (analysis/app/src/syspart.cpp:2310).
- Mechanism: The syscall scanner appends the same function summary once per matching site, and run9 prints a row for every appended entry (analysis/app/src/syspart.cpp:296-315; analysis/app/src/syspart.cpp:2302-2310).
- Reproducer: Source-bounded case: an address-taken function has two instructions resolved to syscall 39 (analysis/tools/egalito/src/pass/findsyscalls.cpp:36-45; analysis/app/src/syspart.cpp:296-315).
- Expected: One relevant `getpid\tf\tf\t` row for the proposed test (analysis/app/src/syspart.cpp:2310).
- Actual: Two identical relevant rows are predicted by the source; this is not runtime-confirmed (analysis/app/src/syspart.cpp:313-315; analysis/app/src/syspart.cpp:2304-2310).
- Evidence: analysis/app/src/testSyspart.cpp:77-86 — -a selects the numeric option; analysis/app/src/testSyspart.cpp:389-392 — option 14 calls run9; analysis/tools/egalito/src/pass/findsyscalls.h:15-21 — results are keyed by instruction; analysis/tools/egalito/src/pass/findsyscalls.cpp:36-45 — each resolved syscall instruction gets an entry; analysis/app/src/syspart.cpp:296-315 — each entry's value appends the same SysNode pointer to who_invokes_syscalls, without a membership check; analysis/app/src/syspart.cpp:2281-2284 — run9 obtains address-taken roots and invokes the scanner; analysis/app/src/syspart.cpp:2293-2319 — the visited guard limits graph-node traversal, while the row loop prints once per matching vector entry and contains no site address.
- Assessment: Tiny test case: make address-taken function f contain two syscall instructions, each resolved to syscall 39, and run mode -a 14. The scanner records results per instruction (analysis/tools/egalito/src/pass/findsyscalls.cpp:36-45); the syscall table names 39 getpid (analysis/app/src/syspart.cpp:92). For f as the reported root, the expected relevant output is one `getpid\tf\tf\t` row. The source predicts two identical rows because each site appends the same function node and the print loop emits a row for each entry (analysis/app/src/syspart.cpp:296-315; analysis/app/src/syspart.cpp:2302-2310). No runtime output was observed.

### Mode 14 computes derived syscall summaries it never reads

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspart.cpp:2284`
- Invariant: Reporting direct syscall invokers along direct call edges needs the invoker map and direct children, which the print loop reads (analysis/app/src/syspart.cpp:2302-2314).
- Mechanism: run9 invokes backward syscall propagation before a print loop that reads neither derived_syscalls nor syscall_info (analysis/app/src/syspart.cpp:2284; analysis/app/src/syspart.cpp:2286-2319).
- Reproducer: Bounded cost: with S recorded syscall sites and a backward graph of V nodes and E parent edges, the call can perform O(S(V+E)) graph visits without changing these rows (analysis/app/src/syspart.cpp:408-448; analysis/app/src/syspart.cpp:2302-2314).
- Expected: For the tiny graph in reason, `getpid\tB\tA\t\n` with the propagation call omitted (analysis/app/src/syspart.cpp:92; analysis/app/src/syspart.cpp:2302-2317).
- Actual: The source performs propagation before printing those rows; output and time were not observed (analysis/app/src/syspart.cpp:2283-2286; analysis/app/src/syspart.cpp:2302-2319).
- Evidence: analysis/app/src/testSyspart.cpp:389-392 — mode 14 calls run9; analysis/app/src/syspart.cpp:2269-2284 — run9 builds the graph, records direct syscall invokers, then unconditionally calls findDerivedSyscalls; analysis/app/src/syspart.cpp:296-321 — findDirectSyscalls fills who_invokes_syscalls; analysis/app/src/syspart.cpp:408-465 — findDerivedSyscalls walks parent edges and updates derived_syscalls and syscall_info; analysis/app/src/syspart.cpp:2286-2319 — the subsequent print loop reads who_invokes_syscalls and direct call targets, but neither derived summary.
- Assessment: Mode 14 calls run9 (analysis/app/src/testSyspart.cpp:389-392). A tiny test graph with AT function A directly calling B, where B invokes syscall 39, should print `getpid\tB\tA\t\n` whether or not propagation runs: syscall 39 is named getpid (analysis/app/src/syspart.cpp:92), and the print loop uses recorded invokers and direct call targets (analysis/app/src/syspart.cpp:2302-2317). The propagation call has no guard in run9 (analysis/app/src/syspart.cpp:2283-2286); its internal null-node guard only skips individual sites (analysis/app/src/syspart.cpp:413-419). For S recorded sites, it can traverse backward through V nodes and E parent edges per site, adding O(S(V+E)) graph visits (analysis/app/src/syspart.cpp:408-438). No runtime cost or output was measured.

### Every visited node rescans all syscall sites

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspart.cpp:2302`
- Invariant: A visited graph node needs only the syscall entries for its own function (analysis/app/src/syspart.cpp:2300-2310).
- Mechanism: For each node reached from each address-taken root, run9 iterates the entire syscall-to-invoker map and every stored invoker before comparing function identities (analysis/app/src/syspart.cpp:2286-2308).
- Reproducer: Bounded cost: if the traversals visit T nodes in total and the map holds S invoker entries, the comparisons cost O(TS), including entries for functions outside those traversals (analysis/app/src/syspart.cpp:2286-2308).
- Expected: Read the visited node's direct syscall set through syscall_mapping (analysis/app/src/syspart.h:22-35; analysis/app/src/syspart.cpp:301-321).
- Actual: Every visited node scans the global who_invokes_syscalls map and its invoker vectors (analysis/app/src/syspart.cpp:2294-2313).
- Evidence: analysis/app/src/testSyspart.cpp:77-87 — -a selects the analysis number; analysis/app/src/testSyspart.cpp:389-392 — case 14 calls run9; analysis/app/src/syspart.cpp:2269-2284 — run9 builds the graph and syscall summaries; analysis/app/src/syspart.cpp:282-321 — findDirectSyscalls records each invoker in the global map and stores each node's direct syscall set in syscall_mapping; analysis/app/src/syspart.cpp:2286-2319 — each address-taken traversal visits nodes and scans the full global invoker map at each visit.
- Assessment: Mode -a 14 calls run9 without a guard that limits the syscall map to the current traversal (analysis/app/src/testSyspart.cpp:389-392). For each newly visited node, run9 scans every stored syscall invoker before checking function identity, so T visited nodes and S stored invoker entries require O(TS) scans (analysis/app/src/syspart.cpp:2294-2308). A tiny test would use address-taken root A calling B, with one syscall in B and a separate function C containing another syscall. Expected output is one line for B's syscall and A, with no line for C; C's invoker entry would still be scanned while visiting A and B (analysis/app/src/syspart.cpp:2302-2317). No runtime cost was measured.

### Linear visited checks make each root traversal quadratic

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspart.cpp:2298`
- Invariant: Checking whether a callgraph node was visited should have bounded lookup cost per node (analysis/app/src/syspart.cpp:2293-2299).
- Mechanism: run9 creates a vector for each address-taken root, linearly searches it on every stack pop, then appends each newly visited node (analysis/app/src/syspart.cpp:2286-2299; analysis/app/src/syspart.cpp:2314-2319).
- Reproducer: Bounded cost: a direct chain of V distinct nodes reachable from one address-taken root performs 0+1+…+(V−1) vector comparisons, or Θ(V²), before accounting for child retrieval (analysis/app/src/syspart.cpp:2293-2299; analysis/app/src/syspart.cpp:2314-2319).
- Expected: Bounded-cost visited membership with the same traversal rows (analysis/app/src/syspart.cpp:2298-2319).
- Actual: Visited membership uses linear search over a growing vector; this is source-supported, not runtime-confirmed (analysis/app/src/syspart.cpp:2293-2299; analysis/app/src/syspart.cpp:2319).
- Evidence: analysis/app/src/testSyspart.cpp:389-392 — mode 14 calls run9; analysis/app/src/syspart.cpp:2274-2281 — run9 builds the call graph and obtains address-taken roots; analysis/app/src/syspart.cpp:2286-2298 — each root gets a fresh vector and a linear membership check on every pop; analysis/app/src/syspart.cpp:2314-2319 — direct children are pushed and newly visited nodes are appended. The loop has no depth or node-count guard (analysis/app/src/syspart.cpp:2294-2320).
- Assessment: A tiny test with one address-taken root f0 and direct edges f0→f1→f2, with only f2 invoking write, should emit `write\tf2\tf0\t\n` from the row-printing path (analysis/app/src/syspart.cpp:2302-2310). The three first visits require 0+1+2 visited-pointer comparisons because membership is checked before each node is appended (analysis/app/src/syspart.cpp:2293-2299; analysis/app/src/syspart.cpp:2319). A chain of V distinct nodes therefore makes this check Θ(V²). No runtime cost was measured.

### Mode 14 builds indirect edges for a direct-edge report

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspart.cpp:2277`
- Invariant: The report traverses direct children only (analysis/app/src/syspart.cpp:2314-2317).
- Mechanism: Without -g, run9 calls full graph generation. After direct-edge and address-taken discovery, that path can repeatedly resolve indirect calls, parse TypeArmor data, and generate indirect edges (analysis/app/src/syspart.cpp:2274-2277; analysis/app/src/ipcallgraph.cpp:1770-1790,1797-1818,1835-1836).
- Reproducer: Source-bounded case: a graph with indirect callsites and no NSS expansion. With -i, full generation revisits graph nodes until resolution stops, although the report follows only direct children (analysis/app/src/ipcallgraph.cpp:1797-1810; analysis/app/src/syspart.cpp:2314-2317).
- Expected: In the proposed case, one syscall/leaf/callback report row, with direct-edge and address-taken discovery supplying the report inputs (analysis/app/src/ipcallgraph.cpp:1742-1762; analysis/app/src/syspart.cpp:2281-2283; analysis/app/src/syspart.cpp:2302-2317).
- Actual: The source selects full generation without -g and executes its additional indirect-analysis path; no runtime output was captured (analysis/app/src/syspart.cpp:2274-2277; analysis/app/src/ipcallgraph.cpp:1797-1836).
- Evidence: analysis/app/src/testSyspart.cpp:74-76 — -g selects direct generation; analysis/app/src/testSyspart.cpp:389-392 — mode 14 calls run9; analysis/app/src/syspart.cpp:2274-2278 — without -g, run9 selects full generation; analysis/app/src/ipcallgraph.cpp:1742-1762 and analysis/app/src/ipcallgraph.cpp:1766-1791 — both generators perform direct-edge and address-taken discovery; analysis/app/src/ipcallgraph.cpp:1797-1818 and analysis/app/src/ipcallgraph.cpp:1835-1836 — full generation additionally resolves indirect calls when -i is set, optionally parses TypeArmor data, and generates indirect edges; analysis/app/src/ipcallgraph.cpp:142-149 and analysis/app/src/syspart.cpp:2314-2317 — the report traverses direct children; analysis/app/src/syspart.cpp:2283-2284 and analysis/app/src/syspart.cpp:2302-2311 — it prints matches from direct syscall discovery, while the derived-syscall pass has no printed result here; analysis/app/src/ipcallgraph.cpp:1955-1976 — NSS can add direct edges, so the proposed case excludes NSS expansion.
- Assessment: A tiny source-bounded test would have an address-taken callback that directly calls a leaf containing one syscall, plus an indirect callsite elsewhere and no NSS expansion. Mode 14 without -g, including with -i, should print the syscall, leaf, and callback as tab-separated fields; the report prints matches while traversing direct children (analysis/app/src/syspart.cpp:2302-2317). The extra indirect passes are code-supported work, but their runtime cost was not measured (analysis/app/src/ipcallgraph.cpp:1797-1818; analysis/app/src/ipcallgraph.cpp:1835-1836).

### Syscall extraction scans functions outside every reported closure

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspart.cpp:2283`
- Invariant: Rows use syscall entries only for nodes reached by direct traversal from an address-taken root (analysis/app/src/syspart.cpp:2286-2317).
- Mechanism: findDirectSyscalls visits every callgraph node, scans each function's instructions, and allocates a SysNode before run9 starts its address-taken traversals (analysis/app/src/syspart.cpp:282-294,319-321,2283-2286).
- Reproducer: Source-bounded case: the selected root directly calls a large unrelated function and takes the address of a separate callback. If the unrelated function is outside the callback's direct closure, its instruction scan and SysNode cannot supply a row. For U such instructions, the extra syscall pass visits U instructions (analysis/app/src/ipcallgraph.cpp:891-895; analysis/app/src/syspart.cpp:284-291,2286-2317).
- Expected: For mode -a 14, syscall extraction needed to produce rows would cover the address-taken roots' direct closures (analysis/app/src/syspart.cpp:2286-2317).
- Actual: The source invokes extraction for every graph node before those traversals, including direct callees outside every reported closure (analysis/app/src/syspart.cpp:2283-2286; analysis/app/src/syspart.cpp:284-321).
- Evidence: analysis/app/src/testSyspart.cpp:389-391 — mode 14 calls run9; analysis/app/src/syspart.cpp:2269-2284 — run9 builds the graph, then calls findDirectSyscalls; analysis/app/src/ipcallgraph.cpp:891-895 — a direct callee is added to the graph; analysis/app/src/syspart.cpp:284-321 — extraction allocates a SysNode and invokes FindSyscalls for every graph node; analysis/tools/egalito/src/pass/findsyscalls.cpp:21-39 — for a nonempty function, the visitor builds and analyzes a CFG and visits its instructions; analysis/app/src/syspart.cpp:2286-2317 — rows are emitted only while traversing direct targets from address-taken functions.
- Assessment: The guards skip libc's syscall() function and functions with an empty CFG, but do not restrict extraction to address-taken closures (analysis/tools/egalito/src/pass/findsyscalls.cpp:19-37). Tiny proposed test: have main take the address of callback and directly call a large unrelated function; put syscall 39 in callback and syscall 1 in unrelated. Assuming both syscalls are resolved, the predicted mode -a 14 row for these functions is `getpid\tcallback\tcallback\t`, with no row for unrelated. The row loop visits only callback's direct closure (analysis/app/src/syspart.cpp:2286-2317), while extraction still processes unrelated (analysis/app/src/syspart.cpp:284-321). This is a source-supported cost finding; no runtime cost was measured.

### Shared direct subgraphs are traversed once per address-taken root

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspart.cpp:2286`
- Invariant: A direct subgraph's syscall summary can be reused across address-taken roots while retaining one set of rows per root (analysis/app/src/syspart.cpp:2286-2317).
- Mechanism: Each root starts a fresh stack and visited vector, so nodes shared by roots are traversed and their direct-child sets rebuilt for each root (analysis/app/src/syspart.cpp:2286-2294,2314-2319; analysis/app/src/ipcallgraph.cpp:140-146).
- Reproducer: Bounded case: A address-taken roots each call the same V-node direct chain containing no syscalls. The loop visits that chain A times and emits no rows, performing at least Ω(A×V) node visits (analysis/app/src/syspart.cpp:2286-2319).
- Expected: Reuse a shared direct subgraph's syscall summary while emitting rows separately for each root (analysis/app/src/syspart.cpp:2302-2310).
- Actual: The shared chain is traversed once per root; for A roots and V shared chain nodes, the loop performs at least A×V node visits (analysis/app/src/syspart.cpp:2286-2319).
- Evidence: analysis/app/src/testSyspart.cpp:389-392 — mode -a 14 calls run9. analysis/app/src/syspart.cpp:2269-2286 — run9 builds the graph, gets the address-taken roots, then iterates over them. analysis/app/src/ipcallgraph.cpp:891-895 — direct calls add graph edges; analysis/app/src/ipcallgraph.cpp:224-247 — edges to the same function reuse its node. analysis/app/src/syspart.cpp:2291-2319 — each root gets a fresh stack and visited vector and traverses its direct targets. analysis/app/src/ipcallgraph.cpp:142-148 — each getDirectCallTargets call constructs a new set.
- Assessment: Tiny test case: two address-taken functions each directly call the same two-function chain, and none contains a syscall. Expect zero syscall rows, while the loop visits the shared chain twice: it resets `visited` for each root and prints rows only on a syscall match (analysis/app/src/syspart.cpp:2286-2319). This is a source-supported cost finding; no runtime output was captured.

<!-- harness:logic:mode-14:end -->

<!-- harness:logic:mode-15:start -->
## Harness logic audit — mode 15

Dispatcher and modules: README.md, analysis/app/README.md, analysis/app/src/testSyspart.cpp, analysis/app/src/syspart.cpp, analysis/app/src/ipcallgraph.cpp, analysis/app/src/ipcallgraph.h

### A missing query function is dereferenced during node lookup

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/ipcallgraph.h:360`
- Invariant: A query name must resolve to a Function before getNode receives it (analysis/app/src/syspart.cpp:2142-2145).
- Mechanism: findFunctionByName returns null for an absent name; getNode dereferences that pointer before mode 15 checks whether the node exists (analysis/app/src/syspart.cpp:68-80; analysis/app/src/ipcallgraph.h:357-361; analysis/app/src/syspart.cpp:2146-2155).
- Reproducer: Source-bounded case: use a valid graph root and request -a 15,root,__missing__, where __missing__ is absent from the loaded functions (analysis/app/src/testSyspart.cpp:408-421; analysis/app/src/syspart.cpp:2142-2145).
- Expected: Node for __missing__ doesn't exist (analysis/app/src/syspart.cpp:2151-2154).
- Actual: Source-supported null-pointer dereference before the message; no runtime outcome was observed (analysis/app/src/syspart.cpp:2143-2151; analysis/app/src/ipcallgraph.h:357-360).
- Evidence: analysis/app/src/testSyspart.cpp:408-421 — passes nonempty names to ifPathExists; analysis/app/src/syspart.cpp:66-80 — an absent name returns null; analysis/app/src/syspart.cpp:2142-2145 — passes both results to getNode before node checks; analysis/app/src/ipcallgraph.h:357-360 — a missing map key leads to f->getName(), which dereferences null; analysis/app/src/syspart.cpp:2151-2154 — the end-node message comes afterward.
- Assessment: Mode 15 checks only that both names are nonempty (analysis/app/src/testSyspart.cpp:408-421). A tiny test is a binary containing root, invoked with -p <binary> -s root -a 15,root,__missing__, where __missing__ is absent. The intended output is "Node for __missing__ doesn't exist" (analysis/app/src/syspart.cpp:2151-2154). The source instead passes the unresolved null Function to getNode before that check (analysis/app/src/syspart.cpp:2143-2151; analysis/app/src/ipcallgraph.h:357-360). Graph generation also precedes name validation, making that work avoidable for this input (analysis/app/src/syspart.cpp:2131-2143).

### An alias can be reported unreachable even when its function is a child

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:2169`
- Invariant: The search must compare graph nodes using the destination function already resolved by name (analysis/app/src/syspart.cpp:2143-2145).
- Mechanism: Name lookup accepts hasName(end), but traversal compares only each child's getName() with end (analysis/app/src/syspart.cpp:73; analysis/app/src/syspart.cpp:2166-2169).
- Reproducer: Source-bounded graph: root calls a function whose getName() is canonical and whose hasName("alias") is true; request -a 15,root,alias with -s root (analysis/app/src/syspart.cpp:73; analysis/app/src/syspart.cpp:2166-2169).
- Expected: alias is reachable from root
- Actual: Source-predicted: NOT REACHABLE; no runtime output observed.
- Evidence: analysis/tools/egalito/src/chunk/function.cpp:41-51 — hasName accepts a symbol alias even when it differs from getName(); analysis/app/src/syspart.cpp:66-80 — findFunctionByName uses hasName; analysis/app/src/testSyspart.cpp:394-421 — mode 15 passes the parsed names to ifPathExists; analysis/app/src/syspart.cpp:2142-2155 — both names resolve to nodes and only missing nodes cause an early return; analysis/app/src/ipcallgraph.cpp:127-139 — getAllCallTargets supplies direct and indirect children; analysis/app/src/syspart.cpp:2166-2180 — traversal compares each child's primary name with the requested alias and prints NOT REACHABLE if none matches.
- Assessment: The missing-node guards do not refute the candidate: they pass when the alias resolves to an existing graph node (analysis/app/src/syspart.cpp:2142-2155). Tiny test case: a graph with root → canonical, where canonical.hasName("alias") is true and canonical.getName() is "canonical"; query -a 15,root,alias with -s root (analysis/app/src/testSyspart.cpp:41-62; analysis/app/src/testSyspart.cpp:394-421). Expected query output: "alias is reachable from root" (analysis/app/src/syspart.cpp:2171). The source instead predicts "NOT REACHABLE" if no traversed child has getName() equal to "alias" (analysis/app/src/syspart.cpp:2166-2180).

### A function is reported unreachable from itself without a cycle

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:2169`
- Invariant: A reachability query from a node to itself includes the zero-edge path (analysis/app/src/syspart.cpp:2156-2160).
- Mechanism: The loop tests only children for the destination name and never tests its initial node (analysis/app/src/syspart.cpp:2156-2169).
- Reproducer: Source-bounded case: a graph node root has no call targets; request -s root -a 15,root,root (analysis/app/src/testSyspart.cpp:408-421; analysis/app/src/syspart.cpp:2156-2169).
- Expected: root is reachable from root
- Actual: Source-predicted: NOT REACHABLE; no runtime output observed.
- Evidence: analysis/app/src/testSyspart.cpp:408-421 — passes root,root to ifPathExists; analysis/app/src/syspart.cpp:2131-2155 — builds the graph and checks both nodes exist; analysis/app/src/ipcallgraph.cpp:127-140 — returns only call targets; analysis/app/src/syspart.cpp:2156-2180 — checks each child, never the initial node, then prints NOT REACHABLE.
- Assessment: Tiny test: analyze a program with a resolvable function root that has no call targets using -p <program> -s root -a 15,root,root. Expected reachability output: "root is reachable from root". The parser accepts identical nonempty names (analysis/app/src/testSyspart.cpp:408-421), and the graph registers the selected root as a node (analysis/app/src/syspart.cpp:2131-2137; analysis/app/src/ipcallgraph.cpp:169-178). The query examines children without checking the initial node, so an empty child set leads to "NOT REACHABLE" (analysis/app/src/syspart.cpp:2156-2180). Graph generation is also avoidable for this self-query (analysis/app/src/syspart.cpp:2131-2140).

### Each visited function materializes all targets before testing any target

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspart.cpp:2166`
- Invariant: A reachability query can stop once it encounters the destination child (analysis/app/src/syspart.cpp:2167-2174).
- Mechanism: getAllCallTargets first inserts every direct and indirect child into a fresh set; only after that work does mode 15 inspect the children (analysis/app/src/ipcallgraph.cpp:127-139; analysis/app/src/syspart.cpp:2166-2169).
- Reproducer: Bounded cost case: the query start has K distinct targets and the destination is one of them. Before it can report reachability, the source allocates and fills a set of K targets, with O(K) temporary space and O(K log K) ordered-set insertion work (analysis/app/src/ipcallgraph.cpp:127-139; analysis/app/src/syspart.cpp:2166-2174).
- Expected: For the proposed two-target test, print "target is reachable from main"; an early-exit traversal could find target without first building the full target set (analysis/app/src/syspart.cpp:2169-2174).
- Actual: The source builds the full set before the destination check. With K distinct targets across K child entries, this entails O(K) temporary set space and O(K log K) ordered-set insertion work before a match can be reported; this cost was not measured (analysis/app/src/ipcallgraph.cpp:127-139; analysis/app/src/syspart.cpp:2166-2173).
- Evidence: analysis/app/src/testSyspart.cpp:394-421 — mode 15 validates the arguments and calls ifPathExists. analysis/app/src/syspart.cpp:2142-2155 — missing start or end nodes return before traversal. analysis/app/src/syspart.cpp:2160-2167 — already visited nodes are skipped; every node that proceeds calls getAllCallTargets before inspecting a child. analysis/app/src/ipcallgraph.cpp:127-139 — that call builds and returns a fresh ordered set from all direct and indirect child lists. analysis/app/src/syspart.cpp:2169-2174 — the destination check can stop the query only after that set has been built.
- Assessment: Tiny test case: a binary whose main directly calls distinct functions target and other, queried with -s main -a 15,main,target. Expect a line reading "target is reachable from main" (analysis/app/src/testSyspart.cpp:394-421; analysis/app/src/syspart.cpp:2169-2173). The cost claim follows from source; no runtime output was captured.

### Mode 15 ignores the direct-only flag

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/testSyspart.cpp:421`
- Invariant: With -g, a path query should use direct edges only; the option is described that way and run1 selects direct graph generation for it (analysis/app/src/testSyspart.cpp:74, analysis/app/src/testSyspart.cpp:101, analysis/app/src/syspart.cpp:1547-1550).
- Mechanism: Mode 15 does not pass direct_flag to ifPathExists, which always calls generate; generate adds indirect edges that the search traverses (analysis/app/src/testSyspart.cpp:421, analysis/app/src/syspart.cpp:2137, analysis/app/src/ipcallgraph.cpp:1835-1836, analysis/app/src/syspart.cpp:2166).
- Reproducer: Source-bounded graph: root takes cb's address and has an unresolved indirect call, but has no direct call to cb. Query -s root -g -a 15,root,cb; full generation can add cb as an indirect target (analysis/app/src/ipcallgraph.cpp:1362-1375, analysis/app/src/ipcallgraph.cpp:709-715, analysis/app/src/testSyspart.cpp:421).
- Expected: For the proposed fixture with -g: NOT REACHABLE (analysis/app/src/testSyspart.cpp:103, analysis/app/src/syspart.cpp:2179-2180).
- Actual: Source predicts: cb is reachable from root through an added indirect edge; this was not observed at runtime (analysis/app/src/ipcallgraph.cpp:709-715, analysis/app/src/syspart.cpp:2166-2173).
- Evidence: analysis/app/src/testSyspart.cpp:421 — mode 15 calls ifPathExists without direct_flag; analysis/app/src/syspart.cpp:2129-2137 — the callee always calls generate; analysis/app/src/ipcallgraph.cpp:1742-1764 — a separate direct graph generator exists; analysis/app/src/ipcallgraph.cpp:1820-1836 — generate creates indirect targets and edges; analysis/app/src/ipcallgraph.cpp:709-715 — unresolved indirect calls receive those targets when TypeArmor is off; analysis/app/src/ipcallgraph.cpp:127-139 — getAllCallTargets combines direct and indirect children; analysis/app/src/syspart.cpp:2166-2173 — the path search traverses that combined set. Full generation also performs indirect target resolution when -i is set, adding avoidable analysis cost for a direct-only query (analysis/app/src/ipcallgraph.cpp:1796-1811).
- Assessment: Mode 15 ignores -g: the flag is set and documented as direct-only, but its path-query call omits it (analysis/app/src/testSyspart.cpp:74, analysis/app/src/testSyspart.cpp:103, analysis/app/src/testSyspart.cpp:421). A tiny test case is a root function that takes cb's address and makes an unresolved indirect call, with no direct call to cb. Query it with -p <fixture> -s root -g -a 15,root,cb; the expected path-query output is NOT REACHABLE (analysis/app/src/ipcallgraph.cpp:1370-1378, analysis/app/src/ipcallgraph.cpp:1451-1452, analysis/app/src/syspart.cpp:2179-2180). This is a source-supported prediction; no output was captured.

### Mode 15 enables TypeArmor without passing its data path to the graph

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:2136`
- Invariant: When -t supplies a TypeArmor file, graph generation must read that file before filtering indirect targets (analysis/app/src/testSyspart.cpp:64-65, analysis/app/src/ipcallgraph.cpp:1815-1816, analysis/app/src/ipcallgraph.cpp:814-831).
- Mechanism: The caller stores the path in Syspart, but ifPathExists sets only the graph's TypeArmor flag. parseTypeArmor opens the graph's separate typeArmorPath; with no path set, it loads no callsite metadata and the filter retains every candidate when metadata is absent (analysis/app/src/testSyspart.cpp:181-182, analysis/app/src/syspart.cpp:2135-2137, analysis/app/src/ipcallgraph.cpp:532-535, analysis/app/src/ipcallgraph.cpp:822-831).
- Reproducer: Source-bounded case: supply -t with metadata that would exclude an address-taken cb from root's indirect call, then query -s root -a 15,root,cb. The absent graph path leaves that callsite without loaded metadata (analysis/app/src/testSyspart.cpp:64-65, analysis/app/src/syspart.cpp:2136-2137, analysis/app/src/ipcallgraph.cpp:532-535, analysis/app/src/ipcallgraph.cpp:822-831).
- Expected: For the stated isolated test case, `NOT REACHABLE` (analysis/app/src/ipcallgraph.cpp:848-861, analysis/app/src/syspart.cpp:2178-2180).
- Actual: The source predicts `cb is reachable from root` because the missing graph path leaves the callsite unfiltered; this is not runtime-confirmed (analysis/app/src/ipcallgraph.cpp:532-535, analysis/app/src/ipcallgraph.cpp:822-833, analysis/app/src/syspart.cpp:2166-2173).
- Evidence: analysis/app/src/testSyspart.cpp:64-65 — `-t` stores the path and enables TypeArmor; analysis/app/src/testSyspart.cpp:184-185 — the path is stored on Syspart; analysis/app/src/testSyspart.cpp:394-422 — mode 15 calls ifPathExists; analysis/app/src/syspart.cpp:2131-2137 — that method enables TypeArmor and generates the graph without passing the path; analysis/app/src/syspart.h:45-46 and analysis/app/src/ipcallgraph.h:284-291 — Syspart and the graph have separate path fields; analysis/app/src/ipcallgraph.cpp:1815-1816 and analysis/app/src/ipcallgraph.cpp:532-535 — generation parses the graph path, whose file read supplies metadata only if it opens; analysis/app/src/ipcallgraph.cpp:822-833 — absent callsite metadata retains every candidate; analysis/app/src/ipcallgraph.cpp:127-138 and analysis/app/src/syspart.cpp:2161-2173 — retained indirect children participate in the reachability search. Other Syspart methods explicitly pass the path to the graph, for example analysis/app/src/syspart.cpp:1512-1514.
- Assessment: A tiny test case is a binary where root has one indirect call, cb is an address-taken candidate, and cb has no other path from root (analysis/app/src/ipcallgraph.cpp:1371-1378, analysis/app/src/ipcallgraph.cpp:1834-1836, analysis/app/src/syspart.cpp:2158-2180). Supply a TypeArmor file with `icallargs executable <call-address> 0` and `fnargs executable <cb-address> 2`; those records would exclude cb from that call (analysis/app/src/ipcallgraph.cpp:565-606, analysis/app/src/ipcallgraph.cpp:848-856). For `-p <binary> -s root -t <file> -a 15,root,cb`, the expected reachability output is `NOT REACHABLE` (analysis/app/src/testSyspart.cpp:99-102, analysis/app/src/testSyspart.cpp:394-422, analysis/app/src/syspart.cpp:2178-2180). No runtime output was observed.

### A same-named child can satisfy a query for a different destination node

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:2169`
- Invariant: After resolving end_func and end_node, reachability should be tested against that destination node (analysis/app/src/syspart.cpp:2143-2155).
- Mechanism: Name lookup retains the last matching module's function, but traversal tests a child's name rather than whether the child is end_node (analysis/app/src/syspart.cpp:69-80, analysis/app/src/syspart.cpp:2166-2169).
- Reproducer: Source-bounded graph: root directly calls A::foo and takes B::foo's address without calling it; B is the later module in name lookup. Both graph nodes exist, while the query -s root -a 15,root,foo resolves its destination to B::foo (analysis/app/src/ipcallgraph.cpp:891-895, analysis/app/src/ipcallgraph.cpp:1362-1375, analysis/app/src/syspart.cpp:69-80, analysis/app/src/syspart.cpp:2143-2145).
- Expected: NOT REACHABLE (analysis/app/src/syspart.cpp:2179-2180)
- Actual: Source-predicted: foo is reachable from root when traversal encounters A::foo (analysis/app/src/syspart.cpp:2166-2173). No runtime output was observed.
- Evidence: analysis/app/src/testSyspart.cpp:394-421 — mode 15 passes root and foo to ifPathExists; analysis/app/src/syspart.cpp:69-80 — lookup retains the later module's matching function; analysis/app/src/ipcallgraph.cpp:224-247 — direct calls add edges to specific Function nodes; analysis/app/src/ipcallgraph.h:355-371 — getNode distinguishes functions across modules; analysis/app/src/syspart.cpp:2142-2155 — the destination node is resolved and checked for existence; analysis/app/src/ipcallgraph.cpp:127-139 — traversal children are call targets; analysis/app/src/syspart.cpp:2166-2173 — success compares a child's name with foo, without comparing it with end_node.
- Assessment: Tiny source-bounded test: put distinct functions named foo in modules A and B, with B later in program order. Have root call A::foo directly and take B::foo's address without calling it. Query mode 15 with -s root -a 15,root,foo. The lookup selects B::foo, but the direct edge leads to A::foo; taking an address creates an AT entry, not a call target (analysis/app/src/syspart.cpp:69-80; analysis/app/src/ipcallgraph.cpp:891-895; analysis/app/src/ipcallgraph.cpp:250-275). Expected output: NOT REACHABLE (analysis/app/src/syspart.cpp:2179-2180).

<!-- harness:logic:mode-15:end -->

<!-- harness:logic:mode-16:start -->
## Harness logic audit — mode 16

Dispatcher and modules: analysis/app/src/testSyspart.cpp, analysis/app/src/syspart.cpp, analysis/tools/egalito/src/pass/findsyscalls.cpp, analysis/tools/egalito/src/pass/findsyscalls.h

### Ambiguous module substring silently selects the last match

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/testSyspart.cpp:440`
- Invariant: The requested substring must select one intended module before its syscall rows are reported (analysis/app/src/testSyspart.cpp:432-452).
- Mechanism: Every matching module overwrites `m`; the loop does not reject multiple matches (analysis/app/src/testSyspart.cpp:435-442).
- Reproducer: Source-bounded case: two loaded modules have names containing `libfoo`, and the intended module is visited first. Request `-a 16,libfoo` (analysis/app/src/testSyspart.cpp:432-442).
- Expected: For the two-module test, report ambiguity and produce no syscall rows (analysis/app/src/testSyspart.cpp:435-452).
- Actual: Source-predicted: print "Module found libfoo_b.so" and report only libfoo_b.so syscall rows; no runtime output was observed (analysis/app/src/testSyspart.cpp:438-452; analysis/app/src/syspart.cpp:186-204).
- Evidence: analysis/app/src/testSyspart.cpp:77-86 — parses -a 16,libfoo; analysis/app/src/testSyspart.cpp:156-161 — loads the program with shared libraries; analysis/app/src/testSyspart.cpp:424-442 — extracts libfoo and overwrites m for every matching module; analysis/app/src/testSyspart.cpp:445-452 — checks only whether m is null, prints the selected name, and scans m; analysis/app/src/syspart.cpp:186-204 — reports syscall rows only from the selected module.
- Assessment: A tiny test would load libfoo_a.so before libfoo_b.so, give each a distinct direct syscall, and request -a 16,libfoo. Expected: an ambiguity message and no syscall rows, since the substring matches both modules (analysis/app/src/testSyspart.cpp:435-452). The source instead selects libfoo_b.so. The selection is printed as "Module found libfoo_b.so", so it is not wholly silent; the ambiguity is not reported (analysis/app/src/testSyspart.cpp:438-452). The last-match behavior is also documented (analysis/app/README.md:64).

### Syscall resolution can use a different register's definition

- Status: **supported**
- Kind: logic
- Location: `analysis/tools/egalito/src/pass/findsyscalls.cpp:124`
- Invariant: Resolving RAX or RDI must inspect the definition of that requested register (analysis/tools/egalito/src/pass/findsyscalls.cpp:43-45,72-74,116).
- Mechanism: The resolver iterates every register definition in a referenced state and retains the last non-null tree, regardless of its register key (analysis/tools/egalito/src/pass/findsyscalls.cpp:121-140). The definition list is an ordered map (analysis/tools/egalito/src/analysis/usedef.h:20-38).
- Reproducer: Source-bounded state: a reference for RAX points to a state defining RAX as 39 and a higher-keyed register as 1. The loop selects the latter constant (analysis/tools/egalito/src/pass/findsyscalls.cpp:116-140).
- Expected: The proposed resolver test returns {39}; a corresponding mode 16 row would end in 39 (analysis/tools/egalito/src/pass/findsyscalls.cpp:40-45; analysis/app/src/syspart.cpp:196-202).
- Actual: For the proposed state, source logic returns {1}. No binary was run and no mode 16 output was observed (analysis/tools/egalito/src/pass/findsyscalls.cpp:124-140).
- Evidence: analysis/app/src/testSyspart.cpp:424-452 — mode 16 calls findDirectSyscallsOfModule; analysis/app/src/syspart.cpp:186-202 — it runs FindSyscalls and prints recorded values; analysis/tools/egalito/src/pass/findsyscalls.cpp:40-45 — syscall sites request RAX; analysis/tools/egalito/src/pass/findsyscalls.cpp:68-74 — libc syscall calls request RDI; analysis/tools/egalito/src/analysis/usedef.cpp:635-643 — useReg records references under the requested register; analysis/tools/egalito/src/pass/findsyscalls.cpp:116-140 — resolution reads every definition in each referenced state and retains the last non-null tree; analysis/tools/egalito/src/analysis/usedef.h:20-36 — definitions are stored in an ordered map, with a register-specific lookup also available at analysis/tools/egalito/src/analysis/usedef.h:116-119.
- Assessment: No guard rejects multiple non-null definitions: the count check only logs them (analysis/tools/egalito/src/pass/findsyscalls.cpp:124-138). A tiny resolver test can give a syscall site's RAX reference a state with RAX=39 and higher-keyed RDX=1; the expected value set is {39}, while this loop selects {1} (analysis/tools/egalito/src/instr/register.cpp:6-8; analysis/tools/egalito/src/pass/findsyscalls.cpp:116-140). This establishes the resolver error for that source-bounded state. The trace does not establish that normal mode 16 analysis produces that state or a wrong printed row (analysis/tools/egalito/src/pass/findsyscalls.cpp:20-34; analysis/app/src/syspart.cpp:191-202).

### Failed recursive register resolution is accepted as complete

- Status: **supported**
- Kind: logic
- Location: `analysis/tools/egalito/src/pass/findsyscalls.cpp:145`
- Invariant: A syscall value is recorded only when every contributing register path resolves to constants (analysis/tools/egalito/src/pass/findsyscalls.cpp:44-50,73-79).
- Mechanism: When a definition refers to another register, the recursive return value is discarded, leaving the outer `all_constants` true even if the recursive search fails (analysis/tools/egalito/src/pass/findsyscalls.cpp:113-119,142-145,158-161).
- Reproducer: Source-bounded state: RAX comes from RBX; RBX has two reaching definitions, constant 39 and one unresolved definition. The recursive search can collect 39 and return false, which the RAX search ignores (analysis/tools/egalito/src/pass/findsyscalls.cpp:116-119,121-145,147-158).
- Expected: An unresolved contributing path prevents recording syscall 39 (analysis/tools/egalito/src/pass/findsyscalls.cpp:44-50).
- Actual: For the stated fixture, the source predicts that 39 is recorded and printed as getpid (analysis/tools/egalito/src/pass/findsyscalls.cpp:139-145,161-163; analysis/app/src/syspart.cpp:92,194-202).
- Evidence: analysis/app/src/testSyspart.cpp:424-452 — mode 16 calls findDirectSyscallsOfModule; analysis/app/src/syspart.cpp:186-202 — it prints values returned by FindSyscalls; analysis/tools/egalito/src/pass/findsyscalls.cpp:40-50 — a syscall value is recorded when the top-level search returns true; analysis/tools/egalito/src/pass/findsyscalls.cpp:113-119 — a search with no reaching definitions returns false; analysis/tools/egalito/src/pass/findsyscalls.cpp:139-145 — a constant is collected, but a recursive register search's return value is ignored; analysis/tools/egalito/src/pass/findsyscalls.cpp:147-163 — an unresolved node makes only that recursive search return false, leaving the outer search true. The `seen` guard does not propagate failure (analysis/tools/egalito/src/pass/findsyscalls.cpp:115,161-163).
- Assessment: A tiny test fixture can give the syscall site's RAX one reaching definition that reads RBX, and give that definition's RBX two reaching definitions: constant 39 and an unresolved node. The expected output is no syscall row and an unresolved-number warning; the source instead predicts a `getpid 39` row because the recursive failure is discarded (analysis/tools/egalito/src/pass/findsyscalls.cpp:116-163; analysis/app/src/syspart.cpp:92,186-202). No runtime output was observed.

### Mode 16 analyzes functions that cannot contribute a row

- Status: **supported**
- Kind: performance
- Location: `analysis/tools/egalito/src/pass/findsyscalls.cpp:21`
- Invariant: A function with neither a syscall instruction nor a recognized call to libc `syscall()` needs no register dataflow to produce mode 16 rows (analysis/tools/egalito/src/pass/findsyscalls.cpp:36-79; analysis/app/src/syspart.cpp:196-202).
- Mechanism: Mode 16 visits every function in the selected module, and the visitor constructs a CFG and runs use-def analysis before checking instructions for either row-producing site (analysis/app/src/syspart.cpp:188-194; analysis/tools/egalito/src/pass/findsyscalls.cpp:21-40).
- Reproducer: Bounded cost: a selected module with N nonempty functions and no syscall sites causes N CFG constructions and N use-def analyses, while producing no syscall rows (analysis/app/src/syspart.cpp:188-202; analysis/tools/egalito/src/pass/findsyscalls.cpp:21-40,68-79).
- Expected: For N eligible functions with nonempty CFGs and no candidate sites, zero syscall rows and zero use-def analyses needed for mode 16 (analysis/tools/egalito/src/pass/findsyscalls.cpp:36-79; analysis/app/src/syspart.cpp:194-202).
- Actual: The source performs N CFG constructions and N use-def analyses for those functions before finding no sites; this is a source-supported cost claim, not an observed runtime result (analysis/app/src/syspart.cpp:188-194; analysis/tools/egalito/src/pass/findsyscalls.cpp:21-40,52-79).
- Evidence: analysis/app/src/testSyspart.cpp:424-452 — mode 16 selects a module and calls findDirectSyscallsOfModule; analysis/app/src/syspart.cpp:186-194 — every function in that module receives a fresh FindSyscalls visitor; analysis/tools/egalito/src/chunk/function.cpp:157-159 — accept invokes visit; analysis/tools/egalito/src/pass/findsyscalls.cpp:16-34 — after the libc-syscall and empty-CFG guards, visit builds a CFG and runs use-def analysis; analysis/tools/egalito/src/pass/findsyscalls.cpp:36-79 — it checks instructions for row-producing sites afterward; analysis/app/src/syspart.cpp:194-202 — rows are printed only for entries in the resulting number map.
- Assessment: The guards skip libc’s `syscall` function and empty CFGs, but there is no candidate-instruction check before use-def analysis (analysis/tools/egalito/src/pass/findsyscalls.cpp:16-40). Tiny test case: select a module containing one ordinary function such as `int f(void) { return 7; }`, with no syscall instruction or call to libc `syscall()`. Expect mode 16 to print its module-identification lines and no syscall row; the source still sends that function through CFG construction and use-def analysis (analysis/app/src/testSyspart.cpp:432-452; analysis/app/src/syspart.cpp:188-202; analysis/tools/egalito/src/pass/findsyscalls.cpp:21-40,52-79). No runtime cost was measured.

### Required start-function lookup is unused by mode 16

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/testSyspart.cpp:181`
- Invariant: Mode 16's module scan does not depend on the start function (analysis/app/src/testSyspart.cpp:424-453).
- Mechanism: Before dispatch, a named `-s` value triggers a scan of functions across loaded modules; mode 16 then uses only its module substring and never reads the resolved start function (analysis/app/src/testSyspart.cpp:179-183,424-453; analysis/app/src/syspart.cpp:66-80).
- Reproducer: Bounded cost: with F loaded functions and `-s __missing__ -a 16,<module>`, name lookup inspects up to F functions before the same module scan runs (analysis/app/src/syspart.cpp:66-80; analysis/app/src/testSyspart.cpp:179-183,434-452).
- Expected: For mode 16, retain the required -s argument check but skip resolving its value; module scan output should be unchanged (analysis/app/src/testSyspart.cpp:143-147,424-453).
- Actual: The source performs an unused named start-function lookup before mode 16; its runtime cost and output have not been observed (analysis/app/src/testSyspart.cpp:179-186,424-453; analysis/app/src/syspart.cpp:66-80).
- Evidence: analysis/app/src/testSyspart.cpp:41-62 — a named -s value sets func_name and satisfies funcFlag; analysis/app/src/testSyspart.cpp:143-147 — the start-argument guard requires that flag; analysis/app/src/testSyspart.cpp:179-183 — the named-value path calls findFunctionByName before dispatch; analysis/app/src/syspart.cpp:66-80 — a missing name is checked against every function in every loaded module; analysis/app/src/syspart.cpp:23-26 — setStartFunc only stores the pointer; analysis/app/src/testSyspart.cpp:424-453 — mode 16 scans modules using its own substring and calls findDirectSyscallsOfModule; analysis/app/src/syspart.cpp:186-205 — that method scans the selected module’s functions without using start_func.
- Assessment: A named -s value triggers a function lookup before mode 16 is dispatched, and mode 16 never reads the resolved start function (analysis/app/src/testSyspart.cpp:179-186,424-453). Tiny test case: use a fixture with one loaded module named fixture and invoke mode 16 with -s __missing__ and a module substring absent from its name. The expected mode output is the substring, the scanned module name, and “No module with the specified name found”; there is no missing-start-function message in this path (analysis/app/src/testSyspart.cpp:432-447). The extra lookup cost is supported by source, not measured.

### Generic syscall names can be reported for numbers absent from x86-64

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:118`
- Invariant: Mode 16's name column must use the x86-64 syscall table for a number recovered from RAX (analysis/tools/egalito/src/pass/findsyscalls.cpp:40-45; analysis/app/src/syspart.cpp:196-202).
- Mechanism: The parser reads header text without evaluating preprocessor conditions, loads generic names first, and leaves entries that the x86-64 header does not overwrite (analysis/app/src/syspart.cpp:113-154).
- Reproducer: Source-bounded case: scan a function with `mov $403, %eax; syscall`. The available generic header defines 403 as `clock_gettime64` inside a conditional block, while the x86-64 header jumps from 334 to 424 (/usr/include/asm-generic/unistd.h:780-784; /usr/include/x86_64-linux-gnu/asm/unistd_64.h:337-339).
- Expected: For a recovered 403, a mode 16 row with an empty name column: `probe <module>  403` (analysis/app/src/syspart.cpp:196-202; /usr/include/x86_64-linux-gnu/asm/unistd_64.h:338-339).
- Actual: Source predicts `probe <module> clock_gettime64 403` (analysis/app/src/syspart.cpp:118-149,196-202; /usr/include/asm-generic/unistd.h:782-784). No runtime output was observed.
- Evidence: analysis/app/src/testSyspart.cpp:167 — populates the map before dispatch; analysis/app/src/syspart.cpp:131-149 — reads the generic header first, then the x86-64 header; analysis/app/src/syspart.cpp:118-125 — accepts numeric definitions without checking preprocessor conditions; /usr/include/asm-generic/unistd.h:782-784 — conditionally defines 403 as clock_gettime64; /usr/include/x86_64-linux-gnu/asm/unistd_64.h:338-339 — has no definition between 334 and 424 to overwrite it; analysis/app/src/testSyspart.cpp:424-452 — mode 16 calls findDirectSyscallsOfModule; analysis/app/src/syspart.cpp:191-202 — prints the recovered number with its map name.
- Assessment: A tiny test case is a function containing `mov $403, %eax; syscall`. If FindSyscalls recovers 403 from RAX, mode 16 should print its number with an empty name column, because the local x86-64 header jumps from 334 to 424 (analysis/tools/egalito/src/pass/findsyscalls.cpp:40-45; /usr/include/x86_64-linux-gnu/asm/unistd_64.h:338-339). No binary was run, so the reported name is a source-supported prediction, not observed output.

### A cyclic register definition can recurse without termination

- Status: **supported**
- Kind: logic
- Location: `analysis/tools/egalito/src/pass/findsyscalls.cpp:158`
- Invariant: Register resolution must terminate when reaching definitions form a cycle (analysis/tools/egalito/src/pass/findsyscalls.cpp:108-161).
- Mechanism: The resolver marks a state as seen only after recursively following its register definition. Revisiting a state already on the active recursion path therefore does not stop the cycle (analysis/tools/egalito/src/pass/findsyscalls.cpp:109-119,142-161).
- Reproducer: Source-bounded use-def graph: state A defines RAX from RBX and refers to state B for RBX; B defines RBX from RAX and refers to A for RAX. Register-to-register moves create those references and definitions, and loop predecessors can feed reaching definitions back into a block (analysis/tools/egalito/src/analysis/usedef.cpp:281-295,633-644,726-737,766-774). A syscall using A's RAX starts the lookup (analysis/tools/egalito/src/pass/findsyscalls.cpp:40-45).
- Expected: Terminate on the active cycle, report the syscall number unresolved, and omit its number-map entry (analysis/tools/egalito/src/pass/findsyscalls.cpp:44-50).
- Actual: For the stated reference graph, the source repeatedly descends A → B → A before either state reaches seen.insert; the runtime outcome is unobserved (analysis/tools/egalito/src/pass/findsyscalls.cpp:115-116,142-145,161).
- Evidence: analysis/app/src/testSyspart.cpp:424-452 — mode 16 calls findDirectSyscallsOfModule; analysis/app/src/syspart.cpp:186-194 — that method runs FindSyscalls on each function; analysis/tools/egalito/src/pass/findsyscalls.cpp:32-44 — use-def analysis precedes syscall RAX lookup and seen is cleared; analysis/tools/egalito/src/analysis/usedef.cpp:2092-2105 — the syscall state records an RAX use; analysis/tools/egalito/src/pass/findsyscalls.cpp:115-116,121-145 — register definitions are followed recursively; analysis/tools/egalito/src/pass/findsyscalls.cpp:161 — a state is marked seen only after its references return, so A → B → A remains unguarded.
- Assessment: A tiny x86-64 test is: entry sets RBX to 0; block A moves RBX to RAX and jumps to B; block B moves RAX to RBX, executes syscall, and jumps to A. The loop can give A a reference to B's RBX definition and B a reference to A's RAX definition (analysis/tools/egalito/src/analysis/usedef.cpp:282-295,635-645,726-735,770-775,801). Expected output is an unresolved-syscall warning and no number-map entry (analysis/tools/egalito/src/pass/findsyscalls.cpp:44-50). This is a source-supported prediction; no runtime output was observed.

### Mode 16 copies the entire syscall result before printing it

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspart.cpp:193`
- Invariant: Printing a visitor's syscall rows does not require a second map and copied value sets (analysis/tools/egalito/src/pass/findsyscalls.h:21-22; analysis/app/src/syspart.cpp:193-202).
- Mechanism: `getNumberMap()` returns a const reference, but `auto list` copies the map; iteration copies each entry, then `auto syscallValues` copies its set again (analysis/tools/egalito/src/pass/findsyscalls.h:21-22; analysis/app/src/syspart.cpp:193-198).
- Reproducer: Bounded cost: a scanned function with M recorded syscall sites and V total resolved values causes copies of M map entries and their sets before its V rows are printed (analysis/app/src/syspart.cpp:193-202).
- Expected: Iterate the map and its entries by const reference, with no result-sized copies (analysis/tools/egalito/src/pass/findsyscalls.h:20-21; analysis/app/src/syspart.cpp:194-201).
- Actual: For a function with M recorded sites and V resolved values, the source copies the map and its sets, then copies each entry and its set again. This adds O(M+V) copy work and temporary storage before or during printing (analysis/app/src/syspart.cpp:194-201).
- Evidence: analysis/app/src/testSyspart.cpp:77-87 — -a selects the analysis number; analysis/app/src/testSyspart.cpp:424-452 — case 16 finds a module and calls findDirectSyscallsOfModule; analysis/app/src/syspart.cpp:188-194 — each function is visited, then its result map is copied; analysis/tools/egalito/src/pass/findsyscalls.h:15-21 — getNumberMap returns a const reference to the map; analysis/tools/egalito/src/pass/findsyscalls.cpp:40-45,68-74 — resolved values populate that map; analysis/app/src/syspart.cpp:196-202 — each map entry and then its value set are copied before rows are printed.
- Assessment: The candidate holds when mode 16 finds a module and its visitor records syscall values. The caller skips the scan if the argument lacks a comma or no module matches (analysis/app/src/testSyspart.cpp:426-452); the visitor can also return with an empty result (analysis/tools/egalito/src/pass/findsyscalls.cpp:19-27). For a tiny test, use a module named toy with a function f containing one resolved syscall numbered 39. Expect a row `f toy getpid 39` among mode 16's output (analysis/app/src/syspart.cpp:92,186-202). No runtime output or cost was measured.

<!-- harness:logic:mode-16:end -->

<!-- harness:logic:mode-17:start -->
## Harness logic audit — mode 17

Dispatcher and modules: analysis/app/src/testSyspart.cpp, analysis/app/src/syspart.cpp, analysis/app/src/ipcallgraph.cpp, analysis/app/src/ipcallgraph.h

### Mode 17 prints no syscall information

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:258`
- Invariant: A syscall summary requires an entry in syscall_mapping (analysis/app/src/syspart.cpp:161; analysis/app/src/syspart.cpp:676-680).
- Mechanism: Mode 17 calls getSyscallInfo for graph nodes but never calls findDirectSyscalls, which creates the mapping (analysis/app/src/syspart.cpp:240-280; analysis/app/src/syspart.cpp:282-323).
- Reproducer: Source trace: select a module containing a function with a syscall and run -a 17,<module> (analysis/app/src/testSyspart.cpp:456-484; analysis/app/src/syspart.cpp:258-260).
- Expected: For `probe`, syscall summary lines including `Total syscalls of probe : 1` and `Direct : probe : getpid` (analysis/app/src/syspart.cpp:683-690).
- Actual: The source path skips those summary lines because getSyscallInfo returns on a null mapping lookup (analysis/app/src/syspart.cpp:161-172; analysis/app/src/syspart.cpp:676-680). Runtime output was not observed.
- Evidence: analysis/app/src/testSyspart.cpp:153-167 — a fresh Syspart is initialized, and populateSyscallMap fills syscall names (analysis/app/src/syspart.cpp:153-158). analysis/app/src/testSyspart.cpp:456-484 — mode 17 calls findCallGraphOfModule. analysis/app/src/syspart.cpp:240-260 — that method generates the graph and calls getSyscallInfo without calling findDirectSyscalls. analysis/app/src/syspart.cpp:282-323 — findDirectSyscalls is the method that inserts entries into syscall_mapping. analysis/app/src/syspart.cpp:161-172 — getSysNode returns null when the mapping is empty. analysis/app/src/syspart.cpp:676-684 — getSyscallInfo then returns before printing a summary.
- Assessment: The mode 17 path generates a call graph but never creates the syscall mapping required by getSyscallInfo (analysis/app/src/syspart.cpp:240-260; analysis/app/src/syspart.cpp:282-323). A tiny test would use a module with a function `probe` containing a direct `getpid` syscall. Its expected summary would include `Total syscalls of probe : 1` and `Direct : probe : getpid` (analysis/app/src/syspart.cpp:683-690). No binary was run, so this is a source-supported finding.

### The reported callgraph omits indirect edges

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:251`
- Invariant: Without -g, the documented callgraph includes indirect edges (analysis/app/src/testSyspart.cpp:103; analysis/app/src/testSyspart.cpp:120).
- Mechanism: Generation records indirect targets, but mode 17 calls printDirectEdges, which reads only direct children (analysis/app/src/ipcallgraph.cpp:1835-1836; analysis/app/src/syspart.cpp:249-251; analysis/app/src/ipcallgraph.cpp:383-397).
- Reproducer: Source-bounded graph: a selected-module function makes one indirect call to an address-taken function and has no direct calls (analysis/app/src/ipcallgraph.cpp:664-715; analysis/app/src/syspart.cpp:243-251).
- Expected: The mode 17 edge report includes the caller-to-target edge when `-g` is absent (analysis/app/src/testSyspart.cpp:103; analysis/app/src/ipcallgraph.cpp:127-139; analysis/app/src/ipcallgraph.cpp:330-350).
- Actual: The mode 17 edge report omits an edge present only among indirect children; this is predicted from source, not observed output (analysis/app/src/syspart.cpp:251; analysis/app/src/ipcallgraph.cpp:383-397).
- Evidence: analysis/app/src/testSyspart.cpp:74 — `-g` sets `direct_flag`; analysis/app/src/testSyspart.cpp:456-484 — mode 17 calls `findCallGraphOfModule` without passing that flag; analysis/app/src/syspart.cpp:243-251 — the method adds module functions as roots, generates the graph, then calls `printDirectEdges`; analysis/app/src/ipcallgraph.cpp:1835-1836 — generation processes indirect edges; analysis/app/src/ipcallgraph.cpp:711-715 — unresolved indirect targets are inserted as indirect children; analysis/app/src/ipcallgraph.cpp:48-50 — the insertion flag selects the indirect-child map; analysis/app/src/ipcallgraph.cpp:383-397 — `printDirectEdges` reads only direct children. The later output is an address-taken list, not the callgraph edge report (analysis/app/src/syspart.cpp:252-279).
- Assessment: A tiny test would define an address-taken target and a selected-module caller whose only call is through a function pointer. Its callgraph should contain a `caller <address> (...) -> target <address> (...)` edge without `-g`, as the option documentation says indirect edges are considered by default (analysis/app/src/testSyspart.cpp:103; analysis/app/src/testSyspart.cpp:121). This is a source-supported prediction; no binary was run.

### Mode 17 filters the address-taken list even without -i

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:247`
- Invariant: The -i option controls whether indirect-call target analysis filters address-taken functions (analysis/app/src/testSyspart.cpp:101; analysis/app/src/ipcallgraph.cpp:1377-1384).
- Mechanism: Mode 17 enables icanalysis unconditionally. When forwardDataFlow returns true for a linked function reference, findATList omits that function from globalATList, which mode 17 prints (analysis/app/src/syspart.cpp:247-255; analysis/app/src/ipcallgraph.cpp:1370-1385).
- Reproducer: Source-bounded case: a selected-module function has a linked reference to a function for which forwardDataFlow returns true; invoke -a 17,<module> without -i (analysis/app/src/ipcallgraph.cpp:1370-1385; analysis/app/src/testSyspart.cpp:456-484).
- Expected: Without `-i`, `target` appears in the global address-taken rows under the fixture conditions (analysis/app/src/ipcallgraph.cpp:1377-1378, analysis/app/src/syspart.cpp:252-257).
- Actual: The source selects the filtering branch even without `-i`; when forward flow returns true and no other path inserts `target`, its row is absent. No runtime output was observed (analysis/app/src/syspart.cpp:247-249, analysis/app/src/ipcallgraph.cpp:1379-1385, analysis/app/src/syspart.cpp:252-257).
- Evidence: analysis/app/src/testSyspart.cpp:26,68 — `-i` controls the parsed flag; analysis/app/src/testSyspart.cpp:456-484 — mode 17 calls `findCallGraphOfModule` without passing that flag; analysis/app/src/syspart.cpp:240-249 — the method sets the graph flag to true and generates the graph; analysis/app/src/ipcallgraph.cpp:1766-1790 — generation reaches `findATList`; analysis/app/src/ipcallgraph.cpp:1370-1385 — a linked function reference is inserted only when forward flow returns false under that flag; analysis/app/src/ipcallgraph.cpp:1797-1811 — the flag also triggers indirect-call target analysis; analysis/app/src/syspart.cpp:252-257 — mode 17 prints the resulting global list. Other data-reference paths can independently insert the same function, so the omission depends on the fixture having no such reference (analysis/app/src/ipcallgraph.cpp:1536-1549, analysis/app/src/ipcallgraph.cpp:1631-1643).
- Assessment: A tiny fixture could contain a module function that loads the address of `target` into a register and calls through that register, with no data-section reference to `target`. Run mode 17 on that module with `-p`, `-s main`, and without `-i`; those arguments satisfy the command guards (analysis/app/src/testSyspart.cpp:137-151, analysis/app/src/testSyspart.cpp:456-484). If the load is represented as a linked instruction and the call reaches the indirect-call handler, the handler returns true and the printed global list omits `target` (analysis/app/src/ipcallgraph.cpp:1359-1374, analysis/app/src/ipcallgraph.cpp:1179-1192, analysis/app/src/ipcallgraph.cpp:1377-1385, analysis/app/src/syspart.cpp:252-257). Expected without `-i`: a `target` row and a global-list count one higher, provided no other reference inserts `target` (analysis/app/src/ipcallgraph.cpp:1377-1378, analysis/app/src/ipcallgraph.cpp:1536-1549, analysis/app/src/syspart.cpp:253-257).

### Indirect-target refinement scans every graph node for a direct-edge report

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspart.cpp:247`
- Invariant: Reporting direct edges does not require resolving indirect-call targets (analysis/app/src/syspart.cpp:251; analysis/app/src/ipcallgraph.cpp:383-397).
- Mechanism: The forced icanalysis setting makes generate initialize target analysis and scan every graph node at least once, repeating the scan while it resolves sites (analysis/app/src/syspart.cpp:247-249; analysis/app/src/ipcallgraph.cpp:1797-1810).
- Reproducer: Bounded case: a selected module yields N graph nodes and no indirect calls. Mode 17 still performs an N-node refinement pass before printing direct edges (analysis/app/src/syspart.cpp:243-251; analysis/app/src/ipcallgraph.cpp:1800-1810).
- Expected: The direct-edge portion can be printed after direct-edge construction without an indirect-target refinement pass (analysis/app/src/ipcallgraph.cpp:1770-1775; analysis/app/src/ipcallgraph.cpp:383-397).
- Actual: The source forces refinement, including initialization and at least one full graph-node scan, before printing direct edges (analysis/app/src/syspart.cpp:247-251; analysis/app/src/ipcallgraph.cpp:1797-1810; analysis/app/src/syspartUtility.cpp:1448-1453).
- Evidence: analysis/app/src/testSyspart.cpp:456-484 — mode 17 selects a module and calls `findCallGraphOfModule`; analysis/app/src/syspart.cpp:243-249 — it adds module functions as roots, forces indirect analysis, then calls `generate`; analysis/app/src/ipcallgraph.cpp:1770-1790 — direct edges and address-taken lists are processed before refinement; analysis/app/src/ipcallgraph.cpp:1797-1810 — refinement initializes and scans every node at least once; analysis/app/src/syspartUtility.cpp:1448-1453 — initialization itself visits every node; analysis/app/src/syspartUtility.cpp:986-992,1141-1157 — each refinement call obtains a working set and walks instructions before skipping those that are not indirect calls or jumps; analysis/app/src/ipcallgraph.cpp:383-397 — direct-edge printing reads direct children.
- Assessment: A tiny test case is a module `toy` containing `a` at 0x1000, `b` at 0x1010, one direct call from `a` to `b`, and no indirect calls. The direct-edge portion of the report should contain `a 1000 (toy) -> b 1010 (toy)` and `TOTAL DIRECT EDGES OF CALLGRAPH : 1` (analysis/app/src/ipcallgraph.cpp:891-895; analysis/app/src/ipcallgraph.cpp:383-397). Even for this case, mode 17 forces indirect analysis and `generate()` enters a do-while loop that visits every graph node at least once (analysis/app/src/syspart.cpp:243-249; analysis/app/src/ipcallgraph.cpp:1797-1810). This is a source-supported cost finding; no runtime cost or output was observed. Mode 17 also reports address-taken functions and sites, so the finding applies specifically to its direct-edge output (analysis/app/src/syspart.cpp:251-279).

### Mode 17 joins the address-taken header to the first result

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:263`
- Invariant: The address-taken column header and its rows must occupy separate lines (analysis/app/src/syspart.cpp:263-275).
- Mechanism: The header write has no newline; the next write prints either the first address-taken row or the final count (analysis/app/src/syspart.cpp:263-279).
- Reproducer: Source-bounded case: select a module with one address-taken site using -a 17,<module>; the first row begins immediately after AT_FN_MODULE (analysis/app/src/testSyspart.cpp:456-484; analysis/app/src/syspart.cpp:263-275).
- Expected: Header line, then `src\t10\tM\t20\tdst\t30\tM` on a separate line (analysis/app/src/syspart.cpp:263-275).
- Actual: Source predicts `AT_FN_MODULE src\t10\tM\t20\tdst\t30\tM` on one line for that case (analysis/app/src/syspart.cpp:263-275).
- Evidence: analysis/app/src/testSyspart.cpp:77-86 — -a selects the analysis number; analysis/app/src/testSyspart.cpp:456-484 — mode 17 requires a comma and a matching module, then calls findCallGraphOfModule; analysis/app/src/syspart.cpp:240-263 — the function generates the graph and prints the header without a newline; analysis/app/src/syspart.cpp:264-279 — the first address-taken row, or the final count if there is no row, is the next write. The comparable header in run5 includes a newline (analysis/app/src/syspart.cpp:1950).
- Assessment: A tiny test case is a module whose analysis produces one address-taken entry: source function src at 0x10, instruction 0x20, target dst at 0x30, all in module M. The expected output has a header line followed by `src\t10\tM\t20\tdst\t30\tM` on its own line (analysis/app/src/syspart.cpp:263-275). This is a source prediction; no runtime output was captured.

### Mode 17 eagerly builds use-def analyses for every module function

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/ipcallgraph.cpp:164`
- Invariant: A function needing only direct-edge and address-taken scans does not need use-def analysis before those scans (analysis/app/src/ipcallgraph.cpp:872-924; analysis/app/src/ipcallgraph.cpp:1345-1375).
- Mechanism: Mode 17 seeds every selected-module function through addFunctionRoot, which immediately requests a working set. A cache miss constructs a CFG and runs use-def analysis before graph generation starts (analysis/app/src/syspart.cpp:243-249; analysis/app/src/ipcallgraph.cpp:155-165; analysis/tools/egalito/src/analysis/dataflow.cpp:13-34).
- Reproducer: Bounded case: a module has N functions with direct calls but no address-taken references or indirect sites. Seeding still runs N use-def analyses, while the direct-edge scan reads instruction links (analysis/app/src/syspart.cpp:243-249; analysis/app/src/ipcallgraph.cpp:872-924; analysis/tools/egalito/src/analysis/dataflow.cpp:29-34).
- Expected: For the proposed f→g case, one direct edge, a direct-edge total of 1, and no global AT functions (analysis/app/src/ipcallgraph.cpp:392-410; analysis/app/src/syspart.cpp:250-256).
- Actual: Source predicts one CFG and use-def analysis per selected function during seeding, plus another per graph node in SyspartUtility; no time or memory cost was measured (analysis/app/src/ipcallgraph.cpp:155-165,1799-1808; analysis/app/src/syspartUtility.cpp:1448-1453; analysis/tools/egalito/src/analysis/dataflow.cpp:13-26).
- Evidence: analysis/app/src/testSyspart.cpp:456-484 — mode 17 calls findCallGraphOfModule for the matched module; analysis/app/src/syspart.cpp:240-249 — it seeds every function before generate; analysis/app/src/ipcallgraph.cpp:155-165 — first insertion requests a working set; analysis/tools/egalito/src/analysis/dataflow.cpp:13-34 — a cache miss builds a CFG and runs use-def analysis; analysis/app/src/ipcallgraph.cpp:1766-1794 — direct-edge and AT scans follow seeding; analysis/app/src/ipcallgraph.cpp:1799-1808 — indirect resolution initializes a separate utility and visits every node; analysis/app/src/syspartUtility.cpp:986-993,1140-1157,1448-1453 — the utility builds use-def state before checking instructions for indirect calls.
- Assessment: The candidate's eager cost is supported by source. The duplicate-root and existing-node guards can skip work, but mode 17 seeds each distinct function in the selected module, so they do not protect those functions on first insertion (analysis/app/src/testSyspart.cpp:456-484; analysis/app/src/syspart.cpp:240-249; analysis/app/src/ipcallgraph.cpp:155-165). The cost is greater than stated: graph generation creates a separate SyspartUtility whose initialize method runs use-def analysis for every graph node, even when there are no indirect sites (analysis/app/src/ipcallgraph.cpp:1799-1808; analysis/app/src/syspartUtility.h:193; analysis/app/src/syspartUtility.cpp:1448-1453). Tiny proposed test: a module containing only f and g, with one linked direct call f→g and no address-taken reference or indirect site. The expected report has one direct edge and `TOTAL DIRECT EDGES OF CALLGRAPH : 1`, with an empty global AT list (analysis/app/src/ipcallgraph.cpp:872-924; analysis/app/src/ipcallgraph.cpp:392-410; analysis/app/src/syspart.cpp:250-256). No output was captured.

### Mode 17 labels two different totals as the global address-taken list

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:279`
- Invariant: Repeated totals with the same label should count the same quantity (analysis/app/src/syspart.cpp:257; analysis/app/src/syspart.cpp:279).
- Mechanism: The first #GLOBAL AT LIST total uses the size of the unique-function set. The second increments once per address-taken instruction site (analysis/app/src/syspart.cpp:252-257; analysis/app/src/syspart.cpp:267-279).
- Reproducer: Source-bounded case: two distinct instructions take the same function's address and both references enter the global set. The set has size one, while the site loop increments twice (analysis/app/src/ipcallgraph.cpp:1370-1385; analysis/app/src/syspart.cpp:252-279).
- Expected: For the stated test case, distinct totals such as "#GLOBAL AT FUNCTIONS : 1" and "#AT SITES : 2" (analysis/app/src/syspart.cpp:252-279).
- Actual: The source predicts "#GLOBAL AT LIST : 1" and later "#GLOBAL AT LIST : 2" for that case; this is not runtime-confirmed (analysis/app/src/syspart.cpp:257; analysis/app/src/syspart.cpp:267-279).
- Evidence: analysis/app/src/syspart.cpp:242-249 — mode 17 adds module functions as roots, enables indirect-call analysis, and generates the graph; analysis/app/src/ipcallgraph.cpp:1370-1385 — each qualifying instruction adds an address-taken site, while a false forwardDataFlow result permits insertion into the global function set; analysis/app/src/ipcallgraph.h:148-152 — sites are keyed by instruction address; analysis/app/src/ipcallgraph.h:327 — the global list is a set of functions; analysis/app/src/syspart.cpp:252-257 — the first labeled total is the set size; analysis/app/src/syspart.cpp:264-279 — the second identically labeled total increments once per site key.
- Assessment: The mode 17 caller reaches findCallGraphOfModule after finding the requested module (analysis/app/src/testSyspart.cpp:456-485). A tiny source-bounded test case is one module with a function f and two distinct non-control-flow linked instructions in another function, both targeting f, with forwardDataFlow returning false at both sites and no other address-taken references (analysis/app/src/ipcallgraph.cpp:1352-1359; analysis/app/src/ipcallgraph.cpp:1370-1385). Expected totals: one global function and two address-taken instruction sites, with distinct labels (analysis/app/src/ipcallgraph.h:327; analysis/app/src/ipcallgraph.h:148-152; analysis/app/src/syspart.cpp:252-279).

<!-- harness:logic:mode-17:end -->

<!-- harness:logic:mode-18:start -->
## Harness logic audit — mode 18

Dispatcher and modules: analysis/app/src/testSyspart.cpp, analysis/app/src/syspart.cpp, analysis/app/src/ipcallgraph.cpp, analysis/app/src/ipcallgraph.h

### A named function outside the constructed graph is reported as size zero

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:2094`
- Invariant: A found function must have its instructions counted before mode 18 reports its partition size (analysis/app/src/syspart.cpp:2081; analysis/app/src/syspart.cpp:2099-2103; analysis/app/src/syspart.cpp:2126).
- Mechanism: Mode 18 builds the graph from the -s root before looking up the requested function. If that function has no graph node, traversal skips it and prints the unchanged zero count (analysis/app/src/syspart.cpp:2070-2085; analysis/app/src/syspart.cpp:2094-2096; analysis/app/src/syspart.cpp:2126). Direct graph traversal processes queued roots and their discovered callees (analysis/app/src/ipcallgraph.cpp:1746-1751; analysis/app/src/ipcallgraph.cpp:891-895).
- Reproducer: Source-bounded case: root and other are parsed functions; other contains one instruction but has no call or address reference from any graph root. Request -s root -g -a 18,other (analysis/app/src/testSyspart.cpp:488-497; analysis/app/src/ipcallgraph.cpp:1746-1761).
- Expected: Partition size of function other 1
- Actual: Source-predicted: Partition size of function other 0; no runtime output observed.
- Evidence: analysis/app/src/testSyspart.cpp:179-182 — `-s` selects the graph root; analysis/app/src/testSyspart.cpp:488-498 — mode 18 passes the requested name to `getPartitionSize`; analysis/app/src/syspart.cpp:2069-2084 — graph construction precedes lookup and traversal; analysis/app/src/ipcallgraph.cpp:169-178 — `setRoot` creates the root node; analysis/app/src/ipcallgraph.cpp:1742-1761 — direct generation traverses queued roots; analysis/app/src/ipcallgraph.cpp:891-895 — a discovered callee becomes a root; analysis/app/src/ipcallgraph.cpp:453-483 — initializer references can also add roots, excluded by the test case; analysis/app/src/ipcallgraph.h:355-371 — `getNode` returns null when neither the function nor a matching name in its module has a node; analysis/app/src/syspart.cpp:2094-2103 — a null node skips instruction counting; analysis/app/src/syspart.cpp:2126 — the count is printed.
- Assessment: A tiny test case would contain two uniquely named parsed functions: `root` and `other`, each with one instruction, with no call or address reference to `other` and no initializer reference to it. Run mode 18 with `-s root -g -a 18,other`; the expected partition line is `Partition size of function other 1`, but the source predicts `Partition size of function other 0`. Mode 18 constructs the graph before looking up `other`, incurring graph construction even when the requested function has no node (analysis/app/src/syspart.cpp:2069-2081). No binary was built or run.

### Partition traversal copies both child maps for every visited function

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspart.cpp:2097`
- Invariant: Reading callsite edges should not require duplicate maps of those edges during counting (analysis/app/src/syspart.cpp:2105-2118).
- Mechanism: Both getters return maps by value, and mode 18 stores both returned maps before scanning instructions. Thus each visited function copies every direct and indirect callsite entry, including entries the instruction loop never matches (analysis/app/src/ipcallgraph.h:207-213; analysis/app/src/syspart.cpp:2097-2118).
- Reproducer: Bounded cost: for one visited function with D direct and J indirect callsite entries, these two getter calls allocate and copy D+J map entries before counting its instructions; across visited functions the extra copying sums over their callsite entries (analysis/app/src/ipcallgraph.h:207-213; analysis/app/src/syspart.cpp:2097-2099).
- Expected: Read-only counting could inspect the existing maps without copying their entries (analysis/app/src/syspart.cpp:2105-2118).
- Actual: Source requires copies of both maps for each visited node that passes the null check; runtime cost was not measured (analysis/app/src/syspart.cpp:2090-2098; analysis/app/src/ipcallgraph.h:207-213).
- Evidence: analysis/app/src/testSyspart.cpp:488-497 — mode 18 passes the function name to getPartitionSize; analysis/app/src/syspart.cpp:2090-2096 — visited and null-node guards precede the getters; analysis/app/src/ipcallgraph.h:207-213 — each getter returns its map by value; analysis/app/src/syspart.cpp:2097-2118 — both results are stored before instruction-address lookups.
- Assessment: The candidate holds for each visited function with a non-null callgraph node: both getters return maps by value, so the traversal copies their map entries before looking up instruction addresses (analysis/app/src/syspart.cpp:2090-2098; analysis/app/src/ipcallgraph.h:207-213). The values are shared pointers, so this does not copy the target vectors (analysis/app/src/ipcallgraph.h:108-116). Tiny test: give function f two instructions, a direct edge from one to a one-instruction leaf, and an indirect-map entry at an address matching neither instruction. Expected output: "Partition size of function f 3"; the unmatched entry is still copied before the lookups (analysis/app/src/syspart.cpp:2097-2126).

### An unknown mode 18 function reaches a null dereference

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:2094`
- Invariant: The requested function must resolve before mode 18 looks up its graph node (analysis/app/src/syspart.cpp:2081; analysis/app/src/ipcallgraph.h:355-369).
- Mechanism: The CLI accepts an empty or unknown name after the comma; findFunctionByName returns null when nothing matches. getPartitionSize pushes that null pointer and passes it to getNode, which dereferences it while searching for a fallback node (analysis/app/src/testSyspart.cpp:488-497; analysis/app/src/syspart.cpp:66-80,2081-2094; analysis/app/src/ipcallgraph.h:355-361).
- Reproducer: Source-bounded case: use a valid -s root and -a 18,__missing_function__ where no loaded function has that name (analysis/app/src/testSyspart.cpp:179-183,488-497; analysis/app/src/syspart.cpp:66-80).
- Expected: Reject an unknown function before graph construction or node lookup (analysis/app/src/syspart.cpp:2069-2094).
- Actual: The source predicts a null dereference on the getNode miss path; no runtime output was observed (analysis/app/src/syspart.cpp:2081-2094; analysis/app/src/ipcallgraph.h:355-361).
- Evidence: analysis/app/src/testSyspart.cpp:490-497 — the handler checks for a comma but does not validate the extracted name; analysis/app/src/syspart.cpp:66-80 — an unmatched name returns null; analysis/app/src/syspart.cpp:2081-2094 — that pointer is pushed and passed to getNode without a guard; analysis/app/src/ipcallgraph.h:355-361 — if the null key is absent, getNode calls f->getName() on null.
- Assessment: The mode 18 handler accepts any text after the comma, including an unknown name, and passes it to getPartitionSize (analysis/app/src/testSyspart.cpp:488-497). A tiny regression case is `-p <valid-binary> -s <known-root> -a 18,__missing_function__`, with no loaded function of that name; its expected output after a fix is an unknown-function diagnostic and a nonzero exit (analysis/app/src/testSyspart.cpp:179-183,488-497; analysis/app/src/syspart.cpp:66-80,2081-2094). The lookup also occurs after call-graph construction, making that analysis cost avoidable for an invalid name (analysis/app/src/syspart.cpp:2069-2081).

### Partition counting searches both callsite maps at every instruction

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspart.cpp:2105`
- Invariant: Counting N instructions and traversing C callsite entries should not require callsite-map searches for instructions with no call edge (analysis/app/src/syspart.cpp:2097-2118).
- Mechanism: For every instruction, the traversal performs one lookup in each ordered child map, even though those maps contain only callsite entries (analysis/app/src/ipcallgraph.h:121-122,207-213; analysis/app/src/syspart.cpp:2099-2115).
- Reproducer: Bounded cost: a visited function with N instructions and C callsites incurs 2N ordered-map lookups; with C at least two, that adds O(N log C) lookup work while counting the N instructions (analysis/app/src/syspart.cpp:2097-2115).
- Expected: Count instructions while traversing callsite entries without two map searches per instruction, provided the entries correspond to instructions (analysis/app/src/syspart.cpp:2099-2118).
- Actual: The source establishes two searches per counted instruction and a copy of each child map per visited node; runtime cost was not measured (analysis/app/src/ipcallgraph.h:207-213; analysis/app/src/syspart.cpp:2097-2115).
- Evidence: analysis/app/src/testSyspart.cpp:488-497 — mode 18 invokes getPartitionSize; analysis/app/src/syspart.cpp:2069-2080 — it generates the call graph; analysis/app/src/syspart.cpp:2094-2101 — it guards missing nodes, then enters the instruction loop; analysis/app/src/syspart.cpp:2103-2115 — it counts each instruction and searches both maps; analysis/app/src/ipcallgraph.h:121-122,207-213 — both child maps are ordered maps returned by value.
- Assessment: Mode -a 18 calls getPartitionSize (analysis/app/src/testSyspart.cpp:488-497). The only guard before instruction traversal skips a missing graph node; there is no callsite guard inside the instruction loop (analysis/app/src/syspart.cpp:2094-2115). Each counted instruction therefore triggers two ordered-map searches, including instructions with no call edge (analysis/app/src/ipcallgraph.h:121-122; analysis/app/src/syspart.cpp:2099-2115). Tiny test: let f have three instructions, one directly calling g, and let g have two instructions. With that edge in the generated graph, expect `Partition size of function f 5` and ten callsite-map searches across the five instructions (analysis/app/src/ipcallgraph.cpp:223-246; analysis/app/src/syspart.cpp:2099-2126).

<!-- harness:logic:mode-18:end -->

<!-- harness:logic:mode-19:start -->
## Harness logic audit — mode 19

Dispatcher and modules: README.md, analysis/app/README.md, analysis/app/src/testSyspart.cpp, analysis/app/src/syspart.h, analysis/app/src/syspart.cpp, analysis/app/src/ipcallgraph.h, analysis/app/src/ipcallgraph.cpp

### Mode 19 ignores the supplied TypeArmor file

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:1977`
- Invariant: When -t is supplied, its path must reach the graph parser before indirect targets are filtered (analysis/app/src/testSyspart.cpp:64-65; analysis/app/src/ipcallgraph.cpp:503; analysis/app/src/ipcallgraph.cpp:809).
- Mechanism: The driver stores the path on Syspart, but run6 sets only the graph's TypeArmor flag. The graph has a separate path field, and its parser opens that field (analysis/app/src/testSyspart.cpp:184-185; analysis/app/src/syspart.cpp:1977; analysis/app/src/ipcallgraph.h:290-291; analysis/app/src/ipcallgraph.cpp:532).
- Reproducer: Source-bounded case: run -a 19 -t with a file containing callsite argument metadata. The parser opens its default empty path instead of the supplied path (analysis/app/src/testSyspart.cpp:64-65; analysis/app/src/ipcallgraph.h:291; analysis/app/src/ipcallgraph.cpp:532-535).
- Expected: The supplied metadata prunes an ineligible indirect target (analysis/app/src/ipcallgraph.cpp:814-821; analysis/app/src/ipcallgraph.cpp:846-864).
- Actual: For a fresh mode 19 invocation, the graph path remains empty, so the supplied file is not loaded and an indirect callsite without metadata retains its candidates (analysis/app/src/testSyspart.cpp:153; analysis/app/src/syspart.cpp:1973-1981; analysis/app/src/ipcallgraph.h:291; analysis/app/src/ipcallgraph.cpp:532-535; analysis/app/src/ipcallgraph.cpp:824-833).
- Evidence: analysis/app/src/testSyspart.cpp:64-65 — -t stores the flag and path; analysis/app/src/testSyspart.cpp:184-185 — the path reaches Syspart; analysis/app/src/testSyspart.cpp:500-503 — mode 19 calls run6; analysis/app/src/syspart.cpp:1973-1981 — run6 enables TypeArmor and generates the graph without passing the path; analysis/app/src/ipcallgraph.h:289-291 — the graph has separate flag and path fields; analysis/app/src/ipcallgraph.h:385-391 — their setters are separate; analysis/app/src/ipcallgraph.cpp:1815-1816 — generation calls the parser; analysis/app/src/ipcallgraph.cpp:532-535 — the parser opens the graph's path only if the file opens; analysis/app/src/ipcallgraph.cpp:824-833 — absent callsite metadata retains the candidate set. Another mode explicitly passes the path (analysis/app/src/syspart.cpp:1544-1546).
- Assessment: A tiny test would use one unresolved indirect call in main whose candidate set includes pthread_create. Supply TypeArmor records marking the callsite as passing 0 arguments and pthread_create as requiring 4 (analysis/app/src/ipcallgraph.cpp:602-605; analysis/app/src/ipcallgraph.cpp:595-600). With the supplied file loaded, the expected output has no “pthread_create is invoked in main” line because the target is pruned (analysis/app/src/ipcallgraph.cpp:846-864; analysis/app/src/syspart.cpp:1999-2000). This is a source-supported prediction, not observed output.

### A similarly named helper is reported as pthread_create

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:1997`
- Invariant: A pthread_create report and thread-start lookup must identify a call to that function, rather than any function whose name contains its name (analysis/app/src/testSyspart.cpp:128; analysis/app/src/syspart.cpp:1180; analysis/app/src/syspart.cpp:1997).
- Mechanism: Both reporting and thread-start discovery use substring matching on the callee name (analysis/app/src/syspart.cpp:1180; analysis/app/src/syspart.cpp:1212; analysis/app/src/syspart.cpp:1997).
- Reproducer: Source-bounded case: root directly calls an ordinary helper named my_pthread_create_helper. The graph records that callee and run6 matches its name (analysis/app/src/ipcallgraph.cpp:891-895; analysis/app/src/syspart.cpp:1986-1998).
- Expected: The helper produces no pthread_create invocation report or thread-start analysis (analysis/app/src/testSyspart.cpp:123; analysis/app/src/syspart.cpp:1165-1184).
- Actual: The source predicts an invocation line naming my_pthread_create_helper and a use-def/RDX analysis of its caller; whether an entry function is printed depends on resolving RDX (analysis/app/src/syspart.cpp:1999-2000; analysis/app/src/syspart.cpp:1134-1156; analysis/app/src/syspart.cpp:1183-1199).
- Evidence: analysis/app/src/testSyspart.cpp:500-503 — mode 19 calls run6. analysis/app/src/syspart.cpp:1973-1981 — run6 builds the call graph from the selected root. analysis/app/src/ipcallgraph.cpp:891-895 — a direct call to a local function adds its target as an edge. analysis/app/src/ipcallgraph.cpp:127-139 — getAllCallTargets includes direct children. analysis/app/src/syspart.cpp:1992-2000 — run6 reports any target whose name contains pthread_create; line 1997 is the separate fork check. analysis/app/src/syspart.cpp:1173-1184 — thread-start discovery applies the same substring check to direct children. analysis/app/src/syspart.cpp:1134-1156 — a match triggers full use-def analysis and an RDX lookup.
- Assessment: A tiny test case is a root function that directly calls a noinline helper named my_pthread_create_helper, passing an entry function as its third argument. Expected output: no invocation report for that helper and no thread-start entry from that call. The source instead matches the helper’s name as pthread_create (analysis/app/src/syspart.cpp:1999) and attempts thread-start analysis of the call site (analysis/app/src/syspart.cpp:1173-1184). No runtime output was captured.

### A RIP-relative pointer load resolves to its storage address

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:1124`
- Invariant: For a thread entry loaded from a pointer variable, resolution must use the pointer's value to identify the function (analysis/app/src/syspart.cpp:1117-1126; analysis/app/src/syspart.cpp:1184-1191).
- Mechanism: The RIPDerefValue branch computes RIP plus displacement and stores that address without reading the dereferenced value. The caller then searches for a Function at the computed address (analysis/app/src/syspart.cpp:1117-1126; analysis/app/src/syspart.cpp:1185-1187).
- Reproducer: Source-bounded case: a call to pthread_create loads RDX from a RIP-relative global pointer slot G containing the address of worker. If its definition reaches RIPDerefValue, resolution searches for a function at G (analysis/app/src/syspart.cpp:1153-1156; analysis/app/src/syspart.cpp:1117-1126; analysis/app/src/syspart.cpp:47-61).
- Expected: For the proposed case, the printed thread-start list contains worker, whose address is stored in G (analysis/app/src/syspart.cpp:2010-2014).
- Actual: Source-predicted: lookup uses G's address, so worker is omitted unless another path resolves it; no runtime output was observed (analysis/app/src/syspart.cpp:1122-1126; analysis/app/src/syspart.cpp:1185-1191).
- Evidence: analysis/app/src/syspart.cpp:1179-1184 — a pthread_create call invokes find_thread_function; analysis/app/src/syspart.cpp:1150-1156 — it traces RDX at the call; analysis/app/src/syspart.cpp:1117-1126 — RIPDerefValue stores RIP plus displacement, the address of G, without reading G; analysis/app/src/syspart.cpp:1185-1191 — the caller looks for a Function at that stored address; analysis/app/src/syspart.cpp:47-61 — lookup compares function addresses.
- Assessment: The earlier linked-instruction check can resolve a Function target, but a RIP-relative reference to a data slot can receive a data link and reach the dereference branch (analysis/app/src/syspart.cpp:1088-1098; analysis/tools/egalito/src/instr/linked-x86_64.cpp:145-155). Tiny test case: define a global function-pointer slot G containing &worker, load RDX from G, then call pthread_create. If that load reaches RIPDerefValue, mode -a 19 should print worker under "Thread start functions :" (analysis/app/src/testSyspart.cpp:500-503; analysis/app/src/syspart.cpp:2010-2014).

### Thread-start discovery retains a fresh analysis for every matching callsite

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspart.cpp:1136`
- Invariant: Analyzing P pthread_create callsites need not retain P separate CFG and use-def allocations through mode completion (analysis/app/src/syspart.cpp:1174-1184; analysis/app/src/syspart.cpp:1205-1216).
- Mechanism: Each matching site calls find_thread_function, which allocates a CFG, configuration, working set, and UseDef, analyzes the CFG, and returns without deleting those allocations (analysis/app/src/syspart.cpp:1134-1163; analysis/app/src/syspart.cpp:1180-1184; analysis/app/src/syspart.cpp:1212-1216).
- Reproducer: Bounded cost: one caller with P matching callsites invokes P full CFG and use-def analyses and retains their allocations until process exit; each invocation also scans the caller's blocks for its callsite (analysis/app/src/syspart.cpp:1136-1156; analysis/app/src/syspart.cpp:1174-1184).
- Expected: Temporary analysis allocations could be released after the callsite result is obtained (analysis/app/src/syspart.cpp:1150-1156).
- Actual: The source performs a fresh analysis for each matching callsite and shows no release path before returning (analysis/app/src/syspart.cpp:1136-1163; analysis/app/src/syspart.cpp:1180-1184; analysis/app/src/syspart.cpp:1212-1216).
- Evidence: analysis/app/src/testSyspart.cpp:500-503 — mode 19 calls run6; analysis/app/src/syspart.cpp:2010 — run6 calls getThreadStartFunction; analysis/app/src/syspart.cpp:1174-1204,1205-1236 — each matching direct or indirect callsite invokes find_thread_function, with the break confined to that callsite's target loop; analysis/app/src/syspart.cpp:1136-1142 — each invocation allocates a CFG, configuration, working set, and UseDef, then analyzes the CFG; analysis/app/src/syspart.cpp:1145-1156 — it scans blocks for the address and reads RDX state; analysis/app/src/syspart.cpp:1156-1163 — both return paths omit release of those allocations.
- Assessment: A tiny test case would put two pthread_create calls in one function, each passing a different thread entry function. Expected mode -a 19 output would list both entry functions under "Thread start functions" (analysis/app/src/testSyspart.cpp:500-503; analysis/app/src/syspart.cpp:2010-2015). This is a source-supported cost finding; no runtime cost or memory measurement was made.

### Mode 19 loads an unused syscall-name map

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/testSyspart.cpp:167`
- Invariant: Fork and thread reporting requires the call graph and thread-entry resolver, not syscall names (analysis/app/src/syspart.cpp:1971-2014).
- Mechanism: The driver unconditionally calls populateSyscallMap before dispatch; that routine reads and parses two system headers or builds a default map, while run6 uses graph targets and thread-start functions (analysis/app/src/testSyspart.cpp:167; analysis/app/src/syspart.cpp:95-158; analysis/app/src/syspart.cpp:1971-2014).
- Reproducer: Bounded cost: every -a 19 invocation parses both available headers line by line, or constructs the fallback map, before entering run6 (analysis/app/src/syspart.cpp:131-158; analysis/app/src/testSyspart.cpp:167; analysis/app/src/testSyspart.cpp:500-503).
- Expected: Mode 19 reaches run6 without initializing syscall names (analysis/app/src/testSyspart.cpp:500-503; analysis/app/src/syspart.cpp:1971-2014).
- Actual: The source initializes syscall names before mode 19 dispatch (analysis/app/src/testSyspart.cpp:167,186,500-503). Runtime cost was not measured.
- Evidence: analysis/app/src/testSyspart.cpp:77-86 — -a selects the analysis number; analysis/app/src/testSyspart.cpp:138-152 — required inputs are checked; analysis/app/src/testSyspart.cpp:167 — populateSyscallMap runs before the switch; analysis/app/src/syspart.cpp:154-158 — initialization reads headers or constructs the fallback map; analysis/app/src/syspart.cpp:131-150 — each available header is read line by line; analysis/app/src/testSyspart.cpp:500-503 — mode 19 calls run6; analysis/app/src/syspart.cpp:1973-2014 — run6 constructs the call graph and reports fork/thread targets.
- Assessment: No mode guard precedes the syscall-map initialization: the driver calls it before dispatching -a 19 (analysis/app/src/testSyspart.cpp:167,186,500-503). The map is private to Syspart (analysis/app/src/syspart.h:42), while run6 reports call targets and thread-start functions without reading it (analysis/app/src/syspart.cpp:1971-2014). Tiny test case: analyze a program whose main calls fork using -a 19; expected output includes a line containing "fork is invoked in main" and "Thread start functions :" (analysis/app/src/syspart.cpp:1997-1998,2010-2014). No binary was run, so elapsed cost and output are unconfirmed.

### An unresolved mode 19 root is accepted

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:1974`
- Invariant: The required -s value must resolve to a Function before it becomes the graph root (analysis/app/src/testSyspart.cpp:143-146; analysis/app/src/syspart.cpp:1974).
- Mechanism: Name and address lookups can return null, and the driver passes that value to setStartFunc without checking it. run6 then passes the stored value to setRoot, which creates a node and requests a working set for it (analysis/app/src/syspart.cpp:47-61; analysis/app/src/syspart.cpp:66-80; analysis/app/src/testSyspart.cpp:173-182; analysis/app/src/syspart.cpp:1974; analysis/app/src/ipcallgraph.cpp:169-177).
- Reproducer: Source-bounded case: invoke -a 19 with -s naming no parsed function. The lookup returns null and dispatch still calls run6 (analysis/app/src/syspart.cpp:66-80; analysis/app/src/testSyspart.cpp:179-182; analysis/app/src/testSyspart.cpp:500-503).
- Expected: Reject an unresolved -s function before graph construction (analysis/app/src/testSyspart.cpp:143-146; analysis/app/src/ipcallgraph.cpp:169-177).
- Actual: The source passes null through setRoot into getWorkingSet; the runtime outcome is unobserved (analysis/app/src/syspart.cpp:66-80; analysis/app/src/testSyspart.cpp:179-182; analysis/app/src/syspart.cpp:1971-1974; analysis/app/src/ipcallgraph.cpp:169-177).
- Evidence: analysis/app/src/syspart.cpp:66-80 — an unmatched name returns null; analysis/app/src/testSyspart.cpp:179-182 — that value is stored without a guard; analysis/app/src/testSyspart.cpp:500-503 — mode 19 calls run6; analysis/app/src/syspart.cpp:1971-1974 — run6 passes the stored root to setRoot; analysis/app/src/ipcallgraph.cpp:169-177 — setRoot creates a node and calls getWorkingSet for it; analysis/tools/egalito/src/analysis/dataflow.cpp:29-33 — getWorkingSet begins analysis for a new value; analysis/tools/egalito/src/analysis/controlflow.cpp:30-32 — that analysis constructs a control flow graph from the value. The later null guard in findDirectEdges cannot protect setRoot (analysis/app/src/ipcallgraph.cpp:872-880).
- Assessment: The driver checks that -s was supplied, but does not check whether its name lookup succeeded (analysis/app/src/testSyspart.cpp:143-146; analysis/app/src/testSyspart.cpp:179-182). A tiny proposed test is a binary containing only main, invoked with -p ./tiny -s __missing__ -a 19. Expected output after a fix: a clear “root function not found” diagnostic and a nonzero exit. No runtime output was captured.

### Alternative thread start functions at one callsite are omitted

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:1082`
- Invariant: Thread-start discovery should retain every resolvable RDX definition reaching a pthread_create callsite (analysis/app/src/syspart.cpp:1153-1156; analysis/app/src/syspart.cpp:1180-1191).
- Mechanism: Use-def tracking can attach multiple register definitions to one use, but findRegDef returns as soon as it resolves the first matching definition. getThreadStartFunction then inserts at most one function for that callsite (analysis/tools/egalito/src/analysis/usedef.cpp:639-644; analysis/app/src/syspart.cpp:1082-1126; analysis/app/src/syspart.cpp:1183-1191).
- Reproducer: Source-bounded case: two branches put the addresses of worker_a and worker_b in RDX before joining at one pthread_create call. If both definitions reach the callsite, findRegDef returns from the first resolved definition without visiting the second (analysis/tools/egalito/src/analysis/usedef.cpp:639-644; analysis/app/src/syspart.cpp:1082-1107; analysis/app/src/syspart.cpp:1153-1156).
- Expected: Both worker_a and worker_b are listed under "Thread start functions :" (analysis/app/src/syspart.cpp:2010-2014).
- Actual: The source path can list only the first resolved worker for that direct callsite; this is source-supported, with no observed runtime output (analysis/app/src/syspart.cpp:1064-1126, analysis/app/src/syspart.cpp:1180-1200).
- Evidence: analysis/tools/egalito/src/instr/register.cpp:8 — RDX maps to R2; analysis/tools/egalito/src/analysis/usedef.cpp:1876-1883 — call analysis records uses of registers 0 through 2; analysis/tools/egalito/src/analysis/usedef.cpp:282-295 — predecessor register definitions are merged; analysis/tools/egalito/src/analysis/usedef.cpp:640-644 — each reaching definition is attached to the call state; analysis/app/src/syspart.cpp:1150-1156 — the callsite passes its RDX references to findRegDef; analysis/app/src/syspart.cpp:1064-1068, analysis/app/src/syspart.cpp:1088-1126 — findRegDef returns on the first recognized definition; analysis/app/src/syspart.cpp:1180-1200 — the direct pthread_create caller inserts at most that one returned function; analysis/app/src/syspart.cpp:2010-2014 — mode 19 prints the resulting set.
- Assessment: Tiny test case: two branches load worker_a and worker_b into RDX, join, then make one direct pthread_create call. If both definitions reach the call, the use-def merge retains both (analysis/tools/egalito/src/analysis/usedef.cpp:282-295, analysis/tools/egalito/src/analysis/usedef.cpp:640-644). Expected mode -a 19 output includes both worker names under "Thread start functions :" (analysis/app/src/testSyspart.cpp:500-503, analysis/app/src/syspart.cpp:2010-2014). No binary was run.

### Mode 19 copies init and fini lists it never reads

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspart.cpp:1982`
- Invariant: Printing mode 19 call targets and thread starts does not require copies of the graph's init and fini function lists (analysis/app/src/syspart.cpp:1984-2015).
- Mechanism: After graph generation, run6 obtains both lists by value and assigns them to Syspart fields, then proceeds to reporting and thread-start discovery without reading either field (analysis/app/src/ipcallgraph.cpp:181-187; analysis/app/src/syspart.cpp:1982-2015).
- Reproducer: Bounded cost: with I init entries and F fini entries, one mode 19 invocation copies and retains O(I + F) function pointers that its remaining path does not use (analysis/app/src/ipcallgraph.cpp:181-187; analysis/app/src/syspart.cpp:1982-2015).
- Expected: Mode 19 produces its call-target and thread-start report without copying the init and fini vectors (analysis/app/src/syspart.cpp:1984-2015).
- Actual: The source copies both vectors and retains them in Syspart, adding O(I + F) pointer-copy and storage cost for I init and F fini entries (analysis/app/src/ipcallgraph.cpp:181-187; analysis/app/src/syspart.cpp:1982-1983; analysis/app/src/syspart.h:40-41). Time and memory were not measured.
- Evidence: analysis/app/src/testSyspart.cpp:500-503 — mode 19 calls run6; analysis/app/src/syspart.cpp:1973-1983 — run6 generates the graph, then assigns both lists without a guard; analysis/app/src/ipcallgraph.cpp:181-187 — both getters return vectors by value; analysis/app/src/syspart.cpp:1984-2015 — the remaining path reports call targets and thread starts without reading either field; analysis/app/src/syspart.cpp:1165-1235 — thread-start discovery uses graph nodes and function lookup; analysis/app/src/syspart.h:40-41 — the copies are stored in Syspart.
- Assessment: Tiny test case: analyze a program whose main returns 0 with -a 19. The mode-specific report should contain `Thread start functions :` and no call-target lines; removing the two assignments should leave that report unchanged (analysis/app/src/syspart.cpp:1984-2015). This is a source-supported cost finding; no binary was run.

<!-- harness:logic:mode-19:end -->

<!-- harness:logic:mode-20:start -->
## Harness logic audit — mode 20

Dispatcher and modules: analysis/app/src/testSyspart.cpp, analysis/app/src/syspart.cpp, analysis/app/src/syspart.h

### Mode 20 rejects a listing request without a start function

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/testSyspart.cpp:143`
- Invariant: Mode 20 lists all parsed functions and does not read a start function (analysis/app/src/testSyspart.cpp:124,505-508; analysis/app/src/syspart.cpp:3129-3138).
- Mechanism: The shared validation rejects every invocation without -s before parsing or mode dispatch (analysis/app/src/testSyspart.cpp:143-146,156,505).
- Reproducer: Source-bounded invocation: -p <valid-binary> -a 20, with no -s (analysis/app/src/testSyspart.cpp:137-151,505-508). No runtime output was observed.
- Expected: Function listing rows for the parsed modules (analysis/app/src/syspart.cpp:3131-3136).
- Actual: Source-predicted: `Start(root) function name/address should be provided`, followed by return -1 (analysis/app/src/testSyspart.cpp:143-146).
- Evidence: analysis/app/src/testSyspart.cpp:21 — funcFlag starts false; analysis/app/src/testSyspart.cpp:41-62 — only `-s` sets it true; analysis/app/src/testSyspart.cpp:77-86 — `-a 20` selects mode 20 without setting funcFlag; analysis/app/src/testSyspart.cpp:137-146 — validation prints the missing-start message and returns before parsing; analysis/app/src/testSyspart.cpp:156-186,505-508 — program parsing and mode 20 dispatch occur later; analysis/app/src/syspart.cpp:3129-3138 — the listing function reads the program's modules and functions without a start function.
- Assessment: A tiny test is `-p <valid-binary> -a 20` with no `-s`. The expected output is a listing row in the form `<function-name> <hex-address> <module-name>` for each parsed function (analysis/app/src/testSyspart.cpp:124; analysis/app/src/syspart.cpp:3129-3138). The shared guard prevents that listing (analysis/app/src/testSyspart.cpp:143-146). No binary was run.

### The -s all shortcut performs an unused function scan

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/testSyspart.cpp:42`
- Invariant: The all-functions listing needs no resolved start function (analysis/app/src/testSyspart.cpp:505-508; analysis/app/src/syspart.cpp:3129-3138).
- Mechanism: The char-pointer comparison at line 42 compares addresses rather than text. For an ordinary -s all argument, the code therefore stores "all" as a function name and scans the parsed modules before dispatch (analysis/app/src/testSyspart.cpp:34,41-59,179-182; analysis/app/src/syspart.cpp:66-80).
- Reproducer: Source-bounded case: -p <valid-binary> -s all -a 20, with F parsed functions and none named all. The lookup examines all F functions; mode 20 then performs its own listing traversal (analysis/app/src/syspart.cpp:66-80,3129-3138). No runtime cost was measured.
- Expected: The `-s all` shortcut skips start-function resolution before mode 20 prints functions (analysis/app/src/testSyspart.cpp:42-44,179-182,505-508).
- Actual: The source predicts an avoidable O(F) lookup before the O(F) listing for F parsed functions when none is named `all` (analysis/app/src/testSyspart.cpp:42,57-59,179-182,505-508; analysis/app/src/syspart.cpp:66-80,3129-3138).
- Evidence: analysis/app/src/testSyspart.cpp:42-44 — `arg` is compared with the string literal by pointer address, so an ordinary `-s all` argument does not set `allFlag`. analysis/app/src/testSyspart.cpp:57-62 — the argument is stored as `func_name` and satisfies the start-function guard. analysis/app/src/testSyspart.cpp:137-167,179-186 — after parsing, the program calls `findFunctionByName` before dispatch. analysis/app/src/syspart.cpp:66-80 — with no function named `all`, lookup examines every parsed function. analysis/app/src/testSyspart.cpp:505-508; analysis/app/src/syspart.cpp:3129-3138 — mode 20 then traverses the functions again to print them.
- Assessment: For a tiny valid binary with `int helper(void){return 0;} int main(void){return helper();}` and no function named `all`, run `-p <binary> -s all -a 20`. Expected output is one `<name> <hex-address> <module>` line per parsed function, including `main` and `helper`; the listing needs no start function (analysis/app/src/testSyspart.cpp:505-508; analysis/app/src/syspart.cpp:3129-3138). The source supports an avoidable full function lookup before that listing. No runtime output or cost was captured.

### Mode 20 runs PLT resolution passes that its printer does not use

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/testSyspart.cpp:162`
- Invariant: Each output record reads only a function's name and address and its module's name (analysis/app/src/syspart.cpp:3129-3138).
- Mechanism: Before dispatch, the driver runs both PLT passes over the Program. They resolve trampoline targets and inspect or replace instruction links, while mode 20 reads function metadata (analysis/app/src/testSyspart.cpp:162-166,505-508; analysis/tools/egalito/src/pass/resolveplt.cpp:12-29; analysis/tools/egalito/src/pass/collapseplt.cpp:64-73,95-99; analysis/app/src/syspart.cpp:3131-3135).
- Reproducer: Bounded source case: a parsed program with P PLT trampolines and I instructions incurs PLT resolution and an instruction-link traversal before printing F function records (analysis/tools/egalito/src/pass/resolveplt.cpp:18-29; analysis/tools/egalito/src/pass/collapseplt.cpp:64-73; analysis/app/src/syspart.cpp:3131-3135). No runtime cost was measured.
- Expected: Mode 20 can print the parsed function records without the two PLT passes (analysis/app/src/testSyspart.cpp:158-161; analysis/app/src/syspart.cpp:3129-3138).
- Actual: The source invokes both passes before mode 20 prints those records (analysis/app/src/testSyspart.cpp:162-166,505-508).
- Evidence: analysis/app/src/testSyspart.cpp:156-166 — parse the program, then invoke ResolvePLTPass and CollapsePLTPass before dispatch; analysis/tools/egalito/src/pass/chunkpass.h:14-32 — pass recursion reaches modules, functions, and instructions; analysis/tools/egalito/src/pass/resolveplt.cpp:22-29,89-98 — resolve unresolved trampoline targets; analysis/tools/egalito/src/pass/collapseplt.cpp:39-54,64-73,95-99 — build IFUNC mappings, traverse modules and data, and inspect or replace instruction links; analysis/app/src/testSyspart.cpp:505-508 — mode 20 calls printFunctions; analysis/app/src/syspart.cpp:3129-3138 — printFunctions reads function and module metadata.
- Assessment: The missing-argument guards can stop execution before parsing, but a valid mode 20 invocation reaches both passes before the mode switch (analysis/app/src/testSyspart.cpp:137-166,186,505-508). The printer reads Function names and addresses from the module's FunctionList, plus module names; PLT trampolines have a separate list (analysis/app/src/syspart.cpp:3129-3138; analysis/tools/egalito/src/chunk/chunkiter.h:57-60). Tiny test case: use a fixture whose parsed program contains module `module-mini`, function `main` at 0x1000, one PLT trampoline, and an instruction with a PLT link; invoke mode 20 with `-s main`. The expected listing record is `main 1000 module-mini` (analysis/app/src/testSyspart.cpp:41-63,77-87,505-508; analysis/app/src/syspart.cpp:3131-3135). This is a source-supported cost finding; no runtime output or timing was captured.

### The function listing flushes stdout for every record

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspart.cpp:3135`
- Invariant: Printing F function records requires F lines, without a per-record flush (analysis/app/src/syspart.cpp:3131-3135).
- Mechanism: The inner loop ends every record with std::endl, which flushes stdout each time (analysis/app/src/syspart.cpp:3133-3135).
- Reproducer: Bounded complexity: a Program containing F functions executes F output flushes through the mode 20 printer (analysis/app/src/testSyspart.cpp:505-508; analysis/app/src/syspart.cpp:3131-3135). No runtime cost was measured.
- Expected: F newline-delimited function records without F forced flushes (analysis/app/src/syspart.cpp:3131-3135).
- Actual: For F visited functions, the source requests one cout flush per record through endl (analysis/app/src/syspart.cpp:3133-3135).
- Evidence: analysis/app/src/testSyspart.cpp:77-87 — -a selects the numeric mode; analysis/app/src/testSyspart.cpp:505-508 — case 20 calls printFunctions; analysis/app/src/syspart.cpp:3129-3138 — the printer visits every module and function; analysis/app/src/syspart.cpp:3135 — each record ends with endl, which requests a stream flush.
- Assessment: The required arguments and parsing steps precede the mode 20 switch (analysis/app/src/testSyspart.cpp:137-186), but case 20 calls printFunctions without a record-count guard (analysis/app/src/testSyspart.cpp:505-508). Tiny test case: a Program with one module named m containing, in iteration order, foo at address 0x10 and bar at 0x20. The expected function-listing output is "foo 10 m\nbar 20 m\n" (analysis/app/src/syspart.cpp:3131-3135). No binary was run or runtime cost measured.
- Command: `awk 'NR>=3125 && NR<=3140 {printf "%d:%s\n",NR,$0}' analysis/app/src/syspart.cpp`

### Mode 20 resolves a start function it never uses

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/testSyspart.cpp:181`
- Invariant: The listing reads each function's name and address and its module's name; it does not read the resolved start function (analysis/app/src/testSyspart.cpp:505-508; analysis/app/src/syspart.cpp:3129-3138).
- Mechanism: For a named -s argument, the driver calls findFunctionByName before mode 20 dispatch. That lookup scans parsed modules and functions and stores a result the printer never reads (analysis/app/src/testSyspart.cpp:179-182,505-508; analysis/app/src/syspart.cpp:66-80,3129-3138).
- Reproducer: Source-bounded case: -p <valid-binary> -s <valid-function-name> -a 20. With F parsed functions, lookup can examine O(F) functions before the printer's own F-function traversal (analysis/app/src/testSyspart.cpp:179-182,505-508; analysis/app/src/syspart.cpp:69-79,3131-3135). No runtime cost was measured.
- Expected: Mode 20 prints the same function records without resolving -s (analysis/app/src/testSyspart.cpp:505-508; analysis/app/src/syspart.cpp:3129-3138).
- Actual: The source performs the unused named-function lookup before printing (analysis/app/src/testSyspart.cpp:179-182,505-508; analysis/app/src/syspart.cpp:66-80,3129-3138).
- Evidence: analysis/app/src/testSyspart.cpp:41-62 — -s foo selects the named-function path; analysis/app/src/testSyspart.cpp:143-151 — required arguments are checked; analysis/app/src/testSyspart.cpp:156-182 — parsing precedes the lookup and setter; analysis/app/src/syspart.cpp:66-80 — lookup scans modules and functions; analysis/app/src/syspart.cpp:23-26 — setter stores the result; analysis/app/src/testSyspart.cpp:505-508 — mode 20 calls printFunctions; analysis/app/src/syspart.cpp:3129-3138 — printer uses only function name, address, and module name.
- Assessment: The required -s argument is parsed as a function name for this case (analysis/app/src/testSyspart.cpp:41-62,143-146). Before mode dispatch, the driver searches parsed functions and stores the result (analysis/app/src/testSyspart.cpp:156-182). The setter only stores the pointer, and mode 20 prints records without reading it (analysis/app/src/syspart.cpp:23-26,3129-3138; analysis/app/src/testSyspart.cpp:505-508). The lookup can examine O(F) functions in addition to the printer's F-function traversal (analysis/app/src/syspart.cpp:66-80,3129-3138). Tiny test: use a binary containing function foo and invoke -p <binary> -s foo -a 20. Expect a record for foo with its hexadecimal address and module name, with no separate start-function record (analysis/app/src/syspart.cpp:3131-3135). This is source-supported; no runtime output or cost was measured.

<!-- harness:logic:mode-20:end -->

<!-- harness:logic:mode-21:start -->
## Harness logic audit — mode 21

Dispatcher and modules: README.md, analysis/app/README.md, analysis/app/src/testSyspart.cpp, analysis/app/src/syspart.cpp, analysis/app/src/syspart.h, analysis/app/src/ipcallgraph.cpp, analysis/app/src/syspartUtility.cpp, analysis/app/src/syspartUtility.h

### Mode 21 passes an uninitialized register to argument tracing

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:2676`
- Invariant: Tracing dlopen's first argument requires register 7 (analysis/app/src/dlanalysis/README.md:53).
- Mechanism: Mode 21 passes "dlopen@", but the register assignment tests equality with "dlopen". Neither assignment runs before reg is passed to the tracer (analysis/app/src/testSyspart.cpp:512; analysis/app/src/syspart.cpp:2676-2682).
- Reproducer: Source-bounded case: analyze a small program that calls a matching dlopen symbol with -a 21. The mismatch occurs for every such invocation; no workload was run (analysis/app/src/testSyspart.cpp:510-513; analysis/app/src/syspart.cpp:2655-2660,2676-2682).
- Expected: Trace register 7, the documented first dlopen argument, and report its library-name value when resolved (analysis/app/src/dlanalysis/README.md:52-54; analysis/app/src/syspartUtility.cpp:259-288).
- Actual: For a matching symbol, the tracer receives an indeterminate `reg` value; its resulting output cannot be established from source alone (analysis/app/src/syspart.cpp:2655-2660,2676-2682).
- Evidence: analysis/app/src/testSyspart.cpp:510-513 — mode 21 passes `dlopen@`; analysis/app/src/syspart.cpp:2651-2667 — a matching libc symbol passes the only early return; analysis/app/src/syspart.cpp:2676-2682 — `reg` is assigned only for `dlopen` or `dlsym`, then passed to the tracer; analysis/app/src/syspartUtility.cpp:93-115 — the tracer accepts and uses that register value.
- Assessment: A tiny test program calling dlopen("libm.so.6", RTLD_LAZY), analyzed with -a 21, should produce an argument result containing `SYM libm.so.6` when the literal is resolved (analysis/app/src/syspartUtility.cpp:277-288). No binary was run. The source shows that mode 21 leaves the register value uninitialized before tracing and still pays for callgraph generation (analysis/app/src/syspart.cpp:2668-2682).

### Searching only libc misses dlopen implementations in libdl

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:2651`
- Invariant: The dlopen target must be found in whichever parsed module defines it; the documented libc-2.27 environment places it in libdl.so (README.md:198-201).
- Mechanism: The driver parses shared libraries, but printDlArgs searches only program->getLibc(), which selects the libc module, and returns on a miss without searching other modules (analysis/app/src/testSyspart.cpp:158; analysis/tools/egalito/src/chunk/program.cpp:58-60; analysis/app/src/syspart.cpp:2651-2666).
- Reproducer: Source-bounded case: use a binary linked against separate libdl.so with dlopen there and no dlopen-prefixed function in libc; request -a 21 (README.md:198-201; analysis/app/src/testSyspart.cpp:510-513). No binary was run.
- Expected: Find the dlopen definition in the parsed libdl module, print "dlopen@@GLIBC_2.2.5 found ", and proceed to argument analysis (README.md:198; analysis/app/src/syspart.cpp:2655-2660,2668-2682).
- Actual: For the stated fixture, the source path prints "Function dlopen@ not found" and returns before argument analysis (analysis/app/src/syspart.cpp:2651-2666). This is a source-supported prediction, not observed runtime output.
- Evidence: analysis/app/src/testSyspart.cpp:143-151 — the driver requires a start function and analysis option; analysis/app/src/testSyspart.cpp:156-166 — it parses shared libraries and runs PLT passes; analysis/tools/egalito/src/chunk/library.cpp:42-50,104-111 — libdl is assigned a normal role rather than the libc role; analysis/tools/egalito/src/chunk/program.cpp:58-60 — getLibc selects only the libc-role module; analysis/app/src/testSyspart.cpp:510-513 — mode 21 passes "dlopen@"; analysis/app/src/syspart.cpp:2651-2666 — printDlArgs searches only that module and returns on a miss; analysis/app/src/syspart.cpp:2668-2682 — argument analysis is reached only after a match.
- Assessment: A tiny source-bounded test is a program whose main calls dlopen("libprobe.so", RTLD_LAZY), linked against separate libdl.so, with no dlopen-prefixed function in libc. Request -a 21 with main as the start function. The expected lookup output is "dlopen@@GLIBC_2.2.5 found ", followed by argument analysis; the documented environment places that symbol in libdl.so (README.md:198; analysis/app/src/syspart.cpp:2655-2660,2668-2682). There is a separate limit on that expectation: option 21 passes "dlopen@", while register selection checks for exactly "dlopen", so the first-argument output cannot be predicted from this path (analysis/app/src/testSyspart.cpp:510-513; analysis/app/src/syspart.cpp:2676-2682).

### The dlopen@ name filter misses an unversioned dlopen symbol

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:2655`
- Invariant: Mode 21 should trace the selected dlopen function's callers (README.md:169; analysis/app/src/syspart.cpp:2682).
- Mechanism: The dispatcher supplies "dlopen@", and the search accepts only names starting with that string. A function named exactly "dlopen" fails the test, so tracing is skipped (analysis/app/src/testSyspart.cpp:510-512; analysis/app/src/syspart.cpp:2651-2666).
- Reproducer: Source-bounded case: libc contains a function named "dlopen" and no dlopen@-prefixed function; invoke -a 21. No workload was run (analysis/app/src/testSyspart.cpp:510-512; analysis/app/src/syspart.cpp:2651-2666).
- Expected: Select the unversioned dlopen function and trace arguments passed by its callers (README.md:169; analysis/app/src/syspart.cpp:2682).
- Actual: For the stated source-bounded case, the code prints "Function dlopen@ not found" and skips tracing (analysis/app/src/syspart.cpp:2663-2666).
- Evidence: analysis/app/src/testSyspart.cpp:77-87 — -a selects the mode; analysis/app/src/testSyspart.cpp:510-512 — mode 21 passes "dlopen@"; analysis/app/src/syspart.cpp:2651-2655 — the libc search requires that prefix, which exact "dlopen" lacks; analysis/app/src/syspart.cpp:2663-2666 — no match prints the failure and returns before tracing at analysis/app/src/syspart.cpp:2682.
- Assessment: Tiny test: provide a parsed libc whose only dlopen function has getName() == "dlopen", then select -a 21. The expected output should begin "dlopen found" and proceed to argument tracing, as mode 21 promises (README.md:169; analysis/app/src/syspart.cpp:2682). The source instead predicts "Function dlopen@ not found" (analysis/app/src/testSyspart.cpp:512; analysis/app/src/syspart.cpp:2655-2666). No workload was run.

### Only the first matching dlopen symbol is traced

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:2660`
- Invariant: Calls to each matching dlopen implementation should contribute arguments to the mode 21 report (README.md:169; analysis/app/src/syspartUtility.cpp:188-191).
- Mechanism: The libc scan stops at its first dlopen@-prefixed function and passes only that Function to argument tracing. The tracer reads the selected function's graph node and parents; it does not query other matching functions (analysis/app/src/syspart.cpp:2651-2660,2682; analysis/app/src/syspartUtility.cpp:179-191).
- Reproducer: Source-bounded case: libc has two distinct dlopen@-prefixed functions, and a reachable caller invokes only the second. Place the first earlier in function iteration. No workload was run (analysis/app/src/syspart.cpp:2652-2660; analysis/app/src/ipcallgraph.cpp:891-895).
- Expected: The dlopen@@V2 caller and its "libsecond.so" argument appear in the mode 21 report (README.md:169; analysis/app/src/syspartUtility.cpp:228-241,259-265).
- Actual: The source requests tracing only for dlopen@@V1; the dlopen@@V2 callsite is outside that request (analysis/app/src/syspart.cpp:2659-2660,2682; analysis/app/src/syspartUtility.cpp:179-191). Runtime output is unobserved.
- Evidence: analysis/app/src/testSyspart.cpp:510-513 — mode 21 passes "dlopen@"; analysis/app/src/syspart.cpp:2651-2660 — the libc scan retains the first prefix match and breaks; analysis/app/src/syspart.cpp:2668-2682 — the graph is generated, then only that Function is passed to the tracer; analysis/app/src/ipcallgraph.cpp:224-247,891-903 — call edges attach parents to their target Function; analysis/app/src/ipcallgraph.h:355-371 — node lookup uses Function identity or the same name and module; analysis/app/src/syspartUtility.cpp:179-191 — tracing reads only the selected node's parents.
- Assessment: Tiny test case: put distinct libc functions dlopen@@V1 and dlopen@@V2 in that iteration order, with a reachable caller invoking only dlopen@@V2 with "libsecond.so". Mode 21 should report that caller and argument (README.md:169; analysis/app/src/syspartUtility.cpp:223-241,259-265). The source selects dlopen@@V1 and stops, so it never requests a trace of dlopen@@V2 (analysis/app/src/testSyspart.cpp:510-513; analysis/app/src/syspart.cpp:2652-2660,2682). A separate guard mismatch leaves reg uninitialized for the actual "dlopen@" argument, so exact runtime output cannot be predicted (analysis/app/src/testSyspart.cpp:512; analysis/app/src/syspart.cpp:2676-2682). No binary was run.

### Duplicate suppression takes quadratic time in the number of traced values

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspartUtility.cpp:261`
- Invariant: Printing R distinct values at one callsite requires only R value records (analysis/app/src/syspartUtility.cpp:259-264).
- Mechanism: For every value in the result set, the printer linearly searches the growing alreadyPrinted vector before appending the value (analysis/app/src/syspartUtility.cpp:189,259-262).
- Reproducer: Bounded complexity case: one dlopen callsite yields R distinct UDResult values. The duplicate checks inspect 0 through R−1 prior entries, totaling Θ(R²) comparisons; no timing was measured (analysis/app/src/syspart.cpp:2682; analysis/app/src/syspartUtility.cpp:235-262).
- Expected: For R distinct values, R value records with duplicate tracking proportional to R (analysis/app/src/syspartUtility.cpp:259-265).
- Actual: Conditional on R distinct values reaching this loop, duplicate checks perform 0 + 1 + ... + (R−1) = R(R−1)/2 UDResult comparisons. This is a source-supported cost, not a runtime measurement (analysis/app/src/syspartUtility.cpp:259-262; analysis/app/src/syspartUtility.h:23-28).
- Evidence: analysis/app/src/testSyspart.cpp:510-513 — mode 21 calls printDlArgs("dlopen@"); analysis/app/src/syspart.cpp:2652-2682 — the matching function is passed to a SyspartUtility with analysisType 0, but the register comparison does not match "dlopen@"; analysis/app/src/syspartUtility.cpp:104-115 — a cache hit can bypass the helper; analysis/app/src/syspartUtility.cpp:188-189,223-241 — the helper creates alreadyPrinted and collects definitions at matching callsites; analysis/app/src/syspartUtility.cpp:259-262 — each collected value is linearly searched before append; analysis/app/src/syspartUtility.h:23-28 — comparisons use UDResult equality.
- Assessment: Tiny proposed test: one callsite passes either "a.so" or "b.so" to dlopen. If analysis yields two distinct UDResult values, the expected printout is two TYPE records followed by one END marker (analysis/app/src/syspartUtility.cpp:259-291). No binary was run. Mode 21 also passes "dlopen@", while register 7 is selected only for "dlopen"; this leaves reg uninitialized and prevents a reliable prediction of actual mode 21 output (analysis/app/src/testSyspart.cpp:510-513; analysis/app/src/syspart.cpp:2676-2682).

<!-- harness:logic:mode-21:end -->

<!-- harness:logic:mode-22:start -->
## Harness logic audit — mode 22

Dispatcher and modules: analysis/app/src/testSyspart.cpp, analysis/app/src/syspart.cpp, analysis/app/src/ipcallgraph.cpp, analysis/app/src/syspartUtility.cpp, analysis/app/src/syspartUtility.h

### Mode 22 ignores the supplied TypeArmor filter

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspart.cpp:2670`
- Invariant: When -t supplies TypeArmor data, indirect target generation should use it to prune candidates (analysis/app/src/testSyspart.cpp:64; analysis/app/src/ipcallgraph.cpp:711).
- Mechanism: Mode 22 generates indirect edges without enabling TypeArmor on the call graph. The graph's flag defaults to false, so each unresolved callsite receives the full address-taken target set and a parent link for every target (analysis/app/src/testSyspart.cpp:515; analysis/app/src/syspart.cpp:2668; analysis/app/src/ipcallgraph.h:290; analysis/app/src/ipcallgraph.cpp:709).
- Reproducer: Source-bounded case: supply -a 22 -t with complete TypeArmor metadata for one unresolved indirect callsite and M address-taken functions, of which K have compatible argument counts. The unfiltered branch inserts M targets and M parent links; the filtering branch can insert K (analysis/app/src/ipcallgraph.cpp:711; analysis/app/src/ipcallgraph.cpp:809; analysis/app/src/ipcallgraph.cpp:844).
- Expected: With complete metadata for that callsite, TypeArmor filtering retains only compatible targets, {A} in the proposed test (analysis/app/src/ipcallgraph.cpp:809; analysis/app/src/ipcallgraph.cpp:853; analysis/app/src/ipcallgraph.cpp:864).
- Actual: The mode 22 source path leaves TypeArmor disabled, so the unresolved callsite receives {A, B} and both targets receive parent entries, adding avoidable graph work and storage (analysis/app/src/syspart.cpp:2668; analysis/app/src/ipcallgraph.h:290; analysis/app/src/ipcallgraph.cpp:711).
- Evidence: analysis/app/src/testSyspart.cpp:64 — -t records the TypeArmor path; analysis/app/src/testSyspart.cpp:184 — main passes that path to Syspart; analysis/app/src/testSyspart.cpp:515 — mode 22 calls printDlArgs; analysis/app/src/syspart.cpp:2660 — a missing dlsym symbol returns before graph generation; analysis/app/src/syspart.cpp:2668 — the remaining path sets the graph program and root, enables indirect analysis, then calls generate without setting TypeArmor; analysis/app/src/ipcallgraph.h:290 — the graph's TypeArmor flag defaults to false; analysis/app/src/ipcallgraph.cpp:1815 — generate parses TypeArmor only when that flag is true; analysis/app/src/ipcallgraph.cpp:1832 — it builds the address-taken target set and generates indirect edges; analysis/app/src/ipcallgraph.cpp:709 — an unresolved callsite passes the resolution guard; analysis/app/src/ipcallgraph.cpp:711 — the false-flag branch inserts the full set and a parent entry for each target.
- Assessment: For a tiny source-bounded test, use a reachable unresolved indirect callsite with TypeArmor metadata specifying one argument and two address-taken functions: A accepts one argument, B accepts two. Inspect the callsite's graph targets after mode 22 with -t: the expected output is {A}; the source path produces {A, B}. The pruning rule excludes B only when TypeArmor is enabled (analysis/app/src/ipcallgraph.cpp:809; analysis/app/src/ipcallgraph.cpp:848; analysis/app/src/ipcallgraph.cpp:864). No binary was run or runtime cost measured.

<!-- harness:logic:mode-22:end -->

<!-- harness:logic:mode-23:start -->
## Harness logic audit — mode 23

Dispatcher and modules: analysis/app/src/testSyspart.cpp, analysis/app/src/syspart.cpp, analysis/app/src/ipcallgraph.cpp, analysis/app/src/ipcallgraph.h, analysis/app/src/nss.cpp, analysis/app/src/syspartUtility.cpp

### A relative root-file path is treated as a function name

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/testSyspart.cpp:52`
- Invariant: Mode 23 needs the -s value stored as its root-file path before run15 opens it [analysis/app/src/testSyspart.cpp:520] [analysis/app/src/syspart.cpp:1636].
- Mechanism: Only a value beginning with '/' sets isFile and start_func_file; a relative path takes the function-name branch. The driver therefore leaves startFuncFile empty, and run15 attempts to open that empty path [analysis/app/src/testSyspart.cpp:52] [analysis/app/src/testSyspart.cpp:57] [analysis/app/src/testSyspart.cpp:169] [analysis/app/src/syspart.cpp:1636].
- Reproducer: Source-bounded case: supply -s roots.txt -a 23, where roots.txt is a readable file containing main [analysis/app/src/testSyspart.cpp:52] [analysis/app/src/testSyspart.cpp:520] [analysis/app/src/syspart.cpp:1645].
- Expected: Read `roots.txt` and generate a call graph rooted at main [analysis/app/src/syspart.cpp:1645] [analysis/app/src/syspart.cpp:1650] [analysis/app/src/syspart.cpp:1663].
- Actual: For this source path, startFuncFile remains empty, so run15 attempts to open an empty filename and returns if the open fails [analysis/app/src/testSyspart.cpp:57] [analysis/app/src/testSyspart.cpp:169] [analysis/app/src/syspart.cpp:1636] [analysis/app/src/syspart.cpp:1638]. This is a source-supported prediction, not observed output.
- Evidence: analysis/app/src/testSyspart.cpp:52 — only a value starting with `/` enters the file branch; analysis/app/src/testSyspart.cpp:57 — `roots.txt` enters the function-name branch; analysis/app/src/testSyspart.cpp:169 — only the file branch calls setStartFuncFile; analysis/app/src/syspart.h:39 — startFuncFile is a string member; analysis/app/src/testSyspart.cpp:520 — mode 23 calls run15; analysis/app/src/syspart.cpp:1636 — run15 opens startFuncFile; analysis/app/src/syspart.cpp:1638 — an unsuccessful open returns before graph generation.
- Assessment: Tiny test: use a valid binary with main, put `main` in a readable `roots.txt`, and pass `-s roots.txt -a 23` with the binary via `-p`. The expected output is a call graph rooted at main: mode 23 calls run15, which reads root names and adds matching functions as roots [analysis/app/src/testSyspart.cpp:520] [analysis/app/src/syspart.cpp:1645] [analysis/app/src/syspart.cpp:1650]. The source supports the failure, but no runtime output was captured.

### An empty or wholly unresolved root file can produce unrelated graph edges

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:1655`
- Invariant: A graph requested from a set of start functions should have at least one resolved start function before generation and printing [analysis/app/src/testSyspart.cpp:520] [analysis/app/src/syspart.cpp:1650] [analysis/app/src/syspart.cpp:1671].
- Mechanism: run15 continues when the root list is empty or every lookup fails. Graph generation then adds init and fini functions as independent roots, traverses them, and prints their edges [analysis/app/src/syspart.cpp:1645] [analysis/app/src/syspart.cpp:1653] [analysis/app/src/syspart.cpp:1663] [analysis/app/src/ipcallgraph.cpp:453] [analysis/app/src/ipcallgraph.cpp:475] [analysis/app/src/ipcallgraph.cpp:1746] [analysis/app/src/ipcallgraph.cpp:755].
- Reproducer: Source-bounded fixture: an empty absolute-path root file and a parsed module whose _init directly calls helper. findData queues _init, and direct traversal records its call [analysis/app/src/syspart.cpp:1645] [analysis/app/src/ipcallgraph.cpp:475] [analysis/app/src/ipcallgraph.cpp:1746] [analysis/app/src/ipcallgraph.cpp:891].
- Expected: For the proposed test, report that no requested roots resolved and print no DIRECT _init-to-helper edge [analysis/app/src/testSyspart.cpp:127] [analysis/app/src/syspart.cpp:1650].
- Actual: The source predicts a DIRECT _init-to-helper record despite the empty root file; this is not runtime-confirmed [analysis/app/src/ipcallgraph.cpp:475] [analysis/app/src/ipcallgraph.cpp:891] [analysis/app/src/ipcallgraph.cpp:763].
- Evidence: analysis/app/src/testSyspart.cpp:143 — the caller checks that -s was supplied, but not that its file resolves any functions; analysis/app/src/syspart.cpp:1638 — run15 returns only if the file cannot be opened; analysis/app/src/syspart.cpp:1645 — an empty file skips root lookup, with no subsequent empty-root guard before generation; analysis/app/src/ipcallgraph.cpp:1744 — direct generation calls findData; analysis/app/src/ipcallgraph.cpp:475 — findData queues _init as a root; analysis/app/src/ipcallgraph.cpp:1746 — generation traverses queued roots; analysis/app/src/ipcallgraph.cpp:891 — traversal records a direct function target; analysis/app/src/ipcallgraph.cpp:755 — printing iterates graph nodes and emits DIRECT records at line 763.
- Assessment: Tiny test case: use an empty absolute-path root file with a parsed module whose _init directly calls helper. The proposed expected output is a no-resolved-roots message and no DIRECT edge, because mode 23 requests a graph from functions in that file [analysis/app/src/testSyspart.cpp:127] [analysis/app/src/testSyspart.cpp:520]. The source instead permits graph generation after zero roots resolve, adding avoidable analysis work [analysis/app/src/syspart.cpp:1645] [analysis/app/src/syspart.cpp:1656] [analysis/app/src/syspart.cpp:1663]. No binary was run.

### Root-file lookup rescans all parsed functions for every name

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspart.cpp:1647`
- Invariant: Resolving R root names against F parsed functions should reuse a name index across the root file [analysis/app/src/syspart.cpp:1645] [analysis/app/src/syspart.cpp:66].
- Mechanism: Each line calls findFunctionByName, which loops over modules and their functions; no lookup result or name index is reused by the next line [analysis/app/src/syspart.cpp:1645] [analysis/app/src/syspart.cpp:1647] [analysis/app/src/syspart.cpp:69] [analysis/app/src/syspart.cpp:71].
- Reproducer: Bounded cost: R distinct missing names in the root file cause R full scans of F parsed functions, or O(RF) name checks, before graph construction; no workload was run [analysis/app/src/syspart.cpp:1645] [analysis/app/src/syspart.cpp:1647] [analysis/app/src/syspart.cpp:69] [analysis/app/src/syspart.cpp:80].
- Expected: Reuse a function-name index across root-file lines while preserving the name and alias matching in the current lookup [analysis/app/src/syspart.cpp:73] [analysis/app/src/syspart.cpp:1645].
- Actual: The source performs a fresh scan per line; missing names scan all functions, with no cache in this path [analysis/app/src/syspart.cpp:66] [analysis/app/src/syspart.cpp:69] [analysis/app/src/syspart.cpp:71] [analysis/app/src/syspart.cpp:1647]. Runtime cost was not measured.
- Evidence: analysis/app/src/testSyspart.cpp:52 — an absolute -s argument selects a root file; analysis/app/src/testSyspart.cpp:158 — parsing precedes dispatch; analysis/app/src/testSyspart.cpp:520 — mode 23 calls run15; analysis/app/src/syspart.cpp:1638 — an unreadable file returns; analysis/app/src/syspart.cpp:1645 — each readable line invokes the lookup; analysis/app/src/syspart.cpp:69 — the lookup scans modules and functions, breaking only the inner loop on a match; analysis/app/src/syspart.cpp:1656 — graph setup follows root lookup.
- Assessment: A tiny test is an absolute-path root file containing two distinct names absent from the parsed program. In mode -a 23, expect two stderr lines ending in "not found"; this is a source prediction, not observed output [analysis/app/src/testSyspart.cpp:52] [analysis/app/src/testSyspart.cpp:520] [analysis/app/src/syspart.cpp:1653]. Each missing name traverses every module's functions, so R missing names cause O(RF) function checks [analysis/app/src/syspart.cpp:69] [analysis/app/src/syspart.cpp:71] [analysis/app/src/syspart.cpp:73] [analysis/app/src/syspart.cpp:1645].

### A root in an NSS library can be missed before the library is parsed

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:1647`
- Invariant: Each name in the root file should be resolved against the modules used to build the graph [analysis/app/src/syspart.cpp:1645] [analysis/app/src/syspart.cpp:1658] [analysis/app/src/syspart.cpp:1666].
- Mechanism: run15 resolves every root before resolveNss; resolveNss can parse additional NSS libraries afterward [analysis/app/src/syspart.cpp:1645] [analysis/app/src/syspart.cpp:1658] [analysis/app/src/ipcallgraph.cpp:1919] [analysis/app/src/ipcallgraph.cpp:1920].
- Reproducer: Source-bounded case: name a function in a backend library loaded only by resolveNss, where that function is neither a needed NSS entry nor reachable from another root. The early lookup cannot find it, and resolveNss queues only its identified needed functions [analysis/app/src/syspart.cpp:1647] [analysis/app/src/ipcallgraph.cpp:1920] [analysis/app/src/ipcallgraph.cpp:1925] [analysis/app/src/ipcallgraph.cpp:1938].
- Expected: The named backend function is rooted and its direct call appears in mode 23 output [analysis/app/src/syspart.cpp:1650] [analysis/app/src/ipcallgraph.cpp:1770] [analysis/app/src/ipcallgraph.cpp:763].
- Actual: For a backend parsed only after the root lookup, the name is skipped; its otherwise unreachable outgoing edge is predicted to be absent [analysis/app/src/syspart.cpp:1647] [analysis/app/src/syspart.cpp:1653] [analysis/app/src/ipcallgraph.cpp:1920] [analysis/app/src/ipcallgraph.cpp:1770].
- Evidence: analysis/app/src/testSyspart.cpp:520 — mode 23 calls run15; analysis/app/src/syspart.cpp:1645 — run15 reads root names; analysis/app/src/syspart.cpp:1647 — each name is looked up before NSS resolution; analysis/app/src/syspart.cpp:66 — lookup searches only modules currently in the program; analysis/app/src/syspart.cpp:1650 — only a found function is added as a root; analysis/app/src/syspart.cpp:1658 — resolveNss runs afterward; analysis/app/src/ipcallgraph.cpp:1919 — NSS resolution adds a backend dependency; analysis/app/src/ipcallgraph.cpp:1920 — it then parses libraries; analysis/tools/egalito/src/conductor/conductor.cpp:102 — parsing skips libraries already parsed; analysis/app/src/ipcallgraph.cpp:1925 — NSS resolution looks up only identified needed functions; analysis/app/src/ipcallgraph.cpp:1938 — it roots those functions; analysis/app/src/ipcallgraph.cpp:1770 — graph generation processes queued roots.
- Assessment: A tiny test would use a program that imports an NSS lookup, an NSS backend loaded only during resolveNss, and a root file naming a unique backend function probe_root that calls probe_marker. Keep probe_root unreachable from other functions and outside the backend's init and fini entries [analysis/app/src/nss.cpp:47] [analysis/app/src/nss.cpp:59] [analysis/app/src/ipcallgraph.cpp:400] [analysis/app/src/ipcallgraph.cpp:475]. Expected output is a DIRECT edge from probe_root to probe_marker; the source instead predicts the missing-root diagnostic and no such edge [analysis/app/src/syspart.cpp:1653] [analysis/app/src/ipcallgraph.cpp:763]. No runtime output was captured.

### Callgraph printing flushes stdout for every edge

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/ipcallgraph.cpp:763`
- Invariant: Printing E edge records needs E records but does not require E stdout flushes [analysis/app/src/ipcallgraph.cpp:755] [analysis/app/src/ipcallgraph.cpp:763] [analysis/app/src/ipcallgraph.cpp:770] [analysis/app/src/ipcallgraph.cpp:774].
- Mechanism: Mode 23 calls printCallGraphWithCallsites, whose direct and indirect record branches each end with std::endl, flushing the stream per record [analysis/app/src/testSyspart.cpp:522] [analysis/app/src/syspart.cpp:1673] [analysis/app/src/ipcallgraph.cpp:763] [analysis/app/src/ipcallgraph.cpp:770] [analysis/app/src/ipcallgraph.cpp:774].
- Reproducer: Bounded cost: a constructed graph with E printed edges executes E record-level flushes; broad indirect candidate sets increase E. No workload or timing measurement was run [analysis/app/src/ipcallgraph.cpp:760] [analysis/app/src/ipcallgraph.cpp:766] [analysis/app/src/ipcallgraph.cpp:763] [analysis/app/src/ipcallgraph.cpp:774].
- Expected: Write each edge record with a newline while allowing stdout to buffer records [analysis/app/src/ipcallgraph.cpp:763] [analysis/app/src/ipcallgraph.cpp:770] [analysis/app/src/ipcallgraph.cpp:774].
- Actual: The source flushes stdout for every printed edge record [analysis/app/src/ipcallgraph.cpp:763] [analysis/app/src/ipcallgraph.cpp:770] [analysis/app/src/ipcallgraph.cpp:774].
- Evidence: analysis/app/src/testSyspart.cpp:77 — -a selects the analysis number; analysis/app/src/testSyspart.cpp:520 — mode 23; analysis/app/src/testSyspart.cpp:522 — calls run15 with option 1; analysis/app/src/syspart.cpp:1671 — option 1 selects callgraph printing; analysis/app/src/syspart.cpp:1673 — calls printCallGraphWithCallsites; analysis/app/src/ipcallgraph.cpp:763 — direct edge record ends with endl; analysis/app/src/ipcallgraph.cpp:770 — resolved indirect edge record ends with endl; analysis/app/src/ipcallgraph.cpp:774 — unresolved indirect edge record ends with endl.
- Assessment: The file-open check can stop mode 23 before printing, but a valid start-function file reaches the printer [analysis/app/src/syspart.cpp:1636] [analysis/app/src/syspart.cpp:1638] [analysis/app/src/syspart.cpp:1673]. Each printed edge ends with std::endl, so E records cause E stream flushes; elapsed cost is unmeasured [analysis/app/src/ipcallgraph.cpp:762] [analysis/app/src/ipcallgraph.cpp:763] [analysis/app/src/ipcallgraph.cpp:769] [analysis/app/src/ipcallgraph.cpp:770] [analysis/app/src/ipcallgraph.cpp:773] [analysis/app/src/ipcallgraph.cpp:774]. Tiny test case: a graph with one direct edge from main at 0x1000, callsite 0x1010, to foo at 0x2000, with both functions in module app, should print `DIRECT app 1010 main 2000 foo app 1000\n` and need no per-record flush [analysis/app/src/ipcallgraph.cpp:760] [analysis/app/src/ipcallgraph.cpp:763].

<!-- harness:logic:mode-23:end -->

<!-- harness:logic:mode-24:start -->
## Harness logic audit — mode 24

Dispatcher and modules: analysis/app/src/testSyspart.cpp, analysis/app/src/syspart.cpp, analysis/app/src/syspart.h, analysis/tools/egalito/src/conductor/interface.cpp, analysis/tools/egalito/src/pass/findsyscalls.cpp, analysis/tools/egalito/src/pass/findsyscalls.h

### A large syscall number can acquire another number's name

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:222`
- Invariant: The name and decimal number in a mode 24 row must refer to the same resolved value (analysis/app/src/syspart.cpp:207-222).
- Mechanism: FindSyscalls retains numbers as unsigned long, but the name map has int keys. Looking up system_calls[value] narrows a large value while the row prints the original value (analysis/tools/egalito/src/pass/findsyscalls.h:15; analysis/app/src/syspart.h:42; analysis/app/src/syspart.cpp:222).
- Reproducer: Source-bounded case: resolve 4294967335 (2^32 + 39) from RAX at a syscall instruction; the value can enter the result set without narrowing (analysis/tools/egalito/src/analysis/slicingtree.h:31-36; analysis/tools/egalito/src/pass/findsyscalls.cpp:40-45,139-140). No mode 24 output was observed.
- Expected: A mode 24 row for 4294967335 has no `getpid` label (analysis/app/src/syspart.cpp:92,222).
- Actual: Source-predicted: `getpid 4294967335` in the row when key 39 maps to `getpid` (analysis/app/src/syspart.cpp:92,222). No runtime output was observed.
- Evidence: analysis/app/src/testSyspart.cpp:525-527 — mode 24 calls printDirectSyscalls; analysis/tools/egalito/src/analysis/usedef.cpp:1037-1047,1075-1077,2074-2080 — MOVABS can define a register with a constant; analysis/tools/egalito/src/pass/findsyscalls.cpp:40-45,139-140 — a resolved RAX constant enters the unsigned-long result set; analysis/tools/egalito/src/pass/findsyscalls.h:15,20-21 — the result retains unsigned-long values; analysis/app/src/syspart.h:42 — syscall names use int keys; analysis/app/src/syspart.cpp:220-222 — lookup converts the value to an int key while output prints the original decimal value.
- Assessment: No range guard appears between the resolved value and the mode 24 lookup (analysis/tools/egalito/src/pass/findsyscalls.cpp:139-140; analysis/app/src/syspart.cpp:213-222). Tiny test: analyze a function containing `movabs $4294967335, %rax; syscall` in mode 24. The expected row must not call 4294967335 `getpid`; the source predicts `getpid 4294967335` when the name map contains its default entry for 39 (analysis/app/src/syspart.cpp:92,222).

### Every ordinary instruction incurs an unnecessary state-map lookup

- Status: **supported**
- Kind: performance
- Location: `analysis/tools/egalito/src/pass/findsyscalls.cpp:39`
- Invariant: The instruction state is needed only when resolving a syscall instruction or a recognized call to libc syscall() (analysis/tools/egalito/src/pass/findsyscalls.cpp:40-45,52-74).
- Mechanism: The visitor calls getState before checking the instruction. getState performs an ordered-map lookup, including for ordinary instructions that produce no result (analysis/tools/egalito/src/pass/findsyscalls.cpp:36-40,82-84; analysis/tools/egalito/src/analysis/usedef.h:306; analysis/tools/egalito/src/analysis/usedef.cpp:340-342).
- Reproducer: Bounded cost: one scanned function with I instructions and one syscall site performs I state-map lookups, although only the candidate site needs one; the map contains an entry per instruction (analysis/app/src/syspart.cpp:211-214; analysis/tools/egalito/src/pass/findsyscalls.cpp:36-44; analysis/tools/egalito/src/analysis/usedef.cpp:331-341). No runtime cost was measured.
- Expected: For a visited function with I instructions and one syscall site, one state lookup suffices for that site (analysis/tools/egalito/src/pass/findsyscalls.cpp:40-45).
- Actual: The source performs I state-map lookups, leaving I−1 avoidable lookups in that case (analysis/tools/egalito/src/pass/findsyscalls.cpp:36-40; analysis/tools/egalito/src/analysis/usedef.cpp:340-342).
- Evidence: analysis/app/src/testSyspart.cpp:525-528 — mode 24 calls printDirectSyscalls; analysis/app/src/syspart.cpp:209-214 — it visits every function; analysis/tools/egalito/src/pass/findsyscalls.cpp:19-27 — libc syscall() and empty-CFG functions return early; analysis/tools/egalito/src/pass/findsyscalls.cpp:36-40 — every instruction reaches getState before the syscall check; analysis/tools/egalito/src/pass/findsyscalls.cpp:52-74 — a recognized libc syscall() target also uses the state; analysis/tools/egalito/src/pass/findsyscalls.cpp:82-84 — other instructions produce no result; analysis/tools/egalito/src/analysis/usedef.h:306 and analysis/tools/egalito/src/analysis/usedef.cpp:340-342 — getState indexes an ordered map.
- Assessment: Tiny proposed test: analyze an x86-64 function `foo` containing `mov rax, 39; syscall; ret`. Expect a `foo ... getpid 39` row and, by source trace, three state-map lookups where one is needed for syscall resolution. The row format and syscall name come from analysis/app/src/syspart.cpp:222 and analysis/app/src/syspart.cpp:92; the lookup count follows from analysis/tools/egalito/src/pass/findsyscalls.cpp:36-44. The test was not run.

### An unresolved PLT call to libc syscall loses a direct syscall row

- Status: **supported**
- Kind: logic
- Location: `analysis/tools/egalito/src/pass/findsyscalls.cpp:63`
- Invariant: Mode 24 should report a resolvable syscall number passed to libc's syscall function (analysis/app/src/testSyspart.cpp:525-529; analysis/tools/egalito/src/pass/findsyscalls.cpp:68-74).
- Mechanism: When PLT resolution leaves a trampoline without a target, CollapsePLTPass preserves its link. FindSyscalls recognizes the trampoline but immediately continues, without examining the call's RDI value (analysis/tools/egalito/src/pass/collapseplt.cpp:95-107; analysis/tools/egalito/src/pass/findsyscalls.cpp:54-74).
- Reproducer: Source-bounded case: a function sets RDI to 39 and calls syscall@PLT, whose target remains unresolved during analysis (analysis/tools/egalito/src/pass/resolveplt.cpp:89-102; analysis/tools/egalito/src/pass/collapseplt.cpp:95-107; analysis/tools/egalito/src/pass/findsyscalls.cpp:54-74). No mode 24 output was observed.
- Expected: For the stated test and a resolvable RDI value, a `probe <address> <module> getpid 39` row (analysis/tools/egalito/src/pass/findsyscalls.cpp:68-74; analysis/app/src/syspart.cpp:92; analysis/app/src/syspart.cpp:217-224).
- Actual: The source predicts no row from that call: the PLT branch continues before adding an entry to `numberMap`, and the printer emits only entries in that map (analysis/tools/egalito/src/pass/findsyscalls.cpp:56-74; analysis/app/src/syspart.cpp:213-224).
- Evidence: analysis/app/src/testSyspart.cpp:156-167 — parsing is followed by PLT resolution and collapse before mode dispatch; analysis/tools/egalito/src/pass/resolveplt.cpp:89-102 — resolution can leave a target unset; analysis/tools/egalito/src/pass/collapseplt.cpp:95-107 — collapse retains the PLT link when that target is unset; analysis/tools/egalito/src/chunk/link.cpp:26-28 — the retained link targets the trampoline; analysis/tools/egalito/src/pass/findsyscalls.cpp:56-74 — the trampoline branch continues before checking the libc syscall target or RDI. A resolved target is converted to a normal link by collapse, so that path does not refute the unresolved case (analysis/tools/egalito/src/pass/collapseplt.cpp:95-99).
- Assessment: A tiny test is `extern long syscall(long, ...); long probe(void) { return syscall(39); }`. If analysis leaves its `syscall@PLT` target unresolved but can determine RDI=39, mode 24 should print a `probe <address> <module> getpid 39` row: mode 24 calls `printDirectSyscalls`, the printer emits rows from `FindSyscalls`, and the syscall table maps 39 to getpid (analysis/app/src/testSyspart.cpp:525-529; analysis/app/src/syspart.cpp:92; analysis/app/src/syspart.cpp:207-224). This is source-supported only; no output was observed.

### Printing unknown syscall numbers grows the name map

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspart.cpp:222`
- Invariant: Printing a resolved number absent from the name table does not require adding it to that table (analysis/app/src/syspart.h:42; analysis/app/src/syspart.cpp:207-224).
- Mechanism: Mode 24 uses map operator[] for each emitted number, inserting an empty string when the key is absent; the map remains a Syspart member across the function scan (analysis/app/src/syspart.h:42; analysis/app/src/syspart.cpp:209-222).
- Reproducer: Bounded cost: U distinct resolved numbers absent from the loaded table cause U additional map entries during printing (analysis/tools/egalito/src/pass/findsyscalls.cpp:40-45,139-140; analysis/app/src/syspart.cpp:215-222). No memory cost was measured.
- Expected: Printing an absent name leaves the map unchanged (analysis/app/src/syspart.h:42; analysis/app/src/syspart.cpp:217-222).
- Actual: For each distinct absent int key reached by the print loop, std::map::operator[] inserts an empty string into the Syspart member map, yielding O(U) avoidable entries for U such keys (analysis/app/src/syspart.h:42; analysis/app/src/syspart.cpp:209-222).
- Evidence: analysis/app/src/testSyspart.cpp:153-167 — creates Syspart and populates its name map; analysis/app/src/testSyspart.cpp:525-528 — mode 24 calls printDirectSyscalls; analysis/app/src/syspart.cpp:209-220 — scans functions and resolved values; analysis/tools/egalito/src/pass/findsyscalls.cpp:40-45 — records resolved syscall-instruction values; analysis/tools/egalito/src/pass/findsyscalls.cpp:68-74 — also records resolved calls to libc syscall(); analysis/app/src/syspart.cpp:222 — indexes the member map for every printed value.
- Assessment: No guard refutes the candidate: mode 24 calls printDirectSyscalls after loading the name map, and the print loop has no membership check (analysis/app/src/testSyspart.cpp:167; analysis/app/src/testSyspart.cpp:525-528; analysis/app/src/syspart.cpp:217-222). A tiny test would give one function at address 0x1000 in module m a resolved syscall value of 700, with 700 absent from the loaded table. Expected output is "f 1000 m  700\n", with the map size unchanged; the current lookup predicts the same output but one extra map entry (analysis/app/src/syspart.cpp:222; analysis/app/src/syspart.h:42). This is source-supported; no runtime output or memory cost was measured.

<!-- harness:logic:mode-24:end -->

<!-- harness:logic:mode-25:start -->
## Harness logic audit — mode 25

Dispatcher and modules: README.md, analysis/app/README.md, analysis/app/src/testSyspart.cpp, analysis/app/src/syspart.cpp, analysis/app/src/syspart.h

### Mode 25 runs unused setup before listing functions

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/testSyspart.cpp:162`
- Invariant: The listing needs the parsed Program's function names, addresses, and modules (analysis/app/src/syspart.cpp:229-235).
- Mechanism: Before dispatch, the driver runs two PLT passes, populates a syscall map, and may search every module for the supplied start function (analysis/app/src/testSyspart.cpp:162-181; analysis/app/src/syspart.cpp:47-80,131-157). Mode 25 only calls printAllFunctions, which reads none of those results (analysis/app/src/testSyspart.cpp:530-533; analysis/app/src/syspart.cpp:229-235).
- Reproducer: Bounded source argument: with F parsed functions, a name-form -s adds a scan of up to F functions before the listing's own F-function traversal; the PLT passes and header reads add further work (analysis/app/src/syspart.cpp:66-80,229-235; analysis/app/src/testSyspart.cpp:162-167). No workload was run.
- Expected: For the proposed one-function Program, one listing row: "main 1000 module-tiny" (analysis/app/src/syspart.cpp:229-238).
- Actual: Source shows the extra setup and optional name lookup execute before that row is printed; no runtime output or timing was observed (analysis/app/src/testSyspart.cpp:162-186,530-533).
- Evidence: analysis/app/src/testSyspart.cpp:156-167 — after parsing, both PLT passes and syscall-map population run before dispatch; analysis/app/src/testSyspart.cpp:179-186 — a name-form -s also triggers function lookup before dispatch; analysis/app/src/syspart.cpp:66-80 — lookup scans functions across modules; analysis/app/src/testSyspart.cpp:530-533 — mode 25 only calls printAllFunctions; analysis/app/src/syspart.cpp:229-238 — that method reads function names, addresses, and module names. The PLT passes resolve symbols and rewrite links (analysis/tools/egalito/src/pass/resolveplt.cpp:17-31,86-94; analysis/tools/egalito/src/pass/collapseplt.cpp:64-70,89-104), which the listing does not read (analysis/app/src/syspart.cpp:229-238).
- Assessment: No mode 25 guard skips setup. The driver requires -s, even though the listing does not use the selected start function (analysis/app/src/testSyspart.cpp:143-146,530-533; analysis/app/src/syspart.cpp:229-238). A tiny test would use a parsed Program with one function named main at 0x1000 in module-tiny; the expected listing row is "main 1000 module-tiny" (analysis/app/src/syspart.cpp:229-238). No binary was run, so the elapsed cost is unmeasured.

### Each mode 25 row flushes stdout

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspart.cpp:235`
- Invariant: Printing N function rows needs N line breaks, without requiring N explicit stream flushes (analysis/app/src/syspart.cpp:231-235).
- Mechanism: The printer ends every row with std::endl, which inserts a newline and flushes the stream (analysis/app/src/syspart.cpp:233-235).
- Reproducer: Bounded source argument: a parsed Program with N functions executes the line at syspart.cpp:235 N times, requesting N flushes; mode 25 calls that printer directly (analysis/app/src/syspart.cpp:231-235; analysis/app/src/testSyspart.cpp:530-533). No output or timing was observed.
- Expected: One newline per function row, without a required flush per row (analysis/app/src/syspart.cpp:231-235).
- Actual: The source requests one flush per function row through `endl`; no runtime impact was observed (analysis/app/src/syspart.cpp:233-235).
- Evidence: analysis/app/src/testSyspart.cpp:77-86 — `-a` selects the mode; analysis/app/src/testSyspart.cpp:137-160 — required arguments are checked and the parsed Program is assigned; analysis/app/src/testSyspart.cpp:530-533 — mode 25 calls `printAllFunctions` directly, with no case-level guard; analysis/app/src/syspart.cpp:229-238 — the printer visits each module and function, and writes one `endl` per function.
- Assessment: For a tiny parsed Program containing one module named M with functions foo at 0x10 and bar at 0x20, mode 25 should print `foo 10 M\nbar 20 M\n`; each row would also request a stream flush because it ends with `endl` (analysis/app/src/syspart.cpp:231-235). Replacing `endl` with `\n` would preserve those rows without requesting a flush per row (analysis/app/src/syspart.cpp:235). No binary was run, so the runtime cost is unmeasured.

<!-- harness:logic:mode-25:end -->

<!-- harness:logic:mode-26:start -->
## Harness logic audit — mode 26

Dispatcher and modules: analysis/app/src/testSyspart.cpp, analysis/app/src/syspart.cpp, analysis/tools/egalito/src/chunk/dump.cpp, analysis/tools/egalito/src/disasm/dump.cpp, analysis/tools/egalito/src/conductor/interface.cpp, analysis/tools/egalito/src/log/log.h

### Mode 26 can silently omit the requested disassembly

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/testSyspart.cpp:156`
- Invariant: A successful disassembly request should emit instruction lines (analysis/app/src/testSyspart.cpp:535-545).
- Mechanism: Without `-l`, the interface mutes logging; the function heading uses `cout`, but the dumper and instruction printer use logging (analysis/tools/egalito/src/conductor/interface.cpp:11-14; analysis/app/src/syspart.cpp:486-490; analysis/tools/egalito/src/chunk/dump.cpp:52-77; analysis/tools/egalito/src/disasm/dump.cpp:21-29).
- Reproducer: Source-bounded case: use a resolvable function with `-a 26,<name>`, omit `-l`, and leave `EGALITO_DEBUG` unset (analysis/app/src/testSyspart.cpp:535-545; analysis/tools/egalito/src/conductor/interface.cpp:11-19).
- Expected: For a resolved function containing instructions, the mode 26 output includes instruction lines (analysis/app/src/testSyspart.cpp:129; analysis/app/src/syspart.cpp:486-490).
- Actual: Source-predicted: a resolved function prints `DISASSEMBLY OF <name>` and a blank line, but no instruction lines (analysis/app/src/syspart.cpp:486-492; analysis/tools/egalito/src/disasm/dump.cpp:62-66).
- Evidence: analysis/app/src/testSyspart.cpp:27,71 — logging defaults off and `-l` enables it; analysis/app/src/testSyspart.cpp:156 — the flag reaches EgalitoInterface; analysis/tools/egalito/src/conductor/interface.cpp:12-25 — the constructor mutes logging, then parses the environment; analysis/tools/egalito/src/log/registry.cpp:33-36,57-60 — muting sets bounds to -1 and an unset environment variable leaves them there; analysis/app/src/testSyspart.cpp:535-545 — mode 26 calls printDisass without changing logging; analysis/app/src/syspart.cpp:486-492 — a resolved function gets a cout heading and a ChunkDumper visit; analysis/tools/egalito/src/chunk/dump.cpp:52-77 — the dumper reaches instructions through logging guarded output; analysis/tools/egalito/src/disasm/dump.cpp:21-29,62-66,96 — instruction printing returns when logging is muted.
- Assessment: Tiny test case: with an existing binary whose `main` contains an instruction, run `testSyspart -p ./tiny-main -s main -a 26,main` with `EGALITO_DEBUG` unset and without `-l`. Mode 26 requests `printDisass` (analysis/app/src/testSyspart.cpp:535-545). Expected: `DISASSEMBLY OF main` followed by an instruction line. The source predicts the heading and a blank line, with no instruction lines (analysis/app/src/syspart.cpp:486-492; analysis/tools/egalito/src/disasm/dump.cpp:62-66). No runtime output was observed.

### A release build compiles out mode 26's disassembly

- Status: **supported**
- Kind: logic
- Location: `analysis/tools/egalito/src/log/defaults.h:13`
- Invariant: Mode 26 should remain able to print instructions in a supported build (analysis/app/src/testSyspart.cpp:107-108,535-545).
- Mechanism: The release target defines `RELEASE_BUILD`, which sets both chunk and disassembly log groups to `-1`; the logging macros then compile their output away (analysis/tools/egalito/src/Makefile:89-90; analysis/tools/egalito/src/log/defaults.h:9-15; analysis/tools/egalito/src/log/log.h:51-55,80-88).
- Reproducer: Source-bounded case: link against Egalito built with its `release` target and request a resolvable function with `-a 26,<name> -l` (analysis/tools/egalito/src/Makefile:89-90; analysis/app/src/testSyspart.cpp:535-545).
- Expected: For a resolved `main`, a heading and at least one instruction line (analysis/app/src/syspart.cpp:486-490; analysis/tools/egalito/src/chunk/dump.cpp:62-77,202-205).
- Actual: Source-predicted for the specified fresh release build: a heading and blank line on stdout, with no instruction lines; timing is printed on stderr (analysis/tools/egalito/src/log/defaults.h:9-15; analysis/tools/egalito/src/log/log.h:83-88; analysis/tools/egalito/src/disasm/dump.cpp:24-30,66-94; analysis/app/src/syspart.cpp:486-492; analysis/app/src/testSyspart.cpp:597-601).
- Evidence: analysis/app/src/testSyspart.cpp:71,156 — `-l` enables verbose logging; analysis/app/src/testSyspart.cpp:535-545 — mode 26 calls `printDisass`; analysis/app/src/syspart.cpp:474-492 — a resolved function gets a cout heading and visits `ChunkDumper`; analysis/tools/egalito/src/chunk/dump.cpp:52-77,202-205 — the visitor reaches `InstrDumper`, which calls `DisasmDump`; analysis/tools/egalito/env.mk:181,189 — library compilation assigns logging groups from source directories; analysis/tools/egalito/src/Makefile:89-90 and analysis/tools/egalito/src/log/defaults.h:9-15 — release compilation sets chunk and disasm levels to -1; analysis/tools/egalito/src/log/log.h:51-55,83-88 — their LOG and IF_LOG sites become inert; analysis/tools/egalito/src/disasm/dump.cpp:24-30,66-94 — instruction printing returns before formatting, and its final output uses LOG.
- Assessment: A tiny test case is a binary with a resolvable `main` containing one instruction, invoked with `-p /path/to/tiny -s main -a 26,main -l` (analysis/app/src/testSyspart.cpp:140-160,535-545). With a freshly built Egalito `release` library, the expected mode 26 output includes an instruction line; the source instead predicts `DISASSEMBLY OF main` followed by a blank line on stdout, plus the program's timing line on stderr (analysis/tools/egalito/src/Makefile:89-90; analysis/tools/egalito/src/chunk/dump.cpp:62-77,202-205; analysis/tools/egalito/src/disasm/dump.cpp:24-30,66-94; analysis/app/src/syspart.cpp:486-492; analysis/app/src/testSyspart.cpp:597-601). No binary was run.

### Hexadecimal function addresses above signed-long range fail lookup

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:479`
- Invariant: A 64-bit `address_t` supplied as a hexadecimal function address should be usable for lookup (analysis/tools/egalito/src/types.h:7-12; analysis/app/src/syspart.cpp:477-480).
- Mechanism: `printDisass` parses the address with signed `stol` before casting it to `address_t`; an unsigned 64-bit value above `LONG_MAX` cannot be returned by `stol` (analysis/app/src/syspart.cpp:477-480; analysis/tools/egalito/src/types.h:10-12).
- Reproducer: Source-bounded input: `-a 26,0x8000000000000000` on a non-ARM build, with the required `-p` and `-s` arguments (analysis/app/src/testSyspart.cpp:138-151,535-545; analysis/tools/egalito/src/types.h:7-12).
- Expected: The 64-bit address reaches `findFunctionByAddress`; if absent, `printDisass` emits a blank line (analysis/app/src/syspart.cpp:47-61, analysis/app/src/syspart.cpp:479-492).
- Actual: Source predicts an uncaught `std::out_of_range` at `stol`, before lookup, on a build with a 64-bit long; no runtime output was observed (analysis/app/src/syspart.cpp:479-480, analysis/app/src/testSyspart.cpp:535-545).
- Evidence: analysis/app/src/testSyspart.cpp:77-87 — `-a` selects mode 26; analysis/app/src/testSyspart.cpp:138-151 — `-p`, `-s`, and `-a` are required; analysis/app/src/testSyspart.cpp:535-545 — mode 26 passes the address text to `printDisass`; analysis/app/src/syspart.cpp:477-480 — hexadecimal input goes through signed `stol` before lookup; analysis/tools/egalito/src/types.h:7-12 — non-ARM `address_t` is `uint64_t`; analysis/app/src/syspart.cpp:47-61 — lookup accepts an `address_t` and can return null.
- Assessment: A tiny test is mode `-a 26,0x8000000000000000` with a valid `-p` ELF and `-s main` (analysis/app/src/testSyspart.cpp:97-104, analysis/app/src/testSyspart.cpp:535-545). If the address is absent, the expected mode output is a blank line after lookup (analysis/app/src/syspart.cpp:47-61, analysis/app/src/syspart.cpp:486-492). On a build with a 64-bit long, the signed `stol` conversion instead exceeds its range before lookup (analysis/app/src/syspart.cpp:479-480). No binary was run.

### Mode 26 performs unrelated syscall and root-function setup

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/testSyspart.cpp:167`
- Invariant: Preparation for a single-function dump should scale with work needed to select and print that function (analysis/app/src/testSyspart.cpp:535-545; analysis/app/src/syspart.cpp:474-492).
- Mechanism: Before dispatch, the driver populates a syscall map from headers or defaults and resolves the separate `-s` root; `printDisass` uses its own argument and lookup and reads neither result (analysis/app/src/testSyspart.cpp:167-183,535-545; analysis/app/src/syspart.cpp:128-157,474-490).
- Reproducer: Bounded cost: for H header lines and F parsed functions, one mode 26 request performs header processing and up to one additional function scan for `-s`, before the target lookup (analysis/app/src/syspart.cpp:47-77,128-157; analysis/app/src/testSyspart.cpp:167-183).
- Expected: A mode 26 request prepares the target lookup and dump (analysis/app/src/testSyspart.cpp:535-545; analysis/app/src/syspart.cpp:474-492).
- Actual: The source adds header processing or default-map construction on every accepted request, plus a separate function scan when `-s` names or addresses a root (analysis/app/src/testSyspart.cpp:143-167,173-183; analysis/app/src/syspart.cpp:47-80,95-157).
- Evidence: analysis/app/src/testSyspart.cpp:138-151 — `-s` is required, so this finding applies to accepted requests. analysis/app/src/testSyspart.cpp:167-183 — syscall-map population and, for `-s main`, root lookup occur before mode dispatch; `-s all` or a file skips the root lookup. analysis/app/src/syspart.cpp:95-157 — map population processes open header files line by line or fills defaults. analysis/app/src/syspart.cpp:66-80 — name lookup scans parsed functions across modules. analysis/app/src/testSyspart.cpp:535-545 — mode 26 passes its separate argument to `printDisass`. analysis/app/src/syspart.cpp:474-492 — `printDisass` performs its own lookup and dump without reading the syscall map or root.
- Assessment: For a tiny binary defining `main` and `target`, a proposed test is `testSyspart -p ./tiny -s main -a 26,target`. The expected output begins `DISASSEMBLY OF target`, followed by its dump and a newline (analysis/app/src/testSyspart.cpp:535-545; analysis/app/src/syspart.cpp:474-492). The source supports the avoidable preparation cost, but no binary was run and no elapsed time or memory was measured.

### Muted dumps still traverse and format the selected function

- Status: **supported**
- Kind: performance
- Location: `analysis/tools/egalito/src/chunk/dump.cpp:77`
- Invariant: When disassembly output is disabled, formatting work should not be performed for every instruction (analysis/tools/egalito/src/disasm/dump.cpp:21-29).
- Mechanism: The dumper visits each instruction and invokes its semantic visitor before the disassembly printer checks its log level; linked instructions also regenerate assembly before that check (analysis/tools/egalito/src/chunk/dump.cpp:52-77,209-216; analysis/tools/egalito/src/disasm/dump.cpp:21-29).
- Reproducer: Bounded cost: a selected function with N linked instructions incurs N semantic visits and N assembly regenerations even when logging is muted by omitting `-l` (analysis/app/src/testSyspart.cpp:156; analysis/tools/egalito/src/conductor/interface.cpp:11-14; analysis/tools/egalito/src/chunk/dump.cpp:62-77,209-216).
- Expected: Muted disassembly should avoid per-instruction formatting and regeneration (analysis/tools/egalito/src/disasm/dump.cpp:21-29; analysis/tools/egalito/src/chunk/dump.cpp:207-212).
- Actual: The source supports one semantic visit per traversed instruction and one assembly regeneration per traversed `LinkedInstruction`, even when printing is muted; no runtime cost was measured (analysis/tools/egalito/src/chunk/dump.cpp:52-77,207-212; analysis/tools/egalito/src/disasm/dump.cpp:21-29).
- Evidence: analysis/app/src/testSyspart.cpp:535-545 — mode 26 calls printDisass; analysis/app/src/syspart.cpp:474-490 — a found function is passed to ChunkDumper; analysis/tools/egalito/src/chunk/dump.h:14-18 — recursion accepts each child; analysis/tools/egalito/src/chunk/dump.cpp:52-77 — function and block recursion reach the instruction semantic visitor without a log guard; analysis/tools/egalito/src/chunk/dump.cpp:207-212 — LinkedInstruction regenerates assembly; analysis/tools/egalito/src/instr/linked-x86_64.cpp:64-79 — x86-64 regeneration writes data and rebuilds assembly; analysis/tools/egalito/src/disasm/dump.cpp:21-29 — the print guard runs afterward.
- Assessment: The caller has no logging guard before invoking the dumper (analysis/app/src/syspart.cpp:486-490). With `-l` omitted and `EGALITO_DEBUG` unset, the interface mutes logging (analysis/app/src/testSyspart.cpp:27,71,156; analysis/tools/egalito/src/conductor/interface.cpp:12-21), but the dumper still visits every instruction and regenerates assembly for each `LinkedInstruction` before the printer's log check (analysis/tools/egalito/src/chunk/dump.cpp:62-77,207-212; analysis/tools/egalito/src/disasm/dump.cpp:21-29). Tiny test: use a function fixture containing one `LinkedInstruction`, mute logging, and count regeneration calls while dumping it. Expected: zero regeneration calls and only the `DISASSEMBLY OF <name>` header from this path; the source predicts one regeneration call (analysis/app/src/syspart.cpp:488-492; analysis/tools/egalito/src/chunk/dump.cpp:207-212).

### An unnamed control-flow target is labeled with a local variable's address

- Status: **supported**
- Kind: logic
- Location: `analysis/tools/egalito/src/chunk/dump.cpp:286`
- Invariant: A target label in the disassembly should identify the linked target (analysis/tools/egalito/src/chunk/dump.cpp:270-289,309-315).
- Mechanism: When a linked target's name is `???`, the formatter inserts `&target`, the address of its local pointer variable, rather than `target` or the link's target address (analysis/tools/egalito/src/chunk/dump.cpp:270-287).
- Reproducer: Source-bounded case: dump a control-flow instruction whose non-null linked target reports `???`; that name is a defined chunk default (analysis/tools/egalito/src/chunk/chunk.h:78-87; analysis/tools/egalito/src/chunk/dump.cpp:270-287).
- Expected: With level 9 logging and the proposed target at 0x401000, the target label should identify that linked target, for example <target-0x401000> (analysis/tools/egalito/src/chunk/link.cpp:53-59; analysis/tools/egalito/src/chunk/dump.cpp:309-315; analysis/tools/egalito/src/disasm/dump.cpp:85-96).
- Actual: Source-predicted only: the numeric operand uses the link's target address, while the label uses &target, the address of a local pointer variable (analysis/tools/egalito/src/chunk/dump.cpp:285-286; analysis/tools/egalito/src/chunk/dump.cpp:309-315; analysis/tools/egalito/src/disasm/dump.cpp:53-57).
- Evidence: analysis/app/src/testSyspart.cpp:535-545 — mode 26 calls printDisass; analysis/app/src/syspart.cpp:486-490 — a found function enters ChunkDumper; analysis/tools/egalito/src/chunk/dump.cpp:62-77 — each instruction's semantic enters InstrDumper; analysis/tools/egalito/src/chunk/dump.cpp:260-272 — a control-flow instruction obtains its linked target; analysis/tools/egalito/src/chunk/dump.cpp:275-286 — PLT and symbol-only links bypass the fallback, but an unnamed non-null target enters the &target branch; analysis/tools/egalito/src/chunk/dump.cpp:309-315 — the formatted label and the link's target address are passed separately; analysis/tools/egalito/src/disasm/dump.cpp:53-57 — the target address becomes the numeric operand; analysis/tools/egalito/src/disasm/dump.cpp:85-96 — the label is printed in angle brackets.
- Assessment: Mode 26 calls printDisass, which sends a found function to ChunkDumper (analysis/app/src/testSyspart.cpp:535-545; analysis/app/src/syspart.cpp:474-491). A tiny source-bounded test would give a ControlFlowInstruction a JumpTableLink to a JumpTable at 0x401000 and enable disassembly logging at level 9. JumpTable inherits the default name "???", and JumpTableLink returns that chunk as its target (analysis/tools/egalito/src/chunk/jumptable.h:42-65; analysis/tools/egalito/src/chunk/chunk.h:185-210; analysis/tools/egalito/src/chunk/chunk.h:87; analysis/tools/egalito/src/chunk/link.cpp:53-59). The expected label substring is <target-0x401000>; the source instead predicts <target-0x...> using the address of the local pointer variable (analysis/tools/egalito/src/chunk/dump.cpp:281-286; analysis/tools/egalito/src/chunk/dump.cpp:309-315; analysis/tools/egalito/src/disasm/dump.cpp:85-96). No output was captured. Disassembly output requires level 9 logging, and the app mutes logging by default unless configured otherwise (analysis/tools/egalito/src/disasm/dump.cpp:47-66; analysis/app/src/testSyspart.cpp:156; analysis/tools/egalito/src/conductor/interface.cpp:12-25).

### An unknown control-flow target name is replaced with a stack address

- Status: **supported**
- Kind: logic
- Location: `analysis/tools/egalito/src/chunk/dump.cpp:286`
- Invariant: A target label in mode 26's disassembly should identify the linked target (analysis/app/src/syspart.cpp:489-490; analysis/tools/egalito/src/chunk/dump.cpp:270-286).
- Mechanism: When a linked control-flow target has the name `???`, the formatter prints `&target`, the address of its local variable, while it separately obtains the link's target address for the operand (analysis/tools/egalito/src/chunk/dump.cpp:270-286,309-315).
- Reproducer: Source-bounded case: dump a function containing a control-flow instruction whose link resolves to a chunk named `???`; that name is a supported chunk default (analysis/tools/egalito/src/chunk/chunk.h:87; analysis/tools/egalito/src/chunk/dump.cpp:270-286). No runtime output was observed.
- Expected: For the proposed fixture, operand `0x401050` and a destination-identifying label such as `<target-401050>` (analysis/tools/egalito/src/chunk/link.cpp:18-20; analysis/tools/egalito/src/chunk/dump.cpp:309-315).
- Actual: Source-predicted, when printed: operand `0x401050` with a `<target-0x...>` label derived from `&target`, a local variable address (analysis/tools/egalito/src/chunk/dump.cpp:281-286,309-315; analysis/tools/egalito/src/disasm/dump.cpp:47-56,87-96).
- Evidence: analysis/app/src/testSyspart.cpp:535-545 — mode 26 calls printDisass; analysis/app/src/syspart.cpp:474-490 — printDisass passes the selected function to ChunkDumper; analysis/tools/egalito/src/chunk/dump.cpp:54-77 — the dumper reaches each instruction's semantic; analysis/tools/egalito/src/chunk/dump.cpp:260-286 — control-flow formatting selects `&target` when the linked chunk's name is `???`; analysis/tools/egalito/src/chunk/dump.cpp:309-315 — it separately passes the link's target address as the operand. PLT and symbol-only links take earlier branches (analysis/tools/egalito/src/chunk/dump.cpp:275-280). Printing is conditional on logging being enabled (analysis/tools/egalito/src/disasm/dump.cpp:47-50,62-65; analysis/tools/egalito/src/log/defaults.h:9-15,38-44).
- Assessment: Tiny source-bounded test: give a control-flow instruction a NormalLink to a chunk named `???` at 0x401050, then dump its containing function in mode 26. The link can hold a ChunkRef, and `???` is a chunk default (analysis/tools/egalito/src/chunk/link.h:87-95; analysis/tools/egalito/src/chunk/chunk.h:87). Expected output includes operand `0x401050` and a label identifying that destination, such as `<target-401050>`. The source instead predicts `<target-0x...>` using the address of the formatter's local `target` variable (analysis/tools/egalito/src/chunk/dump.cpp:270-286,309-315; analysis/tools/egalito/src/disasm/dump.cpp:47-56,87-96). No output was captured.

### An unknown function produces a blank, successful mode 26 result

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:486`
- Invariant: A request for a function that cannot be resolved should report that no disassembly was produced (analysis/app/src/testSyspart.cpp:535-545; analysis/app/src/syspart.cpp:474-492).
- Mechanism: The name lookup returns null when no function matches; `printDisass` skips its heading and dumper for null, then prints only a newline. The driver subsequently returns zero (analysis/app/src/syspart.cpp:66-80,474-492; analysis/app/src/testSyspart.cpp:594-597).
- Reproducer: Source-bounded input: `-p <binary> -s <resolvable-root> -a 26,__missing__`, where no parsed function has that name (analysis/app/src/testSyspart.cpp:137-146,535-545; analysis/app/src/syspart.cpp:66-80). No runtime output was observed.
- Expected: An explicit failed-lookup message and nonzero status for an unresolved function (analysis/app/src/testSyspart.cpp:535-545; analysis/app/src/syspart.cpp:474-492).
- Actual: Source predicts that `printDisass` emits only a newline for the missing function and, if earlier setup completes, the driver reports elapsed time on stderr and exits zero (analysis/app/src/syspart.cpp:486-492; analysis/app/src/testSyspart.cpp:596-599). No runtime output was observed.
- Evidence: analysis/app/src/testSyspart.cpp:77-87 — parses `26,__missing__` as option 26; analysis/app/src/testSyspart.cpp:535-545 — passes `__missing__` to `printDisass`; analysis/app/src/syspart.cpp:66-80 — returns null if no name matches; analysis/app/src/syspart.cpp:474-492 — skips the heading and dumper for null, then prints a newline; analysis/app/src/testSyspart.cpp:594-599 — prints elapsed time to stderr and returns zero.
- Assessment: The only mode 26 argument guard checks for a comma; it does not check whether the function resolves (analysis/app/src/testSyspart.cpp:535-545). A tiny test would use a binary containing `main` and run `-p <binary> -s main -a 26,__missing__`, with no function named `__missing__`. Expected: an explicit lookup failure and a nonzero exit status. The program also parses the binary and runs PLT passes before reaching mode 26, so a failed lookup incurs that analysis cost (analysis/app/src/testSyspart.cpp:156-167).

<!-- harness:logic:mode-26:end -->

<!-- harness:logic:mode-27:start -->
## Harness logic audit — mode 27

Dispatcher and modules: analysis/app/src/testSyspart.cpp, analysis/app/src/syspart.cpp, analysis/app/src/syspart.h, analysis/app/src/ipcallgraph.cpp

### Mode 27 builds an unused syscall reverse index with quadratic copying

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspart.cpp:313`
- Invariant: Mode 27 needs each function's syscall bitset for propagation and output (analysis/app/src/syspart.cpp:1679, analysis/app/src/syspart.cpp:1681, analysis/app/src/syspart.cpp:1696).
- Mechanism: For every direct syscall, extraction appends to who_invokes_syscalls by copying and reassigning its vector (analysis/app/src/syspart.cpp:296, analysis/app/src/syspart.cpp:304, analysis/app/src/syspart.cpp:313, analysis/app/src/syspart.cpp:315). Mode 27 then calls findDerived4, which reads syscall_mapping and graph children, not that reverse index (analysis/app/src/syspart.cpp:1681, analysis/app/src/syspart.cpp:506, analysis/app/src/syspart.cpp:515).
- Reproducer: Source-bounded case: K rooted functions each contain one resolved syscall with the same number. Successive reverse-index updates copy vectors of lengths 1 through K−1, for Θ(K²) pointer copies (analysis/app/src/syspart.cpp:1645, analysis/app/src/syspart.cpp:1650, analysis/app/src/syspart.cpp:299, analysis/app/src/syspart.cpp:313).
- Expected: Mode 27 computes and prints the root syscall bitsets without building an unused reverse index (analysis/app/src/syspart.cpp:1679, analysis/app/src/syspart.cpp:1681, analysis/app/src/syspart.cpp:1696).
- Actual: The source copies and reassigns the reverse-index vector on each repeated syscall number; runtime cost was not measured (analysis/app/src/syspart.cpp:313, analysis/app/src/syspart.cpp:315).
- Evidence: analysis/app/src/testSyspart.cpp:547 — mode 27 calls run15 with option 2; analysis/app/src/syspart.cpp:1677 — option 2 calls findDirectSyscalls; analysis/app/src/syspart.cpp:304 — extraction looks up the reverse index; analysis/app/src/syspart.cpp:313 — an existing vector is copied and appended; analysis/app/src/syspart.cpp:315 — that vector is assigned back; analysis/app/src/syspart.cpp:319 — extraction separately stores the function bitset; analysis/app/src/syspart.cpp:1681 — mode 27 calls findDerived4; analysis/app/src/syspart.cpp:506 — propagation reads syscall_mapping; analysis/app/src/syspart.cpp:515 — propagation reads child bitsets; analysis/app/src/syspart.cpp:1696 — output combines root bitsets.
- Assessment: Mode 27 reaches the extraction path after the start file opens (analysis/app/src/testSyspart.cpp:547, analysis/app/src/syspart.cpp:1638, analysis/app/src/syspart.cpp:1677). For K graph functions each containing one resolved syscall with the same number, successive vector updates copy 1 through K−1 existing pointers, giving Θ(K²) copying (analysis/app/src/syspart.cpp:284, analysis/app/src/syspart.cpp:296, analysis/app/src/syspart.cpp:313, analysis/app/src/syspart.cpp:315). Tiny test case: two isolated root functions, each with resolved syscall 0, listed in the start file; expected syscall stdout is `read\n` once (analysis/app/src/syspart.cpp:92, analysis/app/src/syspart.cpp:1644, analysis/app/src/syspart.cpp:1696, analysis/app/src/syspart.cpp:1705).

### Propagation rescans the whole graph for each level of a call chain

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspart.cpp:501`
- Invariant: A gained syscall bit must reach its callers before the root bitsets are combined (analysis/app/src/syspart.cpp:515, analysis/app/src/syspart.cpp:523, analysis/app/src/syspart.cpp:1688).
- Mechanism: Each change triggers another pass over every graph node, and each visit constructs a fresh set of call targets (analysis/app/src/syspart.cpp:501, analysis/app/src/syspart.cpp:506, analysis/app/src/syspart.cpp:515, analysis/app/src/ipcallgraph.cpp:127).
- Reproducer: Source-bounded graph: N functions form a chain, only the last invokes a syscall, and nodeMap iterates callers before callees. The bit moves back one level per pass, requiring Θ(N²) node visits, including visits to nodes that gain nothing (analysis/app/src/syspart.cpp:501, analysis/app/src/syspart.cpp:506, analysis/app/src/syspart.cpp:521, analysis/app/src/syspart.cpp:526).
- Expected: Propagate gained bits to affected callers while preserving the root result (analysis/app/src/syspart.cpp:521, analysis/app/src/syspart.cpp:1696).
- Actual: For the stated caller-before-callee chain, the source loop visits all N nodes on each of N passes, yielding Θ(N²) node visits; this is a source trace, not a measured runtime result (analysis/app/src/syspart.cpp:501, analysis/app/src/syspart.cpp:506, analysis/app/src/syspart.cpp:526).
- Evidence: analysis/app/src/testSyspart.cpp:547 — mode 27 calls run15 with option 2; analysis/app/src/syspart.cpp:1677 — that option initializes direct syscall bitsets, then calls findDerived4 before combining root bitsets; analysis/app/src/syspart.cpp:284 — initialization covers every graph node, so the mapping guard does not skip nodes in this path; analysis/app/src/ipcallgraph.h:340 — nodeMap is a map keyed by Function pointers, so caller-before-callee order is possible but not guaranteed; analysis/app/src/syspart.cpp:501 — each change causes another complete nodeMap pass; analysis/app/src/syspart.cpp:515 — each visited node requests its call targets; analysis/app/src/ipcallgraph.cpp:127 — that request constructs and returns a fresh set; analysis/app/src/syspart.cpp:521 — a caller gains its child's bits when visited; analysis/app/src/syspart.cpp:523 — a gained bit requests another pass.
- Assessment: A tiny test would use four mapped functions in caller-before-callee iteration order: f0 → f1 → f2 → f3, with only f3 invoking read and f0 as the root. The expected output is one `read`; a pass counter would show four full passes and 16 node visits, because each changing pass moves the bit back one level and the final pass detects no change (analysis/app/src/syspart.cpp:319, analysis/app/src/syspart.cpp:501, analysis/app/src/syspart.cpp:506, analysis/app/src/syspart.cpp:521, analysis/app/src/syspart.cpp:526, analysis/app/src/syspart.cpp:1696). This supports the proposed quadratic visit count for that ordering. No workload or timing was observed.

### The output loop reads past the 600-bit syscall set

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:1704`
- Invariant: Only bit indices 0 through 599 belong to the 600-bit combined set (analysis/app/src/syspart.cpp:1686).
- Mechanism: The loop permits i to equal combined.size(), then indexes combined[i] (analysis/app/src/syspart.cpp:1702, analysis/app/src/syspart.cpp:1704).
- Reproducer: Source-bounded case: any readable root file that reaches mode 27's output loop causes its final iteration to evaluate combined[600], even when the set is empty (analysis/app/src/syspart.cpp:1638, analysis/app/src/syspart.cpp:1677, analysis/app/src/syspart.cpp:1686, analysis/app/src/syspart.cpp:1702).
- Expected: Only indices 0 through 599 are read; the proposed empty-root case emits no syscall names (analysis/app/src/syspart.cpp:1644-1655, analysis/app/src/syspart.cpp:1686-1698).
- Actual: The source reads combined[600] on the final loop iteration, an out-of-range bitset access. No runtime outcome was observed (analysis/app/src/syspart.cpp:1686, analysis/app/src/syspart.cpp:1702-1704).
- Evidence: analysis/app/src/testSyspart.cpp:52-56 — an absolute -s argument selects a root file; analysis/app/src/testSyspart.cpp:169-172 — passes that path to Syspart; analysis/app/src/testSyspart.cpp:547-550 — mode 27 calls run15 with option 2; analysis/app/src/syspart.cpp:1636-1642 — an unreadable file returns early; analysis/app/src/syspart.cpp:1677-1686 — option 2 creates the 600-bit set; analysis/app/src/syspart.cpp:1702-1704 — the loop includes index 600 and reads it, with no intervening guard.
- Assessment: A tiny proposed case is a valid input binary with an existing, empty absolute-path root file, invoked with -p <binary> -s <empty-file> -a 27. The file produces no start functions, so the expected syscall-name output is empty (analysis/app/src/testSyspart.cpp:52-56, analysis/app/src/testSyspart.cpp:547-550, analysis/app/src/syspart.cpp:1644-1655, analysis/app/src/syspart.cpp:1686-1698). If execution reaches the output loop, its final iteration still evaluates combined[600], outside the 600-bit set; the runtime result is unspecified and was not observed (analysis/app/src/syspart.cpp:1686, analysis/app/src/syspart.cpp:1702-1704).

### Mode 27 retains syscall details that its result never reads

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspart.cpp:293`
- Invariant: Mode 27 propagates per-function bitsets and combines the resolved roots' bitsets (analysis/app/src/syspart.cpp:513, analysis/app/src/syspart.cpp:521, analysis/app/src/syspart.cpp:1696).
- Mechanism: Direct-syscall extraction copies the visitor's per-instruction map into `list`, copies it again into each SysNode, and inserts each value into two sets; mode 27's subsequent propagation and output read the bitset instead (analysis/tools/egalito/src/pass/findsyscalls.h:20, analysis/app/src/syspart.cpp:292, analysis/app/src/syspart.cpp:293, analysis/app/src/syspart.cpp:301, analysis/app/src/syspart.cpp:302, analysis/app/src/syspart.cpp:319, analysis/app/src/syspart.cpp:513, analysis/app/src/syspart.cpp:1696).
- Reproducer: Source-bounded cost: for N graph functions with S resolved syscall sites in total, mode 27 copies and retains the per-instruction result maps and populates both per-function syscall sets, although its result uses the bitsets (analysis/app/src/syspart.cpp:284, analysis/app/src/syspart.cpp:292, analysis/app/src/syspart.cpp:293, analysis/app/src/syspart.cpp:301, analysis/app/src/syspart.cpp:302, analysis/app/src/syspart.cpp:1679, analysis/app/src/syspart.cpp:1696).
- Expected: For mode 27, construct the required bitsets without retaining per-instruction maps or populating unused sets on this path (analysis/app/src/syspart.cpp:303, analysis/app/src/syspart.cpp:1679-1707).
- Actual: The source performs both map copies and both set insertions before mode 27 reads the bitsets (analysis/app/src/syspart.cpp:292-303; analysis/app/src/syspart.cpp:1681-1707).
- Evidence: analysis/app/src/testSyspart.cpp:547-550 — mode 27 selects run15 option 2; analysis/app/src/syspart.cpp:1636-1642 — an unreadable start-function file returns before analysis; analysis/app/src/syspart.cpp:1677-1681 — the selected branch calls findDirectSyscalls then findDerived4; analysis/app/src/syspart.cpp:292-319 — extraction copies and retains the map, populates both sets, and creates the bitset; analysis/app/src/syspart.cpp:513-525 — propagation reads bitsets; analysis/app/src/syspart.cpp:1688-1707 — resolved roots contribute bitsets to printed syscall names.
- Assessment: Mode 27 calls run15 with option 2 (analysis/app/src/testSyspart.cpp:547-550). For each graph function, findDirectSyscalls copies the visitor map into a local value and then into SysNode, and inserts each resolved number into two sets (analysis/tools/egalito/src/pass/findsyscalls.h:20-21; analysis/app/src/syspart.cpp:284-303). The mode 27 path subsequently propagates and prints bitsets; it does not read those retained maps or sets (analysis/app/src/syspart.cpp:1677-1707). Other modes do read syscallMap and direct_syscalls, so the saving must be specific to this path (analysis/app/src/syspart.cpp:1000-1005; analysis/app/src/syspart.cpp:176-182). Tiny proposed test: one resolved root with one syscall site numbered 39 and no callees; expected syscall stdout is `getpid`, with or without retaining the extra data (analysis/app/src/syspart.cpp:92, analysis/app/src/syspart.cpp:303, analysis/app/src/syspart.cpp:1696-1707). No runtime cost was measured.

<!-- harness:logic:mode-27:end -->

<!-- harness:logic:mode-28:start -->
## Harness logic audit — mode 28

Dispatcher and modules: analysis/app/src/testSyspart.cpp, analysis/app/src/syspart.cpp, analysis/app/src/syspart.h, analysis/app/src/ipcallgraph.cpp, analysis/app/src/syspartUtility.cpp, analysis/app/src/scripts/compute_syscalls_allfuncs.sh

### NSS libraries loaded after root collection can be omitted

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspart.cpp:1565`
- Invariant: Every function in a library parsed for mode 28 must contribute to the all-functions result (analysis/app/src/testSyspart.cpp:113; analysis/app/src/syspart.cpp:1607).
- Mechanism: run16 collects roots and output functions before resolveNss can parse additional libraries. resolveNss roots only identified NSS entry functions, so an otherwise isolated function in a newly parsed library is absent from both the graph scan and the final union (analysis/app/src/syspart.cpp:1565; analysis/app/src/syspart.cpp:1577; analysis/app/src/ipcallgraph.cpp:1919; analysis/app/src/ipcallgraph.cpp:1920; analysis/app/src/ipcallgraph.cpp:1925; analysis/app/src/ipcallgraph.cpp:1938; analysis/app/src/syspart.cpp:284; analysis/app/src/syspart.cpp:1607).
- Reproducer: Source-bounded case: an NSS backend loaded by resolveNss contains an isolated, non-entry function with a unique syscall; that function is not among the earlier roots or the identified entries (analysis/app/src/syspart.cpp:1565; analysis/app/src/ipcallgraph.cpp:1920; analysis/app/src/ipcallgraph.cpp:1925; analysis/app/src/ipcallgraph.cpp:1938).
- Expected: The unique syscall name appears in mode 28 output (analysis/app/src/testSyspart.cpp:132; analysis/app/src/syspart.cpp:1621-1625).
- Actual: For the stated unreferenced function, the traced path neither adds it to allfuncs nor roots it during NSS resolution, so its unique syscall is omitted from the final union (analysis/app/src/syspart.cpp:1565-1577; analysis/app/src/ipcallgraph.cpp:1924-1939; analysis/app/src/syspart.cpp:1605-1617). This is source-supported, not runtime-confirmed.
- Evidence: analysis/app/src/testSyspart.cpp:552-555 — mode 28 calls run16 with syscall output selected; analysis/app/src/syspart.cpp:1565-1577 — run16 collects roots and its allfuncs vector before resolveNss; analysis/app/src/ipcallgraph.cpp:1919-1939 — resolveNss can parse a library afterward and roots only the identified NSS functions; analysis/app/src/ipcallgraph.cpp:1746-1751 — graph generation processes queued roots; analysis/app/src/syspart.cpp:284-291 — direct syscall discovery scans graph nodes; analysis/app/src/syspart.cpp:1605-1617 — the final union visits only the earlier allfuncs vector.
- Assessment: The source supports a conditional omission. Tiny test case: arrange for NSS resolution to load a backend containing an identified NSS entry and an unreferenced function that makes a unique syscall. The function must be absent when run16 first collects functions (analysis/app/src/syspart.cpp:1565-1573). The expected mode 28 output includes that syscall's name because mode 28 is described as covering all functions in the binary and libraries (analysis/app/src/testSyspart.cpp:132; analysis/app/src/syspart.cpp:1621-1625). No runtime output was observed.

### All-functions union needlessly propagates syscall sets

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspart.cpp:1600`
- Invariant: When every graph function is included in the final union, propagating a function's syscalls to callers cannot add a syscall to that union (analysis/app/src/syspart.cpp:1565; analysis/app/src/syspart.cpp:1607; analysis/app/src/syspart.cpp:515; analysis/app/src/syspart.cpp:521).
- Mechanism: run16 roots every initially parsed function, then findDerived4 repeatedly scans graph nodes and constructs call-target sets before run16 unions the rooted functions' bitsets (analysis/app/src/syspart.cpp:1565; analysis/app/src/syspart.cpp:1600; analysis/app/src/syspart.cpp:1607; analysis/app/src/syspart.cpp:501; analysis/app/src/syspart.cpp:506; analysis/app/src/syspart.cpp:515; analysis/app/src/ipcallgraph.cpp:127).
- Reproducer: Bounded case: N initially parsed functions form a caller-before-callee chain, the last has one syscall, and NSS loads no additional module. All N functions are roots; propagation can require N full graph passes, while unioning their direct bitsets already contains the syscall (analysis/app/src/syspart.cpp:1565; analysis/app/src/syspart.cpp:295; analysis/app/src/syspart.cpp:303; analysis/app/src/syspart.cpp:501; analysis/app/src/syspart.cpp:506; analysis/app/src/syspart.cpp:521; analysis/app/src/syspart.cpp:1607).
- Expected: For the three-function case, unioning direct bitsets yields `read` without propagation (analysis/app/src/syspart.cpp:303; analysis/app/src/syspart.cpp:1615; analysis/app/src/syspart.cpp:92).
- Actual: The source first propagates C's bit through B and A, requiring three full passes in the stated visit order; a caller-before-callee chain of N nodes can require N passes and quadratic node visits before the same union (analysis/app/src/syspart.cpp:501; analysis/app/src/syspart.cpp:506; analysis/app/src/syspart.cpp:521; analysis/app/src/syspart.cpp:1600). This is a source-derived bound, not measured runtime output.
- Evidence: analysis/app/src/testSyspart.cpp:552 — mode 28 calls run16 with option 2; analysis/app/src/syspart.cpp:1565 — run16 records initially parsed functions as roots and in allfuncs; analysis/app/src/syspart.cpp:1596 — option 2 finds direct syscalls; analysis/app/src/syspart.cpp:1600 — then calls findDerived4 before unioning allfuncs; analysis/app/src/syspart.cpp:501 — findDerived4 repeats full nodeMap passes until one has no changes; analysis/app/src/syspart.cpp:510 — each node constructs its call-target set; analysis/app/src/ipcallgraph.cpp:127 — that set is built from direct and indirect children; analysis/app/src/syspart.cpp:1615 — the resulting union is printed.
- Assessment: In the bounded case, propagation cannot change the union because every graph function is already in the union (analysis/app/src/syspart.cpp:1565; analysis/app/src/syspart.cpp:1607). A tiny source-level test case is three functions A→B→C, visited in that order, with only C directly invoking syscall 0; with no additional modules or graph nodes, the expected syscall output is `read` (analysis/app/src/syspart.cpp:92; analysis/app/src/syspart.cpp:1619). This is conditional: NSS resolution can parse a new library and add function roots after `allfuncs` is collected, so propagation may matter in that case (analysis/app/src/ipcallgraph.cpp:1914; analysis/app/src/ipcallgraph.cpp:1932).

### Mode 28 builds a call graph for an all-functions syscall union

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/syspart.cpp:1569`
- Invariant: When every parsed function is included in the final union, call edges cannot add a syscall beyond those functions' direct syscall sets, provided NSS adds no module (analysis/app/src/syspart.cpp:1565; analysis/app/src/syspart.cpp:1607; analysis/app/src/syspart.cpp:1615).
- Mechanism: Mode 28 roots every function and builds the graph before scanning syscalls (analysis/app/src/syspart.cpp:1569; analysis/app/src/syspart.cpp:1582; analysis/app/src/syspart.cpp:1598). Root creation runs use-def analysis for each new function, and graph generation scans function instructions for edges and address-taken references (analysis/app/src/ipcallgraph.cpp:161; analysis/app/src/ipcallgraph.cpp:164; analysis/tools/egalito/src/analysis/dataflow.cpp:13; analysis/tools/egalito/src/analysis/dataflow.cpp:21; analysis/app/src/ipcallgraph.cpp:881; analysis/app/src/ipcallgraph.cpp:1352).
- Reproducer: Bounded source case: N initially parsed functions have no calls or address references, and NSS loads no module. Root creation performs N use-def analyses and graph generation scans their instructions, although the final union needs only their direct syscall sets (analysis/app/src/syspart.cpp:1565; analysis/app/src/ipcallgraph.cpp:155; analysis/app/src/ipcallgraph.cpp:164; analysis/app/src/ipcallgraph.cpp:881; analysis/app/src/syspart.cpp:1607).
- Expected: For the stated two-function test case, stdout: `getpid\n` (analysis/app/src/syspart.cpp:92; analysis/app/src/syspart.cpp:1622).
- Actual: The source performs root use-def analysis and graph generation before computing that same union (analysis/app/src/ipcallgraph.cpp:161; analysis/tools/egalito/src/analysis/dataflow.cpp:21; analysis/app/src/syspart.cpp:1579; analysis/app/src/syspart.cpp:1598). This is a source-supported cost finding, not an observed runtime result.
- Evidence: analysis/app/src/testSyspart.cpp:552 — mode 28 calls run16 with option 2; analysis/app/src/syspart.cpp:1565 — run16 adds every initially parsed function as a graph root and to allfuncs; analysis/app/src/ipcallgraph.cpp:155 — each new root calls getWorkingSet; analysis/tools/egalito/src/analysis/dataflow.cpp:21 — getWorkingSet runs use-def analysis when absent; analysis/app/src/syspart.cpp:1579 — run16 generates the graph before scanning syscalls; analysis/app/src/ipcallgraph.cpp:1766 — generation scans roots for direct edges and address-taken references; analysis/app/src/syspart.cpp:1598 — direct syscall scanning follows graph generation; analysis/app/src/syspart.cpp:1600 — derived syscalls propagate over graph edges; analysis/app/src/syspart.cpp:1607 — the result unions every initially parsed function. With no added module or referenced function, propagation cannot add a syscall outside that union (analysis/app/src/syspart.cpp:496; analysis/app/src/syspart.cpp:1565).
- Assessment: A tiny test case is two parsed functions with no calls or address references: one has direct syscall 39 and the other has none; NSS loads no module. Expected stdout is `getpid\n`, since 39 maps to `getpid` (analysis/app/src/syspart.cpp:92) and mode 28 prints the combined syscall names (analysis/app/src/syspart.cpp:1607; analysis/app/src/syspart.cpp:1622). The source supports an avoidable cost in this case, but no runtime output was captured.

<!-- harness:logic:mode-28:end -->

<!-- harness:logic:mode-100:start -->
## Harness logic audit — mode 100

Dispatcher and modules: analysis/app/src/testSyspart.cpp, analysis/app/src/syspart.cpp, analysis/app/src/ipcallgraph.cpp, analysis/app/src/syspartUtility.cpp, analysis/app/src/syspartUtility.h

### A cached first query suppresses the second argument report

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspartUtility.cpp:107`
- Invariant: Both mode 100 queries should produce their own argument report (analysis/app/src/syspart.cpp:1526; analysis/app/src/syspart.cpp:1532).
- Mechanism: Mode 100 reuses one utility for both queries. The first result is cached; a matching second query returns from the cache before reaching the code that prints callsites and values (analysis/app/src/syspart.cpp:1527; analysis/app/src/syspart.cpp:1530; analysis/app/src/syspartUtility.cpp:107; analysis/app/src/syspartUtility.cpp:115; analysis/app/src/syspartUtility.cpp:230; analysis/app/src/syspartUtility.cpp:264).
- Reproducer: Source-bounded case: request -a 100,sink,7,sink,7 with a direct caller of sink (analysis/app/src/testSyspart.cpp:573; analysis/app/src/testSyspart.cpp:576; analysis/app/src/syspart.cpp:1530; analysis/app/src/syspart.cpp:1534). No workload was run.
- Expected: For the proposed direct-call test, both `ARGUMENTRES-BEGIN-FUNC1` and `ARGUMENTRES-BEGIN-FUNC2` are followed by a `FUNC sink CALLINGFN main CALLINGADDR ...` report and `END` (analysis/app/src/syspart.cpp:1526; analysis/app/src/syspart.cpp:1532; analysis/app/src/syspartUtility.cpp:230; analysis/app/src/syspartUtility.cpp:291).
- Actual: The source predicts that the second marker has no second callsite, value, or `END` report, although the second result set receives cached values (analysis/app/src/syspart.cpp:1532; analysis/app/src/syspartUtility.cpp:107; analysis/app/src/syspartUtility.cpp:109; analysis/app/src/syspartUtility.cpp:111).
- Evidence: analysis/app/src/syspart.cpp:1497 — both function names must resolve or the runner returns; analysis/app/src/syspart.cpp:1527 — one utility is constructed for both queries; analysis/app/src/syspartUtility.cpp:1448 — initialization adds use-def data and does not clear the cache; analysis/app/src/syspartUtility.h:66 — cache equality uses function name, address, and register, so identical queries match; analysis/app/src/syspartUtility.cpp:115 — the first cache miss reaches the reporting helper; analysis/app/src/syspartUtility.cpp:117 — its results are cached; analysis/app/src/syspart.cpp:1532 — the second marker is printed; analysis/app/src/syspartUtility.cpp:107 — the matching second query takes the cache branch; analysis/app/src/syspartUtility.cpp:109 — cached values enter its result set; analysis/app/src/syspartUtility.cpp:111 — it returns before the callsite and value printing at analysis/app/src/syspartUtility.cpp:230 and analysis/app/src/syspartUtility.cpp:264.
- Assessment: A tiny source-bounded test is `volatile int out; __attribute__((noinline)) void sink(int x) { out = x; } int main(void) { sink(42); return out; }`, queried as `-a 100,sink,7,sink,7`; mode 100 parses both names and registers and passes them to the same runner (analysis/app/src/testSyspart.cpp:557; analysis/app/src/testSyspart.cpp:573; analysis/app/src/testSyspart.cpp:585). With a direct caller in the call graph, expected output has a `FUNC sink CALLINGFN main CALLINGADDR ...` report and `END` after each query marker (analysis/app/src/syspart.cpp:1526; analysis/app/src/syspart.cpp:1532; analysis/app/src/syspartUtility.cpp:225; analysis/app/src/syspartUtility.cpp:230; analysis/app/src/syspartUtility.cpp:291). This is a source-supported prediction; no workload output was captured.

### A target with no caller edges produces no argument result

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspartUtility.cpp:294`
- Invariant: When a target has no usable caller, its unknown argument result should be visible to the mode 100 consumer (analysis/app/src/syspartUtility.cpp:294; analysis/app/src/syspart.cpp:1530).
- Mechanism: The helper adds an unknown result when no callsite was found, but prints results only inside the matching-callsite loop. Mode 100 never prints the returned result set (analysis/app/src/syspartUtility.cpp:225; analysis/app/src/syspartUtility.cpp:259; analysis/app/src/syspartUtility.cpp:294; analysis/app/src/syspart.cpp:1529; analysis/app/src/syspart.cpp:1533).
- Reproducer: Source-bounded case: name an existing function with no parent edges as either target; its parent loop has no matching callsite (analysis/app/src/syspartUtility.cpp:188; analysis/app/src/syspartUtility.cpp:294). No workload was run.
- Expected: The affected query section contains a `TYPE 0 ... DESC unknown FUNC root ... UNKNOWN` line (analysis/app/src/syspartUtility.cpp:264; analysis/app/src/syspartUtility.cpp:267).
- Actual: The source predicts a query marker without an argument-result line: unknown enters the result set after the only print block has been skipped, and the caller does not print that set (analysis/app/src/syspartUtility.cpp:259; analysis/app/src/syspartUtility.cpp:298; analysis/app/src/syspart.cpp:1526; analysis/app/src/syspart.cpp:1530). Runtime output was not observed.
- Evidence: analysis/app/src/testSyspart.cpp:577 — mode 100 calls argument resolution; analysis/app/src/syspart.cpp:1526 — prints the first query marker; analysis/app/src/syspart.cpp:1530 — passes a result set to the utility; analysis/app/src/syspartUtility.cpp:115 — the utility calls its helper; analysis/app/src/syspartUtility.cpp:188 — the helper obtains parent edges; analysis/app/src/syspartUtility.cpp:191 — an empty parent set skips the loop; analysis/app/src/syspartUtility.cpp:259 — result printing is inside that loop and a matching-callsite branch; analysis/app/src/syspartUtility.cpp:298 — no matched callsite causes insertion of unknown; analysis/app/src/syspart.cpp:1534 — mode 100 does not print the returned set.
- Assessment: A tiny source-bounded test is a fixture whose root function has no incoming callgraph edges. Query it with `-a 100,root,7,root,6`, assuming `root` is found and is absent from the global AT list (analysis/app/src/testSyspart.cpp:557; analysis/app/src/syspart.cpp:1497; analysis/app/src/syspartUtility.cpp:159). Each query should show a `TYPE 0 ... DESC unknown FUNC root ... UNKNOWN` result after its marker (analysis/app/src/syspartUtility.cpp:137; analysis/app/src/syspartUtility.cpp:264; analysis/app/src/syspartUtility.cpp:267). No binary was run.

### Results from same-named callers in different modules collapse into one

- Status: **supported**
- Kind: logic
- Location: `analysis/app/src/syspartUtility.h:23`
- Invariant: Mode 100's argument report should retain the module of each traced caller (analysis/app/src/syspart.cpp:1526; analysis/app/src/syspartUtility.cpp:265).
- Mechanism: A traced constant records its caller function, but UDResult equality and hashing identify that function only by name. The result set can therefore merge equal values from distinct same-named callers, leaving one module to print (analysis/app/src/syspartUtility.cpp:744; analysis/app/src/syspartUtility.h:23-28; analysis/app/src/syspartUtility.h:34-45; analysis/app/src/syspartUtility.cpp:241; analysis/app/src/syspartUtility.cpp:265).
- Reproducer: Source-bounded case: functions named helper in two modules each directly call the selected target with the same constant in register 7. Graph edges retain the distinct Function pointers; both traces create equal-valued results with the same function name (analysis/app/src/ipcallgraph.cpp:224-247; analysis/app/src/syspartUtility.cpp:223-241; analysis/app/src/syspartUtility.cpp:740-744). No workload was run.
- Expected: Both caller modules appear as origins for value 0 (analysis/app/src/syspartUtility.cpp:263-277).
- Actual: The source predicts one surviving origin and therefore one missing module in the value report (analysis/app/src/syspartUtility.h:23-45; analysis/app/src/syspartUtility.cpp:239-241,263-277).
- Evidence: analysis/app/src/testSyspart.cpp:557-584 — mode 100 calls argument resolution; analysis/app/src/syspart.cpp:1525-1534 — it creates result sets and traces each selected function; analysis/app/src/ipcallgraph.cpp:224-247 — graph nodes are keyed by Function pointers; analysis/app/src/ipcallgraph.cpp:121-124 — parent entries retain node pointers; analysis/app/src/syspartUtility.cpp:187-241 — the target's distinct parents are traversed and each caller's register definition is inserted into one collectedResults set; analysis/app/src/syspartUtility.cpp:736-744 — a constant result carries its caller Function pointer; analysis/app/src/syspartUtility.h:23-45 — equality and hashing use the caller's name instead of its identity or module; analysis/app/src/syspartUtility.cpp:263-277 — reporting prints the module from the surviving result.
- Assessment: Tiny test: put a function named helper in each of two modules, A and B. Give each a distinct call site that passes constant 0 in register 7 to the selected target. The expected value report contains both `TYPE 1 ADDRESS 0 DESC 0x0 FUNC helper MODULE A SYM NULL` and the corresponding line for B (analysis/app/src/syspartUtility.cpp:263-277). The source predicts only one of those origins: equal-valued results from the two callers compare and hash by function name, and insertion into the result set merges them (analysis/app/src/syspartUtility.h:23-45; analysis/app/src/syspartUtility.cpp:239-241). Which module survives is unspecified. No runtime output was captured.

### Each uncached argument trace copies its entire parent-edge map

- Status: **supported**
- Kind: performance
- Location: `analysis/app/src/ipcallgraph.h:187`
- Invariant: Inspecting a target's parent edges need not allocate a second map of those edges (analysis/app/src/ipcallgraph.h:187-190; analysis/app/src/syspartUtility.cpp:191).
- Mechanism: getParentWithType returns parentType by value. Every uncached helper call copies the map before iterating it, including recursive caller queries initiated while resolving mode 100's two targets (analysis/app/src/ipcallgraph.h:187-190; analysis/app/src/syspartUtility.cpp:188-191; analysis/app/src/syspartUtility.cpp:247-249; analysis/app/src/syspart.cpp:1527-1534).
- Reproducer: Bounded cost: if Q uncached traces each reach a node with P parent records, the getter copies Θ(QP) map entries and needs Θ(P) temporary entries per call, beyond traversing the original records. Cache hits bypass the helper (analysis/app/src/syspartUtility.cpp:104-115; analysis/app/src/syspartUtility.cpp:188-191; analysis/app/src/ipcallgraph.h:187-190). No timing or memory use was measured.
- Expected: Eligible traces could iterate the stored parent-edge map without copying it (analysis/app/src/ipcallgraph.h:187-190; analysis/app/src/syspartUtility.cpp:188-191).
- Actual: The source requires a separate map value for each eligible lookup, even before unresolved indirect edges are skipped (analysis/app/src/ipcallgraph.h:187-190; analysis/app/src/syspartUtility.cpp:188-199).
- Evidence: analysis/app/src/testSyspart.cpp:557-585 — mode 100 dispatches two targets; analysis/app/src/syspart.cpp:1527-1534 — both use one utility instance; analysis/app/src/syspartUtility.cpp:104-115 — cache misses enter the helper; analysis/app/src/syspartUtility.cpp:159-188 — earlier guards precede the getter; analysis/app/src/ipcallgraph.cpp:121-125 — parent edges populate parentType; analysis/app/src/ipcallgraph.h:187-190 — getter returns that map by value; analysis/app/src/syspartUtility.cpp:188-191 — helper stores the returned map and iterates it; analysis/app/src/syspartUtility.cpp:245-249 — caller tracing can recurse.
- Assessment: The cost applies when a trace reaches the parent-edge lookup: the recursion limit, cache hit, global address-taken check, visited check, and missing-node check can return earlier (analysis/app/src/syspartUtility.cpp:95-115; analysis/app/src/syspartUtility.cpp:125-185). For each eligible lookup with P parent records, returning the stored map by value copies Θ(P) entries before iteration; Q such lookups copy Θ(QP) entries when each has P records (analysis/app/src/ipcallgraph.h:187-190; analysis/app/src/syspartUtility.cpp:188-191). Tiny proposed test: insert two parent edges into one node, obtain a map with getParentWithType(), clear that returned map, then print its size and the size from a second getter call; expected output is `0 2` (analysis/app/src/ipcallgraph.cpp:121-125; analysis/app/src/ipcallgraph.h:187-190). No runtime output was captured.

<!-- harness:logic:mode-100:end -->

## Runtime-confirmed: VFA can duplicate indirect FCG edges

- Status: **runtime-confirmed**
- Kind: logic/performance
- Location: `analysis/app/src/ipcallgraph.cpp:1190`, `analysis/app/src/syspartUtility.cpp:1375`, `analysis/app/src/ipcallgraph.cpp:34-45`
- Reproducer: Build `test/fcg_repro_02/build.sh 4` and run `analysis/app/syspart -p test/fcg_repro_02/build/branches_4 -s /absolute/path/to/test/fcg_repro_02/build/roots.txt -i -a 23`.
- Observed: The callsite in `main` at `0x1196` printed eight `INDIRECT_RESOLVED` records: two identical records for each of `target_0` through `target_3`. The process exited successfully.
- Mechanism: During address-taken forward data flow, `handleIcallOrIjump` calls `addEdge` when a target flows into an indirect call. Later, VFA calls `insertCallTarget` for each resolved target at the same site. Both paths append to the callsite vector, and `insertCallTarget` does not check whether that target is already present. The printer emits every vector element.
- Impact: Duplicate edges inflate FCG output and consume additional target-list storage. This fixture doubles the four distinct indirect edges at the callsite; the effect on larger workloads has not been measured.
- Expected: One `INDIRECT_RESOLVED` record per distinct callsite-target pair.
