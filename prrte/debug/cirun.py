#!/bin/python3.6

from os import environ
from os import error
from subprocess import Popen
from sys import stdout
from time import strftime

# This array specifies the number of slots neeed to run a run.py testcase
# and the set of run.py testcases that need that number of slots.
# The first element in each row is the number of slots, and the remaining 
# elements are the names of the run.py testcases needing that number of slots
# ["1", "direct", "attach", "indirect-prterun"],
#          ["2", "direct-colaunch1", "direct-colaunch2",
#                "attach-colaunch1", "attach-colaunch2"],
# ,
#          ["4", "indirect-colaunch1", "indirect-colaunch2"],
#          ["5", "indirect-multi"]
tests = [ ["3", "direct-multi"]
        ]
numNodes = 0
hostFile = ""

def log(*text):
    """Write a timestamped log message to stdout"""

    messageText = ""
        # The log message may be a combination of strings, numbers and
        # sublists. Append each message fragment to log message based on type
    for fragment in text:
        if (isinstance(fragment, str)):
            messageText = messageText + fragment
        elif (isinstance(fragment, int) or isinstance(fragment, float)):
            messageText = messageText + str(fragment)
        else:
            for frag in fragment:
                if (isinstance(frag, int) or isinstance(frag, float)):
                    messageText = messageText + str(frag) + " "
                else:
                    messageText = messageText + frag + " "
    print(strftime("%X ") + messageText)
    stdout.flush()

# Get necessary environment variables
try:
    numNodes = int(environ["CI_NUM_NODES"])
except KeyError:
    log("ERROR: CI_NUM_NODES environment variable not set.")
    exit(1)
except ValueError:
    log("ERROR: CI_NUM_NODES environment variable value is not numeric.")
    exit(1)
if (numNodes < 3):
    log("ERROR: At least three nodes are required.")
    exit(1)
try:
    hostFile = environ["CI_HOSTFILE"]
except KeyError:
    log("ERROR: CI_HOSTFILE environment variable not set.")

# Read the hostfile specified by CI_HOSTFILE and read the first
# "CI_NUM_NODES" hostnames from the hostfile
try:
    inFile = open(hostFile, "r")
except OSError:
    log("ERROR: Unable to open input hostfile ", hostFile)
    exit(1)
hostList = []
numHosts = 0
for host in inFile:
    hostList.append(host)
    numHosts = numHosts + 1
    if (numHosts == numNodes):
        break
if (len(hostList) != numNodes):
    log("ERROR: Hostfile must contain at least ", numNodes, " hosts.")
    exit(1)
inFile.close()

# For each slot count, create a hostfile with the requested number of slots
# then invoke run.py with the set of test cases to be run with that slot count
maxRC = 0
for run in tests:
    hostFileName = "hostfile_" + run[0] + "_slots"
    try:
        outFile = open(hostFileName, "w")
    except OSError:
        log("ERROR: Unable to write hostfile " + hostFileName)
        exit(1)
    for host in hostList:
        # Strip off the trailing '\n in the hostname when writing hostfile
        outFile.write(host[0:len(host) - 1] + " slots=" + run[0] + "\n")
    outFile.close()
    environ["CI_HOSTFILE"] = hostFileName
    environ["PRTE_MCA_rmaps_base_verbose"] = "100"
    runCommand = []
    runCommand.append("./run.py")
    for commandParm in run[1:]:
        runCommand.append(commandParm)
    runProc = Popen(runCommand)
    runProc.wait(None)
    rc = runProc.returncode
    if (rc > 0):
        log("ERROR***: One or more failures in current subset of tests")
    maxRC = max(maxRC, rc)
exit(maxRC)
