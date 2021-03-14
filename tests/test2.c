#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/mman.h>
#include <unistd.h>
#include "aux.h"


int main(void) {
	pid_t current_pid = getpid();
	long int buf_len = 1*1024*1024; // 1MB stats buffer
	char *stats_buf = (char *)malloc(buf_len*sizeof(char));
	FILE *out_file = fopen("defrag_stats.dat", "w");
	printf("Process PID : %d\n", current_pid);
	// enable defragging
	scan_process_memory(current_pid, stats_buf, buf_len, MEM_DEFRAG_MARK_SCAN_ALL, NULL);
	// enable capaging
	enable_capaging(current_pid);
	//
	//
	unsigned long length = 4 * 1024 * 1024;
	void *addr = allocate_big_anon(length, PROT_FLAGS, MAPPING_FLAGS, 0);
	create_PFs_random(addr, length);
	 printf("Press Enter after checking vmas!\n");
	 getchar();
	addr = allocate_big_anon(8 * length, PROT_FLAGS, MAPPING_FLAGS, 0);
	create_PFs(addr, 8 * length);
	 printf("Press Enter after checking vmas!\n");
	 getchar();
	// int res = scan_process_memory(current_pid, stats_buf, buf_len, MEM_DEFRAG_DEFRAG, out_file);
    fclose(out_file);
	return 0;
}
