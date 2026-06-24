from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from skill2 import SQL_POR_INTENCION
from skill4 import skill_4_ejecutar
from skills_1_2_3 import skill_1_2_3


MANUAL_QUERIES = [
    ("top_20_clientes_compras", "Top 20 clientes con mayor numero de compras"),
    ("ventas_por_tienda", "Ventas por tienda"),
    ("ventas_por_mes", "Ventas por mes"),
    ("ventas_por_dia_semana", "Ventas por dia de la semana"),
    ("top_productos_por_tienda", "Top productos por tienda"),
    ("ticket_promedio_por_cliente", "Ticket promedio por cliente"),
    ("productos_mayor_ingreso", "Productos con mayor ingreso generado"),
    ("top_clientes_gasto_total", "Top clientes por gasto total"),
    ("ranking_mensual_ventas", "Ranking mensual de ventas"),
]

AGENTIC_QUERIES = [
    ("Cuales fueron los cinco productos mas vendidos?", "Cinco productos mas vendidos"),
    ("Que tienda tuvo mayores ventas?", "Tienda con mayores ventas"),
    ("Cual fue el mes con mayores ingresos?", "Mes con mayores ingresos"),
    ("Cuales son los diez mejores clientes?", "Diez mejores clientes"),
    ("Que productos generaron mayores ingresos?", "Productos con mayor ingreso"),
]

CSV_FIELDS = [
    "tipo",
    "nombre",
    "pregunta",
    "intencion",
    "motor_solicitado",
    "motor_resuelto",
    "estado",
    "filas",
    "hive_tiempo_s",
    "hive_cpu_pct",
    "hive_mem_mb",
    "spark_tiempo_s",
    "spark_cpu_pct",
    "spark_mem_mb",
    "speedup_spark_vs_hive",
    "error",
    "sql",
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ejecuta benchmarks Hive/Spark para el informe TPC-DS."
    )
    parser.add_argument(
        "--suite",
        choices=["all", "manual", "agentic"],
        default="all",
        help="Conjunto de consultas a ejecutar.",
    )
    parser.add_argument(
        "--engine",
        choices=["both", "hive", "spark"],
        default="both",
        help="Motor de ejecucion para cada consulta.",
    )
    parser.add_argument(
        "--out-dir",
        default="benchmark_results",
        help="Carpeta donde se escriben CSV, JSON y tabla LaTeX.",
    )
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(args.out_dir, f"benchmarks_{timestamp}.csv")
    json_path = os.path.join(args.out_dir, f"benchmarks_{timestamp}.json")
    tex_path = os.path.join(args.out_dir, f"benchmarks_{timestamp}.tex")

    spark = None
    if args.engine in {"both", "spark"}:
        spark = _spark_session()

    resultados: List[Dict[str, Any]] = []

    if args.suite in {"all", "manual"}:
        for intencion, nombre in MANUAL_QUERIES:
            row = _run_manual_query(nombre, intencion, args.engine, spark)
            resultados.append(row)
            _write_outputs(resultados, csv_path, json_path, tex_path)

    if args.suite in {"all", "agentic"}:
        for pregunta, nombre in AGENTIC_QUERIES:
            row = _run_agentic_query(nombre, pregunta, args.engine, spark)
            resultados.append(row)
            _write_outputs(resultados, csv_path, json_path, tex_path)

    print("\nListo.")
    print(f"CSV:  {csv_path}")
    print(f"JSON: {json_path}")
    print(f"TEX:  {tex_path}")


def _run_manual_query(
    nombre: str, intencion: str, engine: str, spark: Any
) -> Dict[str, Any]:
    sql = SQL_POR_INTENCION[intencion]
    print(f"\n[MANUAL] {nombre} ({intencion}) -> {engine}")
    return _execute_row(
        tipo="manual",
        nombre=nombre,
        pregunta="",
        intencion=intencion,
        sql=sql,
        motor_solicitado=engine,
        motor_resuelto=engine,
        spark=spark,
    )


def _run_agentic_query(
    nombre: str, pregunta: str, engine: str, spark: Any
) -> Dict[str, Any]:
    print(f"\n[AGENTIC] {pregunta} -> {engine}")
    try:
        sql, motor = skill_1_2_3(pregunta, modo=engine)
        intencion = _find_intention_by_sql(sql)
    except Exception as exc:
        return _error_row(
            tipo="agentic",
            nombre=nombre,
            pregunta=pregunta,
            intencion="",
            sql="",
            motor_solicitado=engine,
            motor_resuelto="",
            error=exc,
        )

    return _execute_row(
        tipo="agentic",
        nombre=nombre,
        pregunta=pregunta,
        intencion=intencion or "",
        sql=sql,
        motor_solicitado=engine,
        motor_resuelto=motor,
        spark=spark,
    )


def _execute_row(
    tipo: str,
    nombre: str,
    pregunta: str,
    intencion: str,
    sql: str,
    motor_solicitado: str,
    motor_resuelto: str,
    spark: Any,
) -> Dict[str, Any]:
    try:
        resultado = skill_4_ejecutar(sql, motor_resuelto, spark)
        row = _base_row(tipo, nombre, pregunta, intencion, sql, motor_solicitado, motor_resuelto)
        row.update(_metrics_from_result(resultado, motor_resuelto))
        row["estado"] = "ok"
        print(_progress_summary(row))
        return row
    except Exception as exc:
        row = _error_row(
            tipo=tipo,
            nombre=nombre,
            pregunta=pregunta,
            intencion=intencion,
            sql=sql,
            motor_solicitado=motor_solicitado,
            motor_resuelto=motor_resuelto,
            error=exc,
        )
        print(f"ERROR: {exc}")
        return row


def _base_row(
    tipo: str,
    nombre: str,
    pregunta: str,
    intencion: str,
    sql: str,
    motor_solicitado: str,
    motor_resuelto: str,
) -> Dict[str, Any]:
    return {
        "tipo": tipo,
        "nombre": nombre,
        "pregunta": pregunta,
        "intencion": intencion,
        "motor_solicitado": motor_solicitado,
        "motor_resuelto": motor_resuelto,
        "estado": "",
        "filas": None,
        "hive_tiempo_s": None,
        "hive_cpu_pct": None,
        "hive_mem_mb": None,
        "spark_tiempo_s": None,
        "spark_cpu_pct": None,
        "spark_mem_mb": None,
        "speedup_spark_vs_hive": None,
        "error": "",
        "sql": sql,
    }


def _error_row(
    tipo: str,
    nombre: str,
    pregunta: str,
    intencion: str,
    sql: str,
    motor_solicitado: str,
    motor_resuelto: str,
    error: Exception,
) -> Dict[str, Any]:
    row = _base_row(tipo, nombre, pregunta, intencion, sql, motor_solicitado, motor_resuelto)
    row["estado"] = "error"
    row["error"] = str(error)
    return row


def _metrics_from_result(resultado: Any, motor: str) -> Dict[str, Any]:
    metrics: Dict[str, Any] = {}
    if isinstance(resultado, dict) and "hive" in resultado and "spark" in resultado:
        hive = resultado["hive"]
        spark = resultado["spark"]
        metrics.update(
            {
                "filas": len(hive.get("rows", [])),
                "hive_tiempo_s": _round(hive.get("tiempo")),
                "hive_cpu_pct": _round(hive.get("cpu")),
                "hive_mem_mb": _round(hive.get("mem")),
                "spark_tiempo_s": _round(spark.get("tiempo")),
                "spark_cpu_pct": _round(spark.get("cpu")),
                "spark_mem_mb": _round(spark.get("mem")),
            }
        )
    elif isinstance(resultado, dict):
        prefix = "hive" if motor == "hive" else "spark"
        metrics.update(
            {
                "filas": len(resultado.get("rows", [])),
                f"{prefix}_tiempo_s": _round(resultado.get("tiempo")),
                f"{prefix}_cpu_pct": _round(resultado.get("cpu")),
                f"{prefix}_mem_mb": _round(resultado.get("mem")),
            }
        )
    else:
        cols, rows, tiempo = resultado[:3]
        prefix = "hive" if motor == "hive" else "spark"
        metrics.update({"filas": len(rows), f"{prefix}_tiempo_s": _round(tiempo)})

    hive_t = metrics.get("hive_tiempo_s")
    spark_t = metrics.get("spark_tiempo_s")
    if hive_t and spark_t:
        metrics["speedup_spark_vs_hive"] = _round(hive_t / spark_t)
    return metrics


def _write_outputs(
    resultados: List[Dict[str, Any]], csv_path: str, json_path: str, tex_path: str
) -> None:
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(resultados)

    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(resultados, fh, ensure_ascii=False, indent=2)

    with open(tex_path, "w", encoding="utf-8") as fh:
        fh.write(_latex_table(resultados))


def _latex_table(resultados: List[Dict[str, Any]]) -> str:
    lines = [
        "\\begin{table}[H]",
        "\\centering",
        "\\caption{Comparacion de rendimiento Hive vs Spark}",
        "\\begin{adjustbox}{max width=\\linewidth}",
        "\\begin{tabular}{llrrrrrrr}",
        "\\toprule",
        "Tipo & Consulta & Hive (s) & Spark (s) & Speedup & CPU Hive & CPU Spark & Mem Hive & Mem Spark \\\\",
        "\\midrule",
    ]
    for row in resultados:
        lines.append(
            "{} & {} & {} & {} & {} & {} & {} & {} & {} \\\\".format(
                _tex(row.get("tipo")),
                _tex(row.get("nombre")),
                _cell(row.get("hive_tiempo_s")),
                _cell(row.get("spark_tiempo_s")),
                _cell(row.get("speedup_spark_vs_hive")),
                _cell(row.get("hive_cpu_pct")),
                _cell(row.get("spark_cpu_pct")),
                _cell(row.get("hive_mem_mb")),
                _cell(row.get("spark_mem_mb")),
            )
        )
    lines.extend(
        [
            "\\bottomrule",
            "\\end{tabular}",
            "\\end{adjustbox}",
            "\\end{table}",
            "",
        ]
    )
    return "\n".join(lines)


def _spark_session() -> Any:
    from pyspark.sql import SparkSession

    return (
        SparkSession.builder.appName("Benchmarks TPC-DS Agentic Analytics")
        .enableHiveSupport()
        .getOrCreate()
    )


def _find_intention_by_sql(sql: str) -> Optional[str]:
    normalized = " ".join(sql.split())
    for intencion, candidate in SQL_POR_INTENCION.items():
        if " ".join(candidate.split()) == normalized:
            return intencion
    return None


def _progress_summary(row: Dict[str, Any]) -> str:
    return (
        "OK | filas={filas} | hive={hive}s cpu={hive_cpu}% mem={hive_mem}MB | "
        "spark={spark}s cpu={spark_cpu}% mem={spark_mem}MB | speedup={speedup}x"
    ).format(
        filas=row.get("filas"),
        hive=_cell(row.get("hive_tiempo_s")),
        hive_cpu=_cell(row.get("hive_cpu_pct")),
        hive_mem=_cell(row.get("hive_mem_mb")),
        spark=_cell(row.get("spark_tiempo_s")),
        spark_cpu=_cell(row.get("spark_cpu_pct")),
        spark_mem=_cell(row.get("spark_mem_mb")),
        speedup=_cell(row.get("speedup_spark_vs_hive")),
    )


def _round(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def _cell(value: Any) -> str:
    return "-" if value is None else str(value)


def _tex(value: Any) -> str:
    text = "" if value is None else str(value)
    return (
        text.replace("\\", "\\textbackslash{}")
        .replace("&", "\\&")
        .replace("%", "\\%")
        .replace("_", "\\_")
        .replace("#", "\\#")
    )


if __name__ == "__main__":
    main()
