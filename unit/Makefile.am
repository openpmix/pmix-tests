# Copyright (c) 2019      Intel, Inc. All rights reserved.

ACLOCAL_AMFLAGS = -Iconfig

bin_PROGRAMS = pmix_test pmix_client pmix_regex pmi_client pmi2_client

headers = test_common.h cli_stages.h server_callbacks.h utils.h test_fence.h \
        test_publish.h test_spawn.h test_cd.h test_resolve_peers.h test_error.h \
        test_replace.h test_internal.h test_server.h argv.h pmix_object.h unit_list.h \
        unit_progress_threads.h

sources = cli_stages.c test_cd.c test_common.c test_error.c \
		test_fence.c test_internal.c test_publish.c test_replace.c test_resolve_peers.c \
		test_spawn.c utils.c argv.c pmix_object.c unit_list.c unit_progress_threads.c

pmix_test_SOURCES = pmix_test.c $(sources) test_server.c server_callbacks.c

pmix_client_SOURCES =  pmix_client.c $(sources)

pmix_regex_SOURCES =  pmix_regex.c $(sources) test_server.c server_callbacks.c

pmi_client_SOURCES = pmi_client.c $(sources)
pmi_client_LDADD = -lpmi

pmi2_client_SOURCES = pmi2_client.c $(sources)
pmi2_client_LDADD = -lpmi2

clean-local:
	rm -f $(noinst_PROGS) *.o *~
