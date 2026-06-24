from __future__ import annotations

import os
from functools import lru_cache

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from charting import construir_meta_graficos, extraer_resultado_base
from skill4 import skill_4_ejecutar
from skill5 import skill_5_to_json
from skills_1_2_3 import skill_1_2_3


FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
CORS(app)


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "execution": "hive-spark",
            "engines": {"hive": True, "spark": True, "both": True},
        }
    )


@app.route("/api/query", methods=["POST"])
def query():
    data = request.get_json(force=True) or {}
    question = data.get("question", "").strip()
    requested_engine = _normalizar_motor(data.get("engine", "ambos"))

    if not question:
        return jsonify({"error": "empty question"}), 400

    try:
        sql, motor = skill_1_2_3(question, modo=requested_engine)
        resultado = _ejecutar(sql, motor)
        cols, rows = extraer_resultado_base(resultado)
        meta = construir_meta_graficos(cols, rows)
        resp = skill_5_to_json(resultado=resultado, sql=sql, engine=motor, meta=meta)
        resp["engine"] = motor
        resp["source"] = "hive-spark"
        return jsonify(resp)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"No se pudo procesar la consulta: {exc}"}), 500


def _normalizar_motor(engine: str) -> str:
    engine = str(engine or "ambos").strip().lower()
    if engine == "ambos":
        return "both"
    if engine in {"auto", "hive", "spark", "both"}:
        return engine
    return "auto"


def _ejecutar(sql: str, motor: str):
    if motor in {"spark", "both"}:
        return skill_4_ejecutar(sql, motor, _spark_session())
    return skill_4_ejecutar(sql, motor, None)


@lru_cache(maxsize=1)
def _spark_session():
    try:
        from pyspark.sql import SparkSession
    except ImportError as exc:
        raise RuntimeError(
            "No se encontro PySpark. Ejecute este servidor en el cluster Spark "
            "o instale/configure pyspark para usar motor spark/both."
        ) from exc

    builder = SparkSession.builder.appName("Agente Analitico Retail TPC-DS")
    if os.getenv("SPARK_ENABLE_HIVE", "1").lower() not in {"0", "false", "no"}:
        builder = builder.enableHiveSupport()
    return builder.getOrCreate()


if __name__ == "__main__":
    app.run(
        host=os.getenv("SERVER_HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "5000")),
        debug=True
    )