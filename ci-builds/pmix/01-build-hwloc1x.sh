#!/bin/bash -ex

#
# Regression test related to
#  https://github.com/openpmix/openpmix/issues/2057
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
./configure --prefix=${_BUILD_DIR}/install \
            --disable-debug \
            --enable-static \
            --enable-shared \
            --disable-visibility \
            --with-libevent=${LIBEVENT_INSTALL_PATH} \
            --with-hwloc=${HWLOC1_INSTALL_PATH}

#--------------------------------
# Make
#--------------------------------
make -j 10

#--------------------------------
# Make Install
#--------------------------------
make -j 10 install

exit 0
