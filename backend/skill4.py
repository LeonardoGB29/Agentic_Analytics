import time
import subprocess
import threading
import urllib.request
import json
import re

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False

YARN_APP_ID_PATTERN = re.compile(r"application_\d+_\d+")


def _get_yarn_cluster_cores():
    """Consulta la API de YARN para obtener los cores virtuales totales del clúster."""
    try:
        url = "http://localhost:8088/ws/v1/cluster/metrics"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=1.5) as response:
            data = json.loads(response.read().decode())
            return max(data.get("clusterMetrics", {}).get("totalVirtualCores", 8), 1)
    except Exception:
        return 8  # Fallback a 8 cores si no se puede acceder a la API


def _get_yarn_app_metrics(app_id):
    """Consulta la API REST de YARN para una aplicación finalizada y calcula recursos."""
    try:
        url = f"http://localhost:8088/ws/v1/cluster/apps/{app_id}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=1.5) as response:
            data = json.loads(response.read().decode())
            app_data = data.get("app", {})
            
            elapsed_time_ms = app_data.get("elapsedTime", 0)
            memory_seconds = app_data.get("memorySeconds", 0)
            vcore_seconds = app_data.get("vcoreSeconds", 0)
            
            elapsed_sec = elapsed_time_ms / 1000.0
            if elapsed_sec > 0:
                mem_mb = memory_seconds / elapsed_sec
                # Promedio de vcores asignados durante la consulta
                vcores_avg = vcore_seconds / elapsed_sec
                
                # Normalizar usando los cores totales del cluster
                total_cores = _get_yarn_cluster_cores()
                cpu_pct = min(100.0, round((vcores_avg / total_cores) * 100.0, 1))
                return {
                    "cpu": cpu_pct,
                    "mem": round(mem_mb, 1)
                }
    except Exception:
        pass
    return None


def _get_spark_metrics(spark):
    """Obtiene métricas agregadas de los ejecutores de Spark desde la API REST local."""
    if not spark:
        return None
    try:
        ui_url = spark.sparkContext.uiWebUrl or "http://localhost:4040"
        app_id = spark.sparkContext.applicationId
        if not app_id:
            return None
        
        url = f"{ui_url.rstrip('/')}/api/v1/applications/{app_id}/executors"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=1.5) as response:
            data = json.loads(response.read().decode())
            
            total_duration = 0
            total_cores = 0
            total_mem_used = 0
            
            for exec_info in data:
                total_duration += exec_info.get("totalDuration", 0)
                total_cores += exec_info.get("totalCores", 0)
                
                # Intentar obtener peakMemoryMetrics
                peak_metrics = exec_info.get("peakMemoryMetrics", {})
                if peak_metrics:
                    heap = peak_metrics.get("JVMHeapMemory", 0)
                    off_heap = peak_metrics.get("JVMOffHeapMemory", 0)
                    total_mem_used += (heap + off_heap)
                else:
                    total_mem_used += exec_info.get("memoryUsed", 0)
                    
            return {
                "total_duration_ms": total_duration,
                "total_cores": max(total_cores, 1),
                "total_mem_bytes": total_mem_used
            }
    except Exception:
        return None


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

    # Intentar obtener el YARN App ID desde stderr
    yarn_app_id = None
    app_ids = YARN_APP_ID_PATTERN.findall(stderr)
    if app_ids:
        yarn_app_id = app_ids[-1]

    # Consultar YARN para obtener métricas reales
    yarn_metrics = None
    if yarn_app_id:
        time.sleep(0.5)  # Espera para que YARN procese la finalización
        yarn_metrics = _get_yarn_app_metrics(yarn_app_id)

    if yarn_metrics:
        final_cpu = yarn_metrics["cpu"]
        final_mem = yarn_metrics["mem"]
    else:
        final_cpu = metrics["cpu"]
        final_mem = metrics["mem"]

    lineas = []
    for l in stdout.strip().split("\n"):
        if l:
            lineas.append(l)

    cols = lineas[0].split("\t")
    rows = []
    for l in lineas[1:]:
        rows.append(tuple(l.split("\t")))

    return cols, rows, time.time() - t0, final_cpu, final_mem


def ejecutar_spark(sql, spark):
    cpu_pct = None
    mem_mb = None

    # Intentar obtener métricas iniciales del Spark UI
    metrics_before = _get_spark_metrics(spark)
    use_psutil_fallback = (metrics_before is None)

    if use_psutil_fallback and _HAS_PSUTIL:
        p = psutil.Process()
        p.cpu_percent(interval=None)
        mem_before = p.memory_info().rss

    t0 = time.time()
    df = spark.sql(sql)
    cols = df.columns
    rows = df.collect()
    elapsed = time.time() - t0

    if not use_psutil_fallback:
        metrics_after = _get_spark_metrics(spark)
        if metrics_after and metrics_before:
            duration_delta_ms = metrics_after["total_duration_ms"] - metrics_before["total_duration_ms"]
            total_cores = metrics_after["total_cores"]
            elapsed_ms = elapsed * 1000.0
            
            if elapsed_ms > 0:
                cpu_pct = min(100.0, round((duration_delta_ms / (elapsed_ms * total_cores)) * 100.0, 1))
            else:
                cpu_pct = 0.0
            
            mem_mb = round(metrics_after["total_mem_bytes"] / (1024 * 1024), 1)
        else:
            use_psutil_fallback = True

    if use_psutil_fallback and _HAS_PSUTIL:
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