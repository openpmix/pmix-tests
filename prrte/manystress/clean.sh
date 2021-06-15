#!/bin/bash -e

echo "============================"
echo "Cleanup manystress output logs"
echo "============================"
set -e
rm -f output.txt
rm -f output.*.txt

rm -f /tmp/output.sleeper.*.txt

# FIXME: Cleanup /tmp/output.sleeper* droppings on all nodes
# This might be sufficient but not sure so keep as comment for now
# if [ "x" != "x$CI_HOSTFILE" ] ; then
#     echo "============================"
#     echo "Cleanup remote output droppings"
#     echo "============================"
#     cat $CI_HOSTFILE | xargs -L1 -I '{}'  ssh {} rm -f /tmp/output.sleeper.\*.txt
# fi


if [ -f "DVM.log" ] ; then
    echo "============================"
    echo "Cleanup manystress DVM log"
    echo "============================"
    set -e
    rm -f DVM.log
fi

echo "============================"
echo "Cleanup manystress sleeper executable"
echo "============================"
rm -f sleeper
