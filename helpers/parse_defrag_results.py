#!/usr/bin/python3

import sys
import re
import copy

regex =	"\[0x([\da-f]+), 0x([\da-f]+)\):(\d+) \[alig:(\d+), migrated:(\d+), src: not:(\d+), src_thp_dst_not:(\d+), src_pte_thp:(\d+) \
dst: out_bound:(\d+), dst_thp_src_not:(\d+), dst_pte_thp:(\d+), isolate_free:(\d+), migrate_free:(\d+), \
anon:(\d+), file:(\d+), non\-lru:(\d+), non\-moveable:(\d+)\], offset: ([\-+]?\d+), vma: 0x([\da-f]+)"

stats_type_enum = {
	0 : "aligned",
	1 : "migrated",
	2 : "src_not_present",
	3 : "src_thp_dst_not_failed",
	4 : "src_pte_thp_failed",
	5 : "dst_out_bounds_failed",
	6 : "dst_thp_src_not_failed",
	7 : "dst_pte_thp_failed",
	8 : "dst_isolate_free_failed",
	9 : "dst_migrate_free_failed",
	10 : "dst_anon_failed",
	11 : "dst_file_failed",
	12 : "dst_non-lru_failed",
	13 : "dst_non-moveable_failed"
}

total_stats = [0 for _ in stats_type_enum.keys()]

def parse_vma_line(line, hex_to_int=False):
	tokens = line.split()
	tokens = [tok.strip(',') for tok in tokens]
	if hex_to_int:
		vma_start = int(tokens[2], 16)
		vma_end = int(tokens[4], 16)
	else:
		vma_start = tokens[2]
		vma_end = tokens[4]
	return vma_start, vma_end

def parse_stats_line(line):
	values = re.findall(regex, line)[0]
	chunk_start, chunk_end, size = values[0:3]
	stats_vals = [int(val) for val in values[3:17]]
	offset, vma = int(values[-2]), values[-1]
	return (chunk_start, chunk_end), stats_vals, (offset, vma)

def pretty_print_defrag_iter(total, vmas_stats):
	print(total)
	for bounds, stats in vmas_stats.items():
		print('0x{} - 0x{} : {}'.format(bounds[0], bounds[1], stats))

filename = sys.argv[1] # filename of defrag results

# read lines from file
lines = []
with open(filename, 'r') as src:
	lines = src.readlines()

# parse each line and read values
defrags = {}

for line in lines:
	line = line.rstrip()
	if line.endswith(':'): # new iteration of defragging
		defrag_iter = int(line.rstrip(':'))
		defrags[defrag_iter] = [copy.deepcopy(total_stats), {}]
		stats_per_defrag = defrags[defrag_iter][0]
		vma_stats = defrags[defrag_iter][1]
	elif line.startswith('vma'): # info for a new vma
		vma_st, vma_end = parse_vma_line(line)
		vma_stats[(vma_st, vma_end)] = [0 for _ in stats_type_enum.keys()]
		stats_per_vma = vma_stats[(vma_st, vma_end)]
	elif line.startswith('['): # stats line
		bounds, stats, off_and_vma = parse_stats_line(line)
		for i in range(len(stats_type_enum)):
			# update stats_per_vma
			stats_per_vma[i] += stats[i]
			# update stats_per_defrag
			stats_per_defrag[i] += stats[i]

print(stats_type_enum)

for iter, val in defrags.items():
	print("Defrag iter {}:".format(iter))
	pretty_print_defrag_iter(val[0], val[1])



