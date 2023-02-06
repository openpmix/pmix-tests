#!/bin/bash -e

SCRIPT_DIR=`dirname $0`

OPENPMIX_BRANCH='v4.2' PMIX_STANDARD_BRANCH='v4' $SCRIPT_DIR/checkout-repos.sh
mv scratch scratch-v4

$SCRIPT_DIR/compare-with-pmix-standard.py --openpmix scratch-v4/openpmix --standard scratch-v4/pmix-standard -t ${SCRIPT_DIR}/../etc/openpmix_v4-pmix-standard_v4.txt
