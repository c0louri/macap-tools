#!/usr/bin/python3

import sys
import copy

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

# create ranges from output of parse_pre_vmas()
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
				row = (range, size, svma[0], pfn_range)
				# all_ranges.append(row)
				pfn_ranges.append((pfn_range, range, size, svma[0], svma[1], (vma_start, vma_end), svma))
			i += 1
	return pfn_ranges

def are_overlapping(range1, range2):
	# pfn ranges = (L1, R1)
	l1, r1 = range1
	l2, r2 = range2
	if max(l1, l2) < min(r1, r2):
		# ranges overlapping
		overlapping_interval = (max(l1,l2), min(r1, r2))
	else:
		# ranges are non-overlapping
		overlapping_interval = None
	return overlapping_interval

def inner_range(range1, range2):
	l1, r1 = range1
	l2, r2 = range2
	if l1 <= l2 and r1 >= r2:
		# range2 is inner
		return 2
	elif l1 >= l2 and r1 <= r2:
		# range1 is inner
		return 1
	else:
		return 0

# returns subvmas which can be removed (inner ranges)
def find_overlapping_ranges(pfn_ranges):
	# new_pfn_ranges = copy.deepcopy(pfn_ranges)
	to_remove_subvmas = []
	total_overlapping_size = 0
	total_overlapping_size_in_same_vma = 0
	i = 0
	while i < len(pfn_ranges) - 1:
		# row = pfn_ranges[i]
		pfn_range = pfn_ranges[i][0]
		vma = pfn_ranges[i][5]
		svma = pfn_ranges[i][6]
		pfn_st, pfn_end = int(pfn_range[0], 16), int(pfn_range[1], 16)
		j = i+1
		while j < len(pfn_ranges):
			# curr_row = pfn_ranges[j]
			curr_pfn_range = pfn_ranges[j][0]
			curr_vma = pfn_ranges[j][5]
			curr_svma = pfn_ranges[j][6]
			curr_pfn_st, curr_pfn_end = int(curr_pfn_range[0], 16), int(curr_pfn_range[1], 16)
			overlapping_range = are_overlapping((pfn_st, pfn_end), (curr_pfn_st, curr_pfn_end))
			if overlapping_range is None:
				j += 1
				continue
			else:
				# print overlapping range
				overlapping_size = overlapping_range[1] - overlapping_range[0]
				total_overlapping_size += overlapping_size
				# check if they are in same vma
				if vma == curr_vma:
					# ranges are in the same vma
					print("Overlapping range: {:x}-{:x} (size={}) of ranges: {}, {} (same)".format(overlapping_range[0], overlapping_range[1],
						overlapping_size, pfn_range, curr_pfn_range))
					total_overlapping_size_in_same_vma += overlapping_size
					# remove inner range (if one is inner of the other)
					to_remove = inner_range((pfn_st, pfn_end), (curr_pfn_st, curr_pfn_end))
					if to_remove == 1:
						#remove first
						to_remove_subvmas.append((vma, svma))
					elif to_remove == 2:
						#remove second
						to_remove_subvmas.append((curr_vma, curr_svma))
				else:
					print("Overlapping range: {:x}-{:x} (size={}) of ranges: {}, {}".format(overlapping_range[0], overlapping_range[1],
						overlapping_size, pfn_range, curr_pfn_range))
										# remove inner range (if one is inner of the other)
					to_remove = inner_range((pfn_st, pfn_end), (curr_pfn_st, curr_pfn_end))
					if to_remove == 1:
						#remove first
						to_remove_subvmas.append((vma, svma))
					elif to_remove == 2:
						#remove second
						to_remove_subvmas.append((curr_vma, curr_svma))
			j += 1
		i += 1
	print("Total overlapping : {}MB".format(total_overlapping_size*4/1024))
	print("Total overlapping in same vma: {}MB".format(total_overlapping_size_in_same_vma*4/1024))
	return to_remove_subvmas

pagemap_name = sys.argv[1]

f = open(pagemap_name, 'r')
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


#main script
svmas_per_vma = parse_pre_vmas(pre_vmas)
# create pfn ranges
pfn_ranges = create_ranges(svmas_per_vma)
pfn_ranges = sorted(pfn_ranges, key=lambda x:int(x[0][0],16))
# for row in pfn_ranges:
# 	print("{}-{} : {}, {}, {}, {}".format(row[0][0], row[0][1], row[1], row[2], row[3], row[4]))
print("#pfn_ranges = ", len(pfn_ranges))
to_remove_svmas = find_overlapping_ranges(pfn_ranges)
#
print()
#
# remove obsolete svmas
new_svmas_per_vma = copy.deepcopy(svmas_per_vma)
for (vma, svma) in to_remove_svmas:
	new_svmas_per_vma[vma].remove(svma)
# create new pfn ranges
new_pfn_ranges = create_ranges(new_svmas_per_vma)
new_pfn_ranges = sorted(new_pfn_ranges, key=lambda x:int(x[0][0],16))
# for row in new_pfn_ranges:
# 	print("{}-{} : {}, {}, {}, {}".format(row[0][0], row[0][1], row[1], row[2], row[3], row[4]))
print("After removing overlapping inner ranges:")
print("#pfn_ranges = ", len(new_pfn_ranges))
find_overlapping_ranges(new_pfn_ranges)