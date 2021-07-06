CC=gcc
CPP=g++
.PHONY: pagecollect
all: pagecollect simple_run capaging memfrag micro

pagecollect:
	cd pagecollect && $(MAKE)

simple_run: simple_run.cpp pagecollect/page-collect.cpp
	$(CPP) -o $@ $^ -lnuma

capaging: capaging.c
	$(CC) -o $@ $^

memfrag: memfrag.c
	$(CC) -o $@ $^

micro: benchmarks/micro/microbench.c
	$(CC) -o $@ $^

clean:
	-rm simple_run capaging memfrag micro
	cd pagecollect && $(MAKE) clean