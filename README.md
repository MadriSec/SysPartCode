# SysPart

SysPart is the implementation of **"SYSPART: Automated Temporal System Call Filtering for Binaries,"** published at the ACM Conference on Computer and Communications Security (CCS) 2023. Read the paper on the [ACM Digital Library](https://dl.acm.org/doi/10.1145/3576915.3623207).

This repository is intended for running and exploring the tool's functionality. To reproduce the results from the paper, use the [SysPartArtifact repository](https://github.com/vidyalakshmir/SysPartArtifact) instead.

The repository is updated with new features and bug fixes. For questions or issues, contact vrajagop@stevens.edu.

## What's New

### Scalable analysis

The latest version includes improved scalability for larger binaries, along with scripts that simplify and accelerate the analysis process. See [Compute system calls](#compute-system-calls) for the main workflow.

### Support for newer operating systems

SysPart has been upgraded from its original Ubuntu 18.04 environment. It has been successfully built on:

- Debian 13 (trixie)
- Debian 12 (bookworm)
- Ubuntu 22.04 LTS
- Ubuntu 24.04 LTS

See [Build the tool](#build-the-tool) for the appropriate build command.

## Requirements

- Linux ELF binaries running on the x86-64 architecture.
- ELF binaries with symbols are recommended for both applications and libraries. Stripped binaries are supported, but results such as the callgraph may be overapproximated.
- The tool was initially tested on Ubuntu 18.04 and has since been upgraded for newer Ubuntu and Debian versions.

## Capabilities

### Applications

- Create a callgraph for an application and its dependent libraries.
- Find system calls invoked by different functions.
- Find system calls reachable from any function or instruction.
- Produce targets of indirect calls.
- Print address-taken functions, noreturn functions, and loops.
- Resolve libraries and functions loaded with `dlopen()` and `dlsym()`.
- Resolve arguments passed to functions such as `execve()`.
- Enforce a system call filter at a program point.

### Server applications

- Determine where server initialization ends and the serving phase begins.
- Determine the system calls reachable from the serving phase.

## Setup

### Clone the repository

This repository uses Git submodules for benchmarking. You must have SSH access configured for [GitHub](https://github.com). See GitHub's [SSH key documentation](https://docs.github.com/en/authentication/connecting-to-github/using-ssh/adding-a-new-ssh-key-to-your-github-account) if needed.

Clone the repository and its submodules with:

```bash
git clone https://github.com/MadriSec/SysPartCode.git
cd SysPartCode
git checkout syspart-wogramma
git submodule update --init --recursive
```

### Install dependencies

```bash
sudo apt-get install make g++ libreadline-dev gdb lsb-release unzip libc6-dbg libstdc++6-7-dbg
sudo apt install libunwind-dev python3
```

### Build the tool

For the original environment, up to Ubuntu 18.04:

```bash
./build.sh
```

For newer Ubuntu and Debian versions:

```bash
./build_upgraded_egalito.sh
```

## Using SysPart

The commands below assume that the tool has been built successfully.

### Compute system calls

To generate a callgraph and compute the system calls reachable from a list of start functions:

```bash
cd analysis/app
src/scripts/compute_syscalls.sh $BINARY $OUT $STARTFILE --log
```

Where:

- `$BINARY` is the ELF binary to analyze.
- `$OUT` is the output directory.
- `$STARTFILE` contains one or more start functions.
- `--log` is optional and records paths from the start functions to system calls in `$OUT/logfile.txt`.

The script writes the callgraph and reachable system calls to separate files in the output directory. Run `src/scripts/compute_syscalls.sh --help` for details about the script and its output files.

This workflow does not produce results for dynamically loaded libraries. See [Dynamic library profiling](#dynamic-library-profiling).

### Generate a callgraph

Use static analysis to generate the callgraph of an application and its dependent libraries:

```bash
./syspart -p $BINARY -s $MAIN -a 1
```

Here, `$BINARY` is the binary name, and `$MAIN` is the name or address of the function from which the callgraph is computed, usually `main()`. Addresses must be hexadecimal values beginning with `0x`.

By default, indirect calls target address-taken functions. The `-i` option performs SysPart's FCG refinement by pruning the address-taken list and resolving indirect calls. Run `./syspart --help` for more options.

### Analysis modes

The `-a` option selects the analysis to run. Its value is a mode number followed by a comma-separated argument list:

```bash
./syspart -p $BINARY -s $START_FUNCTION -a <mode>[,<arg1>,<arg2>,...]
```

The start function supplied with `-s` is normally `main`. For modes that accept a function address, use a hexadecimal address beginning with `0x`. Use `*` where a mode explicitly accepts all functions.

| Mode | Description | Arguments |
| ---: | --- | --- |
| 1 | Print the callgraph. | None |
| 2 | Print system calls filtered at a partition point. | `partition_point_address,func_name` |
| 3 | Print the difference between system calls accessible from the start function and from a specific function. | `func_name` |
| 4 | Print the global address-taken-function list. | None |
| 5 | Print AICT (Average Indirect Call Target). | None |
| 6 | Print possible values passed as arguments to a function. | `func_name,register_id` |
| 7 | Print system call information for one function or all functions. | `func_name` or `*` |
| 8 | Print system calls after including specified libraries. | `no_of_libs,lib1,lib2,...,libn` |
| 9 | Print a callgraph containing only indirect edges. | None |
| 10 | Report whether an indirect call exists on a path, or trace paths back to `main`. | List of functions |
| 11 | Check whether `func2` is reachable from an instruction in `func1`. | `addr,func1,func2` |
| 12 | Find system calls after including modules of `dlsym()` functions. | Output file from dlsym analysis |
| 13 | Print the number of noreturn functions with and without SysPart's noreturn analysis. | None |
| 14 | Print system calls directly invoked from address-taken functions. | None |
| 15 | Check whether a path exists between two functions. | `startfunc,endfunc` |
| 16 | Print direct system calls of a module. | `modulename` |
| 17 | Print the callgraph of a module. | `modulename` |
| 18 | Print the number of instructions in a function. | `functionname` |
| 19 | Report whether `fork()` and `pthread()` functions are invoked. | None |
| 20 | Print all functions from all modules. | None |
| 21 | Print arguments passed to `dlopen()`. | None |
| 22 | Print arguments passed to `dlsym()`. | None |
| 23 | Print the callgraph from start functions listed in a file passed to `-s`. | Start-function file |
| 24 | Print direct system calls. | None |
| 25 | Print all functions with their addresses and modules. | None |
| 26 | Print the disassembly of a function. | `functionname` |
| 27 | Print system calls reachable from start functions listed in a file passed to `-s`. | Start-function file |
| 28 | Print system calls reachable from all functions in the binary and its libraries. | None |

#### Common analysis flags

| Option | Purpose |
| --- | --- |
| `-p PROG` | Binary program to analyze. |
| `-s STARTFN` | Root function name or address. An address must begin with `0x`. For modes 23 and 27, this is a file containing start functions. |
| `-i` | Enable indirect-call-target analysis and FCG refinement. |
| `-g` | Construct an FCG with direct edges only. Indirect edges are included by default. |
| `-l` | Enable logging. |
| `-t PATH` | Enable TypeArmor using the specified TypeArmor output file. |
| `-h`, `--help` | Print the complete command-line help. |

For the authoritative option list and usage syntax, run `./syspart --help` from `analysis/app`.

### Dynamic library profiling

SysPart combines static and dynamic analysis to determine the names of libraries and functions loaded with `dlopen()` and `dlsym()`.

#### Configure `dlopen()` and `dlsym()` names

In the tested Ubuntu 18.04 and libc-2.27 environment, the functions are in `libdl.so` and are named `dlopen@@GLIBC_2.2.5` and `dlsym`. Check the names in your environment and update:

- `analysis/app/src/dlanalysis/dlopen.txt` with the `dlopen` function name.
- `analysis/app/src/dlanalysis/dlsym.txt` with the `dlsym` function name.

#### Static analysis

```bash
cd analysis/app/src/dlanalysis/static
./run_dlanalysis.sh $BINARY $OUTPUT_DIR
```

`$BINARY` is the binary name and `$OUTPUT_DIR` is the directory where results are stored.

This script uses value-flow analysis (VFA). It writes `dlopen_static.txt` and `dlsym_static.txt`. Each line contains the function that invokes `dlopen()` or `dlsym()`, the callsite address, and the resolved argument. For `dlopen()`, the first argument is the shared library name. For `dlsym()`, the second argument is the requested function name.

When values flowing into `dlsym()` are resolved but values flowing into `dlopen()` are not, heuristics search for system libraries exporting the resolved symbols. Potential matching libraries are written to `libraries_matching_syms.txt` in the output directory. By default, the search uses the paths listed in `analysis/app/src/dlanalysis/pathlist.txt`; add application-specific library directories to that file when needed.

#### Dynamic analysis

Dynamic analysis verifies the `dlopen()` and `dlsym()` arguments observed at runtime:

```bash
cd analysis/app/src/dlanalysis/dynamic/fninterposition
make
LD_PRELOAD=./libmydl.so $APP_RUN_COMMAND
```

`$APP_RUN_COMMAND` is the command used to run the application. If root permissions are required, use:

```bash
sudo LD_PRELOAD=./libmydl.so $APP_RUN_COMMAND
```

The run writes `output/fninterp_$pid.txt`, where `$pid` is the process ID. Process the results with:

```bash
./process_output.sh output/ $OUTPUT_FOLDER
```

This creates `fninter_dlopen.txt` and `fninterp_dlsym.txt` in `$OUTPUT_FOLDER`, containing the arguments passed to `dlopen()` and `dlsym()`. It also moves `fninterp_$pid.txt` files from `output/` to `$OUTPUT_FOLDER`.

### Serving-phase detection

SysPart determines a server's serving phase using static and dynamic analysis. Let `$OUTDIR` be the directory where the server's outputs are stored:

```bash
mkdir $OUTDIR/pin
```

#### Find all loops statically

Egalito statically analyzes the server binary and its dependent libraries. It disassembles the binary and extracts its control-flow graph (CFG). For each function, loops are identified with a worklist algorithm based on dominance.

```bash
cd analysis/app
./loops $BINARY > $OUTDIR/loops_output.out
grep -v '^FUNC' $OUTDIR/loops_output.out > $OUTDIR/loops.out
```

#### Find the dominant loop dynamically

Intel Pin determines the dominant loop: the top-level loop where the server spends the most time. The pintool uses the statically collected loop start and exit-node addresses to measure how much time each top-level loop encompasses for every process and thread.

Let `$COMMAND_TO_RUN_SERVER` be the command used to run the server. For example, a BIND server can be started with:

```bash
$BIND_BINARY -f -u bind
```

Set up the Pin environment, where `$base_dir` is the repository location:

```bash
cd analysis/tools
tar -xvf pin-3.11-97998-g7ecce2dac-gcc-linux.tar.gz
export PIN_ROOT="$base_dir/analysis/tools/pin-3.11-97998-g7ecce2dac-gcc-linux"
```

Run the pintool:

```bash
cd analysis/app/src/pintool
sudo $PIN_ROOT/pin -follow_execv -t obj-intel64/timeofouterloop.so -i $OUTDIR/loops.out -p $OUTDIR/pin/ -o pin.out -- $COMMAND_TO_RUN_SERVER
```

After about 30 seconds, stop the server process. You may be able to use `Ctrl+C`; otherwise use the server-specific stop command. For Httpd, for example:

```bash
sudo $HTTPD_BINARY -k graceful-stop
```

Stopping the server is essential for correct output. Finally, parse the results:

```bash
analysis/app/src/scripts/parse_pinout.sh $OUTDIR/pin
```

This produces `$OUTDIR/pin.out`, with one line for the serving phase of each server process or thread.

### Find system calls from `main()` and the main loop

To find system calls reachable from a program point at address `$addr` within function `$func`:

```bash
./syspart -p $BINARY -i -s main -a 2,$addr,$func > syscalls.out

grep 'JSON' syscalls.out | awk {'print $2'} > syscalls.json
grep 'PARTITION_SIZE' syscalls.out | awk {'print $2'} > partition_size.out
grep -w 'MAIN' syscalls.out | awk {'print $2'} > main_syscalls.out
grep -w 'MAINLOOP' syscalls.out | awk {'print $2'} > mainloop_syscalls.out
```

To find system calls reachable from a specific function `$func`:

```bash
./syspart -p $BINARY -i -s main -a 7,$func
```

To find system calls reachable from all functions:

```bash
./syspart -p $BINARY -i -s main -a 7,*
```

### Enforce a system call filter

The [enforcement component](enforcement/README.md) creates a Seccomp-BPF filter containing the allowed system calls and inserts it at the partition boundary.

#### Generate the filter

```bash
cd enforcement/src/scripts
python3 skip_list_filter.py <syscalls_json_file> > ../filter/filter.c
cd ../filter
make
```

These commands create `sysfilter.so`, which contains the system call filter.

#### Insert the filter into a binary

Build the enforcement component and transform the binary at the partition boundary:

```bash
cd enforcement
make
./sysenforce $BINARY <func_name> <partition_addr> $OUTPUT_BINARY sysfilter.so install_filter
```

The `(<func_name>, <partition_addr>)` pairs come from `$OUTDIR/pin.out` and must match the values used to produce the JSON file containing the allowed system calls. The command produces `$OUTPUT_BINARY` with the filter installed by invoking `install_filter()` from `libsyspart.so` at the partition boundary.

Only one active filter is currently supported. See the [enforcement README](enforcement/README.md) for a complete example.

## Tests

Build and run the test suite with:

```bash
cd test
make
```

The tests cover symbol and library relationships in three small examples:

- `hello/` verifies that a direct call to `printHello` is linked to `libhello.so`, and that `libhello.so` is linked to `libstdc++.so.6`.
- `helloIndirect/` checks the same library chain while keeping the `printHello` link indirect.
- `helloDynamic/` runs the dynamic analysis helper and confirms that `dlsym_static.txt` contains `printHello` and `dlopen_static.txt` contains `libhello.so`.