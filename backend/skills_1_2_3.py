from __future__ import annotations

try:
    from .skill1 import normalizar_texto, skill_1_identificar_intencion
    from .skill2 import listar_intenciones_disponibles, skill_2_generar_sql
    from .skill3 import skill_3_seleccionar_motor
except ImportError:
    from skill1 import normalizar_texto, skill_1_identificar_intencion
    from skill2 import listar_intenciones_disponibles, skill_2_generar_sql
    from skill3 import skill_3_seleccionar_motor


def skill_1_2_3(pregunta: str, modo: str = "auto") -> tuple[str, str]:
    """
    Funcion principal.
    Recibe una pregunta en lenguaje natural y devuelve:
    sql, motor
    """
    intencion = skill_1_identificar_intencion(pregunta)
    sql = skill_2_generar_sql(intencion)
    motor = skill_3_seleccionar_motor(intencion, modo)
    return sql, motor


__all__ = [
    "listar_intenciones_disponibles",
    "normalizar_texto",
    "skill_1_2_3",
    "skill_1_identificar_intencion",
    "skill_2_generar_sql",
    "skill_3_seleccionar_motor",
]
