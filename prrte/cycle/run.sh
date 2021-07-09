#!/bin/bash

# Final return value
FINAL_RTN=0

# Number of nodes - for accounting/verification purposes
NUM_NODES=${CI_NUM_NODES:-1}

NUM_ITERS=500

_shutdown()
{
    # ---------------------------------------
    # Cleanup DVM
    # ---------------------------------------
    pterm --dvm-uri file:dvm.uri

    exit $FINAL_RTN
}

# ---------------------------------------
# Start the DVM
# ---------------------------------------
if [ "x" = "x$CI_HOSTFILE" ] ; then
    hostarg=
else
    hostarg="--hostfile $CI_HOSTFILE"
fi
rm -f dvm.uri
echo "======================="
echo "Starting DVM: prte --no-ready-msg --report-uri dvm.uri $hostarg &"
echo "======================="
prte --no-ready-msg --report-uri dvm.uri $hostarg &

# ---------------------------------------
# Run the test - hostname
# ---------------------------------------
_CMD="prun --dvm-uri file:dvm.uri --num-connect-retries 1000 -n 1 hostname"
echo "======================="
echo "Running hostname: $_CMD"
echo "======================="

rm -f output.txt ; touch output.txt
for n in $(seq 1 $NUM_ITERS) ; do
    echo -e "--------------------- Execution (hostname): $n"
    $_CMD 2>&1 | tee -a output.txt
    st=${PIPESTATUS[0]}
    if [ $st -ne 0 ] ; then
        echo "ERROR: prun failed with $st"
        FINAL_RTN=3
        _shutdown
    fi
done

echo "---- Done"
# ---------------------------------------
# Verify the results
# ---------------------------------------
ERRORS=`grep ERROR output.txt | wc -l`
if [[ $ERRORS -ne 0 ]] ; then
    echo "ERROR: Error string detected in the output"
    FINAL_RTN=1
    _shutdown
fi

LINES=`wc -l output.txt | awk '{print $1}'`
if [[ $LINES -ne $NUM_ITERS ]] ; then
    echo "ERROR: Incorrect number of lines of output. Expected $NUM_ITERS. Actual $LINES"
    FINAL_RTN=2
    _shutdown
fi

if [ $FINAL_RTN == 0 ] ; then
    echo "Success - hostname"
fi
_shutdown


rm -f dvm.uri
echo "======================="
echo "Starting DVM: prte --no-ready-msg --report-uri dvm.uri $hostarg &"
echo "======================="
prte --no-ready-msg --report-uri dvm.uri $hostarg &

# ---------------------------------------
# Run the test - init_finalize
# ---------------------------------------
_CMD="prun --dvm-uri file:dvm.uri --num-connect-retries 1000 ./init_finalize_pmix"
echo ""
echo "======================="
echo "Running init_finalize_pmix: $_CMD"
echo "======================="

rm -f output.txt ; touch output.txt
for n in $(seq 1 $NUM_ITERS) ; do
    echo -e "--------------------- Execution (init/finalize): $n"
    $_CMD 2>&1 | tee -a output.txt
    st=${PIPESTATUS[0]}
    if [ $st -ne 0 ] ; then
        echo "ERROR: prun failed with $st"
        FINAL_RTN=3
        _shutdown
    fi
done

echo "---- Done"
# ---------------------------------------
# Verify the results
# ---------------------------------------
ERRORS=`grep ERROR output.txt | wc -l`
if [[ $ERRORS -ne 0 ]] ; then
    echo "ERROR: Error string detected in the output"
    FINAL_RTN=1
    _shutdown
fi

LINES=`wc -l output.txt | awk '{print $1}'`
if [[ $LINES -ne 0 ]] ; then
    echo "ERROR: Incorrect number of lines of output. Expected 0. Actual $LINES"
    FINAL_RTN=2
    _shutdown
fi

if [ $FINAL_RTN == 0 ] ; then
    echo "Success"
fi

_shutdown
