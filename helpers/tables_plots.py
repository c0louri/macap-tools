#!/usr/bin/python3

import sys
import os
#import matplotlib
import copy

# benchmarks = ["liblinear", "XSBench", "micro"]
# defrag_opts = ["nodef", "mark", "all"]
# frag_opts = ["fresh", "frag"]
# alloc_fails = [0, 1, 2, 4, 10, 20, 40, 128]

benchmarks = []
defrag_opts = []
frag_opts = []
alloc_fails = []

col_names = ["ingored_alloc_fails", "#vmas", "#subvmas", "4k cap fails",
			 "2M cap fails", "Ranger successes","Ranger failures", "#32 ranges coverage",
			 "#64 ranges coverage", "#128 ranges coverage", "#ranges for 99% cov"]

runs_dict = {}

def num(s):
	try:
		return int(s)
	except ValueError:
		return float(s)

def dir_contains_results(files_list):
	for file_name in files_list:
		if "_stats.txt" in file_name:
			return True
	return False

def get_stats_file_name(files_list):
	for filename in files_list:
		if ("stats.txt" in filename) and ("counters" not in filename):
			return filename
	return None

def get_bench_run_characteristics(filename):
	# 1st val: name of benchmark
	# 2nd val: nodef | mark | all (mark: defrag only pages marked as misplaced)
	# 3rd val: frag | fresh
	# 4th val: #alloc_2mb_fails
	attrs = []
	# save name of benchmark
	bench_name = filename.split('_')[0]
	attrs.append(bench_name)
	if bench_name not in benchmarks:
		benchmarks.append(bench_name)
	# type of defrag
	if "nodef" in filename:
		attrs.append("nodef")
		if "nodef" not in defrag_opts:
			defrag_opts.append("nodef")
	else:
		if "mark" in filename:
			attrs.append("mark")
			if "mark" not in defrag_opts:
				defrag_opts.append("mark")
		else:
			attrs.append("all")
			if "all" not in defrag_opts:
				defrag_opts.append("all")
	# case of fragmentation
	if "frag" in filename:
		attrs.append("frag")
		if "frag" not in frag_opts:
			frag_opts.append("frag")
	else:
		# it was a fresh run
		attrs.append("fresh")
		if "fresh" not in frag_opts:
			frag_opts.append("fresh")
	# find #alloc_fails
	num_alloc_fails = int(filename.split('_')[-2])
	attrs.append(num_alloc_fails)
	if num_alloc_fails not in alloc_fails:
		alloc_fails.append(num_alloc_fails)
		alloc_fails.sort()
	return attrs


def read_stats(filename):
	print("reading ",filename)
	f_stats = open(filename, 'r')
	lines = f_stats.readlines()
	i = 0
	stats_list = []
	# save stats from every stats collecting iter
	while i < len(lines) - 1:
		if "PRE_DEFRAG" in lines[i] or "POST_DEFRAG" in lines[i]:
			if not lines[i+1].startswith('Offsets_stats:'):
				break # some unfinished stats collecting due to benchmarks exiting
			offset_stats = lines[i+1].split(':')[1].strip().replace(' ', '').split(',')
			offset_stats = [int(val) for val in offset_stats]
			cov_stats = [num(token) for token in lines[i+2].strip().replace(' ', '').split(',')]
			stats_list.append([offset_stats, cov_stats])
			i += 2
			continue
		i += 1
	# find iter with the most allocated pages and from those the last one
	stats_pos = -1
	max_total_pages = -1
	i = len(stats_list)-1
	while i >= 0:
		total_pages = stats_list[i][0][0]
		if total_pages > max_total_pages:
			max_total_pages = total_pages
			stats_pos = i
		i -= 1
	offset_stats, cov_stats = stats_list[stats_pos][0], stats_list[stats_pos][1]
	return cov_stats

def read_counters_stats(filename):
	f_counters = open(filename, 'r')
	lines = f_counters.readlines();
	def_succ = int(lines[0].split()[5])
	def_fails = int(lines[1].split()[5])
	cap_2m_fails = int(lines[3].split()[3])
	cap_4k_fails = int(lines[2].split()[3])
	return [cap_4k_fails, cap_2m_fails, def_succ, def_fails]

def get_table(d, bench, defrag, frag):
	table = []
	nodef_row = ["nodef_0"]+d[(bench, "nodef", frag, 0)]
	table.append(nodef_row)
	for alloc_val in alloc_fails:
		if (bench, defrag, frag, alloc_val) not in d.keys():
			continue
		table.append([alloc_val]+d[(bench, defrag, frag, alloc_val)])
	return table

def read_all_stats(path):
	runs_dict = {}
	for root, dirs, files in os.walk(path):
		if not dir_contains_results(files):
			continue
		filename = root+"/"+"counters_stats.txt"
		cnt_stats = read_counters_stats(filename)
		f_stats_name = get_stats_file_name(files)
		# find benchmark characteristics
		attrs = get_bench_run_characteristics(f_stats_name)
		# get stats from stats file
		filename = root+"/"+f_stats_name
		cov_stats = read_stats(filename)
		table_row = cov_stats[0:2] + cnt_stats + cov_stats[2:]
		runs_dict[tuple(attrs)] = table_row
	return runs_dict

def print_table(table):
	for row in table:
		for val in row[:-1]:
			print(val, end=', ')
		print(row[-1])

def print_all_tables(runs_dict, to_print=False):
	tables = []
	for bench in benchmarks:
		for frag in frag_opts:
			for defrag in defrag_opts:
				if defrag == "nodef":
					continue
				table = get_table(runs_dict, bench, defrag, frag)
				if to_print:
					print("{} {} {}".format(bench, frag, defrag))
					print_table(table)
				tables.append(table)
	return tables

# main part of script

if len(sys.argv) > 1:
	path = sys.argv[1]
else:
	path = "."

runs_dict = read_all_stats(path)
print(benchmarks)
print(defrag_opts)
print(frag_opts)
print(col_names)
if len(sys.argv) > 2:
    bench = sys.argv[2]
    defrag = sys.argv[3]
    frag = sys.argv[4]
    table = get_table(runs_dict, bench, defrag, frag)
    print_table(table)
else:
    tables = print_all_tables(runs_dict, True)
