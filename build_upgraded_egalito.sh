#!/bin/sh


cd analysis/tools/egalito
git checkout merger-wogramma
git pull
git submodule update --init --recursive
make clean
make -j 8
cd ../../app
make clean
make
