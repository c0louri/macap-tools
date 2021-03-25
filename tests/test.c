#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <sys/wait.h>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/mman.h>
#include <unistd.h>
#include <getopt.h>
#include "aux.h"

// variables for measuring time of defrag syscall
struct timeval end, start;
unsigned long time_taken; // time is in microseconds


int length_in_128mb = 1;
unsigned long length_base = 128 * 1024 * 1024;
long int buf_len = 0;
char *stats_buf = NULL;
FILE *out_file = NULL;

static int dumpstats = 0;
static int mem_defrag = 0;
static int capaging = 0;
static int hugepage_madvise = 0;
static int random_alloc = 0;
static int with_signals = 0;

static struct option opts[] =
{
	{"length_in_128mb", required_argument,  0,               'l'},
	{"dumpstats",       no_argument,        &dumpstats,        1},
	{"mem_defrag",      no_argument,        &mem_defrag,       1},
	{"capaging",        no_argument,        &capaging,         1},
	{"madv_hp",         no_argument,        &hugepage_madvise, 1},
	{"random_alloc",    no_argument,        &random_alloc,     1},
	{"with_signals",    no_argument,        &with_signals,     1},
	{0,0,0,0}
};

int main(int argc, char** argv) {
    int options_index = 0;
	int c;
    struct sigaction sa;
	while ((c = getopt_long(argc, argv, "l:", opts, &options_index)) != -1)
	{
		switch (c)
		{
            case 0:
				 /* If this option set a flag, do nothing else now. */
				if (opts[options_index].flag != 0)
					break;
				printf ("option %s", opts[options_index].name);
				if (optarg)
					printf (" with arg %s", optarg);
					printf ("\n");
				break;
		    case 'l':
				length_in_128mb = atoi(optarg);
                break;
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
		// signal(SIGUSR1, sigusr1_handler);
        sa.sa_handler = sigusr1_handler;
        sigemptyset(&sa.sa_mask);
        sa.sa_flags = SA_RESTART;
        if (sigaction(SIGUSR1, &sa, NULL) == -1)
            {printf("Error sigaction\n"); exit(-1);}
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
        printf("Received SIGUSR1 signal!\n");
	}
	else {
		printf("Press Enter to start defragging...\n");
		getchar();
	}
	if (mem_defrag) {
        gettimeofday(&start, NULL);
		scan_process_memory(current_pid, stats_buf, buf_len, MEM_DEFRAG_DEFRAG, out_file);
        gettimeofday(&end, NULL);
        time_taken = 0;
        time_taken = (end.tv_sec - start.tv_sec) *1000*1000;
        time_taken += (end.tv_usec - start.tv_usec);
        printf("Time spend for defragging = %ldus\n", time_taken); 
    }

	if (with_signals) {
		// send signal that defrag has finished
		kill(parent_pid, SIGUSR2);
		// wait for a continue-signal from
		pause();
        printf("Received SIGUSR1 signal!\n");
	}
	else {
		printf("Press Enter to exit...\n");
		getchar();
	}

	if (dumpstats)
		fclose(out_file);
	return 0;
}
