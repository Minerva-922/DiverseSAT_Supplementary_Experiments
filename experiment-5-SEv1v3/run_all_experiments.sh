#!/bin/bash
#
# Master script for experiment-5 (SEv1 + SEv3 *heuristic overlay*,
# RoundingSAT, full k-sweep on 299 instances).
#
# IMPORTANT: the SEv1v3 overlay is NOT a sound symmetry-breaking scheme
# (see README.md and v2.tex Remark rem:diagonal-vs-lex).  Results from
# this experiment are reported as a speculative heuristic complement
# to experiment-4's SEv3-standalone configuration.
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
EXP2_ROOT="${EXP2_ROOT:-../experiment-2-k=3,4}"
EXP4_ROOT="${EXP4_ROOT:-../experiment-4-SEv3}"

step() {
    echo ""
    echo "================================================================"
    echo "== $1"
    echo "================================================================"
}

do_prepare() {
    step "[prepare] Copying goTransformer / goSolver / 299_instances / sumup"
    # Prefer exp-4 (same layout as this experiment); fall back to exp-2/1.
    for src in "$EXP4_ROOT" "$EXP2_ROOT" "$EXP1_ROOT"; do
        # exp-4 exposes files directly, exp-1/2 nest them under roundingsat/.
        if [ -f "$src/transform/goTransformer.py" ]; then
            cp -n "$src/transform/goTransformer.py" transform/
            cp -n "$src/transform/299_instances.txt" transform/
            cp -n "$src/jobs/goSolver.py"           jobs/
            cp -n "$src/jobs/299_instances.txt"     jobs/
            if [ -f "$src/sumup/sumup.py" ]; then
                cp -n "$src/sumup/sumup.py" sumup/
            fi
            echo "  [ok] copied support files from $src (flat layout)"
            break
        elif [ -f "$src/roundingsat/transform/goTransformer.py" ]; then
            cp -n "$src/roundingsat/transform/goTransformer.py" transform/
            cp -n "$src/roundingsat/transform/299_instances.txt" transform/
            cp -n "$src/roundingsat/jobs/goSolver.py"           jobs/
            cp -n "$src/roundingsat/jobs/299_instances.txt"     jobs/
            cp -n "$src/roundingsat/sumup/sumup.py"             sumup/
            echo "  [ok] copied support files from $src (nested layout)"
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
    step "experiment-5 Summary"
    echo "  Goal: evaluate the **SEv1 + SEv3 heuristic overlay** --"
    echo "  SEv3's diagonal-dominance binary clauses conjoined on top of"
    echo "  SEv1's strict-lex module -- as a speculative complement to"
    echo "  experiment-4's SEv3-standalone configuration."
    echo ""
    echo "  WARNING: this overlay is NOT a sound symmetry-breaking scheme"
    echo "  (see README.md and v2.tex Remark rem:diagonal-vs-lex)."
    echo "  Expect some instances to flip to UNSAT or to report strictly"
    echo "  suboptimal diversity -- such behaviour is the object of study."
    echo ""
    echo "  What we run:"
    echo "    Solver:  RoundingSAT     Encodings: OH / UNA / BIN"
    echo "    k:       {2, 3, 4, 5, 10}   SE mode:  SEv1v3 overlay"
    echo ""
    echo "  SEv1v3 working definition:"
    echo "    SEv1  strict-lex chain on C_{i,j}     ((K-1)*(3N-1) clauses)"
    echo "    SEv3  V_{j,j} -> V_{i,j} binaries      (K*(K-1)/2 clauses)"
    echo ""
    echo "  Comparison baselines:"
    echo "    exp-1 / exp-2  :  SEv1 alone    (sound baseline)"
    echo "    exp-4          :  SEv3 alone    (sound standalone substitute)"
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
