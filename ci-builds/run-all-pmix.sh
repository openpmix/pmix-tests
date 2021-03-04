#!/bin/bash


#--------------------------------
# Location of the PMIx checkout
#--------------------------------
if [ -z "${_PMIX_CHECKOUT}" ]; then 
    export _PMIX_CHECKOUT=${HOME}"/openpmix"
fi

if [ ! -d ${_PMIX_CHECKOUT} ] ; then
    echo "Error: No PMIx checkout in ${_PMIX_CHECKOUT}"
    echo "Set the _PMIX_CHECKOUT envar to your pmix checkout"
    exit 1
fi

#--------------------------------
# All of the builds sorted
# Builds must start with at least a 2 digit number (`07`)
#--------------------------------
ALL_BUILDS=(`find pmix -type f | grep -E '.*/[0-9]+' | sort -n`)

echo "----------------------------------"
echo "Special PMIx Build Configurations"
echo ""
echo "All builds defined in pmix-tests:"
echo "  https://github.com/openpmix/pmix-tests/tree/master/ci-builds"
echo "----------------------------------"

LEN=${#ALL_BUILDS[@]}
for (( i=0; i < ${LEN}; i++ )); do
    if [ -x ${ALL_BUILDS[$i]} ] ; then
        echo `date`" --------- Build "$((i+1))" of $LEN : ${ALL_BUILDS[$i]}"

        # Build directory
        export _BUILD_DIR=`mktemp -d $HOME/tmp-build-XXXXX`
        echo `date`" --------- Build "$((i+1))" of $LEN : Building to: $_BUILD_DIR"
        _OUTPUT_FILE=${_BUILD_DIR}"/output.txt"

        # Run the test
        SECONDS=0
        CMD="./"${ALL_BUILDS[$i]}
        $CMD 1> $_OUTPUT_FILE 2>&1

        if [ $? -eq 0 ] ; then
            echo `date`" --------- Build "$((i+1))" of $LEN : Success in $SECONDS second(s)"
            echo `date`" --------- Build "$((i+1))" of $LEN : Cleanup"
            rm -rf ${_BUILD_DIR}
        else
            echo `date`" --------- Build "$((i+1))" of $LEN : FAILED in $SECONDS second(s)"
            cat $_OUTPUT_FILE
            exit 1
        fi
    else
        echo `date`" --------- Build "$((i+1))" of $LEN : ${ALL_BUILDS[$i]}"
        echo "Skip: ${ALL_BUILDS[$i]}"
    fi
done

exit 0

    
