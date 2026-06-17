from __future__ import annotations

try:
    from .skill1 import normalizar_texto
    from .gemini_utils import generar_texto_gemini, limpiar_respuesta_llm
except ImportError:
    from skill1 import normalizar_texto
    from gemini_utils import generar_texto_gemini, limpiar_respuesta_llm


CONSULTAS_PESADAS = {
    "ventas_por_tienda",
    "ventas_por_mes",
    "top_productos_por_tienda",
    "productos_mayor_ingreso",
    "top_clientes_gasto_total",
    "ranking_mensual_ventas",
    "cinco_productos_mas_vendidos",
    "tienda_mayores_ventas",
    "mes_mayores_ingresos",
    "diez_mejores_clientes",
}

CONSULTAS_SIMPLES = {
    "top_20_clientes_compras",
    "ventas_por_dia_semana",
    "ticket_promedio_por_cliente",
}


def skill_3_seleccionar_motor(intencion: str, modo: str = "auto") -> str:
    """
    Devuelve el motor:
    - "hive"
    - "spark"
    - "both"

    Si modo es "hive", "spark" o "both", respeta ese valor.
    Si modo es "auto", decide segun la intencion.
    """
    modo_normalizado = normalizar_texto(modo)
    if modo_normalizado in {"hive", "spark", "both"}:
        return modo_normalizado
    if modo_normalizado != "auto":
        raise ValueError("Modo inválido. Use: auto, hive, spark o both.")

    intencion_normalizada = normalizar_texto(intencion).replace(" ", "_")
    if intencion_normalizada in CONSULTAS_PESADAS:
        return "spark"
    if intencion_normalizada in CONSULTAS_SIMPLES:
        return "hive"

    raise ValueError(
        f"No existe una consulta definida para la intención: {intencion}"
    )


__all__ = ["skill_3_seleccionar_motor"]


def construir_prompt_motor(intencion: str) -> str:
    """
    Construye el prompt para que Gemini seleccione motor en modo automatico.
    """
    pesadas = "\n".join(f"- {item}" for item in sorted(CONSULTAS_PESADAS))
    simples = "\n".join(f"- {item}" for item in sorted(CONSULTAS_SIMPLES))
    return f"""Eres la Skill 3 de un agente Big Data Retail TPC-DS.
Tu tarea es seleccionar el motor de ejecucion para una intencion analitica.

Reglas:
- Responde solo hive o spark.
- Usa spark para consultas pesadas.
- Usa hive para consultas simples.
- No uses Markdown ni explicaciones.

Consultas pesadas:
{pesadas}

Consultas simples:
{simples}

Intencion:
{intencion}
"""


def _seleccionar_motor_por_regla(intencion: str) -> str:
    intencion_normalizada = normalizar_texto(intencion).replace(" ", "_")
    if intencion_normalizada in CONSULTAS_PESADAS:
        return "spark"
    if intencion_normalizada in CONSULTAS_SIMPLES:
        return "hive"

    raise ValueError(
        f"No existe una consulta definida para la intención: {intencion}"
    )


def skill_3_seleccionar_motor(intencion: str, modo: str = "auto") -> str:
    """
    Devuelve el motor:
    - "hive"
    - "spark"
    - "both"

    Si modo es "hive", "spark" o "both", respeta ese valor.
    Si modo es "auto", usa Gemini y valida la respuesta.
    """
    modo_normalizado = normalizar_texto(modo)
    if modo_normalizado in {"hive", "spark", "both"}:
        return modo_normalizado
    if modo_normalizado != "auto":
        raise ValueError("Modo inválido. Use: auto, hive, spark o both.")

    try:
        motor = normalizar_texto(
            limpiar_respuesta_llm(generar_texto_gemini(construir_prompt_motor(intencion)))
        )
        if motor in {"hive", "spark"}:
            return motor
    except RuntimeError:
        pass

    return _seleccionar_motor_por_regla(intencion)


__all__ = [
    "construir_prompt_motor",
    "skill_3_seleccionar_motor",
]
