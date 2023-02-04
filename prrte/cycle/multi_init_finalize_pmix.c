/*
 * Copyright (c) 2019      IBM, Inc.  All rights reserved.
 * Copyright (c) 2023      Nanook Consulting.  All rights reserved.
 * $COPYRIGHT$
 *
 * Additional copyrights may follow
 *
 * $HEADER$
 *
 */

#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>

#include <pmix.h>


int main(int argc, char **argv)
{
    pmix_status_t rc;
    pid_t pid;
    char hostname[1024];
    pmix_proc_t myproc;
    int n, niters = 2;
    bool dofence = true;

    pid = getpid();
    gethostname(hostname, 1024);

    for (n=1; n < argc; n++) {
        if (0 == strncasecmp(argv[n], "--iter", 6)) { // accept iter or iters
            niters = strtoul(argv[n+1], NULL, 10);
            ++n; // skip over argument
        } else if (0 == strcasecmp(argv[n], "--no-fence")) {
            dofence = false;
        }
    }

    for (n=0; n < niters; n++) {
        if( PMIX_SUCCESS != (rc = PMIx_Init(&myproc, NULL, 0)) ) {
            fprintf(stderr, "ERROR: PMIx_Init failed (%lu on %s): %d\n",
                    (unsigned long)pid, hostname, rc);
            exit(1);
        }

        if (dofence) {
            rc = PMIx_Fence(NULL, 0, NULL, 0);
            if (PMIX_SUCCESS != rc) {
                fprintf(stderr, "ERROR: PMIx_Fence failed (%lu on %s): %d\n",
                        (unsigned long)pid, hostname, rc);
                exit(1);
            }
        }

        if (PMIX_SUCCESS != (rc = PMIx_Finalize(NULL, 0))) {
            fprintf(stderr, "ERROR: PMIx_Finalize failed (%lu on %s): %d (%s)\n",
                    (unsigned long)pid, hostname, rc, PMIx_Error_string(rc));
            exit(1);
        }
    }

    fflush(stderr);
    return(0);
}
