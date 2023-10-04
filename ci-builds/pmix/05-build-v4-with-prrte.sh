#!/bin/bash -ex

#
# PRRTE requires a minimum of OpenPMIx v4.2.x
# If we change PMIx v4.2 branch then check to make
# sure that PRRTE still builds correctly.
#

#--------------------------------
# Sanity Checks
#--------------------------------
# Ignore $_PRRTE_CHECKOUT as we will use the current master branch

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

# Only run if we are modifying the v4.2 branch
if [ -n "$PR_TARGET_BRANCH" ] ; then
    if [[ "$PR_TARGET_BRANCH" != "v4.2" ]] ; then
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

#--------------------------------
# PMIx Build
#--------------------------------
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
git clone -b master --recurse-submodules https://github.com/openpmix/prrte.git
cd prrte

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
