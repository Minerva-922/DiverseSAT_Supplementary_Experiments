from subprocess import Popen, PIPE, STDOUT
import subprocess
import multiprocessing
from datetime import datetime
import os
import sys
import signal
import argparse


def worker(id, transformer, input_file, output_file, output_dir, cutoff_time, additional_args):
    print("[{}] Starting transformation on {}".format(id + 1, os.path.basename(input_file)))

    instance_name = os.path.basename(input_file)
    log_file = os.path.join(output_dir, "{}.out".format(instance_name))


    if isinstance(additional_args, tuple):
        additional_args = list(additional_args)
    if len(additional_args) == 1 and isinstance(additional_args[0], (list, tuple)):
        additional_args = [str(arg) for arg in additional_args[0]]
    else:
        additional_args = [str(arg) for arg in additional_args]

    if transformer.endswith('.py'):
        cmd = ['python', transformer, input_file, output_file] + list(additional_args)
    else:
        cmd = [transformer, input_file, output_file] + list(additional_args)

    with open(log_file, 'w') as f_out:
        process = Popen(cmd, stdout=PIPE, stderr=STDOUT, universal_newlines=True)

        def kill_process():
            process.kill()
            print("Timeout for {}".format(instance_name))

        signal.signal(signal.SIGALRM, lambda signum, frame: kill_process())
        signal.alarm(cutoff_time)

        try:
            for line in iter(process.stdout.readline, ''):
                print(line.strip(), file=f_out)
        finally:
            signal.alarm(0)


def read_name_list(name_list_file):
    with open(name_list_file, 'r') as f:
        return set(line.strip() for line in f)

def get_item_under_dir(inputPath, allowed_names=None):
    instances = []
    for item in os.listdir(inputPath):
        item_path = os.path.join(inputPath, item)
        if os.path.isfile(item_path) and (allowed_names is None or os.path.basename(item_path) in allowed_names):
            instances.append(item_path)
        elif os.path.isdir(item_path):
            instances.extend(get_item_under_dir(item_path, allowed_names))
    return instances

def goTransformer(nbCPU, cutoffTime, transformer, old_format_dir, new_format_dir, outputRoot, name_list_file,
                  suffix, result_dir_name, old_suffix, new_suffix, *additional_args):
    transformer_name = os.path.splitext(os.path.basename(transformer))[0]
    dataset_name = os.path.basename(os.path.normpath(old_format_dir))

    allowed_names = read_name_list(name_list_file) if name_list_file else None

    if not os.path.exists(old_format_dir):
        print("Input directory does not exist.")
        return

    if not os.path.exists(new_format_dir):
        os.makedirs(new_format_dir)

    if result_dir_name:
        output_dir = os.path.join(outputRoot, result_dir_name)
    else:
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        if suffix:
            output_dir = os.path.join(outputRoot, f"result-{transformer_name}-{dataset_name}-{suffix}-{timestamp}")
        else:
            output_dir = os.path.join(outputRoot, f"result-{transformer_name}-{dataset_name}-{timestamp}")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    input_files = []
    for item in get_item_under_dir(old_format_dir, allowed_names):
        if item.endswith(old_suffix) and (allowed_names is None or os.path.basename(item) in allowed_names):
            input_files.append(item)

    pool = multiprocessing.Pool(nbCPU)
    jobs = []
    for id, input_file in enumerate(input_files):
        output_file = os.path.join(new_format_dir, os.path.splitext(os.path.basename(input_file))[0] + new_suffix)
        jobs.append(pool.apply_async(worker, (id, transformer, input_file, output_file, output_dir, cutoffTime, additional_args)))

    for job in jobs:
        job.get()
    pool.close()
    pool.join()

    print("All transformations are completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run goTransformer with specified parameters.")
    parser.add_argument("nbCPU", type=int, help="Number of CPUs to use")
    parser.add_argument("cutoffTime", type=int, help="Cutoff time")
    parser.add_argument("transformer", help="Transformer to use")
    parser.add_argument("old_format_dir", help="Directory containing input files")
    parser.add_argument("new_format_dir", help="Directory for output files")
    parser.add_argument("outputRoot", help="Root for output files")
    parser.add_argument("old_suffix", help="Suffix of input files")
    parser.add_argument("new_suffix", help="Suffix for output files")
    parser.add_argument("--name_list", help="Path to a text file containing allowed file names")
    parser.add_argument("--suffix", help="Suffix for the generated result directory")
    parser.add_argument("--result_dir_name", help="Specify a custom name for the result directory")

    args, solver_args = parser.parse_known_args()

    goTransformer(args.nbCPU, args.cutoffTime, args.transformer, args.old_format_dir, args.new_format_dir,
                  args.outputRoot, args.name_list, args.suffix, args.result_dir_name, args.old_suffix,
                  args.new_suffix, *solver_args)
