#!/bin/bash

ACTION=$1
# possible actions: only_vma, only_offset, only_cov

if [ "x$2" != "x" ]; then
    PID=$2
else
    FILENAME=$(ls pagemap_*_0_pre.out)
    FILENAME=${FILENAME%_0_pre.out}
    PID=${FILENAME#pagemap_}
fi

#echo "PID:$PID"
ITER=-1
while true
do
    ((ITER+=1))
    PRE_FILE=pagemap_${PID}_${ITER}_pre.out
    if [[ -e $PRE_FILE ]]; then
        if [ "x$ACTION" != "x" ]; then
            CMD="python3 print_stats.py ${PRE_FILE}"
        else
            CMD="python3 print_stats.py ${PRE_FILE} ${ACTION}"
        fi
        echo "${ITER}_PRE_DEFRAG:"
        eval $CMD
    else
        break
    fi

    POST_FILE=pagemap_${PID}_${ITER}_post.out
    if [[ -e $POST_FILE ]]; then
        if [ "x$ACTION" != "x" ]; then
            CMD="python3 print_stats.py ${PRE_FILE}"
        else
            CMD="python3 print_stats.py ${PRE_FILE} ${ACTION}"
        fi
        echo "\n${ITER}_POST_DEFRAG:"
        eval $CMD
    else
        continue
    fi
    echo ""
done
