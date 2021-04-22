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

static struct option opts[] = {
    { "pid"       , 1, NULL, 'p' },
    { "out-file"  , 1, NULL, 'f' },
    { "raw_data_print", 1, NULL, 'r'},
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
        " -r              -- Print to file raw data of hists (def is not)\n"
        " -m              -- Print to file pagemap raw data (def is not)\n"
        "\n",
        OUT_NAME);
}

// main() --
int main(int argc, char *argv[])
{
    int c;
    char *out_name = OUT_NAME;
    pid_t opt_pid = 0;	/* process to walk */
    int print_raw_data = 0;
    int print_pagemap = 0;


    // Process command-line arguments.
    while ((c = getopt_long(argc, argv, "o:p:rmh", opts, NULL)) != -1) {
        switch (c) {
        case 'o':
            out_name = optarg;
            break;
        case 'p':
            opt_pid = strtoll(optarg, NULL, 0);
            if (opt_pid <= 0) {
                usage();
                exit(-1);
            }
            break;
        case 'r':
            print_raw_data = 1;
            break;
        case 'm': // print pagemap into file
            print_pagemap = 1;
            break;
        case 'h':
            usage();
            exit(0);
        default:
            usage();
            exit(1);
        }
    }

    return collect_pagemap_hist(opt_pid, out_name, print_raw_data, print_pagemap);
}