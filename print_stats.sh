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

echo "PID:$PID"
echo "Present pages, Not present pages, Present pages in subVMAs, Good-offset pages, Bad-offset pages"
ITER=-1
while true
do
    ((ITER+=1))
    PRE_FILE=pagemap_${PID}_${ITER}_pre.out
    if [[ -e $PRE_FILE ]]; then
        #echo $PRE_FILE
        echo "${ITER}_PRE_DEFRAG:"
        python3 pagemap.py $PRE_FILE 
    else
        break 
    fi        

    POST_FILE=pagemap_${PID}_${ITER}_post.out
    if [[ -e $POST_FILE ]]; then
        #echo $POST_FILE
        echo "${ITER}_POST_DEFRAG:"
        python3 pagemap.py $POST_FILE
    else
        continue 
    fi
    echo ""        
done
