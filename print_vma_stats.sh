#!/bin/bash

# PRE_FILES=$(ls pagemap_${PID}_*_pre.out)
# POST_FILES=$(ls pagemap_${PID}_*_post.out)
if [ "x$1" != "x" ]; then
    PID=$1
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
        #echo $PRE_FILE
        CMD="python3 pagemap.py ${PRE_FILE} only_vma"
        echo "${ITER}_PRE_DEFRAG:"
        eval $CMD
    else
        break 
    fi        

    POST_FILE=pagemap_${PID}_${ITER}_post.out
    if [[ -e $POST_FILE ]]; then
        echo ""
        #echo $POST_FILE
        CMD="python3 pagemap.py ${POST_FILE} only_vma"
        echo "${ITER}_POST_DEFRAG:"
        eval $CMD
    else
        continue 
    fi
    echo ""
done
