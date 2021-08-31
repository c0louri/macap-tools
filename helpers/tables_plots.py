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
cov_col_names = ["#VMAs", "#SubVMAs", "#32 Ranges Coverage",
                "#64 Ranges Coverage", "#128 Ranges Coverage", "# Ranges for 99% Coverage"]

cnt_col_names = ["4k CaPaging Successes", "2M CaPaging Successes",
                 "4k CAPaging Fails", "2M CAPaging Fails",
                 "Ranger Successes", "Ranger Fails"]

time_col_names = ["Real time(ms)", "User time(ms)", "System time(ms)", "vCPU time(ms)"]

col_names = ["Case"] + cov_col_names + cnt_col_names + time_col_names

markers = ["o", "X", "+","v", "^", "."]

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

def get_cycles_file_name(files_list):
    for filename in files_list:
        if "cycles" in filename:
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
        if parts[2] != "cap" and parts[2] != "ranger":
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
    # print("reading ",filename)
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

# returns a list [real_time, user_time, sys_time, vcpu_time]
# time is in milliseconds
def read_time_stats(filename):
    f_cycles = open(filename, 'r')
    lines = f_cycles.readlines()
    for line in lines:
        if line.startswith('real time'):
            tokens = [part.strip(',') for part in line.strip().split(' ')]
            real_time = int(tokens[2])
            user_time = int(tokens[5])
            sys_time = int(tokens[8])
            vcpu_time = int(tokens[12])
        elif line.startswith('min_flt'):
            tokens = [part.strip(',') for part in line.strip().split(' ')]
            min_faults = int(tokens[1])
            major_faults = int(tokens[3])
            maxrss_kb = int(tokens[5])
    return [real_time, user_time, sys_time, vcpu_time]

def read_counters_stats(filename):
    f_counters = open(filename, 'r')
    lines = f_counters.readlines()
    def_succ = int(lines[0].split()[5])
    def_fails = int(lines[1].split()[5])
    # def_succ_gb = def_succ * 4 / (1024*1024)
    # def_fails_gb = def_fails * 4 / (1024*1024)
    cap_2m_fails = int(lines[3].split()[3])
    cap_4k_fails = int(lines[2].split()[3])
    cap_2m_succ = int(lines[5].split()[3])
    cap_4k_succ = int(lines[4].split()[3])
    # def_succ = str(def_succ) + " ({:.3f}GB)".format(def_succ_gb)
    # def_fails = str(def_fails) + " ({:.3f}GB)".format(def_fails_gb)
    return [cap_4k_succ, cap_2m_succ, cap_4k_fails, cap_2m_fails, def_succ, def_fails]

def get_cov_cnt_time_table(runs_dict, iteration, bench, frag_case):
    # cov_table = []
    # cnt_table = []
    # time_table = []
    table = []
    for key, val in runs_dict.items():
        if iteration == key[5] and bench == key[0] and frag_case == key[-1]:
            defrag_case = key[2]
            marked = key[3]
            alloc_fails = key[4]
            if defrag_case == "cap":
                case = "CaPaging"
            elif defrag_case == "ranger":
                case = "TRanger"
            elif defrag_case == "both":
                if len(marked_opts) == 1:
                    case = "MACAP" + " (" + alloc_fails + ")"
                else:
                    case = "Both" + " (" + marked + ") " + alloc_fails
            else:
                print("Unkwown defrag case!!")
                exit(-1)
            if case not in cases:
                cases.append(case)
            table.append([case] + val)
    return table

# column names: col_names
# [<cov-stats>, <cnt_stats>, <time_stats>]
# if no coverage stats exist (in runs for counting time)
def read_all_stats(path): #finished
    runs_dict = {}
    for root, dirs, files in os.walk(path):
        if not dir_contains_results(files):
            continue
        # find benchmark characteristics
        folder_name = root.split('/')[-1]
        # print(folder_name)
        attrs = get_bench_run_characteristics(folder_name)
        # read counter stats
        cnt_file_name = root+"/"+"counters_stats.txt"
        cnt_stats = read_counters_stats(cnt_file_name)
        # get stats from stats (from pagemap) file
        stats_file_name = get_stats_file_name(files)
        if stats_file_name:
            cov_stats_name = root + "/" + stats_file_name
            cov_stats = read_cov_stats(cov_stats_name)
        else:
            cov_stats = [0] * len(cov_col_names)
        # get time stats and max memory resident use
        f_cycles_name = root + "/" + get_cycles_file_name(files)
        time_stats = read_time_stats(f_cycles_name)
        runs_dict[tuple(attrs)] = cov_stats + cnt_stats + time_stats
    return runs_dict

def print_table(table):
    for row in table:
        for val in row[:-1]:
            print(val, end=', ')
        print(row[-1])
    # pd.set_option('display.max_columns', None)
    # df = pd.DataFrame(table, columns=cov_col_names)
    # df = df.set_index(cov_col_names[0])
    # print(df)

# returns dictionary:
#       { <fragcase> : { <benchmark> : { <runcase> : <mean values>} }
def get_mean_values(runs_dict, to_print=False):
    tables = {}
    # 1st col of table is runcase
    for frag_case in frag_cases:
        bench_dict = {}
        for bench in benchmarks:
            iter_tables = {}
            for iteration in iterations:
                table = get_cov_cnt_time_table(runs_dict, iteration, bench, frag_case)
                if to_print:
                    print("{} {} {}".format(iteration, frag_case, bench))
                    print_table(table)
                    print()
                # collect in one all iterations of a runcase
                iter_tables[iteration] = table
            runcases = {} # will contain foreach case all stats from all available iterations
            # concentrate together values from iterations from the same runcase
            for iteration, table in iter_tables.items():
                # ger runcases for keys in dicr
                for row in table:
                    if row[0] not in runcases.keys():
                        runcases[row[0]] = [row[1:]]
                    else:
                        runcases[row[0]].append(row[1:])
            for runcase, iter_vals in runcases.items():
                print(bench, " ", frag_case, " ", runcase)
                for row in iter_vals:
                    print(row[-4:])
                stats_num = len(iter_vals[0])
                cov_stats_num = len(cov_col_names)
                cnt_stats_num = len(cnt_col_names)
                final_row = [0] * stats_num
                # calc for each stat the mean values
                # IGNORE time stats (different approach for them)
                for i in range(0, cov_stats_num + cnt_stats_num):
                    vals = [row[i] for row in iter_vals]
                    prod = 1
                    for val in vals:
                        prod *= val
                    if type(iter_vals[0][i]) is int:
                        final_row[i] = int(prod ** (1 / len(vals)))
                    else:
                        final_row[i] = round(prod ** (1 / len(vals)), 3)
                # next for time stats:
                # find iteration which is closest to the median of real time

                # # real_times = [row[-4] for row in iter_vals]
                # # mean_real_time = sum(real_times) / len(real_times)
                # # closest_iter = 0
                # # best_min_dist = abs(real_times[0] - mean_real_time)
                # # for i, vcpu_time in enumerate(real_times[1:]):
                # #     dist = abs(vcpu_time - mean_real_time)
                # #     if dist < best_min_dist:
                # #         best_min_dist = dist
                # #         closest_iter = i
                real_times = [(i, row[-4]) for i, row in enumerate(iter_vals)]
                real_times.sort(key=lambda x : x[1])
                middle = int(len(real_times) / 2)
                closest_iter = real_times[middle][0]
                print("Chosen: ", closest_iter)
                # save time stats of the closest iteration
                time_stats_st_index = cov_stats_num + cnt_stats_num
                final_row[time_stats_st_index:] =  iter_vals[closest_iter][time_stats_st_index:]
                runcases[runcase] = final_row
            bench_dict[bench] = runcases
        tables[frag_case] = bench_dict
    return tables

#####
# FUNCTIONS for printing plots:


def all_runs_in_list(tables):
    all_runs = []
    for fragcase, benchs_dict in tables.items():
        for bench, runcases_dict in benchs_dict.items():
            for runcase, values in runcases_dict.items():
                all_runs.append([fragcase, bench, runcase] + values)
    return all_runs

# print_plots()
# creates:
# fresh: { (stat_type) : { run_case : [(benchmark, mean value)] } }
# frag: { <stat_type> : { <benchmark> : { <runcase> : [frag_case, mean_value] } }
# parameter tables:  { <fragcase> : { <benchmark> : {<runcase>: mean values} }
def print_cov_plots(tables, frag=True):
    # tables: all runs for specific run_case and frag_case
    all_runs = all_runs_in_list(tables)
    if frag:
        df = pd.DataFrame(all_runs, columns=["Frag case", "Benchmark", "Runcase"] + col_names[1:])
        # print(df)
        # dictionary key : statname, value dataframe
        # PRINT coverage stats plots (4 of them)
        if df['#VMAs'].values[0] == 0:
            # no coverage pagecollection
            return
        for col_index in range(2, 6):
            stat_name = cov_col_names[col_index]
            cols_to_keep = ["Frag case", "Benchmark", "Runcase", stat_name]
            new_df = df[cols_to_keep]
            bench_group_df = new_df.groupby("Benchmark")
            for bench, bench_group in bench_group_df:
                # print plot
                fig, ax = plt.subplots()
                i = 0
                print()
                print(stat_name+":")
                print(bench_group.sort_values(by='Frag case'))
                for runcase, runcase_group in bench_group.groupby("Runcase"):
                    runcase_group.sort_values(by='Frag case', inplace=True)
                    # print(runcase_group)
                    frag_cases = list(runcase_group['Frag case'])
                    values = list(runcase_group[stat_name])
                    ax.plot(frag_cases, values, marker=markers[i], label=runcase, linestyle='None')
                    i += 1
                if "Ranges Coverage" in stat_name:
                    ax.set_ylabel('% Memory Footprint')
                    ax.set_ylim([0, 105])
                else:
                    ax.set_ylabel('# Ranges')
                ax.spines['right'].set_visible(False)
                ax.spines['top'].set_visible(False)
                ax.legend(bbox_to_anchor=(0,1.02,1,0.2), loc='lower left', fontsize='small',
                ncol=i, mode="expand", borderaxespad=0, title=bench + " - " + stat_name)
                ax.grid(axis='y')
                filename = ("cov " + bench + " " + stat_name).replace(" ", "_")
                plt.savefig("plots/"+filename)
                plt.show()
    else:
        # fresh case
        pass

def print_allocs_plots(tables):
    all_runs = all_runs_in_list(tables)
    df = pd.DataFrame(all_runs, columns=["Frag case", "Benchmark", "Runcase"] + col_names[1:])
    # print time bars and speedup
    cols_to_keep = ["Frag case", "Benchmark", "Runcase"] + cnt_col_names[:2]
    new_df = df[cols_to_keep]
    bench_group_df = new_df.groupby("Benchmark")
    # width of each vertical bar
    bar_width = 0.4
    # for x axis
    X_axis_labels = cnt_col_names[:2]
    X_axis = np.arange(len(X_axis_labels)) * 3
    X_st = X_axis - (bar_width/2)
    for bench, bench_group in bench_group_df:
        for fragcase, frag_group in bench_group.groupby("Frag case"):
            # print plot
            fig, ax = plt.subplots()
            i = 0
            frag_group.sort_values(by='Runcase', inplace=True)
            for runcase, runcase_group in frag_group.groupby("Runcase"):
                if runcase == "TRanger":
                    continue
                values = list(runcase_group.values[0][3:])
                ax.bar(X_st + i*bar_width, values, width=bar_width,label=runcase)
                i += 1
            ax.set_xticks(X_axis)
            ax.set_xticklabels(X_axis_labels)
            # ax.set_yscale('log')
            ax.set_ylabel('#Allocations')
            ax.spines['right'].set_visible(False)
            ax.spines['top'].set_visible(False)
            ax.legend(bbox_to_anchor=(0,1.02,1,0.2), loc='lower left', fontsize='small',
                ncol=i, mode="expand", borderaxespad=0, title="CaP allocations: {} (fragmentation: {})".format(bench, fragcase))

            ax.grid(axis='y')
            filename = ("allocs " + bench + " " + fragcase).replace(" ", "_")
            plt.savefig("plots/"+filename)
            plt.show()

def print_migr_plots(tables):
    all_runs = all_runs_in_list(tables)
    df = pd.DataFrame(all_runs, columns=["Frag case", "Benchmark", "Runcase"] + col_names[1:])
    # print time bars and speedup
    cols_to_keep = ["Frag case", "Benchmark", "Runcase"] + cnt_col_names[4:]
    new_df = df[cols_to_keep]
    bench_group_df = new_df.groupby("Benchmark")
    # width of each vertical bar
    bar_width = 0.4
    # for x axis
    X_axis_labels = cnt_col_names[4:]
    X_axis = np.arange(len(X_axis_labels)) * 3
    X_st = X_axis - (bar_width / 2)
    for bench, bench_group in bench_group_df:
        for fragcase, frag_group in bench_group.groupby("Frag case"):
            # print plot
            fig, ax = plt.subplots()
            i = 0
            frag_group.sort_values(by='Runcase', inplace=True)
            for runcase, runcase_group in frag_group.groupby("Runcase"):
                if runcase == "CaPaging":
                    continue
                values = list(runcase_group.values[0][3:])
                ax.bar(X_st + i*bar_width, values, width=bar_width,label=runcase)
                i += 1
            ax.set_xticks(X_axis)
            ax.set_xticklabels(X_axis_labels)
            # ax.set_yscale('log')
            ax.set_ylabel('#Migrations')
            ax.spines['right'].set_visible(False)
            ax.spines['top'].set_visible(False)
            ax.legend(bbox_to_anchor=(0,1.02,1,0.2), loc='lower left', fontsize='small',
            ncol=i, mode="expand", borderaxespad=0, title="Migrations: {} (fragmentation: {})".format(bench, fragcase))

            ax.grid(axis='y')
            filename = ("migr " + bench + " " + fragcase).replace(" ", "_")
            plt.savefig("plots/"+filename)
            plt.show()

def print_time_plots(tables):
    all_runs = all_runs_in_list(tables)
    df = pd.DataFrame(all_runs, columns=["Frag case", "Benchmark", "Runcase"] + col_names[1:])
    # print time bars and speedup
    cols_to_keep = ["Frag case", "Benchmark", "Runcase"] + time_col_names
    new_df = df[cols_to_keep]
    bench_group_df = new_df.groupby("Benchmark")
    # width of each vertical bar
    bar_width = 0.4
    # for x axis
    X_axis_labels = time_col_names
    X_axis = np.arange(len(X_axis_labels)) * 2
    X_st = X_axis - bar_width
    for bench, bench_group in bench_group_df:
        for fragcase, frag_group in bench_group.groupby("Frag case"):
            # print plot
            fig, ax = plt.subplots()
            i = 0
            frag_group.sort_values(by='Runcase', inplace=True)
            for runcase, runcase_group in frag_group.groupby("Runcase"):
                values = list(runcase_group.values[0][3:])
                ax.bar(X_st + i*bar_width, values, width=bar_width,label=runcase)
                i += 1
            ax.set_xticks(X_axis)
            ax.set_xticklabels(X_axis_labels)
            ax.set_ylabel('Time(ms)')
            ax.spines['right'].set_visible(False)
            ax.spines['top'].set_visible(False)
            ax.legend(bbox_to_anchor=(0,1.02,1,0.2), loc='lower left', fontsize='small',
            ncol=i, mode="expand", borderaxespad=0, title="{} (fragmentation: {})".format(bench, fragcase))
            # if "ranges coverage" in stat:
            #     ax.legend(xlabel='% Memory Footprint', title=)
            # else:
            #     ax.legend(xlabel='# SubVMAs', title=stat + " ({})".format(frag_case))
            ax.grid(axis='y')
            filename = ("times " + bench + " " + fragcase).replace(" ", "_")
            plt.savefig("plots/"+filename)
            plt.show()


####
# main()
def main():
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = "."

    runs_dict = read_all_stats(path)
    # if len(sys.argv) == 3 and sys.sys.argv[2] == 'fresh':
    #     tables = get_mean_values_fresh(runs_dict, False)
    #     print_cov_plots(tables, frag=False)
    #     print_time_plots(tables)
    #     return

    tables = get_mean_values(runs_dict, False)
    # print_cov_plots(tables, frag=True)
    # print_allocs_plots(tables)
    # print_migr_plots(tables)
    # print_time_plots(tables)


if __name__ == "__main__":
    main()