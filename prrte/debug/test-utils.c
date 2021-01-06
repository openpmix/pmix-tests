#define _GNU_SOURCE

#include <pthread.h>
#include <dlfcn.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <sys/types.h>

#include "test-utils.h"

#define MAX_NAMESPACES 10
#define STDOUT_FD 1
#define STDERR_FD 2

int (*real_printf)(const char *format, ...);
int (*real_fprintf)(FILE *stream, const char *format, ...);
int (*real_fputs)(const char *s, FILE *stream);
int (*real_fwrite)(const void *ptr, size_t size, size_t nmemb, FILE *stream);
int (*real_puts)(const char *s);
int (*real_vfprintf)(FILE *stream, const char *format, va_list args);
int (*real_vprintf)(const char *format, va_list args);

static char *orig_namespace[MAX_NAMESPACES];
static char renamed_namespace[10];
static int line_number;
static char *my_rank = NULL;
static int lock_handle;
static pthread_mutex_t thread_lock = PTHREAD_MUTEX_INITIALIZER;

void cleanup(void) {
    unlink("/tmp/pmix-test-lockfile");
}

char *ns(char *namespace_in) {

return namespace_in;

    int i = 0;
    while ((i < MAX_NAMESPACES) && (NULL != orig_namespace[i])) {
        if (0 == strcmp(namespace_in, orig_namespace[i])) {
            sprintf(renamed_namespace, "NSPACE.%d", i);
            return renamed_namespace;
        }
        i = i + 1;
    }
    if (i >= MAX_NAMESPACES) {
        printf("Too many namespaces\n");
        return "";
    }
    orig_namespace[i] = strdup(namespace_in);
    sprintf(renamed_namespace, "NSPACE.%d", i);
    return renamed_namespace;
}

/*
 * Implement wrappers for stdio write functions that are used in testcases.
 * These wrappers write the tag prefix and then the text that is written
 * in the testcase.
 * All that should be required is wrappers for printf and fprintf. However, gcc
 * translates 'printf("Hi\n")' to 'puts("Hi")' and 'fprintf(stderr, "Hi\n")' to
 * 'fwrite("Hi\n", 1, strlen("Hi\n"), stderr)'. So wrappers for puts, fputs and
 * fwrite are also implemented.
 * Also, output from multiple threads and multiple processes can be interspersed
 * in the output file. To avoid this, the wrappers each lock before writing a
 * line of text and unlock after writing the line. 
 * Unfortunately, flock only enforces locks between processes and not threads,
 * and pthread_mutex_lock only enforces locks between threads. Therefore, two
 * locks are required. 
 * The locks can affect the timing of output, but for the intended use of
 * verifying basic functionality, this shuld not matter.
 */

void lock_stream() {
    if (0 < lock_handle) {
        flock(lock_handle, LOCK_EX);
    }
    pthread_mutex_lock(&thread_lock);
}

void unlock_stream() {
    pthread_mutex_unlock(&thread_lock);
    if (0 < lock_handle) {
        flock(lock_handle, LOCK_UN);
    }
}

void printf_common() {
    char *emsg;
    if (NULL == real_printf) {
        real_printf = dlsym(RTLD_NEXT, "printf");
        if (NULL == real_printf) {
            emsg = "Unable to resolve printf libc version function address\n";
            write(STDERR_FD, emsg, strlen(emsg));
            exit(1);
        }
    }
    if (NULL == real_fprintf) {
        real_fprintf = dlsym(RTLD_NEXT, "fprintf");
        if (NULL == real_fprintf) {
            emsg = "Unable to resolve fprintf libc version function address\n";
            write(STDERR_FD, emsg, strlen(emsg));
            exit(1);
        }
    }
    if (NULL == real_vfprintf) {
        real_vfprintf = dlsym(RTLD_NEXT, "vfprintf");
        if (NULL == real_vfprintf) {
            emsg = "Unable to resolve vfprintf libc version function address\n";
            write(STDERR_FD, emsg, strlen(emsg));
            exit(1);
        }
    }
    if (NULL == real_vprintf) {
        real_vprintf = dlsym(RTLD_NEXT, "vprintf");
        if (NULL == real_vprintf) {
            emsg = "Unable to resolve vprintf libc version function address\n";
            write(STDERR_FD, emsg, strlen(emsg));
            exit(1);
        }
    }
    if (NULL == real_fwrite) {
        real_fwrite = dlsym(RTLD_NEXT, "fwrite");
        if (NULL == real_fwrite) {
            emsg = "Unable to resolve fwrite libc version function address\n";
            write(STDERR_FD, emsg, strlen(emsg));
            exit(1);
        }
    }
    if (NULL == real_puts) {
        real_puts = dlsym(RTLD_NEXT, "puts");
        if (NULL == real_puts) {
            emsg = "Unable to resolve puts libc version function address\n";
            write(STDERR_FD, emsg, strlen(emsg));
            exit(1);
        }
    }
    if (NULL == real_fputs) {
        real_fputs = dlsym(RTLD_NEXT, "fputs");
        if (NULL == real_vfprintf) {
            emsg = "Unable to resolve fputs libc version function address\n";
            write(STDERR_FD, emsg, strlen(emsg));
            exit(1);
        }
    }
    if (NULL == my_rank) {
        char *envp = getenv("PMIX_RANK");
        if (NULL == envp) {
            my_rank = "";
        }
        else {
            my_rank = envp;
        }
        atexit(cleanup);
        lock_handle = open("/tmp/pmix-test-lockfile", O_RDWR | O_CREAT);
        if (-1 != lock_handle) {
            write(lock_handle, "lock", 4);
        }
    }
}

int fprintf(FILE *stream, const char *format, ...) {
    va_list args;
    char prefix[20];
    int n;

    printf_common();
    lock_stream();
    va_start(args, format);
    if ('\0' == my_rank[0]) {
        strcpy(prefix, TPRINT_PFX);
    }
    else {
        sprintf(prefix, "%s-%s", TPRINT_PFX, my_rank);
    }
    n = real_fprintf(stream, "%-10s:%03d: ", prefix, ++line_number);
    n = n + real_vfprintf(stream, format, args);
    fflush(stream);
    va_end(args);
    unlock_stream();
    return n;
}

int printf(const char *format, ...) {
    va_list args;
    char prefix[20];
    int n;

    printf_common();
    lock_stream();
    va_start(args, format);
    if ('\0' == my_rank[0]) {
        strcpy(prefix, TPRINT_PFX);
    }
    else {
        sprintf(prefix, "%s-%s", TPRINT_PFX, my_rank);
    }
    n = real_printf("%-10s:%03d: ", prefix, ++line_number);
    n = n + real_vprintf(format, args);
    fflush(stdout);
    va_end(args);
    unlock_stream();
    return n;
}

int fputs(const char *s, FILE *stream) {
    char prefix[20];
    int n;

    printf_common();
    lock_stream();
    if ('\0' == my_rank[0]) {
        strcpy(prefix, TPRINT_PFX);
    }
    else {
        sprintf(prefix, "%s-%s", TPRINT_PFX, my_rank);
    }
    real_fprintf(stream, "%-10s:%03d: ", prefix, ++line_number);
    n = real_fputs(s, stream);
    fflush(stream);
    unlock_stream();
    return n;
}

int puts(const char *s) {
    char prefix[20];
    int n;

    printf_common();
    lock_stream();
    if ('\0' == my_rank[0]) {
        strcpy(prefix, TPRINT_PFX);
    }
    else {
        sprintf(prefix, "%s-%s", TPRINT_PFX, my_rank);
    }
    real_fprintf(stdout, "%-10s:%03d: ", prefix, ++line_number);
    n = real_puts(s);
    fflush(stdout);
    unlock_stream();
    return n;
}

size_t fwrite(const void *ptr, size_t size, size_t nmemb, FILE *stream) {
    char prefix[20];
    int n;

    printf_common();
    lock_stream();
    if ('\0' == my_rank[0]) {
        strcpy(prefix, TPRINT_PFX);
    }
    else {
        sprintf(prefix, "%s-%s", TPRINT_PFX, my_rank);
    }
    // Setting 'n' assumes the original fwrite is writing 'nmemb' characters
    n = real_fprintf(stream, "%-10s:%03d: ", prefix, ++line_number);
    n = n + real_fwrite(ptr, size, nmemb, stream);
    fflush(stream);
    unlock_stream();
    return n;
}
