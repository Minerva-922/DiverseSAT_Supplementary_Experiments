import os
from pathlib import Path

# Configuration
k_values = [2, 5, 10]
SE_modes = ["noSE", "SEv1"]
encodes = ["OH", "UNA", "BIN"]

# Special mode: when enabled, OH and UNA only encode with SEv1 (skip noSE)
# BIN still encodes with both SEv1 and noSE
FEWEST_TESTS = True  # Set to True to enable minimal testing mode


def should_skip_combination(encode, SE_mode):
    """
    Check if a combination should be skipped based on FEWEST_TESTS mode
    """
    if not FEWEST_TESTS:
        return False

    # In FEWEST_TESTS mode: OH and UNA skip noSE (only encode SEv1)
    if encode in ["OH", "UNA"] and SE_mode == "noSE":
        return True

    return False


# Template for the SLURM script
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
key_word="k_${{k_value}}-${{encode}}-${{SE_mode}}"
python ./goTransformer.py {parallel_num} 10000 ../transformers/${{encode}}_${{SE_mode}}_cnf_to_PBO.py  /users/scherif/ComputeSpace/DiverseSAT/benchmarks/ ../benchmarks/$key_word  ./output-trans/ .cnf .pbo  --name_list 299_instances.txt ${{k_value}}  --suffix $key_word
"""


def generate_job_name(k_value, encode, SE_mode):
    """
    Generate job name in the format: {k}{encode_short}{SE_version}
    e.g., 5Uv1, 10Ov0, 20Bv1
    encode_short: OH->O, UNA->U, BIN->B
    SE_version: noSE->v0, SEv1->v1
    """
    encode_map = {"OH": "O", "UNA": "U", "BIN": "B"}
    encode_short = encode_map.get(encode, encode[0])

    if SE_mode == "noSE":
        se_version = "v0"
    else:
        se_version = SE_mode.replace("SE", "")

    return f"{k_value}{encode_short}{se_version}"


def generate_script_filename(k_value, encode, SE_mode):
    """
    Generate script filename in the format: jobslurm-{k}_{encode}_{SE_mode}
    e.g., jobslurm-5_UNA_SEv1, jobslurm-10_OH_noSE
    """
    return f"jobslurm-{k_value}_{encode}_{SE_mode}"


def get_parallel_num(k_value):
    """
    Determine the parallel number based on k value
    k=5: parallel_num=10
    k=10 or k=20: parallel_num=2
    """
    if k_value > 5:
        return 2
    else:
        return 10


def main():
    output_dir = Path(".")

    print(f"Generating SLURM scripts in current directory...")
    print(f"K values: {k_values}")
    print(f"Encodes: {encodes}")
    print(f"SE modes: {SE_modes}")
    print("-" * 70)

    generated_files = []

    skipped = 0

    for k_value in k_values:
        for encode in encodes:
            for SE_mode in SE_modes:
                if should_skip_combination(encode, SE_mode):
                    skipped += 1
                    print(f"  Skipped: k={k_value}, encode={encode}, SE_mode={SE_mode} (FEWEST_TESTS)")
                    continue

                job_name = generate_job_name(k_value, encode, SE_mode)
                script_filename = generate_script_filename(k_value, encode, SE_mode)
                parallel_num = get_parallel_num(k_value)

                script_content = SLURM_TEMPLATE.format(
                    job_name=job_name,
                    k_value=k_value,
                    encode=encode,
                    SE_mode=SE_mode,
                    parallel_num=parallel_num
                )

                output_file = output_dir / script_filename
                with open(output_file, 'w') as f:
                    f.write(script_content)

                os.chmod(output_file, 0o755)

                generated_files.append((script_filename, job_name, k_value, encode, parallel_num))
                print(
                    f"✓ Generated: {script_filename:40s} (job: {job_name:6s}, k={k_value:2d}, encode={encode:3s}, parallel={parallel_num})")

    print("-" * 70)
    print(f"Total scripts generated: {len(generated_files)}, skipped: {skipped}")

    print(f"\n{'Filename':<40s} {'Job Name':<10s} {'K':<5s} {'Encode':<8s} {'Parallel'}")
    print("-" * 70)
    for filename, job_name, k_value, encode, parallel_num in generated_files:
        print(f"{filename:<40s} {job_name:<10s} {k_value:<5d} {encode:<8s} {parallel_num}")

    submission_script = output_dir / "submit_all.sh"
    with open(submission_script, 'w') as f:
        f.write("#!/bin/bash\n")
        f.write("# Batch submission script for all generated SLURM jobs\n\n")
        for filename, job_name, k_value, encode, parallel_num in generated_files:
            f.write(
                f"echo 'Submitting {filename} (Job: {job_name}, k={k_value}, encode={encode}, parallel={parallel_num})...'\n")
            f.write(f"sbatch {filename}\n")
            f.write("sleep 1\n\n")

    os.chmod(submission_script, 0o755)
    print(f"\n✓ Batch submission script created: submit_all.sh")
    print(f"\nTo submit all jobs, run:")
    print(f"  ./submit_all.sh")

    print(f"\nOr submit individually:")
    for filename, job_name, _, _, _ in generated_files[:3]:
        print(f"  sbatch {filename}")
    if len(generated_files) > 3:
        print(f"  ...")


if __name__ == "__main__":
    main()
