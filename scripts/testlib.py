# import numpy as np
# import scipy.stats
import os
import subprocess

POLYBENCH_LIST = sorted("2mm 3mm adi atax bicg cholesky correlation covariance deriche doitgen durbin fdtd-2d floyd-warshall gemm gemver gesummv gramschmidt jacobi-1d jacobi-2d lu ludcmp mvt symm syr2k syrk trisolv trmm heat-3d".split(" "))


def read_from_file(fname):
	content = list()
	with open(f"{fname}") as f:
		for line in f:
			line = line.rstrip()
			if line:
				content.append(line)
	return content



def write_to_file(fname, content):
	f =open(fname, "w")
	f.write(content)
	f.close()


# def confidence_interval(data, confidence=0.95):
# 	a = 1.0 * np.array(data)
# 	n = len(a)
# 	m, se = np.mean(a), scipy.stats.sem(a)
# 	h = se * scipy.stats.t.ppf((1 + confidence) / 2., n - 1)
# 	return m-h, m+h


def run_cmd(cmd):
	proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	stdout, stderr = proc.communicate()
	return stdout.decode(), stderr.decode()


# compute the accuracy of reuse interval distribution
# rih and rih_baseline should be a ratio distribution
def rt_accuracy(rih_baseline, rih):
	err = 0.0
	for ri in rih_baseline:
		if ri in rih:
			err += abs(rih_baseline[ri] - rih[ri])
		else:
			err += rih_baseline[ri]
	return 1 - (err / 2.)


# do the chi-square goodness to fit of two distributions
def chi_square_test(expect, observe):
	x2 = 0.0
	diff = []
	for x in observe:
		diff += [(observe[x] - expect[x])**2 / expect[x]]
	x2 = sum(diff)
	


