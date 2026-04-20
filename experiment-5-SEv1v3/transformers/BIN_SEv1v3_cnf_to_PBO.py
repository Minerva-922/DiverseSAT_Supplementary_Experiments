#!/usr/bin/env python3
"""
BIN diversity encoding + SEv1 + SEv3 *heuristic overlay* symmetry
elimination.

See ``OH_SEv1v3_cnf_to_PBO.py`` for the header-level description and
the caveat that this overlay is NOT a sound replacement for SEv1 --
it may render otherwise-feasible Diverse SAT instances UNSAT, and is
reported as a speculative heuristic configuration only.
"""

import argparse
import os
import sys
import time
from math import floor, log2

from pysat.formula import CNF, IDPool
from pysat.pb import PBEnc, EncType

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _pbo_io import PBOWriter, add_SEv1, add_SEv3_diagonal  # noqa: E402


PB_encoding = EncType.best

vpool = IDPool(start_from=1)
V = lambda i, j: vpool.id(f"V{i}@{j}")
U = lambda j, i: vpool.id(f"U{j}@{i}")
Z = lambda j, i, ip: vpool.id(f"Z{j}@{i}@{ip}")
C = lambda i, j: vpool.id(f"C{i}@{j}")


def get_PBO(cnf: CNF, K: int) -> PBOWriter:
    pbo = PBOWriter()
    N = cnf.nv
    logK = floor(log2(K))

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
        pbo.add_constraint(
            coeffs=[2 ** i for i in range(0, logK + 1)] + [1] * K,
            vars=[U(j, i) for i in range(0, logK + 1)] + [-V(i, j) for i in range(1, K + 1)],
            op="=",
            rhs=K,
        )
        for i in range(0, logK + 1):
            obj_coeffs.append(K * (2 ** i))
            obj_vars.append(U(j, i))
            for ip in range(0, logK + 1):
                pbo.add_clause([-U(j, i), -U(j, ip), Z(j, i, ip)])
                obj_coeffs.append(-(2 ** (i + ip)))
                obj_vars.append(Z(j, i, ip))

    pbo.set_objective(obj_coeffs, obj_vars, minimize=False)

    add_SEv1(pbo, V, C, K, N)
    add_SEv3_diagonal(pbo, V, K)

    return pbo


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="python BIN_SEv1v3_cnf_to_PBO.py <in.cnf> <out.opb> <K>"
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
