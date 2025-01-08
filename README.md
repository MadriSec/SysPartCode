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

For usage, please refer to the [usage guide](./docs/usage.md).

## 🚨 Errors

If having errors while building, you can check our [error log](./docs/errors.md)