#!/usr/bin/env python3
"""
Generate SLURM RoundingSAT solve-job scripts for experiment-5.

Assumes the OPB files produced by ``../transform/`` already live under
``../benchmarks/k_<k>-<enc>-SEv1v3/``.
"""

import os
from pathlib import Path

k_values = [2, 3, 4, 5, 10]
encodes = ["OH", "UNA", "BIN"]
SE_modes = ["SEv1v3"]
solvers = ["roundingsat"]

SLURM_TEMPLATE = """#!/bin/sh
#SBATCH --job-name={job_name}
#SBATCH --partition=normal
#SBATCH --time=10-1:00:00
#SBATCH --output=slurm-%j.out
#SBATCH --mem=120G
#SBATCH --nodes=1
#SBATCH --exclusive
echo "-----------------------------------------------------------"
echo "hostname                     =   $(hostname)"
echo "SLURM_JOB_NAME               =   $SLURM_JOB_NAME"
echo "SLURM_JOBID                  =   $SLURM_JOBID"
echo "-----------------------------------------------------------"
k_value="{k_value}"
encode="{encode}"
SE_mode="{SE_mode}"
solver="{solver}"
key_word="k_${{k_value}}-${{encode}}-${{SE_mode}}"
python ./goSolver.py {parallel_num} 10000 /users/scherif/ComputeSpace/DiverseSAT/solvers/roundingsat ../benchmarks/$key_word ./results --suffix $key_word
"""


def job_name(k, encode, se, solver):
    enc_map = {"OH": "O", "UNA": "U", "BIN": "B"}
    se_tag = {"SEv1v3": "v13"}[se]
    return f"{k}{enc_map.get(encode, encode[0])}{se_tag}R"


def script_filename(k, encode, se, solver):
    return f"jobslurm-{k}_{encode}_{se}_{solver}"


def main():
    output_dir = Path(".")
    generated = []
    for k in k_values:
        for enc in encodes:
            for se in SE_modes:
                for solver in solvers:
                    name = script_filename(k, enc, se, solver)
                    content = SLURM_TEMPLATE.format(
                        job_name=job_name(k, enc, se, solver),
                        k_value=k,
                        encode=enc,
                        SE_mode=se,
                        solver=solver,
                        parallel_num=10,
                    )
                    out = output_dir / name
                    with open(out, "w") as f:
                        f.write(content)
                    os.chmod(out, 0o755)
                    generated.append(name)
                    print(f"[ok] generated {name}")

    submit = output_dir / "submit_all.sh"
    with open(submit, "w") as f:
        f.write("#!/bin/bash\n")
        f.write("# experiment-5 RoundingSAT submission (SEv1 + SEv3 heuristic overlay)\n")
        f.write(f"# Total jobs: {len(generated)}\n\n")
        for name in generated:
            f.write(f"sbatch {name}\nsleep 1\n\n")
    os.chmod(submit, 0o755)
    print(f"\n[ok] submit_all.sh created with {len(generated)} jobs")


if __name__ == "__main__":
    main()
