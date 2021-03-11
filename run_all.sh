#!/bin/bash

echo never >/sys/kernel/mm/transparent_hugepage/defrag
echo madvise >/sys/kernel/mm/transparent_hugepage/enabled
echo 0 >/sys/kernel/mm/transparent_hugepage/khugepaged/defrag

NUM_ITER=1
BENCH_LIST="503.postencil"
THREAD_NUM_LIST="2"
WORKLOAD_SIZE="05GB"
THP_SIZE_LIST="2mb"

export PREFER_MEM_MODE=yes
export STATS_PERIOD=5
export ONLINE_STATS=yes
export DO_DEFRAG=yes
export CAPAGING=yes
export NO_MIGRATE=
# for 128GB memory, scanning results take noticeable memory, it may kick out benchmark memory
# this option put scanning results on node 0
export RELOCATE_AGENT_MEM=no

for I in $(seq 1 ${NUM_ITER}); do
	for THP_SIZE in ${THP_SIZE_LIST}; do
		export THP_SIZE=${THP_SIZE}
		for SIZE in ${WORKLOAD_SIZE}; do
			export BENCH_SIZE=${SIZE}
			for BENCH in ${BENCH_LIST}; do
				export BENCH=${BENCH}
				echo "${BENCH}, ${BENCH_SIZE}"
				for THREAD_NUM in ${THREAD_NUM_LIST}; do
					echo "Run ${I}, Thread ${THREAD_NUM}, THP size ${THP_SIZE}, stats period: ${STATS_PERIOD}"
					./simple_r.sh ${THREAD_NUM};
					sleep 5;
				done
			done #BENCH
		done #SIZE
	done #THP_SIZE
done #I

unset PREFER_MEM_MODE
unset DO_DEFRAG
unset CAPAGING
unset NO_MIGRATE
unset ONLINE_STATS