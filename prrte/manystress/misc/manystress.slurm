#!/bin/bash
#SBATCH --job-name=manystress
#SBATCH --output=result-manystress.%j.txt
#
#SBATCH --nodes=10
#SBATCH --time=10:00

#
# (See: https://github.com/SchedMD/slurm/blob/master/contribs/torque/generate_pbs_nodefile.pl)
#
export CI_HOSTFILE=`$HOME/bin/generate_pbs_nodefile.pl`

export CI_NUM_NODES=$SLURM_JOB_NUM_NODES

#export CI_NUM_CORES_PER_NODE=8
export CI_NUM_CORES_PER_NODE=$(echo $SLURM_TASKS_PER_NODE | awk -F\( '{print $1}')

echo "DBG: CI_NUM_CORES_PER_NODE=$CI_NUM_CORES_PER_NODE"

if [ ! -f "$CI_HOSTFILE" ] ; then
    echo "ERROR: Missing CI_HOSTFILE '$CI_HOSTFILE'"
    exit 1
fi

if [ "$CI_NUM_NODES" -lt 1 ] ; then
    echo "ERROR: Missing or too few CI_NUM_NODES '$CI_NUM_NODES'"
    exit 1
fi

echo "==== $CI_HOSTFILE ===="
cat "$CI_HOSTFILE"
echo "======================"
echo "==== CI_NUM_NODES ===="
echo $CI_NUM_NODES
echo "======================"
echo "==== CI_NUM_CORES_PER_NODE ===="
echo $CI_NUM_CORES_PER_NODE
echo "======================"

echo "START: `date`"

echo "#########################"
echo " Start CI script: 'run.sh'"
echo "#########################"
./run.sh

echo "DONE: `date`"
