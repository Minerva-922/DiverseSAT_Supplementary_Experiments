import cplex


def add_symmetry_elimination(prob: cplex.Cplex, n: int, k: int):
    """
    Add Symmetry Elimination v1 (lexicographic ordering) constraints.
    C[i,j] indicates prefix equality between model i and model i+1 up to position j.

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
        # SE-3: C[i,0] = 1
        prob.linear_constraints.add(
            lin_expr=[cplex.SparsePair([f"C_{i}_0"], [1])],
            senses=["E"], rhs=[1]
        )

        # SE-1: C[i,j] + V[i,j] - V[i+1,j] <= 1
        for j in range(n):
            prob.linear_constraints.add(
                lin_expr=[cplex.SparsePair(
                    [f"C_{i}_{j}", f"V_{i}_{j}", f"V_{i+1}_{j}"],
                    [1, 1, -1]
                )],
                senses=["L"], rhs=[1]
            )

        # SE-2: prefix propagation
        for j in range(n - 1):
            # Case 1: V[i,j]=0, V[i+1,j]=0 => propagate
            # -C[i,j] + V[i,j] + V[i+1,j] + C[i,j+1] >= 0
            prob.linear_constraints.add(
                lin_expr=[cplex.SparsePair(
                    [f"C_{i}_{j}", f"V_{i}_{j}", f"V_{i+1}_{j}", f"C_{i}_{j+1}"],
                    [-1, 1, 1, 1]
                )],
                senses=["G"], rhs=[0]
            )
            # Case 2: V[i,j]=1, V[i+1,j]=1 => propagate
            # -C[i,j] - V[i,j] - V[i+1,j] + C[i,j+1] >= -2
            prob.linear_constraints.add(
                lin_expr=[cplex.SparsePair(
                    [f"C_{i}_{j}", f"V_{i}_{j}", f"V_{i+1}_{j}", f"C_{i}_{j+1}"],
                    [-1, -1, -1, 1]
                )],
                senses=["G"], rhs=[-2]
            )
