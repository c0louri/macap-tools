#!/usr/bin/python3

import sys

def find_vma(VMAs, addr):
	if type(addr) is str:
		addr = int(addr, 16)
	for vma in VMAs.values():
		if addr >= vma.start and addr < vma.end:
			return vma
	return None

class VMA(object):
	def __init__(self, st, end, p, off, dev, ino, pathname, anchors=[]):
		self.start = st
		self.end = end
		self.size = end-st
		self.perms = p
		if 'p' in self.perms:
			self.region_type = 'private'
		elif 's' in self.perms:
			self.region_type = 'shared'
		else:
			print('Error with region type!')
		self.offset = off
		self.dev = dev
		self.inode = ino
		self.pathname = pathname
		if pathname is None:
			self.is_anonymous = True
		else:
			self.is_anonymous = False
		self.subVMAs = sorted(anchors, key=lambda x:x[0])

	def print_info(self):
		if self.is_anonymous:
			msg = '0x{:x}-0x{:x} {} anon'.format(self.start, self.end, self.region_type)
		else:
			msg = '0x{:x}-0x{:x} {} {}'.format(self.start, self.end, self.region_type, self.pathname)
		print(msg)
		if len(self.subVMAs) > 0:
			self.print_subVMAs()

	def print_subVMAs(self):
		for svma in self.subVMAs:
			print('    vaddr: 0x{:x} ,pfn: 0x{:x} ,offset: {}'.format(svma[0], svma[1], svma[2]))

	def find_subVMAs_by_offset(self, offset):
		res = []
		for svma in self.subVMAs:
			if offset == svma[2]:
				res.append(svma)
		return res

	def find_target_subVMA(self, addr):
		if type(addr) is str:
			addr = int(addr, 16)
		# check if vma contains this vaddr
		if addr < self.start or addr >= self.end:
			return None
		if len(self.subVMAs) == 0:
			return None
		else:
			if addr < self.subVMAs[0][0]:
				# if addr smaller than 1st subvma, return 1st subvma
				return self.subVMAs[0]
			elif addr >= self.subVMAs[-1][0]:
				# if addr larget than last subvma, return last subvma
				return self.subVMAs[-1]
			else:
				# addr is between 2 subVMAs
				i = 0
				while i < len(self.subVMAs)-1:
					if self.subVMAs[i][0] <= addr < self.subVMAs[i+1][0]:
						return self.subVMAs[i]
					i += 1

	def vaddr_in_right_subVMA(self, addr, offset):
		# find subVMA in which addr should be
		target_svma = self.find_target_subVMA(addr)
		# find subVMAs which have same offset as the addr's offset
		offset_subvma = self.find_subVMAs_by_offset(offset)
		return (target_svma in offset_subvma), target_svma


######################

def read_vma_map(pid, anchors=False):
	if anchors:
		open_file = f'/proc/{pid}/anchormaps'
	else:
		open_file = f'/proc/{pid}/maps'
	with open(open_file, 'r') as vma_map_file:
		lines = [line.rstrip('\n') for line in vma_map_file]
		return lines
	return None

def read_vma_pagemap_file(filename):
	with open(filename, 'r') as f:
		lines = [line.rstrip('\n') for line in f]
		# split lines list because it contains info for vma and pagemap
		i = 0
		while not lines[i].startswith("~!~"):
			i += 1
	return lines[ : i], lines[i+1 : ]

###############################

def create_vma_object(line, anchor_lines=[]):
	# preprocessing of vma line
	parts = line.split()
	address, perms, offset, dev, inode = parts[:5]
	offset, inode = int(offset, 16), int(inode)
	if 'p' in perms: # vma is MAP_PRIVATE
		region_type = 'private'
	elif 's' in perms: # vma is MAP_SHARED
		region_type = 'shared'
	else:
		print('Error with region_type!')
		exit()
	# check type of mapping, stach, heap, anonymos, etc
	if len(parts) == 5:
		pathname = None
	elif len(parts) == 6:
		pathname = parts[5] # [stack], [heap], filename, etc
	else:
		print('Error with length of vma line!')
		exit()
	st, end = address.split('-')
	vm_start, vm_end = int(st, 16), int(end, 16)
	# preprocession of anchor lines
	anchors = []
	for a_l in anchor_lines:
		parts = [part.strip('\s') for part in a_l.split()]   # if doesnt work then replace '\s' with ' \t'
		# 2nd element is vaddr, 4th is pfn ,offset is 6th
		anchors.append( ( int(parts[1], 16), int(parts[3], 16), int(parts[5]) ) )
	return VMA(vm_start, vm_end, perms, offset, dev, inode, pathname, anchors)


def create_all_vma(lines, anchors=False):
	checking_anchors = False
	pre_vmas = []
	i = 0
	st, end = 0, 0
	anchor_lines, vma_line = [], ""
	while i < len(lines):
		if not lines[i].startswith((' ', '\t')):
			# it is a vma line
			vma_line = lines[i]
			st, end = lines[i].split()[0].split('-')
		else:
			# it is an line about anchor
			if anchors:
				anchor_lines.append(lines[i])
		if (i+1 == len(lines)) or (not lines[i+1].startswith((' ', '\t'))):
			pre_vmas.append([(st,end), vma_line, anchor_lines])
			vma_line, anchor_lines = "", []
		i = i + 1
	vmas = {}
	for vma in pre_vmas:
		vma_obj = create_vma_object(vma[1], vma[2])
		vmas[(int(vma[0][0], 16), int(vma[0][1], 16))] = vma_obj
	return vmas


def read_vmas(pid, with_anchors=False):
	lines = read_vma_map(pid, with_anchors)
	vmas = create_all_vma(lines, with_anchors) # vmas is a dictionary with key a tuple (start, end)
	return vmas


"""
Returns a tuple:
1st element:
	List of all entries in pagemap
	Each element of list is a tuple consisted of:
		(vaddr, pfn, offset, num_pages, is_right_placed)
		// num_pages is 0 for not present, 1 for present single ones and 512 for thp present ones
		// is_right_placed is about if it part of a subvma and it is places in the right pfn
2nd element:
	Total present pages in custom pagemap
3rd element:
	 Total not present pages in custom pagemap
"""
def read_custom_pagemap(pagemap_file_or_lines, VMAs, read_file=False) :
	lines = []
	if read_file:
		if type(read_file) is not str:
			print("read_custom_pagemap : 1st parameter must be a file name (str)!")
			exit()
		with open(pagemap_file_or_lines, 'r') as map_file:
			lines = [line.rstrip('\n') for line in map_file]
	else:
		if type(pagemap_file_or_lines) is not list:
			print("read_custom_pagemap : 1st parameter must pagemap_file_from_cppbe a list of strings!")
			exit()
		lines = pagemap_file_or_lines
	total_present_pages = 0
	total_not_present_pages = 0
	pages = []
	for line in lines:
		if line.startswith('0x'):
			parts = [part.strip('\s') for part in line.split()]
			vaddr = int(parts[0], 16)
			pfn = int(parts[2], 16)
			offset = int(parts[4])
			page_type = parts[5]
			if page_type == 'not_present':
				total_not_present_pages += 1
				pages.append((vaddr, None, None, 0, None))
			elif 'thp' in page_type:
				# check if it is in subVMA and has the offset of the vma
				vma = find_vma(VMAs, vaddr)
				if vma is None:
					print('Couldn\'t find VMA for this address!', line)
					exit()
				is_right_placed, svma = vma.vaddr_in_right_subVMA(vaddr, offset)
				if page_type == 'no_thp' :
					total_present_pages += 1
					pages.append((vaddr, pfn, offset, 1, is_right_placed))
				elif page_type == 'thp':
					total_present_pages += 512
					pages.append((vaddr, pfn, offset, 512, is_right_placed))
				else:
					print("This shouldn\'t happen1!! ", line)
					exit()
			else:
				print("This shouldn\'t happen2!! ", line)
				exit()
	pages = sorted(pages, key=lambda x: x[0])
	return pages, total_present_pages, total_not_present_pages

"""
pagemap : it should be the return list of read_custom_pagemap()
"""
def create_offset_map(pagemap, VMAs, check_only_vmas_with_subvmas):
	# offsets is a dictionary
	# key is the offset
	# value is a tuple consisted of two COUNTERS:
	# 1st counter is the number of present pages ,with the key offset,
	# which are part of a subvma AND have the offset of the subvma
	# 2nd counter is the number of pages which have the offset but not in the right subvma
	offsets = {}
	# page_good_offset and pages_bad_offset are list(pair)  with 1st element the number of
	# pages in good and bad offset respectively and in the 2nd element a list of those
	# vaddr in each occassion
	pages_good_offset = [0, []]
	pages_bad_offset = [0, []]
	total_pres_p_in_subvmas = 0
	total_not_pres_p_in_subvmas = 0
	total_good_thp = 0
	total_bad_thp = 0
	for entry in pagemap:
		vaddr, pfn, offset, num_pages, is_right_placed = entry
		# if not present, continue to next entry
		if (pfn is None) or (pfn <= 0):
			continue
		vma = find_vma(VMAs, vaddr)
		if len(vma.subVMAs) > 0:
			total_pres_p_in_subvmas += num_pages
		# if no subvmas in vma and if it should check only vaddr in vmas with subvmas,
		# continue to the next vaddr
		if check_only_vmas_with_subvmas and (vma.subVMAs == []):
			continue
		# An address could have an offset of a subVMA but not be part of the subvma
		# In this occasion, num_pages is added to the offset counter of the
		# right placed...
		if offset not in offsets.keys():
			if is_right_placed:
				offsets[offset] = [num_pages, 0]
			else:
				offsets[offset] = [0, num_pages]
		else:
			# offset is already in keys
			if is_right_placed:
				offsets[offset][0] += num_pages
			else:
				offsets[offset][1] += num_pages
		# update pages_***_offset tuples:
		if is_right_placed:
			pages_good_offset[0] += num_pages
			pages_good_offset[1].append(vaddr)
			if num_pages == 512:
				total_good_thp += 1
		else:
			pages_bad_offset[0] += num_pages
			pages_bad_offset[1].append(vaddr)
			if num_pages == 512:
				total_bad_thp += 1

	return offsets, pages_good_offset, pages_bad_offset, total_pres_p_in_subvmas


def compare_pagemap(old_pagemap_file, new_pagemap_file, VMAs):
	pagemap_1, cnt_pres_1, cnt_not_pres_1 = read_custom_pagemap(old_pagemap_file)
	offsets_1, good_p_1, bad_p_1 = create_offset_map(pagemap_1, VMAs, True)
	pagemap_2, cnt_pres_2, cnt_not_pres_2 = read_custom_pagemap(new_pagemap_file)
	offsets_2, good_p_2, bad_p_2 = create_offset_map(pagemap_2, VMAs, True)
	#print(offsets_1)
	#print(offsets_2)
	print('1st pagemap statistics:')
	print('Present pages: ', cnt_pres_1)
	print('Not present pages: ',cnt_not_pres_1)
	print('Good-offset pages: ', good_p_1[0])
	print('Bad-offset pages: ', bad_p_1[0])
	# 2nd pagemap
	print('2nd pagemap statistics:')
	print('Present pages: ', cnt_pres_1)
	print('Not present pages: ',cnt_not_pres_1)
	print('Good-offset pages: ', good_p_1[0])
	print('Bad-offset pages: ', bad_p_1[0])

def print_pagemap_list(pagemap):
	for entry in pagemap:
		vaddr, pfn, offset, num_pages, is_right_placed = entry
		print("0x{:x} pfn: {:x} offset: {}  {}  {}".format(vaddr, pfn, offset, num_pages, is_right_placed))



# def main():
# 	args_number = len(sys.argv)
# 	args = sys.argv
# 	anchors = False
# 	pagemap_file_from_cpp = ""
# 	if args_number == 2:
#         	pid = int(args[1])
# 	elif args_number == 3:
# 		pid, anchors = int(args[1]), bool(int(args[2]))
# 	elif args_number == 4:
# 		pid = int(args[1])
# 		anchors = bool(int(args[2]))
# 		pagemap_file_from_cpp = args[3]
# 	else:
# 		print('#args = 2 : needs as argument PID, then only prints VMA')
# 		print('#args = 3 : arguments= PID, 1 (if anchors enabled)')
# 		print('#args = 4 : PID 1 <pagemap_file_name>')
# 		exit()
# 	VMAs = read_vmas(pid, anchors)
# 	if anchors and (pagemap_file_from_cpp != ""):
# 		custom_pagemap, cnt_pres, cnt_not_pres = read_custom_pagemap(pagemap_file_from_cpp, VMAs)
# 		offsets, good_p, bad_p, total_pres_svma = create_offset_map(custom_pagemap, VMAs, True)
# 		print('Pagemap statistics:')
# 		print('Present pages: ', cnt_pres)
# 		print('Not present pages: ',cnt_not_pres)
# 		print("~~~~~")
# 		print('Total present pages in subVMAs: ', total_pres_svma)
# 		print('Good-offset pages: ', good_p[0])
# 		print('Bad-offset pages: ', bad_p[0])
# 	else:
# 		# print info for VMA
# 		for vma in VMAs.values():
# 			vma.print_info()


# main for compined vma and pagemap lines
def main():
	args_number = len(sys.argv)
	args = sys.argv
	if args_number == 2:
		file_from_cpp = args[1]
	else:
		print('It needs a single parameter: the name of te file created by page-collect.run')
		exit()
	vma_lines, pagemap_lines = read_vma_pagemap_file(file_from_cpp)
	VMAs = create_all_vma(vma_lines, True)
	custom_pagemap, cnt_pres, cnt_not_pres = read_custom_pagemap(pagemap_lines, VMAs, False)
	offsets, good_p, bad_p, total_pres_svma = create_offset_map(custom_pagemap, VMAs, True)
	print('Pagemap statistics:')
	print('Present pages: ', cnt_pres)
	print('Not present pages: ',cnt_not_pres)
	print("~~~~~")
	print('Total present pages in subVMAs: ', total_pres_svma)
	print('Good-offset pages: ', good_p[0])
	print('Bad-offset pages: ', bad_p[0])


if __name__ == "__main__":
    main()

