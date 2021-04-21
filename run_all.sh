#!/bin/bash

./run.sh >run.out 2>run.err 
./run_no_defrag.sh >run.out 2>run.err
poweroff
