PMIX     = $(PMIX_HOME)

CC       = gcc
CPPFLAGS = -I$(PMIX)/include
CFLAGS   = -ggdb -Wall
LD       = $(CC)
LDFLAGS  = -L$(PMIX)/lib -Wl,-rpath,$(PMIX)/lib
LIBS     = -lpmix

SOURCES  = $(wildcard *.c)
OBJECTS  = $(SOURCES:.c=.o)

.PHONY: all clean

all:	jctrl

clean:
	rm -f $(OBJECTS)
	rm -f jctrl

jctrl:	$(OBJECTS)
	$(LD) $(LDFLAGS) -o $@ $^ $(LIBS)
