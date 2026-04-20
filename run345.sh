#!/usr/bin/env bash
# run345.sh —— 一键在 matricsi 集群上跑 DiverseSAT 补充实验 (默认 exp-2/3/4)
#
# 退出码
# ------
#   0 = 全部提交成功（SLURM 任务还在跑，但脚本任务完成）
#   1 = 前置检查失败（路径/二进制/环境）—— 磁盘上没有副作用
#   2 = smoke test 失败 —— 已打印失败原因
#   3 = SLURM sbatch 返回错误
#
# 环境变量（可选覆盖）
# --------------------
#   BENCH_DIR=/path/to/benchmarks           默认 /users/scherif/ComputeSpace/DiverseSAT/benchmarks
#   ROUNDINGSAT_BIN=/path/to/roundingsat    默认 /users/scherif/ComputeSpace/DiverseSAT/solvers/roundingsat
#   GAUSSMAXHS_BIN=/path/to/maxhs           默认 /users/scherif/ComputeSpace/DiverseSAT/solvers/gaussmaxhs/maxhs

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BENCH_DIR="${BENCH_DIR:-/users/scherif/ComputeSpace/DiverseSAT/benchmarks}"
ROUNDINGSAT_BIN="${ROUNDINGSAT_BIN:-/users/scherif/ComputeSpace/DiverseSAT/solvers/roundingsat}"
GAUSSMAXHS_BIN="${GAUSSMAXHS_BIN:-/users/scherif/ComputeSpace/DiverseSAT/solvers/gaussmaxhs/maxhs}"

RUN_EXP2=1
RUN_EXP3=1
RUN_EXP4=1
RUN_EXP5=0   # 默认关闭：SEv1v3 overlay unsound，等 Sami 决策；用 --with-exp5 打开
DRY_RUN=0
ASSUME_YES=0
DO_GIT_PULL=1
DO_SMOKE=1
SEQUENTIAL=0

# 解析 --only / --skip
apply_only() {
    RUN_EXP2=0; RUN_EXP3=0; RUN_EXP4=0; RUN_EXP5=0
    IFS=',' read -ra names <<< "$1"
    for n in "${names[@]}"; do
        case "$n" in
            exp2) RUN_EXP2=1 ;;
            exp3) RUN_EXP3=1 ;;
            exp4) RUN_EXP4=1 ;;
            exp5) RUN_EXP5=1 ;;
            *) echo "Unknown experiment in --only: $n (expected exp2/exp3/exp4/exp5)" >&2; exit 1 ;;
        esac
    done
}
apply_skip() {
    IFS=',' read -ra names <<< "$1"
    for n in "${names[@]}"; do
        case "$n" in
            exp2) RUN_EXP2=0 ;;
            exp3) RUN_EXP3=0 ;;
            exp4) RUN_EXP4=0 ;;
            exp5) RUN_EXP5=0 ;;
            *) echo "Unknown experiment in --skip: $n (expected exp2/exp3/exp4/exp5)" >&2; exit 1 ;;
        esac
    done
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --only)         apply_only "$2"; shift 2 ;;
        --only=*)       apply_only "${1#*=}"; shift ;;
        --skip)         apply_skip "$2"; shift 2 ;;
        --skip=*)       apply_skip "${1#*=}"; shift ;;
        --with-exp5)    RUN_EXP5=1; shift ;;
        --sequential)   SEQUENTIAL=1; shift ;;
        --dry-run)      DRY_RUN=1; shift ;;
        --yes|-y)       ASSUME_YES=1; shift ;;
        --no-git-pull)  DO_GIT_PULL=0; shift ;;
        --no-smoke)     DO_SMOKE=0; shift ;;
        -h|--help)
            sed -n '/^# run345.sh/,/^set -/p' "$0" \
                | grep '^#' | sed 's/^# \{0,1\}//'
            exit 0 ;;
        *)  echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

# 辅助函数
RED='\033[1;31m'; GREEN='\033[1;32m'; YELLOW='\033[1;33m'; BLUE='\033[1;34m'; NC='\033[0m'
log()   { printf "${BLUE}[INFO]${NC}  %s\n" "$*"; }
ok()    { printf "${GREEN}[ OK ]${NC}  %s\n" "$*"; }
warn()  { printf "${YELLOW}[WARN]${NC}  %s\n" "$*"; }
die()   { printf "${RED}[FAIL]${NC}  %s\n" "$*" >&2; exit "${2:-1}"; }
step()  { printf "\n${BLUE}========== %s ==========${NC}\n" "$*"; }

run() {
    if (( DRY_RUN )); then
        printf "${YELLOW}[DRY]${NC}   %s\n" "$*"
    else
        eval "$@"
    fi
}

confirm() {
    (( ASSUME_YES )) && return 0
    local prompt="$1"
    read -r -p "$prompt [y/N] " ans
    [[ "$ans" =~ ^[Yy]$ ]]
}

# Pre-flight 检查
preflight() {
    step "前置检查 (pre-flight)"

    # 1. 当前目录：只检查本次实际要跑的实验
    local required_dirs=()
    (( RUN_EXP2 )) && required_dirs+=( "experiment-2-k=3,4" )
    (( RUN_EXP3 )) && required_dirs+=( "experiment-3-XOR" )
    (( RUN_EXP4 )) && required_dirs+=( "experiment-4-SEv3" )
    (( RUN_EXP5 )) && required_dirs+=( "experiment-5-SEv1v3" )
    for d in "${required_dirs[@]}"; do
        [[ -d "$SCRIPT_DIR/$d" ]] || die "找不到子目录 $d —— 脚本必须放在 added_experiment/ 下。当前在 $SCRIPT_DIR"
    done
    ok "工作目录 $SCRIPT_DIR"

    # 2. sbatch 可用
    command -v sbatch >/dev/null || die "找不到 sbatch 命令 —— 请在 cluster 登录节点上运行此脚本"
    ok "sbatch 可用"

    # 3. Python + pysat
    command -v python3 >/dev/null || die "找不到 python3"
    if ! python3 -c "import pysat" 2>/dev/null; then
        die "python3 -c 'import pysat' 失败。请先执行：pip install --user python-sat"
    fi
    ok "Python $(python3 --version 2>&1 | awk '{print $2}') + pysat 可用"

    # 4. git pull
    if (( DO_GIT_PULL )); then
        if git -C "$SCRIPT_DIR/.." rev-parse --is-inside-work-tree >/dev/null 2>&1; then
            log "git pull ..."
            run "git -C '$SCRIPT_DIR/..' pull --ff-only origin master || warn 'git pull 失败 —— 手动 pull 后重跑本脚本'"
            local HEAD
            HEAD=$(git -C "$SCRIPT_DIR/.." rev-parse --short HEAD 2>/dev/null || echo '?')
            ok "仓库 HEAD = $HEAD"
        else
            warn "不是 git 仓库 —— 跳过 pull"
        fi
    else
        warn "跳过 git pull（--no-git-pull）"
    fi

    # 5. benchmark 目录
    [[ -d "$BENCH_DIR" ]] || die "BENCH_DIR 不存在: $BENCH_DIR（用环境变量 BENCH_DIR=... 覆盖）"
    local N_BENCH
    N_BENCH=$(find "$BENCH_DIR" -maxdepth 1 -name '*.cnf' 2>/dev/null | wc -l)
    (( N_BENCH >= 299 )) \
        && ok "benchmark 目录 $BENCH_DIR 下有 $N_BENCH 个 .cnf 实例" \
        || warn "benchmark 目录 $BENCH_DIR 下只有 $N_BENCH 个 .cnf（期望 ≥ 299）—— 确认是否正确"

    # 6. RoundingSAT 二进制（exp-2/4/5 需要）
    if (( RUN_EXP2 || RUN_EXP4 || RUN_EXP5 )); then
        [[ -x "$ROUNDINGSAT_BIN" ]] \
            || die "RoundingSAT 二进制不存在或不可执行: $ROUNDINGSAT_BIN（用环境变量 ROUNDINGSAT_BIN=... 覆盖）"
        ok "RoundingSAT 二进制 $ROUNDINGSAT_BIN"
    fi

    # 7. CPLEX module（exp-2 和 exp-4 都需要）
    if (( RUN_EXP2 || RUN_EXP4 )); then
        if command -v module >/dev/null 2>&1 && module is-loaded cplex 2>/dev/null; then
            ok "CPLEX 模块已加载"
        else
            warn "CPLEX 模块未加载 —— SLURM 脚本里的 'module load cplex' 会处理；如果集群的 module 名字改过，需要先手动改各 jobslurm-*_CPLEX 脚本"
        fi
    fi

    # 8. GaussMaxHS 二进制（仅 exp-3 需要）
    if (( RUN_EXP3 )); then
        if [[ ! -x "$GAUSSMAXHS_BIN" ]]; then
            warn "GaussMaxHS 二进制不存在: $GAUSSMAXHS_BIN"
            log "需要先跑编译脚本：experiment-3-XOR/build_gaussmaxhs.sh"
            if confirm "现在自动跑 build_gaussmaxhs.sh？"; then
                run "bash '$SCRIPT_DIR/experiment-3-XOR/build_gaussmaxhs.sh'" \
                    || die "GaussMaxHS 编译失败 —— 请看 build_gaussmaxhs.sh 输出再手动排查" 1
                [[ -x "$GAUSSMAXHS_BIN" ]] || die "编译完成但找不到 $GAUSSMAXHS_BIN"
            else
                die "未编译 GaussMaxHS —— 请先跑：bash experiment-3-XOR/build_gaussmaxhs.sh"
            fi
        fi
        ok "GaussMaxHS 二进制 $GAUSSMAXHS_BIN"
    fi

    ok "前置检查全部通过"
}

# Smoke test
smoke_test() {
    (( DO_SMOKE )) || { warn "跳过 smoke test（--no-smoke）"; return 0; }
    step "Smoke test（用 benchmark 目录里最小的 .cnf）"

    local SAMPLE
    SAMPLE=$(find "$BENCH_DIR" -maxdepth 1 -name '*.cnf' -printf '%s %p\n' 2>/dev/null \
                    | sort -n | head -1 | awk '{print $2}')
    [[ -f "$SAMPLE" ]] || die "找不到任何 .cnf 文件做 smoke test"
    log "用例: $(basename "$SAMPLE") ($(stat -c%s "$SAMPLE") bytes)"

    if (( RUN_EXP2 )); then
        log "exp-2 smoke: OH_SEv1_cnf_to_PBO.py K=3"
        run "python3 '$SCRIPT_DIR/experiment-2-k=3,4/roundingsat/transformers/OH_SEv1_cnf_to_PBO.py' '$SAMPLE' /tmp/smoke_exp2.pbo 3 >/dev/null" \
            || die "exp-2 transformer 调用失败" 2
        (( DRY_RUN )) || [[ -s /tmp/smoke_exp2.pbo ]] || die "exp-2 transformer 没产出 .pbo" 2
        ok "exp-2 transformer OK"
    fi

    if (( RUN_EXP3 )); then
        log "exp-3 smoke: OH_SEv1XOR_cnf_to_wcnfxor.py K=3"
        run "python3 '$SCRIPT_DIR/experiment-3-XOR/transformers/OH_SEv1XOR_cnf_to_wcnfxor.py' '$SAMPLE' /tmp/smoke_exp3.wcnfxor 3 >/dev/null" \
            || die "exp-3 transformer 调用失败" 2
        if (( ! DRY_RUN )); then
            [[ -s /tmp/smoke_exp3.wcnfxor ]] || die "exp-3 transformer 没产出 .wcnfxor" 2
            grep -q '^x ' /tmp/smoke_exp3.wcnfxor || die "exp-3 产物里没有 'x ' 开头的 XOR 子句行" 2
        fi
        ok "exp-3 transformer OK"

        if [[ -x "$GAUSSMAXHS_BIN" ]]; then
            log "GaussMaxHS 二进制健全性检查"
            run "'$GAUSSMAXHS_BIN' --help >/dev/null 2>&1 || '$GAUSSMAXHS_BIN' -h >/dev/null 2>&1 || true"
            ok "GaussMaxHS 二进制可执行"
        fi
    fi

    if (( RUN_EXP4 )); then
        log "exp-4 smoke: OH_SEv3_cnf_to_PBO.py K=3"
        run "python3 '$SCRIPT_DIR/experiment-4-SEv3/transformers/OH_SEv3_cnf_to_PBO.py' '$SAMPLE' /tmp/smoke_exp4.opb 3 >/dev/null" \
            || die "exp-4 transformer 调用失败" 2
        (( DRY_RUN )) || [[ -s /tmp/smoke_exp4.opb ]] || die "exp-4 transformer 没产出 .opb" 2
        ok "exp-4 transformer OK"
    fi

    if (( RUN_EXP5 )); then
        log "exp-5 smoke: OH_SEv1v3_cnf_to_PBO.py K=3"
        run "python3 '$SCRIPT_DIR/experiment-5-SEv1v3/transformers/OH_SEv1v3_cnf_to_PBO.py' '$SAMPLE' /tmp/smoke_exp5.opb 3 >/dev/null" \
            || die "exp-5 transformer 调用失败" 2
        (( DRY_RUN )) || [[ -s /tmp/smoke_exp5.opb ]] || die "exp-5 transformer 没产出 .opb" 2
        ok "exp-5 transformer OK"
    fi

    ok "Smoke test 通过"
}

# -------------------------------------------------------------------
# 提交工具：
#   submit_and_collect_ids <dir> <prefix>         —— 无依赖提交
#   submit_with_dependency <dir> <prefix> <deps>  —— 带 afterok 依赖提交
# -------------------------------------------------------------------
submit_and_collect_ids() {
    local dir="$1" prefix="$2"
    local ids="" jobfile jid
    pushd "$dir" >/dev/null || die "cd $dir 失败"
    for jobfile in ${prefix}*; do
        [[ -f "$jobfile" ]] || continue
        if (( DRY_RUN )); then
            printf "${YELLOW}[DRY]${NC}   sbatch --parsable %s  (in %s)\n" "$jobfile" "$dir"
            jid="DRY$RANDOM"
        else
            jid=$(sbatch --parsable "$jobfile") || die "sbatch 失败: $jobfile" 3
            log "  submitted $jobfile → $jid"
        fi
        [[ -n "$ids" ]] && ids+=":"
        ids+="$jid"
        sleep 0.2
    done
    popd >/dev/null
    printf '%s\n' "$ids"
}

submit_with_dependency() {
    local dir="$1" prefix="$2" dep="$3"
    local ids="" jobfile jid
    [[ -z "$dep" ]] && die "submit_with_dependency 收到空依赖列表" 3
    pushd "$dir" >/dev/null || die "cd $dir 失败"
    for jobfile in ${prefix}*; do
        [[ -f "$jobfile" ]] || continue
        if (( DRY_RUN )); then
            printf "${YELLOW}[DRY]${NC}   sbatch --parsable --dependency=afterok:%s %s  (in %s)\n" "$dep" "$jobfile" "$dir"
            jid="DRY$RANDOM"
        else
            jid=$(sbatch --parsable --dependency=afterok:"$dep" "$jobfile") \
                || die "sbatch（带 dependency）失败: $jobfile" 3
            log "  submitted $jobfile → $jid (deps=$dep)"
        fi
        [[ -n "$ids" ]] && ids+=":"
        ids+="$jid"
        sleep 0.2
    done
    popd >/dev/null
    printf '%s\n' "$ids"
}

# 以 afterany（不论成功失败都算完成）方式提交 —— 只用于 --sequential 跨实验等待
submit_with_afterany() {
    local dir="$1" prefix="$2" dep="$3"
    local ids="" jobfile jid
    [[ -z "$dep" ]] && { submit_and_collect_ids "$dir" "$prefix"; return; }
    pushd "$dir" >/dev/null || die "cd $dir 失败"
    for jobfile in ${prefix}*; do
        [[ -f "$jobfile" ]] || continue
        if (( DRY_RUN )); then
            printf "${YELLOW}[DRY]${NC}   sbatch --parsable --dependency=afterany:%s %s  (in %s)\n" "$dep" "$jobfile" "$dir"
            jid="DRY$RANDOM"
        else
            jid=$(sbatch --parsable --dependency=afterany:"$dep" "$jobfile") \
                || die "sbatch（--sequential）失败: $jobfile" 3
            log "  submitted $jobfile → $jid (seq deps=$dep)"
        fi
        [[ -n "$ids" ]] && ids+=":"
        ids+="$jid"
        sleep 0.2
    done
    popd >/dev/null
    printf '%s\n' "$ids"
}

# -------------------------------------------------------------------
# 各实验流程
# -------------------------------------------------------------------
EXP2_IDS=""; EXP3_IDS=""; EXP4_IDS=""; EXP5_IDS=""
PREV_EXP_LAST_IDS=""  # --sequential 模式下，下一个实验 transform 等这些 ID 完成

# 用于 --sequential 的辅助：把 transform 绑到前一个实验的全部 ID
submit_transform_respecting_sequential() {
    local dir="$1" prefix="$2"
    if (( SEQUENTIAL )) && [[ -n "$PREV_EXP_LAST_IDS" ]]; then
        submit_with_afterany "$dir" "$prefix" "$PREV_EXP_LAST_IDS"
    else
        submit_and_collect_ids "$dir" "$prefix"
    fi
}

run_exp2() {
    (( RUN_EXP2 )) || return 0
    step "exp-2 —— 生成 SLURM 脚本"
    pushd "$SCRIPT_DIR/experiment-2-k=3,4" >/dev/null
    run "./run_all_experiments.sh generate" || die "exp-2 generate 失败"
    popd >/dev/null

    step "exp-2 —— 提交 transform（6 个任务）"
    local T_IDS
    T_IDS=$(submit_transform_respecting_sequential \
        "$SCRIPT_DIR/experiment-2-k=3,4/roundingsat/transform" "jobslurm-")
    ok "exp-2 transform IDs: $T_IDS"

    step "exp-2 —— 提交 RoundingSAT solve（6 个任务，依赖 transform）"
    local RS_IDS
    RS_IDS=$(submit_with_dependency \
        "$SCRIPT_DIR/experiment-2-k=3,4/roundingsat/jobs" "jobslurm-" "$T_IDS")
    ok "exp-2 RoundingSAT solve IDs: $RS_IDS"

    step "exp-2 —— 提交 CPLEX solve（8 个任务，不依赖 transform）"
    local CPLEX_IDS
    if (( SEQUENTIAL )) && [[ -n "$PREV_EXP_LAST_IDS" ]]; then
        CPLEX_IDS=$(submit_with_afterany \
            "$SCRIPT_DIR/experiment-2-k=3,4/cplex/jobs" "jobslurm-" "$PREV_EXP_LAST_IDS")
    else
        CPLEX_IDS=$(submit_and_collect_ids \
            "$SCRIPT_DIR/experiment-2-k=3,4/cplex/jobs" "jobslurm-")
    fi
    ok "exp-2 CPLEX solve IDs: $CPLEX_IDS"

    EXP2_IDS="$T_IDS:$RS_IDS:$CPLEX_IDS"
    PREV_EXP_LAST_IDS="$RS_IDS:$CPLEX_IDS"
}

run_exp3() {
    (( RUN_EXP3 )) || return 0
    step "exp-3 —— 生成 SLURM 脚本"
    pushd "$SCRIPT_DIR/experiment-3-XOR" >/dev/null
    run "./run_all_experiments.sh generate" || die "exp-3 generate 失败"
    popd >/dev/null

    step "exp-3 —— 提交 transform（15 个任务）"
    local T_IDS
    T_IDS=$(submit_transform_respecting_sequential \
        "$SCRIPT_DIR/experiment-3-XOR/transform" "jobslurm-")
    ok "exp-3 transform IDs: $T_IDS"

    step "exp-3 —— 提交 GaussMaxHS solve（15 个任务，依赖 transform）"
    local S_IDS
    S_IDS=$(submit_with_dependency \
        "$SCRIPT_DIR/experiment-3-XOR/jobs" "jobslurm-" "$T_IDS")
    ok "exp-3 GaussMaxHS solve IDs: $S_IDS"

    EXP3_IDS="$T_IDS:$S_IDS"
    PREV_EXP_LAST_IDS="$S_IDS"
}

run_exp4() {
    (( RUN_EXP4 )) || return 0
    step "exp-4 —— prepare + 生成 SLURM 脚本（RS + CPLEX, SEv3 standalone）"
    pushd "$SCRIPT_DIR/experiment-4-SEv3" >/dev/null
    run "./run_all_experiments.sh prepare"  || die "exp-4 prepare 失败"
    run "./run_all_experiments.sh generate" || die "exp-4 generate 失败"
    popd >/dev/null

    step "exp-4 —— 提交 transform（15 个任务，CNF→OPB+SEv3）"
    local T_IDS
    T_IDS=$(submit_transform_respecting_sequential \
        "$SCRIPT_DIR/experiment-4-SEv3/transform" "jobslurm-")
    ok "exp-4 transform IDs: $T_IDS"

    step "exp-4 —— 提交 RoundingSAT solve（15 个任务，依赖 transform）"
    local RS_IDS
    RS_IDS=$(submit_with_dependency \
        "$SCRIPT_DIR/experiment-4-SEv3/jobs" "jobslurm-" "$T_IDS")
    ok "exp-4 RoundingSAT solve IDs: $RS_IDS"

    step "exp-4 —— 提交 CPLEX solve（20 个任务, QP/DW/IW/BIN × k={2,3,4,5,10}, 不依赖 transform）"
    local CPLEX_IDS
    if (( SEQUENTIAL )) && [[ -n "$PREV_EXP_LAST_IDS" ]]; then
        CPLEX_IDS=$(submit_with_afterany \
            "$SCRIPT_DIR/experiment-4-SEv3/cplex/jobs" "jobslurm-" "$PREV_EXP_LAST_IDS")
    else
        CPLEX_IDS=$(submit_and_collect_ids \
            "$SCRIPT_DIR/experiment-4-SEv3/cplex/jobs" "jobslurm-")
    fi
    ok "exp-4 CPLEX solve IDs: $CPLEX_IDS"

    EXP4_IDS="$T_IDS:$RS_IDS:$CPLEX_IDS"
    PREV_EXP_LAST_IDS="$RS_IDS:$CPLEX_IDS"
}

run_exp5() {
    (( RUN_EXP5 )) || return 0
    step "exp-5 —— prepare + 生成 SLURM 脚本（SEv1v3 heuristic overlay）"
    warn "exp-5 是 SEv1+SEv3 启发式叠加（非 sound），可能在部分 instance 上比 exp-4 次优或 UNSAT — 这是预期行为"
    pushd "$SCRIPT_DIR/experiment-5-SEv1v3" >/dev/null
    run "./run_all_experiments.sh prepare"  || die "exp-5 prepare 失败"
    run "./run_all_experiments.sh generate" || die "exp-5 generate 失败"
    popd >/dev/null

    step "exp-5 —— 提交 transform（15 个任务，SEv1 ∧ SEv3 overlay）"
    local T_IDS
    T_IDS=$(submit_transform_respecting_sequential \
        "$SCRIPT_DIR/experiment-5-SEv1v3/transform" "jobslurm-")
    ok "exp-5 transform IDs: $T_IDS"

    step "exp-5 —— 提交 RoundingSAT solve（15 个任务，依赖 transform）"
    local S_IDS
    S_IDS=$(submit_with_dependency \
        "$SCRIPT_DIR/experiment-5-SEv1v3/jobs" "jobslurm-" "$T_IDS")
    ok "exp-5 RoundingSAT solve IDs: $S_IDS"

    EXP5_IDS="$T_IDS:$S_IDS"
    PREV_EXP_LAST_IDS="$S_IDS"
}

summary() {
    step "✅ 全部任务已提交 —— 可以关闭终端，SLURM 会自动跑"

    local total=0
    local n
    for pair in "EXP2_IDS:exp-2" "EXP3_IDS:exp-3" "EXP4_IDS:exp-4" "EXP5_IDS:exp-5"; do
        local var="${pair%%:*}" label="${pair##*:}"
        local ids="${!var}"
        if [[ -n "$ids" ]]; then
            n=$(awk -F: '{print NF}' <<< "$ids")
            echo -e "  ${GREEN}${label}${NC}: 共 ${n} 个 SLURM job 已提交"
            total=$((total + n))
        fi
    done
    echo "  ────────────────────────────"
    echo -e "  ${GREEN}合计${NC}: ${total} 个 SLURM job"

    echo ""
    if (( SEQUENTIAL )); then
        echo -e "${YELLOW}模式：--sequential${NC}（exp-2 → exp-3 → exp-4 → exp-5 按顺序跑，后一个等前一个全部完成）"
    else
        echo -e "${BLUE}模式：并行${NC}（四个实验同时在队列里，SLURM 根据资源自行调度；solve 只等自己实验的 transform）"
    fi
    echo ""
    echo -e "${BLUE}监控:${NC}       squeue -u \$USER"
    echo -e "${BLUE}取消所有:${NC}   scancel -u \$USER"
    echo ""
    echo -e "${BLUE}全部跑完后，汇总 CSV:${NC}"
    (( RUN_EXP2 )) && echo "    cd '$SCRIPT_DIR/experiment-2-k=3,4'  && ./run_all_experiments.sh sumup"
    (( RUN_EXP3 )) && echo "    cd '$SCRIPT_DIR/experiment-3-XOR'    && ./run_all_experiments.sh sumup"
    (( RUN_EXP4 )) && echo "    cd '$SCRIPT_DIR/experiment-4-SEv3'   && ./run_all_experiments.sh sumup"
    (( RUN_EXP5 )) && echo "    cd '$SCRIPT_DIR/experiment-5-SEv1v3' && ./run_all_experiments.sh sumup"
    echo ""
    echo -e "${BLUE}结果 CSV 位置:${NC}"
    (( RUN_EXP2 )) && echo "    $SCRIPT_DIR/experiment-2-k=3,4/roundingsat/sumup/results/"
    (( RUN_EXP2 )) && echo "    $SCRIPT_DIR/experiment-2-k=3,4/cplex/sumup/results/"
    (( RUN_EXP3 )) && echo "    $SCRIPT_DIR/experiment-3-XOR/sumup/results/"
    (( RUN_EXP4 )) && echo "    $SCRIPT_DIR/experiment-4-SEv3/sumup/results/          (RoundingSAT)"
    (( RUN_EXP4 )) && echo "    $SCRIPT_DIR/experiment-4-SEv3/cplex/sumup/results/    (CPLEX)"
    (( RUN_EXP5 )) && echo "    $SCRIPT_DIR/experiment-5-SEv1v3/sumup/results/"
    echo ""
    echo -e "预计墙钟时间：每个 solve job 最多 10000 秒（~2.8h），并发度取决于 SLURM 负载。"
}

main() {
    echo -e "${BLUE}"
    echo "============================================================"
    echo "  DiverseSAT supplementary experiments — run345.sh"
    echo "  default: exp-2 / exp-3 / exp-4   (exp-5 opt-in via --with-exp5)"
    echo "============================================================"
    echo -e "${NC}"

    (( DRY_RUN ))    && warn "DRY-RUN 模式：只打印命令，不执行"
    (( SEQUENTIAL )) && warn "SEQUENTIAL 模式：实验之间用 afterany 依赖，前一个实验全部结束后下一个才开始"

    local pending=()
    (( RUN_EXP2 )) && pending+=("exp-2 (RS+CPLEX, k=3,4,                20 jobs)")
    (( RUN_EXP3 )) && pending+=("exp-3 (GaussMaxHS SEv1-XOR, k=2,3,4,5,10, 30 jobs)")
    (( RUN_EXP4 )) && pending+=("exp-4 (RS+CPLEX SEv3, k=2,3,4,5,10,     50 jobs)")
    (( RUN_EXP5 )) && pending+=("exp-5 (RS SEv1∧SEv3 overlay, k=2,3,4,5,10, 30 jobs)")
    [[ ${#pending[@]} -eq 0 ]] && die "--only/--skip 把全部实验都排除了，没事可做"

    log "计划提交："
    for p in "${pending[@]}"; do echo "    • $p"; done

    preflight
    smoke_test

    if ! confirm "前置检查全部通过，现在提交 SLURM 任务？"; then
        die "用户取消" 0
    fi

    run_exp2
    run_exp3
    run_exp4
    run_exp5
    summary
}

main "$@"
