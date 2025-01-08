## 🔧 Setup Instructions

To set up the project, ensure you have SSH access configured for [GitHub](https://github.com) and [Gitlab](). For details on adding a new SSH key to your GitHub account, please refer to this [link](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account).

**Installing Dependencies**  
Install all necessary dependencies by running:
```shell
sudo apt-get install make g++ libreadline-dev gdb lsb-release unzip libc6-dbg libstdc++6-7-dbg python3 python3-launchpadlib
sudo apt install libunwind-dev
```

**Cloning the Repository**  
This repository uses several git submodules for benchmarking. Once your public keys are configured, clone the repository recursively with:

```shell
git clone git@github.com:MadriSec/SysPartCode.git --recursive
```

**Building the Tool**  
Follow the instructions below to build the egalito:
```shell
cd SysPartCode # repository directory

# relative directories of dependencies
export EGALITO_DIR=analysis/tools/egalito
export DISTORM_DIR=analysis/tools/egalito/dep/distorm3

# Set the library path environment variable
export LD_LIBRARY_PATH=${DISTORM_DIR}/make/linux:$LD_LIBRARY_PATH

# Navigate to the Egalito directory and run the GTIRB script
cd ${EGALITO_DIR} && \
bash ./test/script/get-gtirb.sh stable

# Navigate to the dependencies directory, compile, and create symbolic links
cd ${EGALITO_DIR}/dep && \
make && \
ln -s ${DISTORM_DIR}/make/linux/libdistorm3.so.3.4.0 ${DISTORM_DIR}/make/linux/libdistorm3.so.3 && \
ln -s ${DISTORM_DIR}/make/linux/libdistorm3.so.3.4.0 ${DISTORM_DIR}/make/linux/libdistorm3.so && \
ldconfig

# Return to the Egalito directory and build the project
cd ${EGALITO_DIR} && \
make -j $(nproc)
```
then build syspart:
```shell
# Finally build SysPart
cd analysis/app && make -j $(nproc)
```
