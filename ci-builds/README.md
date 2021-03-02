# Special Builds for PMIx/PRRTE CI

These are supported build configurations that are not regularly tested by other CI projects.

## Reproducing a Failure

All of the builds run in the same container that we run the cross version testing. [jjhursey/pmix-xver-tester](https://hub.docker.com/r/jjhursey/pmix-xver-tester)

To recreate a failure you will need to spin up a container instance and run the approprate script. There are a couple of envars that influence behavior that you will wna tot be aware of:
 * `_PMIX_CHECKOUT` : Points to the absolute path of the `openpmix` checkout inside the container
 * `_PRRTE_CHECKOUT` : Points to the absolute path of the `prrte` checkout inside the container (PRRTE builds only)
 * `_BUILD_DIR` : (Optional) set a specific temporary location for the build. By default this will be set to a temporary directory in `$HOME`

### Example 1: Checkout branch inside the container

Checkout your branch (using `master` below) and re-run a specific build.

```
$ docker run --rm -it jjhursey/pmix-xver-tester bash
(docker)$ cd $HOME
(docker)$ git clone -b master https://github.com/openpmix/openpmix.git
(docker)$ export _PMIX_CHECKOUT=$HOME/openpmix
(docker)$ cd pmix-tests/ci-builds/
(docker)$ ./pmix/03-build-python.sh 
```

```
$ docker run --rm -it jjhursey/pmix-xver-tester bash
(docker)$ cd $HOME
(docker)$ git clone -b master https://github.com/openpmix/openpmix.git
(docker)$ git clone -b master https://github.com/openpmix/prrte.git
(docker)$ export _PMIX_CHECKOUT=$HOME/openpmix
(docker)$ export _PRRTE_CHECKOUT=$HOME/prrte
(docker)$ cd pmix-tests/ci-builds/
(docker)$ ./prrte/01-build-hwloc1x.sh
```

### Example 2: Import branch from host

In these examples we are volume mounting our PMIx (and PRRTE) checkouts from the host. This allows you to easily edit the branch outside of the container then use the container as a build box.

Replace `/home/me/my-openpmix` with the full path to your checkout of `openpmix` on your host system.

```
$ docker run --rm -it -v /home/me/my-openpmix:/home/pmixer/openpmix jjhursey/pmix-xver-tester bash
(docker)$ cd $HOME
(docker)$ export _PMIX_CHECKOUT=$HOME/openpmix
(docker)$ cd pmix-tests/ci-builds/
(docker)$ ./pmix/03-build-python.sh 
```

Replace `/home/me/my-openpmix` with the full path to your checkout of `openpmix` on your host system.
Replace `/home/me/my-prrte` with the full path to your checkout of `prrte` on your host system.

```
$ docker run --rm -it -v /home/me/my-openpmix:/home/pmixer/openpmix -v /home/me/my-prrte:/home/pmixer/prrte jjhursey/pmix-xver-tester bash
(docker)$ cd $HOME
(docker)$ export _PMIX_CHECKOUT=$HOME/openpmix
(docker)$ export _PRRTE_CHECKOUT=$HOME/prrte
(docker)$ cd pmix-tests/ci-builds/
(docker)$ ./prrte/01-build-hwloc1x.sh
```


## Adding a Build

To add a build you need to add an executable script to either the `pmix` or `prrte` subdirectory (depending on which project you want it to run against).
The script must be prefixed with at least a 2 digit number. This number is used to define the ordering of the scripts.
It is suggested that you start from an existing script.

If the script is not marked as executable then it is skipped. This is the easiest was to disable a problematic build.

The script should return `0` on success and any other return code on error.
On success the output is supressed when reporting the results.
On failure all of the output produced by the script is displayed, and no further build are run.
