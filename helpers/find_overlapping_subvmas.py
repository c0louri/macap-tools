#!/usr/bin/python3

import sys

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
final_svmas = []
for pre_vma in pre_vmas:
	#print(pre_vma)
	if len(pre_vma[2]) == 0:
		# vma has no svmas
		continue
	# print(pre_vma)
	vma_start, vma_end = int(pre_vma[0][0], 16), int(pre_vma[0][1], 16)
	svmas = []
	for a_l in pre_vma[2]:
		parts = [part.strip('\s') for part in a_l.split()]
		svma_vaddr , svma_pfn, offset = int(parts[1], 16), int(parts[3], 16), int(parts[5])
		if offset != (svma_vaddr>>12) - svma_pfn:
			print("something wrong with subVMAs -0")
			exit()
		svmas.append((svma_vaddr, svma_pfn, offset))
	# sorting subVMAs by their start vaddr
	svmas = sorted(svmas, key=lambda x:x[0])

	# # here subVMAs which would never be used from vma should be deleted
	#if len(svmas) > 1:
	new_start_pos = 0
	new_end_pos = len(svmas) - 1
	## remove subvmas with vaddr < vm_start
	i = 0
	while i < len(svmas):
		# print(svmas[i])
		if svmas[i][0] <= vma_start:
			new_start_pos = i
		else:
			break
		i += 1
	## remove subvmas with vaddr >= vm_end which will never be used
	# reverse parsing of svmas list
	i = len(svmas) - 1
	while i > 0:
		if svmas[i][0] < vma_end:
			new_end_pos = i
			break
		i -= 1
	svmas = svmas[new_start_pos : new_end_pos+1]
	# remaining subvmas are potentially populated
	## create active vpn-pfn ranges for each subvma
	# check onlyy first subvmas (special case)
	if len(svmas) == 1:
		vpn_range = (vma_start >> 12, vma_end >> 12)
	else:
		# print(svmas)
		vpn_range = (vma_start >> 12, svmas[1][0] >> 12)
	offset = svmas[0][2]
	pfn_range = (vpn_range[0] - offset, vpn_range[1] - offset)
	# save info of first svma
	final_svmas.append((pfn_range, vpn_range))
	# check the rest of svmas
	i = 1
	while i < len(svmas):
		svma = svmas[i]
		if svma[0] > vma_end:
			print("this subvma should have been deleted")
			exit()
		vpn_range_start = svma[0] >> 12
		if i == len(svmas)-1:
			# it is the last subvma
			vpn_range_end = vma_end >> 12
		else:
			vpn_range_end = svmas[i+1][0] >> 12
		vpn_range = (vpn_range_start, vpn_range_end)
		pfn_range = (vpn_range[0] - offset, vpn_range[1] - offset)
		# save svma and pfn range in final lists
		final_svmas.append((pfn_range, vpn_range))
		i += 1

# sort final svmas by their pfn start address
svmas = sorted(final_svmas, key=lambda x : x[0][0])

i = 0
while i < len(svmas):
	svma1 = svmas[i]
	j = i + 1
	while j < len(svmas):
		svma2 = svmas[j]
		overlapping_range = are_overlapping(svma1, svma2)
		if overlapping_range is not None:
			length = overlapping_range[1] - overlapping_range[0] # length in page frames (4k pages)
			length_mb = (length * 4) / 1024
			print("Found overlapping ranges, length={}({}MB) !".format(length, length_mb))
			print("Svma ranges: ({:x}, {:x}), ({:x}, {:x})".format(
				  svma1[1][0]<<12, svma1[1][1]<<12, svma2[1][0]<<12, svma2[1][1]<<12))
			print("Overlapping range: ({:x}, {:x})".format(
				  overlapping_range[0], overlapping_range[1]))
		j += 1
	i += 1
