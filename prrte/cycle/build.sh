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
echo "Building PMIx cycle tests"
echo "=========================="

${PCC} init_finalize_pmix.c -o init_finalize_pmix
${PCC} multi_init_finalize_pmix.c -o multi_init_finalize_pmix
