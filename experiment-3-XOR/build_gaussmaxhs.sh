#!/usr/bin/env bash
# =============================================================================
# Build & install GaussMaxHS on the matricsi cluster.
#
# GaussMaxHS (Soos & Meel, KR'21) is a CNF+XOR MaxSAT solver based on MaxHS;
# it links statically against IBM CPLEX and produces a binary named `maxhs`.
# The exp-3 SLURM scripts expect the binary at
#     $INSTALL_PREFIX/maxhs
# (by default `/users/scherif/ComputeSpace/DiverseSAT/solvers/gaussmaxhs/maxhs`).
#
# Usage
# -----
#   # 1. Full build on the login node (default):
#   bash build_gaussmaxhs.sh
#
#   # 2. Full build inside a SLURM job (recommended if login node restricts CPU):
#   sbatch build_gaussmaxhs.sh --as-slurm
#
#   # 3. Dry-run (print what would happen, no side effects):
#   bash build_gaussmaxhs.sh --dry-run
#
#   # 4. Custom CPLEX path:
#   CPLEX_ROOT=/opt/ibm/ILOG/CPLEX_Studio2211 bash build_gaussmaxhs.sh
#
# Exit codes
# ----------
#   0 = binary built, installed, and smoke-test passes (1 XOR + 4 CNF instance).
#   1 = configuration error (CPLEX not found, etc.) — nothing changed on disk.
#   2 = compile error — partial artefacts left under $BUILD_DIR for inspection.
#   3 = smoke-test failure (unexpected optimum or output format).
# =============================================================================

#SBATCH --job-name=build_gaussmaxhs
#SBATCH --partition=normal
#SBATCH --time=0-2:00:00
#SBATCH --output=slurm-build_gaussmaxhs-%j.out
#SBATCH --mem=16G
#SBATCH --nodes=1
#SBATCH --cpus-per-task=4

set -euo pipefail

# ----------------------------------------------------------------------------
# 1. Tunables (override via environment variables)
# ----------------------------------------------------------------------------
GIT_URL="${GIT_URL:-https://github.com/meelgroup/gaussmaxhs.git}"
GIT_REF="${GIT_REF:-master}"                                # branch or commit SHA to pin to

BUILD_ROOT="${BUILD_ROOT:-/users/scherif/ComputeSpace/DiverseSAT/build}"
BUILD_DIR="${BUILD_DIR:-${BUILD_ROOT}/gaussmaxhs}"
INSTALL_PREFIX="${INSTALL_PREFIX:-/users/scherif/ComputeSpace/DiverseSAT/solvers/gaussmaxhs}"

# CPLEX static libraries (libcplex.a, libilocplex.a) + headers (ilcplex/cplex.h).
# Leave CPLEX_LIBDIR / CPLEX_INCDIR unset to let the script auto-detect.
CPLEX_ROOT="${CPLEX_ROOT:-}"
CPLEX_LIBDIR="${CPLEX_LIBDIR:-}"
CPLEX_INCDIR="${CPLEX_INCDIR:-}"

JOBS="${JOBS:-4}"
DRY_RUN=0

# ----------------------------------------------------------------------------
# 2. CLI handling
# ----------------------------------------------------------------------------
for arg in "$@"; do
    case "$arg" in
        --dry-run)   DRY_RUN=1 ;;
        --as-slurm)  exec sbatch "$0" "${@/--as-slurm/}" ;;
        -h|--help)
            sed -n '/^# Usage/,/^# Exit codes/p' "$0" | sed 's/^# //;s/^#$//'
            exit 0 ;;
        *) echo "unknown arg: $arg" >&2; exit 1 ;;
    esac
done

say()  { printf '\033[1;34m[gaussmaxhs]\033[0m %s\n' "$*"; }
run()  { if [[ $DRY_RUN -eq 1 ]]; then printf '+ %s\n' "$*"; else eval "$@"; fi; }
fail() { printf '\033[1;31m[gaussmaxhs] ERROR:\033[0m %s\n' "$*" >&2; exit "${2:-1}"; }

# ----------------------------------------------------------------------------
# 3. Load cluster modules (matricsi uses Lmod / tcl-modules)
# ----------------------------------------------------------------------------
if command -v module >/dev/null 2>&1; then
    say "loading compiler / build toolchain"
    run "module purge || true"
    # Adjust these names if matricsi's module tree uses different labels.
    run "module load gcc/11 || module load gcc || true"
    run "module load cmake || true"
    run "module load python/3.10 || module load python || true"
    # CPLEX is not provided as a module on matricsi (per exp-1 history);
    # Python `import cplex` works because CPLEX is installed site-wide
    # and the `cplex` Python pkg ships its own libs. We need the C
    # static libs separately, see next section.
fi

# ----------------------------------------------------------------------------
# 4. Locate CPLEX static libraries
# ----------------------------------------------------------------------------
autodetect_cplex () {
    # Common install roots shipped with `IBM ILOG CPLEX Studio`
    local candidates=(
        "${CPLEX_ROOT:-}"
        "/opt/ibm/ILOG/CPLEX_Studio2211"
        "/opt/ibm/ILOG/CPLEX_Studio221"
        "/opt/ibm/ILOG/CPLEX_Studio201"
        "/users/scherif/ILOG/CPLEX_Studio2211"
        "/users/scherif/ILOG/CPLEX_Studio221"
        "/users/scherif/ComputeSpace/DiverseSAT/cplex"
        "/softs/CPLEX_Studio2211"
        "/softs/CPLEX_Studio221"
    )
    for root in "${candidates[@]}"; do
        [[ -z "$root" ]] && continue
        local lib="$root/cplex/lib/x86-64_linux/static_pic"
        local inc="$root/cplex/include"
        if [[ -f "$lib/libcplex.a" && -f "$lib/libilocplex.a" && -f "$inc/ilcplex/cplex.h" ]]; then
            CPLEX_LIBDIR="$lib"
            CPLEX_INCDIR="$inc"
            say "auto-detected CPLEX at $root"
            return 0
        fi
    done
    return 1
}

if [[ -z "$CPLEX_LIBDIR" || -z "$CPLEX_INCDIR" ]]; then
    if ! autodetect_cplex; then
        fail "CPLEX static libraries not found. Set CPLEX_ROOT, or export
       CPLEX_LIBDIR  (directory containing libcplex.a + libilocplex.a)
       CPLEX_INCDIR  (directory containing ilcplex/cplex.h)
Example:
       export CPLEX_ROOT=/opt/ibm/ILOG/CPLEX_Studio2211
or
       export CPLEX_LIBDIR=\$CPLEX_ROOT/cplex/lib/x86-64_linux/static_pic
       export CPLEX_INCDIR=\$CPLEX_ROOT/cplex/include" 1
    fi
fi

[[ -f "$CPLEX_LIBDIR/libcplex.a"    ]] || fail "missing $CPLEX_LIBDIR/libcplex.a"
[[ -f "$CPLEX_LIBDIR/libilocplex.a" ]] || fail "missing $CPLEX_LIBDIR/libilocplex.a"
[[ -f "$CPLEX_INCDIR/ilcplex/cplex.h" ]] || fail "missing $CPLEX_INCDIR/ilcplex/cplex.h"

say "CPLEX_LIBDIR = $CPLEX_LIBDIR"
say "CPLEX_INCDIR = $CPLEX_INCDIR"

# ----------------------------------------------------------------------------
# 5. Clone (or update) the gaussmaxhs repository
# ----------------------------------------------------------------------------
run "mkdir -p '$BUILD_ROOT'"
if [[ -d "$BUILD_DIR/.git" ]]; then
    say "updating existing checkout at $BUILD_DIR"
    run "cd '$BUILD_DIR' && git fetch --tags origin && git checkout '$GIT_REF' && git pull --ff-only origin '$GIT_REF' || true"
else
    say "cloning $GIT_URL -> $BUILD_DIR"
    run "git clone '$GIT_URL' '$BUILD_DIR'"
    run "cd '$BUILD_DIR' && git checkout '$GIT_REF'"
fi

# ----------------------------------------------------------------------------
# 6. Configure & build
# ----------------------------------------------------------------------------
say "configuring GaussMaxHS (make config)"
run "cd '$BUILD_DIR' && make config \
        LINUX_CPLEXLIBDIR='$CPLEX_LIBDIR' \
        LINUX_CPLEXINCDIR='$CPLEX_INCDIR' \
        prefix='$INSTALL_PREFIX'"

say "building ($JOBS parallel jobs)"
if ! run "cd '$BUILD_DIR' && make -j$JOBS"; then
    fail "compilation failed; see logs under $BUILD_DIR" 2
fi

# GaussMaxHS's upstream Makefile places the final binary at one of these paths.
BINARY=""
for candidate in \
    "$BUILD_DIR/build/release/bin/maxhs" \
    "$BUILD_DIR/build/bin/release/maxhs" \
    "$BUILD_DIR/build/dynamic/bin/maxhs" \
    "$BUILD_DIR/maxhs"
do
    if [[ -x "$candidate" ]]; then
        BINARY="$candidate"
        break
    fi
done
if [[ -z "$BINARY" ]]; then
    if [[ $DRY_RUN -eq 1 ]]; then
        BINARY="$BUILD_DIR/build/release/bin/maxhs"
        say "(dry-run) assuming binary will land at $BINARY"
    else
        fail "compiled but could not find resulting 'maxhs' binary under $BUILD_DIR/build/" 2
    fi
fi

say "built binary: $BINARY"

# ----------------------------------------------------------------------------
# 7. Install to the path the SLURM jobs expect
# ----------------------------------------------------------------------------
run "mkdir -p '$INSTALL_PREFIX'"
run "install -m 0755 '$BINARY' '$INSTALL_PREFIX/maxhs'"
say "installed -> $INSTALL_PREFIX/maxhs"

# ----------------------------------------------------------------------------
# 8. Smoke test with the upstream README example (4 vars, 4 soft + 2 hard-XOR)
#    Expected output: 'o 5' and 's OPTIMUM FOUND'.
# ----------------------------------------------------------------------------
if [[ $DRY_RUN -eq 0 ]]; then
    TMP="$(mktemp -d)"
    trap 'rm -rf "$TMP"' EXIT
    cat > "$TMP/smoke.wcnfxor" <<'EOF'
p wcnf 4 6 10
5 1 2 -3 0
5 1 -2 3 0
5 -1 2 3 0
5 -1 -2 -3 0
x 10 1 2 3 0
x 10 -1 3 4 0
EOF
    say "running smoke test on upstream README instance"
    if ! OUT="$('$INSTALL_PREFIX/maxhs' "$TMP/smoke.wcnfxor" 2>&1)"; then
        printf '%s\n' "$OUT" >&2
        fail "smoke test: maxhs exited non-zero" 3
    fi
    printf '%s\n' "$OUT" | sed -e 's/^/  /'
    if ! printf '%s' "$OUT" | grep -q '^s OPTIMUM FOUND'; then
        fail "smoke test: did not see 's OPTIMUM FOUND' in output" 3
    fi
    if ! printf '%s' "$OUT" | grep -q '^o 5'; then
        fail "smoke test: expected 'o 5' (cost 5), got unexpected cost line" 3
    fi
    say "smoke test PASSED (cost 5 as expected)"
fi

# ----------------------------------------------------------------------------
# 9. Summary
# ----------------------------------------------------------------------------
cat <<EOS

================================================================
GaussMaxHS build complete.
  source tree : $BUILD_DIR
  binary      : $INSTALL_PREFIX/maxhs
  CPLEX libs  : $CPLEX_LIBDIR
  CPLEX incs  : $CPLEX_INCDIR

Next steps:
  cd $(dirname "$0")
  ./run_all_experiments.sh submit   # or sbatch jobs/jobslurm-*_gaussmaxhs
================================================================
EOS
