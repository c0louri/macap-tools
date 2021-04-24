#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <unistd.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/types.h>
#include <sys/time.h>
#include <sys/resource.h>
#include <sys/sysinfo.h>
#include <signal.h>
#include <err.h>
#include <fcntl.h>
#include <limits.h>

//#define CHUNK (1UL << 32)
#define CHUNK (1UL << 30)
typedef ulong uint64_t;

void usage(const char *prog, FILE *out)
{
	fprintf(out, "usage: %s allocsize\n", prog);
	fprintf(out, " allocsize is kbytes, or number[KMGP] (P = pages)\n");
	exit(out == stderr);
}

void usr_handler(int signal) 
{
	printf("catch signal\n");
	exit(-1);
}

uint64_t size_huge_tbl[] = {
	1UL << 21, //2M
	1UL << 22, //4M
	1UL << 23, //8M
	1UL << 24, //16M
	1UL << 25, //32M
	1UL << 26, //64M
	1UL << 27, //128M
	1UL << 28, //256M
	1UL << 29, //512M
	1UL << 30, //1G
	//1UL << 31, //2G
	//1UL << 32, //4G
};

uint64_t size_subhuge_tbl[] = {
	1UL << 12, //4
	1UL << 13, //8
	1UL << 14, //16
	1UL << 15, //32
	1UL << 16, //64
	1UL << 17, //128
	1UL << 18, //256
	1UL << 19, //512
	1UL << 20, //1M
};

static uint64_t random_range(uint64_t a,uint64_t b) {
    uint64_t v;
    uint64_t range;
    uint64_t upper;
    uint64_t lower;
    uint64_t mask;

    if(a == b) {
        return a;
    }

    if(a > b) {
        upper = a;
        lower = b;
    } else {
        upper = b;
        lower = a; 
    }

    range = upper - lower;

    mask = 0;
    //XXX calculate range with log and mask? nah, too lazy :).
    while(1) {
        if(mask >= range) {
            break;
        }
        mask = (mask << 1) | 1;
    }


    while(1) {
        v = rand() & mask;
        if(v <= range) {
            return lower + v;
        }
    }
}

size_t getCurrentRSS( )
{

  long rss = 0L;
  FILE* fp = NULL;

  if ( (fp = fopen( "/proc/self/statm", "r" )) == NULL )
    return (size_t)0L;    /* Can't open? */

  if ( fscanf( fp, "%*s%ld", &rss ) != 1 )
  {
    fclose( fp );
    return (size_t)0L;    /* Can't read? */
  }
  
  fclose( fp );
  return (size_t)rss * (size_t)sysconf( _SC_PAGESIZE);

}



int main(int argc, char *argv[])
{
	long long kbtotal = 0;
	unsigned long long i, j, numchunk, numchunk_huge, numchunk_sub_huge, compaction = 0, use_huge = 1;
	int fd;
	unsigned int offset;
	unsigned long long free_size;
	void **data;
	sigset_t set;
	struct sigaction sa;
  int huge_page_frag_percentage;
  int free_frag_percentage;

	printf("%s\n", argv[1]);

	if (argc >= 2) {
		char *end = NULL;
		/* BOF??? */
		kbtotal = strtoull(argv[1], &end, 0);

		switch(*end) {
			case 'g':
			case 'G':
				kbtotal *= 1024;
			case 'm':
			case 'M':
				kbtotal *= 1024;
			case '\0':
			case 'k':
			case 'K':
				kbtotal *= 1024;
				break;
			case 'p':
			case 'P':
				kbtotal *= 4;
				break;
			default:
				usage(argv[0], stderr);
				break;
		}
	}
	
	if (argc < 2 || kbtotal == 0)
		usage(argv[0], stderr);

	if (argc >= 3)
		huge_page_frag_percentage = atoi(argv[2]);

  if (argc >= 4)
		free_frag_percentage = atoi(argv[3]);
  else
    free_frag_percentage = 50;

	if (argc >= 5)
		use_huge = atoi(argv[3]);

	if (argc >= 6)
		compaction = atoi(argv[4]);

	if (use_huge)
		printf("Use huge page\n");
	else
		printf("Do not use huge page\n");

	if (compaction)
		printf("do compaction\n");
	else
		printf("Do not compact memory\n");

	numchunk = kbtotal / CHUNK;
	printf("allocate %llx memory,  numchunk = %d\n", kbtotal, numchunk);
	data = mmap(0, sizeof(void *) * numchunk, 
			PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_ANONYMOUS, -1, 0);

	sa.sa_flags = 0;
	sa.sa_handler = usr_handler;

	if (sigaction(SIGUSR1, &sa, NULL) == -1)
		errx(1, "sigaction");

	sigemptyset(&set);
	sigaddset(&set, SIGUSR1);

retry:
	printf("allocate memory\n");
	for (i = 0 ; i < numchunk; i++) {
		data[i] = mmap(NULL, CHUNK, PROT_READ | PROT_WRITE,
				MAP_ANONYMOUS | MAP_PRIVATE, -1, 0);

		if (!data[i]) {
			perror("alloc\n");
		}

		if (use_huge) {
			if (madvise(data[i], CHUNK, MADV_HUGEPAGE) < 0) {
				perror("error");
				exit(-1);
			}
		} else {
			if (madvise(data[i], CHUNK, MADV_NOHUGEPAGE) < 0) {
				perror("error");
				exit(-1);
			}
		}

		memset(data[i], 1, CHUNK);

		//for (j = 2, offset = 0; offset < CHUNK; j++) {
		//for (j = 0; j < CHUNK; j+=(1<<20)) {
		//	free_size = size_tbl[random_range(0, 8)];
			//printf("%x, %lx\n", j, free_size);
			//munmap(data[i] + j, free_size);
		//	madvise(data[i] + j, free_size, MADV_DONTNEED);
		//}
	}

  struct sysinfo si;
  sysinfo(&si);
  printf("Fragmenter %lu %lu %lu\n", getCurrentRSS(), si.totalram, kbtotal);
  printf("%lu %lu %lu\n", huge_page_frag_percentage, numchunk, numchunk*huge_page_frag_percentage/100, numchunk-(numchunk*huge_page_frag_percentage/100));
  numchunk_sub_huge = numchunk*huge_page_frag_percentage/100;
  numchunk_huge=numchunk-(numchunk*huge_page_frag_percentage/100);

  int k;
  while(getCurrentRSS()>(kbtotal*free_frag_percentage/100)){
	  
    for (i = 0 ; i < numchunk; i++) {
      if(i <numchunk_sub_huge) {

        for (j = 0; j < CHUNK; j+=(1UL<<20)) {

          //for (k = 2, offset = 0; k < 20; k++) {
			    //  madvise(data[i] + j + offset, ((1UL<<20) / (1<<k)), MADV_DONTNEED);
			    //  offset += ((1UL<<20) / (1<<(k-1)));
		      //}
			    free_size = size_subhuge_tbl[random_range(0, 8)];
			    //printf("%x, %lx\n", j, free_size);
			    //munmap(data[i] + j, free_size);
			    madvise(data[i] + j, free_size, MADV_DONTNEED);
		    }
      }
      else{
		    for (j = 0; j < CHUNK; j+=(1UL<<30)) {
			    free_size = size_huge_tbl[random_range(0, 9)];
			    //printf("%x, %lx\n", j, free_size);
			    //munmap(data[i] + j, free_size);
			    madvise(data[i] + j, free_size, MADV_DONTNEED);
		    }
      }
	  }
    printf("%lu %lu\n", getCurrentRSS(), si.totalram/2);

  }
	//printf("pausing\n");
	//pause();
	//sigwaitinfo(&set, NULL);
  	//kill(getppid(), SIGUSR2);
  	//printf("Sending signal to %d\n",getppid());
	pause();
	
  if (compaction) {
		printf("compaction\n");
		fd = open("/proc/sys/vm/compact_memory", O_WRONLY);
		if (fd < 0)
			errx(1, "cannot open file");

		if (write(fd, "1", 2) < 0)
			errx(1, "cannot write file");

		close(fd);
	}
	sleep(5);

	printf("retry\n");
	for (i = 0 ; i < numchunk; i++) 
		munmap(data[i], CHUNK);

	goto retry;
}
