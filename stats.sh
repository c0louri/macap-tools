#!/bin/bash

./pagecollect/pagecollect -p $1 -o vmas_pagemap_$1_$2_$3.out 2>pagecollect_$1_$2_$3.out
python3 pagemap.py vmas_pagemap_$1_$2_$3.out
