#!/bin/bash
echo never >/sys/kernel/mm/transparent_hugepage/defrag
echo madvise >/sys/kernel/mm/transparent_hugepage/enabled
echo 0 >/sys/kernel/mm/transparent_hugepage/khugepaged/defrag
# echo never >/sys/kernel/mm/transparent_hugepage/defrag
# echo madvise >/sys/kernel/mm/transparent_hugepage/enabled
# echo 1 >/sys/kernel/mm/transparent_hugepage/khugepaged/defrag
# echo 511 >/sys/kernel/mm/transparent_hugepage/khugepaged/max_ptes_none
# echo 999999 >/sys/kernel/mm/transparent_hugepage/khugepaged/alloc_sleep_millisecs
# echo 999999 >/sys/kernel/mm/transparent_hugepage/khugepaged/scan_sleep_millisecs
# sysctl vm.vma_scan_threshold_type=1
# sysctl vm.vma_scan_percentile=100
# echo -n 'file mm/mem_defrag.c -p' > /sys/kernel/debug/dynamic_debug/control
# echo -n 'file mem_defrag.c -p' > /sys/kernel/debug/dynamic_debug/control
# echo function > /sys/kernel/debug/tracing/current_tracer
# echo free_pcppages_bulk > /sys/kernel/debug/tracing/set_ftrace_filter
# echo drain_all_pages>> /sys/kernel/debug/tracing/set_ftrace_filter
sysctl vm.defrag_ignore_drain=0
sysctl vm/defrag_split_thp=1
