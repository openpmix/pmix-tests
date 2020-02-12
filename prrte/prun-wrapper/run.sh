#!/bin/bash -xe

# Final return value
FINAL_RTN=0

# Number of nodes - for accounting/verification purposes
# Default: 1
NUM_NODES=${CI_NUM_NODES:-1}

# Note this test is best exercised if you have a --hostfile or --host arg
_HOSTFILE_ARG=""
if [ "x" != "x$CI_HOSTFILE" ] ; then
    _HOSTFILE_ARG="--hostfile ${CI_HOSTFILE}"
fi

_DASH_HOST_ARG=""
_DASH_HOST_NUM_NODES=1
if [ "x" != "x$CI_HOSTFILE" ] ; then
    _HOST_A=`head -n 1 ${CI_HOSTFILE}`
    _HOST_B=`tail -n 1 ${CI_HOSTFILE}`
    _DASH_HOST_ARG="--host ${_HOST_A}:5,${_HOST_B}:5"
    _DASH_HOST_NUM_NODES=2
fi


# ---------------------------------------
# Run the test - Hostname with --hostfile
# ---------------------------------------
./bin/myrun --map-by ppr:5:node ${_HOSTFILE_ARG} hostname 2>&1 | tee output-hn.txt

# ---------------------------------------
# Verify the results
# ---------------------------------------
ERRORS=`grep ERROR output-hn.txt | wc -l`
if [[ $ERRORS -ne 0 ]] ; then
    echo "ERROR: Error string detected in the output"
    exit 1
fi

LINES=`wc -l output-hn.txt | awk '{print $1}'`
if [[ $LINES -ne $(( 5 * $NUM_NODES )) ]] ; then
    echo "ERROR: Incorrect number of lines of output"
    exit 2
fi

if [ $FINAL_RTN == 0 ] ; then
    echo "Success - hostname"
fi

# ---------------------------------------
# Run the test - Hostname with --hostfile and full path
# ---------------------------------------
$PWD/bin/myrun --map-by ppr:5:node ${_HOSTFILE_ARG} hostname 2>&1 | tee output-hn.txt

# ---------------------------------------
# Verify the results
# ---------------------------------------
ERRORS=`grep ERROR output-hn.txt | wc -l`
if [[ $ERRORS -ne 0 ]] ; then
    echo "ERROR: Error string detected in the output"
    exit 1
fi

LINES=`wc -l output-hn.txt | awk '{print $1}'`
if [[ $LINES -ne $(( 5 * $NUM_NODES )) ]] ; then
    echo "ERROR: Incorrect number of lines of output"
    exit 2
fi

if [ $FINAL_RTN == 0 ] ; then
    echo "Success - hostname"
fi


# ---------------------------------------
# Run the test - Hostname with --host
# ---------------------------------------
./bin/myrun --map-by ppr:5:node ${_DASH_HOST_ARG} hostname 2>&1 | tee output-hn.txt

# ---------------------------------------
# Verify the results
# ---------------------------------------
ERRORS=`grep ERROR output-hn.txt | wc -l`
if [[ $ERRORS -ne 0 ]] ; then
    echo "ERROR: Error string detected in the output"
    exit 1
fi

LINES=`wc -l output-hn.txt | awk '{print $1}'`
if [[ $LINES -ne $(( 5 * $_DASH_HOST_NUM_NODES )) ]] ; then
    echo "ERROR: Incorrect number of lines of output"
    exit 2
fi

if [ $FINAL_RTN == 0 ] ; then
    echo "Success - hostname"
fi


# ---------------------------------------
# Run the test - Hello World (PMIx) with --hostfile
# ---------------------------------------
./bin/myrun --map-by ppr:5:node ${_HOSTFILE_ARG} ../hello_world/hello 2>&1 | tee output.txt

# ---------------------------------------
# Verify the results
# ---------------------------------------
ERRORS=`grep ERROR output.txt | wc -l`
if [[ $ERRORS -ne 0 ]] ; then
    echo "ERROR: Error string detected in the output"
    exit 1
fi

LINES=`wc -l output.txt | awk '{print $1}'`
if [[ $LINES -ne $(( 5 * $NUM_NODES )) ]] ; then
    echo "ERROR: Incorrect number of lines of output"
    exit 2
fi

# ---------------------------------------
# Run the test - Hello World (PMIx) with --hostfile
# ---------------------------------------
./bin/myrun --map-by ppr:5:node ${_DASH_HOST_ARG} ../hello_world/hello 2>&1 | tee output.txt

# ---------------------------------------
# Verify the results
# ---------------------------------------
ERRORS=`grep ERROR output.txt | wc -l`
if [[ $ERRORS -ne 0 ]] ; then
    echo "ERROR: Error string detected in the output"
    exit 1
fi

LINES=`wc -l output.txt | awk '{print $1}'`
if [[ $LINES -ne $(( 5 * $_DASH_HOST_NUM_NODES )) ]] ; then
    echo "ERROR: Incorrect number of lines of output"
    exit 2
fi


# ---------------------------------------
# Yay
# ---------------------------------------
if [ $FINAL_RTN == 0 ] ; then
    echo "Success - hello world"
fi

exit $FINAL_RTN

