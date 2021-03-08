/* page-collect.c -- collect a snapshot each of of the /proc/pid/maps files,
 *      with each VM region interleaved with a list of physical addresses
 *      which make up the virtual region.
 * Copyright C2009 by EQware Engineering, Inc.
 *
 *    page-collect.c is part of PageMapTools.
 *
 *    PageMapTools is free software: you can redistribute it and/or modify
 *    it under the terms of version 3 of the GNU General Public License
 *    as published by the Free Software Foundation
 *
 *    PageMapTools is distributed in the hope that it will be useful,
 *    but WITHOUT ANY WARRANTY; without even the implied warranty of
 *    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *    GNU General Public License for more details.
 *
 *    You should have received a copy of the GNU General Public License
 *    along with PageMapTools.  If not, see http://www.gnu.org/licenses.
 */

#define _LARGEFILE64_SOURCE

#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <assert.h>
#include <errno.h>
#include <string.h>
#include <getopt.h>

#include <sys/types.h>
#include <dirent.h>
#include <sys/stat.h>
#include <unistd.h>
#include <fcntl.h>
#include <ctype.h>

#include <stdint.h>
#include <map>
#include <vector>
#include <algorithm>
#include <string>
#include <math.h>

#include "page-collect.h"

// ERR() --
#define ERR(format, ...) fprintf(stderr, format, ## __VA_ARGS__)


// Regular_TLB - fixed size entry 4K or 2M
uint64_t Regular_TLB_4K = 0;
uint64_t Regular_TLB_2M = 0;


static struct option opts[] = {
    { "pid"       , 1, NULL, 'p' },
    { "out-file"  , 1, NULL, 'f' },
    { "help"      , 0, NULL, 'h' },
    { NULL        , 0, NULL, 0 }
};

// bool pairCompare(const std::pair<int64_t, uint64_t>& firstElem, const std::pair<int64_t, uint64_t>& secondElem) {
//     return firstElem.second > secondElem.second;
// }

// bool pairCompareMin(const std::pair<int64_t, uint64_t>& firstElem, const std::pair<int64_t, uint64_t>& secondElem) {
//     return firstElem.second < secondElem.second;
// }

// is_directory() --
static bool is_directory(const char *dirname)
{
    struct stat buf;
    int n;

    assert(dirname != NULL);

    n = stat(dirname, &buf);

    return (n == 0 && (buf.st_mode & S_IFDIR) != 0)? TRUE: FALSE;

}

void print_page_info(FILE *out, uint64_t vaddr, uint64_t pfn, bool is_thp) {
    if (pfn == 0) // page not present
        fprintf(out,  "0x%-16lx :pfn -1 ,offset 0 not_present\n", vaddr);
    else {
        long long offset = (vaddr>>PAGE_SHIFT) - pfn;
        if (is_thp)
            fprintf(out, "0x%-16lx :pfn %-16lx ,offset %lld thp\n", vaddr, pfn, offset);
        else
            fprintf(out, "0x%-16lx :pfn %-16lx ,offset %lld  no_thp\n", vaddr, pfn, offset);
    }
}

// usage() --
static void usage(void)
{
    fprintf(stderr,
        "usage: page-collect {switches}\n"
        "switches:\n"
        " -p pid          -- Collect only for process with $pid\n"
        " -o out-file     -- Output file name (def=%s)\n"
        "\n",
        OUT_NAME);
}


// main() --
int main(int argc, char *argv[])
{
    int n;
    FILE *m   = NULL;
    FILE *am  = NULL;
    int pm    = -1;
    int kflags = -1;
    FILE *out = NULL;
    int retval = 0;
    int c;
    char *out_name = "./page-collect.dat";
    pid_t opt_pid = 0;	/* process to walk */

    uint64_t total_present_pages = 0;
    // std::map<uint64_t, uint64_t> Offsets;
    // Process command-line arguments.
    while ((c = getopt_long(argc, argv, "o:f:p:h", opts, NULL)) != -1) {
        switch (c) {
        case 'o':
            out_name = optarg;
            break;
        case 'p':
            opt_pid = strtoll(optarg, NULL, 0);
            break;
        case 'h':
            usage();
            exit(0);
        default:
            usage();
            exit(1);
        }
    }

    // Open output file for writing.
    out = fopen(out_name, "w");
    if (out == NULL) {
        ERR("Unable to open file \"%s\" for writing (errno=%d). (1)\n", out_name, errno);
        retval = -1;
        goto done;
    }

    char d_name[FILENAMELEN];
    sprintf(d_name, "%s/%d", PROC_DIR_NAME, opt_pid);
    printf("-----Checking %s/%d...-----\n", PROC_DIR_NAME, opt_pid);

    // ...if the entry is a numerically-named directory...
    if (!is_directory(d_name)) {
        printf("Something wrong with proc path!\n");
        retval = -1;
        goto done;
    }

    char m_name[FILENAMELEN];
    char pm_name[FILENAMELEN];
    char kflags_name[FILENAMELEN];
    char am_name[FILENAMELEN];
    char line[LINELEN];

    //Open pid/maps file for reading.
    sprintf(m_name, "%s/%s", d_name, MAPS_NAME);
    m = fopen(m_name, "r");
    if (m == NULL)
    {
        ERR("Unable to open \"%s\" for reading (errno=%d) (5).\n", m_name, errno);
        exit(-1);
    }

    // Open pid/pagemap file for reading.
    sprintf(pm_name, "%s/%s", d_name, PAGEMAP_NAME);
    pm = open(pm_name, O_RDONLY);
    if (pm == -1)
    {
        ERR("Unable to open \"%s\" for reading (errno=%d). (7)\n", pm_name, errno);
        retval = -1;
        goto done;
    }

    //Open kpageflags file for reading.
    sprintf(kflags_name, "%s/%s", PROC_DIR_NAME, KPAGEFLAGS_NAME);
    kflags = open(kflags_name, O_RDONLY);
    if (kflags == -1)
    {
        ERR("Unable to open \"%s\" for reading (errno=%d). (7)\n", kflags_name, errno);
        retval = -1;
        goto done;
    }

    //Open pid/anchormaps for reading
    sprintf(am_name, "%s/%s", d_name, ANCHOR_MAPS_NAME);
    am = fopen(am_name, "r");
    if (am == NULL)
    {
        ERR("Unable to open \"%s\" for reading (errno=%d) (5).\n", am_name, errno);
        exit(-1);
    }
    while(fgets(line, LINELEN, am) != NULL)
    {
        fputs(line, out);
    }
    if (am != NULL) {
        fclose(am);
    }
    fputs("~!~\n", out);
    // START implementation
    // For each line in the maps file...
    while (fgets(line, LINELEN, m) != NULL)
    {
        unsigned long vm_start; // beginning of the current vma
        unsigned long vm_end;   // end of the current vma
        int num_pages = 0;      // size of the current vma

        unsigned long vpn;      // current vpn that is inspected
        unsigned long long pfn; // and corresponding pfn
        // long long current_offset;

        unsigned long prev_vpn = 0;         // previous vpn
        unsigned long long prev_pfn = 0;    // previous pfn
        // long long prev_offset = 0;

        // unsigned contiguity_length = 0;
        // get the range of the vma
        n = sscanf(line, "%lX-%lX", &vm_start, &vm_end);
        if (n != 2) {
            ERR("Invalid line read from \"%s\": %s (6)\n", m_name, line);
            continue;
        }

        num_pages = (vm_end - vm_start) / PAGE_SIZE;
        vpn = vm_start / PAGE_SIZE;


        // If the virtual address range is greater than 0.
        if (num_pages > 0)
        {
            //long index = (vm_start / PAGE_SIZE) * sizeof(unsigned long long);
            off64_t index = vpn * 8;
            off64_t o;
            ssize_t t;

            // Seek to the appropriate index of pagemap file.
            o = lseek64(pm, index, SEEK_SET);
            if (o != index) {
                ERR("Error seeking to %ld in file \"%s\" (errno=%d). (8)\n", index, pm_name, errno);
                continue;
            }

            // For each page in the vitual address range...
            while (num_pages > 0)
            {
                // contains the physical address read in /proc/$pid/pagemap
                unsigned long long pa;
                unsigned long current_page_size;

                // Read a 64-bit word from each of the pagemap file...
                t = read(pm, &pa, sizeof(unsigned long long));
                if (t < 0) {
                    ERR("Error reading file \"%s\" (errno=%d). (11)\n", pm_name, errno);
                    goto do_continue;
                }

                // if the physical page is present
                if (pa & PM_PRESENT) {

                    pfn = PM_PFRAME(pa);

                    // /proc/kpageflags
                    off64_t index_kflags = pfn * 8;
                    off64_t o_kflags;
                    unsigned long long kflags_result;

                    // Seek to appropriate index of /proc/kpageflags file.
                    o_kflags = lseek64(kflags, index_kflags, SEEK_SET);
                    if (o_kflags != index_kflags) {
                        ERR("Error seeking to %ld in file \"%s\" (errno=%d). (8)\n", index_kflags, kflags_name, errno);
                        continue;
                    }

                    // Read a 64-bit word from each of the /proc/kpageflags file...
                    t = read(kflags, &kflags_result, sizeof(unsigned long long));
                    if (t < 0) assert(0);

                    // now we should compute whether this is a 4K or a 2M entry
                    if (CMP_BIT(kflags_result, KPF_THP)) {
                        if ((vpn % 512 == 0) && (pfn % 512 == 0)) {
                            Regular_TLB_2M++;
                            current_page_size=512;
                        }
                        else {
                            printf("What is going on %lu %lu\n", vpn, pfn);
                        //	assert(0);
                        }
                    }
                    else {
                        Regular_TLB_4K++;
                        current_page_size=1;
                    }

                    // populate pagemap-like file
                    print_page_info(out, vpn << PAGE_SHIFT, pfn, (current_page_size==THP_SIZE ? 1 : 0));

                    // Tracking
                    // current_offset =  vpn - pfn;
                    // if (current_offset == prev_offset) {
                    //     contiguity_length += current_page_size;
                    //
                    // }
                    // else {
                    //     contiguity_length = current_page_size;
                    // }

                    // 6. track the number of mappings with same VA-to-PA (Offset)
                    // Offsets[vpn-pfn]+=current_page_size;

                    prev_vpn = vpn + current_page_size -1;
                    prev_pfn = pfn + current_page_size -1;
                    // prev_offset = current_offset;

                    total_present_pages+=current_page_size;
                }
                else {
                    // Page is NOT present
                    print_page_info(out, vpn << PAGE_SHIFT, 0, 0);
                }

                // 7. proceed with the next page in the virtual address range..
                num_pages-=current_page_size;
                vpn+=current_page_size;

                // if we found a 2MB page, jump forward in the pagemap file
                if(current_page_size == 512 && num_pages){
                    // Seek to the appropriate index of pagemap file.
                    off64_t _2M_index = vpn * 8;
                    o = lseek64(pm, _2M_index, SEEK_SET);
                    if (o != _2M_index) {
                        ERR("Error seeking to %ld in file \"%s\" (errno=%d). (8)\n", index, pm_name, errno);
                        continue;
                    }
                }

            }

        }
        do_continue:
        ;
    }
  // finalization phase..
  done:
    fprintf(out, "\n----------\n");
    fprintf(out, "\n----------\n");
    fprintf(out, "working_set\n");
    fprintf(out, "----------\n");
    fprintf(out, "total_present_pages: %ld\n", total_present_pages);
    fprintf(out, "4K pages: %ld\n", Regular_TLB_4K);
    fprintf(out, "2M pages: %ld\n", Regular_TLB_2M);
    fprintf(out, "total_present_working_set: %ld (MB)\n", total_present_pages * PAGE_SIZE / 1024 / 1024);

    // Finilizing things...
    if (pm != -1) {
        close(pm);
    }
    if (m != NULL) {
        fclose(m);
    }
    if (kflags != -1) {
        close(kflags);
    }
    if (out != NULL) {
        fclose(out);
    }
    return retval;
}
