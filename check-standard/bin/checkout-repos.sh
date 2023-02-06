#!/bin/bash -e

#-------------------------
# 'master', 'v4.2'
OPENPMIX_BRANCH="${OPENPMIX_BRANCH:-master}"

# 'master', 'v4'
PMIX_STANDARD_BRANCH="${PMIX_STANDARD_BRANCH:-master}"

echo "=========================="
echo "OpenPMIx      : "${OPENPMIX_BRANCH}
echo "PMIx Standard : "${PMIX_STANDARD_BRANCH}
echo "=========================="

#-------------------------
_OPENPMIX_DIR=${PWD}"/scratch/openpmix"
_PMIX_STANDARD_DIR=${PWD}"/scratch/pmix-standard"
if [[ -d ${_OPENPMIX_DIR} ]] ; then
    echo "Error: The OpenPMIx directory exists. Please remove and re-run."
    echo "       ${_OPENPMIX_DIR}"
    exit 1
fi
if [[ -d ${_OPENPMIX_DIR} ]] ; then
    echo "Error: The PMIx Standard directory exists. Please remove and re-run."
    echo "       ${PMIX_STANDARD_BRANCH}"
    exit 1
fi

#-------------------------
mkdir -p scratch
cd scratch

echo "========> Cloning OpenPMIx"
git clone -b ${OPENPMIX_BRANCH} https://github.com/openpmix/openpmix.git openpmix

echo "========> Cloning PMIx Standard"
git clone -b ${PMIX_STANDARD_BRANCH} https://github.com/pmix/pmix-standard.git pmix-standard

echo "========> Building PMIx Standard"
cd pmix-standard
make

echo "========> Success"
exit 0
