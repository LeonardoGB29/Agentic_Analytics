import time
import subprocess
def ejecutar_hive(sql):
    t0 = time.time()

    result = subprocess.run(
        ["hive", "--hiveconf", "hive.cli.print.header=true", "-e", sql],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    
    lineas = []
    for l in result.stdout.strip().split("\n"):
        if l:
            lineas.append(l)

    cols = lineas[0].split("\t")
    rows = []
    for l in lineas[1:]:
        rows.append(tuple(l.split("\t")))

    return cols, rows, time.time() - t0

def ejecutar_spark(sql, spark):
    t0 = time.time()

    df = spark.sql(sql)
    cols = df.columns
    rows = df.collect()

    return cols, rows, time.time() - t0

def skill_4_ejecutar(sql, motor, spark):
    if motor == "both":
        cols_h, rows_h, t_hive  = ejecutar_hive(sql)
        cols_s, rows_s, t_spark = ejecutar_spark(sql, spark)
        return {
            "hive":  {"cols": cols_h, "rows": rows_h, "tiempo": t_hive},
            "spark": {"cols": cols_s, "rows": rows_s, "tiempo": t_spark},
        }
    
    elif motor == "hive":
        return ejecutar_hive(sql)
    
    elif motor == "spark":
        return ejecutar_spark(sql, spark)