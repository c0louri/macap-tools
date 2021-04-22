CC=gcc

all: test test2

test: test.c aux.h
	$(CC) -o $@ $^

test2: est2.c aux.h
	$(CC) -o $@ $^

clean:
	-rm test test2