CC=gcc
.PHONY: pagecollect
all: pagecollect simple_run capaging

pagecollect:
	cd pagecollect && $(MAKE)

simple_run: simple_run.c pagecollect/page-collect.c
	$(CC) -o $@ $^ -lnuma

capaging: capaging.c
	$(CC) -o $@ $^

test: tests/test.c tests/aux.h
	$(CC) -o $@ $^

test2: tests/test2.c tests/aux.h
	$(CC) -o $@ $^

clean:
	-rm simple_run capaging test test2
	cd pagecollect && $(MAKE) clean