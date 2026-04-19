#!/usr/bin/env python3
"""
Compile a CNF instance into a CNF+XOR WDIMACS (GaussMaxHS) file using the
**Unary (UNA)** diversity encoding and the **SEv1-XOR** variant of the
symmetry-elimination constraints.

SEv1-XOR has the **same semantics** as the exp-1 / exp-2 SEv1 baseline
(non-strict lexicographic ordering; no explicit distinctness — that
emerges from the max-diversity objective).  The only change is in
**how SE-2 and SE-4 are encoded**: we introduce a Y variable

        Y_{i,j} <=> V_{i,j} XOR V_{i+1,j}                       (SE-4)

and write SE-4 as a single *native* XOR hard clause instead of four
CNF clauses; SE-2 becomes a compact 3-literal clause
``C_{i,j} /\ -Y_{i,j} -> C_{i,j+1}``.  SE-1 and SE-3 are unchanged.
SE-5 (distinctness big-OR) is **intentionally NOT added** here, to
keep the encoded problem identical to the exp-1 / exp-2 baseline.

The resulting file can be fed directly to
    https://github.com/meelgroup/gaussmaxhs
which performs Gauss-Jordan elimination on the XOR module while delegating
the weighted CNF part to MaxHS.
"""

import argparse
import os
import sys
import time
from math import ceil, floor

from pysat.formula import CNF, IDPool
import pysat.card as card

# Make the sibling helper importable regardless of CWD.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wcnfxor_io import WcnfXor  # noqa: E402


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

    # k parallel copies of the original CNF (hard clauses).
    for i in range(1, K + 1):
        for clause in cnf.clauses:
            lits = []
            for l in clause:
                if l > 0:
                    lits.append(V(i, l))
                else:
                    lits.append(-V(i, -l))
            wcnf.append(lits)

        # Enforce U(j, i) -> U(j, i-1) (unary/thermometer encoding of counts).
        if i > 1:
            for j in range(1, N + 1):
                wcnf.append([-U(j, i), U(j, i - 1)])

    # --- Unary diversity objective encoding ---
    for j in range(1, N + 1):
        wcnf.extend(
            card.CardEnc.equals(
                lits=[U(j, i) for i in range(1, K + 1)] + [-V(i, j) for i in range(1, K + 1)],
                bound=K,
                encoding=card.EncType.cardnetwrk,
                vpool=vpool,
            )
        )
        for i in range(1, K + 1):
            f = i * (K - i) - (i - 1) * (K - i + 1)
            if f == 0:
                continue
            elif f > 0:
                wcnf.append([U(j, i)], f)
                obj_sum += f
            else:
                delta -= f
                obj_sum -= f
                wcnf.append([-U(j, i)], -f)

    # --- Symmetry elimination: SEv1 with explicit Y as native XOR ---
    for i in range(1, K):
        # SE-3: C_{i,1} = 1
        wcnf.append([C(i, 1)])

        for j in range(1, N + 1):
            # SE-1: C_{i,j} -> (-V_{i,j} \/ V_{i+1,j})
            wcnf.append([-C(i, j), -V(i, j), V(i + 1, j)])

        for j in range(1, N):
            # SE-2: C_{i,j} /\ -Y_{i,j} -> C_{i,j+1}
            wcnf.append([-C(i, j), Y(i, j), C(i, j + 1)])

        # SE-4: Y_{i,j} <-> (V_{i,j} XOR V_{i+1,j})
        #       encoded as:  Y_{i,j} XOR V_{i,j} XOR V_{i+1,j} = 0
        for j in range(1, N + 1):
            wcnf.append_xor([Y(i, j), V(i, j), V(i + 1, j)], rhs=0)

        # Note: SE-5 (big-OR of Y, strict distinctness) is intentionally
        # OMITTED here so that exp-3 matches the exp-1/exp-2 SEv1 baseline
        # semantically (non-strict lexicographic ordering).  Distinctness is
        # enforced implicitly by the max-diversity objective.

    return wcnf, obj_sum, delta


def main() -> None:
    parser = argparse.ArgumentParser(
        description="python UNA_SEv1XOR_cnf_to_wcnfxor.py <in.cnf> <out.wcnfxor> <K>"
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
