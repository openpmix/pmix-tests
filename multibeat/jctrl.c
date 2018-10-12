#include "barrier.h"
#include "state.h"
#include "hb.h"
#include "util.h"

#define _GNU_SOURCE
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <time.h>
#include <signal.h>

#include <pmix.h>

static pmix_info_t waiter;

int
main(void)
{
    int rc;
    pmix_value_t value;
    pmix_value_t *val = &value;
    uint32_t nprocs;

    /* init us - note that the call to "init" includes the return of
     * any job-related info provided by the RM. */
    rc = PMIx_Init(&myproc, NULL, 0);
    if (PMIX_SUCCESS != rc) {
        fprintf(stderr,
                "Client ns %s rank %d: PMIx_Init failed: %d\n",
                myproc.nspace, myproc.rank, rc);
        exit(1);
    }
    fprintf(stderr,
            "Client ns %s rank %d: Running\n",
            myproc.nspace, myproc.rank);

    /* job-related info is found in our nspace, assigned to the
     * wildcard rank as it doesn't relate to a specific rank. Setup
     * a name to retrieve such values */
    PMIX_PROC_CONSTRUCT(&wcproc);
    (void) strncpy(wcproc.nspace, myproc.nspace, PMIX_MAX_NSLEN);
    wcproc.rank = PMIX_RANK_WILDCARD;

    /* get our job size */
    if (PMIX_SUCCESS != (rc = PMIx_Get(&wcproc, PMIX_JOB_SIZE,
                                       NULL, 0, &val))) {
        fprintf(stderr,
                "Client ns %s rank %d: PMIx_Get job size failed: %d\n",
                myproc.nspace, myproc.rank, rc);
        exit(1);
    }
    nprocs = val->data.uint32;
    PMIX_VALUE_RELEASE(val);
    fprintf(stderr,
            "Client %s:%d job size %d\n",
            myproc.nspace, myproc.rank, nprocs);

    {
        int all = 0;

        PMIX_INFO_CONSTRUCT(&waiter);
        PMIX_INFO_LOAD(&waiter, PMIX_WAIT, &all, PMIX_INT);
    }

    register_heartbeat_handler();
    setup_heartbeat();
    beat_beat_beat();

    barrier();

    if (PMIX_SUCCESS != (rc = PMIx_Finalize(NULL, 0))) {
        fprintf(stderr,
                "Client ns %s rank %d:PMIx_Finalize failed: %d\n",
                myproc.nspace, myproc.rank, rc);
    } else {
        fprintf(stderr,
                "Client ns %s rank %d:PMIx_Finalize successfully completed\n",
                myproc.nspace, myproc.rank);
    }
    fflush(stderr);
    return(0);
}
