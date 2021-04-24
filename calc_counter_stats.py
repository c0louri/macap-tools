#!/usr/bin/python3

""" template of counters_*.out:
memdefrag_defrag 0
memdefrag_scan 0
memdefrag_dest_free_pages 0
memdefrag_dest_anon_pages 0
memdefrag_dest_file_pages 0
memdefrag_dest_free_pages_failed 0
memdefrag_dest_anon_pages_failed 0
memdefrag_dest_file_pages_failed 0
memdefrag_dest_nonlru_pages_failed 0
memdefrag_dest_unmovable_pages_failed 0
memdefrag_src_compound_pages_failed 0
memdefrag_dst_compound_pages_failed 0
memdefrag_src_split_hugepages 0
memdefrag_dst_split_hugepages 0
Capaging failure 4K (0-order) counters:
INVALID_PFN:	0
EXCEED_MEMORY:	0
GUARD_PAGE:	0
OCCUPIED:	0
BUDDY_OCCUPIED:	0
WRONG_ALIGNMENT:	0
EXCEED_ZONE:	0
NOTHING_FOUND:	0
BUDDY_GUARD:	0
SUBBLOCK:	0
PAGECACHE:	0
NUMA:	0
Capaging failure 2M (9-order) counters:
INVALID_PFN:	0
EXCEED_MEMORY:	0
GUARD_PAGE:	0
OCCUPIED:	0
BUDDY_OCCUPIED:	0
WRONG_ALIGNMENT:	0
EXCEED_ZONE:	0
NOTHING_FOUND:	0
BUDDY_GUARD:	0
SUBBLOCK:	0
PAGECACHE:	0
NUMA:	0
"""

def parse_counter_file(file_name):
    f = open(file_name, 'r')
    lines = f.readlines()
    lines = [line.rstrip('\n') for line in lines]
    defrag_lines = lines[0 : 14]
    cap_4k_fails_lines = lines[15 : 28]
    cap_2m_fails_lines = lines[29 : 42]  
    # defrag
    defrag_vals = [int(line.split()[1]) for line in defrag_lines]
    dst_free_tries, dst_anon_tries, dst_file_tries = defrag_vals[2:5]
    dst_free_fails, dst_anon_fails, dst_file_fails = defrag_vals[5:8]
    dst_nonlru_fails, dst_unmov_fails = defrag_vals[8:10]
    src_comp_fails, dst_comp_fails = defrag_vals[10:12]    

    defrag_success = (dst_free_tries+dst_anon_tries+dst_free_tries) - \
                     (dst_free_fails+dst_anon_fails+dst_file_fails)
    defrag_fails = dst_free_fails + dst_anon_fails + dst_file_fails + \
                   dst_nonlru_fails + dst_unmov_fails + \
                   src_comp_fails + dst_comp_fails

    # calculate total 4k failures
    total_cap_4k_fails = sum([int(line.split()[1]) for line in cap_4k_fails_lines])
    # calculate total 2m failures
    total_cap_2m_fails = sum([int(line.split()[1]) for line in cap_2m_fails_lines])
    
    return defrag_success, defrag_fails, total_cap_4k_fails, total_cap_2m_fails     
