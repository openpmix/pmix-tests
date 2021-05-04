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

gcc -o tcfilter tcfilter.c
if [ $? -ne 0 ] ; then
    echo "Compilation of tcfilter failed"
    exit 1
fi

  # Build tests using PRRTE examples
for program in direct indirect attach daemon hello direct-multi indirect-multi
do
    echo "=========================="
    echo "Building PMIx ${program}"
    echo "=========================="
    # test-utils needs to be rebuilt for each test to include proper labeling
    # Testcase headers are assumed to be in the same directory as testcase source
    gcc -g -o test-utils.o -c -DTPRINT_PFX="\"${program}\"" test-utils.c
    if [ $? -ne 0 ] ; then
        echo "Compilation of test-utils failed"
        exit 1
    fi
    ${PCC} -Wall -g -o ${program} -I${CI_PRRTE_SRC}/examples/debugger ${CI_PRRTE_SRC}/examples/debugger/${program}.c test-utils.o -ldl
    if [ $? -ne 0 ] ; then
        echo "Compilation of $program failed"
        exit 1
    fi
done
