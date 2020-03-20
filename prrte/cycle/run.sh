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
    pterm

    exit $FINAL_RTN
}

# ---------------------------------------
# Start the DVM
# ---------------------------------------
if [ "x" = "x$CI_HOSTFILE" ] ; then
    prte --daemonize
else
    prte --daemonize --hostfile $CI_HOSTFILE
fi

# Wait for DVM to start
sleep 5


# ---------------------------------------
# Run the test - hostname
# ---------------------------------------
_CMD="prun -n 1 hostname"
echo "======================="
echo "Running hostname: $_CMD"
echo "======================="

rm output.txt ; touch output.txt
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

# ---------------------------------------
# Run the test - init_finalize
# ---------------------------------------
_CMD="prun ./init_finalize_pmix"
echo ""
echo "======================="
echo "Running init_finalize_pmix: $_CMD"
echo "======================="

rm output.txt ; touch output.txt
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
