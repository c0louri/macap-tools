#!/usr/bin/python3

import sys
import copy

def are_overlapping(svma1, svma2):
	# pfn ranges = (L1, R1)
	l1, r1 = svma1[0]
	l2, r2 = svma2[0]
	if max(l1, l2) < min(r1, r2):
		# ranges overlapping

		overlapping_interval = (max(l1,l2), min(r1, r2))
	else:
		# ranges are non-overlapping
		overlapping_interval = None
	return overlapping_interval

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

# parse and save in a better format vma/subvmas
# clean duplicate subvmas or never-used subvmas
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

all_ranges = []
pfn_ranges = []
for bounds, svmas in svmas_per_vmas.items():
	if len(svmas) == 0:
		#no subvma in this vma
		all_ranges.append(bounds)
	vma_start = bounds[0]
	vma_end = bounds[1]
	i = 0
	while i < len(svmas):
		vma = svmas[i]
		offset = vma[2]
		if (i == 0) or (int(vma[0],16) < int(vma_start, 16)):
			range_start = vma_start
		else:
			range_start = vma[0]
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
			row = (range, size, vma[0], pfn_range)
			all_ranges.append(row)
			pfn_ranges.append((pfn_range, range, size, vma[0], vma[1]))
		i += 1

# print(pfn_ranges)

pfn_ranges = sorted(pfn_ranges, key=lambda x:int(x[0][0],16))
for row in pfn_ranges:
	print("{}-{} : {}, {}, {}, {}".format(row[0][0], row[0][1], row[1], row[2], row[3], row[4]))



