#!/usr/bin/python3

import sys
import re
import copy


regex_mapcount = "0x([\da-f]+), scan_p: ([\da-f]+), dst_p: ([\da-f]+), \
cnt: ([-\d]+), mapcnt: ([-\d]+), mapping: ([\d\sa-z()]*), idx: ([\d\sa-z()]*), flags: ([\d\sa-z()|]*), ([a-z]*), order: (\d+), \
head: ([\da-f]+), flags: ([\d\sa-z()|]*)"

regex_neg_mapcount = "0x([\da-f]+), scan_p: ([\da-f]+), dst_p: ([\da-f]+), \
cnt: ([\-\d]+), mapcnt: ([\-\d]+), mapping: ([\d\sa-z()]*), idx: ([\d\sa-z()]*), flags: ([\d\sa-z()|]*), ([a-z]*), order: (\d+), \
bud:([01]),bal:([01]),kmemcg:([01]),table:([01]),ca_pcp:([01]),ca_res:([01])"


# all table pages also have table page flag set

# all fail cases which result to ignoring vaddr and proceeding to the next one
# lines strt with f::
fail_tokens = [
    "pte-mapped src",
    "not-managed",
    "out-of-bounds",
    "free_fail-split",
    "free_trans",
    "free_nobuddy",
    "free_zero-hp",
    "free_other",
    "free_migrate",
    # all cases below are accompanied by dest page info
    "pte-mapped dst",
    "exch_can_migrate",
    "exch_split", # except this
    "exch_busy",
    "exch_anon",
    "exch_file",
    "exch_nonlru",
    "exch_unmovable"
]

other_tokens = [
    "_succ_split-src-hp",
    "_succ_split-dst-hp",
    "_succ_split-dst-pte-thp"
]

stats_defrag = {
    "pte-mapped src" : 0,
    "not-managed" : 0,
    "out-of-bounds" : 0,
    "free_fail-split" : 0,
    "free_trans" : 0,
    "free_nobuddy" : 0,
    "free_zero-hp" : 0,
    "free_other" : 0,
    "free_migrate" : 0,
    # all cases below are accompanied by dest page info
    "pte-mapped dst" : 0,
    "exch_can_migrate" : 0,
    "exch_split": 0, # except this
    "exch_busy" : 0,
    "exch_anon": 0,
    "exch_file" : 0,
    "exch_nonlru" : 0,
    "exch_unmovable" : 0
}

stats_page_defrag = {
    "occupied/other" : 0,
    "slab" : 0,
    "buddy" : 0,
    "balloon" : 0,
    "kmemcg" : 0,
    "table" : 0,
    "ca_pcp" : 0,
    "ca_res" : 0
}

# unmapped_page_types = {
#     0: "buddy",
#     1: "balloon",
#     2: "kmemcg",
#     3: "table",
#     4: "ca_pcp",
#     5: "ca_res",
# }

def parse_f_line(line):
    tokens = line.split("::")[1].strip().split(',')
    tokens = [tok.strip() for tok in tokens]
    vaddr = tokens[0]
    scan_pfn = tokens[1]
    dest_pfn = tokens[2]
    size = int(tokens[3])
    fail_type = tokens[4].strip(' ')
    return vaddr, scan_pfn, dest_pfn, size, fail_type

## def main():
filename = sys.argv[1] # filename of defrag fail results

# read lines from file
lines = []
with open(filename, 'r') as src:
    lines = src.readlines()

# parse each line and read values
defrags = {}
#

for line in lines:
    line = line.rstrip()
    if line.endswith(':'):
        # new iteration of defragging
        print(line)
        defrag_iter = int(line.rstrip(':'))
        defrags[defrag_iter] = [[], {}]  # 1st is fails, 2nd is dest pages of fails
        fails = defrags[defrag_iter][0]
        page_info = defrags[defrag_iter][1]
    elif line.startswith('f::'):
        #line is trash or describes a failure
        addr, scan_pfn, dst_pfn, size, fail_case = parse_f_line(line)
        fails.append((addr, scan_pfn, dst_pfn, size, fail_case))
            # print("{} : curr_pfn: {}, dest_pfn: {}, dest_type: {}, (curr_order: {})".format(addr, scan_pfn, dst_pfn, page_type, order))
    elif line.startswith('dst::'):
        pfn = line.strip('dst:: ').split(',')[0]
        page_type = ""
        if "slab" in line: # destination page is slab page
            page_type += "slab"
        elif "bud" in line: # dest page is unmapped
            page_type = ""
            if "bud:1" in line:
                page_type += "buddy|"
            if "bal:1" in line:
                page_type += "balloon|"
            if "kmemcg:1"in line:
                page_type += "kmemcg|"
            if "table:1" in line:
                page_type += "table|"
            if "ca_pcp:1" in line:
                page_type += "ca_pcp|"
            if "ca_res:1" in line:
                page_type += "ca_res|"
            if len(page_type) > 0:
                page_type = page_type[:-1] # remove last '|'
        else:
            page_type = ""
        page_info[pfn] = page_type

for it, v in defrags.items():
    fails = v[0]
    page_info = v[1]
    total_stats = copy.deepcopy(stats_defrag)
    total_page_f_stats = copy.deepcopy(stats_page_defrag)
    with open("def_iter_{}.txt".format(it), 'w') as f_w:
        for row in fails:
            dest_pfn = row[2]
            if dest_pfn in page_info.keys():
                page_type = page_info[dest_pfn]
            else:
                page_type = ""
            f_w.write("{}, scan_pfn: {}, size: {}, dest_pfn: {}, {}, {}\n".\
                      format(row[0], row[1], row[3], row[2], page_type, row[4]))
            fail_type = row[4]
            # update total fail stats
            total_stats[fail_type] += int(row[3])
            # update page type fails
            if page_type == "":
                total_page_f_stats["occupied/other"] += size
            else:
                for pt in page_type.split('|'):
                    total_page_f_stats[pt] += size
        f_w.write("\nTotal stats:\n {}\n {}\n".format(total_stats, total_page_f_stats))


    # calculate some total stats (cumulative)
    # for k, val in defrags.items():
    #     compact_stats = copy.deepcopy(stats_defrag)
    #     fails = val[0]
    #     for (addr, scan_pfn, dst_pfn, page_type, order) in fails:
    #         type_tokens = page_type.split('|')
    #         for tok in type_tokens:
    #             compact_stats[tok] += (1 << order)
    #     defrags[k][1] = compact_stats
    #
    # for k, val in defrags.items():
    #     print("Defrag iter {}:".format(k))
    #     print("  #total_fails : ", len(val[0]))
    #     print("  #fails per type: ", val[1])
    #     # for ptype, cnt in val[1].items():
    #     #     print("    {} : {}".format(ptype, cnt))