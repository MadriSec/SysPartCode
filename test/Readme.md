# SysPart Test Suite (`test`)

Small end-to-end integration tests that build sample x86-64 C++ binaries and verify `analysis/app/syspart` callgraph construction, indirect-call handling, and static `dlopen()`/`dlsym()` argument resolution.

> **Prerequisite:** `analysis/app/syspart` must be built first (via `./build.sh` or `./build_upgraded_egalito.sh` from the repository root), and `g++` must be available on Linux x86-64.

## Directory Layout

| Path | Role |
| --- | --- |
| `Makefile` | Builds `hello/libhello.so`, `hello/main`, `helloIndirect/main`, `helloDynamic/main`, and invokes `run_all_tests.sh`. |
| `run_all_tests.sh` | Discovers all executable `test.sh` scripts under `test/`, runs each, counts lines containing `"Test passed"`, and exits `0` iff all pass. |
| `hello/` | Direct shared-library call test (`main.cpp` calls `extern "C" void printHello()` in `libhello.so`, which writes to `std::cout`). |
| `helloIndirect/` | Function-pointer indirect call test (`main.cpp` assigns `void (*funcPtr)() = printHello; funcPtr();`). |
| `helloDynamic/` | Dynamic loading test (`main.cpp` calls `dlopen("../hello/libhello.so", RTLD_LAZY)` and `dlsym(handle, "printHello")`). |

## Running Tests

```bash
cd test
make              # builds all test binaries and runs run_all_tests.sh
make clean        # removes built binaries, .so files, and generated .txt outputs
```

To re-run tests without rebuilding:

```bash
cd test
./run_all_tests.sh
```

## What Each Test Verifies

| Test | Command Under Test | Assertions |
| --- | --- | --- |
| `hello/test.sh` | `LD_LIBRARY_PATH=hello ../analysis/app/syspart -p hello/main -s main -i -a 1` | Confirms `DIRECT` edge from executable to `printHello` in `module-libhello.so` **and** `DIRECT` edge from `printHello` in `libhello.so` to `module-libstdc++.so.6`. |
| `helloIndirect/test.sh` | `LD_LIBRARY_PATH=hello ../analysis/app/syspart -p helloIndirect/main -s main -i -a 1` | Confirms there is **no** `DIRECT` edge from executable to `printHello` in `module-libhello.so` (call stays indirect), while `libhello.so` -> `module-libstdc++.so.6` direct linkage is still present. |
| `helloDynamic/test.sh` | `../analysis/app/src/dlanalysis/static/run_dlanalysis.sh $PWD/helloDynamic/main $PWD/helloDynamic` | Confirms `helloDynamic/dlsym_static.txt` contains `printHello` and `helloDynamic/dlopen_static.txt` contains `libhello.so`. |

## Known Quirks & Gotchas

1. **Run from `test/`:** Each `test.sh` uses relative paths (`hello/main`, `../analysis/app/syspart`), so `run_all_tests.sh` and individual `test.sh` scripts must be invoked with `test/` as the current working directory.
2. **Cached output in `helloDynamic/test.sh`:** `helloDynamic/test.sh` skips running `run_dlanalysis.sh` if `helloDynamic/dlsym_static.txt` already exists. Run `rm -f helloDynamic/*.txt` (or `make clean`) before re-testing changes to `syspart` or `dlanalysis`.
3. **Side effect of `helloDynamic/test.sh`:** `run_dlanalysis.sh` invokes `USE_LOADER=0 make` inside `analysis/app/`, which will rebuild `syspart` if sources changed.
4. **Circular Makefile dependency note:** In `test/Makefile`, `all` depends on `run_tests` and `run_tests` depends on `all`; GNU Make drops the circular prerequisite on `all` with a warning and still executes the build + tests.
5. **Leftover `.out` files:** `make clean` removes `*.txt`, `*.so`, `*.o`, and `main`, but does not remove `hello/hello.out` or `helloIndirect/hello.out` (they are git-ignored by `*.out`).
