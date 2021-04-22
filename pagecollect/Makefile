CC=gcc
CPP=g++

.PHONY: pagecollect cap_pagecollect

all: pagecollect cap_pagecollect
pagecollect: pagecollect_main.c page-collect.c
	$(CC) -O3 -o $@ $^

cap_pagecollect: pagecollect_main.cpp page-collect.cpp
	$(CPP) -O3 -o $@ $^

clean:
	-rm pagecollect cap_pagecollect cap_pagecollect.o