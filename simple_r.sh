#!/bin/bash

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

if [[ "x${RELOCATE_AGENT_MEM}" == "xyes" ]]; then
	LAUNCHER="${LAUNCHER} --relocate_agent_mem"
fi

#PREFER MEM MODE
if [[ "x${PREFER_MEM_MODE}" == "xyes" ]]; then
NUMACTL_CMD="${LAUNCHER} -N 1 --prefer_memnode 1"
else
NUMACTL_CMD="${LAUNCHER} -N 1 -m 1"
fi

# THREAD_PER_CORE=`lscpu|grep ^Thread|awk '{print $NF}'`
# CORE_PER_SOCKET=`lscpu|grep ^Core|awk '{print $NF}'`
# SOCKET=`lscpu|grep Socket|awk '{print $NF}'`
# TOTAL_CORE=$((CORE_PER_SOCKET*SOCKET))
# set CPUMASK for numa config
FAST_NUMA_NODE=1
FAST_NUMA_NODE_CPUS=`numactl -H| grep "node ${FAST_NUMA_NODE} cpus" | cut -d" " -f 4-`
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

echo "begin benchmark"

RES_FOLDER=results
mkdir -p ${RES_FOLDER}
# save sysctl vm config
sudo sysctl vm > ${RES_FOLDER}/vm_config

export NTHREADS=${CPUS}

sudo dmesg -c >/dev/null
CUR_PWD=`pwd`
	cd ${CUR_PWD}/${BENCH}
	source ./bench_run.sh
	export > ${CUR_PWD}/${RES_FOLDER}/${BENCH}_env
	eval ${PRE_CMD}
	${NUMACTL_CMD} -- ${BENCH_RUN} 2> ${CUR_PWD}/${RES_FOLDER}/${BENCH}_cycles
	eval ${POST_CMD}
	unset PRE_CMD
	unset POST_CMD


