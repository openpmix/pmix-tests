#!/bin/bash -ex

#
# Regression test related to:
#  https://github.com/openpmix/openpmix/issues/2003#issuecomment-756902073
#

#--------------------------------
# Sanity Checks
#--------------------------------
if [ -z "${_PMIX_CHECKOUT}" ]; then
    echo "Error: No PMIx checkout"
    # git clone https://github.com/openpmix/openpmix.git
    exit 1
fi

if [ ! -d ${_PMIX_CHECKOUT} ] ; then
    echo "Error: No PMIx checkout in ${_PMIX_CHECKOUT}"
    echo "Set the _PMIX_CHECKOUT envar to your pmix checkout"
    exit 1
fi

# Only works on the master and v4.0 branches
if [ -n "$PR_TARGET_BRANCH" ] ; then
    if [[ "$PR_TARGET_BRANCH" != "master" && "$PR_TARGET_BRANCH" != "v4.0" ]] ; then
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

cd $_BUILD_DIR

cp -R ${_PMIX_CHECKOUT} .
cd `basename ${_PMIX_CHECKOUT}`

#--------------------------------
# Autogen
#--------------------------------
export AUTOMAKE_JOBS=20
./autogen.pl

#--------------------------------
# Configure
#--------------------------------
mkdir -p debian/static-build

#--------------------------------
# VPATH static
#--------------------------------
# cd debian/static-build/
# ../../configure --prefix=${_BUILD_DIR}/install-static \
#                 --disable-shared --enable-static \
#                 --with-libevent=${LIBEVENT_INSTALL_PATH} \
#                 --with-hwloc=${HWLOC_INSTALL_PATH} \
#                 --enable-python-bindings
# make -j 20
# make -j 20 install

exit 0
