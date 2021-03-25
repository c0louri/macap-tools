#!/usr/bin/bash

#global
SIZE=8 #8 is multiplier of 128mb

# signal handlers
function pre_handler()
(
	echo "Collecting predefrag stats for $!"
	./stats.sh $! pre 0 >res_$CASE.out
	kill -SIGUSR1 $!
)

function post_handler()
{
	echo "Collecting postdefrag stats for $!"
	./stats.sh $! post 0 >>res_$CASE.out
	kill -SIGUSR1 $!
}
trap pre_handler SIGUSR1
trap post_handler SIGUSR2

# disable defrag for every test
echo never >/sys/kernel/mm/transparent_hugepage/defrag
echo 0 >/sys/kernel/mm/transparent_hugepage/khugepaged/defrag


## with THP enabled
echo always >/sys/kernel/mm/transparent_hugepage/enabled

CASE=always_lin
echo $CASE  
./test -l $SIZE --mem_defrag --capaging --with_signals > run.out &
wait $!; wait $!
sleep 1

CASE=always_random
echo $CASE  
./test -l $SIZE --mem_defrag --capaging --random_alloc --with_signals >> run.out &
wait $!; wait $!
sleep 1

## without THP enabled
echo never >/sys/kernel/mm/transparent_hugepage/enabled
CASE=never_lin
echo $CASE  
./test -l $SIZE --mem_defrag --capaging --with_signals >>run.out  &
wait $!; wait $!
sleep 1

CASE=never_random
echo $CASE  
./test -l $SIZE --mem_defrag --capaging --random_alloc --with_signals >>run.out &
wait $!; wait $!
sleep 1

#madvise case
echo madvise >/sys/kernel/mm/transparent_hugepage/enabled
CASE=madv_lin
echo $CASE  
./test -l $SIZE --mem_defrag --capaging --madv_hp --with_signals >>run.out &
wait $!; wait $!
sleep 1
CASE=madv_random
echo $CASE  
./test -l $SIZE --mem_defrag --capaging --random_alloc --madv_hp --with_signals >>run.out &
wait $!; wait $!
sleep 1
trap - USR1
trap - USR2

mkdir results
mv res_* results/
#rm pagecollect_*
#rm vmas_pagemap_*
