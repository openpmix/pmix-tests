#include "barrier.h"
#include "state.h"
#include "util.h"

#define _GNU_SOURCE
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <time.h>

#include <pmix.h>

/*
 * --  callbacks ----------------------------------------------------
 */

/* event handler registration is done asynchronously because it
 * may involve the PMIx server registering with the host RM for
 * external events. So we provide a callback function that returns
 * the status of the request (success or an error), plus a numerical index
 * to the registered event. The index is used later on to deregister
 * an event handler - if we don't explicitly deregister it, then the
 * PMIx server will do so when it see us exit */

/*
 * pmix_hdlr_reg_cbfunc_t
 */
static void
evhandler_reg_callbk(pmix_status_t status,
                     size_t evhandler_ref,
                     void *cbdata)
{
    volatile int *active = (volatile int *) cbdata;

    if (PMIX_SUCCESS != status) {
        fprintf(stderr,
                "Client %s:%d EVENT HANDLER REGISTRATION FAILED "
                "WITH STATUS %d, ref=%lu\n",
                myproc.nspace, myproc.rank,
                status, (unsigned long) evhandler_ref);
    }
    *active = status;
}

/*
 * pmix_notification_fn_t
 */
static void
event_handler(size_t evhdlr_registration_id,
              pmix_status_t status,
              const pmix_proc_t *source,
              pmix_info_t info[], size_t ninfo,
              pmix_info_t results[], size_t nresults,
              pmix_event_notification_cbfunc_fn_t cbfunc,
              void *cbdata)
{
    static int count;

    fprintf(stderr,
            "%s: rank=%d source=%d count=%d\n",
            PMIx_Error_string(status),
            myproc.rank,
            source->rank,
            ++count);

    if (NULL != cbfunc) {
        cbfunc(PMIX_EVENT_ACTION_COMPLETE,
               NULL, 0,
               NULL, NULL,
               cbdata);
    }
}

static void
monitor_done(pmix_status_t status,
             pmix_info_t *info, size_t ninfo,
             void *cbdata,
             pmix_release_cbfunc_t release_fn,
             void *release_cbdata)
{
    volatile int *activep = (volatile int *) cbdata;

    if (NULL != release_fn) {
        release_fn(release_cbdata);
    }

    *activep = status;
}

/*
 * -- heart beat management -----------------------------------------
 */

void
register_heartbeat_handler(void)
{
    pmix_status_t sp = PMIX_MONITOR_HEARTBEAT_ALERT;
    volatile int active = -1;

    PMIx_Register_event_handler(&sp, 1,
                                NULL, 0,
                                event_handler,
                                evhandler_reg_callbk,
                                (void *) &active);
    WAIT_WHILE_EQ(active, -1);
    if (0 != active) {
        fprintf(stderr,
                "[%s:%d] heartbeat handler registration failed\n",
                myproc.nspace, myproc.rank);
        exit(active);
    }
}

void
setup_heartbeat(void)
{
    pmix_info_t *iptr;
    pmix_info_t *info;
    uint32_t n;
    int rc;
    volatile int active = -1;

    PMIX_INFO_CREATE(iptr, 1);
    PMIX_INFO_LOAD(&iptr[0], PMIX_MONITOR_HEARTBEAT, NULL, PMIX_POINTER);

    PMIX_INFO_CREATE(info, 3);
    PMIX_INFO_LOAD(&info[0], PMIX_MONITOR_ID, "MONITOR1", PMIX_STRING);
    n = 2;  // require a heartbeat every 2 seconds
    PMIX_INFO_LOAD(&info[1], PMIX_MONITOR_HEARTBEAT_TIME, &n, PMIX_UINT32);
    n = 2;  // two heartbeats can be missed before declaring us "stalled"
    PMIX_INFO_LOAD(&info[2], PMIX_MONITOR_HEARTBEAT_DROPS, &n, PMIX_UINT32);

    rc = PMIx_Process_monitor_nb(iptr, PMIX_MONITOR_HEARTBEAT_ALERT,
                                 info, 3, monitor_done, (void *) &active);
    if (PMIX_SUCCESS != rc) {
        fprintf(stderr,
                "Client ns %s rank %d: #1 PMIx_Process_monitor_nb "
                "failed: %d\n",
                myproc.nspace, myproc.rank, rc);
        exit(1);
    }
    WAIT_WHILE_EQ(active, -1);

    PMIX_INFO_FREE(iptr, 1);
    PMIX_INFO_FREE(info, 3);
}

#define SLEEP_FOR 8
#define CHOMP(_s) (_s)[strlen(_s)-1] = '\0'
#define TIME_IS(_n)                             \
    do {                                        \
        time_t t = time(NULL);                  \
        _n = ctime(&t);                         \
        CHOMP(_n);                              \
    } while (0)

void
beat_beat_beat(void)
{
    int k = 0;

    srand(getpid());

    while (k < 5) {
        const int n = rand() % 4;

        if (n == 0) {
            char *now;

            TIME_IS(now);
            fprintf(stderr,
                    "%s:%d: stop sending heartbeats for %ds\n",
                    now, myproc.rank, SLEEP_FOR);
            sleep(SLEEP_FOR);
            TIME_IS(now);
            fprintf(stderr,
                    "%s:%d: resume\n",
                    now, myproc.rank);
            ++k;
        }

        PMIx_Heartbeat();

        sleep(1);
    }
}
