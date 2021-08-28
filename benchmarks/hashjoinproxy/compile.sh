gcc -fopenmp -c murmurhash.c
gcc -fopenmp -c hashjoin.c
gcc -fopenmp hashjoin.o  murmurhash.o -o hashjoin
rm *.o
