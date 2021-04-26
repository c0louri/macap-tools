CC=gcc
CPP=g++
.PHONY: pagecollect
all: pagecollect simple_run capaging memfrag

pagecollect:
	cd pagecollect && $(MAKE)

simple_run: simple_run.cpp pagecollect/page-collect.cpp
	$(CPP) -o $@ $^ -lnuma

capaging: capaging.c
	$(CC) -o $@ $^

memfrag: memfrag.c
	$(CC) -o $@ $^

clean:
	-rm simple_run capaging memfrag
	cd pagecollect && $(MAKE) clean