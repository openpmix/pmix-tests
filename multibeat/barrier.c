#include <stdio.h>

#include <pmix.h>

extern pmix_proc_t myproc;
extern pmix_proc_t wcproc;

void
barrier(void)
{
    const int rc = PMIx_Fence(&wcproc, 1, NULL, 0);

    if (PMIX_SUCCESS != rc) {
        fprintf(stderr,
                "Client ns %s rank %d: PMIx_Fence failed: %d\n",
                myproc.nspace, myproc.rank, rc);
        exit(1);
    }
}
