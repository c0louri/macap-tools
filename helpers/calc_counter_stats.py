#!/usr/bin/python3
import sys

cap_4k_fails_start_line = 16
cap_2m_fails_start_line = 30
cap_4k_succ_start_line = 44
cap_2m_succ_start_line = 50
thp_collapse_start_line = 56

def parse_counter_file(file_name):
    f = open(file_name, 'r')
    lines = f.readlines()
    lines = [line.rstrip('\n') for line in lines]
    # save lines apart
    defrag_lines = lines[0 : cap_4k_fails_start_line-1]
    cap_4k_fails_lines = lines[cap_4k_fails_start_line : cap_2m_fails_start_line-1]
    cap_2m_fails_lines = lines[cap_2m_fails_start_line : cap_4k_succ_start_line-1]
    cap_4k_succ_lines = lines[cap_4k_succ_start_line : cap_2m_succ_start_line-1]
    cap_2m_succ_lines = lines[cap_2m_succ_start_line : thp_collapse_start_line-1]
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
    # calculate total 4k successes
    total_cap_4k_succ = sum([int(line.split()[1]) for line in cap_4k_succ_lines])
    # calculate total 2m successes
    total_cap_2m_succ = sum([int(line.split()[1]) for line in cap_2m_succ_lines])
    return defrag_success, defrag_fails, total_cap_4k_fails, total_cap_2m_fails, \
            total_cap_4k_succ, total_cap_2m_succ


def main():
    args = sys.argv
    if len(args) != 3:
        print("Wrong number of arguments!")
        exit()
    start_file = args[1]
    end_file = args[2]
    start_stats = parse_counter_file(start_file)
    end_stats = parse_counter_file(end_file)
    def_succ_diff = end_stats[0] - start_stats[0]
    def_fails_diff = end_stats[1] - start_stats[1]
    cap_4k_fails_diff = end_stats[2] - start_stats[2]
    cap_2m_fails_diff = end_stats[3] - start_stats[3]
    cap_4k_succ_diff = end_stats[4] - start_stats[4]
    cap_2m_succ_diff = end_stats[5] - start_stats[5]
    # convert to GB
    def_fails_diff_gb = def_fails_diff*4 / (1024*1024)
    def_succ_diff_gb = def_succ_diff*4 / (1024*1024)
    cap_4k_fails_diff_gb = cap_4k_fails_diff*4 / (1024*1024)
    cap_2m_fails_diff_gb = cap_2m_fails_diff*2 / (1024)
    cap_4k_succ_diff_gb = cap_4k_succ_diff*4 / (1024*1024)
    cap_2m_succ_diff_gb = cap_2m_succ_diff*2 / (1024)
    print("Defrag successes (in 4K pages): {} ({:.4f}GB)".format(def_succ_diff, def_succ_diff_gb))
    print("Defrag failures (in 4K pages): {} ({:.4f}GB)".format(def_fails_diff, def_fails_diff_gb))
    print("Cap 4k fails: {} ({:.4f}GB)".format(cap_4k_fails_diff, cap_4k_fails_diff_gb))
    print("Cap 2m fails: {} ({:.4f}GB)".format(cap_2m_fails_diff, cap_2m_fails_diff_gb))
    print("Cap 4k successes: {} ({:.4f}GB)".format(cap_4k_succ_diff, cap_4k_succ_diff_gb))
    print("Cap 2m successes: {} ({:.4f}GB)".format(cap_2m_succ_diff, cap_2m_succ_diff_gb))

if __name__ == "__main__":
    main()
