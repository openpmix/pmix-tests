#!/bin/bash -ex

#
# PRRTE requires a minimum of OpenPMIx v4.2.4
#

#--------------------------------
# Sanity Checks
#--------------------------------
# Ignore $_PMIX_CHECKOUT as we will use the head of the current v4.2 branch

if [ -z "${_PRRTE_CHECKOUT}" ]; then
    echo "Error: No PRRTE checkout"
    # git clone https://github.com/openpmix/prrte.git
    exit 1
fi

if [ ! -d ${_PRRTE_CHECKOUT} ] ; then
    echo "Error: No PRRTE checkout in ${_PRRTE_CHECKOUT}"
    echo "Set the _PRRTE_CHECKOUT envar to your prrte checkout"
    exit 1
fi

#--------------------------------
# Setup a clean build location
#--------------------------------
if [ -z "${_BUILD_DIR}" ]; then
    _BUILD_DIR=`mktemp -d $HOME/tmp-build-XXXXX`
fi

cd $_BUILD_DIR

#--------------------------------
# PMIx Build
#--------------------------------
if [ -n "$PR_TARGET_BRANCH" ] ; then
    if [ "$PR_TARGET_BRANCH" == "v3.0" ] || [ "$PR_TARGET_BRANCH" == "v3.1" ] ; then
        git clone -b v4.2 --recurse-submodules https://github.com/openpmix/openpmix.git
    else
        # no need to do another build as we have tested against pmix master elsewhere
        exit 0
    fi
else
    exit 0
fi
cd openpmix

#--------------------------------
# Autogen
#--------------------------------
export AUTOMAKE_JOBS=20
./autogen.pl

#--------------------------------
# Configure
#--------------------------------
./configure --prefix=${_BUILD_DIR}/install-pmix \
            --disable-debug \
            --with-libevent=${LIBEVENT_INSTALL_PATH} \
            --with-hwloc=${HWLOC_INSTALL_PATH}

#--------------------------------
# Make
#--------------------------------
make -j 10

#--------------------------------
# Make Install
#--------------------------------
make -j 10 install


#--------------------------------
# PRRTE Build
#--------------------------------
cd $_BUILD_DIR
cp -R ${_PRRTE_CHECKOUT} .
cd `basename ${_PRRTE_CHECKOUT}`

#--------------------------------
# Autogen
#--------------------------------
export AUTOMAKE_JOBS=20
./autogen.pl

#--------------------------------
# Configure
#--------------------------------
./configure --prefix=${_BUILD_DIR}/install-prrte \
            --disable-debug \
            --with-pmix=${_BUILD_DIR}/install-pmix \
            --with-libevent=${LIBEVENT_INSTALL_PATH} \
            --with-hwloc=${HWLOC_INSTALL_PATH}

#--------------------------------
# Make
#--------------------------------
make -j 10

#--------------------------------
# Make Install
#--------------------------------
make -j 10 install


exit 0
