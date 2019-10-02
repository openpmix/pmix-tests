# -*- shell-script -*-
#
# $HEADER$
#

#
# Init autoconf
#

AC_PREREQ([2.69])
AC_INIT([pmix-unit], [1.0], [http://pmix.org], [pmix-unit])
AC_CONFIG_AUX_DIR([config])
AC_CONFIG_MACRO_DIR([config])

echo "Configuring PMIx unit test suite"
PMIXUNIT_CONFIGURE_SETUP
AC_CANONICAL_TARGET
AM_INIT_AUTOMAKE([1.10 foreign -Wall -Werror])

# If Automake supports silent rules, enable them.
m4_ifdef([AM_SILENT_RULES], [AM_SILENT_RULES([yes])])

#
# This is useful later
#

AC_CANONICAL_HOST
AC_DEFINE_UNQUOTED(PMIXTEST_ARCH, "$host",
    [Architecture that we are compiled for])

# Define some basic useful values
PMIXUNIT_BASIC_SETUP

#
# Find out if we're just making a distribution tarball and not going
# to try to compile
#

AC_ARG_ENABLE(dist,
    AC_HELP_STRING([--enable-dist],
        [do not try to compile; configure just so that we can make a distribution tarball]))

#
# Get C compiler
#

if test "$CC" != ""; then
    BASE="`basename $CC`"
else
    BASE=
fi
if test "$BASE" = "" -o "$BASE" = "." -o "$BASE" = "cc" -o \
    "$BASE" = "gcc" -o "$BASE" = "xlc" -o "$BASE" = "pgcc" -o \
    "$BASE" = "icc"; then
    AC_CHECK_PROG(HAVE_PMIXCC, pmixcc, yes, no)
    if test "$HAVE_PMIXCC" = "yes"; then
        CC=pmixcc
        export CC
    fi
fi

CFLAGS_save=$CFLAGS
AC_PROG_CC_C99
CFLAGS=$CFLAGS_save

#
# Because these are meant to be used for debugging, after all
#

if test -z "$CFLAGS"; then
    CFLAGS="-g"
fi

# This did not exist pre AM 1.11.x (where x is somewhere >0 and <3),
# but it is necessary in AM 1.12.x.
ifdef([AM_PROG_AR], [AM_PROG_AR])
LT_INIT([disable-shared])

#
# Setup hwloc
#
PMIXUNIT_HWLOC_CONFIG

#
# Setup libevent
#
PMIXUNIT_LIBEVENT_CONFIG

#
# Find PMIx installation
#

PMIXUNIT_CHECK_PMIX

#
# Ensure that we can compile and link a PMIx program
#

AC_CHECK_HEADER([pmix.h], [], [AC_MSG_WARN([Cannot find pmix.h])
                               AC_MSG_ERROR([Cannot continue])])
AC_CHECK_FUNC([PMIx_Init], [], [AC_MSG_WARN([Cannot find PMIx_Init symbol])
                                AC_MSG_ERROR([Cannot continue])])

#
# Party on
#

AC_CONFIG_FILES([
    Makefile
])
AC_OUTPUT
