import os
import csv
import re
from collections import defaultdict

# Configuration
RESULT_ROOT_DIR = "../jobs/results/"
OUTPUT_DIR = './results'

# CPLEX result dir naming: result-{solver_name}-benchmarks-k_{k}-{encoding}-{SE_mode}-{timestamp}
# e.g. result-CPLEX-BIN-SE-benchmarks-k_2-BIN-SE-20260322123456
DIR_PATTERN = re.compile(r'^result-(.+?)-benchmarks-k_(\d+)-([A-Z]+)-((?:SE|no)\w*)-(\d{14})$')

def parse_directory_name(dirname):
    """
    Parse directory name to extract configuration parameters.
    Returns: (solver, k_value, encoding, symmetry, timestamp) or None if parsing fails
    """
    match = DIR_PATTERN.match(dirname)
    if match:
        solver = match.group(1)
        k_value = match.group(2)
        encoding = match.group(3)
        symmetry = match.group(4)
        timestamp = match.group(5)
        return (solver, k_value, encoding, symmetry, timestamp)
    return None

def get_solver_type(solver_name):
    """Map solver name to file type for record parsing."""
    solver_mapping = {
        'RC2': 'rc2',
        'maxhs': 'maxhs',
        'wmaxcdcl_24': 'wmaxcdcl',
        'CASHWMaxSAT_DisjCom_noscip': 'cash',
        'open-wbo': 'open',
        'roundingSAT': 'rounding',
        'CPLEX': 'cplex',
    }
    
    for key, value in solver_mapping.items():
        if solver_name.startswith(key):
            return value
    
    return None

def scan_result_directories(root_dir):
    """
    Scan result directory and organize by configuration.
    Returns: dict mapping (solver, k, encoding, symmetry) -> list of (timestamp, full_path)
    Raises: ValueError if parsing fails or duplicates found
    """
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
        config_key = (solver, k_value, encoding, symmetry)
        configs[config_key].append((timestamp, full_path))
    
    # Check for unparseable directories
    if unparseable_dirs:
        error_msg = f"ERROR: Cannot parse the following directories:\n"
        for dirname in unparseable_dirs:
            error_msg += f"  - {dirname}\n"
        error_msg += "\nExpected format: result-<solver>-k_<K>-<encoding>-<symmetry>-<timestamp>"
        raise ValueError(error_msg)
    
    # Check for duplicate configurations (same config, different timestamps)
    duplicates = []
    for config_key, paths in configs.items():
        if len(paths) > 1:
            solver, k_value, encoding, symmetry = config_key
            duplicates.append((config_key, paths))
    
    if duplicates:
        error_msg = "ERROR: Found duplicate configurations with different timestamps:\n"
        for config_key, paths in duplicates:
            solver, k_value, encoding, symmetry = config_key
            error_msg += f"\n  Config: solver={solver}, k={k_value}, encoding={encoding}, symmetry={symmetry}\n"
            for timestamp, path in sorted(paths):
                error_msg += f"    - {timestamp}: {path}\n"
        error_msg += "\nPlease remove duplicate directories or rename them to have unique configurations."
        raise ValueError(error_msg)
    
    return configs

def generate_csv_filename(solver, k_value, encoding, symmetry):
    """Generate CSV filename based on configuration."""
    # Normalize solver name for CSV
    solver_clean = solver.replace('CASHWMaxSAT_DisjCom_noscip', 'CASH')
    solver_clean = solver_clean.replace('wmaxcdcl_24', 'wmaxcdcl')
    
    return f"{solver_clean}-{encoding}-k{k_value}-{symmetry}.csv"

def custom_sort(record):
    """Sort records by benchmark name, handling numeric parts properly"""
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
    if type(converted_parts[0]) == int:
        return tuple([str(converted_parts[0])] + converted_parts[1:])
    return tuple(converted_parts)

# [Keep all the get_*_record functions unchanged]
def get_maxhs_record(filename, filepath):
    Benchmark = filename.replace(".3pm", "").replace(".wcnf_old", "").replace(".wcnf", "").replace(".cnf", "").replace(".lp", "").replace(".proto", "").replace(".out", "")
    OPT = None
    is_BEST = 0
    nb_var = None
    nb_cons = None
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
        elif line.startswith('c CPU'):
            tot_time = float(line.split(":")[1].strip().split(" ")[0])
            solving_time = tot_time
    return Benchmark, nb_var, nb_cons, is_BEST, OPT, parse_time, tot_time, solving_time

def get_wmaxcdcl_record(filename, filepath):
    Benchmark = filename.replace(".3pm", "").replace(".wcnf_old", "").replace(".wcnf", "").replace(".lp", "").replace(".proto", "").replace(".out", "")
    OPT = None
    is_BEST = 0
    nb_var = None
    nb_cons = None
    tot_time = None
    parse_time = None
    solving_time = None
    with open(filepath, 'r') as file:
        lines = file.readlines()
    for line in lines:
        line = line.strip()
        if line.startswith('o'):
            OPT = line.split()[1]
        elif line.startswith('c |  Parse time: '):
            parse_time = float(line.split()[4])
        elif line.startswith('s OPTIMUM FOUND'):
            is_BEST = 1
        elif line.startswith('c |  Number of variables:  '):
            nb_var = int(line.split()[5])
        elif line.startswith('c |  Number of clauses:       '):
            nb_cons = int(line.split()[5])
        elif line.startswith('c CPU'):
            tot_time = float(line.split()[4])
            solving_time = tot_time
    return Benchmark, nb_var, nb_cons, is_BEST, OPT, parse_time, tot_time, solving_time

def get_cash_record(filename, filepath):
    OPT_val = None
    BEST = None
    solving_time = None
    is_OPT = 0
    benchmark_name = filename.replace(".3pm", "").replace(".wcnf_old", "").replace(".wcnf", "").replace(".lp", "").replace(".proto", "").replace(".out", "")
    with open(filepath, 'r') as file:
        lines = file.readlines()
    for line in lines:
        line = line.strip()
        if line.startswith('o'):
            OPT_val = line.split()[1]
        elif line.startswith('c Found solution:'):
            BEST = int(line.strip().split()[-1])
        elif line.startswith('s OPTIMUM FOUND'):
            is_OPT = 1
        elif line.startswith('CPUTIME='):
            solving_time = line.strip().replace("CPUTIME=", "").split()[0]
    return benchmark_name, BEST, is_OPT, OPT_val, solving_time

def get_open_record(filename, filepath):
    Benchmark = filename.replace(".3pm", "").replace(".wcnf_old", "").replace(".wcnf", "").replace(".lp", "").replace(".proto", "").replace(".out", "")
    OPT = None
    is_BEST = 0
    nb_var = None
    nb_hard = None
    nb_soft = None
    tot_time = None
    parse_time = None
    solving_time = None
    with open(filepath, 'r') as file:
        lines = file.readlines()
    for line in lines:
        line = line.strip()
        if line.startswith('o'):
            OPT = line.split()[1]
        elif line.startswith('c |  Parse time:   '):
            parse_time = float(line.split()[4])
        elif line.startswith('s OPTIMUM FOUND'):
            is_BEST = 1
        elif line.startswith('c |  Number of variables:  '):
            nb_var = int(line.split()[-2])
        elif line.startswith('c |  Number of soft clauses: '):
            nb_soft = int(line.split()[-2])
        elif line.startswith('c |  Number of hard clauses: '):
            nb_hard = int(line.split()[-2])
        elif line.startswith('c  Total time: '):
            tot_time = float(line.split()[3])
            solving_time = tot_time - parse_time
    return Benchmark, nb_var, nb_soft, nb_hard, is_BEST, OPT, parse_time, tot_time, solving_time

def get_RC2_record(filename, filepath):
    Benchmark = filename.replace(".3pm", "").replace(".wcnf_old", "").replace(".wcnf", "").replace(".lp", "").replace(".proto", "").replace(".out", "")
    OPT = None
    is_BEST = None
    trans_time = None
    tot_time = None
    solving_time = None
    with open(filepath, 'r') as file:
        lines = file.readlines()
    for line in lines:
        line = line.strip()
        if line.startswith('$$$'):
            parts = line.split()
            trans_time = float(parts[3])

        if line.startswith('###'):
            parts = line.split()
            OPT = int(parts[4])
            tot_time = parts[6]
            solving_time = parts[8]

    is_BEST = 1 if (OPT is not None) else 0

    return Benchmark, is_BEST, OPT, trans_time, tot_time, solving_time

def get_cplex_record(filename, filepath):
    Benchmark = filename.replace(".cnf", "").replace(".out", "")
    OPT = None
    is_BEST = 0
    tot_time = None
    solving_time = None
    trans_time = None
    infeasible = False
    with open(filepath, 'r') as file:
        lines = file.readlines()
    for line in lines:
        line = line.strip()
        if 'infeasible' in line.lower():
            infeasible = True
        elif line.startswith('>>>'):
            parts = line.split()
            for i, p in enumerate(parts):
                if p == 'OPT':
                    OPT = int(parts[i + 1])
                elif p == 'TimeCost':
                    tot_time = float(parts[i + 1])
                elif p == 'TimeSolve':
                    solving_time = float(parts[i + 1])
                elif p == 'TimeTrans':
                    trans_time = float(parts[i + 1])
            if not infeasible:
                is_BEST = 1
    return Benchmark, is_BEST, OPT, tot_time, solving_time

def get_roundingSAT_record(filename, filepath):
    Benchmark = filename.replace(".3pm", "").replace(".wcnf_old", "").replace(".wcnf", "").replace(".lp", "").replace(".proto", "").replace(".out", "").replace(".pbo","")
    OPT = None
    is_BEST = 0
    nb_var = None
    nb_cons = None
    tot_time = None
    solving_time = None
    with open(filepath, 'r') as file:
        lines = file.readlines()
    for line in lines:
        line = line.strip()
        if line.startswith('o'):
            OPT = -int(line.split()[1])
        elif line.startswith('c total solve time'):
            solving_time = float(line.split()[-2])
        elif line.startswith('s OPTIMUM FOUND'):
            is_BEST = 1
        elif line.startswith('c CPU'):
            tot_time = float(line.split(":")[1].strip().split(" ")[0])
    return Benchmark, is_BEST, OPT, tot_time, solving_time

def process_configuration(config_key, dir_path, file_type):
    """Process all .out files in a directory and return records."""
    records = []
    
    for filename in os.listdir(dir_path):
        filepath = os.path.join(dir_path, filename)
        if os.path.isfile(filepath) and filename.endswith('.out'):
            try:
                if file_type == 'maxhs':
                    records.append(get_maxhs_record(filename, filepath))
                elif file_type == 'wmaxcdcl':
                    records.append(get_wmaxcdcl_record(filename, filepath))
                elif file_type == 'cash':
                    records.append(get_cash_record(filename, filepath))
                elif file_type == 'open':
                    records.append(get_open_record(filename, filepath))
                elif file_type == 'rounding':
                    records.append(get_roundingSAT_record(filename, filepath))
                elif file_type == 'cplex':
                    records.append(get_cplex_record(filename, filepath))
                elif file_type == 'rc2':
                    records.append(get_RC2_record(filename, filepath))

            except Exception as e:
                print(f"Warning: Error processing {filepath}: {e}")
    
    return records

def get_csv_header(file_type):
    """Return appropriate CSV header for file type."""
    headers = {
        'maxhs': ['Benchmark', 'nb_var', 'nb_cons', 'is_OPT', 'BEST', 'parse_time', 'tot_time', 'solving_time'],
        'wmaxcdcl': ['Benchmark', 'nb_var', 'nb_cons', 'is_OPT', 'BEST', 'parse_time', 'tot_time', 'solving_time'],
        'cash': ['Benchmark', 'BEST', 'is_OPT', "opt_val", 'solving_time'],
        'open': ['Benchmark', 'nb_var','nb_soft',  'nb_hard', 'is_OPT', 'BEST', 'parse_time', 'tot_time', 'solving_time'],
        'rounding': ['Benchmark', 'is_OPT', 'BEST', 'tot_time', 'solving_time'],
        'cplex': ['Benchmark', 'is_OPT', 'BEST', 'tot_time', 'solving_time'],
        'rc2': ['Benchmark', 'is_OPT', 'BEST', 'tot_time', 'solving_time'],
    }
    return headers.get(file_type, [])

def main():
    """Main processing function with automatic configuration detection."""
    
    print(f"Scanning result directory: {RESULT_ROOT_DIR}")
    
    try:
        configs = scan_result_directories(RESULT_ROOT_DIR)
    except ValueError as e:
        print(str(e))
        return
    
    print(f"\nFound {len(configs)} unique configurations:")
    for config_key in sorted(configs.keys()):
        solver, k_value, encoding, symmetry = config_key
        print(f"  - Solver: {solver}, K: {k_value}, Encoding: {encoding}, Symmetry: {symmetry}")
    
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Process each configuration
    for config_key, paths in configs.items():
        solver, k_value, encoding, symmetry = config_key
        timestamp, dir_path = paths[0]  # Only one path per config due to duplicate check
        
        file_type = get_solver_type(solver)
        if file_type is None:
            print(f"\nERROR: Unknown solver type '{solver}' in configuration:")
            print(f"  K: {k_value}, Encoding: {encoding}, Symmetry: {symmetry}")
            print(f"  Directory: {dir_path}")
            raise ValueError(f"Cannot determine file type for solver: {solver}")
        
        csv_filename = generate_csv_filename(solver, k_value, encoding, symmetry)
        csv_path = os.path.join(OUTPUT_DIR, csv_filename)
        
        print(f"\nProcessing: {csv_filename}")
        print(f"  Directory: {os.path.basename(dir_path)}")
        print(f"  File type: {file_type}")
        
        # Process files and collect records
        records = process_configuration(config_key, dir_path, file_type)
        
        if not records:
            print(f"  Warning: No records found in {dir_path}")
            continue
        
        # Sort and write to CSV
        sorted_records = sorted(records, key=custom_sort)
        
        with open(csv_path, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(get_csv_header(file_type))
            writer.writerows(sorted_records)
        
        print(f"  ✓ Wrote {len(sorted_records)} records to {csv_filename}")
    
    print(f"\n✓ All done! Output files in: {OUTPUT_DIR}")

if __name__ == '__main__':
    main()
