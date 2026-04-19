"""
Generate SLURM transform scripts: CNF  ->  CNF+XOR WDIMACS (.wcnfxor)
for the GaussMaxHS experiments in experiment-2.

The output files are placed under ``../benchmarks/k_<k>-<enc>-SEv1XOR/``
and are then consumed by ../jobs/genearte_scripts_jobs.py.

k values covered here: 3 and 4 (matching the rest of experiment-2).
Encodings: OH, UNA, BIN — all with the new SEv1-XOR variant.
"""

import os
from pathlib import Path

k_values = [2, 3, 4, 5, 10]
encodes = ["OH", "UNA", "BIN"]
# Only SEv1XOR makes sense for GaussMaxHS: the whole point of this
# experiment is to leverage native XOR clauses. We still include a plain
# CNF baseline (no XOR) via the normal SEv1 transformer for comparison.
SE_modes = ["SEv1XOR"]

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
echo "SLURM_JOB_ID                 =   $SLURM_JOB_ID"
echo "SLURM_NODELIST               =   $SLURM_NODELIST"
echo "-----------------------------------------------------------"
k_value="{k_value}"
encode="{encode}"
SE_mode="{SE_mode}"
key_word="k_${{k_value}}-${{encode}}-${{SE_mode}}"
python ./goTransformer.py {parallel_num} 10000 ../transformers/${{encode}}_${{SE_mode}}_cnf_to_wcnfxor.py  /users/scherif/ComputeSpace/DiverseSAT/benchmarks/ ../benchmarks/$key_word  ./output-trans/ .cnf .wcnfxor  --name_list 299_instances.txt ${{k_value}}  --suffix $key_word
"""


def job_name(k, encode, se):
    enc_map = {"OH": "O", "UNA": "U", "BIN": "B"}
    return f"{k}{enc_map.get(encode, encode[0])}xG"  # 'x' = XOR, 'G' = Gauss


def script_filename(k, encode, se):
    return f"jobslurm-{k}_{encode}_{se}"


def main():
    output_dir = Path(".")
    generated = []

    for k in k_values:
        for enc in encodes:
            for se in SE_modes:
                name = script_filename(k, enc, se)
                content = SLURM_TEMPLATE.format(
                    job_name=job_name(k, enc, se),
                    k_value=k,
                    encode=enc,
                    SE_mode=se,
                    parallel_num=10,
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
        f.write("# GaussMaxHS transform submission (experiment-2)\n\n")
        for name in generated:
            f.write(f"sbatch {name}\nsleep 1\n\n")
    os.chmod(submit, 0o755)
    print(f"\n✓ submit_all.sh created with {len(generated)} jobs")


if __name__ == "__main__":
    main()
