'''

This script run the  DynamoRIO benchmark and output the timing info in seconds
	- Support NUMA Affinity
		The script will run each benchmark several times
		In each run, it first put all data in local, then in remote node to test the NUMA effect

		Based on the thread count, the script will set the affinity and bind all processes to one node

Variables:
	BENCHMARKLIST {list} -- List of NPB benchmark to run
	TESTBENCH {list} -- List of NPB benchmark used for debugging
	APP_PATH {str} -- [NEED MODIF] The absolute path of NPB APP app
	CORE_COUNT {int} -- Total Physical cores in each NUMA node
	if __name__ {[type]} -- main
'''
#!usr/bin/python3
import argparse
import os
import re
import testlib
from scipy import stats
import pandas as pd


ITERATION_TRAVERSED = {
	"2mm" : 16826368,
	"3mm" : 25214976,
	"adi" : 25077836,
	"atax" : 8390656,
	"bicg" : 8390656,
	"correlation" : 4433215,
	"covariance" : 4367040,
	"deriche" : 20971520,
	"doitgen" : 1080033280,
	"fdtd-2d" : 14661638,
	"gemm" : 8421376,
	"gemver" : 14683136,
	"gesummv" : 8393728,
	"gramschmidt" : 8380352,
	"heat-3d" : 44008272,
	"jacobi-2d" : 12533808,
	"lu" : 2787904,
	"mvt" : 8388608,
	"syrk" : 4243584,
	"syr2k" : 6357120,
	"symm" : 4161536,
	"trmm" : 4194304,
	"anisotropic-diffusion": 27050400,
	"dct" : 16842752,
	"harris" : 68251740,
	"tce": 536870912
}

# freqmine, vips cannot control the thread count through command line input
# they require to set os environemnt
APP_PATH="/localdisk/tools/ppcg/out.ppcg-0.08.4-42-g5e07c52"
CACHEGRIND_PATH="/localdisk/tools/valgrind"

CORE_COUNT=4
# with the benchmark name, generate its running command
# if the program with the input size is not compiled, compile it first
def generate_command(program, input_size='A'):
	if not os.path.isfile(f"{APP_PATH}/{program}.{input_size}"):
		os.system(f"make {program} CLASS={input_size}")
	return f"{APP_PATH}/{program}.{input_size}"

def generate_core_bind_seq(thread_cnt):
	assert thread_cnt <= CORE_COUNT, "Thread count is greater than the physical core count"
	return "{"+",".join([str(i) for i in range(0, 2*thread_cnt, 2)])+"}"

# pass the output of parsec output
# return the time in pure second
# pass the output of parsec output
# return the time in pure second
def time_parser(stderr):
	print(stderr)
	time = 0.0
	real_time = 0.0
	for line in stderr.split("\n"):
		line = line.rstrip()
		if line.startswith("user") or line.startswith("sys"):
			time_output = line.split("\t")[1]
			time += int(time_output.split("m")[0]) * 60.0 + float(time_output.split("m")[1][:-1])
		if line.startswith("real"):
			time_output = line.split("\t")[1]
			real_time = int(time_output.split("m")[0]) * 60.0 + float(time_output.split("m")[1][:-1])
	return time, real_time

# print the performance
def dump_performance(perf):
	for program in perf:
		print(f"[{program}] {perf[program]}")


def load_miss_ratio(program, content):
	dr = 0
	dw = 0
	d1mr = 0
	d1mw = 0
	dlmr = 0
	dlmw = 0
	start_read_miss_ratio = False
	for line in content:
		line = line.rstrip()
		# if line.startswith(f"fn={kernel}._omp_fn"):
		if line.startswith(f"fn=.omp_outlined."):
			print(line)
			start_read_miss_ratio = True
			continue
		if line.startswith(f"fn=") and start_read_miss_ratio:
			start_read_miss_ratio = False
		if start_read_miss_ratio:
			linelist = line.split(" ")
			dr += int(linelist[4])
			dw += int(linelist[-3])
			d1mr += int(linelist[5])
			d1mw += int(linelist[-2])
			dlmr += int(linelist[-4])
			dlmw += int(linelist[-1])
			# print(f"{int(linelist[5])+int(linelist[-2])} {int(linelist[-4])+int(linelist[-1])}, {(int(linelist[-4])+int(linelist[-1])) / (int(linelist[5])+int(linelist[-2]))}")
			continue
	# sanity check
	if ITERATION_TRAVERSED[program] != int(d1mr+d1mw):
		print(f"Expected Access {ITERATION_TRAVERSED[program]}, ACTUAL {d1mr+d1mw}")
	else:
		print(f"PASS")
	# print(f"[{program}] {d1mr+d1mw} {dlmr+dlmw} {(dlmr+dlmw) / (d1mr+d1mw)}")
	d1_miss_rate, dl_miss_rate = 0.0, 0.0
	if dw+dr > 0:
		d1_miss_rate = ((d1mr+d1mw) / (dw+dr))
	if d1mr+d1mw > 0:
		dl_miss_rate = ((dlmr+dlmw) / (d1mr+d1mw))
	return d1_miss_rate, dl_miss_rate


def main(benchmarks, cache_size, thread_cnt=4, total_epoch=5):
	corebind = "0"
	print("=====================================================================")
	print("CONFIGURATIONS:")
	print(f"Cache Params to simulate\t{cache_size*1024},{cache_size*16},64")
	print(f"Total # of Threads to run\t{thread_cnt}")
	if thread_cnt > 1:
		core_bind = generate_core_bind_seq(t)
		print(f"Core Binding\t{core_bind}")
	print(f"Total Epoch numbers to run\t{total_epoch}")
	print(f"BENCHMARK SET:\n")
	for program in benchmarks:
		print(program)
	print("======================================================================")
	# {
	# 	program: { experiment: average time in second }
	# }
	performance = dict()
	miss_ratio = dict()
	for program in benchmarks:
		if program in ["nussinov", "seidel-2d", "floyd-warshall", "ludcmp"]:
			continue
		print(f"[{thread_cnt}] Compiling {program} ...")
		testlib.run_cmd(f"{APP_PATH}/../polybench_test.sh --keep")
		print(f"{APP_PATH}/../polybench_test.sh --keep")
		total_time, total_opt_time = 0.0, 0.0


		print(f"read address range from /localdisk/tools/valgrind/{program}.addr")
		address_range = ""
		if os.path.exists(f"/localdisk/tools/valgrind/{program}.addr"):
			content = testlib.read_from_file(f"/localdisk/tools/valgrind/{program}.addr")
			new_content = []
			for address_range in content:
				m = re.search(rf"(.*),0x(.*),(.*)", address_range)
				if m:
					array_name = m.group(1)
					base = int(m.group(2), 16)
					size = m.group(3)
					new_content.append(f"{array_name},{base},{size}")
			address_range = ";".join(new_content)
		print(f"{address_range}")
		cmd = f"time valgrind --tool=cachegrind --fair-sched=yes --D1=128,2,64 --LL={cache_size*1024},4,64 --cachegrind-out-file={program}-t{thread_cnt}-mrc.txt {APP_PATH}/{program}.orig"
		if thread_cnt > 1:
			os.environ['OMP_PROC_BIND'] = 'true'
			os.environ['OMP_DYNAMIC'] = 'false'
			os.environ['OMP_NUM_THREADS'] = f'{t}'
			os.environ["OMP_PLACES"] = f'{core_bind}'
			os.environ["ADDRESS_TUPLES"] = f'{address_range}'
			cmd = f"time valgrind --tool=cachegrind --fair-sched=yes --D1=128,2,64 --LL={cache_size*1024},4,64 --cachegrind-out-file={CACHEGRIND_PATH}/{program}-t{thread_cnt}-mrc.txt {APP_PATH}/{program}.ppcg_omp 2> {CACHEGRIND_PATH}/{program}.out"
		corebind = generate_core_bind_seq(thread_cnt)
		os.environ["OMP_NUM_THREADS"] = f"{thread_cnt}"
		for epoch in range(total_epoch):
			print(f"[{epoch}] Running {program} ...")
			print(cmd)
			stdout, stderr = testlib.run_cmd(cmd)
			testlib.write_to_file(f"{CACHEGRIND_PATH}/{program}.addr", stdout)
			# time, real = time_parser(stderr)
			time = float(testlib.read_from_file(f"{CACHEGRIND_PATH}/{program}.addr")[-1])
			time = 0.0
			total_time += time
		performance[program] = total_time / total_epoch
		print(f"[{program}] {total_time / total_epoch}")
		kernel_name = program
		if program in ["fdtd-2d", "jacobi-1d", "jacobi-2d", "heat-3d", "floyd-warshall"]:
			kernel_name = program.replace("-", "_")
		if not os.path.exists(f"{CACHEGRIND_PATH}/{program}-t{thread_cnt}-mrc.txt"):
			continue
		print(f"read miss ratio from {program}-t{thread_cnt}-mrc.txt")
		content = testlib.read_from_file(f"{CACHEGRIND_PATH}/{program}-t{thread_cnt}-mrc.txt")
		# d1mr, dlmr = load_miss_ratio(f"kernel_{kernel_name}", content)
		d1mr, dlmr = load_miss_ratio(program, content)
		miss_ratio[program] = dlmr

		print(f"do the trace anlaysis ... from {CACHEGRIND_PATH}/{program}.out")
		os.system(f"python3 ./scripts/reuse_analysis.py -p {program}")
	# perfpd = pd.DataFrame.from_dict(performance, orient='index', columns=[f"T={thread_cnt}"])
	# print(perfpd)
	# perfpd.to_csv(f"cachegrind_polybench_c{cache_size}KB_t{thread_cnt}_time.csv")
	# print(miss_ratiopd)
	# miss_ratiopd.to_csv(f"cachegrind_polybench_c{cache_size}KB_t{thread_cnt}_mr.csv")
	return miss_ratio, performance


if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Process some integers.')
	parser.add_argument('-p', '--prog', action='store', dest='benchmarks',
					type=str, nargs='*', default=testlib.POLYBENCH_LIST,
					help='set the program to be run, if not set, run all benchmarks')
	parser.add_argument('-t', '--tgroup', action='store', dest='thread_cnts',
					type=int, nargs='*', default=[2,4,6,8,10],
					help='set the set of threds to be run, if not set, run the default [2,4,6,8,10] setting')
	parser.add_argument('-c', '--cache', type=int, default=128,
                    help='set the size of the cache to simulate (KB)')
	parser.add_argument('-e', '--epoch', type=int, default=5,
                    help='set the times each program will run')
	args = parser.parse_args()
	
	for t in args.thread_cnts:
		mr_frames, perf_frames = [], [] # merge the MRC and time of cachegrind
		mrc_perf = dict() # time to collect the miss ratio, it is the sum of a row in perf_frames
		for program in args.benchmarks:
			mrc_perf[program] = 0.0
		# for cache_kb in [2,4,8,16,32,64,128]:
		for cache_kb in [2]:
			mrc, perf = main(args.benchmarks, cache_kb, thread_cnt=t, total_epoch=args.epoch)
			perfpd = pd.DataFrame.from_dict(perf, orient='index', columns=[f"{cache_kb*16} Blocks"])
			mrpd = pd.DataFrame.from_dict(mrc, orient='index', columns=[f"{cache_kb*16} Blocks"])
			mr_frames += [mrpd]
			perf_frames += [perfpd]
			for program in args.benchmarks:
				mrc_perf[program] += perf[program]
		# print(f"4096 Blocks (256KB)")
		# print(mrpd_4096b)
		name = "-".join(args.benchmarks)
		resultpd = pd.concat(mr_frames, join='outer', axis=1) 
		# resultpd.to_csv(f"cachegrind_t{t}_{name}_mrc_polybench.csv")
		resultpd = pd.concat(perf_frames, join='outer', axis=1) 
		# resultpd.to_csv(f"cachegrind_t{t}_{name}_perf_polybench.csv")
		# generate_core_bind_seq(1)
		resultpd = pd.DataFrame.from_dict(mrc_perf, orient='index', columns=[f"T = {t}"])
		# resultpd.to_csv(f"cachegrind_t{t}_{name}_overall_perf_polybench.csv")
