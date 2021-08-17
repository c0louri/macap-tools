#!/usr/bin/python3

import sys
import os
import matplotlib.pyplot as plt
import copy
import pandas as pd
import numpy as np

# starting string of folder name: <bench>_[frag|fresh]_[cap|ranger|both]_[all|mark]_
benchmarks = []
frag_opts = []
defrag_opts = []
marked_opts = []
alloc_fails = []
iterations = []
frag_cases = []

cases = [] # both all 500, Ranger , Cap, etc

#case : "<defrag_option, marked_option, all_fails"
col_names = ["Case", "#vmas", "#subvmas", "4k cap fails",
            "2M cap fails", "Ranger successes","Ranger failures", "#32 ranges coverage",
            "#64 ranges coverage", "#128 ranges coverage", "#ranges for 99% cov"]

runs_dict = {} # key : (<run_case>, <bench_name>, <frag case>) <--- tuple of strings

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
    # 2nd val: frag | fresh (frag_opts)
    # 3rd val: cap | ranger | both (defrag_opts)
    # 4th val: all | mark (which pages will try to migrate)
    # 5th val: #alloc_2mb_fails
    # 6th val: name of runs (case) or maybe not existing
    # 7th val: percentage of subhuge unmappings (fragmenter) -
    #           percentage of remaining allocated memory (fragmenter)
    # save name of benchmark
    parts = filename.split('_')
    #benchmark:
    if parts[0] not in benchmarks:
        benchmarks.append(parts[0])
    #fragment cases:
    if parts[1] not in frag_opts:
        frag_opts.append(parts[1])
    #defrag cases:
    if parts[2] not in defrag_opts:
        defrag_opts.append(parts[2])
    #use or no of marking:
    if parts[3] not in marked_opts:
        marked_opts.append(parts[3])
    #alloc fails:
    if parts[4] not in alloc_fails:
        alloc_fails.append(parts[4])
    #run case:
    if parts[5] not in iterations:
        iterations.append(parts[5])
    #frag cases:
    if parts[-1] not in frag_cases:
        frag_cases.append(parts[-1])
    return parts

def read_cov_stats(filename): # finished
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

def read_counters_stats(filename): # finished
    f_counters = open(filename, 'r')
    lines = f_counters.readlines();
    def_succ = int(lines[0].split()[5])
    def_fails = int(lines[1].split()[5])
    def_succ_gb = def_succ * 4 / (1024*1024)
    def_fails_gb = def_fails * 4 / (1024*1024)
    cap_2m_fails = int(lines[3].split()[3])
    cap_4k_fails = int(lines[2].split()[3])
    def_succ = str(def_succ) + " ({:.3f}GB)".format(def_succ_gb)
    def_fails = str(def_fails) + " ({:.3f}GB)".format(def_fails_gb)
    return [cap_4k_fails, cap_2m_fails, def_succ, def_fails]

def get_table(d, iteration, bench, frag_case):
    table = []
    for key, val in runs_dict.items():
        if iteration == key[5] and bench == key[0] and frag_case == key[-1]:
            defrag_case = key[2]
            marked = key[3]
            alloc_fails = key[4]
            if defrag_case == "cap":
                case = "CaPaging"+alloc_fails
            elif defrag_case == "ranger":
                case = "TRanger"
            elif defrag_case == "both":
                case = "Both" + " (" + marked + ") " + alloc_fails
            else:
                print("Unkwown defrag case!!")
                exit(-1)
            if case not in cases:
                cases.append(case)
            table.append([case] + val)
    return table

def read_all_stats(path): #finished
    runs_dict = {}
    for root, dirs, files in os.walk(path):
        if not dir_contains_results(files):
            continue
        # find benchmark characteristics
        folder_name = root.split('/')[-1]
        print(folder_name)
        attrs = get_bench_run_characteristics(folder_name)
        # read counter stats
        cnt_file_name = root+"/"+"counters_stats.txt"
        cnt_stats = read_counters_stats(cnt_file_name)
        # get stats from stats (from pagemap) file
        f_stats_name = get_stats_file_name(files)
        cov_stats_name = root+"/"+f_stats_name
        cov_stats = read_cov_stats(cov_stats_name)
        table_row = cov_stats[0:2] + cnt_stats + cov_stats[2:]
        runs_dict[tuple(attrs)] = table_row
    return runs_dict

def print_table(table):
    for row in table:
        for val in row[:-1]:
            print(val, end=', ')
        print(row[-1])
    # pd.set_option('display.max_columns', None)
    # df = pd.DataFrame(table, columns=col_names)
    # df = df.set_index(col_names[0])
    # print(df)

# returns dictionary:
#       { <fragcase> : { <benchmark> : {<iter>:table} }
def print_all_tables(runs_dict, to_print=False):
    tables = {}
    # 1st col of table is runcase
    for frag_case in frag_cases:
        bench_dict = {}
        for bench in benchmarks:
            iter_tables = {}
            for iteration in iterations:
                table = get_table(runs_dict, iteration, frag_case, bench)
                if to_print:
                    print("{} {} {}".format(iteration, frag_case, bench))
                    print_table(table)
                iter_tables[iteration] = table
            bench_dict[bench] = iter_tables
        tables[frag_case] = bench_dict
    return tables

#####
# FUNCTIONS for printing plots:

def print_all_plots(tables):
    for key, iter_tables in tables.items():
        frag_case, benchmark = key[0], key[1]
        print_plots(benchmark, frag_case, iter_tables)

# creates:
# { (stat_type, fragcase) : { run_case : [(benchmark, mean value)] } }
# parameter tables:  { <fragcase> : { <benchmark> : {<iter>:table} }
def print_plots(tables):
    # tables: all runs for specific run_case and frag_case
    final_dict = {}

    for col_idx in range(-4, 0): # index of the showing collumn
        # -4 -> 32 cov, -3 -> 64 cov, -2 -> 128 cov, -1 -> 99% perc
        for frag_case, bench_tables in tables.items():

            runcases_dict = {}
            for bench, iter_tables in bench_tables.items():
                bench_case_vals = {} # values of all iterations of all cases in specific benchmark
                for iteration, run_stats in iter_tables.items():
                    run_case = run_stats[0]
                    stats_val = run_stats[col_idx]
                    # update keys
                    if run_case not in bench_case_vals.keys():
                        bench_case_vals[run_case] = []
                    else:
                        bench_case_vals[run_case].append(stats_val)
                # calculate mean value in runcase_vals dict
                for case, vals in bench_case_vals.items():
                    # bench_case_vals[case] = sum(vals) / len(vals)
                    # geomean:
                    bench_case_vals[case] = np.prod(vals) ** (1 / len(vals))
                for case, mean_val in bench_case_vals.items():
                    runcases_dict[case].append((bench, mean_val))
            final_dict[(col_names[col_idx], frag_case)] = runcases_dict
    # print all plots
    for key, runcase_dict in final_dict.items():
        stat, frag_case = key[0], key[1]

        fig, ax = plt.subplots()
        for runcase, bench_and_val in runcase_dict.items():
            # benchmarks:
            x = [tup[0] for tup in bench_and_val]
            # values:
            y = [tup[1] for tup in bench_and_val]
            ax.plot(x, y, marker='o', label=runcase)
        ax.legend(xlabel='% Memory Footprint', title=stat + " ({})".format(frag_case))
        ax.grid(axis='y')
        plt.show()


####
# main()
def main():
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
        runcase = sys.argv[2]
        bench = sys.argv[3]
        frag = sys.argv[4]
        table = get_table(runs_dict, runcase, bench, frag)
        print_table(table)
    else:
        tables = print_all_tables(runs_dict, True)
        print_all_plots(tables)


if __name__ == "__main__":
    main()