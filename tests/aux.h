#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>

#define DEFRAG_SYSCALL 335
#define CAPAGING_SYSCALL 337

#define MEM_DEFRAG_SCAN					0
#define MEM_DEFRAG_MARK_SCAN_ALL		1
#define MEM_DEFRAG_CLEAR_SCAN_ALL		2
#define MEM_DEFRAG_DEFRAG				3
#define MEM_DEFRAG_CONTIG_SCAN			5

#define PROT_FLAGS 		PROT_READ|PROT_WRITE
#define MAPPING_FLAGS 	MAP_ANONYMOUS|MAP_PRIVATE

int scan_process_memory(pid_t pid, char *buf, int buf_len, int action, FILE *out) {
	int res = 0;
	if (buf) {
		memset(buf, 0, buf_len);
	}
	switch (action) {
		case MEM_DEFRAG_MARK_SCAN_ALL:
			printf("Marking process for defrag!\n");
			res = syscall(DEFRAG_SYSCALL, 0, NULL, 0, MEM_DEFRAG_MARK_SCAN_ALL);
			break;
		case MEM_DEFRAG_SCAN:
			break;
		case MEM_DEFRAG_DEFRAG:
			printf("Defrag started...");
			res = syscall(DEFRAG_SYSCALL, 0, buf, buf_len, MEM_DEFRAG_DEFRAG);
			printf("Defragging done!");
			break;
		case MEM_DEFRAG_CLEAR_SCAN_ALL:
			res = syscall(DEFRAG_SYSCALL, pid, NULL, 0, MEM_DEFRAG_CLEAR_SCAN_ALL);
			break;
		case MEM_DEFRAG_CONTIG_SCAN:
		default:
			break;
	}
	if (out && buf) {
		fputs("~~~~~Defrag log!!!!\n", out);
		fputs(buf, out);
	}
	return res;
}

void enable_capaging(pid_t pid) {
	syscall(CAPAGING_SYSCALL, NULL, 0, 0);
}

void *allocate_big_anon(unsigned long length, int prot_flags, int map_flags, int use_huge) {
	void *addr = mmap(NULL, length, prot_flags, map_flags, -1, 0);
	if (use_huge) {
		madvise(addr, length, MADV_HUGEPAGE);
	}
	printf("New region: vaddr: %p, length: %dMB\n", addr, length>>20);
	return addr;
}

void create_PFs(void *addr, unsigned long length) {
	/* UNTESTED function */
    printf("Provoking PFs in a linear way...\n");
	time_t t;
	srand((unsigned) time(&t));
	char *i = (char *)addr;
	//for(; i < (char *)addr + length - 8; i += 512*4096 + 4096)
	//	*((unsigned long *)i) = rand();
	//for(; i < (char *)addr + length - 8; i += 8*4096)
	//	*((unsigned long *)i) = rand();
	for(; i < (char *)addr + length; i += 2048)
		*i = rand() % 256;
}

void shuffle(unsigned long **array, size_t n) {
    printf("Shuffling address for PFs\n");
	time_t t;
	srand(12345678);
	if (n > 1) {
		size_t i;
		for (i = 0; i < n-1; i++) {
			size_t j = i + rand() / (RAND_MAX/(n-i) +1);
			unsigned long *t = array[j];
			array[j] = array[i];
			array[i] = t;
		}
	}
    printf("Shuffling is done\n");
}

void create_PFs_random(void *addr, unsigned long length) {
	printf("Provoking PFs at random pages of region starting at %p\n", addr);
	time_t t;
	srand((unsigned) time(&t));
	unsigned long **array = NULL;
	size_t array_length = length >> 12; // length / 4096
	array = (unsigned long **)malloc(array_length * sizeof(unsigned long *));
	for (size_t i = 0; i < array_length; i++)
		array[i] = (unsigned long *)((char *)addr + i * 4096);
	shuffle(array, array_length);
	for (size_t i = 0; i < array_length; i++)
		*(array[i]) = rand();
    free(array);
}

// functions for handling SIGUSR1/SIGUSR2 arriving in benchmark
void sigusr1_handler() { ; }
void sigusr2_handler() { ; }