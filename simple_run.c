#define _GNU_SOURCE

#include <string.h>
#include <stdio.h>
#include <inttypes.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/wait.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <signal.h>
#include <getopt.h>
#include <numa.h>
#include <numaif.h>
#include <sched.h>
#include <errno.h>

#include <time.h>
#include <sys/time.h>
#define TV_MSEC tv_usec / 1000
#include <sys/resource.h>
#include <sys/utsname.h>
#include "./pagecollect/page-collect.h"


typedef struct
{
  int waitstatus;
  struct rusage ru;
  struct timeval start, elapsed; /* Wallclock time of process.  */
} RESUSE;

/*#define RUSAGE_CHILDREN -1*/

/* Avoid conflicts with ASCII code  */
enum {
	OPT_TRACE_LOC = 256,
	OPT_DEFRAG_FREQ_FACTOR,
	OPT_CHILD_STDIN,
	OPT_CHILD_STDOUT,
};

int syscall_mem_defrag = 335;
int syscall_enable_capaging = 337;

unsigned cycles_high, cycles_low;
unsigned cycles_high1, cycles_low1;
RESUSE time_stats;
pid_t child;
volatile int child_quit = 0;
volatile int info_done = 0;
int dumpstats_signal = 1;
int dumpstats_period = 1;
int mem_defrag = 0;
int capaging = 0;
// int vm_stats = 0;
int defrag_online_stats = 0;
// unsigned int sleep_ms_defrag = 0;
int defrag_freq_factor = 1;

long scan_process_memory(pid_t pid, char *buf, int len, int action)
{
	return syscall(syscall_mem_defrag, pid, buf, len, action);
}

static void sleep_ms(unsigned int milliseconds)
{
	struct timespec ts;

	if (!milliseconds)
		return;

	ts.tv_sec = milliseconds / 1000;
	ts.tv_nsec = (milliseconds % 1000) * 1000000;
	nanosleep(&ts, NULL);
}

static int get_new_filename(const char *filename, char **final_name)
{
	const char *template = "%s_%d";
	int len = strlen(filename) + 5; /* 1: _, 3: 0-999, 1: \n  */
	int index = 0;
	struct stat st;
	int file_not_exist;

	if (!final_name)
		return -EINVAL;

	*final_name = malloc(len);
	if (!*final_name)
		return -ENOMEM;
	memset(*final_name, 0, len);

	sprintf(*final_name, template,filename, index);

	while ((file_not_exist = stat(*final_name, &st)) == 0)
	{
		index++;
		sprintf(*final_name, template, filename, index);

		if (index >= 1000)
			break;
	}

	if (index >= 1000) {
		free(*final_name);
		*final_name = NULL;
		return -EBUSY;
	}

	return 0;
}

#define BUF_LEN 1024

void read_stats_periodically(pid_t app_pid) {
	char *stats_filename = NULL;
	char *stats_buf = NULL;
	int stats_handle = 0;
	FILE *defrag_online_output = NULL;
	long read_ret;
	const int buf_len = 1024 * 1024 * 16;
	int loop_count = 0;
	int file_index = 0;
	char out_name[100];
	int ret = 0;

	stats_buf = malloc(buf_len);
	if (!stats_buf)
		return;
	memset(stats_buf, 0, buf_len);

	if (defrag_online_stats) {
		if (get_new_filename("./defrag_online_stats", &stats_filename))
			goto cleanup;

		defrag_online_output = fopen(stats_filename, "w");
		if (!defrag_online_output) {
			perror("cannot write stats file");
			goto cleanup;
		}
		free(stats_filename);
		stats_filename = NULL;
	}

	sleep(1);
	do {
		if (dumpstats_signal) {
			loop_count++;
			if (loop_count % defrag_freq_factor == 0) {
				/* defrag memory before scanning  */
				if (mem_defrag) {
					// get custom_pagemap from page-collect.cpp
					sprintf(out_name, "pagemap_%d_%d_pre.out", app_pid, file_index);
					ret = collect_custom_pagemap(app_pid, out_name);
					// sleep_ms(sleep_ms_defrag);
					if (defrag_online_stats) {
						while ((read_ret = scan_process_memory(app_pid, stats_buf, buf_len, 3)) > 0) {
							fputs(stats_buf, defrag_online_output);
							memset(stats_buf, 0, buf_len);
							// sleep_ms(sleep_ms_defrag);
						}
						if (read_ret < 0)
							break;
						fputs("----\n", defrag_online_output);
					} else {
						while (scan_process_memory(app_pid, NULL, 0, 3) > 0)
							// sleep_ms(sleep_ms_defrag);
					}
					// sleep_ms(sleep_ms_defrag);
					sprintf(out_name, "pagemap_%d_%d_post.out", app_pid, file_index++);
					ret = collect_custom_pagemap(app_pid, out_name);
				}
			}
		}
		sleep(dumpstats_period);
	} while (!child_quit);

	if (defrag_online_output)
		fclose(defrag_online_output);
cleanup:
	if (stats_buf)
		free(stats_buf);
	if (stats_filename)
		free(stats_filename);

	return;
}

void toggle_dumpstats_signal()
{
	dumpstats_signal ^= 1;
}

void child_exit(int sig, siginfo_t *siginfo, void *context)
{
	char buffer[255];
	char proc_buf[64];
    uint64_t start;
    uint64_t end;
	int status;
	unsigned long r;		/* Elapsed real milliseconds.  */
	unsigned long system_time;
	unsigned long user_time;
	FILE *childinfo;
	unsigned long cpu_freq = 1;
	char *hz;
	char *unit;

	if (waitpid(siginfo->si_pid, &status, WNOHANG) != child)
		return;

	child_quit = 1;
	getrusage(RUSAGE_CHILDREN, &time_stats.ru);
    asm volatile
        ( "RDTSCP\n\t"
          "mov %%edx, %0\n\t"
          "mov %%eax, %1\n\t"
          "CPUID\n\t"
          :
          "=r" (cycles_high1), "=r" (cycles_low1)
          ::
          "rax", "rbx", "rcx", "rdx"
        );
	gettimeofday (&time_stats.elapsed, (struct timezone *) 0);

	time_stats.elapsed.tv_sec -= time_stats.start.tv_sec;
	if (time_stats.elapsed.tv_usec < time_stats.start.tv_usec)
	{
		/* Manually carry a one from the seconds field.  */
		time_stats.elapsed.tv_usec += 1000000;
		--time_stats.elapsed.tv_sec;
	}
	time_stats.elapsed.tv_usec -= time_stats.start.tv_usec;

	time_stats.waitstatus = status;

	r = time_stats.elapsed.tv_sec * 1000 + time_stats.elapsed.tv_usec / 1000;

	user_time = time_stats.ru.ru_utime.tv_sec * 1000 + time_stats.ru.ru_utime.TV_MSEC;
	system_time = time_stats.ru.ru_stime.tv_sec * 1000 + time_stats.ru.ru_stime.TV_MSEC;


    start = ((uint64_t)cycles_high <<32 | cycles_low);
    end = ((uint64_t)cycles_high1 <<32 | cycles_low1);


	fprintf(stderr, "cycles: %lu\n", end - start);

	fprintf(stderr, "real time(ms): %lu, user time(ms): %lu, system time(ms): %lu, virtual cpu time(ms): %lu\n",
			r, user_time, system_time, user_time+system_time);
	fprintf(stderr, "min_flt: %lu, maj_flt: %lu, maxrss: %lu KB\n",
			time_stats.ru.ru_minflt, time_stats.ru.ru_majflt,
			time_stats.ru.ru_maxrss);
	fflush(stderr);

	info_done = 1;
}

int main(int argc, char** argv)
{
	static int dumpstats = 0;
	static int use_dumpstats_signal = 0;
	static int no_migration = 0;
	static int relocate_agent_mem = 0;
	static struct option long_options [] =
	{
		{"cpunode", required_argument, 0, 'N'},
		{"memnode", required_argument, 0, 'm'},
		{"prefer_memnode", required_argument, 0, 'M'},
		{"cpumask", required_argument, 0, 'c'},
		{"dumpstats", no_argument, &dumpstats, 1},
		{"dumpstats_signal", no_argument, &use_dumpstats_signal, 1},
		{"dumpstats_period", required_argument, 0, 'p'},
		// {"defrag_freq_factor", required_argument, 0, OPT_DEFRAG_FREQ_FACTOR},
		{"nomigration", no_argument, &no_migration, 1},
		{"mem_defrag", no_argument, &mem_defrag, 1},
		{"capaging", no_argument, &mem_defrag, 1},
		{"defrag_online_stats", no_argument, &defrag_online_stats, 1},
		{"child_stdin", required_argument, 0, OPT_CHILD_STDIN},
		{"child_stdout", required_argument, 0, OPT_CHILD_STDOUT},
		// {"sleep_ms_defrag", required_argument, 0, 'S'},
		{"relocate_agent_mem", no_argument, &relocate_agent_mem, 1},
		{0,0,0,0}
	};
	struct sigaction child_exit_act = {0}, dumpstats_act = {0};

	int option_index = 0;
	int c;
	unsigned long cpumask = -1;
	int index;
	struct bitmask *cpu_mask = NULL;
	struct bitmask *node_mask = NULL;
	struct bitmask *mem_mask = NULL;
	struct bitmask *parent_mask = NULL;
	int child_stdin_fd = 0;
	int child_stdout_fd = 0;
	int prefer_mem_mode = 0;

	parent_mask = numa_allocate_nodemask();

	if (!parent_mask)
		numa_error("numa_allocate_nodemask");

	numa_bitmask_setbit(parent_mask, 1);

	/*numa_run_on_node(0);*/
	numa_bind(parent_mask);

	if (argc < 2)
		return 0;

	while ((c = getopt_long(argc, argv, "N:M:m:c:",
							long_options, &option_index)) != -1)
	{
		switch (c)
		{
			case 0:
				 /* If this option set a flag, do nothing else now. */
				if (long_options[option_index].flag != 0)
					break;
				printf ("option %s", long_options[option_index].name);
				if (optarg)
					printf (" with arg %s", optarg);
					printf ("\n");
				break;
			case 'N':
				/* cpunode = (int)strtol(optarg, NULL, 0); */
				node_mask = numa_parse_nodestring(optarg);
				break;
			case 'M':
				prefer_mem_mode = 1;
			case 'm':
				/* memnode = (int)strtol(optarg, NULL, 0); */
				mem_mask = numa_parse_nodestring(optarg);
				break;
			case 'c':
				cpumask = strtoul(optarg, NULL, 0);
				cpu_mask = numa_allocate_nodemask();
				index = 0;
				while (cpumask) {
					if (cpumask & 1) {
						numa_bitmask_setbit(cpu_mask, index);
					}
					cpumask = cpumask >> 1;
					++index;
				}
				break;
			case 'p':
				dumpstats_period = atoi(optarg);
				break;
			case OPT_DEFRAG_FREQ_FACTOR:
				defrag_freq_factor = atoi(optarg);
				break;
			case OPT_CHILD_STDIN:
				child_stdin_fd = open(optarg, O_RDONLY);
				if (!child_stdin_fd) {
					perror("child stdin file open error\n");
					exit(-1);
				}
				break;
			case OPT_CHILD_STDOUT:
				child_stdout_fd = open(optarg, O_CREAT | O_RDWR, 0644);
				if (!child_stdout_fd) {
					perror("child stdout file open error\n");
					exit(-1);
				}
				break;
			// case 'S':
			// 	sleep_ms_defrag = atoi(optarg);
				break;
			case '?':
				return 1;
			default:
				abort();
		}
	}

	/* push it to child process command line  */
	argv += optind;

	printf("child arg: %s\n", argv[0]);

	/* cpu_mask overwrites node_mask  */
	if (cpu_mask)
	{
		numa_bitmask_free(node_mask);
		node_mask = NULL;
	}

	// child_exit_act
	child_exit_act.sa_sigaction = child_exit;
	child_exit_act.sa_flags = SA_SIGINFO;
	if (sigaction(SIGCHLD, &child_exit_act, NULL) < 0) {
		perror("sigaction on SIGCHLD");
		exit(0);
	}
	// dumpstats_act
	dumpstats_act.sa_handler = toggle_dumpstats_signal;
	if (sigaction(SIGUSR1, &dumpstats_act, NULL) < 0) {
		perror("sigaction on dumpstats");
		exit(0);
	}

    asm volatile
        ( "CPUID\n\t"
          "RDTSC\n\t"
          "mov %%edx, %0\n\t"
          "mov %%eax, %1\n\t"
          :
          "=r" (cycles_high), "=r" (cycles_low)
          ::
          "rax", "rbx", "rcx", "rdx"
        );
	gettimeofday (&time_stats.start, (struct timezone *) 0);

	child = fork();

	if (child == 0) { // child
		int child_status;

		if (node_mask)
		{
			if (numa_run_on_node_mask_all(node_mask) < 0)
				numa_error("numa_run_on_node_mask_all");
		} else if (cpu_mask)
		{
			if (sched_setaffinity(getpid(), numa_bitmask_nbytes(cpu_mask),
							(cpu_set_t*)cpu_mask->maskp) < 0)
				numa_error("sched_setaffinity");
		}

		if (mem_mask && !no_migration)
		{
			if (prefer_mem_mode) {
				if (set_mempolicy(MPOL_PREFERRED,
							  mem_mask->maskp,
							  mem_mask->size + 1) < 0)
					numa_error("set_mempolicy");
			} else {
				if (set_mempolicy(MPOL_BIND,
							  mem_mask->maskp,
							  mem_mask->size + 1) < 0)
					numa_error("set_mempolicy");
			}
		}

		if (child_stdin_fd) {
			dup2(child_stdin_fd, 0);
			close(child_stdin_fd);
		}
		if (child_stdout_fd) {
			dup2(child_stdout_fd, 1);
			close(child_stdout_fd);
		}

		if (mem_defrag)
			scan_process_memory(0, NULL, 0, 1);
		if (capaging)
			syscall(syscall_enable_capaging, NULL, 0, 0);

		child_status = execvp(argv[0], argv);

		perror("child die\n");
		fprintf(stderr, "application execution error: %d\n", child_status);
		exit(-1);
	}

	fprintf(stderr, "child pid: %d\n", child);
	fprintf(stdout, "child pid: %d\n", child);

	if (relocate_agent_mem) {
		numa_bitmask_setbit(parent_mask, 0);
		numa_set_membind(parent_mask);
	}

	if (node_mask)
		numa_bitmask_free(node_mask);
	if (mem_mask)
		numa_bitmask_free(mem_mask);
	if (cpu_mask)
		numa_bitmask_free(cpu_mask);
	if (parent_mask)
		numa_bitmask_free(parent_mask);

	if (use_dumpstats_signal)
		dumpstats_signal = 0;

	if (dumpstats || use_dumpstats_signal)
		read_stats_periodically(child);

	while (!info_done)
		sleep(1);

	return 0;

}
