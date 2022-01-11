#!/bin/bash -e

script_name="run-xversion.sh"

ADDITIONAL_OPTIONS=""
ADDITIONAL_RUN_OPTIONS=""

trepo=""
tbranch=""
tpath=""

while [[ $# -gt 0 ]] ; do
    case $1 in
        "-h" | "--help")
            printf "Usage: %s [option]
    -r | --repo [REPO]      HTTPS repo address (requires -b)
    -b | --branch [BRANCH]  Git branch (requires -r)
    -p | --path [PATH]      Full path to source directory
    -h | --help             Print this help message
" \
                ${script_name}
            return 0
            ;;
        "-r" | "-R" | "--repo" | "--remote")
            if [[ "x$trepo" != "x" ]] ; then
                echo "Error: --repo can only be supplied one time"
                exit 1
            fi
            shift
            trepo=$1
            ADDITIONAL_OPTIONS+=" --with-repo $trepo"
            ;;
        "-b" | "-B" | "--branch")
            if [[ "x$tbranch" != "x" ]] ; then
                echo "Error: --branch can only be supplied one time"
                exit 1
            fi
            shift
            tbranch=$1
            ADDITIONAL_OPTIONS+=" --with-branch $tbranch"
            ;;
        "-p" | "-P" | "--path")
            if [[ "x$tpath" != "x" ]] ; then
                echo "Error: --path can only be supplied one time"
                exit 1
            fi
            shift
            tpath=$1
            ADDITIONAL_OPTIONS+=" --with-src $tpath"
            ;;
        "--")
            shift
            ADDITIONAL_RUN_OPTIONS+=" "$@
            break
            ;;
        *)
            printf "Unkonwn option: %s\n" $1
            exit 1
            ;;
    esac
    shift
done

if [[ "x$trepo" != "x" && "x$tbranch" == "x" || "x$trepo" == "x" && "x$tbranch" != "x" ]] ; then
    echo "Error: Must supply both --repo and --branch together"
    exit 1
fi

echo ""
echo "============ Run Options"
echo ""
echo "General : "$ADDITIONAL_OPTIONS
echo "Run Only: "$ADDITIONAL_RUN_OPTIONS

echo ""
echo "============ Update test repo"
echo ""
cd $HOME/pmix-tests/crossversion/
set +e
git pull
set -e

echo ""
echo "============ Checking builds"
echo ""
./xversion.py --basedir=$HOME/scratch \
              --with-hwloc=${HWLOC_INSTALL_PATH} \
              --with-hwloc1=${HWLOC1_INSTALL_PATH} \
              --with-libevent=${LIBEVENT_INSTALL_PATH} \
              ${ADDITIONAL_OPTIONS} -r -q

echo ""
echo "============ Checking versions"
echo ""
./xversion.py --basedir=$HOME/scratch \
              --with-hwloc=${HWLOC_INSTALL_PATH} \
              --with-hwloc1=${HWLOC1_INSTALL_PATH} \
              --with-libevent=${LIBEVENT_INSTALL_PATH} \
              ${ADDITIONAL_OPTIONS} ${ADDITIONAL_RUN_OPTIONS} -b -q
