#!/bin/bash -e

echo "=========================="
echo "Setup the prun wrapper"
echo "=========================="

rm -rf bin
mkdir -p bin
cd bin

cp `which prun` myrun
cp `which prte` .
cp `which prted` .

cd -

cd ../hello_world && ./build.sh ; cd -
