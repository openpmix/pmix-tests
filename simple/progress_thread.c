/*
 * Copyright (c) 2014-2018 Intel, Inc.  All rights reserved.
 * Copyright (c) 2015      Cisco Systems, Inc.  All rights reserved.
 * $COPYRIGHT$
 *
 * Additional copyrights may follow
 *
 * $HEADER$
 */


#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <time.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <errno.h>
#include <signal.h>
#include <event.h>

#include "simptest.h"

static bool active = false;
static debug_event_t block;
static struct timeval long_timeout = {
    .tv_sec = 3600,
    .tv_usec = 0
};
static pthread_t engine;
static debug_event_base_t *debug_evbase;

/*
 * If this event is fired, just restart it so that this event base
 * continues to have something to block on.
 */
static void dummy_timeout_cb(int fd, short args, void *cbdata)
{
    event_add(&block, &long_timeout);
}

/*
 * Main for the progress thread
 */
static void* progress_engine(void)
{
    while (active) {
        event_base_loop(debug_evbase, EVLOOP_ONCE);
    }

    return PMIX_TEST_THREAD_CANCELLED;
}

void pmix_test_thread_stop(void)
{
    active = false;

    /* break the event loop - this will cause the loop to exit upon
       completion of any current event */
    event_base_loopbreak(debug_evbase);

    pthread_join(engine, NULL);

    event_base_free(debug_evbase);
}

int pmix_test_thread_start(debug_event_base_t **evbase)
{
    active = true;

    /* get an event base */
    if (NULL == (debug_evbase = event_base_new())) {
        return -1;
    }
    /* add an event to the new event base (if there are no events,
       event_loop() will return immediately) */
    event_assign(&block, debug_evbase, -1, EV_PERSIST,
                   dummy_timeout_cb, NULL);
    event_add(&block, &long_timeout);

    /* fork off a thread to progress it */
    engine = (pthread_t) -1;

    int rc = pthread_create(&engine, NULL, (void*(*)(void*))progress_engine, NULL);
    *evbase = debug_evbase;
    return rc;
}
