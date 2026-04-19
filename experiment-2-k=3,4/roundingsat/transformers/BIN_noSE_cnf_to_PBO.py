from pysat.formula import CNF, IDPool
from math import floor, log2
import time
import os
import argparse


vpool = IDPool(start_from=1)
V = lambda i, j: vpool.id('V{0}@{1}'.format(i, j))
U = lambda j, r: vpool.id('U{0}@{1}'.format(j, r))
z = lambda j, r, rp: vpool.id('Z{0}@{1}@{2}'.format(j, r, rp))


class PBOWriter:
    def __init__(self):
        self.variables = {"happy_sentry_0": 0}
        self.objective = ""
        self.constraints = []

    def get_internal_lit(self, lit_name):
        lit_name = str(lit_name)
        if lit_name.startswith("-"):
            name = lit_name[1:]
        else:
            name = lit_name
        if name not in self.variables:
            self.variables[name] = "x" + str(len(self.variables))
        if lit_name.startswith("-"):
            return "~" + self.variables[name]
        else:
            return self.variables[name]

    def set_objective(self, coeffs, vars, minimize=True):
        if not minimize:
            minimize = True
            coeffs = [-c for c in coeffs]
        assert minimize == True
        terms = []
        for c, v in zip(coeffs, vars):
            if c >= 0:
                terms.append(f"+{c} {self.get_internal_lit(v)}")
            else:
                terms.append(f"{c} {self.get_internal_lit(v)}")
        self.objective = f"{'min' if minimize else 'max'}: {' '.join(terms)};"

    def add_clause(self, vars):
        self.add_constraint([1] * len(vars), vars, ">=", 1)

    def add_constraint(self, coeffs, vars, op, rhs):
        assert op in (">=", "=", "<=")
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

    def write_to_file(self, filename):
        with open(filename, 'w') as f:
            f.write(f"* #variable= {len(self.variables)}\n")
            f.write(f"* #constraints= {len(self.constraints)}\n")
            f.write(self.objective + "\n")
            for constraint in self.constraints:
                f.write(constraint + "\n")


def get_PBO(cnf, K):
    pbo = PBOWriter()
    N = cnf.nv
    logK = floor(log2(K))

    # CNF constraints for each of the K models
    for i in range(1, K + 1):
        for clause in cnf.clauses:
            lits = []
            for l in clause:
                if l > 0:
                    lits.append(V(i, l))
                else:
                    lits.append(-V(i, -l))
            pbo.add_clause(lits)

    # Binary counting constraint: sum 2^r * U[j,r] = sum V[i,j]
    for j in range(1, N + 1):
        pbo.add_constraint(
            coeffs=[2**r for r in range(logK + 1)] + [1] * K,
            vars=[U(j, r) for r in range(logK + 1)] + [-V(i, j) for i in range(1, K + 1)],
            op="=", rhs=K
        )

    # z linearization: clause form  -U[j,r] \/ -U[j,r'] \/ z[j,r,r']
    for j in range(1, N + 1):
        for r in range(logK + 1):
            for rp in range(logK + 1):
                pbo.add_clause([-U(j, r), -U(j, rp), z(j, r, rp)])

    # Objective: maximize sum K*2^r*U[j,r] - sum 2^(r+r')*z[j,r,r']
    obj_coeffs = []
    obj_vars = []
    for j in range(1, N + 1):
        for r in range(logK + 1):
            obj_coeffs.append(K * (2**r))
            obj_vars.append(U(j, r))
        for r in range(logK + 1):
            for rp in range(logK + 1):
                obj_coeffs.append(-(2**(r + rp)))
                obj_vars.append(z(j, r, rp))

    pbo.set_objective(obj_coeffs, obj_vars, minimize=False)
    return pbo


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="python this.py <path/to/cnf> <path/to/pbo> <K>")
    parser.add_argument("input_path", help="path/to/cnf")
    parser.add_argument("output_path", help="path/to/pbo")
    parser.add_argument("K", help="the number of models")
    args = parser.parse_args()

    start_time = time.time()
    cnf = CNF(from_file=args.input_path)
    read_end_time = time.time()

    PBO = get_PBO(cnf, int(args.K))
    transform_end_time = time.time()

    PBO.write_to_file(args.output_path)
    print_end_time = time.time()

    print(f"Benchmark {os.path.basename(args.input_path)} "
          f"whole_trans_time {print_end_time - start_time} "
          f"read_time {read_end_time - start_time} transform_time {transform_end_time - read_end_time} print_time {print_end_time - transform_end_time})")
