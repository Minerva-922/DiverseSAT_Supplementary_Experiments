#!/bin/bash
#
# Master script for experiment-4 (SEv3 standalone, with RoundingSAT and
# CPLEX, full k-sweep on 299 instances).
#
# Usage:
#   ./run_all_experiments.sh prepare    # verify self-contained support files are present
#   ./run_all_experiments.sh generate   # emit SLURM scripts into transform/, jobs/, cplex/jobs/
#   ./run_all_experiments.sh submit     # sbatch everything
#   ./run_all_experiments.sh sumup      # aggregate results into CSV
#   ./run_all_experiments.sh summary    # print experiment configuration
#   ./run_all_experiments.sh test       # run the Python self-test
#
# If no argument is given, "prepare + generate + summary" is executed.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

step() {
    echo ""
    echo "================================================================"
    echo "== $1"
    echo "================================================================"
}

# 历史版本会从 ../experiment-1/ 或 ../experiment-2-k=3,4/ 跨目录拷贝
# 支持脚本 (goTransformer.py / goSolver.py / sumup.py / 299_instances.txt)。
# 现在所有需要的文件都已经物理复制到 experiment-4-SEv3/ 自身的目录下并 commit，
# 因此 prepare 只做存在性校验 —— 不再动 ../experiment-* 的任何东西。
do_prepare() {
    step "[prepare] Verifying self-contained support files"
    local missing=0 f
    for f in \
        transform/goTransformer.py \
        transform/genearte_scripts.py \
        transform/299_instances.txt \
        jobs/goSolver.py \
        jobs/genearte_scripts_jobs.py \
        jobs/299_instances.txt \
        sumup/sumup.py \
        cplex/jobs/goSolver.py \
        cplex/jobs/genearte_scripts_jobs.py \
        cplex/jobs/299_instances.txt \
        cplex/sumup/sumup.py
    do
        if [ -f "$f" ]; then
            echo "  [ok] $f"
        else
            echo "  [MISSING] $f"
            missing=$((missing + 1))
        fi
    done
    if [ "$missing" -gt 0 ]; then
        echo ""
        echo "  !! $missing 个支持文件缺失 —— 请先 git pull（此实验目录现在应自包含，"
        echo "     不再从 ../experiment-1 / ../experiment-2-k=3,4 拷贝）"
        exit 1
    fi
}

do_generate() {
    step "[generate] SLURM transform scripts (CNF -> OPB)"
    ( cd transform && python3 genearte_scripts.py )
    step "[generate] SLURM solve scripts (RoundingSAT)"
    ( cd jobs && python3 genearte_scripts_jobs.py )
    step "[generate] SLURM solve scripts (CPLEX)"
    ( cd cplex/jobs && python3 genearte_scripts_jobs.py )
}

do_submit() {
    step "[submit] transform jobs"
    ( cd transform && bash submit_all.sh )
    step "[submit] solve jobs (RoundingSAT)"
    ( cd jobs && bash submit_all.sh )
    step "[submit] solve jobs (CPLEX)"
    ( cd cplex/jobs && bash submit_all.sh )
}

do_sumup() {
    step "[sumup] aggregating RoundingSAT results"
    ( cd sumup && python3 sumup.py )
    step "[sumup] aggregating CPLEX results"
    ( cd cplex/sumup && python3 sumup.py )
}

do_test() {
    step "[test] self-test on tiny synthetic CNFs"
    python3 tests/self_test.py
}

do_summary() {
    step "experiment-4 Summary"
    echo "  Goal: evaluate SEv3 (\"square binary clauses\", per the PDF"
    echo "  materials/14-symmetry_elimination.pdf Version 3) as a"
    echo "  standalone, lightweight partial symmetry breaker."
    echo ""
    echo "  What we run:"
    echo "    RoundingSAT: OH / UNA / BIN"
    echo "    CPLEX:       QP / DW / IW / BIN"
    echo "    k:           {2, 3, 4, 5, 10}   SE mode: SEv3 alone (no SEv1)"
    echo ""
    echo "  SEv3 working definition (see transformers/_pbo_io.py):"
    echo "    V_{j,j} -> V_{i,j}     for j in {1..K-1}, i in {j+1..K}"
    echo "       i.e.  K*(K-1)/2 binary clauses  (~V_{j,j} OR V_{i,j})"
    echo ""
    echo "  Comparison baseline: same configurations from experiment-1 /"
    echo "  experiment-2 with SEv1 alone, and experiment-3 with SEv1XOR."
    echo ""
    echo "  Total jobs:"
    echo "    transform:          3 (encodings) * 5 (k) = 15"
    echo "    solve/RoundingSAT:  3 (encodings) * 5 (k) = 15"
    echo "    solve/CPLEX:        4 (encodings) * 5 (k) = 20"
    echo "    grand total                               = 50"
}

case "${1:-all}" in
    prepare)  do_prepare ;;
    generate) do_generate ;;
    submit)   do_submit ;;
    sumup)    do_sumup ;;
    summary)  do_summary ;;
    test)     do_test ;;
    all)      do_prepare; do_generate; do_summary ;;
    *) echo "Unknown command: $1. Use {prepare|generate|submit|sumup|summary|test|all}." >&2; exit 1 ;;
esac
