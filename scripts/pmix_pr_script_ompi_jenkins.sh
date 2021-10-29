#!/bin/bash
#
# Script used by the Open MPI https://jenkins.open-mpi.org/jenkins/ jenkins instance
# for running the PMIX tests driven by non-prrte launcher test suite
#
ifaketty () { script -qfc "$(printf "%q " "$@")"; }
echo $PATH
echo $SHELL
echo "SHA1 -"${sha1}
echo "On login node:"
hostname

#
# Start by figuring out what we are...
#
os=`uname -s`
if test "${os}" = "Linux"; then
    eval "PLATFORM_ID=`sed -n 's/^ID=//p' /etc/os-release`"
    eval "VERSION_ID=`sed -n 's/^VERSION_ID=//p' /etc/os-release`"
else
    PLATFORM_ID=`uname -s`
    VERSION_ID=`uname -r`
fi

echo "--> platform: $PLATFORM_ID"
echo "--> version: $VERSION_ID"

./autogen.pl
if [ $? != 0 ]; then
    echo "---------------------------------------------------------------------"
    echo "--------------------------- autogen FAILED --------------------------"
    echo "---------------------------------------------------------------------"
    exit -1
fi

./configure --prefix=${PWD}/install_dir --with-libevent=/usr --with-hwloc=/usr
if [ $? != 0 ]; then
    echo "---------------------------------------------------------------------"
    echo "-------------------------- configure FAILED -------------------------"
    echo "---------------------------------------------------------------------"
    exit -1
fi
make clean
make check
if [ $? != 0 ]; then
    echo "---------------------------------------------------------------------"
    echo "------------------------- make check FAILED -------------------------"
    echo "---------------------------------------------------------------------"
    exit -1
fi
make -j 4 V=1 install
if [ $? != 0 ]; then
    echo "---------------------------------------------------------------------"
    echo "------------------------ make install FAILED ------------------------"
    echo "---------------------------------------------------------------------"
    exit -1
fi
export PMIX_INSTALLDIR=${PWD}/install_dir
pushd ${PWD}/test/test_v2
echo "---------------------------------------------------------------------"
echo "-------------------------- MAKING V2 TESTS --------------------------"
echo "---------------------------------------------------------------------"
make clean
make
if [ $? != 0 ]; then
    echo "---------------------------------------------------------------------"
    echo "---------------------- MAKE OF V2 TESTS FAILED ----------------------"
    echo "---------------------------------------------------------------------"
    exit -1
fi

echo "---------------------------------------------------------------------"
echo "------------------------- STARTING V2 TESTS -------------------------"
echo "---------------------------------------------------------------------"
for test in test_init_fin test_helloworld test_get_basic test_get_peers test_fence_basic test_fence_wildcard
do
    echo "RUNNING: ./pmix_test -s 1 -n 2 -e ./$test"
    timeout -s SIGSEGV 10m ./pmix_test -s 1 -n 2 -e ./$test
    if [ $? != 0 ]; then
        echo "---------------------------------------------------------------------"
        echo "--------------------------- $test FAILED ----------------------------"
        echo "---------------------------------------------------------------------"
        exit -1
    fi

    echo "RUNNING: ./pmix_test -s 4 -n 16 -e ./$test"
    timeout -s SIGSEGV 10m ./pmix_test -s 4 -n 16 -e ./$test
    if [ $? != 0 ]; then
        echo "---------------------------------------------------------------------"
        echo "--------------------------- $test FAILED ----------------------------"
        echo "---------------------------------------------------------------------"
        exit -1
    fi

    echo "RUNNING: ./pmix_test -s 4 -n 16 -e ./$test -d '0:0,1,3,5,7,9;1:2,4,6,8;2:10,12;3:11,13,14,15'"
    timeout -s SIGSEGV 10m ./pmix_test -s 4 -n 16 -e ./$test -d '0:0,1,3,5,7,9;1:2,4,6,8;2:10,12;3:11,13,14,15'
    if [ $? != 0 ]; then
        echo "---------------------------------------------------------------------"
        echo "--------------------------- $test FAILED ----------------------------"
        echo "---------------------------------------------------------------------"
        exit -1
    fi

done

# Timed wildcard and partial fence tests (the different runs are for testing different parameters)
PMIX_ERR_TIMEOUT=232
num_timeouts=0
for test in test_fence_wildcard test_fence_partial
do
    echo "RUNNING: ./pmix_test -s 4 -n 16 -d '0:0,1,3,5,7,9;1:2,4,6,8;2:10,12;3:11,13,14,15' -- ./$test --time-fence"
    timeout -s SIGSEGV 10m ./pmix_test -s 4 -n 16 -d '0:0,1,3,5,7,9;1:2,4,6,8;2:10,12;3:11,13,14,15' -- ./$test --time-fence
    retcode=$?
    if [ $retcode != 0 ]; then
        # If test failed due to an intra-test timeout, retry with different parameters
        if [ $retcode -eq $PMIX_ERR_TIMEOUT ]; then
            ((num_timeouts++))
            echo "TIMED OUT; RETRYING with: ./pmix_test -s 4 -n 16 -d '0:0,1,3,5,7,9;1:2,4,6,8;2:10,12;3:11,13,14,15' -- ./$test -m 400"
            sleep 60
            timeout -s SIGSEGV 10m ./pmix_test -s 4 -n 16 -d '0:0,1,3,5,7,9;1:2,4,6,8;2:10,12;3:11,13,14,15' -- ./$test -m 400
            retcode=$?
            if [ $retcode != 0 ]; then
                if [ $retcode -eq $PMIX_ERR_TIMEOUT ]; then
                    ((num_timeouts++))
                    echo "---------------------------------------------------------------------"
                    echo "----- $test INTERNALLY TIMED OUT; CONTINUING ----------"
                    echo "---------------------------------------------------------------------"
                else
                    echo "---------------------------------------------------------------------"
                    echo "-------------------- $test FAILED ---------------------"
                    echo "---------------------------------------------------------------------"
                    exit -1
                fi
            fi
        else
            echo "---------------------------------------------------------------------"
            echo "-------------------- $test FAILED ---------------------"
            echo "---------------------------------------------------------------------"
            exit -1
        fi
    fi

    echo "RUNNING: ./pmix_test -s 4 -n 16 -d '0:0,1,3,5,7,9;1:2,4,6,8;2:10,12;3:11,13,14,15' -- ./$test -m 200 -r 150"
    timeout -s SIGSEGV 10m ./pmix_test -s 4 -n 16 -d '0:0,1,3,5,7,9;1:2,4,6,8;2:10,12;3:11,13,14,15' -- ./$test -m 200 -r 150
    retcode=$?
    if [ $retcode != 0 ]; then
        # If test failed due to an intra-test timeout, retry with different parameters
        if [ $retcode -eq $PMIX_ERR_TIMEOUT ]; then
            ((num_timeouts++))
            echo "TIMED OUT; RETRYING with: ./pmix_test -s 4 -n 16 -d '0:0,1,3,5,7,9;1:2,4,6,8;2:10,12;3:11,13,14,15' -- ./$test -m 400"
            sleep 60
            timeout -s SIGSEGV 10m ./pmix_test -s 4 -n 16 -d '0:0,1,3,5,7,9;1:2,4,6,8;2:10,12;3:11,13,14,15' -- ./$test -m 400
            retcode=$?
            if [ $retcode != 0 ]; then
                if [ $retcode -eq $PMIX_ERR_TIMEOUT ]; then
                    ((num_timeouts++))
                    echo "---------------------------------------------------------------------"
                    echo "----- $test INTERNALLY TIMED OUT; CONTINUING ----------"
                    echo "---------------------------------------------------------------------"
                else
                    echo "---------------------------------------------------------------------"
                    echo "-------------------- $test FAILED ---------------------"
                    echo "---------------------------------------------------------------------"
                    exit -1
                fi
            fi
        else
            echo "---------------------------------------------------------------------"
            echo "-------------------- $test FAILED ---------------------"
            echo "---------------------------------------------------------------------"
            exit -1
        fi
    fi
done

if [ $num_timeouts -eq 0 ]; then
    echo "---------------------------------------------------------------------"
    echo "---------------- ALL V2 TESTS COMPLETED SUCCESSFULLY ----------------"
    echo "---------------------------------------------------------------------"
    exit 0
else
    echo "---------------------------------------------------------------------"
    echo "--------------- ALL V2 TESTS COMPLETED; $num_timeouts TIMED OUT. ----------------"
    echo "---------------------------------------------------------------------"
    exit 0
fi
