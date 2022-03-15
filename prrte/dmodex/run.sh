#!/bin/bash -xe

# Final return value
FINAL_RTN=0

# Number of nodes - for accounting/verification purposes
# Default: 1
NUM_NODES=${CI_NUM_NODES:-1}

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
    prte --no-ready-msg &
else
    prte --no-ready-msg --hostfile $CI_HOSTFILE &
fi

date
# Wait for DVM to start
sleep 5
date


# ---------------------------------------
# Run the test - Dmodex (PMIx)
# ---------------------------------------
prun --map-by ppr:5:node ./dmodex 2>&1 | tee output.txt

# ---------------------------------------
# Verify the results
# ---------------------------------------
ERRORS=`grep -i "error\|fail" output.txt | wc -l`
if [[ $ERRORS -ne 0 ]] ; then
    echo "ERROR: Error string detected in the output"
    FINAL_RTN=1
    _shutdown
fi

LINES=`grep -i "PMIx_Finalize successfully completed" output.txt | wc -l`
if [[ $LINES -ne $(( 5 * $NUM_NODES )) ]] ; then
    echo "ERROR: Incorrect number of lines of output"
    FINAL_RTN=2
    _shutdown
fi


if [ $FINAL_RTN == 0 ] ; then
    echo "Success - dmodex"
fi

_shutdown

