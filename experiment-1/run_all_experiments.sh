#!/bin/bash
#
# Master script to run all DiverseSAT added experiments on the SLURM cluster.
#
# Usage:
#   ./run_all_experiments.sh              # Run all steps (generate scripts + submit)
#   ./run_all_experiments.sh generate     # Only generate SLURM scripts (no submission)
#   ./run_all_experiments.sh submit       # Only submit (assumes scripts already generated)
#   ./run_all_experiments.sh sumup        # Only aggregate results into CSV
#
# Prerequisites:
#   - Python 3 with: pysat, cplex, psutil
#   - RoundingSAT binary at /users/scherif/ComputeSpace/DiverseSAT/solvers/roundingsat
#   - Benchmark CNF files at /users/scherif/ComputeSpace/DiverseSAT/benchmarks/
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

# ──────────────────────────────────────────────
# Step 1: Generate SLURM scripts
# ──────────────────────────────────────────────
generate_scripts() {
    step "Step 1/4: Generate RoundingSAT Transform SLURM Scripts"
    cd "$SCRIPT_DIR/roundingsat/transform"
    python3 genearte_scripts.py
    log "Transform scripts generated in: $(pwd)"

    step "Step 2/4: Generate RoundingSAT Solve SLURM Scripts"
    cd "$SCRIPT_DIR/roundingsat/jobs"
    python3 genearte_scripts_jobs.py
    log "Solve scripts generated in: $(pwd)"

    step "Step 3/4: Generate CPLEX SLURM Scripts"
    cd "$SCRIPT_DIR/cplex/jobs"
    python3 genearte_scripts_jobs.py
    log "CPLEX scripts generated in: $(pwd)"

    log "All SLURM scripts generated successfully."
}

# ──────────────────────────────────────────────
# Step 2: Submit all SLURM jobs
# ──────────────────────────────────────────────
submit_jobs() {
    step "Step 4/4: Submit All SLURM Jobs"

    echo ""
    log "Phase A: RoundingSAT Transform (CNF -> PBO)"
    cd "$SCRIPT_DIR/roundingsat/transform"
    if [ -f submit_all.sh ]; then
        echo "  Scripts to submit:"
        ls jobslurm-* 2>/dev/null | while read f; do echo "    $f"; done
        echo ""
        read -p "  Submit RoundingSAT transform jobs? [y/N] " ans
        if [[ "$ans" =~ ^[Yy]$ ]]; then
            bash submit_all.sh
            log "RoundingSAT transform jobs submitted."
        else
            warn "Skipped RoundingSAT transform submission."
        fi
    else
        warn "No submit_all.sh found. Run 'generate' first."
    fi

    echo ""
    log "Phase B: RoundingSAT Solve (PBO -> results)"
    cd "$SCRIPT_DIR/roundingsat/jobs"
    if [ -f submit_all.sh ]; then
        echo "  Scripts to submit:"
        ls jobslurm-* 2>/dev/null | while read f; do echo "    $f"; done
        echo ""
        read -p "  Submit RoundingSAT solve jobs? [y/N] " ans
        if [[ "$ans" =~ ^[Yy]$ ]]; then
            bash submit_all.sh
            log "RoundingSAT solve jobs submitted."
        else
            warn "Skipped RoundingSAT solve submission."
        fi
    else
        warn "No submit_all.sh found. Run 'generate' first."
    fi

    echo ""
    log "Phase C: CPLEX Solve (CNF -> results)"
    cd "$SCRIPT_DIR/cplex/jobs"
    if [ -f submit_all.sh ]; then
        echo "  Scripts to submit:"
        ls jobslurm-* 2>/dev/null | while read f; do echo "    $f"; done
        echo ""
        read -p "  Submit CPLEX jobs? [y/N] " ans
        if [[ "$ans" =~ ^[Yy]$ ]]; then
            bash submit_all.sh
            log "CPLEX jobs submitted."
        else
            warn "Skipped CPLEX submission."
        fi
    else
        warn "No submit_all.sh found. Run 'generate' first."
    fi

    echo ""
    log "All submissions complete. Use 'squeue -u \$USER' to monitor."
}

# ──────────────────────────────────────────────
# Step 3: Aggregate results
# ──────────────────────────────────────────────
sumup_results() {
    step "Aggregating Results"

    echo ""
    log "Aggregating RoundingSAT results..."
    cd "$SCRIPT_DIR/roundingsat/sumup"
    python3 sumup.py || warn "RoundingSAT sumup encountered errors (results may be incomplete)."

    echo ""
    log "Aggregating CPLEX results..."
    cd "$SCRIPT_DIR/cplex/sumup"
    python3 sumup.py || warn "CPLEX sumup encountered errors (results may be incomplete)."

    log "Result aggregation complete."
    log "  RoundingSAT CSVs: $SCRIPT_DIR/roundingsat/sumup/results/"
    log "  CPLEX CSVs:       $SCRIPT_DIR/cplex/sumup/results/"
}

# ──────────────────────────────────────────────
# Summary / help
# ──────────────────────────────────────────────
print_summary() {
    step "Experiment Summary"
    echo ""
    echo "  CPLEX experiments (15 SLURM tasks):"
    echo "    QP-SE:   k = 2, 5, 10"
    echo "    DW-SE:   k = 2, 5, 10"
    echo "    IW-SE:   k = 2, 5, 10"
    echo "    BIN-SE:  k = 2, 5, 10"
    echo "    BIN-noSE: k = 2, 5, 10"
    echo ""
    echo "  RoundingSAT experiments (12+12 = 24 SLURM tasks):"
    echo "    Transform + Solve:"
    echo "      OH-SEv1:  k = 2, 5, 10"
    echo "      UNA-SEv1: k = 2, 5, 10"
    echo "      BIN-noSE: k = 2, 5, 10"
    echo "      BIN-SEv1: k = 2, 5, 10"
    echo ""
    echo "  Total: 39 SLURM tasks"
    echo ""
    echo "  Workflow:"
    echo "    1. generate  - Generate all SLURM scripts"
    echo "    2. submit    - Submit jobs to cluster"
    echo "       Note: RoundingSAT transform must finish before solve!"
    echo "    3. sumup     - Aggregate results into CSV after completion"
    echo ""
}

# ──────────────────────────────────────────────
# Main dispatch
# ──────────────────────────────────────────────
case "$ACTION" in
    generate)
        generate_scripts
        print_summary
        ;;
    submit)
        submit_jobs
        ;;
    sumup)
        sumup_results
        ;;
    all)
        generate_scripts
        print_summary
        submit_jobs
        ;;
    *)
        echo "Usage: $0 {all|generate|submit|sumup}"
        echo ""
        echo "  all       Generate scripts and submit (default)"
        echo "  generate  Only generate SLURM scripts"
        echo "  submit    Only submit (assumes scripts already generated)"
        echo "  sumup     Aggregate results into CSV"
        exit 1
        ;;
esac

log "Done."
