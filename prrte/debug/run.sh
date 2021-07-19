#!/bin/bash

# Baselines assume exactly 3 nodes
_required_num_nodes=3

_python=""

# Find all python* binaries
_CHECK_BINARIES=()
_CHECK_BINARIES+=`compgen -c python | grep -v "config\|m$" | sort -ru`

for _py in ${_CHECK_BINARIES} ; do
    _py_fp=`command -v ${_py}`
    # Check if we have this binary installed
    if [ $? -eq 0 ] ; then
        # Extract the major version
        VER=`${_py_fp} -c 'import sys; print(sys.version_info[0])'`
        # Find the first one at level 3 or above
        if [ $VER -ge 3 ] ; then
            _python=${_py_fp}
            break
        fi
    fi
done

if [[ $_python == "" ]] ; then
    echo "Error: A Python 3 or later interpreter count not be found."
    exit 1
fi

# Sanity checking on number of nodes
if [ "x" = "x$CI_NUM_NODES" ] ; then
    echo "Error: CI_NUM_NODES must be provided"
    exit 2
fi
if [ "x" = "x$CI_HOSTFILE" ] ; then
    echo "Error: A CI_HOSTFILE must be provided with 3 nodes"
    exit 3
fi
if [[ "$CI_NUM_NODES" -lt "$_required_num_nodes" ]] ; then
    echo "Error: CI_NUM_NODES must be greater than or equal to $_required_num_nodes"
    exit 2
fi

export CI_NUM_NODES=$_required_num_nodes

CI_HOSTFILE_DEBUG=${CI_HOSTFILE}.debug
head -n $CI_NUM_NODES $CI_HOSTFILE > $CI_HOSTFILE_DEBUG
export CI_HOSTFILE=$CI_HOSTFILE_DEBUG

# Wrapper script used by CI framework to invoke test cases in this directory

${_python} ./cirun.py
_rtn=$?
rm $CI_HOSTFILE_DEBUG
exit $_rtn
