# -*- shell-script -*-
#
# Copyright (c) 2009-2015 Cisco Systems, Inc.  All rights reserved.
# Copyright (c) 2013      Los Alamos National Security, LLC.  All rights reserved.
# Copyright (c) 2013-2019 Intel, Inc.  All rights reserved.
# $COPYRIGHT$
#
# Additional copyrights may follow
#
# $HEADER$
#

# MCA_hwloc_CONFIG([action-if-found], [action-if-not-found])
# --------------------------------------------------------------------
AC_DEFUN([PMIXUNIT_HWLOC_CONFIG],[
    PMIXUNIT_VAR_SCOPE_PUSH([pmix_unit_hwloc_dir pmix_unit_hwloc_libdir pmix_unit_hwloc_standard_lib_location pmix_unit_hwloc_standard_header_location])

    AC_ARG_WITH([hwloc-header],
                [AC_HELP_STRING([--with-hwloc-header=HEADER],
                                [The value that should be included in C files to include hwloc.h])])


    AC_ARG_WITH([hwloc],
                [AC_HELP_STRING([--with-hwloc=DIR],
                                [Search for hwloc headers and libraries in DIR ])])

    AC_ARG_WITH([hwloc-libdir],
                [AC_HELP_STRING([--with-hwloc-libdir=DIR],
                                [Search for hwloc libraries in DIR ])])

    pmix_unit_hwloc_support=0
    pmix_unit_check_hwloc_save_CPPFLAGS="$CPPFLAGS"
    pmix_unit_check_hwloc_save_LDFLAGS="$LDFLAGS"
    pmix_unit_check_hwloc_save_LIBS="$LIBS"

    if test "$with_hwloc" != "no"; then
        AC_MSG_CHECKING([for hwloc in])
        if test ! -z "$with_hwloc" && test "$with_hwloc" != "yes"; then
            pmix_unit_hwloc_dir=$with_hwloc/include
            pmix_unit_hwloc_standard_header_location=no
            pmix_unit_hwloc_standard_lib_location=no
            AS_IF([test -z "$with_hwloc_libdir" || test "$with_hwloc_libdir" = "yes"],
                  [if test -d $with_hwloc/lib64; then
                       pmix_unit_hwloc_libdir=$with_hwloc/lib64
                   elif test -d $with_hwloc/lib; then
                       pmix_unit_hwloc_libdir=$with_hwloc/lib
                   else
                       AC_MSG_RESULT([Could not find $with_hwloc/lib or $with_hwloc/lib64])
                       AC_MSG_ERROR([Can not continue])
                   fi
                   AC_MSG_RESULT([$pmix_unit_hwloc_dir and $pmix_unit_hwloc_libdir])],
                  [AC_MSG_RESULT([$with_hwloc_libdir])])
        else
            pmix_unit_hwloc_dir=/usr/include
            if test -d /usr/lib64; then
                pmix_unit_hwloc_libdir=/usr/lib64
            elif test -d /usr/lib; then
                pmix_unit_hwloc_libdir=/usr/lib
            else
                AC_MSG_RESULT([not found])
                AC_MSG_WARN([Could not find /usr/lib or /usr/lib64 - you may])
                AC_MSG_WARN([need to specify --with-hwloc_libdir=<path>])
                AC_MSG_ERROR([Can not continue])
            fi
            AC_MSG_RESULT([(default search paths)])
            pmix_unit_hwloc_standard_header_location=yes
            pmix_unit_hwloc_standard_lib_location=yes
        fi
        AS_IF([test ! -z "$with_hwloc_libdir" && test "$with_hwloc_libdir" != "yes"],
              [pmix_unit_hwloc_libdir="$with_hwloc_libdir"
               pmix_unit_hwloc_standard_lib_location=no])

        PMIXUNIT_CHECK_PACKAGE([pmix_unit_hwloc],
                           [hwloc.h],
                           [hwloc],
                           [hwloc_topology_init],
                           [-lhwloc],
                           [$pmix_unit_hwloc_dir],
                           [$pmix_unit_hwloc_libdir],
                           [pmix_unit_hwloc_support=1],
                           [pmix_unit_hwloc_support=0])
    fi

    if test ! -z "$with_hwloc" && test "$with_hwloc" != "no" && test "$pmix_unit_hwloc_support" != "1"; then
        AC_MSG_WARN([HWLOC SUPPORT REQUESTED AND NOT FOUND])
        AC_MSG_ERROR([CANNOT CONTINUE])
    fi

    if test "$pmix_unit_hwloc_support" = "1"; then
        AC_MSG_CHECKING([if external hwloc version is 1.5 or greater])
        AC_COMPILE_IFELSE(
              [AC_LANG_PROGRAM([[#include <hwloc.h>]],
              [[
    #if HWLOC_API_VERSION < 0x00010500
    #error "hwloc API version is less than 0x00010500"
    #endif
              ]])],
              [AC_MSG_RESULT([yes])],
              [AC_MSG_RESULT([no])
               AC_MSG_ERROR([Cannot continue])])
    fi

    CPPFLAGS="$pmix_unit_check_hwloc_save_CPPFLAGS"
    LDFLAGS="$pmix_unit_check_hwloc_save_LDFLAGS"
    LIBS="$pmix_unit_check_hwloc_save_LIBS"

    AC_MSG_CHECKING([will hwloc support be built])
    if test "$pmix_unit_hwloc_support" != "1"; then
        AC_MSG_RESULT([no])
        pmix_unit_hwloc_source=none
        pmix_unit_hwloc_support_will_build=no
        PMIX_HWLOC_HEADER=
    else
        AC_MSG_RESULT([yes])
        pmix_unit_hwloc_source=$pmix_unit_hwloc_dir
        pmix_unit_hwloc_support_will_build=yes
        # Set output variables
        PMIX_HWLOC_HEADER="<hwloc.h>"
        AS_IF([test "$pmix_unit_hwloc_standard_header_location" != "yes"],
              [PMIXUNIT_FLAGS_APPEND_UNIQ(CPPFLAGS, $pmix_unit_hwloc_CPPFLAGS)
               PMIXUNIT_FLAGS_APPEND_UNIQ(LDFLAGS, $pmix_unit_hwloc_LDFLAGS)])
        PMIXUNIT_FLAGS_APPEND_UNIQ(LIBS, $pmix_unit_hwloc_LIBS)
    fi

    PMIXUNIT_VAR_SCOPE_POP
])dnl
