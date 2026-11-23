# External Tools (`analysis/tools`)

This directory houses the two third-party binary instrumentation/analysis frameworks that SysPart depends on.

## Contents

| Item | Type | Role in SysPart |
| --- | --- | --- |
| `egalito/` | Git submodule (`https://github.com/MadriSec/egalito.git`, branch `master`) | Static ELF disassembler, IR (`Program`/`Module`/`Function`/`Block`/`Instruction`), CFG/Use-Def/DataFlow analysis, `FindSyscalls` pass, PLT resolution (`ResolvePLTPass`/`CollapsePLTPass`), and ELF binary rewriting (`SyspartPass` used by `enforcement/`). |
| `pin-3.11-97998-g7ecce2dac-gcc-linux.tar.gz` | Tarball archive | Intel Pin 3.11 dynamic binary instrumentation kit used to compile and execute the serving-phase loop profiler ([`timeofouterloop.cpp`](../app/src/pintool/timeofouterloop.cpp)). |

## Egalito Setup & Build Variants

`egalito/` is an unpopulated directory until submodules are initialized:

```bash
git submodule update --init --recursive
```

SysPart supports two Egalito branches depending on the host OS (see root [build.sh](../../build.sh) and [build_upgraded_egalito.sh](../../build_upgraded_egalito.sh)):

1. **Legacy Ubuntu 18.04 (`build.sh`):**
   - Branch: `syspart-updated`
   - Environment: `USE_LOADER=0`
   - Build: `make -j 8`
2. **Modern Ubuntu 22.04/24.04 & Debian 12/13 (`build_upgraded_egalito.sh`):**
   - Branch: `master`
   - Sub-submodules initialized: `dep/capstone`, `dep/distorm3`, `dep/keystone`
   - Build: `make -j 8 src`

### How Downstream Makefiles Link Against Egalito

Both [analysis/app/Makefile](../app/Makefile) and [enforcement/Makefile](../../enforcement/Makefile):
- Include `analysis/tools/egalito/env.mk` (which defines `BUILDDIR`, `SHORT_LINK`, etc.).
- Add `-I .../egalito/src/` and link `-legalito` with `-Wl,-rpath` pointing to `egalito/src/$(BUILDDIR)` and `egalito/dep/capstone/install/lib`.
- Copy `libegalito.so` into their own `$(BUILDDIR)`.
- Invoke `rebuild-src` on `egalito/src` automatically during `make`.

## Intel Pin Setup

Pin is only needed if you are running dynamic serving-phase loop profiling ([analysis/app/src/pintool/README.md](../app/src/pintool/README.md)):

```bash
cd analysis/tools
tar -xvf pin-3.11-97998-g7ecce2dac-gcc-linux.tar.gz
export PIN_ROOT="$(pwd)/pin-3.11-97998-g7ecce2dac-gcc-linux"
```

Then build the pintool from `analysis/app/src/pintool/` with `make PIN_ROOT=$PIN_ROOT`.
