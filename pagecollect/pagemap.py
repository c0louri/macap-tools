#!/usr/bin/python3

import sys

def find_vma(VMAs, addr):
	if addr is str:
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
			is_anonymous = True
		else:
			is_anonymous = False
		self.subVMAs = sorted(anchors, key=lambda x:x[0])

	def print_info(self):
		if self.is_anonymous:
			msg = '0x{:x}-0x{:x} {} anon'.format(self.start, self.end, self.region_type)
		else:
			msg = '0x{:x}-0x{:x} {} {}'.format(self.start, self.end, self.region_type, self.pathname)
		print(msg)
		return msg

	def print_subVMAs(self):
		for svma in subVMAs:
			print('vaddr: 0x{:x} ,pfn: 0x{:x} ,offset: {}'.format(svma[0], svma[1], svma[2]))

	def find_subVMAs_by_offset(self, offset):
		res = []
		for svma in self.subVMAs:
			if offset == svma[2]:
				res.append(svma)
		return res

	def vaddr_in_right_subVMA(self, addr, offset):
		# find subVMA in which addr should be
		target_svma = self.find_target_subVMA(addr)
		# find subVMAs which have same offset as the addr's offset
		offset_subvma = self.find_subVMAs_by_offset(offset)
		return (target_svma in offset_subvma), target_svma

	def find_target_subVMA(self, addr):
		if addr is str:
			addr = int(addr, 16)
		# check if vma contains this vaddr
		if addr < self.start or addr >= self.end:
			return None
		for svma in self.subVMAs:
			if addr >= svma[0]:
				return svma
		return None

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


def create_vma_object(line, anchor_lines=[]):
	# preprocessing of vma line
	parts = line.split()
	address, perms, offset, dev, inode = parts[:5]
	offset, inode = int(offset), int(inode)
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
		parts = [part.strip('\s') for part in line.split()]   # if doesnt work then replace '\s' with ' \t'
		# 2nd element is vaddr, 4th is pfn ,off
		anchors.append( ( int(parts[1], 16), int(parts[3], 16), int(parts[5]) ) )
	return VMA(vm_start, vm_end, perms, offset, dev, inode, pathname, anchors)


def create_all_vma(lines, anchors=False):
	checking_anchors = False
	pre_vmas = []
	i = 0
	vma = []
	st, end = 0, 0
	anchor_lines = []
	while i < len(lines):
		if not lines[i].startswith((' ', '\t')):
			# it is a vma line
			vma = lines[i]
			st, end = lines[i].split()[0].split('-')
		else:
			# it is an line about anchor
			if anchors:
				anchor_lines.append(lines[i])
		if (i+1 == len(lines)) or (not lines[i+1].startswith((' ', '\t'))):
			pre_vmas.append([(st,end), vma, anchor_lines])
			anchor_lines = []
		i = i + 1
	vmas = {}
	for vma in pre_vmas:
		vma_obj = create_vma_object(vma[1], vma[2])
		vmas[(int(vma[0][0]), int(vma[0][1]))] = vma_obj
	return vmas


def read_vmas(pid, with_anchors=False):
	lines = read_vma_map(pid, with_anchors)
	vmas = create_all_vma(lines, with_anchors) # vmas is a dictionary with key a tuple (start, end)



def main():
	args_number = len(sys.argv)
	args = str(sys.argv)
	if len(args_number) == 2:
		pid = int(args[1])
		anchors = False
	elif len(args_number) == 3:
		pid, anchors = int(args[1]), bool(int(args[2]))
	else:
		print('wrong number of arguments')
		exit()
	vmas = read_vmas(pid, anchors)
	print('Done')