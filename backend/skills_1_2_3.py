from __future__ import annotations

import json
import os

try:
    from .gemini_utils import generar_texto_gemini, limpiar_respuesta_llm
    from .skill1 import (
        INTENCIONES_DISPONIBLES,
        _identificar_intencion_por_reglas,
        normalizar_texto,
        skill_1_identificar_intencion,
    )
    from .skill2 import SQL_POR_INTENCION, listar_intenciones_disponibles, skill_2_generar_sql
    from .skill3 import _seleccionar_motor_por_regla, skill_3_seleccionar_motor
except ImportError:
    from gemini_utils import generar_texto_gemini, limpiar_respuesta_llm
    from skill1 import (
        INTENCIONES_DISPONIBLES,
        _identificar_intencion_por_reglas,
        normalizar_texto,
        skill_1_identificar_intencion,
    )
    from skill2 import SQL_POR_INTENCION, listar_intenciones_disponibles, skill_2_generar_sql
    from skill3 import _seleccionar_motor_por_regla, skill_3_seleccionar_motor


def skill_1_2_3(pregunta: str, modo: str = "auto") -> tuple[str, str]:
    """
    Funcion principal optimizada.
    Recibe una pregunta en lenguaje natural y devuelve sql, motor.

    Para ahorrar cuota, usa una sola llamada a Gemini para identificar intencion
    y motor. El SQL se toma del catalogo validado local.
    """
    modo_normalizado = normalizar_texto(modo)
    if modo_normalizado not in {"auto", "hive", "spark", "both"}:
        raise ValueError("Modo inválido. Use: auto, hive, spark o both.")

    intencion = None
    motor_sugerido = None

    if os.getenv("GEMINI_DESACTIVADO", "").lower() not in {"1", "true", "si"}:
        try:
            intencion, motor_sugerido = _planificar_con_gemini(pregunta)
        except RuntimeError:
            intencion = None
            motor_sugerido = None

    if not intencion:
        pregunta_normalizada = normalizar_texto(pregunta)
        intencion = _identificar_intencion_por_reglas(pregunta_normalizada)

    if not intencion:
        # Ultimo respaldo: conserva compatibilidad con la Skill 1 individual.
        # Si no hay API key, esta funcion tambien cae a reglas locales.
        intencion = skill_1_identificar_intencion(pregunta)

    sql = _generar_sql_catalogo(intencion)

    if modo_normalizado in {"hive", "spark", "both"}:
        motor = modo_normalizado
    elif motor_sugerido in {"hive", "spark"}:
        motor = motor_sugerido
    else:
        motor = _seleccionar_motor_por_regla(intencion)

    return sql, motor


def _generar_sql_catalogo(intencion: str) -> str:
    intencion_normalizada = normalizar_texto(intencion).replace(" ", "_")
    try:
        return SQL_POR_INTENCION[intencion_normalizada]
    except KeyError as exc:
        raise ValueError(
            f"No existe una consulta definida para la intención: {intencion}"
        ) from exc


def _planificar_con_gemini(pregunta: str) -> tuple[str, str | None]:
    respuesta = limpiar_respuesta_llm(generar_texto_gemini(_construir_prompt_plan(pregunta)))
    try:
        data = json.loads(respuesta)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Gemini no devolvio JSON valido: {respuesta}") from exc

    intencion = normalizar_texto(data.get("intencion", "")).replace(" ", "_")
    motor = normalizar_texto(data.get("motor", ""))

    if intencion not in INTENCIONES_DISPONIBLES:
        raise RuntimeError(f"Gemini devolvio una intencion invalida: {intencion}")
    if motor and motor not in {"hive", "spark"}:
        raise RuntimeError(f"Gemini devolvio un motor invalido: {motor}")

    return intencion, motor or None


def _construir_prompt_plan(pregunta: str) -> str:
    intenciones = "\n".join(f"- {intencion}" for intencion in INTENCIONES_DISPONIBLES)
    return f"""Eres un planificador para un agente analitico Big Data Retail TPC-DS.
Debes resolver Skill 1 y Skill 3 en una sola respuesta:
1. Identificar la intencion analitica.
2. Elegir el motor recomendado: hive o spark.

Intenciones validas:
{intenciones}

Reglas de motor:
- hive para consultas simples: top_20_clientes_compras, ventas_por_dia_semana, ticket_promedio_por_cliente
- spark para las demas consultas

Responde solo JSON valido, sin Markdown, con esta forma exacta:
{{"intencion":"nombre_intencion","motor":"hive_o_spark"}}

Pregunta del usuario:
{pregunta}
"""


__all__ = [
    "listar_intenciones_disponibles",
    "normalizar_texto",
    "skill_1_2_3",
    "skill_1_identificar_intencion",
    "skill_2_generar_sql",
    "skill_3_seleccionar_motor",
]
