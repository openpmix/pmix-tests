README
------

Runs many instances of a `sleeper` exe with random sleep time.
The number of instances is variable and is intended to be more
than can run all at once.

The script start up to a given threshold, and then starts more as tasks
complete.  Since the `sleeper` exe's have different sleep times, the
available slots for running changes and stress tests the mapping and other
parts of the system.

See the `END` and `MAX_PROC` variables in the middle of the script for
setting the above thresholds.  Currently, this is being set based on the
number of resources (nodes and cores):
 - `MAX_PROC` is set to `CI_NUM_NODES` times a `NUM_CORES_PER_NODE`
 - `END` is set to `n` x total number of cores (e.g., 3 x `MAX_PROC`)
The intent is to have much more work than available cores to keep things busy.

 - Note: Use `CI_NUM_CORES_PER_NODE` env var to override the default number
   of cores per node.  Since this is non-standard, we assume a default but
   adding this in case we need to set it via the CI/CD environment.

Environment Variables
----------------------

The test assumes/uses the following environment variables.

 - `CI_NUM_NODES` -- number of nodes available for use by test
 - `CI_HOSTFILE`  -- hostfile with node names for use by test
 - `CI_NUM_CORES_PER_NODE` -- (optional) number of cores per node


Outputs/DEBUG
-------------

Upon success, the return value will be 0 and a "Success" string is printed
to console.

In `run.sh`, setting `DEBUG=1` enables more debug output and some logging
of prte daemon output.  It also shows contents of various "output" files
used in test to help diagnose where failures might be occuring.  Additionally,
if DEBUG is enabled a shell atexit handler lists the contents of the various
logs/output files to help show state of things.

Briefly, the output files are as follows:
  - "output.txt"
        Capture overall status/error of test.

  - "output.<count>.txt"
        Capture prun and sleeper app stderr/stdout contents
        This file is used to assess pass/fail for sleeper app.
        The "<count>" is count of (n-th) app instance being started.

  - "/tmp/output.sleeper.<host>.<count>.<pid>.txt"
        Capture sleeper (app) output/errors which helps to separate
        stage when errors occur, i.e., did the app ever run
        and if so, which ones did/did-not run, on which host,
        what errors did that instance encounter.
        Really only helpful in debug scenarios.
        The "<host>"  is hostname where app instance started.
        The "<count>" is count of (n-th) app instance being started.
        The "<pid>"   is process-ID of app instance started.

  - "DVM.log"
        (DEBUG only) Output from prte daemon


TODO
----
 - NOTE: The validty checks do few grep's of output file
   to check if number of expected matches the config for
   that run.  A bit fragile, and likely needs improvement.

