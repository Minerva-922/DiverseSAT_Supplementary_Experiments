"""
Aggregate GaussMaxHS solve results (experiment-3) into CSV tables.

GaussMaxHS is a CNF+XOR MaxSAT solver built on top of MaxHS, so the
per-instance log lines match the standard MaxHS format — we reuse the
``maxhs`` parser for them.
"""

import os
import csv
import re
from collections import defaultdict

# Configuration
RESULT_ROOT_DIR = "../jobs/results/"
OUTPUT_DIR = './results'

# Directory naming pattern: result-{solver}-k_{k_value}-{encoding}-{symmetry}-{timestamp}
# symmetry examples: SE, SEv1, SEv1XOR, SEv3, noSE, ...
DIR_PATTERN = re.compile(r'^result-(.+?)-k_(\d+)-([A-Z]+)-((?:SE|no)[A-Za-z0-9]*)-(\d{14})$')


def parse_directory_name(dirname):
    match = DIR_PATTERN.match(dirname)
    if match:
        return match.group(1), match.group(2), match.group(3), match.group(4), match.group(5)
    return None


def get_solver_type(solver_name):
    """Map solver name to parser key. GaussMaxHS uses the MaxHS format."""
    solver_mapping = {
        'gaussmaxhs': 'maxhs',
        'GaussMaxHS': 'maxhs',
        'maxhs': 'maxhs',
    }
    for key, value in solver_mapping.items():
        if solver_name.startswith(key):
            return value
    return None


def scan_result_directories(root_dir):
    if not os.path.exists(root_dir):
        raise ValueError(f"Result directory does not exist: {root_dir}")

    configs = defaultdict(list)
    unparseable_dirs = []
    for dirname in os.listdir(root_dir):
        full_path = os.path.join(root_dir, dirname)
        if not os.path.isdir(full_path):
            continue
        parsed = parse_directory_name(dirname)
        if parsed is None:
            unparseable_dirs.append(dirname)
            continue
        solver, k_value, encoding, symmetry, timestamp = parsed
        configs[(solver, k_value, encoding, symmetry)].append((timestamp, full_path))

    if unparseable_dirs:
        msg = "ERROR: Cannot parse the following directories:\n"
        for d in unparseable_dirs:
            msg += f"  - {d}\n"
        msg += "\nExpected format: result-<solver>-k_<K>-<encoding>-<symmetry>-<timestamp>"
        raise ValueError(msg)

    duplicates = [(k, v) for k, v in configs.items() if len(v) > 1]
    if duplicates:
        msg = "ERROR: Found duplicate configurations with different timestamps:\n"
        for config_key, paths in duplicates:
            solver, k_value, encoding, symmetry = config_key
            msg += f"\n  Config: solver={solver}, k={k_value}, encoding={encoding}, symmetry={symmetry}\n"
            for t, p in sorted(paths):
                msg += f"    - {t}: {p}\n"
        raise ValueError(msg)

    return configs


def generate_csv_filename(solver, k_value, encoding, symmetry):
    return f"{solver}-{encoding}-k{k_value}-{symmetry}.csv"


def custom_sort(record):
    name = record[0]
    parts = re.split(r'([0-9]*\.[0-9]+|[0-9]+)', name)
    converted_parts = []
    for part in parts:
        if part.isdigit():
            converted_parts.append(int(part))
        elif re.match(r'[0-9]*\.[0-9]+', part):
            converted_parts.append(float(part))
        elif part:
            converted_parts.append(part)
    if converted_parts and type(converted_parts[0]) == int:
        return tuple([str(converted_parts[0])] + converted_parts[1:])
    return tuple(converted_parts)


def get_maxhs_record(filename, filepath):
    Benchmark = (filename.replace(".wcnfxor", "").replace(".wcnf_old", "")
                 .replace(".wcnf", "").replace(".cnf", "").replace(".out", ""))
    OPT = None
    is_BEST = 0
    nb_var = None
    nb_cons = None
    nb_xor = None
    tot_time = None
    parse_time = None
    solving_time = None
    with open(filepath, 'r') as file:
        lines = file.readlines()
    for line in lines:
        line = line.strip()
        if line.startswith('o'):
            OPT = line.split()[1]
        elif line.startswith('c Parse time:'):
            parse_time = float(line.split()[-2])
        elif line.startswith('s OPTIMUM FOUND'):
            is_BEST = 1
        elif line.startswith('c #vars: '):
            nb_var = int(line.split()[-1])
        elif line.startswith('c #Clauses: '):
            nb_cons = int(line.split()[-1])
        elif line.startswith('c #XORs: ') or line.startswith('c xors: '):
            try:
                nb_xor = int(line.split()[-1])
            except ValueError:
                pass
        elif line.startswith('c CPU'):
            tot_time = float(line.split(":")[1].strip().split(" ")[0])
            solving_time = tot_time
    return Benchmark, nb_var, nb_cons, nb_xor, is_BEST, OPT, parse_time, tot_time, solving_time


def process_configuration(config_key, dir_path, file_type):
    records = []
    for filename in os.listdir(dir_path):
        filepath = os.path.join(dir_path, filename)
        if os.path.isfile(filepath) and filename.endswith('.out'):
            try:
                if file_type == 'maxhs':
                    records.append(get_maxhs_record(filename, filepath))
            except Exception as e:
                print(f"Warning: Error processing {filepath}: {e}")
    return records


def get_csv_header(file_type):
    if file_type == 'maxhs':
        return ['Benchmark', 'nb_var', 'nb_cons', 'nb_xor', 'is_OPT', 'BEST',
                'parse_time', 'tot_time', 'solving_time']
    return []


def main():
    print(f"Scanning result directory: {RESULT_ROOT_DIR}")
    try:
        configs = scan_result_directories(RESULT_ROOT_DIR)
    except ValueError as e:
        print(str(e))
        return

    print(f"\nFound {len(configs)} unique configurations:")
    for config_key in sorted(configs.keys()):
        print(f"  - {config_key}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for config_key, paths in configs.items():
        solver, k_value, encoding, symmetry = config_key
        timestamp, dir_path = paths[0]

        file_type = get_solver_type(solver)
        if file_type is None:
            raise ValueError(f"Cannot determine file type for solver: {solver}")

        csv_filename = generate_csv_filename(solver, k_value, encoding, symmetry)
        csv_path = os.path.join(OUTPUT_DIR, csv_filename)
        print(f"\nProcessing: {csv_filename}")
        print(f"  Directory: {os.path.basename(dir_path)}")

        records = process_configuration(config_key, dir_path, file_type)
        if not records:
            print(f"  Warning: No records found in {dir_path}")
            continue

        sorted_records = sorted(records, key=custom_sort)
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(get_csv_header(file_type))
            writer.writerows(sorted_records)
        print(f"  ✓ Wrote {len(sorted_records)} records to {csv_filename}")

    print(f"\n✓ All done! Output files in: {OUTPUT_DIR}")


if __name__ == '__main__':
    main()
