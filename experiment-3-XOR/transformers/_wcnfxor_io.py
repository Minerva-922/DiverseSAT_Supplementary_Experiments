"""
Helper that knows how to serialise a Weighted Partial MaxSAT instance
extended with native XOR hard clauses in the CNF+XOR WDIMACS dialect
understood by GaussMaxHS (https://github.com/meelgroup/gaussmaxhs).

File format (a superset of standard WDIMACS):

    c comment lines start with 'c'
    p wcnf <nvars> <nclauses> <top>
    <w>   <lit> <lit> ... 0           # regular weighted CNF clause
    x <w> <lit> <lit> <lit> ... 0     # hard XOR clause (length >= 3)

Conventions used by GaussMaxHS:
    * `<w>` on an XOR line must equal the hard / `top` weight.
    * `x <w>  l1 l2 ... lm 0`        asserts   l1 XOR l2 XOR ... XOR lm  = 1
    * `x <w> -l1 l2 ... lm 0`        asserts   l1 XOR l2 XOR ... XOR lm  = 0
      (negating a literal flips the parity of the XOR).
    * All XORs must be hard and at least 3 literals long.

We use a tiny `WcnfXor` container that mirrors the parts of
`pysat.formula.WCNF` we need plus a list of XOR constraints.
"""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple


class WcnfXor:
    """Weighted Partial MaxSAT instance with optional hard XOR constraints."""

    def __init__(self) -> None:
        self.nv: int = 0
        # Hard CNF clauses (list of literals).
        self.hard: List[List[int]] = []
        # Soft CNF clauses and their weights (parallel lists).
        self.soft: List[List[int]] = []
        self.wght: List[int] = []
        # Hard XOR clauses. Each entry: (literals, rhs) where rhs ∈ {0, 1}
        # and (XOR of literals) == rhs.
        self.xor: List[Tuple[List[int], int]] = []

    # ---- adding clauses ----
    def _bump_nv(self, lits: Sequence[int]) -> None:
        for l in lits:
            if abs(l) > self.nv:
                self.nv = abs(l)

    def append(self, clause: Sequence[int], weight: int | None = None) -> None:
        """Append a CNF clause. weight=None means hard."""
        lits = list(clause)
        self._bump_nv(lits)
        if weight is None:
            self.hard.append(lits)
        else:
            self.soft.append(lits)
            self.wght.append(int(weight))

    def extend(self, clauses: Iterable[Sequence[int]], weight: int | None = None) -> None:
        for c in clauses:
            self.append(c, weight)

    def append_xor(self, lits: Sequence[int], rhs: int = 1) -> None:
        """Append a hard XOR clause  (XOR of lits) == rhs, rhs ∈ {0, 1}."""
        if rhs not in (0, 1):
            raise ValueError(f"rhs must be 0 or 1, got {rhs}")
        if len(lits) < 3:
            raise ValueError(
                f"GaussMaxHS requires XOR clauses of length >= 3; got {len(lits)} literals: {list(lits)}"
            )
        lits = list(lits)
        self._bump_nv(lits)
        self.xor.append((lits, int(rhs)))

    # ---- serialisation ----
    def to_file(self, path: str, top: int | None = None) -> None:
        """Write the instance in GaussMaxHS CNF+XOR WDIMACS format."""
        # Hard weight (``top``) must be strictly greater than the sum of soft
        # weights, as per the Weighted Partial MaxSAT convention.
        if top is None:
            total_soft = sum(self.wght) if self.wght else 0
            top = total_soft + 1

        nb_clauses = len(self.hard) + len(self.soft) + len(self.xor)

        with open(path, "w") as f:
            f.write(f"c CNF+XOR MaxSAT (GaussMaxHS dialect)\n")
            f.write(f"c   vars={self.nv}  hard_cnf={len(self.hard)}"
                    f"  soft={len(self.soft)}  xor={len(self.xor)}\n")
            f.write(f"p wcnf {self.nv} {nb_clauses} {top}\n")

            for clause in self.hard:
                f.write(f"{top} " + " ".join(str(l) for l in clause) + " 0\n")

            for clause, w in zip(self.soft, self.wght):
                f.write(f"{w} " + " ".join(str(l) for l in clause) + " 0\n")

            # XOR clauses: "x <top> <lits> 0" for rhs=1, flip one lit for rhs=0.
            for lits, rhs in self.xor:
                out_lits = list(lits)
                if rhs == 0:
                    # Flip the sign of the first literal to invert the RHS parity.
                    out_lits[0] = -out_lits[0]
                f.write(f"x {top} " + " ".join(str(l) for l in out_lits) + " 0\n")
