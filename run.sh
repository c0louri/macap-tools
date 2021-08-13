#!/bin/bash

FRAG_UNFIN=true
trap "FRAG_UNFIN=false" SIGUSR2

## 1st -> CPUs
## 2nd -> alloc fails allowed
## 3rd -> yes or no for fragmenter use
## 4th -> if yes, nodefrag
## 5th -> defrag only marked pages

echo always >/sys/kernel/mm/transparent_hugepage/enabled
echo never >/sys/kernel/mm/transparent_hugepage/defrag
echo 0 >/sys/kernel/mm/transparent_hugepage/khugepaged/defrag
echo 999999 >/sys/kernel/mm/transparent_hugepage/khugepaged/alloc_sleep_millisecs
echo 999999 >/sys/kernel/mm/transparent_hugepage/khugepaged/scan_sleep_millisecs

# CaP sysctl config:
sysctl vm.cap_direct_pcp_alloc=0
# sysctl vm.cap_aligned_offset=0
sysctl vm.cap_eager_placement=1
# sysctl vm.cap_old = 0

# TRanger sysctl config:
sysctl vm.defrag_buf_log_level=0 # (0->none, 1->def log, 2->compact, 3->extended fails)
sysctl vm.defrag_ignore_drain=0
# sysctl vm.defrag_split_thp=1
# sysctl vm.defrag_range_ignoring=0
sysctl vm.vma_scan_threshold_type=1
sysctl vm.vma_scan_percentile=100
sysctl vm.defrag_size_threshold=5
# sysctl vm.num_breakout_chunks=
# sysctl vm.vm.vma_no_repeat_defrag=1


echo 5000 > /sys/kernel/mm/transparent_hugepage/kmem_defragd/scan_sleep_millisecs

BENCH=$1
export CPUS=$2
FAILED_ALLOCS_AFTER=$3
USE_MEMFRAG=$4
USE_DEFRAG=$5
MARKED_DEFRAG=$6
ITER=$7
SUB_HP_K=$8
PERC_KEEP=$9
DEFRAG_SCAN_INTERVAL=$10
FRAG_SIZE="220G" # ram 240gb

#
if [[ "x${DEFRAG_SCAN_INTERVAL}" == "x" ]]; then
    echo 5000 > /sys/kernel/mm/transparent_hugepage/kmem_defragd/scan_sleep_millisecs
else
    echo $DEFRAG_SCAN_INTERVAL > /sys/kernel/mm/transparent_hugepage/kmem_defragd/scan_sleep_millisecs
fi
#

if [[ "x${BENCH}" == "xliblinear" ]]; then
    BENCH_RUN="/home/user/benchmarks/liblinear/liblinear-2.43/train /home/user/benchmarks/liblinear/kdd12.tr"
    PERC="80"
elif [[ "x${BENCH}" == "xXSBench" ]]; then
    BENCH_RUN="/home/user/benchmarks/XSBench/openmp-threading/XSBench -t ${CPUS} -s XL -l 64 -G unionized -p 500000"
    PERC="40"
elif [[ "x${BENCH}" == "xmicro" ]]; then
    BENCH_RUN="/home/user/ppac-tools/micro 120G"
    PERC="40"
fi

if [[ "x${PERC_KEEP}" == "x" ]]; then
    PERC_LEFT_ALLOC=$PERC
else
    PERC_LEFT_ALLOC=$PERC_KEEP
fi

if [[ "x${SUB_HP_K}" == "x" ]]; then
    SUB_HP_KEEP="0"
else
    SUB_HP_KEEP=$SUB_HP_K
fi

if [[ "x${STATS_PERIOD}" == "x" ]]; then
    STATS_PERIOD=10
    if [[ "x${BENCH}" == "xliblinear" ]]; then
         STATS_PERIOD=30
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

if [[ "x${USE_DEFRAG}" == "xcap" ]]; then # using only Ca Paging
    LAUNCHER="${PROJECT_LOC}/simple_run --dumpstats --dumpstats_period ${STATS_PERIOD} --nomigration --capaging --defrag_online_stats"
    BENCH="${BENCH}_cap"
    echo 999999 > /sys/kernel/mm/transparent_hugepage/kmem_defragd/scan_sleep_millisecs
    sysctl vm.kthread_defragd_disabled=1
elif [[ "x${USE_DEFRAG}" == "xboth_syscall" ]]; then # using both, defrag is executed through syscall
    BENCH="${BENCH}_both"
    LAUNCHER="${PROJECT_LOC}/simple_run --dumpstats --dumpstats_period ${STATS_PERIOD} --nomigration --capaging --defrag_online_stats --mem_defrag_with_syscall"
    echo 999999 > /sys/kernel/mm/transparent_hugepage/kmem_defragd/scan_sleep_millisecs
    sysctl vm.kthread_defragd_disabled=1
elif [[ "x${USE_DEFRAG}" == "xranger_syscall" ]]; then # using only TRanger with syscalls
    BENCH="${BENCH}_ranger"
    LAUNCHER="${PROJECT_LOC}/simple_run --dumpstats --dumpstats_period ${STATS_PERIOD} --nomigration --defrag_online_stats --mem_defrag_with_syscall"
    echo 999999 > /sys/kernel/mm/transparent_hugepage/kmem_defragd/scan_sleep_millisecs
    sysctl vm.kthread_defragd_disabled=1
elif [[ "x${USE_DEFRAG}" == "xranger" ]]; then # using only TRanger with syscalls
    BENCH="${BENCH}_ranger"
    LAUNCHER="${PROJECT_LOC}/simple_run --dumpstats --dumpstats_period ${STATS_PERIOD} --nomigration --defrag_online_stats --mem_defrag"
    echo 999999 > /sys/kernel/mm/transparent_hugepage/kmem_defragd/scan_sleep_millisecs
    sysctl vm.kthread_defragd_disabled=0
else # using both, defrag is executed in a kthread
    BENCH="${BENCH}_both"
    LAUNCHER="${PROJECT_LOC}/simple_run --dumpstats --dumpstats_period ${STATS_PERIOD} --nomigration --capaging --defrag_online_stats --mem_defrag"
    sysctl vm.kthread_defragd_disabled=0
fi

if [[ "x${MARKED_DEFRAG}" == "xno" ]]; then
    sysctl vm.defrag_only_misplaced=0
    BENCH="${BENCH}_all"
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
# echo $FAST_NUMA_NODE_CPUS
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
# echo $NUMACTL_CMD

GLOBAL_RES_FOLDER=results
export NTHREADS=${CPUS}
CUR_PWD=`pwd`

#cat /proc/vmstat | grep defrag > vmstat_init.out

for FAILS in $FAILED_ALLOCS_AFTER; do
    sysctl vm.cap_2mb_alloc_fails=$FAILS
    echo "begin benchmark ${BENCH} failed_allocs=${FAILS}, memfrag=${USE_MEMFRAG} size=${FRAG_SIZE}, per_sub_hp=${SUB_HP_KEEP} per_left_alloc=${PERC_LEFT_ALLOC}"
    # start fragmentation tool if it is needed
    dmesg -c > /dev/null
    cat /proc/capaging_contiguity_map > cmap_init.out
    if [[ "x${USE_MEMFRAG}" == "xyes" ]]; then
        ./memfrag ${FRAG_SIZE} ${SUB_HP_KEEP} ${PERC_LEFT_ALLOC} &
        FRAG_PID=$!
        #sleep 140
        while $FRAG_UNFIN; do : ; done
        sleep 5
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
    cat /proc/capaging_contiguity_map > cmap_after_frag.out

    BENCH_CONF="${BENCH}_${FAILS}"
    if [[ "x${ITER}" == "x" ]]; then
        RES_FOLDER="${GLOBAL_RES_FOLDER}/${BENCH_CONF}_"
    else
        RES_FOLDER="${GLOBAL_RES_FOLDER}/${BENCH_CONF}_${ITER}"
    fi
    if [[ "x${USE_MEMFRAG}" == "xyes" ]]; then
        RES_FOLDER="${RES_FOLDER}_${SUB_HP_KEEP}-${PERC_LEFT_ALLOC}"
    else
        RES_FOLDER="${RES_FOLDER}_0-0"
    fi
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
    cat /proc/capaging_contiguity_map > cmap_end.out
    # calc counters of CAP, defrag for more complete stats
    python3 helpers/calc_counter_stats.py counters_start.out counters_end.out > counters_stats.txt

    DEF_BUF_LEVEL=$(cat /proc/sys/vm/defrag_buf_log_level)
    if [[ "x${DEF_BUF_LEVEL}" == "x3" ]]; then # log : fails and pages
        mkdir ${CUR_PWD}/${RES_FOLDER}/d_iters
        python3 helpers/parse_defrag_fails.py defrag_online_stats_0
        mv def_iter_* ${CUR_PWD}/${RES_FOLDER}/d_iters/

    elif [[ "x${DEF_BUF_LEVEL}" == "x2" ]]; then # compact stats
        python3 helpers/parse_defrag_results.py defrag_online_stats_0 > defrag_compact_stats
        mv defrag_compact_stats ${CUR_PWD}/${RES_FOLDER}/
    fi

    # move pagemap files and counters
    mv defrag_online_stats_* ${CUR_PWD}/${RES_FOLDER}/
    mv counters* ${CUR_PWD}/${RES_FOLDER}/
    dmesg -s 32768000 > ${CUR_PWD}/${RES_FOLDER}/dmesg.out
    mv cmap* ${CUR_PWD}/${RES_FOLDER}/
    mkdir ${CUR_PWD}/${RES_FOLDER}/pagemaps
    rm ${CUR_PWD}/${RES_FOLDER}/pagemaps/*
    mv pagemap_* ${CUR_PWD}/${RES_FOLDER}/pagemaps
    # create separate defrag iter logs
    chown -R user ${CUR_PWD}/
    echo "benchmark ended"
done
#sudo poweroff
