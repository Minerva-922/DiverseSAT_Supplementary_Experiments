#!/usr/bin/env python3
"""
Compile a CNF instance into an OPB (PBO) file suitable for RoundingSAT,
using the **One-Hot (OH)** diversity encoding together with the
**SEv1 + SEv3 heuristic overlay** symmetry-elimination scheme.

SEv1 (strict-lex, ternary form, see ``_pbo_io.add_SEv1``):
    Builds the C_{i,j} chain variables that enforce strict lexicographic
    ordering between consecutive model copies.  Contributes
    (K-1)*(3N-1) clauses and 2(K-1)N auxiliary variables.

SEv3 (diagonal dominance, see ``_pbo_io.add_SEv3_diagonal``):
    V_{j,j}  ->  V_{i,j}     for j in {1, ..., K-1}, i in {j+1, ..., K}
    K*(K-1)/2 binary clauses, no auxiliary variables.

WARNING -- this configuration is a *heuristic overlay*, NOT a sound
replacement for SEv1:  the canonical representative selected by SEv1
(lex-min permutation) and the one selected by SEv3 (diagonal-min
permutation) need not coincide, so conjoining them as hard constraints
may render otherwise-feasible Diverse SAT instances UNSAT or induce a
strictly suboptimal diversity value.  See v2.tex Remark
``rem:diagonal-vs-lex'' and experiment-5 README for a concrete witness
at (k=3, n=3).  Experiment-5 reports behaviour empirically.

Uniqueness: following the exp-1 / exp-2 / exp-4 convention, no
explicit distinctness constraint is enforced here either.
"""

import argparse
import os
import sys
import time

from pysat.formula import CNF, IDPool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _pbo_io import PBOWriter, add_SEv1, add_SEv3_diagonal  # noqa: E402


vpool = IDPool(start_from=1)
V = lambda i, j: vpool.id(f"V{i}@{j}")
U = lambda j, i: vpool.id(f"U{j}@{i}")
C = lambda i, j: vpool.id(f"C{i}@{j}")


def get_PBO(cnf: CNF, K: int) -> PBOWriter:
    pbo = PBOWriter()
    N = cnf.nv

    for i in range(1, K + 1):
        for clause in cnf.clauses:
            lits = []
            for l in clause:
                if l > 0:
                    lits.append(V(i, l))
                else:
                    lits.append(-V(i, -l))
            pbo.add_clause(lits)

    obj_coeffs = []
    obj_vars = []
    for j in range(1, N + 1):
        pbo.add_constraint([1] * (K + 1), [U(j, i) for i in range(0, K + 1)], "=", 1)
        pbo.add_constraint(
            coeffs=[i for i in range(1, K + 1)] + [1] * K,
            vars=[U(j, i) for i in range(1, K + 1)] + [-V(i, j) for i in range(1, K + 1)],
            op="=",
            rhs=K,
        )
        for i in range(1, K + 1):
            if i * (K - i) == 0:
                break
            obj_coeffs.append(i * (K - i))
            obj_vars.append(U(j, i))

    pbo.set_objective(obj_coeffs, obj_vars, minimize=False)

    add_SEv1(pbo, V, C, K, N)
    add_SEv3_diagonal(pbo, V, K)

    return pbo


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="python OH_SEv1v3_cnf_to_PBO.py <in.cnf> <out.opb> <K>"
    )
    parser.add_argument("input_path")
    parser.add_argument("output_path")
    parser.add_argument("K")
    args = parser.parse_args()

    start_time = time.time()
    cnf = CNF(from_file=args.input_path)
    read_end_time = time.time()

    PBO = get_PBO(cnf, int(args.K))
    transform_end_time = time.time()

    PBO.write_to_file(args.output_path)
    print_end_time = time.time()

    print(
        f"Benchmark {os.path.basename(args.input_path)} "
        f"whole_trans_time {print_end_time - start_time} "
        f"read_time {read_end_time - start_time} "
        f"transform_time {transform_end_time - read_end_time} "
        f"print_time {print_end_time - transform_end_time} "
        f"n_vars {len(PBO.variables) - 1} n_constraints {len(PBO.constraints)}"
    )
