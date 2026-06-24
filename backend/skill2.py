from __future__ import annotations
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
    c.c_customer_sk,
    c.c_customer_id,
    CONCAT(COALESCE(c.c_first_name, ''), ' ', COALESCE(c.c_last_name, '')) AS cliente,
    COUNT(*) AS numero_compras
FROM tpcds_bigdata.store_sales ss
JOIN tpcds_bigdata.customer c
    ON ss.ss_customer_sk = c.c_customer_sk
GROUP BY
    c.c_customer_sk,
    c.c_customer_id,
    c.c_first_name,
    c.c_last_name
ORDER BY numero_compras DESC
LIMIT 20""",
    "ventas_por_tienda": """SELECT
    s.s_store_sk,
    s.s_store_id,
    s.s_store_name,
    s.s_city,
    s.s_country,
    SUM(COALESCE(ss.ss_net_paid, 0)) AS ventas_totales
FROM tpcds_bigdata.store_sales ss
JOIN tpcds_bigdata.store s
    ON ss.ss_store_sk = s.s_store_sk
GROUP BY
    s.s_store_sk,
    s.s_store_id,
    s.s_store_name,
    s.s_city,
    s.s_country
ORDER BY ventas_totales DESC""",
    "ventas_por_mes": """SELECT
    d.d_year AS anio,
    d.d_moy AS mes,
    SUM(COALESCE(ss.ss_net_paid, 0)) AS ventas_totales
FROM tpcds_bigdata.store_sales ss
JOIN tpcds_bigdata.date_dim d
    ON ss.ss_sold_date_sk = d.d_date_sk
GROUP BY
    d.d_year,
    d.d_moy
ORDER BY
    anio,
    mes""",
    "ventas_por_dia_semana": """SELECT
    d.d_day_name AS dia_semana,
    SUM(COALESCE(ss.ss_net_paid, 0)) AS ventas_totales
FROM tpcds_bigdata.store_sales ss
JOIN tpcds_bigdata.date_dim d
    ON ss.ss_sold_date_sk = d.d_date_sk
GROUP BY
    d.d_day_name
ORDER BY ventas_totales DESC""",
    "top_productos_por_tienda": """WITH ventas_producto_tienda AS (
    SELECT
        s.s_store_id,
        s.s_store_name,
        i.i_item_id,
        COALESCE(i.i_product_name, i.i_item_desc) AS producto,
        SUM(COALESCE(ss.ss_quantity, 0)) AS cantidad_vendida
    FROM tpcds_bigdata.store_sales ss
    JOIN tpcds_bigdata.store s
        ON ss.ss_store_sk = s.s_store_sk
    JOIN tpcds_bigdata.item i
        ON ss.ss_item_sk = i.i_item_sk
    GROUP BY
        s.s_store_id,
        s.s_store_name,
        i.i_item_id,
        i.i_product_name,
        i.i_item_desc
),
ranking_productos AS (
    SELECT
        s_store_id,
        s_store_name,
        i_item_id,
        producto,
        cantidad_vendida,
        ROW_NUMBER() OVER (
            PARTITION BY s_store_id
            ORDER BY cantidad_vendida DESC
        ) AS ranking
    FROM ventas_producto_tienda
)
SELECT
    s_store_id,
    s_store_name,
    i_item_id,
    producto,
    cantidad_vendida,
    ranking
FROM ranking_productos
WHERE ranking <= 10
ORDER BY s_store_id, ranking""",
    "ticket_promedio_por_cliente": """SELECT
    c.c_customer_sk,
    c.c_customer_id,
    CONCAT(COALESCE(c.c_first_name, ''), ' ', COALESCE(c.c_last_name, '')) AS cliente,
    COUNT(*) AS numero_compras,
    SUM(COALESCE(ss.ss_net_paid, 0)) AS gasto_total,
    AVG(COALESCE(ss.ss_net_paid, 0)) AS ticket_promedio
FROM tpcds_bigdata.store_sales ss
JOIN tpcds_bigdata.customer c
    ON ss.ss_customer_sk = c.c_customer_sk
GROUP BY
    c.c_customer_sk,
    c.c_customer_id,
    c.c_first_name,
    c.c_last_name
ORDER BY ticket_promedio DESC
LIMIT 20""",
    "productos_mayor_ingreso": """SELECT
    i.i_item_sk,
    i.i_item_id,
    COALESCE(i.i_product_name, i.i_item_desc) AS producto,
    i.i_category,
    i.i_brand,
    SUM(COALESCE(ss.ss_net_paid, 0)) AS ingreso_generado
FROM tpcds_bigdata.store_sales ss
JOIN tpcds_bigdata.item i
    ON ss.ss_item_sk = i.i_item_sk
GROUP BY
    i.i_item_sk,
    i.i_item_id,
    i.i_product_name,
    i.i_item_desc,
    i.i_category,
    i.i_brand
ORDER BY ingreso_generado DESC
LIMIT 20""",
    "top_clientes_gasto_total": """SELECT
    c.c_customer_sk,
    c.c_customer_id,
    CONCAT(COALESCE(c.c_first_name, ''), ' ', COALESCE(c.c_last_name, '')) AS cliente,
    SUM(COALESCE(ss.ss_net_paid, 0)) AS gasto_total
FROM tpcds_bigdata.store_sales ss
JOIN tpcds_bigdata.customer c
    ON ss.ss_customer_sk = c.c_customer_sk
GROUP BY
    c.c_customer_sk,
    c.c_customer_id,
    c.c_first_name,
    c.c_last_name
ORDER BY gasto_total DESC
LIMIT 20""",
    "ranking_mensual_ventas": """WITH ventas_tienda_mes AS (
    SELECT
        d.d_year AS anio,
        d.d_moy AS mes,
        s.s_store_id,
        s.s_store_name,
        SUM(COALESCE(ss.ss_net_paid, 0)) AS ventas_totales
    FROM tpcds_bigdata.store_sales ss
    JOIN tpcds_bigdata.date_dim d
        ON ss.ss_sold_date_sk = d.d_date_sk
    JOIN tpcds_bigdata.store s
        ON ss.ss_store_sk = s.s_store_sk
    GROUP BY
        d.d_year,
        d.d_moy,
        s.s_store_id,
        s.s_store_name
),
ranking_mensual AS (
    SELECT
        anio,
        mes,
        s_store_id,
        s_store_name,
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
    s_store_id,
    s_store_name,
    ventas_totales,
    ranking_mensual
FROM ranking_mensual
WHERE ranking_mensual <= 10
ORDER BY anio, mes, ranking_mensual""",
    "cinco_productos_mas_vendidos": """SELECT
    i.i_item_id,
    COALESCE(i.i_product_name, i.i_item_desc) AS producto,
    SUM(COALESCE(ss.ss_quantity, 0)) AS cantidad_vendida
FROM tpcds_bigdata.store_sales ss
JOIN tpcds_bigdata.item i
    ON ss.ss_item_sk = i.i_item_sk
GROUP BY
    i.i_item_id,
    i.i_product_name,
    i.i_item_desc
ORDER BY cantidad_vendida DESC
LIMIT 5""",
    "tienda_mayores_ventas": """SELECT
    s.s_store_id,
    s.s_store_name,
    SUM(COALESCE(ss.ss_net_paid, 0)) AS ventas_totales
FROM tpcds_bigdata.store_sales ss
JOIN tpcds_bigdata.store s
    ON ss.ss_store_sk = s.s_store_sk
GROUP BY
    s.s_store_id,
    s.s_store_name
ORDER BY ventas_totales DESC
LIMIT 1""",
    "mes_mayores_ingresos": """SELECT
    d.d_year AS anio,
    d.d_moy AS mes,
    SUM(COALESCE(ss.ss_net_paid, 0)) AS ingresos_totales
FROM tpcds_bigdata.store_sales ss
JOIN tpcds_bigdata.date_dim d
    ON ss.ss_sold_date_sk = d.d_date_sk
GROUP BY
    d.d_year,
    d.d_moy
ORDER BY ingresos_totales DESC
LIMIT 1""",
    "diez_mejores_clientes": """SELECT
    c.c_customer_sk,
    c.c_customer_id,
    CONCAT(COALESCE(c.c_first_name, ''), ' ', COALESCE(c.c_last_name, '')) AS cliente,
    SUM(COALESCE(ss.ss_net_paid, 0)) AS gasto_total
FROM tpcds_bigdata.store_sales ss
JOIN tpcds_bigdata.customer c
    ON ss.ss_customer_sk = c.c_customer_sk
GROUP BY
    c.c_customer_sk,
    c.c_customer_id,
    c.c_first_name,
    c.c_last_name
ORDER BY gasto_total DESC
LIMIT 10""",
}


ESQUEMA_TPCDS = """Base de datos: tpcds_bigdata

Tabla tpcds_bigdata.customer:
- c_customer_sk INT
- c_customer_id STRING
- c_first_name STRING
- c_last_name STRING
- c_email_address STRING

Tabla tpcds_bigdata.item:
- i_item_sk INT
- i_item_id STRING
- i_item_desc STRING
- i_product_name STRING
- i_category STRING
- i_brand STRING

Tabla tpcds_bigdata.store:
- s_store_sk INT
- s_store_id STRING
- s_store_name STRING
- s_city STRING
- s_state STRING
- s_country STRING

Tabla tpcds_bigdata.date_dim:
- d_date_sk INT
- d_date DATE
- d_year INT
- d_moy INT
- d_day_name STRING

Tabla tpcds_bigdata.store_sales:
- ss_sold_date_sk INT
- ss_item_sk INT
- ss_customer_sk INT
- ss_store_sk INT
- ss_ticket_number STRING
- ss_quantity INT
- ss_net_paid DOUBLE
- ss_net_profit DOUBLE"""


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
- Usa siempre nombres de tablas calificados con base de datos, por ejemplo tpcds_bigdata.store_sales.
- No incluyas USE tpcds_bigdata.
- No agregues punto y coma al final.
- Devuelve unicamente SQL valido para Hive/Spark.
- No uses Markdown, explicaciones, comentarios ni texto adicional.
- Usa COALESCE en agregaciones numericas cuando aplique.

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
    if "USE TPCDS_BIGDATA" in sql_upper:
        raise ValueError("El SQL no debe incluir USE tpcds_bigdata.")
    if sql_limpio.endswith(";"):
        raise ValueError("El SQL no debe terminar en punto y coma.")
    if "tpcds_bigdata." not in sql_limpio:
        raise ValueError("El SQL debe usar tablas calificadas con tpcds_bigdata.")


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
