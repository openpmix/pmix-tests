

# We are not striving for performance, so set debug flags
CFLAGS += -g
LIBS=-lutil -levent_pthreads

all_static: progress_thread.o simptest_static simpclient_static

all: progress_thread.o simptest simpclient

progress_thread.o: progress_thread.c
	$(CC) -I$(LIBEVENT_HOME)/include -I$(PMIX_HOME)/include -c progress_thread.c

simptest: simptest.c progress_thread.c
	$(CC) -I$(PMIX_HOME)/include -L$(PMIX_HOME)/lib -I$(LIBEVENT_HOME)/include -L$(LIBEVENT_HOME)/lib -lpmix -levent -o simptest simptest.c progress_thread.o

simptest_static: simptest.c progress_thread.c
	$(CC) -I$(PMIX_HOME)/include -I$(LIBEVENT_HOME)/include -L$(LIBEVENT_HOME)/lib -levent_pthreads -levent -I$(HWLOC_HOME)/include -L$(HWLOC_HOME)/lib -lhwloc -lpthread -lutil -o simptest simptest.c progress_thread.o $(PMIX_HOME)/lib/libpmix.a

simpclient: simpclient.c
	$(CC) -I$(PMIX_HOME)/include -L$(PMIX_HOME)/lib -I$(LIBEVENT_HOME)/include -L$(LIBEVENT_HOME)/lib -lpmix -levent -o simpclient simpclient.c

simpclient_static: simpclient.c
	$(CC) -I$(PMIX_HOME)/include -I$(LIBEVENT_HOME)/include -L$(LIBEVENT_HOME)/lib -levent_pthreads -levent -I$(HWLOC_HOME)/include -L$(HWLOC_HOME)/lib -lhwloc -lpthread -lutil -o simpclient simpclient.c $(PMIX_HOME)/lib/libpmix.a

clean:
	rm -f *.o simptest simpclient
