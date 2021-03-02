#!/bin/bash

./pagecollect/pagecollect -p $1 -o custom_pagemap_$1.out
python3 pagemap.py $1 1 custom_pagemap_$1.out
