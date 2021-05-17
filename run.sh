#!/bin/bash

## 1st -> CPUs
## 2nd -> alloc fails allowed
## 3rd -> yes or no for fragmenter use
## 4th -> if yes, nodefrag
## 5th -> defrag only marked pages

#BENCH=liblinear
#BENCH_RUN="/home/user/benchmarks/liblinear/liblinear-2.43/train /home/user/benchmarks/liblinear/kdd12.tr"
BENCH=XSBench
BENCH_RUN="/home/user/benchmarks/XSBench/openmp-threading/XSBench -t 10 -s XL -l 64 -G unionized"

echo always >/sys/kernel/mm/transparent_hugepage/enabled
echo never >/sys/kernel/mm/transparent_hugepage/defrag
echo 0 >/sys/kernel/mm/transparent_hugepage/khugepaged/defrag
#echo 999999 >/sys/kernel/mm/transparent_hugepage/khugepaged/alloc_sleep_millisecs
#echo 999999 >/sys/kernel/mm/transparent_hugepage/khugepaged/scan_sleep_millisecs

sysctl vm.defrag_ignore_drain=0
sysctl vm.cap_direct_pcp_alloc=0
sysctl vm.cap_aligned_offset=0
sysctl vm.defrag_show_only_subchunk_stats=1

echo 3000 > /sys/kernel/mm/transparent_hugepage/kmem_defragd/scan_sleep_millisecs

export CPUS=$1
FAILED_ALLOCS_AFTER=$2
USE_MEMFRAG=$3
USE_DEFRAG=$4
MARKED_DEFRAG=$5

FRAG_SIZE="140G"

if [[ "x${STATS_PERIOD}" == "x" ]]; then
    STATS_PERIOD=20
    if [[ "x${BENCH}" == "xliblinear" ]]; then
         STATS_PERIOD=60
    fi
    if [[ "x${BENCH}" == "xXSBench" ]]; then
        STATS_PERIOD=10
    fi
fi

if [[ "x${USE_MEMFRAG}" == "xyes" ]]; then
	BENCH="${BENCH}_frag"
else
	BENCH="${BENCH}_fresh"
fi

PROJECT_LOC=$(pwd)

if [[ "x${USE_DEFRAG}" == "xno" ]]; then
    LAUNCHER="${PROJECT_LOC}/simple_run --dumpstats --dumpstats_period ${STATS_PERIOD} --nomigration --capaging --defrag_online_stats"
    BENCH="${BENCH}_nodef"
elif [[ "${USE_DEFRAG}" == "xsyscall" ]]; then
    LAUNCHER="${PROJECT_LOC}/simple_run --dumpstats --dumpstats_period ${STATS_PERIOD} --nomigration --capaging --defrag_online_stats --mem_defrag_with_syscall"
    echo 999999 > /sys/kernel/mm/transparent_hugepage/kmem_defragd/scan_sleep_millisecs
else
    LAUNCHER="${PROJECT_LOC}/simple_run --dumpstats --dumpstats_period ${STATS_PERIOD} --nomigration --capaging --defrag_online_stats --mem_defrag"
fi

if [[ "x${MARKED_DEFRAG}" == "xno" ]]; then
    sysctl vm.defrag_only_misplaced=0
else
    sysctl vm.defrag_only_misplaced=1
    BENCH="${BENCH}_mark"
fi

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

for FAILS in $FAILED_ALLOCS_AFTER; do
    sysctl vm.cap_2mb_alloc_fails=$FAILS
    echo "begin benchmark ${BENCH} failed_allocs=${FAILS}, memfrag=${USE_MEMFRAG} size=${FRAG_SIZE}"
    # start fragmentation tool if it is needed
    if [[ "x${USE_MEMFRAG}" == "xyes" ]]; then
        ./memfrag ${FRAG_SIZE} 5 10 &
        FRAG_PID=$!
        sleep 140
    fi
    ## clean previous run's stats/outputs/etc
    rm kdd12.tr.model
    ./clean.sh

    # save initial values of vmstat, capaging counters
    cat /proc/vmstat | grep memdefrag > counters_start.out
    echo "Capaging failure 4K (0-order) counters:" >> counters_start.out
    cat /proc/capaging/0/failure >> counters_start.out
    echo "Capaging failure 2M (9-order) counters:" >> counters_start.out
    cat /proc/capaging/9/failure >> counters_start.out
     echo "THP collapse vmstat counters:" >> counters_start.out
    cat /proc/vmstat | grep thp_promote >> counters_start.out

    BENCH_CONF="${BENCH}_${FAILS}"
    RES_FOLDER="${GLOBAL_RES_FOLDER}/${BENCH_CONF}"
    mkdir $RES_FOLDER
    ${NUMACTL_CMD} -- ${BENCH_RUN} 2> ${CUR_PWD}/${RES_FOLDER}/${BENCH_CONF}_cycles.txt

    # save values of vmstat, capaging counters after execution
    cat /proc/vmstat | grep memdefrag > counters_end.out
    echo "Capaging failure 4K (0-order) counters:" >> counters_end.out
    cat /proc/capaging/0/failure >> counters_end.out
    echo "Capaging failure 2M (9-order) counters:" >> counters_end.out
    cat /proc/capaging/9/failure >> counters_end.out
    echo "THP collapse vmstat counters:" >> counters_end.out
    cat /proc/vmstat | grep thp_promote >> counters_end.out

    # kill fragmenter if it used
    if [[ "x$USE_MEMFRAG" == "xyes" ]]; then
        kill -USR1 $FRAG_PID
    fi
    echo "Printing stats..."
    # collect stats from pagemap files
    ./get_stats.sh complete_results > ${CUR_PWD}/${RES_FOLDER}/${BENCH_CONF}_stats.txt
    # calc counters of CAP, defrag for more complete stats
    python3 helpers/calc_counter_stats.py counters_start.out counters_end.out > counters_stats.txt
    # move pagemap files and counters
    mv defrag_online_stats_* ${CUR_PWD}/${RES_FOLDER}/
    mv counters* ${CUR_PWD}/${RES_FOLDER}/
    dmesg > ${CUR_PWD}/${RES_FOLDER}/dmesg.out
    mkdir ${CUR_PWD}/${RES_FOLDER}/pagemaps
    rm ${CUR_PWD}/${RES_FOLDER}/pagemaps/*
    mv pagemap_* ${CUR_PWD}/${RES_FOLDER}/pagemaps
    chown -R user ${CUR_PWD}/
    # sync; echo 3 > /proc/sys/vm/drop_caches # drop all OS' caches
    echo "benchmark ended"
done
#sudo poweroff
