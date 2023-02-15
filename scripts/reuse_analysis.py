# Python3 program to find highest
# power of 2 smaller than or
# equal to n.
import argparse
import math
import collections
import re
import os
import testlib

CACHEGRIND_PATH="/localdisk/tools/valgrind"
DATA_PATH="./data"

array_range = {
	# "A":("0x4c8d000",8503688),
	# "x1":("0x403a000",8248),
	# "x2":("0x403d000",8248),
	# "y_1":("0x4040000",8248),
	# "y_2":("0x4043000",8248)
	"A":("0x4c8d000",8503688),
	"x":("0x403a000",8248),
	"y":("0x403d000",8248),
	"tmp":("0x4040000",8248)
}

def find_array(addr):
	addr_dec = int(addr, 16)
	for array in array_range:
		start = int(array_range[array][0], 16)
		end = start + array_range[array][1]
		if addr_dec >= start and addr_dec <= end:
			return array
	return None

def highestPowerof2(n):
	p = int(math.log(n, 2))
	return int(pow(2, p))


def histogram_to_dist(histogram):
	total = sum(histogram.values())
	dist = collections.defaultdict(float)
	for ri in histogram:
		dist[ri] = histogram[ri] / total
	return dist


def read_trace(program):
	count = 0
	LAT = dict()
	histogram = collections.defaultdict(int)
	print(f"analyzing {program}, open trace {CACHEGRIND_PATH}/{program}.out")
	with open(f"{CACHEGRIND_PATH}/{program}.out") as f:
		for line in f:
			line = line.rstrip()
			m = re.search(rf"^s(.*),(.*),(.*)", line)
			if m:
				set_id = m.group(1)
				addr = m.group(2)
				block = m.group(3)
				array = find_array(addr)
				# if not array:
				# 	print(f"{addr} not an array access")
				if block in LAT:
					reuse = count - LAT[block][0]
					reuse = highestPowerof2(reuse)
					# if reuse <= 256 and reuse >= 64:
					# 	print(f"array {array} forms reuse {reuse}")
					histogram[reuse] += 1
				LAT[block] = (count, array)
				count += 1
	histogram[-1] = len(LAT)
	return histogram


if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Process some integers.')
	parser.add_argument('-p', '--prog', action='store', dest='benchmarks',
					type=str, nargs='*', default=testlib.POLYBENCH_LIST,
					help='set the program to be run, if not set, run all benchmarks')
	args = parser.parse_args()
	for program in args.benchmarks:
		if os.path.exists(f"{CACHEGRIND_PATH}/{program}.out"):
			histogram = read_trace(program)
			dist = histogram_to_dist(histogram)
			for ri in sorted(dist):
				print(f"{ri},{dist[ri]}")
			content = "Start to dump reuse time\n"
			content += "\n".join([f"{ri},{dist[ri]}" for ri in sorted(dist)])
			testlib.write_to_file(f"{DATA_PATH}/{program}-t4-cachegrind-rih.data", content)
		# testlib.run_cmd(f"./scripts/generate_cache_miss_ratio {DATA_PATH}/{program}-t4-cachegrind-rih.data {DATA_PATH}/{program}-t4-cachegrind-mrc.data")
		print(f"removing {CACHEGRIND_PATH}/{program}.out")
		testlib.run_cmd(f"rm {CACHEGRIND_PATH}/{program}.out")


				