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
# Run the test - Dmodex (PMIx)
# ---------------------------------------
prterun --hostfile $CI_HOSTFILE --map-by ppr:10:node ./dmodex 2>&1 | tee output.txt
if [ $? -ne 0 ]; then
    echo "Error - seems prterun failed."
    exit 42
fi

# ---------------------------------------
# Verify the results
# ---------------------------------------
ERRORS=`grep -i "error\|fail\|lost" output.txt | wc -l`
if [[ $ERRORS -ne 0 ]] ; then
    echo "ERROR: Error string detected in the output"
    exit 1
fi

LINES=`grep -i "PMIx_Finalize successfully completed" output.txt | wc -l`
if [[ $LINES -ne $(( 10 * $NUM_NODES )) ]] ; then
    echo "ERROR: Incorrect number of lines of output"
    exit 2
fi

rm output.txt

# Now verify prun
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

prun --map-by ppr:10:node ./dmodex 2>&1 | tee output.txt
if [ $? -ne 0 ]; then
    echo "Error - seems prun failed."
    FINAL_RTN=43
    _shutdown
fi

# ---------------------------------------
# Verify the results
# ---------------------------------------
ERRORS=`grep -i "error\|fail\|lost" output.txt | wc -l`
if [[ $ERRORS -ne 0 ]] ; then
    echo "ERROR: Error string detected in the output"
    FINAL_RTN=44
    _shutdown
fi

LINES=`grep -i "PMIx_Finalize successfully completed" output.txt | wc -l`
if [[ $LINES -ne $(( 10 * $NUM_NODES )) ]] ; then
    echo "ERROR: Incorrect number of lines of output"
    FINAL_RTN=3
    _shutdown
fi

if [ $FINAL_RTN == 0 ] ; then
    echo "Success - dmodex"
fi

_shutdown

