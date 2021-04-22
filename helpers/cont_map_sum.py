## Node 0, zone   Normal [0x116800--0x124400](220MB),
# needs a single argument, a file with the ouput of ...
# ... /proc/capaging_contiguity_map
import sys

with open(sys.argv[1], 'r') as f:
    lines = f.readlines()
    normal_line = None
    for line in lines:
        if 'Normal' in line:
            normal_line = line
            break
    entries = [entry.strip(", \n") for entry in normal_line.split(' ')]
    print(entries)
    parse_str = "[0x{:x}--0x{:x}]({:d}MB)"
    total_mb = 0
    for entry in entries:
        if not entry.startswith('['):
            continue
        tokens = entry.rstrip('MB),').split('](')
        total_mb += int(tokens[1])
        print(entry, int(tokens[1]))
    print('Total available memory in NORMAL zone: {}MB'.format(total_mb))
