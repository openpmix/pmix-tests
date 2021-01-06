#!/bin/bash

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

# Wrapper script used by CI framework to invoke test cases in this directory
${_python} ./run.py
exit $?
