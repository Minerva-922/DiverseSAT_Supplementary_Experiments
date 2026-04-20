#!/usr/bin/env python3
"""
Generate SLURM transform scripts (CNF -> OPB) for experiment-5.

experiment-5 studies the **SEv1 + SEv3 heuristic overlay** -- i.e.
SEv3's diagonal-dominance binary clauses conjoined on top of the
SEv1 strict-lex module.  This overlay is NOT a sound replacement for
SEv1 (see v2.tex Remark ``rem:diagonal-vs-lex'': the two pick
different canonical representatives and may together make an otherwise
feasible instance UNSAT), and is reported only as a speculative
heuristic complement to experiment-4's SEv3-standalone configuration.
"""

import os
from pathlib import Path

k_values = [2, 3, 4, 5, 10]
encodes = ["OH", "UNA", "BIN"]
SE_modes = ["SEv1v3"]

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
key_word="k_${{k_value}}-${{encode}}-${{SE_mode}}"
python ./goTransformer.py {parallel_num} 10000 ../transformers/${{encode}}_${{SE_mode}}_cnf_to_PBO.py  /users/scherif/ComputeSpace/DiverseSAT/benchmarks/ ../benchmarks/$key_word  ./output-trans/ .cnf .pbo  --name_list 299_instances.txt ${{k_value}}  --suffix $key_word
"""


def job_name(k, encode, se):
    enc_map = {"OH": "O", "UNA": "U", "BIN": "B"}
    se_tag = {"SEv1v3": "v13"}[se]
    return f"{k}{enc_map.get(encode, encode[0])}{se_tag}"


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
                print(f"[ok] generated {name}")

    submit = output_dir / "submit_all.sh"
    with open(submit, "w") as f:
        f.write("#!/bin/bash\n")
        f.write("# experiment-5 transform submission (SEv1 + SEv3 heuristic overlay)\n\n")
        for name in generated:
            f.write(f"sbatch {name}\nsleep 1\n\n")
    os.chmod(submit, 0o755)
    print(f"\n[ok] submit_all.sh created with {len(generated)} jobs")


if __name__ == "__main__":
    main()
