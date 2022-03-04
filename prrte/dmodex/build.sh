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
${PCC} --showme
set -e

echo "=========================="
echo "Building PMIx dmodex"
echo "=========================="

${PCC} dmodex.c -o dmodex

echo "=========================="
echo "PMIx dmodex build"
echo "=========================="
