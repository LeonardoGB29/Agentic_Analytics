from __future__ import annotations
import re
from typing import List

try:
    from .skill1 import normalizar_texto
    from .gemini_utils import generar_texto_gemini, limpiar_respuesta_llm
except ImportError:
    from skill1 import normalizar_texto
    from gemini_utils import generar_texto_gemini, limpiar_respuesta_llm


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


SQL_POR_INTENCION = {
    "top_20_clientes_compras": """SELECT
    c.cliente_sk,
    c.cliente_id,
    c.nombre_completo AS cliente,
    COUNT(*) AS numero_compras
FROM dw_retail.fact_ventas fv
JOIN dw_retail.dim_cliente c
    ON fv.cliente_sk = c.cliente_sk
GROUP BY
    c.cliente_sk,
    c.cliente_id,
    c.nombre_completo
ORDER BY numero_compras DESC
LIMIT 20""",
    "ventas_por_tienda": """SELECT
    t.tienda_sk,
    t.tienda_id,
    t.nombre_tienda,
    t.ciudad,
    t.pais,
    SUM(COALESCE(fv.venta_neta, 0)) AS ventas_totales
FROM dw_retail.fact_ventas fv
JOIN dw_retail.dim_tienda t
    ON fv.tienda_sk = t.tienda_sk
GROUP BY
    t.tienda_sk,
    t.tienda_id,
    t.nombre_tienda,
    t.ciudad,
    t.pais
ORDER BY ventas_totales DESC""",
    "ventas_por_mes": """SELECT
    f.anio,
    f.mes,
    SUM(COALESCE(fv.venta_neta, 0)) AS ventas_totales
FROM dw_retail.fact_ventas fv
JOIN dw_retail.dim_fecha f
    ON fv.fecha_sk = f.fecha_sk
GROUP BY
    f.anio,
    f.mes
ORDER BY
    anio,
    mes""",
    "ventas_por_dia_semana": """SELECT
    f.dia_semana,
    SUM(COALESCE(fv.venta_neta, 0)) AS ventas_totales
FROM dw_retail.fact_ventas fv
JOIN dw_retail.dim_fecha f
    ON fv.fecha_sk = f.fecha_sk
GROUP BY
    f.dia_semana
ORDER BY ventas_totales DESC""",
    "top_productos_por_tienda": """WITH ventas_producto_tienda AS (
    SELECT
        t.tienda_id,
        t.nombre_tienda,
        p.producto_id,
        p.nombre_producto AS producto,
        SUM(COALESCE(fv.cantidad, 0)) AS cantidad_vendida
    FROM dw_retail.fact_ventas fv
    JOIN dw_retail.dim_tienda t
        ON fv.tienda_sk = t.tienda_sk
    JOIN dw_retail.dim_producto p
        ON fv.producto_sk = p.producto_sk
    GROUP BY
        t.tienda_id,
        t.nombre_tienda,
        p.producto_id,
        p.nombre_producto
),
ranking_productos AS (
    SELECT
        tienda_id,
        nombre_tienda,
        producto_id,
        producto,
        cantidad_vendida,
        ROW_NUMBER() OVER (
            PARTITION BY tienda_id
            ORDER BY cantidad_vendida DESC
        ) AS ranking
    FROM ventas_producto_tienda
)
SELECT
    tienda_id,
    nombre_tienda,
    producto_id,
    producto,
    cantidad_vendida,
    ranking
FROM ranking_productos
WHERE ranking <= 10
ORDER BY tienda_id, ranking""",
    "ticket_promedio_por_cliente": """SELECT
    c.cliente_sk,
    c.cliente_id,
    c.nombre_completo AS cliente,
    COUNT(*) AS numero_compras,
    SUM(COALESCE(fv.venta_neta, 0)) AS gasto_total,
    AVG(COALESCE(fv.venta_neta, 0)) AS ticket_promedio
FROM dw_retail.fact_ventas fv
JOIN dw_retail.dim_cliente c
    ON fv.cliente_sk = c.cliente_sk
GROUP BY
    c.cliente_sk,
    c.cliente_id,
    c.nombre_completo
ORDER BY ticket_promedio DESC
LIMIT 20""",
    "productos_mayor_ingreso": """SELECT
    p.producto_sk,
    p.producto_id,
    p.nombre_producto AS producto,
    p.categoria,
    p.marca,
    SUM(COALESCE(fv.venta_neta, 0)) AS ingreso_generado
FROM dw_retail.fact_ventas fv
JOIN dw_retail.dim_producto p
    ON fv.producto_sk = p.producto_sk
GROUP BY
    p.producto_sk,
    p.producto_id,
    p.nombre_producto,
    p.categoria,
    p.marca
ORDER BY ingreso_generado DESC
LIMIT 20""",
    "top_clientes_gasto_total": """SELECT
    c.cliente_sk,
    c.cliente_id,
    c.nombre_completo AS cliente,
    SUM(COALESCE(fv.venta_neta, 0)) AS gasto_total
FROM dw_retail.fact_ventas fv
JOIN dw_retail.dim_cliente c
    ON fv.cliente_sk = c.cliente_sk
GROUP BY
    c.cliente_sk,
    c.cliente_id,
    c.nombre_completo
ORDER BY gasto_total DESC
LIMIT 20""",
    "ranking_mensual_ventas": """WITH ventas_tienda_mes AS (
    SELECT
        f.anio,
        f.mes,
        t.tienda_id,
        t.nombre_tienda,
        SUM(COALESCE(fv.venta_neta, 0)) AS ventas_totales
    FROM dw_retail.fact_ventas fv
    JOIN dw_retail.dim_fecha f
        ON fv.fecha_sk = f.fecha_sk
    JOIN dw_retail.dim_tienda t
        ON fv.tienda_sk = t.tienda_sk
    GROUP BY
        f.anio,
        f.mes,
        t.tienda_id,
        t.nombre_tienda
),
ranking_mensual AS (
    SELECT
        anio,
        mes,
        tienda_id,
        nombre_tienda,
        ventas_totales,
        RANK() OVER (
            PARTITION BY anio, mes
            ORDER BY ventas_totales DESC
        ) AS ranking_mensual
    FROM ventas_tienda_mes
)
SELECT
    anio,
    mes,
    tienda_id,
    nombre_tienda,
    ventas_totales,
    ranking_mensual
FROM ranking_mensual
WHERE ranking_mensual <= 10
ORDER BY anio, mes, ranking_mensual""",
    "cinco_productos_mas_vendidos": """SELECT
    p.producto_id,
    p.nombre_producto AS producto,
    SUM(COALESCE(fv.cantidad, 0)) AS cantidad_vendida
FROM dw_retail.fact_ventas fv
JOIN dw_retail.dim_producto p
    ON fv.producto_sk = p.producto_sk
GROUP BY
    p.producto_id,
    p.nombre_producto
ORDER BY cantidad_vendida DESC
LIMIT 5""",
    "tienda_mayores_ventas": """SELECT
    t.tienda_id,
    t.nombre_tienda,
    SUM(COALESCE(fv.venta_neta, 0)) AS ventas_totales
FROM dw_retail.fact_ventas fv
JOIN dw_retail.dim_tienda t
    ON fv.tienda_sk = t.tienda_sk
GROUP BY
    t.tienda_id,
    t.nombre_tienda
ORDER BY ventas_totales DESC
LIMIT 1""",
    "mes_mayores_ingresos": """SELECT
    f.anio,
    f.mes,
    SUM(COALESCE(fv.venta_neta, 0)) AS ingresos_totales
FROM dw_retail.fact_ventas fv
JOIN dw_retail.dim_fecha f
    ON fv.fecha_sk = f.fecha_sk
GROUP BY
    f.anio,
    f.mes
ORDER BY ingresos_totales DESC
LIMIT 1""",
    "diez_mejores_clientes": """SELECT
    c.cliente_sk,
    c.cliente_id,
    c.nombre_completo AS cliente,
    SUM(COALESCE(fv.venta_neta, 0)) AS gasto_total
FROM dw_retail.fact_ventas fv
JOIN dw_retail.dim_cliente c
    ON fv.cliente_sk = c.cliente_sk
GROUP BY
    c.cliente_sk,
    c.cliente_id,
    c.nombre_completo
ORDER BY gasto_total DESC
LIMIT 10""",
}


ESQUEMA_TPCDS = """Base de datos: dw_retail

Tabla dw_retail.dim_cliente:
- cliente_sk INT
- cliente_id STRING
- nombre_completo STRING
- email STRING
- ciudad STRING
- estado STRING
- pais STRING
- genero STRING
- nivel_educativo STRING
- potencial_compra STRING

Tabla dw_retail.dim_producto:
- producto_sk INT
- producto_id STRING
- nombre_producto STRING
- categoria STRING
- clase STRING
- marca STRING
- fabricante STRING
- precio_actual DOUBLE
- costo_mayoreo DOUBLE

Tabla dw_retail.dim_tienda:
- tienda_sk INT
- tienda_id STRING
- nombre_tienda STRING
- ciudad STRING
- estado STRING
- pais STRING
- gerente STRING
- mercado_desc STRING

Tabla dw_retail.dim_fecha:
- fecha_sk INT
- fecha DATE
- anio INT
- mes INT
- dia_mes INT
- dia_semana STRING
- trimestre INT
- es_feriado STRING
- es_fin_semana STRING

Tabla dw_retail.fact_ventas:
- venta_sk BIGINT
- cliente_sk INT
- tienda_sk INT
- producto_sk INT
- fecha_sk INT
- ticket_number INT
- cantidad INT
- precio_venta DOUBLE
- descuento DOUBLE
- venta_neta DOUBLE
- venta_neta_con_impuesto DOUBLE
- impuesto DOUBLE
- ganancia_neta DOUBLE
- anio_venta INT

Relaciones del esquema estrella:
- fact_ventas.cliente_sk = dim_cliente.cliente_sk
- fact_ventas.tienda_sk = dim_tienda.tienda_sk
- fact_ventas.producto_sk = dim_producto.producto_sk
- fact_ventas.fecha_sk = dim_fecha.fecha_sk
- fact_ventas esta particionada por anio_venta"""


FEW_SHOTS_SQL = f"""Intencion: cinco_productos_mas_vendidos
SQL:
{SQL_POR_INTENCION["cinco_productos_mas_vendidos"]}

Intencion: ventas_por_tienda
SQL:
{SQL_POR_INTENCION["ventas_por_tienda"]}

Intencion: ranking_mensual_ventas
SQL:
{SQL_POR_INTENCION["ranking_mensual_ventas"]}

Intencion: ticket_promedio_por_cliente
SQL:
{SQL_POR_INTENCION["ticket_promedio_por_cliente"]}"""


def skill_2_generar_sql(intencion: str) -> str:
    """
    Recibe una intencion y devuelve el SQL correspondiente.
    """
    intencion_normalizada = normalizar_texto(intencion).replace(" ", "_")

    try:
        return SQL_POR_INTENCION[intencion_normalizada]
    except KeyError as exc:
        raise ValueError(
            f"No existe una consulta definida para la intención: {intencion}"
        ) from exc


def listar_intenciones_disponibles() -> List[str]:
    """
    Devuelve la lista de intenciones soportadas.
    """
    return INTENCIONES_DISPONIBLES.copy()


__all__ = [
    "INTENCIONES_DISPONIBLES",
    "SQL_POR_INTENCION",
    "listar_intenciones_disponibles",
    "skill_2_generar_sql",
]


def construir_prompt_sql(intencion: str) -> str:
    """
    Construye el prompt principal para que Gemini genere SQL Hive/Spark.
    """
    intenciones = "\n".join(f"- {item}" for item in INTENCIONES_DISPONIBLES)
    return f"""Eres la Skill 2 de un agente analitico Big Data Retail TPC-DS.
Tu tarea es generar una consulta SQL valida para Hive/Spark SQL.

Esquema completo:
{ESQUEMA_TPCDS}

Intenciones soportadas:
{intenciones}

Ejemplos few-shot:
{FEW_SHOTS_SQL}

Reglas obligatorias:
- Usa siempre nombres de tablas calificados con base de datos, por ejemplo dw_retail.fact_ventas.
- No incluyas USE dw_retail.
- No agregues punto y coma al final.
- Devuelve unicamente SQL valido para Hive/Spark.
- No uses Markdown, explicaciones, comentarios ni texto adicional.
- Usa COALESCE en agregaciones numericas cuando aplique.
- Usa el esquema estrella: fact_ventas como tabla de hechos y dimensiones dim_cliente, dim_tienda, dim_producto y dim_fecha.

Intencion solicitada:
{intencion}
"""


def validar_sql_generado(sql: str) -> None:
    """
    Valida restricciones minimas del SQL generado por Gemini.
    """
    sql_limpio = sql.strip()
    sql_upper = sql_limpio.upper()

    if not sql_limpio:
        raise ValueError("Gemini no devolvio SQL.")
    if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
        raise ValueError("La respuesta de Gemini no inicia con SELECT o WITH.")
    if ";" in sql_limpio:
        raise ValueError("El SQL debe contener una sola sentencia sin punto y coma.")
    if "--" in sql_limpio or "/*" in sql_limpio:
        raise ValueError("El SQL no debe contener comentarios.")
    prohibidas = (
        "USE", "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
        "TRUNCATE", "MERGE", "GRANT", "REVOKE", "LOAD", "EXPORT", "IMPORT",
    )
    for palabra in prohibidas:
        if re.search(rf"\b{palabra}\b", sql_upper):
            raise ValueError(f"El SQL contiene una operacion no permitida: {palabra}.")
    if "dw_retail." not in sql_limpio:
        raise ValueError("El SQL debe usar tablas calificadas con dw_retail.")

    tablas_permitidas = {
        "fact_ventas",
        "dim_cliente",
        "dim_tienda",
        "dim_producto",
        "dim_fecha",
    }
    tablas_usadas = set(
        re.findall(r"dw_retail\.([a-zA-Z_][a-zA-Z0-9_]*)", sql_limpio)
    )
    tablas_invalidas = tablas_usadas - tablas_permitidas
    if tablas_invalidas:
        raise ValueError(
            "El SQL usa tablas fuera del esquema permitido: "
            + ", ".join(sorted(tablas_invalidas))
        )


def skill_2_generar_sql(intencion: str) -> str:
    """
    Recibe una intencion y devuelve SQL generado por Gemini.
    Si Gemini no esta configurado o devuelve SQL invalido, usa el catalogo local.
    """
    intencion_normalizada = normalizar_texto(intencion).replace(" ", "_")
    if intencion_normalizada not in SQL_POR_INTENCION:
        raise ValueError(
            f"No existe una consulta definida para la intención: {intencion}"
        )

    try:
        sql = limpiar_respuesta_llm(
            generar_texto_gemini(construir_prompt_sql(intencion_normalizada))
        )
        validar_sql_generado(sql)
        return sql
    except (RuntimeError, ValueError):
        return SQL_POR_INTENCION[intencion_normalizada]


__all__ = [
    "INTENCIONES_DISPONIBLES",
    "ESQUEMA_TPCDS",
    "FEW_SHOTS_SQL",
    "SQL_POR_INTENCION",
    "construir_prompt_sql",
    "listar_intenciones_disponibles",
    "skill_2_generar_sql",
    "validar_sql_generado",
]
