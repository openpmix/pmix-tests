#!/bin/bash -xe

# Final return value
FINAL_RTN=0

# Number of nodes - for accounting/verification purposes
# Default: 1
NUM_NODES=${CI_NUM_NODES:-1}

if [ "x" == "x$MPIR_SHIM_ROOT" ] ; then
    export MPIR_SHIM_ROOT=/workspace/exports/mpir-shim
fi
if [ "x" == "x$PMIX_ROOT" ] ; then
    export PMIX_ROOT=/workspace/exports/pmix
fi

# ---------------------------------------
# Run the test - Hostname with --hostfile
# ---------------------------------------
cd mpir-to-pmix-guide/test/ci/
./run.sh
FINAL_RTN=$?

if [ $FINAL_RTN == 0 ] ; then
    echo "Success - MPIR Shim"
fi
