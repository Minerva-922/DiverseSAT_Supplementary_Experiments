#!/usr/bin/env python3
"""
Generate SLURM RoundingSAT solve-job scripts for experiment-2 (k in {3, 4}).

This mirrors experiment-1/roundingsat/jobs/genearte_scripts_jobs.py but with
an updated k_values list so that we can obtain the missing data points for
k = 3 and k = 4. It assumes the PBO files have been produced by
`../transform/goTransformer.py` (see genearte_scripts.py in ../transform/)
and placed under `../benchmarks/k_<k>-<enc>-<SE_mode>/`.
"""

import os
from pathlib import Path

k_values = [3, 4]
# noSE dropped — see note in ../../cplex/jobs/genearte_scripts_jobs.py.
SE_modes = ["SEv1"]
encodes = ["OH", "UNA", "BIN"]
solvers = ["roundingsat"]

FEWEST_TESTS = False

SLURM_TEMPLATE = """#!/bin/sh
#SBATCH --job-name={job_name}
#SBATCH --partition=normal            # submission queue (normal or long or bigmem or bigpu or quadgpu)
#SBATCH --time=10-1:00:00            # 1-1 means one day and one hour
#SBATCH --output=slurm-%j.out        # if --error is absent, includes also the errors
#SBATCH --mem=120G    # T-tera, G-giga, M-mega
#SBATCH --nodes=1
#SBATCH --exclusive
echo "-----------------------------------------------------------"
echo "hostname                     =   $(hostname)"
echo "SLURM_JOB_NAME               =   $SLURM_JOB_NAME"
echo "SLURM_SUBMIT_DIR             =   $SLURM_SUBMIT_DIR"
echo "SLURM_JOBID                  =   $SLURM_JOBID"
echo "SLURM_JOB_ID                 =   $SLURM_JOB_ID"
echo "SLURM_NODELIST               =   $SLURM_NODELIST"
echo "SLURM_JOB_NODELIST           =   $SLURM_JOB_NODELIST"
echo "SLURM_TASKS_PER_NODE         =   $SLURM_TASKS_PER_NODE"
echo "SLURM_JOB_CPUS_PER_NODE      =   $SLURM_JOB_CPUS_PER_NODE"
echo "SLURM_TOPOLOGY_ADDR_PATTERN  = $SLURM_TOPOLOGY_ADDR_PATTERN"
echo "SLURM_TOPOLOGY_ADDR          =   $SLURM_TOPOLOGY_ADDR"
echo "SLURM_CPUS_ON_NODE           =   $SLURM_CPUS_ON_NODE"
echo "SLURM_NNODES                 =   $SLURM_NNODES"
echo "SLURM_JOB_NUM_NODES          =   $SLURM_JOB_NUM_NODES"
echo "SLURMD_NODENAME              =   $SLURMD_NODENAME"
echo "SLURM_NTASKS                 =   $SLURM_NTASKS"
echo "SLURM_NPROCS                 =   $SLURM_NPROCS"
echo "SLURM_MEM_PER_NODE           =   $SLURM_MEM_PER_NODE"
echo "SLURM_PRIO_PROCESS           =   $SLURM_PRIO_PROCESS"
echo "-----------------------------------------------------------"
k_value="{k_value}"
encode="{encode}"
SE_mode="{SE_mode}"
solver="{solver}"
key_word="k_${{k_value}}-${{encode}}-${{SE_mode}}"
{solver_command}
"""

SOLVER_COMMANDS = {
    "roundingsat": "python ./goSolver.py {parallel_num} 10000 /users/scherif/ComputeSpace/DiverseSAT/solvers/roundingsat ../benchmarks/$key_word ./results",
}


def should_skip_combination(encode, SE_mode):
    return False


def get_encode_short(encode):
    mapping = {"OH": "O", "UNA": "U", "BIN": "B"}
    return mapping.get(encode, encode[0])


def get_solver_short(solver):
    mapping = {"roundingsat": "R"}
    return mapping.get(solver, solver[0])


def generate_job_name(k_value, encode, SE_mode, solver):
    encode_short = get_encode_short(encode)
    se_version = SE_mode.replace("SE", "")
    solver_short = get_solver_short(solver)
    return f"{k_value}{encode_short}{se_version}{solver_short}"


def generate_script_filename(k_value, encode, SE_mode, solver):
    return f"jobslurm-{k_value}_{encode}_{SE_mode}_{solver}"


def get_parallel_num(k_value):
    return 10


def main():
    output_dir = Path(".")

    print(f"Generating SLURM scripts in current directory...")
    print(f"K values: {k_values}")
    print(f"Encodings: {encodes}")
    print(f"SE modes: {SE_modes}")
    print(f"Solvers: {solvers}")
    if FEWEST_TESTS:
        print(f"⚠ FEWEST_TESTS mode enabled: OH and UNA will skip noSE")
    print("-" * 90)

    generated_files = []
    skipped_count = 0

    for k_value in k_values:
        for encode in encodes:
            for SE_mode in SE_modes:
                if should_skip_combination(encode, SE_mode):
                    skipped_count += 1
                    print(f"⊗ Skipped: k={k_value}, encode={encode}, SE={SE_mode} (FEWEST_TESTS mode)")
                    continue

                for solver in solvers:
                    job_name = generate_job_name(k_value, encode, SE_mode, solver)
                    script_filename = generate_script_filename(k_value, encode, SE_mode, solver)
                    parallel_num = get_parallel_num(k_value)
                    solver_command = SOLVER_COMMANDS[solver].format(parallel_num=parallel_num)

                    script_content = SLURM_TEMPLATE.format(
                        job_name=job_name,
                        k_value=k_value,
                        encode=encode,
                        SE_mode=SE_mode,
                        solver=solver,
                        parallel_num=parallel_num,
                        solver_command=solver_command,
                    )

                    output_file = output_dir / script_filename
                    with open(output_file, 'w') as f:
                        f.write(script_content)
                    os.chmod(output_file, 0o755)

                    generated_files.append((script_filename, job_name, k_value, encode, SE_mode, solver, parallel_num))
                    print(
                        f"✓ Generated: {script_filename:45s} (job: {job_name:8s}, k={k_value:2d}, {encode:3s}, {SE_mode:4s}, {solver:11s}, p={parallel_num})")

    print("-" * 90)
    print(f"Total scripts generated: {len(generated_files)}")
    if skipped_count > 0:
        print(f"Total combinations skipped: {skipped_count}")

    submission_script = output_dir / "submit_all.sh"
    with open(submission_script, 'w') as f:
        f.write("#!/bin/bash\n")
        f.write("# Batch submission script for all generated SLURM jobs (experiment-2, k=3,4)\n")
        if FEWEST_TESTS:
            f.write("# Generated with FEWEST_TESTS mode enabled\n")
        f.write(f"# Total jobs: {len(generated_files)}\n\n")
        for filename, job_name, k_value, encode, SE_mode, solver, parallel_num in generated_files:
            f.write(
                f"echo 'Submitting {filename} (Job: {job_name}, k={k_value}, {encode}, {SE_mode}, {solver}, parallel={parallel_num})...'\n")
            f.write(f"sbatch {filename}\n")
            f.write("sleep 1\n\n")
    os.chmod(submission_script, 0o755)

    print(f"\n✓ Batch submission script created: submit_all.sh")


if __name__ == "__main__":
    main()
