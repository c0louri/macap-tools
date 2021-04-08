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
    int c;
    char *out_name = "./page-collect.dat";
    pid_t opt_pid = 0;	/* process to walk */
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
    return collect_custom_pagemap(opt_pid, out_name);
    // return collect_pagemap_hist(opt_pid, out_name, 0, 0);
}
