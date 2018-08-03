/*
 * Copyright (c) 2004-2010 The Trustees of Indiana University and Indiana
 *                         University Research and Technology
 *                         Corporation.  All rights reserved.
 * Copyright (c) 2004-2011 The University of Tennessee and The University
 *                         of Tennessee Research Foundation.  All rights
 *                         reserved.
 * Copyright (c) 2004-2005 High Performance Computing Center Stuttgart,
 *                         University of Stuttgart.  All rights reserved.
 * Copyright (c) 2004-2005 The Regents of the University of California.
 *                         All rights reserved.
 * Copyright (c) 2006-2013 Los Alamos National Security, LLC.
 *                         All rights reserved.
 * Copyright (c) 2009-2012 Cisco Systems, Inc.  All rights reserved.
 * Copyright (c) 2011      Oak Ridge National Labs.  All rights reserved.
 * Copyright (c) 2013-2018 Intel, Inc. All rights reserved.
 * Copyright (c) 2015      Research Organization for Information Science
 *                         and Technology (RIST). All rights reserved.
 * Copyright (c) 2016      IBM Corporation.  All rights reserved.
 * $COPYRIGHT$
 *
 * Additional copyrights may follow
 *
 * $HEADER$
 *
 */

#include <pmix_server.h>

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

extern char **environ;
static debug_event_base_t *debug_evbase = NULL;
static bool verbose = false;

static pmix_status_t connected(const pmix_proc_t *proc, void *server_object,
                               pmix_op_cbfunc_t cbfunc, void *cbdata);
static pmix_status_t finalized(const pmix_proc_t *proc, void *server_object,
                               pmix_op_cbfunc_t cbfunc, void *cbdata);
static pmix_status_t abort_fn(const pmix_proc_t *proc, void *server_object,
                              int status, const char msg[],
                              pmix_proc_t procs[], size_t nprocs,
                              pmix_op_cbfunc_t cbfunc, void *cbdata);
static pmix_status_t fencenb_fn(const pmix_proc_t procs[], size_t nprocs,
                                const pmix_info_t info[], size_t ninfo,
                                char *data, size_t ndata,
                                pmix_modex_cbfunc_t cbfunc, void *cbdata);
static pmix_status_t dmodex_fn(const pmix_proc_t *proc,
                               const pmix_info_t info[], size_t ninfo,
                               pmix_modex_cbfunc_t cbfunc, void *cbdata);
static pmix_status_t publish_fn(const pmix_proc_t *proc,
                                const pmix_info_t info[], size_t ninfo,
                                pmix_op_cbfunc_t cbfunc, void *cbdata);
static pmix_status_t lookup_fn(const pmix_proc_t *proc, char **keys,
                               const pmix_info_t info[], size_t ninfo,
                               pmix_lookup_cbfunc_t cbfunc, void *cbdata);
static pmix_status_t unpublish_fn(const pmix_proc_t *proc, char **keys,
                                  const pmix_info_t info[], size_t ninfo,
                                  pmix_op_cbfunc_t cbfunc, void *cbdata);
static pmix_status_t spawn_fn(const pmix_proc_t *proc,
                              const pmix_info_t job_info[], size_t ninfo,
                              const pmix_app_t apps[], size_t napps,
                              pmix_spawn_cbfunc_t cbfunc, void *cbdata);
static pmix_status_t connect_fn(const pmix_proc_t procs[], size_t nprocs,
                                const pmix_info_t info[], size_t ninfo,
                                pmix_op_cbfunc_t cbfunc, void *cbdata);
static pmix_status_t disconnect_fn(const pmix_proc_t procs[], size_t nprocs,
                                   const pmix_info_t info[], size_t ninfo,
                                   pmix_op_cbfunc_t cbfunc, void *cbdata);
static pmix_status_t register_event_fn(pmix_status_t *codes, size_t ncodes,
                                       const pmix_info_t info[], size_t ninfo,
                                       pmix_op_cbfunc_t cbfunc, void *cbdata);
static pmix_status_t deregister_events(pmix_status_t *codes, size_t ncodes,
                                       pmix_op_cbfunc_t cbfunc, void *cbdata);
static pmix_status_t notify_event(pmix_status_t code,
                                  const pmix_proc_t *source,
                                  pmix_data_range_t range,
                                  pmix_info_t info[], size_t ninfo,
                                  pmix_op_cbfunc_t cbfunc, void *cbdata);
static pmix_status_t query_fn(pmix_proc_t *proct,
                              pmix_query_t *queries, size_t nqueries,
                              pmix_info_cbfunc_t cbfunc,
                              void *cbdata);
static void tool_connect_fn(pmix_info_t *info, size_t ninfo,
                            pmix_tool_connection_cbfunc_t cbfunc,
                            void *cbdata);
static void log_fn(const pmix_proc_t *client,
                   const pmix_info_t data[], size_t ndata,
                   const pmix_info_t directives[], size_t ndirs,
                   pmix_op_cbfunc_t cbfunc, void *cbdata);

static pmix_server_module_t mymodule = {
    .client_connected = connected,
    .client_finalized = finalized,
    .abort = abort_fn,
    .fence_nb = fencenb_fn,
    .direct_modex = dmodex_fn,
    .publish = publish_fn,
    .lookup = lookup_fn,
    .unpublish = unpublish_fn,
    .spawn = spawn_fn,
    .connect = connect_fn,
    .disconnect = disconnect_fn,
    .register_events = register_event_fn,
    .deregister_events = deregister_events,
    .notify_event = notify_event,
    .query = query_fn,
    .tool_connected = tool_connect_fn,
    .log = log_fn
};

typedef struct {
    mylock_t lock;
    debug_event_t ev;
    pmix_proc_t caller;
    pmix_info_t *info;
    size_t ninfo;
    pmix_op_cbfunc_t cbfunc;
    pmix_spawn_cbfunc_t spcbfunc;
    pmix_release_cbfunc_t relcbfunc;
    void *cbdata;
} myxfer_t;
static void xfcon(myxfer_t *p)
{
    DEBUG_CONSTRUCT_LOCK(&p->lock);
    p->info = NULL;
    p->ninfo = 0;
    p->cbfunc = NULL;
    p->spcbfunc = NULL;
    p->cbdata = NULL;
}
static void xfdes(myxfer_t *p)
{
    DEBUG_DESTRUCT_LOCK(&p->lock);
    if (NULL != p->info) {
        PMIX_INFO_FREE(p->info, p->ninfo);
    }
}

typedef struct {
    int exit_code;
    pid_t pid;
} wait_tracker_t;

static volatile int wakeup;
static int exit_code = 0;
static debug_event_t handler;
static wait_tracker_t *children;
static bool istimeouttest = false;
static mylock_t globallock;
static pmix_pdata_t *pubdata = NULL;
static size_t npub = 0, nprocs = 1;

static void set_namespace(int nprocs, char *ranks, char *nspace,
                          pmix_op_cbfunc_t cbfunc, myxfer_t *x);
static void errhandler(size_t evhdlr_registration_id,
                       pmix_status_t status,
                       const pmix_proc_t *source,
                       pmix_info_t info[], size_t ninfo,
                       pmix_info_t results[], size_t nresults,
                       pmix_event_notification_cbfunc_fn_t cbfunc,
                       void *cbdata);
static void wait_signal_callback(int fd, short event, void *arg);
static void errhandler_reg_callbk (pmix_status_t status,
                                   size_t errhandler_ref,
                                   void *cbdata);

static void opcbfunc(pmix_status_t status, void *cbdata)
{
    myxfer_t *x = (myxfer_t*)cbdata;

    /* release the caller, if necessary */
    if (NULL != x->cbfunc) {
        x->cbfunc(PMIX_SUCCESS, x->cbdata);
    }
    DEBUG_WAKEUP_THREAD(&x->lock);
}


static void dlcbfunc(int sd, short flags, void *cbdata)
{
    myxfer_t *x = (myxfer_t*)cbdata;

    PMIX_TEST_PRINT("INVENTORY READY FOR DELIVERY\n");

    PMIx_server_deliver_inventory(x->info, x->ninfo, NULL, 0, opcbfunc, (void*)x);
}

static void infocbfunc(pmix_status_t status,
                       pmix_info_t *info, size_t ninfo,
                       void *cbdata,
                       pmix_release_cbfunc_t release_fn,
                       void *release_cbdata)
{
    mylock_t *lock = (mylock_t*)cbdata;
    myxfer_t *x;
    size_t n;

    PMIX_TEST_PRINT("INVENTORY RECEIVED\n");

    /* we don't have any place to send this, so for test
     * purposes only, let's push it back down for processing.
     * Note: it must be thread-shifted first as we are in
     * the callback event thread of the underlying PMIx
     * server */
    x = (myxfer_t*)malloc(sizeof(myxfer_t));
    xfcon(x);
    x->ninfo = ninfo;
    PMIX_INFO_CREATE(x->info, x->ninfo);
    for (n=0; n < ninfo; n++) {
        PMIX_INFO_XFER(&x->info[n], &info[n]);
    }
    DEBUG_THREADSHIFT(x, dlcbfunc);

    if (NULL != release_fn) {
        release_fn(release_cbdata);
    }
    lock->status = status;
    DEBUG_WAKEUP_THREAD(lock);
}

/* this is an event notification function that we explicitly request
 * be called when the PMIX_MODEL_DECLARED notification is issued.
 * We could catch it in the general event notification function and test
 * the status to see if the status matched, but it often is simpler
 * to declare a use-specific notification callback point. In this case,
 * we are asking to know whenever a model is declared as a means
 * of testing server self-notification */
static void model_callback(size_t evhdlr_registration_id,
                           pmix_status_t status,
                           const pmix_proc_t *source,
                           pmix_info_t info[], size_t ninfo,
                           pmix_info_t results[], size_t nresults,
                           pmix_event_notification_cbfunc_fn_t cbfunc,
                           void *cbdata)
{
    size_t n;

    if (verbose) {
        /* just let us know it was received */
        fprintf(stderr, "SIMPTEST: Model event handler called with status %d(%s)\n",
                status, PMIx_Error_string(status));
        for (n=0; n < ninfo; n++) {
            if (PMIX_STRING == info[n].value.type) {
                fprintf(stderr, "\t%s:\t%s\n", info[n].key, info[n].value.data.string);
            }
        }
    }

    /* we must NOT tell the event handler state machine that we
     * are the last step as that will prevent it from notifying
     * anyone else that might be listening for declarations */
    if (NULL != cbfunc) {
        cbfunc(PMIX_SUCCESS, NULL, 0, NULL, NULL, cbdata);
    }
    DEBUG_WAKEUP_THREAD(&globallock);
}

/* event handler registration is done asynchronously */
static void model_registration_callback(pmix_status_t status,
                                        size_t evhandler_ref,
                                        void *cbdata)
{
    mylock_t *lock = (mylock_t*)cbdata;

    if (PMIX_SUCCESS != status) {
        fprintf(stderr, "simptest EVENT HANDLER REGISTRATION FAILED WITH STATUS %d, ref=%lu\n",
                   status, (unsigned long)evhandler_ref);
    }
    lock->status = status;
    DEBUG_WAKEUP_THREAD(lock);
}

int main(int argc, char **argv)
{
    char **client_env=NULL;
    char **client_argv=NULL;
    char *tmp, **atmp, *executable=NULL;
    int rc, n, k;
    uid_t myuid;
    gid_t mygid;
    pid_t pid;
    myxfer_t *x;
    pmix_proc_t proc;
    wait_tracker_t *child;
    pmix_info_t *info;
    size_t ninfo;
    bool cross_version = false;
    bool usock = true;
    bool hwloc = false;
    mylock_t mylock;
    pmix_status_t code;

    /* smoke test */
    if (PMIX_SUCCESS != 0) {
        fprintf(stderr, "ERROR IN COMPUTING CONSTANTS: PMIX_SUCCESS = %d\n", PMIX_SUCCESS);
        exit(1);
    }

    /* see if we were passed the number of procs to run or
     * the executable to use */
    for (n=1; n < argc; n++) {
        if (0 == strcmp("-n", argv[n]) &&
            NULL != argv[n+1]) {
            nprocs = strtol(argv[n+1], NULL, 10);
            ++n;  // step over the argument
        } else if (0 == strcmp("-e", argv[n]) &&
                   NULL != argv[n+1]) {
            executable = strdup(argv[n+1]);
            /* check for timeout test */
            if (NULL != strstr(executable, "simptimeout")) {
                istimeouttest = true;
            }
            for (k=n+2; NULL != argv[k]; k++) {
                pmix_argv_append_nosize(&client_argv, argv[k]);
            }
            n += k;
        } else if (0 == strcmp("-x", argv[n])) {
            /* cross-version test - we will set one child to
             * run at a different version. Requires -n >= 2 */
            cross_version = true;
            usock = false;
        } else if (0 == strcmp("-u", argv[n])) {
            /* enable usock */
            usock = false;
        } else if (0 == strcmp("-v", argv[n])) {
            verbose = true;
        } else if (0 == strcmp("-V", argv[n]) || 0 == strcmp("--version", argv[n])) {
            fprintf(stderr, "Testing version %s\n", PMIx_Get_version());
        } else if (0 == strcmp("-h", argv[n])) {
            /* print the options and exit */
            fprintf(stderr, "usage: simptest <options>\n");
            fprintf(stderr, "    -n N     Number of clients to run\n");
            fprintf(stderr, "    -e foo   Name of the client executable to run (default: simpclient\n");
            fprintf(stderr, "    -x       Test cross-version support\n");
            fprintf(stderr, "    -u       Enable legacy usock support\n");
            fprintf(stderr, "    -d       Execute with verbose output\n");
            fprintf(stderr, "    -V | --version      Report version being tested\n");
            exit(0);
        }
    }
    if (NULL == executable) {
        executable = strdup("./simpclient");
    }
    if (cross_version && nprocs < 2) {
        fprintf(stderr, "Cross-version testing requires at least two clients\n");
        exit(1);
    }

    /* setup the server library and tell it to support tool connections */
    ninfo = 3;
    PMIX_INFO_CREATE(info, ninfo);
    PMIX_INFO_LOAD(&info[0], PMIX_SERVER_TOOL_SUPPORT, NULL, PMIX_BOOL);
    PMIX_INFO_LOAD(&info[1], PMIX_USOCK_DISABLE, &usock, PMIX_BOOL);
    PMIX_INFO_LOAD(&info[2], PMIX_SERVER_GATEWAY, NULL, PMIX_BOOL);
    if (PMIX_SUCCESS != (rc = PMIx_server_init(&mymodule, info, ninfo))) {
        fprintf(stderr, "Init failed with error %d\n", rc);
        return rc;
    }
    PMIX_INFO_FREE(info, ninfo);

    /* register the default errhandler */
    DEBUG_CONSTRUCT_LOCK(&mylock);
    ninfo = 1;
    PMIX_INFO_CREATE(info, ninfo);
    PMIX_INFO_LOAD(&info[0], PMIX_EVENT_HDLR_NAME, "SIMPTEST-DEFAULT", PMIX_STRING);
    PMIx_Register_event_handler(NULL, 0, info, ninfo,
                                errhandler, errhandler_reg_callbk, (void*)&mylock);

    DEBUG_WAIT_THREAD(&mylock);
    PMIX_INFO_FREE(info, ninfo);
    if (PMIX_SUCCESS != mylock.status) {
        exit(mylock.status);
    }
    DEBUG_DESTRUCT_LOCK(&mylock);

    /* start our internal progress thread */
    if (0 != pmix_test_thread_start(&debug_evbase)) {
        fprintf(stderr, "Failed to start progress thread\n");
        exit(1);
    }

    /* setup to see sigchld on the forked tests */
    children = (wait_tracker_t*)malloc(nprocs*sizeof(wait_tracker_t));
    memset(children, 0, nprocs*sizeof(wait_tracker_t));
    event_assign(&handler, debug_evbase, SIGCHLD,
                 EV_SIGNAL|EV_PERSIST,wait_signal_callback, &handler);
    event_add(&handler, NULL);

    /* we have a single namespace for all clients */
    atmp = NULL;
    for (n=0; n < nprocs; n++) {
        asprintf(&tmp, "%d", n);
        pmix_argv_append_nosize(&atmp, tmp);
        free(tmp);
    }
    tmp = pmix_argv_join(atmp, ',');
    pmix_argv_free(atmp);
    x = (myxfer_t*)malloc(sizeof(myxfer_t));
    xfcon(x);
    set_namespace(nprocs, tmp, "foobar", opcbfunc, x);

    /* set common argv and env */
    client_env = pmix_argv_copy(environ);
    pmix_argv_prepend_nosize(&client_argv, executable);
    if (verbose) {
        PMIX_SETENV(rc, "PMIX_TEST_VERBOSE", "1", &client_env);
    }

    wakeup = nprocs;
    myuid = getuid();
    mygid = getgid();

    /* collect our inventory */
    DEBUG_CONSTRUCT_LOCK(&mylock);
    PMIX_TEST_PRINT("Collecting inventory\n");
    if (PMIX_SUCCESS != (rc = PMIx_server_collect_inventory(NULL, 0, infocbfunc, (void*)&mylock))) {
        fprintf(stderr, "Collect inventory failed: %d\n", rc);
        DEBUG_DESTRUCT_LOCK(&mylock);
        goto done;
    }
    DEBUG_WAIT_THREAD(&mylock);
    if (verbose) {
        fprintf(stderr, "Inventory collected: %d\n", mylock.status);
    }
    if (PMIX_SUCCESS != mylock.status) {
        exit(mylock.status);
    }
    DEBUG_DESTRUCT_LOCK(&mylock);

    /* if the nspace registration hasn't completed yet,
     * wait for it here */
    DEBUG_WAIT_THREAD(&x->lock);
    free(tmp);
    xfdes(x);
    free(x);

    /* fork/exec the test */
    (void)strncpy(proc.nspace, "foobar", PMIX_MAX_NSLEN);
    for (n = 0; n < nprocs; n++) {
        proc.rank = n;
        if (PMIX_SUCCESS != (rc = PMIx_server_setup_fork(&proc, &client_env))) {//n
            fprintf(stderr, "Server fork setup failed with error %d\n", rc);
            PMIx_server_finalize();
            return rc;
        }
        /* if cross-version test is requested, then oscillate PTL support
         * by rank */
        if (cross_version) {
            if (0 == n % 2) {
                pmix_setenv("PMIX_MCA_ptl", "tcp", true, &client_env);
            } else {
                pmix_setenv("PMIX_MCA_ptl", "usock", true, &client_env);
            }
        } else if (!usock) {
            /* don't disable usock => enable it on client */
            pmix_setenv("PMIX_MCA_ptl", "usock", true, &client_env);
        }
        x = (myxfer_t*)malloc(sizeof(myxfer_t));
        xfcon(x);
        if (PMIX_SUCCESS != (rc = PMIx_server_register_client(&proc, myuid, mygid,
                                                              NULL, opcbfunc, x))) {
            fprintf(stderr, "Server register client failed with error %d\n", rc);
            PMIx_server_finalize();
            return rc;
        }
        /* don't fork/exec the client until we know it is registered
         * so we avoid a potential race condition in the server */
        DEBUG_WAIT_THREAD(&x->lock);
        xfdes(x);
        free(x);
        pid = fork();
        if (pid < 0) {
            fprintf(stderr, "Fork failed\n");
            PMIx_server_finalize();
            return -1;
        }
        if (pid == 0) {
            execve(executable, client_argv, client_env);
            /* Does not return */
            exit(0);
        } else {
            children[n].pid = pid;
        }
    }
    free(executable);
    pmix_argv_free(client_argv);
    pmix_argv_free(client_env);

    PMIX_TEST_PRINT("Children spawned - waiting for termination\n")
    /* hang around until the client(s) finalize */
    while (0 < wakeup) {
        struct timespec ts;
        ts.tv_sec = 0;
        ts.tv_nsec = 100000;
        nanosleep(&ts, NULL);
    }

    /* see if anyone exited with non-zero status */
    for (n=0; n < nprocs; n++) {
        if (0 != children[n].exit_code) {
            fprintf(stderr, "Child %d exited with status %d - test FAILED\n", n, children[n].exit_code);
            goto done;
        }
    }

  done:
    /* deregister the event handlers */
    PMIx_Deregister_event_handler(0, NULL, NULL);

    /* release the child tracker */
    free(children);

    /* finalize the server library */
    if (PMIX_SUCCESS != (rc = PMIx_server_finalize())) {
        fprintf(stderr, "Finalize failed with error %d\n", rc);
        exit_code = rc;
    }

    if (0 == exit_code) {
        fprintf(stderr, "Test finished OK!\n");
    } else {
        fprintf(stderr, "TEST FAILED WITH ERROR %d\n", exit_code);
    }

    return exit_code;
}

static void set_namespace(int nprocs, char *ranks, char *nspace,
                          pmix_op_cbfunc_t cbfunc, myxfer_t *x)
{
    char *regex, *ppn;
    char hostname[1024];

    gethostname(hostname, sizeof(hostname));
    x->ninfo = 7;

    PMIX_INFO_CREATE(x->info, x->ninfo);
    (void)strncpy(x->info[0].key, PMIX_UNIV_SIZE, PMIX_MAX_KEYLEN);
    x->info[0].value.type = PMIX_UINT32;
    x->info[0].value.data.uint32 = nprocs;

    (void)strncpy(x->info[1].key, PMIX_SPAWNED, PMIX_MAX_KEYLEN);
    x->info[1].value.type = PMIX_UINT32;
    x->info[1].value.data.uint32 = 0;

    (void)strncpy(x->info[2].key, PMIX_LOCAL_SIZE, PMIX_MAX_KEYLEN);
    x->info[2].value.type = PMIX_UINT32;
    x->info[2].value.data.uint32 = nprocs;

    (void)strncpy(x->info[3].key, PMIX_LOCAL_PEERS, PMIX_MAX_KEYLEN);
    x->info[3].value.type = PMIX_STRING;
    x->info[3].value.data.string = strdup(ranks);

    PMIx_generate_regex(hostname, &regex);
    (void)strncpy(x->info[4].key, PMIX_NODE_MAP, PMIX_MAX_KEYLEN);
    x->info[4].value.type = PMIX_STRING;
    x->info[4].value.data.string = regex;

    PMIx_generate_ppn(ranks, &ppn);
    (void)strncpy(x->info[5].key, PMIX_PROC_MAP, PMIX_MAX_KEYLEN);
    x->info[5].value.type = PMIX_STRING;
    x->info[5].value.data.string = ppn;

    (void)strncpy(x->info[6].key, PMIX_JOB_SIZE, PMIX_MAX_KEYLEN);
    x->info[6].value.type = PMIX_UINT32;
    x->info[6].value.data.uint32 = nprocs;

    PMIx_server_register_nspace(nspace, nprocs, x->info, x->ninfo,
                                cbfunc, x);
}

static void errhandler(size_t evhdlr_registration_id,
                       pmix_status_t status,
                       const pmix_proc_t *source,
                       pmix_info_t info[], size_t ninfo,
                       pmix_info_t results[], size_t nresults,
                       pmix_event_notification_cbfunc_fn_t cbfunc,
                       void *cbdata)
{
    if (verbose) {
        fprintf(stderr, "SERVER: ERRHANDLER CALLED WITH STATUS %d\n", status);
    }
    /* we must NOT tell the event handler state machine that we
     * are the last step as that will prevent it from notifying
     * anyone else that might be listening for declarations */
    if (NULL != cbfunc) {
        cbfunc(PMIX_SUCCESS, NULL, 0, NULL, NULL, cbdata);
    }
}

static void errhandler_reg_callbk (pmix_status_t status,
                                   size_t errhandler_ref,
                                   void *cbdata)
{
    mylock_t *lock = (mylock_t*)cbdata;

    if (verbose) {
        fprintf(stderr, "SERVER: ERRHANDLER REGISTRATION CALLBACK CALLED WITH STATUS %d, ref=%lu\n",
                    status, (unsigned long)errhandler_ref);
    }
    lock->status = status;
    DEBUG_WAKEUP_THREAD(lock);
}

static pmix_status_t connected(const pmix_proc_t *proc, void *server_object,
                               pmix_op_cbfunc_t cbfunc, void *cbdata)
{
    if (verbose) {
        fprintf(stderr, "SERVER: CLIENT CONNECTED %s:%d\n",
                    proc->nspace, proc->rank);
    }
    if (NULL != cbfunc) {
        cbfunc(PMIX_SUCCESS, cbdata);
    }
    return PMIX_SUCCESS;
}
static pmix_status_t finalized(const pmix_proc_t *proc, void *server_object,
                     pmix_op_cbfunc_t cbfunc, void *cbdata)
{
    if (verbose) {
        fprintf(stderr, "SERVER: FINALIZED %s:%d WAKEUP %d\n",
                    proc->nspace, proc->rank, wakeup);
    }
    /* ensure we call the cbfunc so the proc can exit! */
    if (NULL != cbfunc) {
        cbfunc(PMIX_SUCCESS, cbdata);
    }
    return PMIX_SUCCESS;
}

static void abcbfunc(pmix_status_t status, void *cbdata)
{
    myxfer_t *x = (myxfer_t*)cbdata;

    /* be sure to release the caller */
    if (NULL != x->cbfunc) {
        x->cbfunc(status, x->cbdata);
    }
    xfdes(x);
    free(x);
}

static pmix_status_t abort_fn(const pmix_proc_t *proc,
                              void *server_object,
                              int status, const char msg[],
                              pmix_proc_t procs[], size_t nprocs,
                              pmix_op_cbfunc_t cbfunc, void *cbdata)
{
    pmix_status_t rc;
    myxfer_t *x;

    if (verbose) {
        if (NULL != procs) {
            fprintf(stderr, "SERVER: ABORT on %s:%d\n", procs[0].nspace, procs[0].rank);
        } else {
            fprintf(stderr, "SERVER: ABORT OF ALL PROCS IN NSPACE %s\n", proc->nspace);
        }
    }

    /* instead of aborting the specified procs, notify them
     * (if they have registered their errhandler) */

    /* use the myxfer_t object to ensure we release
     * the caller when notification has been queued */
    x = (myxfer_t*)malloc(sizeof(myxfer_t));
    xfcon(x);
    (void)strncpy(x->caller.nspace, proc->nspace, PMIX_MAX_NSLEN);
    x->caller.rank = proc->rank;

    PMIX_INFO_CREATE(x->info, 2);
    (void)strncpy(x->info[0].key, "DARTH", PMIX_MAX_KEYLEN);
    x->info[0].value.type = PMIX_INT8;
    x->info[0].value.data.int8 = 12;
    (void)strncpy(x->info[1].key, "VADER", PMIX_MAX_KEYLEN);
    x->info[1].value.type = PMIX_DOUBLE;
    x->info[1].value.data.dval = 12.34;
    x->cbfunc = cbfunc;
    x->cbdata = cbdata;

    if (PMIX_SUCCESS != (rc = PMIx_Notify_event(status, &x->caller,
                                                PMIX_RANGE_NAMESPACE,
                                                x->info, 2,
                                                abcbfunc, x))) {
        fprintf(stderr, "SERVER: FAILED NOTIFY ERROR %d\n", (int)rc);
    }

    return PMIX_SUCCESS;
}


static pmix_status_t fencenb_fn(const pmix_proc_t procs[], size_t nprocs,
                      const pmix_info_t info[], size_t ninfo,
                      char *data, size_t ndata,
                      pmix_modex_cbfunc_t cbfunc, void *cbdata)
{
    PMIX_TEST_PRINT("SERVER: FENCENB\n");

    /* pass the provided data back to each participating proc */
    if (NULL != cbfunc) {
        cbfunc(PMIX_SUCCESS, data, ndata, cbdata, NULL, NULL);
    }
    return PMIX_SUCCESS;
}


static pmix_status_t dmodex_fn(const pmix_proc_t *proc,
                     const pmix_info_t info[], size_t ninfo,
                     pmix_modex_cbfunc_t cbfunc, void *cbdata)
{
    PMIX_TEST_PRINT("SERVER: DMODEX\n");

    /* if this is a timeout test, then do nothing */
    if (istimeouttest) {
        return PMIX_SUCCESS;
    }

    /* we don't have any data for remote procs as this
     * test only runs one server - so report accordingly */
    if (NULL != cbfunc) {
        cbfunc(PMIX_ERR_NOT_FOUND, NULL, 0, cbdata, NULL, NULL);
    }
    return PMIX_SUCCESS;
}


static pmix_status_t publish_fn(const pmix_proc_t *proc,
                      const pmix_info_t info[], size_t ninfo,
                      pmix_op_cbfunc_t cbfunc, void *cbdata)
{
    size_t n;

    PMIX_TEST_PRINT("SERVER: PUBLISH\n");

    if (NULL != info && 0 < ninfo) {
        if (NULL != pubdata) {
            PMIX_PDATA_FREE(pubdata, npub);
        }
        npub = ninfo;
        PMIX_PDATA_CREATE(pubdata, npub);
        for (n=0; n < npub; n++) {
            (void)strncpy(pubdata[n].proc.nspace, proc->nspace, PMIX_MAX_NSLEN);
            pubdata[n].proc.rank = proc->rank;
            (void)strncpy(pubdata[n].key, info[n].key, PMIX_MAX_KEYLEN);
            pmix_value_xfer(&pubdata[n].value, (pmix_value_t*)&info[n].value);
        }
    }

    if (NULL != cbfunc) {
        cbfunc(PMIX_SUCCESS, cbdata);
    }
    return PMIX_SUCCESS;
}


static pmix_status_t lookup_fn(const pmix_proc_t *proc, char **keys,
                     const pmix_info_t info[], size_t ninfo,
                     pmix_lookup_cbfunc_t cbfunc, void *cbdata)
{
    size_t i, k, n;
    pmix_pdata_t *pd = NULL;
    pmix_status_t ret = PMIX_ERR_NOT_FOUND;
    char **results = NULL;

    PMIX_TEST_PRINT("SERVER: LOOKUP\n");

    for (n=0; NULL != keys[n]; n++) {
        for(k=0; k < npub; k++) {
            if (0 == strncmp(keys[n], pubdata[k].key, PMIX_MAX_KEYLEN)) {
                PMIX_ARGV_APPEND(i, results, keys[n]);
                break;
            }
        }
    }
    PMIX_ARGV_COUNT(i, results);
    if (0 < i) {
        PMIX_PDATA_CREATE(pd, i);
        for (n=0; NULL != results[n]; n++) {
            /* find this key in the published data */
            for (k=0; k < npub; k++) {
                if (0 == strncmp(results[n], pubdata[k].key, PMIX_MAX_KEYLEN)) {
                    (void)strncpy(pd[n].proc.nspace, pubdata[k].proc.nspace, PMIX_MAX_NSLEN);
                    pd[n].proc.rank = pubdata[k].proc.rank;
                    (void)strncpy(pd[n].key, pubdata[k].key, PMIX_MAX_KEYLEN);
                    pmix_value_xfer(&pd[n].value, &pubdata[k].value);
                    break;
                }
            }
        }
        PMIX_ARGV_FREE(results);
    }
    if (NULL != cbfunc) {
        cbfunc(ret, pd, i, cbdata);
    }
    if (0 < i) {
        PMIX_PDATA_FREE(pd, i);
    }
    return PMIX_SUCCESS;
}


static pmix_status_t unpublish_fn(const pmix_proc_t *proc, char **keys,
                        const pmix_info_t info[], size_t ninfo,
                        pmix_op_cbfunc_t cbfunc, void *cbdata)
{
    PMIX_TEST_PRINT("SERVER: UNPUBLISH\n");

    if (NULL != cbfunc) {
        cbfunc(PMIX_SUCCESS, cbdata);
    }
    return PMIX_SUCCESS;
}

static void spcbfunc(pmix_status_t status, void *cbdata)
{
    myxfer_t *x = (myxfer_t*)cbdata;

    if (NULL != x->spcbfunc) {
        x->spcbfunc(PMIX_SUCCESS, "DYNSPACE", x->cbdata);
    }
}

static pmix_status_t spawn_fn(const pmix_proc_t *proc,
                    const pmix_info_t job_info[], size_t ninfo,
                    const pmix_app_t apps[], size_t napps,
                    pmix_spawn_cbfunc_t cbfunc, void *cbdata)
{
    myxfer_t *x;
    size_t n;
    pmix_proc_t *pptr;
    bool spawned;

    PMIX_TEST_PRINT("SERVER: SPAWN\n");

    /* check the job info for parent and spawned keys */
    for (n=0; n < ninfo; n++) {
        if (0 == strncmp(job_info[n].key, PMIX_PARENT_ID, PMIX_MAX_KEYLEN)) {
            pptr = job_info[n].value.data.proc;
            if (verbose) {
                fprintf(stderr, "SPAWN: Parent ID %s:%d\n", pptr->nspace, pptr->rank);
            }
        } else if (0 == strncmp(job_info[n].key, PMIX_SPAWNED, PMIX_MAX_KEYLEN)) {
            spawned = PMIX_INFO_TRUE(&job_info[n]);
            if (verbose) {
                fprintf(stderr, "SPAWN: Spawned %s\n", spawned ? "TRUE" : "FALSE");
            }
        }
    }

    /* in practice, we would pass this request to the local
     * resource manager for launch, and then have that server
     * execute our callback function. For now, we will fake
     * the spawn and just pretend */

    /* must register the nspace for the new procs before
     * we return to the caller */
    x = (myxfer_t*)malloc(sizeof(myxfer_t));
    xfcon(x);
    x->spcbfunc = cbfunc;
    x->cbdata = cbdata;

    set_namespace(2, "0,1", "DYNSPACE", spcbfunc, x);

    return PMIX_SUCCESS;
}

static int numconnects = 0;

static pmix_status_t connect_fn(const pmix_proc_t procs[], size_t nprocs,
                                const pmix_info_t info[], size_t ninfo,
                                pmix_op_cbfunc_t cbfunc, void *cbdata)
{
    PMIX_TEST_PRINT("SERVER: CONNECT\n");

    /* in practice, we would pass this request to the local
     * resource manager for handling */

    numconnects++;

    if (NULL != cbfunc) {
        cbfunc(PMIX_SUCCESS, cbdata);
    }

    return PMIX_SUCCESS;
}


static pmix_status_t disconnect_fn(const pmix_proc_t procs[], size_t nprocs,
                                   const pmix_info_t info[], size_t ninfo,
                                   pmix_op_cbfunc_t cbfunc, void *cbdata)
{
    PMIX_TEST_PRINT("SERVER: DISCONNECT\n");

    /* in practice, we would pass this request to the local
     * resource manager for handling */

    if (NULL != cbfunc) {
        cbfunc(PMIX_SUCCESS, cbdata);
    }

    return PMIX_SUCCESS;
}

static pmix_status_t register_event_fn(pmix_status_t *codes, size_t ncodes,
                                       const pmix_info_t info[], size_t ninfo,
                                       pmix_op_cbfunc_t cbfunc, void *cbdata)
{
    if (NULL != cbfunc) {
        cbfunc(PMIX_SUCCESS, cbdata);
    }
    return PMIX_SUCCESS;
}

static pmix_status_t deregister_events(pmix_status_t *codes, size_t ncodes,
                                       pmix_op_cbfunc_t cbfunc, void *cbdata)
{
    return PMIX_SUCCESS;
}

static pmix_status_t notify_event(pmix_status_t code,
                                  const pmix_proc_t *source,
                                  pmix_data_range_t range,
                                  pmix_info_t info[], size_t ninfo,
                                  pmix_op_cbfunc_t cbfunc, void *cbdata)
{
    return PMIX_SUCCESS;
}

typedef struct query_data_t {
    pmix_info_t *data;
    size_t ndata;
} query_data_t;

static pmix_status_t query_fn(pmix_proc_t *proct,
                              pmix_query_t *queries, size_t nqueries,
                              pmix_info_cbfunc_t cbfunc,
                              void *cbdata)
{
    size_t n;
    pmix_info_t *info;

    PMIX_TEST_PRINT("SERVER: QUERY\n");

    if (NULL == cbfunc) {
        return PMIX_ERROR;
    }
    /* keep this simple */
    PMIX_INFO_CREATE(info, nqueries);
    for (n=0; n < nqueries; n++) {
        if (verbose) {
            fprintf(stderr, "\tKey: %s\n", queries[n].keys[0]);
        }
        (void)strncpy(info[n].key, queries[n].keys[0], PMIX_MAX_KEYLEN);
        info[n].value.type = PMIX_STRING;
        if (0 > asprintf(&info[n].value.data.string, "%d", (int)n)) {
            return PMIX_ERROR;
        }
    }
    cbfunc(PMIX_SUCCESS, info, nqueries, cbdata, NULL, NULL);
    return PMIX_SUCCESS;
}

static void tool_connect_fn(pmix_info_t *info, size_t ninfo,
                            pmix_tool_connection_cbfunc_t cbfunc,
                            void *cbdata)
{
    pmix_proc_t proc;

    PMIX_TEST_PRINT("SERVER: TOOL CONNECT\n");

    /* just pass back an arbitrary nspace */
    (void)strncpy(proc.nspace, "TOOL", PMIX_MAX_NSLEN);
    proc.rank = 0;

    if (NULL != cbfunc) {
        cbfunc(PMIX_SUCCESS, &proc, cbdata);
    }
}

static void log_fn(const pmix_proc_t *client,
                   const pmix_info_t data[], size_t ndata,
                   const pmix_info_t directives[], size_t ndirs,
                   pmix_op_cbfunc_t cbfunc, void *cbdata)
{
    PMIX_TEST_PRINT("SERVER: LOG\n");

    if (NULL != cbfunc) {
        cbfunc(PMIX_SUCCESS, cbdata);
    }
}

static void wait_signal_callback(int fd, short event, void *arg)
{
    debug_event_t *sig = (debug_event_t*) arg;
    int status;
    pid_t pid;
    wait_tracker_t *t2;
    size_t n;

    if (SIGCHLD != event_get_signal(sig)) {
        return;
    }

    /* we can have multiple children leave but only get one
     * sigchild callback, so reap all the waitpids until we
     * don't get anything valid back */
    while (1) {
        pid = waitpid(-1, &status, WNOHANG);
        if (-1 == pid && EINTR == errno) {
            /* try it again */
            continue;
        }
        /* if we got garbage, then nothing we can do */
        if (pid <= 0) {
            return;
        }

        /* we are already in an event, so it is safe to access the list */
        for(n=0; n < nprocs; n++) {
            if (pid == children[n].pid) {
                /* found it! */
                if (WIFEXITED(status)) {
                    children[n].exit_code = WEXITSTATUS(status);
                } else {
                    if (WIFSIGNALED(status)) {
                        children[n].exit_code = WTERMSIG(status) + 128;
                    }
                }
                if (0 != children[n].exit_code && 0 == exit_code) {
                    exit_code = children[n].exit_code;
                }
                --wakeup;
                break;
            }
        }
    }
}
