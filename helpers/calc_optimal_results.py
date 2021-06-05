#!/usr/bin/python3

import sys
import math
import copy

def read_vma_map(filename):
	f = open(filename, 'r')
	lines = f.readlines()
	i = 0
	while i < len(lines):
		line = lines[i]
		if line.startswith("~!~"):
			break
		i += 1
	f.close()
	# keep only lines with info of vmas / subvmas
	lines = lines[ : i]
	# read vmas, subvmas from lines
	st, end = 0, 0
	pre_vmas, anchor_lines, vma_line = [], [], ""
	i = 0
	while i < len(lines):
		if not lines[i].startswith('\t'):
			# it is a vma line
			vma_line = lines[i]
			st, end = lines[i].split()[0].split('-')
		else:
			# it is an line about anchor
			anchor_lines.append(lines[i])
		if (i+1 == len(lines)) or (not lines[i+1].startswith((' ', '\t'))):
			pre_vmas.append([(st,end), vma_line, anchor_lines])
			vma_line, anchor_lines = "", []
		i = i + 1
	return pre_vmas

# parse and save in a better format vma/subvmas
# clean duplicate subvmas or never-used subvmas
def parse_pre_vmas(pre_vmas):
	svmas_per_vmas = {}
	for pre_vma in pre_vmas:
		vma_start, vma_end = hex(int(pre_vma[0][0], 16)>>12), hex(int(pre_vma[0][1],16)>>12)
		if len(pre_vma[2]) == 0:
			# vma has no svmas
			svmas_per_vmas[(vma_start, vma_end)] = []
			continue
		svmas = []
		for a_l in pre_vma[2]:
			parts = [part.strip('\s') for part in a_l.split()]
			svma_vpn, svma_pfn, offset = hex(int(parts[1], 16) >> 12), parts[3], int(parts[5])
			svmas.append((svma_vpn, svma_pfn, offset))
		# sorting subVMAs by their start vaddr
		svmas_per_vmas[(vma_start, vma_end)] = sorted(svmas, key=lambda x:int(x[0],16))
	return svmas_per_vmas

def create_ranges(svmas_per_vmas):
	# all_ranges = []
	pfn_ranges = []
	for bounds, svmas in svmas_per_vmas.items():
		# if len(svmas) == 0:
		# 	#no subvma in this vma
		# 	all_ranges.append(bounds)
		vma_start = bounds[0]
		vma_end = bounds[1]
		i = 0
		while i < len(svmas):
			svma = svmas[i]
			offset = svma[2]
			if (i == 0) or (int(svma[0],16) < int(vma_start, 16)):
				range_start = vma_start
			else:
				range_start = svma[0]
			if i == len(svmas)- 1: #its the last subvma
				range_end = vma_end
			else:
				if int(svmas[i+1][0], 16) > int(vma_end,16):
					range_end = vma_end
				else:
					range_end = svmas[i+1][0]
			# check if it is a valid range
			range = (range_start, range_end)
			size = int(range[1],16) - int(range[0], 16)
			if size > 0:
				pfn_range = (hex(int(range[0], 16) - offset), hex(int(range[1], 16) - offset))
				#pfn_ranges.append((pfn_range, range, size, svma[0], svma[1], (vma_start, vma_end), svma))
				pfn_ranges.append((pfn_range, range))
			i += 1
	return pfn_ranges

def populate_range_tlb_hist(pfn_ranges):
	range_tlb_hist = {}
	sizes_list = [] # the right way
	for range in pfn_ranges:
		size = int(range[0][1], 16) - int(range[0][0], 16)
		if size not in range_tlb_hist.keys():
			range_tlb_hist[size] = 1
		else:
			range_tlb_hist[size] += 1
		sizes_list.append(size)
	sizes_list = sorted(sizes_list, reverse=True)
	return range_tlb_hist, sizes_list


def find_contiguous_ranges(pfn_ranges):
	new_ranges = []
	pfn_ranges = [((int(a[0][0], 16), int(a[0][1], 16)), (int(a[1][0], 16), int(a[1][1], 16))) for a in pfn_ranges]
	i = 0
	while i < len(pfn_ranges):
		(curr_pfn_st, curr_pfn_end), (curr_vpn_st, curr_vpn_end) = pfn_ranges[i]
		if i == len(pfn_ranges) - 1:
			new_ranges.append( ( ( hex(curr_pfn_st), hex(curr_pfn_end) ), ( hex(curr_vpn_st), hex(curr_vpn_end) ) ) )
			break
		j = i + 1
		while j < len(pfn_ranges):
			(next_pfn_st, next_pfn_end), (next_vpn_st, next_vpn_end) = pfn_ranges[j]
			if (curr_pfn_end == next_pfn_st) and (curr_vpn_end == next_vpn_st):
				curr_pfn_end = next_pfn_end
				curr_vpn_end = next_vpn_end
				j += 1
			else:
				new_ranges.append( ( ( hex(curr_pfn_st), hex(curr_pfn_end) ), ( hex(curr_vpn_st), hex(curr_vpn_end) ) ) )
				break
			if j == len(pfn_ranges): # cornel case at end
				new_ranges.append( ( ( hex(curr_pfn_st), hex(curr_pfn_end) ), ( hex(curr_vpn_st), hex(curr_vpn_end) ) ) )
		i = j
	return new_ranges

def fix_pfn_ranges(old_pfn_ranges):
	final_pfn_ranges = []
	pfn_ranges = [((int(a[0][0], 16), int(a[0][1], 16)), (int(a[1][0], 16), int(a[1][1], 16))) for a in old_pfn_ranges]

	(curr_pfn_st, curr_pfn_end), (curr_vpn_st, curr_vpn_end) = pfn_ranges[0]
	i = 1
	while i < len(pfn_ranges):
		(next_pfn_st, next_pfn_end), (next_vpn_st, next_vpn_end) = pfn_ranges[i]
		if curr_pfn_st < curr_pfn_end < next_pfn_st < next_pfn_end: # case I (non-overlapping ranges)
			# add curr range to new pfn ranges
			final_pfn_ranges.append( ( ( hex(curr_pfn_st), hex(curr_pfn_end) ), ( hex(curr_vpn_st), hex(curr_vpn_end) ) ) )
			# set as current the next range
			(curr_pfn_st, curr_pfn_end), (curr_vpn_st, curr_vpn_end) = pfn_ranges[i]
			i += 1
		elif curr_pfn_st < curr_pfn_end == next_pfn_st < next_pfn_end : # (l1 < r1 == l2 < r2), case II
			if curr_vpn_end == next_vpn_st: # case II.a )the two ranges are contiguous in both address spaces
				# combine ranges (extend frst)
				curr_pfn_end = next_pfn_end
				curr_vpn_end = next_vpn_end
				# range is not added to final ranges, beacuse the next range could be interleaving with the next of it
				i += 1
			else: # case II.b)
				# curr and next ranges are not conitguous in virt address range, but can be handled as non-interleaving
				final_pfn_ranges.append( ( ( hex(curr_pfn_st), hex(curr_pfn_end) ), ( hex(curr_vpn_st), hex(curr_vpn_end) ) ) )
				# set as current the next range
				(curr_pfn_st, curr_pfn_end), (curr_vpn_st, curr_vpn_end) = pfn_ranges[i]
				i += 1
		elif next_pfn_st < curr_pfn_end: # case III (l2 < r1) interleaving ranges
			if curr_pfn_st == next_pfn_st: # case III.i (l1 == l2)
				if curr_pfn_end > next_pfn_end: # case III.i.a (l1 == l2 < r2 < r1) next_range inside curr_range (common start)
					# three ranges, add l1, l2
					# keep in final ranges interleaving of the highest vaddr
					if curr_vpn_st > next_vpn_st: # keep current as whole (ignore next)
						i += 1
					else: # add in final ranges the common part with next vpn range and curr is the rest
						# next_vpn_st > curr_vpn_st
						final_pfn_ranges.append( ( ( hex(next_pfn_st), hex(next_pfn_end) ), ( hex(next_vpn_st), hex(next_vpn_end) ) ) )
						# update current range with the remainder
						curr_pfn_st = next_pfn_end
						remain_size = curr_pfn_end - next_pfn_end
						curr_vpn_st = curr_vpn_st + remain_size
						i += 1
				elif curr_pfn_end < next_pfn_end: # case III.i.c (l1 == l2 < r1 < r2) curr range inside next range (common start)
					if curr_vpn_st > next_vpn_st:
						#add curr to final pfn ranges, and keep the remainder of next as current
						final_pfn_ranges.append( ( ( hex(curr_pfn_st), hex(curr_pfn_end) ), ( hex(curr_vpn_st), hex(curr_vpn_end) ) ) )
						# keep remainder of next range in final pfn ranges
						remain_size = next_pfn_end - curr_pfn_end
						curr_pfn_st = next_pfn_end - remain_size
						curr_pfn_end = next_pfn_end
						curr_vpn_st = next_vpn_end - remain_size
						curr_vpn_end = next_vpn_end
						i += 1
					else:
						# curr_vpn_st < next_vpn_st
						curr_pfn_st, curr_pfn_end = next_pfn_st, next_pfn_end
						curr_vpn_st, curr_vpn_end = next_vpn_st, next_vpn_end
						i += 1
				elif curr_pfn_end == next_pfn_end: # case III.i.b (l1 == l2 and r1 == r2) same pfn ranges
					# keep the range withthe highest vpn range
					if curr_vpn_st > next_vpn_st:
						# keep current range, no addit
						i += 1
					else:
						curr_pfn_st, curr_pfn_end = next_pfn_st, next_pfn_end
						curr_vpn_st, curr_vpn_end = next_vpn_st, next_vpn_end
						i += 1
			else: # case III.ii (l1 < l2) (if l1 > l2 something is wrong with sorting)
				if curr_pfn_end < next_pfn_end: # case III.ii.a (l1 < l2 < r1 < r2)
					common_size = curr_pfn_end - next_pfn_st
					bef_remain_size = next_pfn_st - curr_pfn_st
					after_remain_size = next_pfn_end - curr_pfn_end
					# find in which part common part will be
					if curr_vpn_st < next_vpn_st:
						# keep common size with after range
						after_remain_size += common_size
					else:
						# keep common size in before range
						bef_remain_size += common_size
					# add before range in final pfn_ranges
					final_pfn_ranges.append( ( ( hex(curr_pfn_st), hex(curr_pfn_st + bef_remain_size) ),
											   ( hex(curr_vpn_st), hex(curr_vpn_st + bef_remain_size) ) ) )
					# update curr range with the remainder
					curr_pfn_end = next_pfn_end
					curr_pfn_st = next_pfn_end - after_remain_size
					curr_vpn_end = next_vpn_end
					curr_vpn_st = next_vpn_end - after_remain_size
					i += 1
				elif curr_pfn_end == next_pfn_end: # case III.ii.b (l1 < l2 < r1 == r2)
					if curr_vpn_st < next_pfn_st:
						# add to final pfn ranges the remainder range in the beginning
						bef_remain_size = next_pfn_st - curr_pfn_st
						final_pfn_ranges.append( ( ( hex(curr_pfn_st), hex(curr_pfn_st + bef_remain_size) ),
											   	   ( hex(curr_vpn_st), hex(curr_vpn_st + bef_remain_size) ) ) )
						# update current with the remainder
						curr_pfn_st = next_pfn_st
						curr_pfn_end = next_pfn_end
						curr_vpn_st = next_vpn_st
						curr_vpn_end = next_vpn_end
						i += 1
					else:
						# keep whole curr pfn range, ignore next range
						i += 1
				elif curr_pfn_end > next_pfn_end: # case III.ii.c (l1 < l2 < r2 < r1) next range in inner
					if curr_vpn_st > next_vpn_st:
						# ignored next range
						i += 1
					else:
						after_and_remain_size = curr_pfn_end - next_pfn_end
						before_common_size = next_pfn_st - curr_pfn_st
						# add in final_pfn_ranges before and common range (separately)
						final_pfn_ranges.append( ( ( hex(curr_pfn_st), hex(curr_pfn_st + before_common_size) ),
											   	   ( hex(curr_vpn_st), hex(curr_vpn_st + before_common_size) ) ) )
						final_pfn_ranges.append( ( ( hex(next_pfn_st), hex(next_pfn_end) ),
											   	   ( hex(next_vpn_st), hex(next_vpn_end) ) ) )
						# update remain with
						curr_pfn_st = curr_pfn_end - after_and_remain_size
						curr_pfn_end = curr_pfn_end
						curr_vpn_st = curr_vpn_end - after_and_remain_size
						curr_vpn_end = curr_vpn_end
						i += 1
	final_pfn_ranges.append( ( ( hex(curr_pfn_st), hex(curr_pfn_end) ), ( hex(curr_vpn_st), hex(curr_vpn_end) ) ) )
	return final_pfn_ranges



def print_cov_stats(hist, sizes, init_total_size):
	total_size = sum(sizes)
	hist_vals_pairs = [(k,v) for k,v in hist.items()]
	#
	num_entr, num_entr_80p_cov, num_entr_90p_cov, num_entr_99p_cov = 0, 0, 0, 0
	curr_cov = 0
	_32_entr_cov, _64_entr_cov , _128_entr_cov, _256_entr_cov = 0, 0, 0, 0
	_80p_cov, _90p_cov, _99p_cov = 0, 0, 0
	# first is size, second is time
	for (size, num) in hist_vals_pairs:

		if (num_entr + num > 32) and not _32_entr_cov:
			_32_entr_cov = curr_cov + (32 - num_entr) * size
		if (num_entr + num > 64) and not _64_entr_cov:
			_64_entr_cov = curr_cov + (64 - num_entr) * size
			print('fd')
		if (num_entr + num > 128) and not _128_entr_cov:
			_128_entr_cov = curr_cov + (128 - num_entr) * size
		if (num_entr + num > 256) and not _256_entr_cov:
			_256_entr_cov = curr_cov + (256 - num_entr) * size

		if (((curr_cov + size * num) / init_total_size) >= 0.8) and not num_entr_80p_cov:
			remaining_pages = math.ceil(0.8 * init_total_size) - curr_cov
			required_entries = math.ceil(remaining_pages / size)
			num_entr_80p_cov = num_entr + required_entries
			_80p_cov = curr_cov + required_entries * size
		if (((curr_cov + size * num) / init_total_size) >= 0.9) and not num_entr_90p_cov:
			remaining_pages = math.ceil(0.9 * init_total_size) - curr_cov
			required_entries = math.ceil(remaining_pages / size)
			num_entr_90p_cov = num_entr + required_entries
			_90p_cov = curr_cov + required_entries * size
		if (((curr_cov + size * num) / init_total_size) >= 0.99) and not num_entr_99p_cov:
			remaining_pages = math.ceil(0.99 * init_total_size) - curr_cov
			required_entries = math.ceil(remaining_pages / size)
			num_entr_99p_cov = num_entr + required_entries
			_99p_cov = curr_cov + required_entries * size

		num_entr += num
		curr_cov += size * num
	print("total_entries: {}".format(num_entr))
	print("total_coverage: {} (MB)".format(curr_cov * 4 / 1024))
	print()
	print("32 entries coverage: {:.2f}%% ({} 4k pages)".format(100*(_32_entr_cov/init_total_size), _32_entr_cov))
	print("64 entries coverage: {:.2f}%% ({} 4K pages)".format(100*(_64_entr_cov/init_total_size), _64_entr_cov))
	print("128 entries coverage: {:.2f}%% ({} 4K pages)".format(100*(_128_entr_cov/init_total_size), _128_entr_cov))
	print("256 entries coverage: {:.2f}%% ({} 4K pages)".format(100*(_256_entr_cov/init_total_size), _256_entr_cov))
	print()
	print("#entries for at least 80%% cov: {} (exact cov {:.2f}%%)".format(num_entr_80p_cov, 100*(_80p_cov/init_total_size)))
	print("#entries for at least 90%% cov: {} (exact cov {:.2f}%%)".format(num_entr_90p_cov, 100*(_90p_cov/init_total_size)))
	print("#entries for at least 99%% cov: {} (exact cov {:.2f}%%)".format(num_entr_99p_cov, 100*(_99p_cov/init_total_size)))

# main of script
pagemap_name = sys.argv[1]
pre_vmas = read_vma_map(pagemap_name)
svmas_vmas = parse_pre_vmas(pre_vmas)
pfn_ranges = create_ranges(svmas_vmas)
#range_tlb_hist = range_tlb_hist(svmas_vmas)
pfn_ranges = sorted(pfn_ranges, key=lambda x:int(x[0][0],16))

init_total_size = 0
for range in pfn_ranges:
	size_mb = (int(range[0][1], 16) - int(range[0][0], 16))
	init_total_size += size_mb
	# print("{}-{}: {} - {}, {}MB".format(range[0][0], range[0][1], range[1][0], range[1][1], size_mb))
print(init_total_size," 4K pages (of all vmas)")

less_pfn_ranges = find_contiguous_ranges(pfn_ranges)

distinct_pfn_ranges = fix_pfn_ranges(less_pfn_ranges)

print(len(distinct_pfn_ranges))

total_size = 0
for range in distinct_pfn_ranges:
	size_mb = (int(range[0][1], 16) - int(range[0][0], 16))* 4 / 1024
	total_size += size_mb
	print("{}-{}: {} - {}, {}MB".format(range[0][0], range[0][1], range[1][0], range[1][1], size_mb))
print(total_size,"MB")

print("Sorted by vpn:")
sort_by_vpn_ranges = sorted(distinct_pfn_ranges, key=lambda x: int(x[1][0], 16))
total_size = 0
for range in sort_by_vpn_ranges:
	size_mb = (int(range[0][1], 16) - int(range[0][0], 16))* 4 / 1024
	total_size += size_mb
	print("{}-{}: {} - {}, {}MB".format(range[0][0], range[0][1], range[1][0], range[1][1], size_mb))

range_tlb_hist,sizes_list = populate_range_tlb_hist(distinct_pfn_ranges)
print(sizes_list)
# print_range_hist(range_tlb_hist, sizes_list)
print_cov_stats(range_tlb_hist, sizes_list, init_total_size)