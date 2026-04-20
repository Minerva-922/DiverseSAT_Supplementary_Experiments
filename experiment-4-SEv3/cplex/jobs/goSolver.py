from subprocess import Popen, PIPE, STDOUT
import subprocess
import multiprocessing
from datetime import datetime
import os
import sys
import signal
import argparse
import psutil
import csv
import time
import threading


def get_process_memory(proc):
    try:
        if sys.platform == 'linux':
            with open(f'/proc/{proc.pid}/status') as f:
                for line in f:
                    if 'VmHWM' in line:
                        return int(line.split()[1]) * 1024

        # default action for macOS and other systems
        # 尝试使用 memory_full_info()，如果失败则降级到 memory_info()
        try:
            mem_info = proc.memory_full_info()
            # 优先使用 rss（常驻内存），因为在某些系统上 uss 可能为 0
            return mem_info.rss if mem_info.rss > 0 else mem_info.uss
        except (psutil.AccessDenied, AttributeError):
            # 如果 memory_full_info() 失败，使用 memory_info()
            mem_info = proc.memory_info()
            return mem_info.rss
    except Exception as e:
        return 0

def memory_monitor(process, stop_event, peak_memory, cutoff_mem_mb, process_status):
    try:
        sampling_interval = 0.01  # 10ms
        termination_grace_period = 0.1  # 100ms的终止宽限期

        while not stop_event.is_set():
            try:
                # 获取主进程内存
                current_memory = get_process_memory(process) / 1024 / 1024  # Convert to MB
                
                # 累加所有子进程的内存
                try:
                    for child in process.children(recursive=True):
                        try:
                            child_memory = get_process_memory(child) / 1024 / 1024
                            current_memory += child_memory
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

                if current_memory > 0:
                    peak_memory[0] = max(peak_memory[0], current_memory)

                    if current_memory < 1:  # 如果小于1MB
                        time.sleep(0.001)  # 等待一小段时间
                        # 重新计算总内存（包括子进程）
                        current_memory = get_process_memory(process) / 1024 / 1024
                        try:
                            for child in process.children(recursive=True):
                                try:
                                    child_memory = get_process_memory(child) / 1024 / 1024
                                    current_memory += child_memory
                                except (psutil.NoSuchProcess, psutil.AccessDenied):
                                    continue
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                        if current_memory > 0:
                            peak_memory[0] = max(peak_memory[0], current_memory)

                # 检查是否超出内存限制
                if cutoff_mem_mb and current_memory > cutoff_mem_mb:
                    try:
                        process_status[0] = "pending_termination"  # 标记进程即将终止
                        
                        # 在终止进程前记录最终内存使用（包括所有子进程）
                        final_memory = get_process_memory(process) / 1024 / 1024
                        try:
                            for child in process.children(recursive=True):
                                try:
                                    child_final_memory = get_process_memory(child) / 1024 / 1024
                                    final_memory += child_final_memory
                                except (psutil.NoSuchProcess, psutil.AccessDenied):
                                    continue
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                        peak_memory[0] = max(peak_memory[0], final_memory)

                        # 给进程一个短暂的时间完成最后的输出
                        time.sleep(termination_grace_period)
                        
                        # 终止所有子进程
                        try:
                            for child in process.children(recursive=True):
                                try:
                                    child.kill()
                                except (psutil.NoSuchProcess, psutil.AccessDenied):
                                    continue
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                        process.kill()
                    except psutil.NoSuchProcess:
                        pass
                    process_status[0] = "out_of_mem"
                    stop_event.set()
                    print("Memory limit exceeded")
                    break

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break

            time.sleep(sampling_interval)

    except Exception as e:
        print(f"Memory monitoring error: {str(e)}")
    finally:
        # 在监控结束后继续检查一段时间的内存使用
        try:
            additional_monitoring_time = 0.2  # 200ms
            monitoring_interval = 0.01  # 10ms
            iterations = int(additional_monitoring_time / monitoring_interval)
            
            for _ in range(iterations):
                try:
                    # 计算总内存（包括所有子进程）
                    final_memory = get_process_memory(process) / 1024 / 1024
                    try:
                        for child in process.children(recursive=True):
                            try:
                                child_memory = get_process_memory(child) / 1024 / 1024
                                final_memory += child_memory
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                continue
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                    if final_memory > 0:
                        peak_memory[0] = max(peak_memory[0], final_memory)
                except:
                    break
                time.sleep(monitoring_interval)
        except:
            pass



def output_monitor(process, output_file, stop_event):
    """持续监控并收集进程的输出"""
    # 一次性打开文件，避免频繁的文件操作
    with open(output_file, 'w', buffering=1) as f:  # 使用行缓冲
        try:
            # 实时复制输出到标准输出，这样可以在终端看到实时进度
            for line in iter(process.stdout.readline, ''):
                if stop_event.is_set() and process.poll() is not None:
                    break
                
                
                f.write(line)
                
            # 确保收集最后的输出
            remaining_output, _ = process.communicate(timeout=0.5)
            if remaining_output:
                sys.stdout.write(remaining_output)
                sys.stdout.flush()
                f.write(remaining_output)
                
        except subprocess.TimeoutExpired:
            process.kill()
            remaining_output, _ = process.communicate()
            if remaining_output:
                sys.stdout.write(remaining_output)
                sys.stdout.flush()
                f.write(remaining_output)
                
        except Exception as e:
            print(f"Error in output monitor: {str(e)}")

def terminate_process_tree(parent_pid):
    """终止进程及其所有子进程"""
    try:
        parent = psutil.Process(parent_pid)
        children = parent.children(recursive=True)
        
        for child in children:
            try:
                child.kill()
            except psutil.NoSuchProcess:
                pass
            
        parent.kill()
    except psutil.NoSuchProcess:
        pass

def worker(id, solver, instance, output_dir, cutoff_time, cutoff_mem, additional_args):
    print("[{}] Starting benchmark on {}".format(id + 1, os.path.basename(instance)))

    instance_name = os.path.basename(instance)
    output_file = os.path.join(output_dir, "{}.out".format(instance_name))
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    open(output_file, 'w').close()

    if additional_args and isinstance(additional_args[0], (list, tuple)):
        additional_args = additional_args[0]

    if solver.endswith('.py'):
        # 自动检测可用的 Python 命令
        python_cmd = sys.executable if sys.executable else 'python3'
        cmd = [python_cmd, solver, instance] + list(additional_args)
    else:
        cmd = [solver, instance] + list(additional_args)
    
    #print("**********", " ".join(cmd))

    peak_memory = [0]
    process_status = ["completed"]
    stop_event = threading.Event()
    solver_time = [0]

    cutoff_mem_mb = cutoff_mem * 1024 if cutoff_mem else None

    start_time = time.perf_counter()
    process = None
    
    try:
        process = Popen(
            cmd,
            stdout=PIPE,
            stderr=STDOUT,
            universal_newlines=True,
            bufsize=1,  # 行缓冲
            env={**os.environ, 'PYTHONUNBUFFERED': '1'}  # 确保Python输出不被缓存
        )
        psutil_process = psutil.Process(process.pid)

        monitor_thread = threading.Thread(
            target=memory_monitor,
            args=(psutil_process, stop_event, peak_memory, cutoff_mem_mb, process_status)
        )
        monitor_thread.start()

        output_thread = threading.Thread(
            target=output_monitor,
            args=(process, output_file, stop_event)
        )
        output_thread.start()

        def kill_process():
            try:
                process_status[0] = "out_of_time"
                solver_time[0] = cutoff_time
                if process and process.pid:
                    terminate_process_tree(process.pid)
            finally:
                stop_event.set()
                print("Timeout for {}".format(instance_name))

        signal.signal(signal.SIGALRM, lambda signum, frame: kill_process())
        signal.alarm(cutoff_time)

        try:
            process.wait()
        finally:
            signal.alarm(0)
            stop_event.set()
            
            # 确保进程被终止
            if process and process.poll() is None:
                terminate_process_tree(process.pid)
                try:
                    process.wait(timeout=1)
                except:
                    pass

            # 等待监控线程结束
            monitor_thread.join()
            output_thread.join(timeout=1)

    except Exception as e:
        print(f"Error in worker: {str(e)}")
        if process and process.poll() is None:
            terminate_process_tree(process.pid)

    finally:
        solver_time[0] = time.perf_counter() - start_time

    print("[{}] Finished benchmark on {}".format(id + 1, os.path.basename(instance)))

    if process_status[0] == "out_of_mem":
        return instance_name, "out_of_mem", solver_time[0]
    elif process_status[0] == "out_of_time":
        return instance_name, peak_memory[0], "out_of_time"
    else:
        return instance_name, peak_memory[0], solver_time[0]



def write_time_and_memory_csv(output_dir, benchmark_data, prefix):
    csv_file = os.path.join(output_dir, f"time_and_memory-{prefix}.csv")
    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Instance", "PeakMem(MB)", "Time(s)"])
        for instance, peak_mem, exec_time in benchmark_data:
            peak_mem_str = f"{peak_mem:.2f}" if isinstance(peak_mem, (int, float)) else peak_mem
            exec_time_str = f"{exec_time:.2f}" if isinstance(exec_time, (int, float)) else exec_time
            writer.writerow([instance, peak_mem_str, exec_time_str])

def read_name_list(name_list_file):
    with open(name_list_file, 'r') as f:
        return set(line.strip() for line in f)

def get_item_under_dir(inputPath, allowed_names=None):
    instances = []
    for item in os.listdir(inputPath):
        item_path = os.path.join(inputPath, item)
        if os.path.isfile(item_path) and (allowed_names is None or os.path.basename(item_path) in allowed_names):
            instances.append(item_path)
        elif os.path.isdir(item_path):
            instances.extend(get_item_under_dir(item_path, allowed_names))
    return instances

def goSolver(nbCPU, cutoffTime, cutoffMem, solver, inputPath, outputRoot, name_list_file, suffix, *additional_args):
    solver_name = os.path.splitext(os.path.basename(solver))[0]
    dataset_name = os.path.basename(os.path.normpath(inputPath))

    allowed_names = read_name_list(name_list_file) if name_list_file else None

    if not os.path.exists(inputPath):
        print("Input path does not exist.")
        return

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

    if suffix:
        output_dir = os.path.join(outputRoot, f"result-{solver_name}-{dataset_name}-{suffix}-{timestamp}")
    else:
        output_dir = os.path.join(outputRoot, f"result-{solver_name}-{dataset_name}-{timestamp}")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    instances = []
    if os.path.isdir(inputPath):
        for item in os.listdir(inputPath):
            item_path = os.path.join(inputPath, item)
            if os.path.isfile(item_path) and (allowed_names is None or os.path.basename(item_path) in allowed_names):
                instances.append(item_path)
            elif os.path.isdir(item_path):
                instances.extend(get_item_under_dir(item_path, allowed_names))
    else:
        instances.append(inputPath)

    pool = multiprocessing.Pool(nbCPU)
    jobs = []
    for id, instance in enumerate(instances):
        jobs.append(pool.apply_async(worker, (id, solver, instance, output_dir, cutoffTime, cutoffMem, additional_args)))

    benchmark_data = []
    for job in jobs:
        instance_name, peak_mem, exec_time = job.get()
        benchmark_data.append((instance_name, peak_mem, exec_time))

    pool.close()
    pool.join()

    
    out_suffix = f"{solver_name}_{dataset_name}" + (suffix if suffix is not None else "")
    write_time_and_memory_csv(output_dir, benchmark_data, out_suffix)

    print("All benchmarks are completed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run goSolver with specified parameters.")
    parser.add_argument("nbCPU", type=int, help="Number of CPUs to use")
    parser.add_argument("cutoffTime", type=int, help="Cutoff time in seconds")
    parser.add_argument("solver", help="Solver to use")
    parser.add_argument("inputPath", help="Path to input file")
    parser.add_argument("outputRoot", help="Root for output files")

    parser.add_argument("--cutoff_mem", type=float, help="Memory limit in GB", default=None)
    parser.add_argument("--name_list", help="Path to a text file containing allowed file names")
    parser.add_argument("--suffix", help="Suffix for the generated result directory")


    args, solver_args = parser.parse_known_args()

    goSolver(args.nbCPU, args.cutoffTime, args.cutoff_mem, args.solver, args.inputPath, args.outputRoot,
             args.name_list, args.suffix, solver_args)

