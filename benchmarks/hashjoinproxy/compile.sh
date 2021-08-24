gcc -c murmurhash.c
gcc -c hashjoin.c
gcc hashjoin.o  murmurhash.o -o hashjoin
rm *.o
