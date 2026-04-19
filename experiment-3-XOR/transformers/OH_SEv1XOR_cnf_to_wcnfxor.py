#!/usr/bin/env python3
"""
Compile CNF -> CNF+XOR WDIMACS (GaussMaxHS) with the **One-Hot (OH)**
diversity encoding and SEv1-XOR symmetry elimination.

See the sibling file ``UNA_SEv1XOR_cnf_to_wcnfxor.py`` for a description
of the SEv1-XOR scheme.
"""

import argparse
import os
import sys
import time

from pysat.formula import CNF, IDPool
from pysat.pb import PBEnc, EncType
import pysat.card as card

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wcnfxor_io import WcnfXor  # noqa: E402


PB_encoding = EncType.best

vpool = IDPool(start_from=1)
V = lambda i, j: vpool.id(f"V{i}@{j}")
U = lambda j, i: vpool.id(f"U{j}@{i}")
C = lambda i, j: vpool.id(f"C{i}@{j}")
Y = lambda i, j: vpool.id(f"Y{i}@{j}")


def get_wcnfxor(cnf: CNF, K: int) -> tuple[WcnfXor, int, int]:
    wcnf = WcnfXor()
    N = cnf.nv
    obj_sum = 0
    delta = 0

    # k parallel copies of the CNF.
    for i in range(1, K + 1):
        for clause in cnf.clauses:
            lits = []
            for l in clause:
                if l > 0:
                    lits.append(V(i, l))
                else:
                    lits.append(-V(i, -l))
            wcnf.append(lits)

    # --- One-Hot diversity objective ---
    for j in range(1, N + 1):
        wcnf.extend(
            card.CardEnc.equals(
                lits=[U(j, i) for i in range(0, K + 1)],
                bound=1,
                encoding=card.EncType.cardnetwrk,
                vpool=vpool,
            )
        )

        wcnf.extend(
            PBEnc.equals(
                lits=[U(j, i) for i in range(1, K + 1)] + [-V(i, j) for i in range(1, K + 1)],
                weights=[i for i in range(1, K + 1)] + [1] * K,
                bound=K,
                vpool=vpool,
                encoding=PB_encoding,
            )
        )
        for i in range(1, K + 1):
            if i * (K - i) == 0:
                break
            obj_sum += i * (K - i)
            wcnf.append([U(j, i)], i * (K - i))

    # --- Symmetry elimination: SEv1 with explicit Y as native XOR ---
    for i in range(1, K):
        wcnf.append([C(i, 1)])

        for j in range(1, N + 1):
            wcnf.append([-C(i, j), -V(i, j), V(i + 1, j)])

        for j in range(1, N):
            wcnf.append([-C(i, j), Y(i, j), C(i, j + 1)])

        for j in range(1, N + 1):
            wcnf.append_xor([Y(i, j), V(i, j), V(i + 1, j)], rhs=0)

        # Note: SE-5 (big-OR of Y, strict distinctness) is intentionally
        # OMITTED so that exp-3 matches the exp-1/exp-2 SEv1 baseline
        # semantically (non-strict lex).  Distinctness emerges from the
        # diversity objective at the optimum.

    return wcnf, obj_sum, delta


def main() -> None:
    parser = argparse.ArgumentParser(
        description="python OH_SEv1XOR_cnf_to_wcnfxor.py <in.cnf> <out.wcnfxor> <K>"
    )
    parser.add_argument("input_path", help="path/to/input.cnf")
    parser.add_argument("output_path", help="path/to/output.wcnfxor")
    parser.add_argument("K", help="the number of diverse models")
    args = parser.parse_args()

    start_time = time.time()
    cnf = CNF(from_file=args.input_path)
    read_end_time = time.time()

    wcnf, obj_sum, delta = get_wcnfxor(cnf, int(args.K))
    transform_end_time = time.time()

    wcnf.to_file(args.output_path)
    print_end_time = time.time()

    print(
        f"Benchmark {os.path.basename(args.input_path)} obj_sum {obj_sum} delta {delta} "
        f"whole_trans_time {print_end_time - start_time} "
        f"read_time {read_end_time - start_time} transform_time {transform_end_time - read_end_time} "
        f"print_time {print_end_time - transform_end_time} "
        f"n_xor_clauses {len(wcnf.xor)} n_hard {len(wcnf.hard)} n_soft {len(wcnf.soft)}"
    )


if __name__ == "__main__":
    main()
