#!/bin/bash -ex

#
# PRRTE requires a minimum of OpenPMIx v4.1.x
#

#--------------------------------
# Sanity Checks
#--------------------------------
# Ignore $_PMIX_CHECKOUT as we will use the current v4.1.x branch

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
git clone -b v4.1 https://github.com/openpmix/openpmix.git
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
            --with-hwloc=${HWLOC1_INSTALL_PATH}

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
