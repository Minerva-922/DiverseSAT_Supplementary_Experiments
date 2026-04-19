#!/usr/bin/env python3
"""
Generate SLURM solve-job scripts for GaussMaxHS on the CNF+XOR files
produced by ../transform/ (experiment-2, k in {3, 4}).

The GaussMaxHS binary is expected to live at
``/users/scherif/ComputeSpace/DiverseSAT/solvers/gaussmaxhs/maxhs``
(this mirrors the RoundingSAT path used elsewhere in the project — adjust
the constant below to match the actual deployment location if needed).
"""

import os
from pathlib import Path

k_values = [2, 3, 4, 5, 10]
encodes = ["OH", "UNA", "BIN"]
SE_modes = ["SEv1XOR"]
solvers = ["gaussmaxhs"]

# Path to the GaussMaxHS binary on the cluster.  The default is laid out the
# same way RoundingSAT is in experiment-1; change this before dispatching.
GAUSSMAXHS_BIN = "/users/scherif/ComputeSpace/DiverseSAT/solvers/gaussmaxhs/maxhs"

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
echo "SLURM_SUBMIT_DIR             =   $SLURM_SUBMIT_DIR"
echo "SLURM_JOBID                  =   $SLURM_JOBID"
echo "-----------------------------------------------------------"
k_value="{k_value}"
encode="{encode}"
SE_mode="{SE_mode}"
solver="{solver}"
key_word="k_${{k_value}}-${{encode}}-${{SE_mode}}"
python ./goSolver.py {parallel_num} 10000 {solver_bin} ../benchmarks/$key_word ./results
"""


def job_name(k, enc, se, solver):
    enc_map = {"OH": "O", "UNA": "U", "BIN": "B"}
    return f"{k}{enc_map.get(enc, enc[0])}xG"


def script_filename(k, enc, se, solver):
    return f"jobslurm-{k}_{enc}_{se}_{solver}"


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
                        solver_bin=GAUSSMAXHS_BIN,
                    )
                    out = output_dir / name
                    with open(out, "w") as f:
                        f.write(content)
                    os.chmod(out, 0o755)
                    generated.append(name)
                    print(f"✓ Generated {name}")

    submit = output_dir / "submit_all.sh"
    with open(submit, "w") as f:
        f.write("#!/bin/bash\n")
        f.write("# GaussMaxHS solve-job submission (experiment-2, k=3,4)\n\n")
        for name in generated:
            f.write(f"sbatch {name}\nsleep 1\n\n")
    os.chmod(submit, 0o755)
    print(f"\n✓ submit_all.sh created with {len(generated)} jobs")


if __name__ == "__main__":
    main()
