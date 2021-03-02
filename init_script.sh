#!/bin/bash
echo never >/sys/kernel/mm/transparent_hugepage/defrag
echo never >/sys/kernel/mm/transparent_hugepage/enabled
echo 500 >/sys/kernel/mm/transparent_hugepage/khugepaged/max_ptes_none

sysctl vm.vma_scan_threshold_type=1
sysctl vm.vma_scan_percentile=100
echo -n 'file mm/mem_defrag.c -p' > /sys/kernel/debug/dynamic_debug/control
