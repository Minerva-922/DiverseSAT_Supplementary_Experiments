#!/bin/bash
#
# Master script for experiment-4 (SEv3 as a redundant constraint on
# top of SEv1, RoundingSAT, preliminary tests on k in {2, 3, 5}).
#
# Usage:
#   ./run_all_experiments.sh prepare    # copy support scripts + instance list
#   ./run_all_experiments.sh generate   # emit SLURM scripts into transform/ and jobs/
#   ./run_all_experiments.sh submit     # sbatch everything
#   ./run_all_experiments.sh sumup      # aggregate results into CSV
#   ./run_all_experiments.sh summary    # print experiment configuration
#   ./run_all_experiments.sh test       # run the Python self-test
#
# If no argument is given, "prepare + generate + summary" is executed.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

EXP1_ROOT="${EXP1_ROOT:-../experiment-1}"
EXP2_ROOT="${EXP2_ROOT:-../experiment-2}"

step() {
    echo ""
    echo "================================================================"
    echo "== $1"
    echo "================================================================"
}

do_prepare() {
    step "[prepare] Copying goTransformer / goSolver / 299_instances / sumup"
    # Prefer experiment-2 copies (k=3,4), fall back to experiment-1.
    for src in "$EXP2_ROOT" "$EXP1_ROOT"; do
        if [ -f "$src/roundingsat/transform/goTransformer.py" ]; then
            cp -n "$src/roundingsat/transform/goTransformer.py" transform/
            cp -n "$src/roundingsat/transform/299_instances.txt"    transform/
            cp -n "$src/roundingsat/jobs/goSolver.py"               jobs/
            cp -n "$src/roundingsat/jobs/299_instances.txt"         jobs/
            cp -n "$src/roundingsat/sumup/sumup.py"                 sumup/
            echo "  [ok] copied support files from $src"
            break
        fi
    done
}

do_generate() {
    step "[generate] SLURM transform scripts (CNF -> OPB)"
    ( cd transform && python3 genearte_scripts.py )
    step "[generate] SLURM solve scripts (RoundingSAT)"
    ( cd jobs && python3 genearte_scripts_jobs.py )
}

do_submit() {
    step "[submit] transform jobs"
    ( cd transform && bash submit_all.sh )
    step "[submit] solve jobs"
    ( cd jobs && bash submit_all.sh )
}

do_sumup() {
    step "[sumup] aggregating results"
    ( cd sumup && python3 sumup.py )
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
    echo "    Solver:  RoundingSAT     Encodings: OH / UNA / BIN"
    echo "    k:       {2, 3, 4, 5, 10}   SE mode:  SEv3 alone (no SEv1)"
    echo ""
    echo "  SEv3 working definition (see transformers/_pbo_io.py):"
    echo "    V_{j,j} -> V_{i,j}     for j in {1..K-1}, i in {j+1..K}"
    echo "       i.e.  K*(K-1)/2 binary clauses  (~V_{j,j} OR V_{i,j})"
    echo ""
    echo "  Comparison baseline: same configurations from experiment-1 /"
    echo "  experiment-2 with SEv1 alone, and experiment-3 with SEv1XOR."
    echo ""
    echo "  Total jobs:"
    echo "    transform: 3 (encodings) * 5 (k)           = 15"
    echo "    solve:     3 (encodings) * 5 (k) * 1 (slv) = 15"
    echo "    grand total                                 = 30"
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
