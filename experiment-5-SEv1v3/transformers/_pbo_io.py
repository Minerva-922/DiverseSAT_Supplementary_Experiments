"""
Shared writer for OPB/PBO (pseudo-Boolean optimisation) instances, the
input format understood by RoundingSAT.

File format reminder (from the OPB spec used by RoundingSAT)::

    * #variable= <nv>
    * #constraint= <nc>
    min: +c1 x1 -c2 x2 ... ;
    +a11 x1 +a12 x2 ... >= b1 ;
    +a21 x1 +a22 x2 ... = b2 ;
    ...

We keep the same tiny helper class as the historical
``{IW,DW}_cnf_to_PBO.py`` encoders so files produced here are
bit-for-bit compatible with the existing RoundingSAT pipeline.
"""

from __future__ import annotations

from typing import Iterable, List, Sequence


class PBOWriter:
    """Minimal OPB writer preserved from DiverseSAT-supplementary-master."""

    def __init__(self) -> None:
        # "happy_sentry_0" keeps index 0 aside so that len(self.variables)
        # equals the index of the next fresh variable name.
        self.variables: dict[str, int | str] = {"happy_sentry_0": 0}
        self.objective: str = ""
        self.constraints: list[str] = []

    # ---- variable bookkeeping ------------------------------------------------
    def get_internal_lit(self, lit_name: object) -> str:
        """Map a signed-integer literal (as produced by pysat) to the
        ``x<k>`` (or ``~x<k>``) notation used in OPB files."""
        lit_name = str(lit_name)
        if lit_name.startswith("-"):
            name = lit_name[1:]
        else:
            name = lit_name
        if name not in self.variables:
            self.variables[name] = "x" + str(len(self.variables))
        if lit_name.startswith("-"):
            return "~" + str(self.variables[name])
        else:
            return str(self.variables[name])

    # ---- objective -----------------------------------------------------------
    def set_objective(
        self,
        coeffs: Sequence[int],
        vars: Sequence[object],
        minimize: bool = True,
    ) -> None:
        if not minimize:
            # RoundingSAT only minimises. Flip signs to encode a maximisation.
            minimize = True
            coeffs = [-c for c in coeffs]
        terms = []
        for c, v in zip(coeffs, vars):
            if c >= 0:
                terms.append(f"+{c} {self.get_internal_lit(v)}")
            else:
                terms.append(f"{c} {self.get_internal_lit(v)}")
        self.objective = f"min: {' '.join(terms)};"

    # ---- constraints ---------------------------------------------------------
    def add_clause(self, vars: Sequence[object]) -> None:
        """Add a clause (disjunction) as the PB constraint ``sum x_i >= 1``."""
        self.add_constraint([1] * len(vars), vars, ">=", 1)

    def add_constraint(
        self,
        coeffs: Sequence[int],
        vars: Sequence[object],
        op: str,
        rhs: int,
    ) -> None:
        assert op in (">=", "=", "<="), f"unsupported op {op!r}"
        if op == "<=":
            coeffs = [-c for c in coeffs]
            rhs = -rhs
            op = ">="
        terms = []
        for c, v in zip(coeffs, vars):
            if c >= 0:
                terms.append(f"+{c} {self.get_internal_lit(v)}")
            else:
                terms.append(f"{c} {self.get_internal_lit(v)}")
        self.constraints.append(f"{' '.join(terms)} {op} {rhs};")

    def extend_clauses(self, clauses: Iterable[Sequence[int]]) -> None:
        for c in clauses:
            self.add_clause(list(c))

    # ---- output --------------------------------------------------------------
    def write_to_file(self, filename: str) -> None:
        with open(filename, "w") as f:
            # -1 for the "happy_sentry_0" placeholder.
            f.write(f"* #variable= {len(self.variables) - 1}\n")
            f.write(f"* #constraint= {len(self.constraints)}\n")
            f.write(self.objective + "\n")
            for constraint in self.constraints:
                f.write(constraint + "\n")


def add_SEv1(pbo: PBOWriter, V, C, K: int, N: int) -> int:
    """Add the strict-lex SEv1 block (no Y variables, ternary version).

    Returns the number of clauses/constraints that were appended so the
    caller can verify counts in unit tests.
    """
    n_before = len(pbo.constraints)
    for i in range(1, K):
        pbo.add_clause([C(i, 1)])
        for j in range(1, N + 1):
            # C_{i,j} -> (V_{i,j} -> V_{i+1,j})
            pbo.add_clause([-C(i, j), -V(i, j), V(i + 1, j)])
        for j in range(1, N):
            # C_{i,j} /\ V_{i,j}=V_{i+1,j}  ->  C_{i,j+1}
            pbo.add_clause([-C(i, j), V(i, j), V(i + 1, j), C(i, j + 1)])
            pbo.add_clause([-C(i, j), -V(i, j), -V(i + 1, j), C(i, j + 1)])
    return len(pbo.constraints) - n_before


def add_SEv3_diagonal(pbo: PBOWriter, V, K: int) -> int:
    """Add the **SEv3** symmetry-elimination block, literally as defined
    in ``materials/14-symmetry_elimination.pdf`` (page 1, "Version 3"):

        V_{j, j}  ->  V_{i, j}         for j in {1, ..., K-1},
                                            i in {j+1, ..., K}

    i.e. binary clauses  (not V_{j,j}) OR V_{i,j}.

    Key properties (from the proof in the PDF):
      * No auxiliary variables — uses only the original diversity
        variables V_{i,j}.
      * Exactly K*(K-1)/2 binary clauses — the "square binary clauses"
        Sami described in the JAIR meeting (22:09 / 22:27).
      * Semantically forces V_{j,j} = min over i in {j,...,K} of V_{i,j}.
      * For every diverse-SAT solution A = (alpha_1, ..., alpha_K) the
        PDF proof constructs a permutation A' of A that satisfies the
        block, so SEv3 preserves *feasibility of the diverse problem*.
      * SEv3 is NOT a complete symmetry breaker — several permutations
        of the same set of models can survive, hence "eliminates some of
        the symmetries but not all of them".

    In experiment-5 this block is added **on top of SEv1** as a
    *heuristic overlay* (conjunction of SEv1 and SEv3).  This overlay
    is NOT guaranteed to preserve feasibility: SEv1's unique lex-minimal
    permutation and SEv3's diagonal-minimal permutation need not
    coincide, so conjoining them as hard constraints can make an
    otherwise-feasible instance UNSAT or force a strictly suboptimal
    diversity value (see v2.tex Remark ``rem:diagonal-vs-lex'').  The
    overlay is therefore reported only as a speculative heuristic
    complement to the ``SEv3 standalone'' configuration of
    experiment-4.

    Returns the number of clauses appended (should be K*(K-1)/2).
    """
    n_before = len(pbo.constraints)
    for j in range(1, K):
        for i in range(j + 1, K + 1):
            pbo.add_clause([-V(j, j), V(i, j)])
    return len(pbo.constraints) - n_before


# Back-compat alias — my first draft used a wrong "anchor column" reading.
add_SEv3_pairwise = add_SEv3_diagonal
