# Compare Open MPI to the PMIx Standard

The goal of the functionality in this directory is to compare the OpenPMIx implementation with the PMIx Standard document. A script is used to generate a difference between the two. A 'triage' file is used to identify known differences.

The output from this script can use used to assist the PMIx communities in making sure functionality is matched (as approprate) between the two projects on a regular basis.

## Preparing the directory

Checkout the necessary repos.

By default the script will checkout `master` on both repos.
```shell
./bin/checkout-repos.sh
```

You can set the two envars seen below to customize that branch:
```shell
OPENPMIX_BRANCH='v4.2' PMIX_STANDARD_BRANCH='v4' ./bin/checkout-repos.sh
```

Example:
```shell
shell$ ./bin/checkout-repos.sh
==========================
OpenPMIx      : master
PMIx Standard : master
==========================
========> Cloning OpenPMIx
Cloning into 'openpmix'...
remote: Enumerating objects: 48094, done.
remote: Counting objects: 100% (252/252), done.
remote: Compressing objects: 100% (138/138), done.
remote: Total 48094 (delta 150), reused 183 (delta 114), pack-reused 47842
Receiving objects: 100% (48094/48094), 20.61 MiB | 12.15 MiB/s, done.
Resolving deltas: 100% (36646/36646), done.
========> Cloning PMIx Standard
Cloning into 'pmix-standard'...
remote: Enumerating objects: 3177, done.
remote: Counting objects: 100% (217/217), done.
remote: Compressing objects: 100% (113/113), done.
remote: Total 3177 (delta 115), reused 190 (delta 104), pack-reused 2960
Receiving objects: 100% (3177/3177), 13.20 MiB | 9.48 MiB/s, done.
Resolving deltas: 100% (2063/2063), done.
========> Building PMIx Standard
...
========> Success
```

## Running the script

Command line arguments:
 * `-t` : Triage file (optional)
 * `-v` : Verbose output
 * `-d` : Verbose + Debugging output
 * `--openpmix` : OpenPMIx git checkout (default `scratch/openpmix`)
 * `--standard` : PMIx Standard git checkout (default `scratch/pmix-standard`)

```shell
./bin/compare-with-pmix-standard.py -t etc/openpmix_master-pmix-standard_master.txt
```

Example:
```shell
shell$ ./bin/compare-with-pmix-standard.py -t etc/openpmix_master-pmix-standard_master.txt
--------------------------------------------------
OpenPMIx Directory     : scratch/openpmix
         Git Info.     : master (0b8d0435)
PMIx Standard Directory: scratch/pmix-standard
              Git Info.: master (78956843)
Traige file            : etc/openpmix_master-pmix-standard_master.txt
--------------------------------------------------
   0 : Symbols missing from the PMIx Standard defined by OpenPMIx
   0 : Symbols missing from OpenPMIx defined by the PMIx Standard
 210 : Symbols in triage file
   0 : Symbols in triage file that were not missing.
--------------------------------------------------
Success! No missing symbols found!
```

## Update the triage files

Edit the file in `etc/`

## Update the branches in the script

The OpenPMIx and PMIx Standard branches are defined in the following wrapper scripts.
 * `bin/run-v4-check.sh` : Check OpenPMIx against the v4 PMIx Standard
 * `bin/run-v5-check.sh` : Check OpenPMIx against the v5 PMIx Standard

Look for the `OPENPMIX_BRANCH` and `PMIX_STANDARD_BRANCH` envars in those scripts. Adjusting the values of these envars will select the respective branch in that repository.

## Run in the Docker environment

Example to run the full v5 check using your local version of `pmix-tests`:
```shell
docker run --rm -v /host/path/to/pmix-tests:/home/pmixer/pmix-tests jjhursey/pmix-standard /bin/bash -c "cd /tmp ; /home/pmixer/pmix-tests/check-standard/bin/run-v5-check.sh"
```

