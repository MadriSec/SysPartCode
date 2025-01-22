# SysPart Howto
**Lets try to add information for all -a options, like in case seven below.**

| Flag            | Explanation |
|:---------------:|-------------|
| 'p', "PROG"     | The binary program to be analyzed |
| 's', "STARTFN"  | Name or address of the root function of the function call graph (usually main). Address should start with 0x |
| 't', "PATH"     | To enable typearmor. PATH refers to the path to the typearmor output file |
| 'i'             | To enable indirect call target analysis |
| 'l'             | To enable logging |
| 'g'             | To construct FCG with only direct edges. By default indirect edges are considered |
| |
| 'a', "ANALYSIS" | The type of analysis to be performed. Pass the number corresponding to each analysis followed by a comma separated argument list. |
|   | Example:** ```shell syspart -p ./mcf_s_base.imdeatest-m64 -s main -a 1``` |
| 1 | Prints the callgraph (no args)
| 2 | Print system calls filtered, given the address at which to partition and function containing the partition point (args : partition_point_address, func_name)
| 3 | Prints the difference of system calls accessible from STARTFN and syscalls accessible from a specific function (args : func_name)
| 4 | Prints the global AT list
| 5 | Prints AICT (Average Indirect call target)
| 6 | Prints the possible values of argument passed to a function (args : func_name, register_id)
| 7 | Prints the system call info of all functions or of a specific function(args : func_name or * (for all fns))
|   |  - AT functions are included. |
|   |  - Example: ```shell syspart -p <binary> -s main -a 7,*``` |
|   | <details> <summary> Results </summary> <pre> Total syscalls of __stdout_write : 2    // How many syscalls are called <br> <br> Direct : stdout_write : ioctl           // Syscalls that are directly called by the function <br> Derived : stdout_write : writev         // Syscalls that are reachable through invoked functions <br> Total : stdout_write : ioctl writev     // Direct + Derived <br> 16,20,                                  // Syscall numbers for each in Total </pre> </details> |
| | |
| 8 | Prints system calls filtered after including specified libraries (args : no_of_libs, lib1, lib2,...,libn) |
| 9 | Prints the callgraph with only indirect edges |
| 10 | If indirect call exists in any path or to trace the path of functions back to main (args : list of functions |
| 11 | If func2 is accessible from instruction with address addr in func1 (args : addr1, func1, func2) |
| 12 | Find system calls after including modules of dlsymed functions (args : output file from dlsym analysis) |
| 13 | Prints the no: of noreturn functions with and without our noreturn analysis |
| 14 | Prints the system calls which are directly invoked from AT functions |
| 15 | Prints if there is a path between from startfunc to endfun (args: startfunc, endfunc) |
| 16 | Print direct system calls of module (args : modulename) |
| 17 | Prints the callgraph of a module (args : modulename) |
| 18 | Prints the number of instructions in a function (args : functionname) |
| 19 | Prints if fork() and pthread() functions are invoked within the application |
| 20 | Print all functions of all modules |
| 21 | Prints the arguments to dlopen() |
| 22 | Prints the arguments to dlsym() |
