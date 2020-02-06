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
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <time.h>

#include <pmix.h>

static pmix_proc_t myproc;

int main(int argc, char **argv)
{
    pmix_status_t rc;
    pid_t pid;
    char hostname[1024];
    pmix_value_t *val = NULL;
    pmix_proc_t proc_wildcard;
    int job_size;
    int local_size, local_rank;

    pid = getpid();
    gethostname(hostname, 1024);

    if( PMIX_SUCCESS != (rc = PMIx_Init(&myproc, NULL, 0)) ) {
        fprintf(stderr, "ERROR: PMIx_Init failed (%lu on %s): %d\n", (unsigned long)pid, hostname, rc);
        exit(1);
    }

    PMIX_PROC_CONSTRUCT(&proc_wildcard);
    (void)strncpy(proc_wildcard.nspace, myproc.nspace, PMIX_MAX_NSLEN);
    proc_wildcard.rank = PMIX_RANK_WILDCARD;

    // Job size
    if( PMIX_SUCCESS != (rc = PMIx_Get(&proc_wildcard, PMIX_JOB_SIZE, NULL, 0, &val)) ) {
        fprintf(stderr, "ERROR: PMIx_Get(PMIX_JOB_SIZE) failed (%lu on %s): %d\n", (unsigned long)pid, hostname, rc);
        exit(1);
    }
    job_size = val->data.uint32;
    PMIX_VALUE_RELEASE(val);

    // Number of ranks on this node
    if( PMIX_SUCCESS != (rc = PMIx_Get(&proc_wildcard, PMIX_LOCAL_SIZE, NULL, 0, &val)) ) {
        fprintf(stderr, "ERROR: PMIx_Get(PMIX_LOCAL_SIZE) failed (%lu on %s): %d\n", (unsigned long)pid, hostname, rc);
        exit(1);
    }
    local_size = val->data.uint32;
    PMIX_VALUE_RELEASE(val);

    // My local rank on this node
    if( PMIX_SUCCESS != (rc = PMIx_Get(&myproc, PMIX_LOCAL_RANK, NULL, 0, &val)) ) {
        fprintf(stderr, "ERROR: PMIx_Get(PMIX_LOCAL_RANK) failed (%lu on %s): %d\n", (unsigned long)pid, hostname, rc);
        exit(1);
    }
    local_rank = val->data.uint16;
    PMIX_VALUE_RELEASE(val);

    printf("%d/%d [%d/%d] Hello World from %s (pid %lu)\n",
           myproc.rank, job_size,
           local_rank, local_size,
           hostname, (unsigned long)pid);


    if (PMIX_SUCCESS != (rc = PMIx_Finalize(NULL, 0))) {
        fprintf(stderr, "ERROR: PMIx_Finalize failed (%lu on %s): %d (%s)\n", (unsigned long)pid, hostname, rc, PMIx_Error_string(rc));
        exit(1);
    }

    fflush(stderr);
    return(0);
}
