#!/bin/bash -e

if [ "x" == "x$MPIR_SHIM_ROOT" ] ; then
    export MPIR_SHIM_ROOT=/workspace/exports/mpir-shim
fi
if [ "x" == "x$PMIX_ROOT" ] ; then
    export PMIX_ROOT=/workspace/exports/pmix
fi

echo "=========================="
echo "Checkout the current MPIR Shim"
echo "=========================="
git clone https://github.com/openpmix/mpir-to-pmix-guide.git

echo "=========================="
echo "Build the MPIR Shim"
echo "=========================="
cd mpir-to-pmix-guide
./autogen.sh
./configure --prefix=$MPIR_SHIM_ROOT --with-pmix=$PMIX_ROOT
make
make install

echo "=========================="
echo "Build the MPIR Shim CI"
echo "=========================="
cd test/ci/
./build.sh

