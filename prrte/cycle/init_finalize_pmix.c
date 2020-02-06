/*
 * Copyright (c) 2019      IBM, Inc.  All rights reserved.
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

    pid = getpid();
    gethostname(hostname, 1024);

    if( PMIX_SUCCESS != (rc = PMIx_Init(&myproc, NULL, 0)) ) {
        fprintf(stderr, "ERROR: PMIx_Init failed (%lu on %s): %d\n", (unsigned long)pid, hostname, rc);
        exit(1);
    }

    if (PMIX_SUCCESS != (rc = PMIx_Finalize(NULL, 0))) {
        fprintf(stderr, "ERROR: PMIx_Finalize failed (%lu on %s): %d (%s)\n", (unsigned long)pid, hostname, rc, PMIx_Error_string(rc));
        exit(1);
    }

    fflush(stderr);
    return(0);
}
