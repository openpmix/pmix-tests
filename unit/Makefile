# Copyright (c) 2019      Intel, Inc. All rights reserved.

PROGS = pmix_test pmix_client pmix_regex pmi_client pmi2_client

all: $(PROGS)

headers = test_common.h cli_stages.h server_callbacks.h utils.h test_fence.h \
        test_publish.h test_spawn.h test_cd.h test_resolve_peers.h test_error.h \
        test_replace.h test_internal.h test_server.h

sources = cli_stages.c test_cd.c test_common.c test_error.c \
		test_fence.c test_internal.c test_publish.c test_replace.c test_resolve_peers.c \
		test_spawn.c utils.c

pmix_test: pmix_test.c $(sources)
	$(CC) -o pmix_test pmix_test.c $(sources) test_server.c server_callbacks.c

pmix_client: pmix_client.c $(sources)
	$(CC) -o pmix_client pmix_client.c $(sources)

pmix_regex: pmix_regex.c $(sources)
	$(CC) -o pmix_regex pmix_regex.c $(sources) test_server.c server_callbacks.c

pmi_client: pmi_client.c $(sources)
	$(CC) -o pmi_client pmi_client.c $(sources) -lpmi

pmi2_client: pmi2_client.c $(sources)
	$(CC) -o pmi2_client pmi2_client.c $(sources) -lpmi2

-include $(SRC:%.c=%.d)

clean:
	rm -f $(PROGS) *.o *~
