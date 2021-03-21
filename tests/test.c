#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <sys/wait.h>
#include <sys/types.h>
#include <sys/mman.h>
#include <unistd.h>
#include <getopt.h>
#include "aux.h"


int length_in_128mb = 1;
unsigned long length_base = 128 * 1024 * 1024;
long int buf_len = 0;
char *stats_buf = NULL;
FILE *out_file = NULL;

int dumpstats = 0;
int mem_defrag = 0;
int capaging = 0;
int hugepage_madvise = 0;
int random_alloc = 0;
int with_signals = 0;

static struct option opts [] =
{
	{"length_in_128mb", required_argument, 1, 'l'},
	{"dumpstats", no_argument, &dumpstats, 1},
	{"mem_defrag", no_argument, &mem_defrag, 1},
	{"capaging", no_argument, &mem_defrag, 1},
	{"madv_hp", no_argument, &hugepage_madvise, 1},
	{"random_alloc", no_argument, &random_alloc, 1},
	{"with_signals", no_argument, &with_signals, 1},
	{0,0,0,0}
};

int main(int argc, char** argv) {
	int c;
	while ((c = getopt_long(argc, argv, "l:", opts, NULL)) != -1)
	{
		switch (c)
		{
			case 'l':
				length_in_128mb = atoi(optarg);
			default:
				abort();
		}
	}

	pid_t current_pid = getpid();
	pid_t parent_pid = getppid();

	if (dumpstats) {
		buf_len = 1*1024*1024;
		stats_buf = (char *)malloc(buf_len*sizeof(char));
		out_file = fopen("defrag_stats.dat", "w");
	}

	if (with_signals) {
		signal(SIGUSR1, sigusr1_handler);
		signal(SIGUSR2, sigusr2_handler);
	}

	printf("Process PID : %d\n", current_pid);
	// enable defragging
	if (mem_defrag)
		scan_process_memory(current_pid, stats_buf, buf_len, MEM_DEFRAG_MARK_SCAN_ALL, NULL);
	// enable capaging
	if (capaging)
		enable_capaging(current_pid);
	//
	//
	unsigned long length = length_in_128mb * length_base;
	void *addr = allocate_big_anon(length, PROT_FLAGS, MAPPING_FLAGS, hugepage_madvise);

	if (random_alloc)
		create_PFs_random(addr, length);
	else
		create_PFs(addr, length);

    if (with_signals) {
		// send signal that program is ready for defragging
		// so as to collect pre-defrag stats
		kill(parent_pid, SIGUSR1);
		pause();
	}
	else {
		printf("Press Enter to start defragging...\n");
		getchar();
	}
	if (mem_defrag)
		scan_process_memory(current_pid, stats_buf, buf_len, MEM_DEFRAG_DEFRAG, out_file);

	if (with_signals) {
		// send signal that defrag has finished
		kill(parent_pid, SIGUSR2);
		// wait for a continue-signal from
		pause();
	}
	else {
		printf("Press Enter to exit...\n");
		getchar();
	}

	if (dumpstats)
		fclose(out_file);
	return 0;
}
