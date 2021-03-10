#!/bin/bash

./pagecollect/pagecollect -p $1 -o vmas_pagemap_$1.out
python3 pagemap.py vmas_pagemap_$1.out
