#!/bin/sh


cd analysis/tools/egalito
git pull
make clean
make -j 8
cd ../../app
make clean
make
