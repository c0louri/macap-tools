#!/bin/bash

BENCH=liblinear_nodefrag_nopcp
BENCH_RUN="/home/user/benchmarks/liblinear/liblinear-2.43/train /home/user/benchmarks/liblinear/kdd12.tr"
FAILED_ALLOCS_AFTER="0 1 2 5 10"
break_chunks="0"

echo always >/sys/kernel/mm/transparent_hugepage/enabled
echo never >/sys/kernel/mm/transparent_hugepage/defrag
echo 0 >/sys/kernel/mm/transparent_hugepage/khugepaged/defrag
#echo 999999 >/sys/kernel/mm/transparent_hugepage/khugepaged/alloc_sleep_millisecs
#echo 999999 >/sys/kernel/mm/transparent_hugepage/khugepaged/scan_sleep_millisecs


if [ "x$1" != "x" ]
then
	export CPUS=$1
else
	export CPUS=1
fi

if [[ "x${STATS_PERIOD}" == "x" ]]; then
	STATS_PERIOD=30
fi

PROJECT_LOC=$(pwd)

LAUNCHER="${PROJECT_LOC}/simple_run --dumpstats --dumpstats_period ${STATS_PERIOD} --nomigration --capaging --defrag_online_stats"

#PREFER MEM MODE
if [[ "x${PREFER_MEM_MODE}" == "xyes" ]]; then
NUMACTL_CMD="${LAUNCHER} -N 0 --prefer_memnode 0"
else
NUMACTL_CMD="${LAUNCHER} -N 0 -m 0"
fi

# set CPUMASK for numa config
FAST_NUMA_NODE=0
FAST_NUMA_NODE_CPUS=`numactl -H| grep "node ${FAST_NUMA_NODE} cpus" | cut -d" " -f 4-`
echo $FAST_NUMA_NODE_CPUS
read -a CPUS_ARRAY <<< "${FAST_NUMA_NODE_CPUS}"
ALL_CPU_MASK=0
for IDX in $(seq 0 $((CPUS-1)) ); do
    CPU_IDX=$((IDX % ${#CPUS_ARRAY[@]}))
    CPU_MASK=$((1<<${CPUS_ARRAY[${CPU_IDX}]}))
    #CPU_MASK=$((1<<${CPUS_ARRAY[${CPU_IDX}]} | 1<<(${CPUS_ARRAY[${CPU_IDX}]}+${TOTAL_CORE})))
    ALL_CPU_MASK=`echo "${CPU_MASK}+${ALL_CPU_MASK}" | bc`
done
ALL_CPU_MASK=`echo "obase=16; ${ALL_CPU_MASK}" | bc`
NUMACTL_CMD="${NUMACTL_CMD} -c 0x${ALL_CPU_MASK}"
echo $NUMACTL_CMD

RES_FOLDER=results
export NTHREADS=${CPUS}
CUR_PWD=`pwd`

sysctl vm.cap_direct_pcp_alloc=1

for CHUNKS in $break_chunks; do
    sysctl vm.num_breakout_chunks=$CHUNKS
    for FAILS in $FAILED_ALLOCS_AFTER; do
        echo "begin benchmark chunks=${CHUNKS}, failed_allocs=${FAILS}"
        rm kdd12.tr.model
        ./clean.sh
        sysctl vm.cap_2mb_alloc_fails=$FAILS
        mkdir results/${BENCH}_${FAILS}
        ${NUMACTL_CMD} -- ${BENCH_RUN} 2> ${CUR_PWD}/${RES_FOLDER}/${BENCH}_${FAILS}/${BENCH}_${FAILS}_cycles.txt
        echo "Printing stats..."
        ./print_stats.sh > ${CUR_PWD}/${RES_FOLDER}/${BENCH}_${FAILS}/${BENCH}_${FAILS}.stats.txt
        ./print_cov_stats.sh > ${CUR_PWD}/${RES_FOLDER}/${BENCH}_${FAILS}/${BENCH}_${FAILS}.cov_stats.txt        
        # mv pagemap_* ${CUR_PWD}/${RES_FOLDER}/${BENCH}_${FAILS}/
    done
done
