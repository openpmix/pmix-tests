/*
 * Copyright (c) 2014-2019 Intel, Inc.  All rights reserved.
 * Copyright (c) 2015      Cisco Systems, Inc.  All rights reserved.
 * Copyright (c) 2017-2019 Research Organization for Information Science
 *                         and Technology (RIST).  All rights reserved.
 * Copyright (c) 2019      Mellanox Technologies, Inc.
 *                         All rights reserved.
 * $COPYRIGHT$
 *
 * Additional copyrights may follow
 *
 * $HEADER$
 */

#include <unistd.h>
#include <string.h>
#include <pthread.h>
#include <event.h>

#include "test_common.h"
#include "unit_list.h"
#include "unit_progress_threads.h"


/* create a tracking object for progress threads */
typedef struct {
    unit_list_item_t super;

    int refcount;
    char *name;

    struct event_base *ev_base;

    /* This will be set to false when it is time for the progress
       thread to exit */
    volatile bool ev_active;

    /* This event will always be set on the ev_base (so that the
       ev_base is not empty!) */
    pmix_event_t block;

    bool engine_constructed;
    pmix_thread_t engine;
} unit_progress_tracker_t;

static void tracker_constructor(unit_progress_tracker_t *p)
{
    p->refcount = 1;  // start at one since someone created it
    p->name = NULL;
    p->ev_base = NULL;
    p->ev_active = false;
    p->engine_constructed = false;
}

static void tracker_destructor(unit_progress_tracker_t *p)
{
    pmix_event_del(&p->block);

    if (NULL != p->name) {
        free(p->name);
    }
    if (NULL != p->ev_base) {
        pmix_event_base_free(p->ev_base);
    }
    if (p->engine_constructed) {
        PMIX_DESTRUCT(&p->engine);
    }
}

static PMIX_CLASS_INSTANCE(unit_progress_tracker_t,
                          unit_list_item_t,
                          tracker_constructor,
                          tracker_destructor);

static bool inited = false;
static unit_list_t tracking;
static struct timeval long_timeout = {
    .tv_sec = 3600,
    .tv_usec = 0
};
static const char *shared_thread_name = "PMIX-wide async progress thread";

/*
 * If this event is fired, just restart it so that this event base
 * continues to have something to block on.
 */
static void dummy_timeout_cb(int fd, short args, void *cbdata)
{
    unit_progress_tracker_t *trk = (unit_progress_tracker_t*)cbdata;

    pmix_event_add(&trk->block, &long_timeout);
}

/*
 * Main for the progress thread
 */
static void* progress_engine(pmix_object_t *obj)
{
    pmix_thread_t *t = (pmix_thread_t*)obj;
    unit_progress_tracker_t *trk = (unit_progress_tracker_t*)t->t_arg;

    while (trk->ev_active) {
        pmix_event_loop(trk->ev_base, PMIX_EVLOOP_ONCE);
    }

    return PMIX_THREAD_CANCELLED;
}

static void stop_progress_engine(unit_progress_tracker_t *trk)
{
    assert(trk->ev_active);
    trk->ev_active = false;
    /* break the event loop - this will cause the loop to exit upon
       completion of any current event */
    pmix_event_base_loopexit(trk->ev_base);

    pmix_thread_join(&trk->engine, NULL);
}

static int start_progress_engine(unit_progress_tracker_t *trk)
{
    assert(!trk->ev_active);
    trk->ev_active = true;

    /* fork off a thread to progress it */
    trk->engine.t_run = progress_engine;
    trk->engine.t_arg = trk;

    int rc = pmix_thread_start(&trk->engine);

    return rc;
}

struct event_base *unit_progress_thread_init(const char *name)
{
    unit_progress_tracker_t *trk;
    int rc;

    if (!inited) {
        PMIX_CONSTRUCT(&tracking, unit_list_t);
        inited = true;
    }

    if (NULL == name) {
        name = shared_thread_name;
    }

    /* check if we already have this thread */
    UNIT_LIST_FOREACH(trk, &tracking, unit_progress_tracker_t) {
        if (0 == strcmp(name, trk->name)) {
            /* we do, so up the refcount on it */
            ++trk->refcount;
            /* return the existing base */
            return trk->ev_base;
        }
    }

    trk = PMIX_NEW(unit_progress_tracker_t);
    if (NULL == trk) {
        return NULL;
    }

    trk->name = strdup(name);
    if (NULL == trk->name) {
        PMIX_RELEASE(trk);
        return NULL;
    }

    if (NULL == (trk->ev_base = pmix_event_base_create())) {
        PMIX_RELEASE(trk);
        return NULL;
    }

    /* add an event to the new event base (if there are no events,
       pmix_event_loop() will return immediately) */
    pmix_event_assign(&trk->block, trk->ev_base, -1, PMIX_EV_PERSIST,
                   dummy_timeout_cb, trk);
    pmix_event_add(&trk->block, &long_timeout);

    /* construct the thread object */
    PMIX_CONSTRUCT(&trk->engine, pmix_thread_t);
    trk->engine_constructed = true;
    if (PMIX_SUCCESS != (rc = start_progress_engine(trk))) {
        PMIX_RELEASE(trk);
        return NULL;
    }
    unit_list_append(&tracking, &trk->super);

    return trk->ev_base;
}

int unit_progress_thread_stop(const char *name)
{
    unit_progress_tracker_t *trk;

    if (!inited) {
        /* nothing we can do */
        return PMIX_ERR_NOT_FOUND;
    }

    if (NULL == name) {
        name = shared_thread_name;
    }

    /* find the specified engine */
    UNIT_LIST_FOREACH(trk, &tracking, unit_progress_tracker_t) {
        if (0 == strcmp(name, trk->name)) {
            /* decrement the refcount */
            --trk->refcount;

            /* If the refcount is still above 0, we're done here */
            if (trk->refcount > 0) {
                return PMIX_SUCCESS;
            }

            /* If the progress thread is active, stop it */
            if (trk->ev_active) {
                stop_progress_engine(trk);
            }
            unit_list_remove_item(&tracking, &trk->super);
            PMIX_RELEASE(trk);
            return PMIX_SUCCESS;
        }
    }

    return PMIX_ERR_NOT_FOUND;
}

int unit_progress_thread_finalize(const char *name)
{
    unit_progress_tracker_t *trk;

    if (!inited) {
        /* nothing we can do */
        return PMIX_ERR_NOT_FOUND;
    }

    if (NULL == name) {
        name = shared_thread_name;
    }

    /* find the specified engine */
    UNIT_LIST_FOREACH(trk, &tracking, unit_progress_tracker_t) {
        if (0 == strcmp(name, trk->name)) {
            /* If the refcount is still above 0, we're done here */
            if (trk->refcount > 0) {
                return PMIX_SUCCESS;
            }

            unit_list_remove_item(&tracking, &trk->super);
            PMIX_RELEASE(trk);
            return PMIX_SUCCESS;
        }
    }

    return PMIX_ERR_NOT_FOUND;
}

/*
 * Stop the progress thread, but don't delete the tracker (or event base)
 */
int unit_progress_thread_pause(const char *name)
{
    unit_progress_tracker_t *trk;

    if (!inited) {
        /* nothing we can do */
        return PMIX_ERR_NOT_FOUND;
    }

    if (NULL == name) {
        name = shared_thread_name;
    }

    /* find the specified engine */
    UNIT_LIST_FOREACH(trk, &tracking, unit_progress_tracker_t) {
        if (0 == strcmp(name, trk->name)) {
            if (trk->ev_active) {
                stop_progress_engine(trk);
            }

            return PMIX_SUCCESS;
        }
    }

    return PMIX_ERR_NOT_FOUND;
}

int unit_progress_thread_resume(const char *name)
{
    unit_progress_tracker_t *trk;

    if (!inited) {
        /* nothing we can do */
        return PMIX_ERR_NOT_FOUND;
    }

    if (NULL == name) {
        name = shared_thread_name;
    }

    /* find the specified engine */
    UNIT_LIST_FOREACH(trk, &tracking, unit_progress_tracker_t) {
        if (0 == strcmp(name, trk->name)) {
            if (trk->ev_active) {
                return PMIX_ERR_RESOURCE_BUSY;
            }

            return start_progress_engine(trk);
        }
    }

    return PMIX_ERR_NOT_FOUND;
}
