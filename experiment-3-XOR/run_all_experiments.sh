#!/bin/bash
#
# Master script for experiment-3: native CNF+XOR MaxSAT using GaussMaxHS.
#
# This tests Sami's idea from the JAIR meeting: the Y-variable definition
#   Y_{i,j}  <->  V_{i,j} XOR V_{i+1,j}                      (SE-4)
# is written as a *native* hard XOR clause and solved by the CNF+XOR
# MaxSAT solver GaussMaxHS (https://github.com/meelgroup/gaussmaxhs),
# which performs Gauss-Jordan elimination on the XOR module on top of
# MaxHS.
#
# We call the resulting variant SEv1-XOR.
#
# Usage:
#   ./run_all_experiments.sh [all|generate|submit|sumup]
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ACTION="${1:-all}"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
step() { echo -e "\n${CYAN}========== $* ==========${NC}"; }

generate_scripts() {
    step "Step 1/2: CNF -> CNF+XOR transform SLURM scripts"
    cd "$SCRIPT_DIR/transform"
    python genearte_scripts.py

    step "Step 2/2: GaussMaxHS solve SLURM scripts"
    cd "$SCRIPT_DIR/jobs"
    python genearte_scripts_jobs.py

    log "All SLURM scripts generated."
}

submit_jobs() {
    step "Submit jobs (GaussMaxHS)"

    log "Phase A: Transform (CNF -> .wcnfxor)"
    cd "$SCRIPT_DIR/transform"
    if [ -f submit_all.sh ]; then
        read -p "  Submit transform jobs? [y/N] " ans
        [[ "$ans" =~ ^[Yy]$ ]] && bash submit_all.sh || warn "Skipped."
    else
        warn "Run 'generate' first."
    fi

    log "Phase B: Solve (.wcnfxor -> results)"
    cd "$SCRIPT_DIR/jobs"
    if [ -f submit_all.sh ]; then
        read -p "  Submit GaussMaxHS solve jobs? [y/N] " ans
        [[ "$ans" =~ ^[Yy]$ ]] && bash submit_all.sh || warn "Skipped."
    fi
}

sumup_results() {
    step "Aggregating GaussMaxHS results"
    cd "$SCRIPT_DIR/sumup" && python sumup.py || warn "sumup had errors."
}

print_summary() {
    step "experiment-3 Summary"
    echo "  Solver   : GaussMaxHS (CNF+XOR MaxSAT)"
    echo "  SE mode  : SEv1-XOR  (SE-4 as native hard XOR clauses, SE-5 kept)"
    echo "  Encodings: OH, UNA, BIN"
    echo "  k values : 3, 4  (for comparability with experiment-2;"
    echo "                    extend k_values in transform/jobs scripts as needed)"
    echo ""
    echo "  Total    : 6 transform + 6 solve = 12 SLURM tasks."
}

case "$ACTION" in
    generate) generate_scripts; print_summary ;;
    submit)   submit_jobs ;;
    sumup)    sumup_results ;;
    all)      generate_scripts; print_summary; submit_jobs ;;
    *)
        echo "Usage: $0 {all|generate|submit|sumup}"; exit 1 ;;
esac

log "Done."
