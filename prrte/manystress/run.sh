#!/bin/bash

# Final return value
FINAL_RTN=0

# Number of nodes - for accounting/verification purposes
NUM_NODES=${CI_NUM_NODES:-1}

# Number of cores in each node (default to 20)
NUM_CORES_PER_NODE=${CI_NUM_CORES_PER_NODE:-20}

# Scale test based on number of nodes
TTL_NUM_CORES=$(expr $NUM_NODES \* $NUM_CORES_PER_NODE)

# Enable more verbose output (set VERBOSE=1)
VERBOSE=1

# TJN: Stash some debug bits for now
DEBUG=0

#
# Control params for _run_stress_test
#
#   MAX_PROC -- maximum number of "active" processes,
#               which is used to throttle how many are
#               actively being launched/running at a time.
#               (Generally want to make this less than 'END',
#                so there are subset of active, while trying
#                to get the full set of tasks done.)
#
#               MAX_PROC <= min available number slots on 1 node,
#               because we do not use oversubscription flag.
#
#               Example: If have only 1 node with 8 slots (cores),
#               the max value for MAX_PROC is 8.  If have 2 node for
#               total of 16 slots (cores), MAX_PROC can be up to 16.
#
#   END      -- Upper bound on number of processes to startup.
#               This is used to calculate the total 'NTASKS'
#               that will be run through the system.
#
# Static values for easy testing
# TJN: HACK - Try to see if this changes CI status/hang
#export MAX_PROC=20
#export END=100
#
#---
# Setting 'MAX_PROC' to total number of cores that we can use over all nodes
# Setting 'END'      to 3x number of cores we have to ensure we have many more
#                     tasks than available cores to run on
export MAX_PROC=$TTL_NUM_CORES
export END=$(expr $TTL_NUM_CORES \* 3)

_shutdown()
{
    # ---------------------------------------
    # Cleanup DVM
    # ---------------------------------------
    pterm --dvm-uri file:dvm.uri --num-connect-retries 1000

    exit $FINAL_RTN
}

###########################################################
# Original script by Wael Elwasif (elwasifwr@ornl.gov)
# Adapted to manystress by Thomas Naughton (naughtont@ornl.gov)
#
# Stress testing of launching tasks.
#
# All output sent stdout and "output.txt" file using 'tee',
# with individual prun outputs going to "output.*.txt" files.
#
# Comments on the output files:
#  - "output.txt"
#	Capture overall errors/status
#
#  - "output.<mycount>.txt"
#	Capture prun and app stderr/stdout contents
#       This file is used to assess pass/fail for App.
#
#  - "/tmp/output.sleeper.<host>.<mycount>.<pid>.txt"
#	Capture sleeper (app) output/errors which helps to separate
#       stage when errors occur, i.e., did the app ever run
#       and if so, which ones did/did-not run, which host,
#       what errors did that instance encounter.
#       Really only helpful in debug scenarios.
#       FIXME: Cleanup on remote nodes too.
###########################################################
_run_stress_test()
{
    export HN=$(hostname)

    # TJN: Moved 'MAX_PROC' to top-of-file

    # Array of currently running prun processes
    declare -A pidarr
    declare -A finished
    declare -A all_finished
    declare -A launch_time
    i=0;
    export num_active=0
    export num_finished=0

    export START=1
    # TJN: Moved 'END' to top-of-file
    export NTASKS=$(expr $END - $START)

    echo "#  INFO: NUM_NODES=$NUM_NODES NUM_CORES_PER_NODE=$NUM_CORES_PER_NODE TTL_NUM_CORES=$TTL_NUM_CORES MAX_PROC=$MAX_PROC END=$END" | tee -a output.txt
    echo "# SETUP: MAX_PROC=$MAX_PROC START=$START END=$END NTASKS=$NTASKS" | tee  -a output.txt

    export mycount=0

    export array=($(seq $START $END))
    for val in "${array[@]}"; do

        mycount=$(expr $mycount + 1)

        # XXX: EDIT HERE
        # Task duration 1-10 seconds
        nseconds=$(( ( RANDOM % 10 )  + 1 ))
        #nseconds=45

#        if [ $VERBOSE -gt 0 ] ; then
#            echo "$(date) : $(date +%s) : [$mycount] Launch 'sleep $nseconds'" | tee -a output.txt
#        fi

        #
        # We launch prun (_CMD) in background, but also append
        # the output to logfile (output.txt).  This could get
        # mixed up but we do not care about order of output.
        #
        # NOTE: Final validity checks assume each sleeper outputs
        #       single line containing 'DONE' string.
        #

        #_CMD="prun -n 1 --pmixmca pmix_client_spawn_verbose 100 -- ./sleeper -n ${nseconds} -i ${mycount}"
        _CMD="prun --dvm-uri file:dvm.uri --num-connect-retries 1000 -n 1 -- ./sleeper -n ${nseconds} -i ${mycount}"

        # Launch prun without waiting (**background**)
        #$_CMD 2>&1 | tee -a output.txt &
        $_CMD &> output.${mycount}.txt &
        pid=$!
        st=${PIPESTATUS[0]}
        if [ $st -ne 0 ] ; then
            echo "ERROR: prun failed with $st" | tee -a output.txt
            FINAL_RTN=9
            _shutdown
        fi

        num_active=$(expr $num_active + 1)
        if [ $VERBOSE -gt 0 ] ; then
            echo "$(date) : $(date +%s) : Launched ${val} (pid = $pid) : num_active = $num_active  num_finished = $num_finished (cmd[$mycount]: sleep $nseconds)" | tee -a output.txt
        fi

        # Add child PID and launch-counter-ID to 'pidarr' tracking array
        pidarr[$pid]="${val}";

        # Record child PID and launch-time to 'launch_time' tracking array
        launch_time[$pid]=$(date +%s);

        #echo "$pid STARTED $(date +%s)" | tee -a output.txt

        #echo "${!pidarr[@]}";
        i=$(expr $i+1);

        #wait when we've launched MAX_PROC processes for any one to finish
        while [ $(expr $MAX_PROC - $num_active) -eq 0 ]; do
            do_sleep=1
            for p in ${!pidarr[@]}; do
                # Check if process $p is alive
                kill -0 $p 2>/dev/null;
                if [ $? -ne 0 ] ; then
                    wait $p;
                    #echo "$p FINISHED $(date +%s)" | tee -a output.txt
                    #echo "$p FINISHED" | tee -a output.txt

                    # Decrement number of active processes
                    num_active=$(expr $num_active - 1);

                    # Increment number of finished processes
                    num_finished=$(expr $num_finished + 1);

                    #delete=($p);
                    #pidarr=( "${pidarr[@]/$delete}" );

                    # Record child PID and launcher-counter-ID to 'finished' tracking array
                    finished[$p]=${pidarr[$p]}

                    # Calculate execution time
                    runtime=$(expr $(date +%s) - ${launch_time[$p]} )

                    if [ $VERBOSE -gt 0 ] ; then
                        echo "$(date) : $(date +%s) : Finished ${pidarr[$p]} (pid = $p) : num_active = $num_active  num_finished = $num_finished runtime = $runtime" | tee -a output.txt
                    fi

                    # Remove child PID from 'pidarr' tracking array
                    unset pidarr[$p]

                    do_sleep=0
                    #echo "${!pidarr[@]}";
              fi
            done # for p

            if [ $do_sleep -eq 1 ] ; then
                if [ ${#finished[@]} -gt 0 ]; then
                    keys=( "${!finished[@]}" ) ;
                    k0=${keys[0]};
                    unset finished[$k0];
                fi
                sleep 0.5
            fi

        done # while

    done # for val

    echo "DONE SUBMITTING - now only waiting" | tee -a output.txt
    while [ ${#pidarr[@]} -gt 0 ]; do
        do_sleep=1
        for p in ${!pidarr[@]}; do
            # Check if process $p is alive
            kill -0 $p 2>/dev/null;
            if [ $? -ne 0 ] ; then
                wait $p;
                #echo "$p FINISHED $(date +%s)" | tee -a output.txt
                num_active=$(expr $num_active - 1);
                num_finished=$(expr $num_finished + 1);
                #delete=($p);
                #pidarr=( "${pidarr[@]/$delete}" );
                finished[$p]=${pidarr[$p]}
                if [ $VERBOSE -gt 0 ] ; then
                    echo "$(date) : $(date +%s) : Finished ${pidarr[$p]} (pid = $p) : num_active = $num_active  num_finished = $num_finished" | tee -a output.txt
                fi
                unset pidarr[$p];
                do_sleep=0;
                #echo "${!pidarr[@]}";
            fi;
        done;
        if [ $do_sleep -eq 1 ] ; then
            sleep 0.5
        fi

        if [ $DEBUG -gt 0 ] ; then
            # DEBUG - Adding longer sleep to see if that changes things
            sleep 2
        fi

        for k0 in "${!finished[@]}" ; do
            unset finished[$k0]
        done

        if [ $VERBOSE -gt 0 ] ; then
            # FINISHED: Dump remaining list of "finished"
            if [ ${#finished[@]} -gt 0 ];  then
                # Note: Using same timestamp for all of these print to help sort output
                _time_stamp="$(date) : $(date +%s)"
                for _p in ${!pidarr[@]} ; do
                    echo "$_time_stamp : (count=${#pidarr[@]}) ALIVE-LIST-ITEM: $_p" | tee -a output.txt
                done
            fi
        fi

        if [ $VERBOSE -gt 0 ] ; then
            # ALIVE: Dump remaining list of "still alive"
            if [ ${#pidarr[@]} -gt 0 ];  then
                # Note: Using same timestamp for all of these print to help sort output
                _time_stamp="$(date) : $(date +%s)"
                for _p in ${!pidarr[@]} ; do
                    echo "$_time_stamp : (count=${#pidarr[@]}) ALIVE-LIST-ITEM: $_p" | tee -a output.txt
                done
            fi
        fi

        # DEBUG TO SEE WHAT IS STILL RUNNING?
        if [ $DEBUG -gt 0 ] ; then
            if [ ${#pidarr[@]} -gt 0 ];  then
                which ps
                echo "======= DEBUG (ps prun/tee) ========="
                echo "DBG: USER=$USER"
                # The pid we stash away is from end of the command pipeline
                # (i.e., "prun | tee -a output")
                #ps -aux | grep tee | grep -v grep | grep ^$USER
                ps -aux | grep prun | grep -v grep | grep ^$USER
                echo "======================="
            fi
        fi

    done

    #echo "${!pidarr[@]}"
    #wait ${!pidarr[@]};
    echo "TASKS FINISHED on $HN" | tee -a output.txt
}


# ---------------------------------------
# Bogus case: Check for missing app executable up front
# ---------------------------------------
if [ ! -f "./sleeper" ] ; then
    echo "ERROR: Missing executable './sleeper'"
    echo " INFO: Remember to run './build.sh' first"
    exit 1
fi


# ---------------------------------------
# Start the DVM
# ---------------------------------------
 if [ "x" = "x$CI_HOSTFILE" ] ; then
    hostarg=
 else
    hostarg="--hostfile $CI_HOSTFILE"
fi

if [ $DEBUG -gt 0 ] ; then
    # Enable some DVM logging and show log on exit
    # Must launch DVM in background to get output and not use daemonize.
    #trap "{ echo '== DVM LOG =='; cat DVM.log; echo '======'; }" INT TERM EXIT
    trap "{ echo '== DVM LOG =='; cat DVM.log; echo '======'; echo '== per-run-logfiles =='; more output.*.txt |cat ; echo '=======' ;}" INT TERM EXIT

    debugarg="--prtemca plm_base_verbose 5 --pmixmca pmix_client_spawn_verbose 100 --pmixmca pmix_server_spawn_verbose 10"
else
    debugarg=
 fi

echo " # CMD: prte --no-ready-msg --report-uri dvm.uri $hostarg $debugarg &"
prte --no-ready-msg --report-uri dvm.uri $hostarg $debugarg &



########

# ---------------------------------------
# (Sanity test) Run the test - hostname
# ---------------------------------------
_CMD="prun --dvm-uri file:dvm.uri --num-connect-retries 1000 -n 1 hostname"
echo "======================="
echo "Running hostname: $_CMD"
echo "======================="

# Cleanout any past runs and start fresh output.txt
rm -f output*txt ; touch output.txt 

# FIXME: Need to cleanup on remote nodes too (this only gets local)
rm -f /tmp/output.sleeper.*.txt

for n in $(seq 1 $NUM_ITERS) ; do
    echo -e "--------------------- Execution (hostname): $n"
    $_CMD 2>&1 | tee -a output.txt
    st=${PIPESTATUS[0]}
    if [ $st -ne 0 ] ; then
        echo "ERROR: prun failed with $st"
        FINAL_RTN=1
        _shutdown
    fi
done

echo "---- Done"
# ---------------------------------------
# (Sanity test) Verify the results
# ---------------------------------------
ERRORS=`grep ERROR output.txt | wc -l`
if [[ $ERRORS -ne 0 ]] ; then
    echo "ERROR: (Sanity Check) Error string detected in the output"
    FINAL_RTN=2
    _shutdown
fi

LINES=`wc -l output.txt | awk '{print $1}'`
if [[ $LINES -ne 1 ]] ; then
    echo "ERROR: (Sanity Check) Incorrect number of lines of output. Expected 1. Actual $LINES"
    FINAL_RTN=3
    _shutdown
fi

echo "Sanity check passed"

echo "---- Done"

# ---------------------------------------
# Run the test
# ---------------------------------------
#rm output.txt ; touch output.txt
rm output*txt ; touch output.txt
_run_stress_test


echo "---- Done"
# ---------------------------------------
# Verify the results
# ---------------------------------------
ERRORS=`grep ERROR output.txt | wc -l`
if [[ $ERRORS -ne 0 ]] ; then
    echo "ERROR: Error string detected in the output"
    FINAL_RTN=4
    _shutdown
fi

LINES=`wc -l output.txt | awk '{print $1}'`
if [[ $LINES -eq 0 ]] ; then
    echo "ERROR: No results in output file. Expected >0. Actual $LINES"
    FINAL_RTN=5
    _shutdown
fi

# Check individual output.N.txt files
_outlog_err=0
for _file in `ls -1 output.*.txt` ; do

    # Expect some text in output.N.txt logfiles
    LINES=`wc -l $_file | awk '{print $1}'`
    if [[ $LINES -eq 0 ]] ; then
        echo "ERROR: No results in output file ($_file). Expected >0. Actual $LINES"
        _outlog_err=1
        FINAL_RTN=5
    fi

    # Expect no ERRORs in output.N.txt logfiles
    ERRORS=`grep ERROR $_file | wc -l`
    if [[ $ERRORS -ne 0 ]] ; then
        echo "ERROR: Error string detected in the output ($_file)"
        _outlog_err=1
        FINAL_RTN=5
        echo "=== $_file ==="
        cat $_file
        echo "================================="
    fi

    # Expect no failed in output.N.txt logfiles
    ERRORS=`grep failed $_file | wc -l`
    if [[ $ERRORS -ne 0 ]] ; then
        echo "ERROR: Failed string detected in the output ($_file)"
        _outlog_err=1
        FINAL_RTN=5
        echo "=== $_file ==="
        cat $_file
        echo "================================="
    fi

done
# Check for problems w/ individual output.N.txt files
if [ ${_outlog_err} -ne 0 ] ; then
    echo "ERROR: Bad output from individual outlogs"
    FINAL_RTN=5
    _shutdown
fi

# The 'sleeper' exe prints 'DONE' in its output,
# we check to see that number of instances actually ran.
# If all goes well, for N instances should have N lines of "DONE".
n_expected=$END
n_lines=$(grep DONE output*txt | grep -v TERMINATING | grep -v SUBMITTING |wc -l)

if [ $DEBUG -gt 0 ] ; then
    echo "DEBUG: n_expected=$n_expected"
    echo "DEBUG: n_lines=$n_lines"
fi

if [ "$n_expected" -ne "$n_lines" ] ; then
    echo "FAILURE: $n_expected != $n_lines"
    FINAL_RTN=6

    # Try to dump output files if mismatch in num lines (maybe helpful)
    echo '======'; echo '== per-run-logfiles =='; more output.*.txt |cat ; echo '======='

    _shutdown
fi


echo "---- Done"
if [ $FINAL_RTN == 0 ] ; then
    #echo "SUCCESS: $n_expected == $n_lines"
    echo "SUCCESS"
fi

if [ $DEBUG -eq 0 ] ; then
    # (Unless Debug) Remove prun/sleeper output.*.txt droppings.
    # Note: In debug, atexit handler lists contents for debug purposes
    # so we avoid blowing the files away at end so can list contents.

    echo "Cleanup output.*.txt droppings"
    rm -f output.*.txt

    # FIXME: Need to cleanup on remote nodes too (this only gets local)
    echo "Cleanup /tmp/output.sleeper.*.txt droppings"
    rm -f /tmp/output.sleeper.*.txt
fi

_shutdown

