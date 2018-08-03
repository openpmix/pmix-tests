

# We are not striving for performance, so set debug flags
CFLAGS += -g

all: progress_thread.o simptest simpclient

progress_thread.o: progress_thread.c
	$(CC) -I$(LIBEVENT_HOME)/include -I$(PMIX_HOME)/include -c progress_thread.c

simptest: simptest.c progress_thread.c
	$(CC) -I$(PMIX_HOME)/include -L$(PMIX_HOME)/lib -I$(LIBEVENT_HOME)/include -L$(LIBEVENT_HOME)/lib -lpmix -levent -o simptest simptest.c progress_thread.o

simpclient: simpclient.c
	$(CC) -I$(PMIX_HOME)/include -L$(PMIX_HOME)/lib -I$(LIBEVENT_HOME)/include -L$(LIBEVENT_HOME)/lib -lpmix -levent -o simpclient simpclient.c

clean:
	rm -f *.o simptest simpclient
