#!/bin/bash -ex

#
# Build and run distcheck on a clean PMIx checkout copy.
#

#--------------------------------
# Sanity Checks
#--------------------------------
if [ -z "${_PMIX_CHECKOUT}" ]; then
    echo "Error: No PMIx checkout"
    # git clone https://github.com/openpmix/openpmix.git
    exit 1
fi

if [ ! -d "${_PMIX_CHECKOUT}" ] ; then
    echo "Error: No PMIx checkout in ${_PMIX_CHECKOUT}"
    echo "Set the _PMIX_CHECKOUT envar to your pmix checkout"
    exit 1
fi

# Only works on the master branch for now.
if [ -n "$PR_TARGET_BRANCH" ] ; then
    if [[ "$PR_TARGET_BRANCH" != "master" ]] ; then
        echo "Warning: This build does not work for this branch"
        exit 0
    fi
fi

#--------------------------------
# Setup a clean build location
#--------------------------------
if [ -z "${_BUILD_DIR}" ]; then
    _BUILD_DIR=`mktemp -d $HOME/tmp-build-XXXXX`
fi

cd "${_BUILD_DIR}"

cp -R "${_PMIX_CHECKOUT}" .
cd `basename "${_PMIX_CHECKOUT}"`

#--------------------------------
# Autogen
#--------------------------------
export AUTOMAKE_JOBS=20
./autogen.pl

#--------------------------------
# Configure
#--------------------------------
./configure --with-libevent=${LIBEVENT_INSTALL_PATH} \
            --with-hwloc=${HWLOC_INSTALL_PATH}

#--------------------------------
# Make Distcheck
#--------------------------------
make -j 20 distcheck \
     DISTCHECK_CONFIGURE_FLAGS="--with-libevent=${LIBEVENT_INSTALL_PATH} --with-hwloc=${HWLOC_INSTALL_PATH}"

exit 0
