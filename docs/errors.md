### \#1 `AttributeError: 'NoneType' object has no attribute 'people'`
In debian 12, this error is occured while building egalito. Installing the following package solved this error:
`$ sudo apt-get install python3-launchpadlib`

### \#2 `E: Package 'libboost1.67-dev' has no installation candidate`
In debian 12, this error is occured while building egalito. Solved doing the following:
```shell
# check if you have any other libboost:
$ dpkg -l | grep libboost
# if you dont have libboost<version>-dev:
$ apt-cache search libboost 
# and install available libboost<version>-dev.
```
### \#3 `/usr/bin/ld: cannot find -ldistorm3: No such file or directory`
In debian 12, this error occured while building egalito. Solved by doing the following:
```shell
# Replace DISTORM_DIR with egalito/dep/distorm3. This is added to make linker see the distorm.so
export LD_LIBRARY_PATH=${DISTORM_DIR}/make/linux:$LD_LIBRARY_PATH
&& cd ${EGALITO_DIR} \
    && bash ./test/script/get-gtirb.sh stable \

# After building the dependencies, linked libdistorm3.so.3.4.0 to formats that build script was looking
&& cd dep \
    && make \
    && ln -s ${DISTORM_DIR}/make/linux/libdistorm3.so.3.4.0 ${DISTORM_DIR}/make/linux/libdistorm3.so.3 \
    && ln -s ${DISTORM_DIR}/make/linux/libdistorm3.so.3.4.0 ${DISTORM_DIR}/make/linux/libdistorm3.so \
    && ldconfig \
&& cd ${EGALITO_DIR} \
    && make -j $(nproc)

```


### \#4 `404 Not Found [IP: ...]` while accessing `http://ppa.launchpad.net/mhier/libboost-latest/ubuntu bookworm`

In Debian 12, this error occurs while building egalito. Because the repository `mhier/libboost-latest` does not have a release for Bookworm. This repository was likely added for `libboost`, which has already been installed. 

To solve this error, do the following:

1. Remove the repository from `/etc/apt/sources.list.d/`:
   ```bash
   rm /etc/apt/sources.list.d/mhier-libboost-latest.list
   ```

2. Edit `get_gtirb.sh` to comment out the line that adds the repository:
   ```diff
   -add-apt-repository ppa:mhier/libboost-latest
   +#add-apt-repository ppa:mhier/libboost-latest
   ```

After making these changes, retry the build process.

### \#5 `‘dummy’ may be used uninitialized [-Werror=maybe-uninitialized]`

In Debian 12, this error occurs while building Egalito due to the `dummy` variable in `gtest-death-test.cc` not being initialized. This can be solved by initializing the variable and adjusting the build script.

**Steps to resolve:**

1. Go to the error file (`gtest-death-test.cc`) and initialize the variable:
   ```c++
   int dummy = 0;
   ```
   This change aligns with the [latest version of googletest](https://github.com/google/googletest/blob/35d0c365609296fa4730d62057c487e3cfa030ff/googletest/src/gtest-death-test.cc#L1242), where the variable is initialized.

2. Edit `get-gtirb.sh` to skip re-cloning `gtirb` and creating the `build` directory by commenting out the relevant lines:
   ```diff
   -git clone --recursive https://github.com/GrammaTech/gtirb.git
   +#git clone --recursive https://github.com/GrammaTech/gtirb.git
   ...
   -mkdir build
   +#mkdir build
   ```

3. Run the script again:
   ```bash
   ./test/scripts/get-gtirb.sh
   ```

This time, it should run.