#!/bin/sh


cd analysis/tools/egalito
git checkout master
git pull
git submodule update --init --recursive -- dep/capstone dep/distorm3 dep/keystone
make -C src clean
make -j 8 src
cd ../../app
make clean
make
