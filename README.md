# SysPartCode


This repository contains the source code of "SYSPART: Automated Temporal System Call Filtering for Binaries", published in ACM Conference on Computer and Communications Security (CCS) 2023. (https://dl.acm.org/doi/10.1145/3576915.3623207). The purpose of this repository to run and explore the different functionalities offered by the tool. If you are looking to reproduce the results of the paper, please refer to this repository https://github.com/vidyalakshmir/SysPartArtifact.

We update this repository to add more features and fix bugs. In case of any queries or issues, please contact vrajagop@stevens.edu.

**Basic Requirements & Limitations**
- **Linux Binaries:** Supports *ELF on x86-64* architecture.
- **ELF Binary Testing:** Effective with symbols; results from stripped binaries may be overapproximated.
- **Compatibility:** Tested on *Ubuntu 18.04*; updates for newer Linux versions are in progress (✨ Stay Tuned).

**Capabilities of the Tool**
- **Capabilities on Any Application:**
  - Create callgraphs of application binaries and their dependent libraries.
  - Get system calls invoked from different functions.
  - Determine system calls reachable from any function or any part of code (instruction).
  - Produce targets of indirect calls.
  - Print address-taken functions.
  - Resolve the names of libraries and functions loaded using dlopen() and dlsym().
  - Resolve arguments passed to functions (e.g., execve()).
  - Print non-returning functions and loops.
  - Enforce system call filters at a program point.

- **Capabilities on Server Applications**
  - Determine where the initialization phase of the server ends and the serving phase begins.
  - Identify system calls reachable from the serving phase of the server.

## 🔧 Setup Instructions

To set up the project, please refer to the instructions in the [setup guide](./docs/setup.md).

## 🔍 Using the tool

For usage, please refer to the usage guide(.docs/usage.md)

### Generate Callgraph
Uses static analysis to generate the callgraph of the application and its dependent libraries.

```bash
./syspart -p $BINARY -s $MAIN -a 1
```
Where `$BINARY` is the name of the binary and `$MAIN` is the name or address of the function from which the callgraph is computed (usually `main()`). The address should be provided in hexadecimal and should start with `0x`.

By default, all indirect calls target the AT functions. The `-i` option performs the FCG refining of SysPart (prune AT list and resolve indirect calls).
For more options, refer to:

```bash
./syspart --help
```

### Dynamic Library Profiling
Determines the names of libraries and functions loaded using `dlopen()` and `dlsym()` through a combination of static and dynamic analyses.

#### Determine the `dlopen` and `dlsym` Function Names
In the tested environment (Ubuntu 18.04 and libc-2.27), the `dlopen` and `dlsym` functions are in `libdl.so` with names `dlopen@@GLIBC_2.2.5` and `dlsym`. Please verify and update `analysis/app/src/dlanalysis/dlopen.txt` and `analysis/app/src/dlanalysis/dlsym.txt` with the correct names in your environment.

#### Static Analysis
```bash
cd analysis/app/src/dlanalysis/static
./run_dlanalysis.sh $BINARY $OUTPUT_DIR
```
Where `$BINARY` is the name of the binary and `$OUTPUT_DIR` is the output directory for the files. This script uses value-flow analysis (VFA) and stores the results in `dlopen_static.txt` and `dlsym_static.txt`. Each line contains the function invoking `dlopen`/`dlsym`, the callsite address, and the passed argument.

If values flowing into `dlsym()` call sites are resolved, but not those to `dlopen()`, the system searches for libraries exporting the resolved symbols. All matching libraries are potential `dlopen()` inputs, listed in `libraries_matching_syms.txt` in the output folder. It's recommended to add application-specific folders to the file `analysis/app/src/dlanalysis/pathlist.txt` as dependent libraries might reside in those paths.

#### Dynamic Analysis
For verification, dynamic analysis captures the runtime arguments to `dlopen` and `dlsym`.

```bash
cd analysis/app/src/dlanalysis/dynamic/fninterposition
make
LD_PRELOAD=./libmydl.so $APP_RUN_COMMAND
```
If the application requires root permissions, use:

```bash
sudo LD_PRELOAD=./libmydl.so $APP_RUN_COMMAND
```

Results are saved in `output/fninterp_$pid.txt`, where `$pid` is the process ID. To process these results:

```bash
./process_output.sh output/ $OUTPUT_FOLDER
```

This produces `fninter_dlopen.txt` and `fninterp_dlsym.txt` in `$OUTPUT_FOLDER`, containing the arguments to `dlopen()` and `dlsym()`, respectively. It also moves `fninterp_$pid.txt` files from `output/` to `$OUTPUT_FOLDER`.

### Serving Phase Detection

### System Calls of Main() and Mainloop

### System Call Enforcement