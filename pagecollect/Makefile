CC=gcc
CPP=g++

.PHONY: pagecollect cap_pagecollect

all: pagecollect cap_pagecollect
pagecollect: pagecollect_main.c page-collect.c
	$(CC) -O3 -o $@ $^

cap_pagecollect:
	$(CPP) -O3 -Wall -c -o cap_pagecollect.o page-collect.cpp
	$(CPP) -O3 -Wall cap_pagecollect.o -o cap_pagecollect

clean:
	-rm pagecollect cap_pagecollect cap_pagecollect.o