CC=gcc
.PHONY: pagecollect
all: pagecollect simple_run capaging

pagecollect:
	cd pagecollect && $(MAKE)

simple_run: simple_run.c pagecollect/page-collect.c
	$(CC) -o $@ $^ -lnuma

capaging: capaging.c
	$(CC) -o $@ $^

test: tests/test.c
	$(CC) -o $@ $^

clean:
	-rm simple_run capaging test
	cd pagecollect && $(MAKE) clean