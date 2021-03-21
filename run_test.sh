#!/usr/bin/bash
set -e

# signal handlers
function pre_handler()
{
	echo "Collecting predefrag stats for $CHILD"
	../stats.sh $CHILD
	kill -SIGUSR1 $CHILD
}

function post_handler()
{
	echo "Collecting predefrag stats for $CHILD"
	../stats.sh $CHILD
	kill -SIGUSR2 $CHILD
}

trap pre_handler SIGUSR1
trap post_handler SIGUSR2

echo never >/sys/kernel/mm/transparent_hugepage/defrag
echo 0 >/sys/kernel/mm/transparent_hugepage/khugepaged/defrag


## with THP enabled
echo always >/sys/kernel/mm/transparent_hugepage/enabled
./tests/test -l 1 --mem_defrag --capaging --with_signals &
CHILD=$!
wait $CHILD
# ./tests/test -l 8 --mem_defrag --capaging --random_alloc --with_signals &
# CHILD=$!

# ## without THP enabled
# echo never >/sys/kernel/mm/transparent_hugepage/enabled
# ./tests/test -l 8 --mem_defrag --capaging --with_signals &
# CHILD=$!
# ./tests/test -l 8 --mem_defrag --capaging --random_alloc --with_signals &
# CHILD=$!

# echo madvise >/sys/kernel/mm/transparent_hugepage/enabled
# ./tests/test -l 8 --mem_defrag --capaging --madv_hp --with_signals &
# CHILD=$!
# ./test -l 8 --mem_defrag --capaging --random_alloc --madv_hp --with_signals &
# CHILD=$!

trap - USR1
trap - USR2
exit