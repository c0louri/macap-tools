#!/bin/bash

echo never >/sys/kernel/mm/transparent_hugepage/defrag
echo madvise >/sys/kernel/mm/transparent_hugepage/enabled
echo 0 >/sys/kernel/mm/transparent_hugepage/khugepaged/defrag

sysctl vm.num_breakout_chunks=50
sysctl vm.cap_2mb_alloc_fails=3


if [ "x$1" != "x" ]
then
	export CPUS=$1
else
	export CPUS=1
fi

if [[ "x${STATS_PERIOD}" == "x" ]]; then
	STATS_PERIOD=5
fi

PROJECT_LOC=$(pwd)

LAUNCHER="${PROJECT_LOC}/simple_run --dumpstats --dumpstats_period ${STATS_PERIOD} --nomigration --mem_defrag --capaging --defrag_online_stats"

#PREFER MEM MODE
if [[ "x${PREFER_MEM_MODE}" == "xyes" ]]; then
NUMACTL_CMD="${LAUNCHER} -N 0 --prefer_memnode 0"
else
NUMACTL_CMD="${LAUNCHER} -N 0 -m 0"
fi

echo "begin benchmark"

RES_FOLDER=results
export NTHREADS=${CPUS}
sudo dmesg -c >/dev/null
CUR_PWD=`pwd`

echo madvise >/sys/kernel/mm/transparent_hugepage/enabled
export > ${CUR_PWD}/${RES_FOLDER}/${BENCH}_env_madvise
${NUMACTL_CMD} -- ${BENCH_RUN} 2> ${CUR_PWD}/${RES_FOLDER}/${BENCH}_cycles_madvise
echo always >/sys/kernel/mm/transparent_hugepage/enabled
export > ${CUR_PWD}/${RES_FOLDER}/${BENCH}_env_always
${NUMACTL_CMD} -- ${BENCH_RUN} 2> ${CUR_PWD}/${RES_FOLDER}/${BENCH}_cycles_always

unset BENCH_RUN
unset BENCH

