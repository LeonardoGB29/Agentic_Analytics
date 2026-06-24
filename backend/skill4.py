import time
import subprocess
import threading

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False


def _monitor_process(proc_pid, result_holder, stop_event):
    """Background thread that samples CPU% and peak RSS of a process."""
    try:
        p = psutil.Process(proc_pid)
        p.cpu_percent(interval=None)  # primer llamado descarta (inicializa)
        peak_mem = 0
        cpu_samples = []
        while not stop_event.is_set():
            try:
                cpu_samples.append(p.cpu_percent(interval=None))
                mem = p.memory_info().rss
                if mem > peak_mem:
                    peak_mem = mem
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break
            stop_event.wait(0.1)
        result_holder["cpu"] = sum(cpu_samples) / len(cpu_samples) if cpu_samples else 0
        result_holder["mem"] = round(peak_mem / (1024 * 1024), 1)
    except Exception:
        result_holder["cpu"] = None
        result_holder["mem"] = None


def ejecutar_hive(sql):
    t0 = time.time()

    proc = subprocess.Popen(
        ["hive", "--hiveconf", "hive.cli.print.header=true", "-e", sql],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )

    metrics = {"cpu": None, "mem": None}
    stop_event = threading.Event()
    monitor_thread = None

    if _HAS_PSUTIL:
        monitor_thread = threading.Thread(
            target=_monitor_process,
            args=(proc.pid, metrics, stop_event),
            daemon=True
        )
        monitor_thread.start()

    stdout, stderr = proc.communicate()

    stop_event.set()
    if monitor_thread:
        monitor_thread.join(timeout=2)

    if proc.returncode != 0:
        raise RuntimeError(stderr)

    lineas = []
    for l in stdout.strip().split("\n"):
        if l:
            lineas.append(l)

    cols = lineas[0].split("\t")
    rows = []
    for l in lineas[1:]:
        rows.append(tuple(l.split("\t")))

    return cols, rows, time.time() - t0, metrics["cpu"], metrics["mem"]


def ejecutar_spark(sql, spark):
    cpu_pct = None
    mem_mb = None

    if _HAS_PSUTIL:
        p = psutil.Process()
        p.cpu_percent(interval=None)  # inicializar
        mem_before = p.memory_info().rss

    t0 = time.time()
    df = spark.sql(sql)
    cols = df.columns
    rows = df.collect()
    elapsed = time.time() - t0

    if _HAS_PSUTIL:
        cpu_pct = p.cpu_percent(interval=None)
        mem_after = p.memory_info().rss
        mem_mb = round(max(mem_after - mem_before, 0) / (1024 * 1024), 1)

    return cols, rows, elapsed, cpu_pct, mem_mb


def skill_4_ejecutar(sql, motor, spark):
    if motor == "both":
        cols_h, rows_h, t_hive, cpu_h, mem_h = ejecutar_hive(sql)
        cols_s, rows_s, t_spark, cpu_s, mem_s = ejecutar_spark(sql, spark)
        return {
            "hive":  {"cols": cols_h, "rows": rows_h, "tiempo": t_hive, "cpu": cpu_h, "mem": mem_h},
            "spark": {"cols": cols_s, "rows": rows_s, "tiempo": t_spark, "cpu": cpu_s, "mem": mem_s},
        }

    elif motor == "hive":
        cols, rows, t, cpu, mem = ejecutar_hive(sql)
        return {"cols": cols, "rows": rows, "tiempo": t, "cpu": cpu, "mem": mem}

    elif motor == "spark":
        cols, rows, t, cpu, mem = ejecutar_spark(sql, spark)
        return {"cols": cols, "rows": rows, "tiempo": t, "cpu": cpu, "mem": mem}