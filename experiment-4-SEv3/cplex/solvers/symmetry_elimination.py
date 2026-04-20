"""
Symmetry-elimination helpers for the CPLEX encodings used in
experiment-4 (SEv3 standalone).

Two helpers are exposed:

  * ``add_symmetry_elimination``
        The SEv1 lex-leader chain from experiment-1 / experiment-2,
        kept here verbatim so that exp-4's CPLEX solvers share the
        exact same reference implementation as the baselines.

  * ``add_symmetry_elimination_v3``
        The SEv3 "diagonal dominance" block from
        ``materials/14-symmetry_elimination.pdf`` (Version 3):

            V_{j,j}  ->  V_{i,j}    for j in {1..k-1}, i in {j+1..k}

        as K*(K-1)/2 binary clauses, no auxiliary variables.

The CPLEX-*-SEv3.py solver scripts in this directory use
``add_symmetry_elimination_v3`` (SEv3 standalone, per
Proposition~\\ref{prop:diagonal-dominance} in ``v2.tex``).
"""

import cplex


def add_symmetry_elimination(prob: cplex.Cplex, n: int, k: int):
    """
    Add SEv1 (strict-lex, lex-leader) constraints.

    C[i,j] indicates prefix equality between model i and model i+1 up
    to position j.

      SE-1: C[i,j]=1 AND V[i,j]=1 => V[i+1,j]=1
      SE-2: C[i,j]=1 AND V[i,j]=V[i+1,j] => C[i,j+1]=1
      SE-3: C[i,0]=1 (base case)
    """
    if n == 0 or k <= 1:
        return

    prob.variables.add(
        names=[f"C_{i}_{j}" for i in range(k - 1) for j in range(n)],
        types=[prob.variables.type.binary] * ((k - 1) * n)
    )

    for i in range(k - 1):
        prob.linear_constraints.add(
            lin_expr=[cplex.SparsePair([f"C_{i}_0"], [1])],
            senses=["E"], rhs=[1]
        )

        for j in range(n):
            prob.linear_constraints.add(
                lin_expr=[cplex.SparsePair(
                    [f"C_{i}_{j}", f"V_{i}_{j}", f"V_{i+1}_{j}"],
                    [1, 1, -1]
                )],
                senses=["L"], rhs=[1]
            )

        for j in range(n - 1):
            prob.linear_constraints.add(
                lin_expr=[cplex.SparsePair(
                    [f"C_{i}_{j}", f"V_{i}_{j}", f"V_{i+1}_{j}", f"C_{i}_{j+1}"],
                    [-1, 1, 1, 1]
                )],
                senses=["G"], rhs=[0]
            )
            prob.linear_constraints.add(
                lin_expr=[cplex.SparsePair(
                    [f"C_{i}_{j}", f"V_{i}_{j}", f"V_{i+1}_{j}", f"C_{i}_{j+1}"],
                    [-1, -1, -1, 1]
                )],
                senses=["G"], rhs=[-2]
            )


def add_symmetry_elimination_v3(prob: cplex.Cplex, n: int, k: int) -> int:
    """
    Add SEv3 "diagonal dominance" constraints, per
    ``materials/14-symmetry_elimination.pdf`` (Version 3):

        V_{j,j}  ->  V_{i,j}      for j in {1..k-1}, i in {j+1..k}

    Translated to 0-indexed CPLEX variables this becomes, for every
    jj in {0..min(k-1, n) - 1} and every ii in {jj+1..k-1}:

        V_{jj}_{jj}  <=  V_{ii}_{jj}        (linear:  V_jj_jj - V_ii_jj <= 0)

    No auxiliary variables are introduced; exactly
    ``min(k-1, n) * (something)`` constraints are added in total -- see
    below for the precise count when n >= k.

    When n >= k (the overwhelmingly common case in our benchmarks), the
    count is exactly ``k * (k - 1) / 2`` binary inequalities, matching
    the PBO / CNF version in ../transformers/_pbo_io.py.

    When n < k - 1, the diagonal positions V_{jj,jj} for jj >= n do not
    exist; in that case we silently skip those rows (they would have
    been vacuous anyway in the PDF definition, since the relevant
    column does not exist).

    Returns the number of constraints appended, so callers (or unit
    tests) can verify counts.
    """
    if n == 0 or k <= 1:
        return 0

    n_before = prob.linear_constraints.get_num()

    j_max = min(k - 1, n)  # exclusive bound on jj
    for jj in range(j_max):
        for ii in range(jj + 1, k):
            prob.linear_constraints.add(
                lin_expr=[cplex.SparsePair(
                    [f"V_{jj}_{jj}", f"V_{ii}_{jj}"],
                    [1, -1]
                )],
                senses=["L"], rhs=[0]
            )

    return prob.linear_constraints.get_num() - n_before
