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

/*
1st parameter : size (or number of 4k pages)

*/

//#define CHUNK (1UL << 32)
#define CHUNK (1UL << 30)

void usage(const char *prog, FILE *out)
{
    fprintf(out, "usage: %s allocsize\n", prog);
    fprintf(out, " allocsize is kbytes, or number[KMGP] (P = pages)\n");
    exit(out == stderr);
}


int main(int argc, char *argv[])
{
    long long btotal = 0;
    void *addr_1, *addr_2, *addr_3;
    unsigned char *tmp_addr;
    unsigned long long size_1st, size_2nd, size_3rd;
    int use_huge = 1;

    printf("%s\n", argv[1]);

    if (argc >= 2) {
        char *end = NULL;
        /* BOF??? */
        btotal = strtoull(argv[1], &end, 0);

        switch(*end) {
            case 'g':
            case 'G':
                btotal *= 1024;
            case 'm':
            case'M':
                btotal *= 1024;
            case '\0':
            case 'k':
			case 'K':
				btotal *= 1024;
                break;
            case 'p':
            case 'P':
                btotal *= 4;
                break;
            default:
                usage(argv[0], stderr);
                break;
        }
    }

    if (argc < 2 || btotal == 0)
        usage(argv[0], stderr);
    if (argc >= 3)
        use_huge = atoi(argv[2]);


    printf("allocate %ldGB memory\n", btotal >> 30); // print #GB to allocate
    // 1st phase: malloc for 10% of total space
    size_1st = 0.1 * btotal;
    printf("1st phase: allocate %lldMB\n", size_1st >> 20);
	addr_1 = mmap(NULL, size_1st, PROT_READ | PROT_WRITE, MAP_ANONYMOUS | MAP_PRIVATE, -1, 0);
    if (use_huge) {
        if (madvise(addr_1, size_1st, MADV_HUGEPAGE) < 0) {
            perror("error");
            exit(-1);
        }
    } else {
        if (madvise(addr_1, size_1st, MADV_NOHUGEPAGE) < 0) {
            perror("error");
            exit(-1);
        }
    }
    // memset 512MB per second for the 1st phase
    memset(addr_1, 1, size_1st);
    tmp_addr = (unsigned char *) addr_1;
    for (int i = 0; i < 1; i++)
        for (unsigned long long j = 0; j < size_1st; j += 2)
            tmp_addr[j] = j % 256;
    // sleep(20);
    // 2nd phase: malloc for 80% of total space
    size_2nd = 0.8 * btotal;
    printf("2nd phase: allocate %lldMB\n", size_2nd >> 20);
    addr_2 = mmap(NULL, size_2nd, PROT_READ | PROT_WRITE, MAP_ANONYMOUS | MAP_PRIVATE, -1, 0);
    if (use_huge) {
        if (madvise(addr_2, size_2nd, MADV_HUGEPAGE) < 0) {
            perror("error");
            exit(-1);
        }
    } else {
        if (madvise(addr_2, size_2nd, MADV_NOHUGEPAGE) < 0) {
            perror("error");
            exit(-1);
        }
    }
    // memset 1GB per second for the 2nd phase
    memset(addr_2, 200, size_2nd);
    tmp_addr = (unsigned char *) addr_2;
    for (int i = 0; i < 1; i++)
        for (unsigned long long j = 0; j < size_2nd; j+= 16)
            tmp_addr[j] = j % 256;
    // sleep(30);
    // 3rd phase: malloc for the rest of total space (same as 1st)
    size_3rd = size_1st;
    printf("3rd phase: allocate %lldMB\n", size_3rd >> 20);
	addr_3 = mmap(NULL, size_3rd, PROT_READ | PROT_WRITE, MAP_ANONYMOUS | MAP_PRIVATE, -1, 0);
    if (use_huge) {
        if (madvise(addr_3, size_3rd, MADV_HUGEPAGE) < 0) {
            perror("error");
            exit(-1);
        }
    } else {
        if (madvise(addr_3, size_3rd, MADV_NOHUGEPAGE) < 0) {
            perror("error");
            exit(-1);
        }
    }
    // memset 1GB per second for the 3rd phase
    memset(addr_3, 3000, size_3rd);
    tmp_addr = (unsigned char *) addr_3;
    for (int i = 0; i < 1; i++)
        for (unsigned long long j = 0; j < size_3rd; j+=2)
            tmp_addr[j] = j % 256;
    // sleep(30);

    // final run over all ranges
    unsigned char * addrs[3];
    addrs[0] = (unsigned char *) addr_1;
    addrs[1] = (unsigned char *) addr_2;
    addrs[2] = (unsigned char *) addr_3;

        for (unsigned long i = 0; i < size_2nd; i += 64)
            addrs[1][i] = addrs[0][i % size_1st] * addrs[2][i % size_3rd];

    munmap(addr_1, size_1st);
    munmap(addr_2, size_2nd);
    munmap(addr_3, size_3rd);

    return 0;
}
