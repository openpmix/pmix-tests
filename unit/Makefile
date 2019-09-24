# Copyright (c) 2019      Intel, Inc. All rights reserved.

PROGS = pmix_test pmix_client pmix_regex pmi_client pmi2_client

all: $(PROGS)

headers = test_common.h cli_stages.h server_callbacks.h utils.h test_fence.h \
        test_publish.h test_spawn.h test_cd.h test_resolve_peers.h test_error.h \
        test_replace.h test_internal.h test_server.h argv.h pmix_object.h unit_list.h \
        unit_progress_threads.h

sources = cli_stages.c test_cd.c test_common.c test_error.c \
		test_fence.c test_internal.c test_publish.c test_replace.c test_resolve_peers.c \
		test_spawn.c utils.c argv.c pmix_object.c unit_list.c unit_progress_threads.c

pmix_test: pmix_test.c $(sources) test_server.c server_callbacks.c
	$(CC) -I./ -I$(PMIXHOME)/include -L$(PMIXHOME)/lib -I$(EVENTHOME)/include -L$(EVENTHOME)/lib -o pmix_test pmix_test.c $(sources) test_server.c server_callbacks.c -lpmix -levent

pmix_client: pmix_client.c $(sources)
	$(CC) -I./ -I$(PMIXHOME)/include -L$(PMIXHOME)/lib -I$(EVENTHOME)/include -L$(EVENTHOME)/lib -o pmix_client pmix_client.c $(sources) -lpmix -levent

pmix_regex: pmix_regex.c $(sources) test_server.c server_callbacks.c
	$(CC) -I./ -I$(PMIXHOME)/include -L$(PMIXHOME)/lib -I$(EVENTHOME)/include -L$(EVENTHOME)/lib -o pmix_regex pmix_regex.c $(sources) test_server.c server_callbacks.c -lpmix -levent

pmi_client: pmi_client.c $(sources)
	$(CC) -I./ -I$(PMIXHOME)/include -L$(PMIXHOME)/lib -I$(EVENTHOME)/include -L$(EVENTHOME)/lib -o pmi_client pmi_client.c $(sources) -lpmi -levent

pmi2_client: pmi2_client.c $(sources)
	$(CC) -I./ -I$(PMIXHOME)/include -L$(PMIXHOME)/lib -I$(EVENTHOME)/include -L$(EVENTHOME)/lib -o pmi2_client pmi2_client.c $(sources) -lpmi2 -levent

-include $(SRC:%.c=%.d)

clean:
	rm -f $(PROGS) *.o *~
