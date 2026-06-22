from __future__ import annotations

import re
import unicodedata

try:
    from .gemini_utils import generar_texto_gemini, limpiar_respuesta_llm
except ImportError:
    from gemini_utils import generar_texto_gemini, limpiar_respuesta_llm


PATRONES_INTENCION = [
    ("cinco_productos_mas_vendidos", ["cinco", "productos", "mas", "vendidos"]),
    ("diez_mejores_clientes", ["diez", "mejores", "clientes"]),
    ("tienda_mayores_ventas", ["tienda", "mayores", "ventas"]),
    ("tienda_mayores_ventas", ["tienda", "mayor", "ventas"]),
    ("mes_mayores_ingresos", ["mes", "mayores", "ingresos"]),
    ("mes_mayores_ingresos", ["mes", "mayor", "ingreso"]),
    ("ranking_mensual_ventas", ["ranking", "mensual", "ventas"]),
    ("top_productos_por_tienda", ["top", "productos", "tienda"]),
    ("ticket_promedio_por_cliente", ["ticket", "promedio", "cliente"]),
    ("productos_mayor_ingreso", ["productos", "mayor", "ingreso"]),
    ("productos_mayor_ingreso", ["productos", "ingreso", "generado"]),
    ("top_clientes_gasto_total", ["clientes", "gasto", "total"]),
    ("top_20_clientes_compras", ["top", "20", "clientes", "compras"]),
    ("top_20_clientes_compras", ["clientes", "mayor", "numero", "compras"]),
    ("ventas_por_dia_semana", ["ventas", "dia", "semana"]),
    ("ventas_por_mes", ["ventas", "mes"]),
    ("ventas_por_tienda", ["ventas", "tienda"]),
]

INTENCIONES_DISPONIBLES = [
    "top_20_clientes_compras",
    "ventas_por_tienda",
    "ventas_por_mes",
    "ventas_por_dia_semana",
    "top_productos_por_tienda",
    "ticket_promedio_por_cliente",
    "productos_mayor_ingreso",
    "top_clientes_gasto_total",
    "ranking_mensual_ventas",
    "cinco_productos_mas_vendidos",
    "tienda_mayores_ventas",
    "mes_mayores_ingresos",
    "diez_mejores_clientes",
]


def normalizar_texto(texto: str) -> str:
    """
    Convierte texto a minusculas, elimina tildes y limpia espacios.
    """
    if not isinstance(texto, str):
        texto = str(texto)

    texto = texto.lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(
        caracter for caracter in texto if unicodedata.category(caracter) != "Mn"
    )
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def skill_1_identificar_intencion(pregunta: str) -> str:
    """
    Recibe una pregunta en lenguaje natural y devuelve una intencion.
    Funciona con preguntas en espanol, con o sin tildes.
    """
    prompt = construir_prompt_intencion(pregunta)
    try:
        intencion_llm = limpiar_respuesta_llm(generar_texto_gemini(prompt))
        intencion_normalizada = normalizar_texto(intencion_llm).replace(" ", "_")
        if intencion_normalizada in INTENCIONES_DISPONIBLES:
            return intencion_normalizada
    except RuntimeError:
        pass

    pregunta_normalizada = normalizar_texto(pregunta)
    for intencion, palabras_clave in PATRONES_INTENCION:
        if all(palabra in pregunta_normalizada for palabra in palabras_clave):
            return intencion

    raise ValueError("No se pudo identificar la intención de la pregunta.")


def construir_prompt_intencion(pregunta: str) -> str:
    """
    Construye el prompt de Gemini para clasificar la intencion analitica.
    """
    intenciones = "\n".join(f"- {intencion}" for intencion in INTENCIONES_DISPONIBLES)
    return f"""Eres la Skill 1 de un agente analitico Big Data Retail TPC-DS.
Tu tarea es clasificar la pregunta del usuario en una unica intencion valida.

Intenciones validas:
{intenciones}

Reglas:
- Si la pregunta no es analitica o no corresponde al catalogo, responde: desconocida
- Responde solo el nombre exacto de la intencion, sin explicaciones.
- No uses Markdown.
- La pregunta puede estar en espanol con o sin tildes.

Pregunta:
{pregunta}
"""


__all__ = [
    "INTENCIONES_DISPONIBLES",
    "construir_prompt_intencion",
    "normalizar_texto",
    "skill_1_identificar_intencion",
]


def _tiene(texto: str, *palabras: str) -> bool:
    return any(palabra in texto for palabra in palabras)


def _identificar_intencion_por_reglas(texto: str) -> str | None:
    """
    Respaldo local para preguntas realistas cuando Gemini no esta configurado.
    """
    if _tiene(texto, "dia", "dias", "lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo", "fin de semana") and _tiene(texto, "venta", "ventas", "vende", "vendio", "vendieron"):
        return "ventas_por_dia_semana"

    if _tiene(texto, "ranking mensual", "por cada mes") or (
        _tiene(texto, "ranking", "ordenadas", "ordenado")
        and _tiene(texto, "mes", "mensual")
        and _tiene(texto, "tienda", "tiendas", "local", "locales")
    ):
        return "ranking_mensual_ventas"

    if _tiene(texto, "5", "cinco", "top 5") and _tiene(texto, "producto", "productos", "articulo", "articulos") and _tiene(texto, "vendido", "vendidos", "unidades", "cantidad"):
        return "cinco_productos_mas_vendidos"

    if _tiene(texto, "10", "diez", "top 10") and _tiene(texto, "cliente", "clientes") and _tiene(texto, "mejor", "mejores", "valioso", "valiosos", "gasto", "gastaron", "dinero"):
        return "diez_mejores_clientes"

    if _tiene(texto, "producto", "productos", "articulo", "articulos") and _tiene(texto, "ingreso", "ingresos", "dinero", "plata", "facturacion", "monto", "generaron", "aportaron"):
        return "productos_mayor_ingreso"

    if _tiene(texto, "20", "veinte", "primeros 20") and _tiene(texto, "cliente", "clientes") and _tiene(texto, "compra", "compras", "compraron", "hicieron"):
        return "top_20_clientes_compras"

    if _tiene(texto, "veces", "cantidad de compras", "numero de compras") and _tiene(texto, "cliente", "clientes", "compraron"):
        return "top_20_clientes_compras"

    if _tiene(texto, "ticket", "promedio", "medio", "monto promedio") and _tiene(texto, "cliente", "clientes", "compra", "paga", "gasta"):
        return "ticket_promedio_por_cliente"

    if _tiene(texto, "por tienda", "por cada tienda", "cada tienda", "en cada tienda", "por local", "cada local") and _tiene(texto, "producto", "productos", "articulo", "articulos", "lideres"):
        return "top_productos_por_tienda"

    if _tiene(texto, "cliente", "clientes") and _tiene(texto, "gasto", "gastaron", "dinero", "monto total", "comprado", "ingresos", "valiosos"):
        return "top_clientes_gasto_total"

    if _tiene(texto, "mes", "mensual") and _tiene(texto, "mayor", "mas fuerte", "mas dinero", "facturacion", "ingreso", "ingresos"):
        return "mes_mayores_ingresos"

    if _tiene(texto, "mes", "mensual", "mes a mes") and _tiene(texto, "venta", "ventas", "vendio"):
        return "ventas_por_mes"

    if _tiene(texto, "tienda", "tiendas", "local", "locales") and _tiene(texto, "mayor", "mas vendio", "numero uno", "mayores ventas", "mayor ingreso"):
        return "tienda_mayores_ventas"

    if _tiene(texto, "tienda", "tiendas", "local", "locales") and _tiene(texto, "venta", "ventas", "vendio", "vendido", "total vendido", "comparar"):
        return "ventas_por_tienda"

    return None


def skill_1_identificar_intencion(pregunta: str) -> str:
    """
    Recibe una pregunta en lenguaje natural y devuelve una intencion.
    Usa Gemini primero y reglas locales como respaldo para pruebas/desarrollo.
    """
    prompt = construir_prompt_intencion(pregunta)
    try:
        intencion_llm = limpiar_respuesta_llm(generar_texto_gemini(prompt))
        intencion_normalizada = normalizar_texto(intencion_llm).replace(" ", "_")
        if intencion_normalizada in INTENCIONES_DISPONIBLES:
            return intencion_normalizada
    except RuntimeError:
        pass

    pregunta_normalizada = normalizar_texto(pregunta)
    intencion_local = _identificar_intencion_por_reglas(pregunta_normalizada)
    if intencion_local:
        return intencion_local

    for intencion, palabras_clave in PATRONES_INTENCION:
        if all(palabra in pregunta_normalizada for palabra in palabras_clave):
            return intencion

    raise ValueError("No se pudo identificar la intención de la pregunta.")
