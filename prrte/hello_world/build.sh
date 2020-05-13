#!/bin/bash -e

echo "=========================="
echo "Detect wrapper compiler"
echo "=========================="
set +e
PCC=`which pmixcc`
if [ $? != 0 ] ; then
    PCC=`which pcc`
    if [ $? != 0 ] ; then
        echo "ERROR: Failed to find a wrapper compiler"
        exit 1
    fi
fi
echo "Compiler: $PCC"
echo ${PCC} --showme
set -e

echo "=========================="
echo "Building PMIx Hello World"
echo "=========================="

${PCC} hello.c -o hello
