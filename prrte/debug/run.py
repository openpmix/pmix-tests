#!/bin/python3.6

from os import environ
from os import error
from os import remove
from subprocess import call
from subprocess import CalledProcessError
from subprocess import check_call
from subprocess import DEVNULL
from subprocess import PIPE
from subprocess import STDOUT
from subprocess import Popen
from sys import argv
from sys import stdout
from threading import Timer
from time import sleep
from time import strftime

SYS_DAEMON_NEEDED = 0x01
ATTACH_TARGET_NEEDED = 0x02
MULTINODE_TEST = 0x04
ATTACH_WAITTIME = 10.0

# Set of tests to run. There is one row per test. The columns in the row are:
# col[0]: Test case name, labels the testcase and is included in output
#         filenames
# col[1]: Flags for special setup processing for testcase execution
#         SYS_DAEMON_NEEDED: Start prte system deamon before starting testcase
#         ATTACH_TARGET_NEEDED: Launch prterun session to attach to
#         MULTINODE_TEST: Specify hostfile when starting daemon
# col[2]: Path to main executable for testcase
# col[3-n]: Command line arguments for testcase
#
# A multinode testcase includes MULTINODE_TEST in it's testcase flags settings
tests = [ ["direct", SYS_DAEMON_NEEDED, "./direct"],
            # This test requires a hostfile with 3 slots per node
          ["direct-multi", SYS_DAEMON_NEEDED | MULTINODE_TEST, "./direct-multi",
                  "--app-pernode", "2", "--app-np", "6"],
            # This test requires a hostfile with 2 slots per node
          ["direct-colaunch1", SYS_DAEMON_NEEDED | MULTINODE_TEST, "./direct-multi",
                  "--app-pernode", "2", "--app-np", "6",
                  "--daemon-colocate-per-node", "1"],
            # This test requires a hostfile with 2 slots per node
          ["direct-colaunch2", SYS_DAEMON_NEEDED | MULTINODE_TEST, "./direct-multi",
                  "--app-pernode", "2", "--app-np", "6",
                  "--daemon-colocate-per-proc", "1"],
            # This test requires a hostfile with 5 slots per node
          ["indirect-multi", MULTINODE_TEST, "./indirect-multi",
                  "--num-nodes", "$numNodes", "--hostfile", "$hostfile",
                  "prterun", "--hostfile", "$hostfile", "--np", "12", "./hello"],
            # This test requires a hostfile with 4 slots per node
          ["indirect-colaunch1", MULTINODE_TEST, "./indirect-multi",
                  "--daemon-colocate-per-node", "1", "prterun", "--hostfile", "$hostfile",
                  "--np", "12", "./hello"],
            # This test requires a hostfile with 4 slots per node
          ["indirect-colaunch2", MULTINODE_TEST, "./indirect-multi",
                  "--daemon-colocate-per-proc", "1", "prterun", "--hostfile", "$hostfile",
                  "--np", "12", "./hello"],
            # This test requires a hostfile with 2 slots per node
          ["attach-colaunch1", ATTACH_TARGET_NEEDED | MULTINODE_TEST, "./attach",
                  "--daemon-colocate-per-node", "1", "$attach-namespace"],
            # This test requires a hostfile with 2 slots per node
          ["attach-colaunch2", ATTACH_TARGET_NEEDED | MULTINODE_TEST, "./attach",
                  "--daemon-colocate-per-proc", "1", "$attach-namespace"]
# These testcases are not working at this point, so comment them out for now
#         ["attach", ATTACH_TARGET_NEEDED, "./attach", "$attach-namespace"],
#         ["indirect-prterun", 0, "./indirect", "prterun", "-n", "2",
#                 "./hello", "10"],
        ]
# Commands to start prte system daemons for multi-node tests. The testcase
# name (array element 0) must match the name of the testcase in the tests array
# and the name of the hostfile should be the same as the hostfile in the 
# testcase run command, if any in the tests array.
hostfileDaemons = [ ["direct-multi", "prte", "--system-server", "--hostfile",
                            "$hostfile", "--report-uri", "+"],
                    ["direct-colaunch1", "prte", "--system-server", "--hostfile",
                            "$hostfile", "--report-uri", "+"],
                    ["direct-colaunch2", "prte", "--system-server", "--hostfile",
                            "$hostfile", "--report-uri", "+"]
                  ]

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

def testcaseTimer(proc, waitTimeout):
    """Timer thread used to detect if a testcase has reached it's time limit."""

        # Testcase timeout limit has been reached.
        # If the testcase process did not complete, kill it now
    childStatus = proc.poll()
    if (childStatus == None):
        log("ERROR: Testcase execution timed out, kill pid ", proc.pid)
        proc.kill()

        # Get testcase completion status. 0=success, anything else=failure
    proc.wait(waitTimeout)
    return proc.returncode

def shutdownPrte(prteProcess, waitTimeout):
    """Shut down a prte system daemon"""
    ptermProcess = Popen(["pterm", "--system-server-only"],
                          stdout=DEVNULL, stderr=DEVNULL)
    rc = prteProcess.wait(waitTimeout)
    ptermProcess.wait(waitTimeout)
    return rc

def writeStdio(stdoutFile, stdoutText, stderrFile, stderrText):
    """Write stdout and stderr test to output files"""
    for text in stdoutText:
        stdoutFile.write(text)
    for text in stderrText:
        stderrFile.write(text)

def run(selected, testCases):
    """Driver to run individual test cases specified in testCases"""

      # Run the individual testcases. If a test case fails, that results
      # in an exception which logs that test case failure and then the
      # next test case is run.
    global testcases, failures, failedTests
    prteProcess = None
    rc = 0
    testcaseTimeout = 120.0
    daemonDelay = 10.0
    waitTimeout = 10.0
    hostFile = "./hostfile"
    try:
        hostFile = environ["CI_HOSTFILE"]
    except KeyError:
        pass
    numNodes = 1
    try:
        numNodes = int(environ["CI_NUM_NODES"])
    except KeyError:
        pass
    except ValueError:
        log("ERROR: CI_NUM_NODES environment variable value is not numeric.")
        exit(1)
    try:
        testcaseTimeout = float(environ["TC_TIMEOUT"])
    except KeyError:
        pass
    except ValueError:
        log("ERROR: TC_TIMEOUT environment variable value is not numeric.")
        exit(1)
    try:
        waitTimeout = float(environ["TC_WAIT_TIMEOUT"])
    except KeyError:
        pass
    except ValueError:
        log("ERROR: TC_WAIT_TIMEOUT environment variable value is not numeric.")
        exit(1)
    try:
        daemonDelay = float(environ["TC_DAEMON_DELAY"])
    except KeyError:
        pass
    except ValueError:
        log("ERROR: TC_DAEMON_DELAY environment variable value is not numeric.")
        exit(1)

    log("Testcase timeout limit is ", testcaseTimeout, " seconds.")
    log("Process wait timeout limit is ", waitTimeout, " seconds.")
    log("Daemon startup delay is ", daemonDelay, " seconds.")
    for testCase in testCases:
        if ((selected != "**all**") and (selected != testCase[0])):
            continue
        log("Initialize testcase ", testCase[0])
          # Testcases can fail if there are leftover /tmp/prte* directories from
          # previous runs that did not properly clean up. Solve this by
          # deleting any such directories owned by this user
        call("rm -rf /tmp/prte*", shell=True)
        testcases = testcases + 1
        prteProcess = None
        attachProcess = None
        attachTimerThread = None
        prteNamespace = ""
        attachNamespace = ""
  
          # If the test requires a persistent prte daemon, start it here
        if ((testCase[1] & SYS_DAEMON_NEEDED) != 0):
            if ((testCase[1] & MULTINODE_TEST) == 0):
                prteProcess = Popen(["prte", "--report-uri", "+",
                                    "--system-server"], stdout=PIPE,
                                    stderr=STDOUT)
            else:
                  # This is a multinode testcase (with hostfile). Find the
                  # matching prte daemon startup command and start the daemon.
                prteCommand = None
                for daemonCmd in hostfileDaemons:
                    if (daemonCmd[0] == testCase[0]):
                        prteCommand = daemonCmd[1:]
                        break
                if (prteCommand == None):
                    log("Multi-node prte daemon command not found for ",
                        testCase[0])
                    failures = failures + 1
                    failedTests.append(testCase[0])
                    rc = 1
                    continue
                for idx, testArg in enumerate(prteCommand):
                    if (testArg == "$hostfile"):
                        prteCommand[idx] = hostFile
                log("Starting multi-node prte ", prteCommand)
                prteProcess = Popen(prteCommand, stdout=PIPE, stderr=STDOUT)

               # The namespace is the first ';' delimited token in the first
               # line # of prte daemon output. This read also serves as a
               # barrier to ensure prte is started before running the test
            pipe = prteProcess.stdout
            prteOutput = pipe.readline()
            line = str(object=prteOutput, encoding="ascii")
            semiIndex = line.find(";")
            if (semiIndex != -1):
                prteNamespace = line[0:semiIndex]
            log("prte namespace: ", prteNamespace)

              # Delay to allow daemon to fully initialize
            sleep(daemonDelay)

          # If the test requires an application to attach to, start the app here
        if ((testCase[1] & ATTACH_TARGET_NEEDED) != 0):
            if ((testCase[1] & MULTINODE_TEST) != 0):
                attachProcess = Popen(["prterun", "--report-uri", "+",
                                      "--hostfile", hostFile,
                                      "--map-by", "node", "--rank-by", "slot",
                                      "-n", str(numNodes * 2), "hello",
                                      str(int(ATTACH_WAITTIME))], 
                                      stdout=PIPE, stderr=STDOUT)
            else:
                attachProcess = Popen(["prterun", "--report-uri", "+",
                                      "-n", "2", "hello",
                                      str(int(ATTACH_WAITTIME))], 
                                      stdout=PIPE, stderr=STDOUT)
              # The namespace is the first ';' delimited token in the first line
              # of prterun output. This read also serves as a barrier to
              # ensure prterun is started before running the test
            pipe = attachProcess.stdout
            attachOutput = pipe.readline()
            line = str(object=attachOutput, encoding="ascii")
            semiIndex = line.find(";")
            if (semiIndex != -1):
                attachNamespace = line[0:semiIndex]
                  # --report-uri namespace string contains trailing task index
                  # that must be removed
                dotIndex = attachNamespace.rfind(".")
                if (dotIndex != -1):
                    attachNamespace = attachNamespace[0:dotIndex]
            log("attach target namespace: ", attachNamespace)

              # Delay to allow application to fully initialize
            sleep(daemonDelay)

              # Create a thread to monitor the attach target and kill it if it
              # exceeds its allotted execution time
            attachTimerThread = Timer(testcaseTimeout, testcaseTimer,
                                args=(attachProcess, waitTimeout))
            attachTimerThread.daemon = True
            attachTimerThread.start()

          # If the testcase command arguments contain symbolic names then
          # replace them with actual values here
        for idx, testArg in enumerate(testCase):
            if (testArg == "$namespace"):
                testCase[idx] = prteNamespace
            if (testArg == "$attach-namespace"):
                testCase[idx] = attachNamespace
            if (testArg == "$hostfile"):
                testCase[idx] = hostFile
            if (testArg == "$numNodes"):
                testCase[idx] = str(numNodes)

        stdoutPath = str.format("{}.stdout", testCase[0])
        stderrPath = str.format("{}.stderr", testCase[0])
        origStdoutPath = stdoutPath + ".orig"
        origStderrPath = stderrPath + ".orig"
          # Delete old testcase output files. Missing files is not an error
        for path in [stdoutPath, stderrPath, origStdoutPath, origStderrPath]:
            try:
                remove(path)
            except FileNotFoundError as e:
                continue
        stdoutFile = open(stdoutPath, "w+")
        stderrFile = open(stderrPath, "w+")
        origStdoutFile = open(origStdoutPath, "w+")
        origStderrFile = open(origStderrPath, "w+")
        try:
              # Create the test case process
            testProcess = Popen(testCase[2:], stdout=PIPE, stderr=PIPE,
                                universal_newlines=True)
            log("Starting testcase pid ", testProcess.pid, ": '", testCase[2:],
                "'")

              # Create a thread to monitor the testcase and kill it if it
              # exceeds its alloted execution time
            timerThread = Timer(testcaseTimeout, testcaseTimer,
                                args=(testProcess, waitTimeout))
            timerThread.daemon = True
            timerThread.start()

              # Trap UnicodeDecodeError since stdio output from target process may
              # contain invalid characters in text strings
            stdoutText = ""
            stderrText = ""
            try:
                  # Note that testProcess.communicate blocks until the process exits
                stdoutText, stderrText = testProcess.communicate()
            except UnicodeDecodeError as e:
                # If this exception occurs, stdoutText and stderrText are not updated
                log("ERROR: Testcase ", testCase[0],
                    " has invalid stdio data 0x", bytearray([e.object[e.start]]).hex(),
                    " at offsets ", e.start, " to ", e.end)
                failures = failures + 1
                failedTests.append(testCase[0])
                if (prteProcess != None):
                    shutdownPrte(prteProcess, waitTimeout)
                rc = 1
                continue
    
              # Get test case exit code first to avoid leaving a zombie process
            runRC = testProcess.wait(waitTimeout)

              # Test case complete, cancel the testcase timer
            timerThread.cancel()

              # Test case has terminated, clean up related processes here
            if ((testCase[1] & ATTACH_TARGET_NEEDED) != 0):
                attachTimerThread.cancel()
                  # The attach target runs for approximately ATTACH_WAITTIME
                  # seconds, so if it hasn't terminated yet then wait that
                  # number of seconds to give it a chance to exit normally
                targetStatus = attachProcess.poll()
                if (targetStatus == None):
                    sleep(ATTACH_WAITTIME)

                  # If a target application was needed and it did not terminate
                  # then kill it here.
                targetStatus = attachProcess.poll()
                if (targetStatus == None):
                    log("Attach target pid ", attachProcess.pid, 
                        " did not terminate, killing target")
                    attachProcess.kill()
                    writeStdio(stdoutFile, stdoutText, stderrFile, stderrText)
                    failures = failures + 1
                    failedTests.append(testCase[0])
                    rc = 1
                    continue

              # If this testcase started a prte daemon, shut it down here
            if ((testCase[1] & SYS_DAEMON_NEEDED) != 0):
                prteRC = shutdownPrte(prteProcess, waitTimeout)
                if (prteRC != 0):
                    log("ERROR: prte daemon failed with rc=", prteRC)
                    failures = failures + 1
                    failedTests.append(testCase[0])
                    continue

              # Make sure testcase exited successfully
            if (runRC != 0):
                log("ERROR: Test failed with return code ", runRC)
                if (len(stderrText) > 0):
                    log("Testcase stderr is:\n", stderrText)
                writeStdio(stdoutFile, stdoutText, stderrFile, stderrText)
                failures = failures + 1
                failedTests.append(testCase[0])
                rc = 1
                continue

               # Save original stdout and stderr in case they are needed for

            origStdout = Popen("/bin/cat", stdin=PIPE, stdout=origStdoutFile)

              # Write stdout to backup file
            pipe = origStdout.stdin
            for text in stdoutText:
                pipe.write(text.encode(encoding="UTF-8"))
            pipe.close()
            origStdout.wait(waitTimeout)
            origStderr = Popen("/bin/cat", stdin=PIPE, stdout=origStderrFile)

              # Write stderr to backup file
            pipe = origStderr.stdin
            for text in stderrText:
                pipe.write(text.encode(encoding="UTF-8"))
            pipe.close()
            origStderr.wait(waitTimeout)

            log("Verify stdout/stderr for testcase ", testCase[0])
              # Get the testcase stdout and stderr output, split that output
              # into '\n'-delimited newlines, and sort the resulting text
              # arrays by the line prefix tag
            stdoutText = sorted(stdoutText.splitlines(keepends=True))
            stderrText = sorted(stderrText.splitlines(keepends=True))

              # Filter stdout and stderr, translating variable text like
              # namespaces to constant strings so that comparison to baseline
              # files can be successfully done
            stdoutFilter = Popen("./tcfilter", stdin=PIPE, stdout=stdoutFile)

              # Send stdout text to filter
            pipe = stdoutFilter.stdin
            for text in stdoutText:
                pipe.write(text.encode(encoding="UTF-8"))
            pipe.close()
            stdoutFilter.wait(waitTimeout)

            stderrFilter = Popen("./tcfilter", stdin=PIPE, stdout=stderrFile)

              # Send stderr text to filter
            pipe = stderrFilter.stdin
            for text in stderrText:
                  #####################################################################
                  # This check for the Epoll string is a hack to bypass an error      #
                  # reported in PMIx issue 2140 so testcases will not fail because of #
                  # this error. This test should be removed once issue 2140 is fixed  #
                  #####################################################################
                if (text.find("[warn] Epoll ADD(") == -1):
                    pipe.write(text.encode(encoding="UTF-8"))
            pipe.close()
            stderrFilter.wait(waitTimeout)

              # Compare stdout and stderr output to corresponding baselines
            diffProcess = Popen(["./compare.py", stdoutPath,
                                 stdoutPath + ".baseline"])
            diffProcess.wait(waitTimeout)
            if (diffProcess.returncode != 0):
                log("ERROR: testcase ", testCase[0],
                    " stdout does not match baseline")
                failures = failures + 1
                failedTests.append(testCase[0])
                rc = 1
                continue

            diffProcess = Popen(["./compare.py", stderrPath,
                                 stderrPath  + ".baseline"])
            diffProcess.wait(waitTimeout)
            if (diffProcess.returncode != 0):
                log("ERROR: testcase ", testCase[0],
                    " stderr does not match baseline")
                failures = failures + 1
                failedTests.append(testCase[0])
                rc = 1
                continue
        except CalledProcessError as e:
            log("ERROR: Command ", "'", e.cmd, "' failed with return code ",
                e.returncode)
            failures = failures + 1
            failedTests.append(testCase[0])
            rc = 1
            if (prteProcess != None):
                shutdownPrte(prteProcess, waitTimeout)

        except error as e:
            log("ERROR: Command", "'", testCase, "' failed: ", e.strerror)
            failures = failures + 1
            failedTests.append(testCase[0])
            rc = 1
            if (prteProcess != None):
                shutdownPrte(prteProcess, waitTimeout)

        log("Completed testcase ", testCase[0])

    return rc

failedTests = []
failures = 0
testcases = 0
rc = -1
if (len(argv) > 1):
    for idx, testCase in enumerate(argv):
        if (idx > 0):
            rc = max(rc, run(testCase, tests))
else:
    # Since testcases have different setups, the complete set can no longer be
    # run in a single invocation of run.py
    log("ERROR: run.py must be invoked with at least one test case name specified.")
    exit(1)
log("Ran " + str(testcases) + " tests, " + str(failures) + " failed")
if (failures > 0):
    log("Failed tests:")
    for failedTest in failedTests:
        log("    ", failedTest)
exit(rc)
