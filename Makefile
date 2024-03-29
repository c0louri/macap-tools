CC=gcc
CPP=g++
.PHONY: pagecollect
all: pagecollect simple_run capaging memfrag micro micro2 hashjoin

pagecollect:
	cd pagecollect && $(MAKE)

simple_run: simple_run.cpp pagecollect/page-collect.cpp
	$(CPP) -o $@ $^ -lnuma

capaging: capaging.c
	$(CC) -o $@ $^

memfrag: memfrag.c
	$(CC) -o $@ $^

micro:
	cd benchmarks/micro && $(CC) -o $@ microbench.c

micro2:
	cd benchmarks/micro2 && $(CC) -o $@ microbench.c

hashjoin:
	cd benchmarks/hashjoinproxy && ./compile.sh

clean:
	-rm simple_run capaging memfrag
	cd pagecollect && $(MAKE) clean
	-rm benchmarks/micro/micro
	-rm benchmarks/micro2/micro2
	-rm benchmarks/hashjoinproxy/hashjoin