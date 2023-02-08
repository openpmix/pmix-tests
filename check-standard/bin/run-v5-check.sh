#!/bin/bash -e

SCRIPT_DIR=`dirname $0`

OPENPMIX_BRANCH='master' PMIX_STANDARD_BRANCH='master' $SCRIPT_DIR/checkout-repos.sh
mv scratch scratch-v5

$SCRIPT_DIR/compare-with-pmix-standard.py --openpmix scratch-v5/openpmix --standard scratch-v5/pmix-standard -t ${SCRIPT_DIR}/../etc/openpmix_master-pmix-standard_master.txt
