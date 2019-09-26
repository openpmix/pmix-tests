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

ifndef PMIXHOME
ifneq ("$(wildcard /usr/include/pmix.h)","")
	export PMIXHOME=/usr
endif
endif

ifndef PMIXHOME
ifneq ("$(wildcard /usr/local/include/pmix.h)","")
	export PMIXHOME=/usr/local
endif
endif

ifndef PMIXHOME
ifneq ("$(wildcard /opt/include/pmix.h)","")
	export PMIXHOME=/opt
endif
endif

ifndef PMIXHOME
ifneq ("$(wildcard /opt/local/include/pmix.h)","")
	export PMIXHOME=/opt/local
endif
endif

ifdef PMIXHOME
	export PMIXFIND=-I$(PMIXHOME)/include -L$(PMIXHOME)/lib -L$(PMIXHOME)/lib64
else
	export PMIXFIND=
endif

ifndef EVENTHOME
ifneq ("$(wildcard /usr/include/event.h)","")
	export EVENTHOME=/usr
endif
endif

ifndef EVENTHOME
ifneq ("$(wildcard /usr/local/include/event.h)","")
	export EVENTHOME=/usr/local
endif
endif

ifndef EVENTHOME
ifneq ("$(wildcard /opt/include/event.h)","")
	export EVENTHOME=/opt
endif
endif

ifndef EVENTHOME
ifneq ("$(wildcard /opt/local/include/event.h)","")
	export EVENTHOME=/opt/local
endif
endif

ifdef EVENTHOME
	export EVENTFIND=-I$(EVENTHOME)/include -L$(EVENTHOME)/lib -L$(EVENTHOME)/lib64
else
	export EVENTFIND=
endif


pmix_test: pmix_test.c $(sources) test_server.c server_callbacks.c
	$(CC) -I./ $(PMIXFIND) $(EVENTFIND) -o pmix_test pmix_test.c $(sources) test_server.c server_callbacks.c -lpmix -levent

pmix_client: pmix_client.c $(sources)
	$(CC) -I./ $(PMIXFIND) $(EVENTFIND) -o pmix_client pmix_client.c $(sources) -lpmix -levent

pmix_regex: pmix_regex.c $(sources) test_server.c server_callbacks.c
	$(CC) -I./ $(PMIXFIND) $(EVENTFIND) -o pmix_regex pmix_regex.c $(sources) test_server.c server_callbacks.c -lpmix -levent

pmi_client: pmi_client.c $(sources)
	$(CC) -I./ $(PMIXFIND) $(EVENTFIND) -o pmi_client pmi_client.c $(sources) -lpmi -levent

pmi2_client: pmi2_client.c $(sources)
	$(CC) -I./ $(PMIXFIND) $(EVENTFIND) -o pmi2_client pmi2_client.c $(sources) -lpmi2 -levent

-include $(SRC:%.c=%.d)

clean:
	rm -f $(PROGS) *.o *~
