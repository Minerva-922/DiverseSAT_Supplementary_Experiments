import cplex
from pysat.formula import CNF
import time
import sys
import os
from symmetry_elimination import add_symmetry_elimination


def parse_cnf_file(input_file: str):
    formula = CNF(from_file=input_file)
    return formula.nv, formula.clauses

def create_cplex_instance() -> cplex.Cplex:
    prob = cplex.Cplex()
    prob.objective.set_sense(prob.objective.sense.maximize)

    prob.parameters.threads.set(1)
    prob.parameters.clocktype.set(1)
    prob.parameters.timelimit.set(7200)

    prob.set_log_stream(None)
    prob.set_error_stream(None)
    prob.set_warning_stream(None)
    prob.parameters.mip.tolerances.integrality.set(0)
    prob.parameters.mip.tolerances.mipgap.set(0)
    prob.parameters.mip.tolerances.absmipgap.set(0)

    return prob

def create_variables(prob: cplex.Cplex, n: int, k: int):
    prob.variables.add(
        names=[f"V_{i}_{j}" for i in range(k) for j in range(n)],
        types=[prob.variables.type.binary] * (k * n)
    )

    prob.variables.add(
        names=[f"U_{j}_{r}" for j in range(n) for r in range(1, k+1)],
        types=[prob.variables.type.binary] * (n*k),
        obj=[r*(k-r)-(r-1)*(k-r+1) for j in range(n) for r in range(1, k+1)]
    )


def add_cnf_constraints(prob: cplex.Cplex, n: int, k: int, clauses):
    for i in range(k):
        for clause in clauses:
            vars_in_clause = []
            coeffs_in_clause = []
            for lit in clause:
                var = abs(lit) - 1
                coef = 1 if lit > 0 else -1
                vars_in_clause.append(f"V_{i}_{var}")
                coeffs_in_clause.append(coef)
            prob.linear_constraints.add(
                lin_expr=[cplex.SparsePair(vars_in_clause, coeffs_in_clause)],
                senses=["G"],
                rhs=[1 - len([lit for lit in clause if lit < 0])]
            )

def add_counting_constraints(prob: cplex.Cplex, n: int, k: int):
    for j in range(n):
        v_vars = [f"V_{i}_{j}" for i in range(k)]
        u_vars = [f"U_{j}_{r}" for r in range(1, k+1)]

        prob.linear_constraints.add(
            lin_expr=[cplex.SparsePair(
                v_vars + u_vars,
                [1] * k + [-1 for r in range(1, k+1)]
            )],
            senses=["E"],
            rhs=[0]
        )

        for r in range(2, k + 1):
            prob.linear_constraints.add(
                lin_expr=[cplex.SparsePair([f"U_{j}_{r}", f"U_{j}_{r-1}"], [1, -1])],
                senses=["L"],
                rhs=[0]
            )

if __name__ == '__main__':
    cnf_file = sys.argv[1]
    k = int(sys.argv[2])

    start_time = time.time()
    n, clauses = parse_cnf_file(cnf_file)
    read_end_time = time.time()

    prob = create_cplex_instance()
    create_variables(prob, n, k)
    add_cnf_constraints(prob, n, k, clauses)
    add_counting_constraints(prob, n, k)
    add_symmetry_elimination(prob, n, k)
    trans_end_time = time.time()

    prob.solve()
    end_time = time.time()

    if prob.solution.is_primal_feasible():
        print("Solution is feasible.")
    else:
        print("Solution is infeasible.")

    print("\n---------------------")
    print(f"@@@ {prob.solution.status[prob.solution.get_status()]}")
    print(f">>> Benchmark {os.path.basename(cnf_file)} k {k} OPT {int(prob.solution.get_objective_value())}"
          f" TimeCost {end_time - start_time} TimeSolve {end_time - trans_end_time} TimeRead {read_end_time - start_time} TimeTrans {trans_end_time - read_end_time}")
