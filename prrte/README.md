# Test suite for PRRTE

This test suite is meant to be able to be run stand alone or under CI.

All of the tests that are intended for CI must be listed in the  `.ci-tests` and/or `.ci-scale-tests` files.

## Running tests stand alone

 1. Make sure that PRRTE and other required libraries are in your `PATH`/`LD_LIBRARY_PATH`
 2. Drop into a directory:
    - Use the `build.sh` script to build any test articles
    - Use the `run.sh` script to run the test program


## CI Environment Variables

The CI infrastructure defines two environment variables to be used in the test programs. These are defined during the `run.sh` phase not the `build.sh` phase.

 * `CI_HOSTFILE` : Absolute path to the hostfile for this run.
 * `CI_NUM_NODES` : Number of nodes in this cluster.


### Adding a new test for CI

 1. Create a directory with your test.
    - Note: Please make your test scripts such that they can be easily run with or without the CI environment variables.
 2. Create a build script named `build.sh`
    - CI will call this exactly one time.
 3. Create a run script named `run.sh`
    - The script is responsible for (1) starting `prte`, (2) runing your test, and (3) shutting down `prte`.
    - CI wil call this exactly one time (with a timeout in case it hangs).
 4. Add your directory name to the `.ci-tests` and/or `.ci-scale-tests` files in this directory in the order that they should be executed.
    - Note that adding the directory is not sufficient to have CI run the test, it must be in the file.
    - The `.ci-tests` file is used when running at small scales.
    - The `.ci-scale-tests` file is used for running at larger scales. Please be mindful of the time required to run the test and resources needed by the test.
    - Comments (starting with `#`) are allowed.
