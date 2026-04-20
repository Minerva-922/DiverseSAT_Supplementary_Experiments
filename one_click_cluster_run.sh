#!/usr/bin/env bash
# one_click_cluster_run.sh —— 一键在 matricsi 集群上跑 exp-2 + exp-3
#
# 合作者只需在集群上执行一次：
#
#     cd /users/scherif/ComputeSpace/DiverseSAT/DiverseSAT_Supplementary_Experiments/added_experiment
#     bash one_click_cluster_run.sh
#
# 脚本会自动完成：
#   1. 检查环境（git 最新、Python pysat、solver 二进制、benchmark 目录）
#   2. 跑一次快速的 transform smoke test，避免整批失败
#   3. 生成 SLURM 脚本
#   4. 用 sbatch --dependency 把 "transform → solve" 自动串联后提交
#   5. 打印最终的 job ID 列表和后续步骤（sumup）
#
# 用法
#   bash one_click_cluster_run.sh                 # 两个实验都跑
#   bash one_click_cluster_run.sh --exp2-only     # 只跑 exp-2
#   bash one_click_cluster_run.sh --exp3-only     # 只跑 exp-3
#   bash one_click_cluster_run.sh --dry-run       # 打印所有命令但不执行
#   bash one_click_cluster_run.sh --yes           # 跳过所有确认（全自动）
#   bash one_click_cluster_run.sh --no-git-pull   # 跳过 git pull
#   bash one_click_cluster_run.sh --no-smoke      # 跳过 smoke test
#   bash one_click_cluster_run.sh --help          # 显示此帮助
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
DRY_RUN=0
ASSUME_YES=0
DO_GIT_PULL=1
DO_SMOKE=1

while [[ $# -gt 0 ]]; do
    case "$1" in
        --exp2-only)    RUN_EXP3=0; shift ;;
        --exp3-only)    RUN_EXP2=0; shift ;;
        --dry-run)      DRY_RUN=1; shift ;;
        --yes|-y)       ASSUME_YES=1; shift ;;
        --no-git-pull)  DO_GIT_PULL=0; shift ;;
        --no-smoke)     DO_SMOKE=0; shift ;;
        -h|--help)
            sed -n '/^# one_click_cluster_run.sh/,/^set -/p' "$0" \
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
    # run <cmd...>  —— 遵守 DRY_RUN
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

    # 1. 当前目录
    if [[ ! -d "$SCRIPT_DIR/experiment-2-k=3,4" ]] || [[ ! -d "$SCRIPT_DIR/experiment-3-XOR" ]]; then
        die "脚本必须放在 added_experiment/ 目录下（找不到 experiment-2-k=3,4 或 experiment-3-XOR 子目录）。当前在 $SCRIPT_DIR"
    fi
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

    # 4. git pull（默认跑；--no-git-pull 可以跳）
    if (( DO_GIT_PULL )); then
        if git -C "$SCRIPT_DIR/.." rev-parse --is-inside-work-tree >/dev/null 2>&1; then
            log "git pull ..."
            run "git -C '$SCRIPT_DIR/..' pull --ff-only origin master || warn 'git pull 失败 —— 手动 pull 后重跑本脚本'"
            local HEAD=$(git -C "$SCRIPT_DIR/.." rev-parse --short HEAD 2>/dev/null || echo '?')
            ok "仓库 HEAD = $HEAD"
        else
            warn "不是 git 仓库 —— 跳过 pull"
        fi
    else
        warn "跳过 git pull（--no-git-pull）"
    fi

    # 5. benchmark 目录
    [[ -d "$BENCH_DIR" ]] || die "BENCH_DIR 不存在: $BENCH_DIR（用环境变量 BENCH_DIR=... 覆盖）"
    local N_BENCH=$(find "$BENCH_DIR" -maxdepth 1 -name '*.cnf' 2>/dev/null | wc -l)
    (( N_BENCH >= 299 )) \
        && ok "benchmark 目录 $BENCH_DIR 下有 $N_BENCH 个 .cnf 实例" \
        || warn "benchmark 目录 $BENCH_DIR 下只有 $N_BENCH 个 .cnf（期望 ≥ 299）—— 确认是否正确"

    # 6. exp-2 的 solver 二进制
    if (( RUN_EXP2 )); then
        [[ -x "$ROUNDINGSAT_BIN" ]] \
            || die "RoundingSAT 二进制不存在或不可执行: $ROUNDINGSAT_BIN（用环境变量 ROUNDINGSAT_BIN=... 覆盖）"
        ok "RoundingSAT 二进制 $ROUNDINGSAT_BIN"

        # CPLEX 只能通过 module 加载，没法静态检查。但至少警告一下。
        if command -v module >/dev/null 2>&1 && module is-loaded cplex 2>/dev/null; then
            ok "CPLEX 模块已加载"
        else
            warn "CPLEX 模块未加载 —— SLURM 脚本里的 'module load cplex' 会处理；如果集群的 module 名字改过，需要先手动改 cplex/jobs/jobslurm-*_CPLEX"
        fi
    fi

    # 7. exp-3 的 GaussMaxHS 二进制（缺失则提示编译）
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

# Smoke test：在最小 .cnf 上跑一遍 transform，确认 Python 环境和参数格式 OK
smoke_test() {
    (( DO_SMOKE )) || { warn "跳过 smoke test（--no-smoke）"; return 0; }
    step "Smoke test（用 benchmark 目录里最小的 .cnf）"

    local SAMPLE=$(find "$BENCH_DIR" -maxdepth 1 -name '*.cnf' -printf '%s %p\n' 2>/dev/null \
                    | sort -n | head -1 | awk '{print $2}')
    [[ -f "$SAMPLE" ]] || die "找不到任何 .cnf 文件做 smoke test"
    log "用例: $(basename "$SAMPLE") ($(stat -c%s "$SAMPLE") bytes)"

    if (( RUN_EXP2 )); then
        log "exp-2 smoke test: OH_SEv1_cnf_to_PBO.py on K=3"
        run "python3 '$SCRIPT_DIR/experiment-2-k=3,4/roundingsat/transformers/OH_SEv1_cnf_to_PBO.py' '$SAMPLE' /tmp/smoke_exp2.pbo 3 >/dev/null" \
            || die "exp-2 transformer 调用失败" 2
        (( DRY_RUN )) || [[ -s /tmp/smoke_exp2.pbo ]] || die "exp-2 transformer 没产出 .pbo" 2
        ok "exp-2 transformer OK"
    fi

    if (( RUN_EXP3 )); then
        log "exp-3 smoke test: OH_SEv1XOR_cnf_to_wcnfxor.py on K=3"
        run "python3 '$SCRIPT_DIR/experiment-3-XOR/transformers/OH_SEv1XOR_cnf_to_wcnfxor.py' '$SAMPLE' /tmp/smoke_exp3.wcnfxor 3 >/dev/null" \
            || die "exp-3 transformer 调用失败" 2
        if (( ! DRY_RUN )); then
            [[ -s /tmp/smoke_exp3.wcnfxor ]] || die "exp-3 transformer 没产出 .wcnfxor" 2
            grep -q '^x ' /tmp/smoke_exp3.wcnfxor || die "exp-3 产物里没有 'x ' 开头的 XOR 子句行" 2
        fi
        ok "exp-3 transformer OK"

        # 额外：用真正的 maxhs 二进制跑一个 --help 确认可执行
        if [[ -x "$GAUSSMAXHS_BIN" ]]; then
            log "GaussMaxHS 二进制健全性检查"
            run "'$GAUSSMAXHS_BIN' --help >/dev/null 2>&1 || '$GAUSSMAXHS_BIN' -h >/dev/null 2>&1 || true"
            ok "GaussMaxHS 二进制可执行"
        fi
    fi

    ok "Smoke test 通过"
}

# 工具：迭代一个 submit_all.sh 对应的 jobslurm-* 文件，逐个 sbatch --parsable，
#       返回冒号分隔的 job ID 列表（可作为 --dependency=afterok 的参数）
submit_and_collect_ids() {
    local dir="$1"     # 包含 jobslurm-* 的目录
    local prefix="$2"  # 筛选前缀，如 jobslurm-
    local ids=""
    local jobfile jid

    pushd "$dir" >/dev/null || die "cd $dir 失败"

    # jobslurm-3_OH_SEv1 / jobslurm-2_OH_SEv1XOR 等
    for jobfile in ${prefix}*; do
        [[ -f "$jobfile" ]] || continue
        if (( DRY_RUN )); then
            printf "${YELLOW}[DRY]${NC}   sbatch --parsable $jobfile  (in $dir)\n"
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

# 工具：带 --dependency 提交一批 solve jobs
submit_with_dependency() {
    local dir="$1"
    local prefix="$2"
    local dep="$3"     # 冒号分隔 job ID
    local ids=""
    local jobfile jid

    pushd "$dir" >/dev/null || die "cd $dir 失败"

    for jobfile in ${prefix}*; do
        [[ -f "$jobfile" ]] || continue
        if (( DRY_RUN )); then
            printf "${YELLOW}[DRY]${NC}   sbatch --parsable --dependency=afterok:$dep $jobfile  (in $dir)\n"
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

# exp-2 流程
EXP2_IDS=""
run_exp2() {
    (( RUN_EXP2 )) || return 0
    step "exp-2 —— 生成 SLURM 脚本"

    pushd "$SCRIPT_DIR/experiment-2-k=3,4" >/dev/null
    run "./run_all_experiments.sh generate" || die "exp-2 generate 失败"
    popd >/dev/null

    step "exp-2 —— 提交 transform（6 个任务）"
    local TRANSFORM_IDS
    TRANSFORM_IDS=$(submit_and_collect_ids \
        "$SCRIPT_DIR/experiment-2-k=3,4/roundingsat/transform" "jobslurm-")
    ok "exp-2 transform IDs: $TRANSFORM_IDS"

    step "exp-2 —— 提交 RoundingSAT solve（6 个任务，依赖 transform）"
    local RS_IDS
    RS_IDS=$(submit_with_dependency \
        "$SCRIPT_DIR/experiment-2-k=3,4/roundingsat/jobs" "jobslurm-" "$TRANSFORM_IDS")
    ok "exp-2 RoundingSAT solve IDs: $RS_IDS"

    step "exp-2 —— 提交 CPLEX solve（8 个任务，独立于 transform）"
    local CPLEX_IDS
    CPLEX_IDS=$(submit_and_collect_ids \
        "$SCRIPT_DIR/experiment-2-k=3,4/cplex/jobs" "jobslurm-")
    ok "exp-2 CPLEX solve IDs: $CPLEX_IDS"

    EXP2_IDS="$TRANSFORM_IDS:$RS_IDS:$CPLEX_IDS"
}

# exp-3 流程
EXP3_IDS=""
run_exp3() {
    (( RUN_EXP3 )) || return 0
    step "exp-3 —— 生成 SLURM 脚本"

    pushd "$SCRIPT_DIR/experiment-3-XOR" >/dev/null
    run "./run_all_experiments.sh generate" || die "exp-3 generate 失败"
    popd >/dev/null

    step "exp-3 —— 提交 transform（15 个任务）"
    local TRANSFORM_IDS
    TRANSFORM_IDS=$(submit_and_collect_ids \
        "$SCRIPT_DIR/experiment-3-XOR/transform" "jobslurm-")
    ok "exp-3 transform IDs: $TRANSFORM_IDS"

    step "exp-3 —— 提交 GaussMaxHS solve（15 个任务，依赖 transform）"
    local SOLVE_IDS
    SOLVE_IDS=$(submit_with_dependency \
        "$SCRIPT_DIR/experiment-3-XOR/jobs" "jobslurm-" "$TRANSFORM_IDS")
    ok "exp-3 GaussMaxHS solve IDs: $SOLVE_IDS"

    EXP3_IDS="$TRANSFORM_IDS:$SOLVE_IDS"
}

# 最终状态
summary() {
    step "✅ 全部任务已提交 —— 可以关闭终端，SLURM 会自动跑"

    if [[ -n "$EXP2_IDS" ]]; then
        local N_EXP2=$(awk -F: '{print NF}' <<< "$EXP2_IDS")
        echo -e "  ${GREEN}exp-2${NC}: 共 ${N_EXP2} 个 SLURM job 已提交"
        echo -e "    （其中 RoundingSAT solve 自动等 transform 完成再跑，CPLEX 独立并行）"
    fi
    if [[ -n "$EXP3_IDS" ]]; then
        local N_EXP3=$(awk -F: '{print NF}' <<< "$EXP3_IDS")
        echo -e "  ${GREEN}exp-3${NC}: 共 ${N_EXP3} 个 SLURM job 已提交"
        echo -e "    （GaussMaxHS solve 自动等 transform 完成再跑）"
    fi

    echo ""
    echo -e "${BLUE}监控:${NC}    squeue -u \$USER"
    echo -e "${BLUE}取消所有:${NC}  scancel -u \$USER"
    echo ""
    echo -e "${BLUE}全部跑完后，汇总 CSV:${NC}"
    (( RUN_EXP2 )) && echo "    cd '$SCRIPT_DIR/experiment-2-k=3,4' && ./run_all_experiments.sh sumup"
    (( RUN_EXP3 )) && echo "    cd '$SCRIPT_DIR/experiment-3-XOR' && ./run_all_experiments.sh sumup"
    echo ""
    echo -e "${BLUE}结果 CSV 位置:${NC}"
    (( RUN_EXP2 )) && echo "    $SCRIPT_DIR/experiment-2-k=3,4/roundingsat/sumup/results/"
    (( RUN_EXP2 )) && echo "    $SCRIPT_DIR/experiment-2-k=3,4/cplex/sumup/results/"
    (( RUN_EXP3 )) && echo "    $SCRIPT_DIR/experiment-3-XOR/sumup/results/"
    echo ""
    echo -e "预计墙钟时间：每个 solve job 最多 10000 秒（~2.8h），SLURM 并发按集群负载。"
}

# main
main() {
    echo -e "${BLUE}"
    echo "============================================================"
    echo "  DiverseSAT supplementary experiments (exp-2 + exp-3)"
    echo "  one-click cluster runner"
    echo "============================================================"
    echo -e "${NC}"

    (( DRY_RUN )) && warn "DRY-RUN 模式：只打印命令，不执行"

    preflight
    smoke_test

    if ! confirm "前置检查全部通过，现在提交 SLURM 任务？"; then
        die "用户取消" 0
    fi

    run_exp2
    run_exp3
    summary
}

main "$@"
