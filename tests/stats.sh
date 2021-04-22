#!/bin/bash
mkdir -p results
../pagecollect/pagecollect -p $1 -o results/vmas_pagemap_$1_$2_$3.out 2>results/pagecollect_$1_$2_$3.out
python3 ../print_stats.py results/vmas_pagemap_$1_$2_$3.out
