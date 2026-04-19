#!/bin/bash
#
# Master script for experiment-2: extend experiment-1 with k = 3 and k = 4.
#
# This folder mirrors the layout of experiment-1 (CPLEX + RoundingSAT), but
# the generators only emit scripts for k in {3, 4}. Everything else — the
# encodings (QP/DW/IW/BIN for CPLEX, OH/UNA/BIN for RoundingSAT), the
# FEWEST_TESTS policy, and the SLURM templates — is identical to
# experiment-1, so the two sets of results can be concatenated directly.
#
# Usage:
#   ./run_all_experiments.sh              # Generate scripts + submit
#   ./run_all_experiments.sh generate     # Only generate SLURM scripts
#   ./run_all_experiments.sh submit       # Only submit (assumes generated)
#   ./run_all_experiments.sh sumup        # Only aggregate results into CSV
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
    step "Step 1/3: RoundingSAT Transform SLURM scripts (k=3,4)"
    cd "$SCRIPT_DIR/roundingsat/transform"
    python genearte_scripts.py

    step "Step 2/3: RoundingSAT Solve SLURM scripts (k=3,4)"
    cd "$SCRIPT_DIR/roundingsat/jobs"
    python genearte_scripts_jobs.py

    step "Step 3/3: CPLEX SLURM scripts (k=3,4)"
    cd "$SCRIPT_DIR/cplex/jobs"
    python genearte_scripts_jobs.py

    log "All SLURM scripts generated."
}

submit_jobs() {
    step "Submit jobs (k=3,4)"

    echo ""
    log "Phase A: RoundingSAT Transform (CNF -> PBO)"
    cd "$SCRIPT_DIR/roundingsat/transform"
    if [ -f submit_all.sh ]; then
        read -p "  Submit RoundingSAT transform jobs? [y/N] " ans
        [[ "$ans" =~ ^[Yy]$ ]] && bash submit_all.sh || warn "Skipped."
    else
        warn "Run 'generate' first."
    fi

    echo ""
    log "Phase B: RoundingSAT Solve (PBO -> results)"
    cd "$SCRIPT_DIR/roundingsat/jobs"
    if [ -f submit_all.sh ]; then
        read -p "  Submit RoundingSAT solve jobs? [y/N] " ans
        [[ "$ans" =~ ^[Yy]$ ]] && bash submit_all.sh || warn "Skipped."
    fi

    echo ""
    log "Phase C: CPLEX (CNF -> results)"
    cd "$SCRIPT_DIR/cplex/jobs"
    if [ -f submit_all.sh ]; then
        read -p "  Submit CPLEX jobs? [y/N] " ans
        [[ "$ans" =~ ^[Yy]$ ]] && bash submit_all.sh || warn "Skipped."
    fi
}

sumup_results() {
    step "Aggregating Results (k=3,4)"

    log "RoundingSAT..."
    cd "$SCRIPT_DIR/roundingsat/sumup" && python sumup.py || warn "RoundingSAT sumup had errors."

    log "CPLEX..."
    cd "$SCRIPT_DIR/cplex/sumup" && python sumup.py || warn "CPLEX sumup had errors."
}

print_summary() {
    step "experiment-2 Summary"
    echo "  Purpose: supplement experiment-1 (k=2,5,10) with k=3 and k=4."
    echo "  noSE is dropped — per the JAIR meeting, it is no longer the"
    echo "  same problem once uniqueness is part of the definition."
    echo ""
    echo "  CPLEX experiments  (8 SLURM tasks):"
    echo "    QP-SE / DW-SE / IW-SE / BIN-SE    for k = 3, 4"
    echo ""
    echo "  RoundingSAT experiments (6+6 = 12 SLURM tasks):"
    echo "    OH-SEv1 / UNA-SEv1 / BIN-SEv1     for k = 3, 4"
    echo "    (transform + solve per configuration)"
    echo ""
    echo "  Total: 20 SLURM tasks."
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
