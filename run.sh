#!/bin/bash

BENCH=liblinear_2
BENCH_RUN="/home/user/benchmarks/liblinear/liblinear-2.43/train /home/user/benchmarks/liblinear/kdd12.tr"
FAILED_ALLOCS_AFTER="2 1 0 2 3 4 5 10 20"
SPLIT_THP="split"
# STATS_PERIODS="5 30"

echo always >/sys/kernel/mm/transparent_hugepage/enabled
echo never >/sys/kernel/mm/transparent_hugepage/defrag
echo 0 >/sys/kernel/mm/transparent_hugepage/khugepaged/defrag
#echo 999999 >/sys/kernel/mm/transparent_hugepage/khugepaged/alloc_sleep_millisecs
#echo 999999 >/sys/kernel/mm/transparent_hugepage/khugepaged/scan_sleep_millisecs
sysctl vm.defrag_ignore_drain=0
sysctl vm.cap_direct_pcp_alloc=0


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

LAUNCHER="${PROJECT_LOC}/simple_run --dumpstats --dumpstats_period ${STATS_PERIOD} --nomigration --capaging --defrag_online_stats --mem_defrag"
# LAUNCHER="${PROJECT_LOC}/simple_run --dumpstats --dumpstats_period ${STATS_PERIOD} --nomigration --capaging --defrag_online_stats"

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

GLOBAL_RES_FOLDER=results
export NTHREADS=${CPUS}
CUR_PWD=`pwd`

cat /proc/vmstat | grep defrag > vmstat_init.out

for SPLIT in $SPLIT_THP; do
    if [[ "x${SPLIT}" == "xnosplit" ]]; then
        sysctl vm.defrag_split_thp=0
    else
        sysctl vm.defrag_split_thp=1
    fi
    for FAILS in $FAILED_ALLOCS_AFTER; do
        sysctl vm.cap_2mb_alloc_fails=$FAILS
        echo "begin benchmark split_thp=${SPLIT}, failed_allocs=${FAILS}"
        rm kdd12.tr.model
        ./clean.sh
        BENCH_CONF="${BENCH}_${SPLIT}_${FAILS}"
        RES_FOLDER="${GLOBAL_RES_FOLDER}/${BENCH_CONF}"
        mkdir $RES_FOLDER
        # save initial values of vmstat, capaging counters
        cat /proc/vmstat | grep memdefrag > counters_start.out
        echo "Capaging failure 4K (0-order) counters:" >> counters_start.out
        cat /proc/capaging/0/failure >> counters_start.out
        echo "Capaging failure 2M (9-order) counters:" >> counters_start.out
        cat /proc/capaging/9/failure >> counters_start.out
        ${NUMACTL_CMD} -- ${BENCH_RUN} 2> ${CUR_PWD}/${RES_FOLDER}/${BENCH_CONF}_cycles.txt
        # save values of vmstat, capaging counters after execution
        cat /proc/vmstat | grep memdefrag > counters_end.out
        echo "Capaging failure 4K (0-order) counters:" >> counters_end.out
        cat /proc/capaging/0/failure >> counters_end.out
        echo "Capaging failure 2M (9-order) counters:" >> counters_end.out
        cat /proc/capaging/9/failure >> counters_end.out
        echo "Printing stats..."
        ./get_stats.sh complete_results > ${CUR_PWD}/${RES_FOLDER}/${BENCH_CONF}_stats.txt
        # move outputs of counters to res_folder of benchmark and change ownership to user (non-root)
        mv pagemap_* ${CUR_PWD}/${RES_FOLDER}/
        mv counters* ${CUR_PWD}/${RES_FOLDER}/
        chmod -R user ${CUR_PWD}/
        # sync; echo 3 > /proc/sys/vm/drop_caches # drop all OS' caches
        echo "benchmark ended"
    done
done
