import os

os.environ["GEMINI_DESACTIVADO"] = "1"

from skills_1_2_3 import _resolver_plan
from skills_1_2_3 import (
    listar_intenciones_disponibles,
    normalizar_texto,
    skill_1_2_3,
    skill_1_identificar_intencion,
    skill_2_generar_sql,
    skill_3_seleccionar_motor,
)


PREGUNTAS_REALES = {
    "top_20_clientes_compras": [
        "Muestrame los 20 clientes que mas compras hicieron",
        "Quiero saber cuales son los veinte clientes con mas compras registradas",
        "Dame el ranking de clientes por cantidad de compras, solo los primeros 20",
        "Que clientes compraron mas veces en la tienda?",
    ],
    "ventas_por_tienda": [
        "Cuanto vendio cada tienda en total?",
        "Necesito comparar las ventas totales entre tiendas",
        "Muestrame el total vendido agrupado por tienda",
        "Como van las ventas por local?",
    ],
    "ventas_por_mes": [
        "Como se comportaron las ventas mes a mes?",
        "Dame las ventas mensuales del negocio",
        "Quiero ver el total de ventas agrupado por anio y mes",
        "Cuanto se vendio en cada mes?",
    ],
    "ventas_por_dia_semana": [
        "Que dias de la semana se vende mas?",
        "Dame las ventas agrupadas por dia semanal",
        "Quiero saber si se vende mas lunes, martes o fines de semana",
        "Cuales son los dias con mayor venta?",
    ],
    "top_productos_por_tienda": [
        "Cuales son los productos mas vendidos en cada tienda?",
        "Dame el top 10 de productos por cada tienda",
        "Por tienda, que productos tuvieron mayor cantidad vendida?",
        "Necesito saber los productos lideres de venta en cada local",
    ],
    "ticket_promedio_por_cliente": [
        "Cuanto gasta en promedio cada cliente por compra?",
        "Dame el ticket medio de los clientes",
        "Cual es el promedio de gasto por cliente?",
        "Quiero ver el monto promedio que paga cada cliente",
    ],
    "productos_mayor_ingreso": [
        "Que productos generaron mas dinero?",
        "Dame los productos que mas ingresos produjeron",
        "Cuales son los articulos con mayor venta en dinero?",
        "Ordena los productos por ingreso total generado",
    ],
    "top_clientes_gasto_total": [
        "Quienes son los clientes que mas dinero gastaron?",
        "Dame los clientes con mayor gasto acumulado",
        "Quiero ver el top de clientes por monto total comprado",
        "Cuales clientes dejaron mas ingresos al negocio?",
    ],
    "ranking_mensual_ventas": [
        "Haz un ranking de ventas por cada mes",
        "Quiero ver las tiendas ordenadas por ventas dentro de cada mes",
        "Dame el ranking mensual de tiendas segun ventas",
        "Por cada mes, que tienda vendio mas?",
    ],
    "cinco_productos_mas_vendidos": [
        "Cuales son los 5 productos con mas unidades vendidas?",
        "Dame los cinco articulos mas vendidos",
        "Top 5 productos por cantidad vendida",
        "Que productos se vendieron mas en cantidad? Solo cinco",
    ],
    "tienda_mayores_ventas": [
        "Cual fue la tienda que mas vendio?",
        "Que local tuvo el mayor monto de ventas?",
        "Dime la tienda numero uno en ventas",
        "Cual tienda genero el mayor ingreso total?",
    ],
    "mes_mayores_ingresos": [
        "En que mes se gano mas dinero?",
        "Cual fue el mes con el mayor ingreso total?",
        "Dime el mes mas fuerte en ventas",
        "Que mes tuvo la mayor facturacion?",
    ],
    "diez_mejores_clientes": [
        "Dame los 10 clientes mas importantes por gasto",
        "Cuales son los diez clientes que mas compraron en dinero?",
        "Top 10 mejores clientes segun gasto total",
        "Quienes son los 10 clientes mas valiosos para el negocio?",
    ],
}


def test_normalizar_texto():
    assert normalizar_texto("  Ventas por DIA de la semana  ") == "ventas por dia de la semana"


def test_skill_1_identifica_preguntas_reales_de_usuario():
    for intencion_esperada, preguntas in PREGUNTAS_REALES.items():
        for pregunta in preguntas:
            assert skill_1_identificar_intencion(pregunta) == intencion_esperada, pregunta


def test_skill_1_tolera_variantes_cortas_y_modo_conversacional():
    casos = {
        "ventas x tienda": "ventas_por_tienda",
        "ticket promedio x cliente": "ticket_promedio_por_cliente",
        "top clientes x gasto total": "top_clientes_gasto_total",
        "productos que mas plata generaron": "productos_mayor_ingreso",
        "mes con mas facturacion": "mes_mayores_ingresos",
    }

    for pregunta, intencion_esperada in casos.items():
        assert skill_1_identificar_intencion(pregunta) == intencion_esperada


def test_skill_2_genera_sql_valido_para_todas_las_intenciones():
    for intencion in listar_intenciones_disponibles():
        sql = skill_2_generar_sql(intencion)
        assert sql.lstrip().upper().startswith(("SELECT", "WITH"))
        assert "tpcds_bigdata." in sql
        assert "USE TPCDS_BIGDATA" not in sql.upper()
        assert not sql.rstrip().endswith(";")


def test_skill_2_sql_contiene_tablas_esperadas_en_casos_clave():
    sql = skill_2_generar_sql("top_productos_por_tienda")
    assert "tpcds_bigdata.store_sales" in sql
    assert "tpcds_bigdata.store" in sql
    assert "tpcds_bigdata.item" in sql
    assert "ROW_NUMBER()" in sql

    sql = skill_2_generar_sql("ranking_mensual_ventas")
    assert "tpcds_bigdata.date_dim" in sql
    assert "RANK()" in sql


def test_skill_3_auto_selecciona_motor_esperado():
    assert skill_3_seleccionar_motor("ticket_promedio_por_cliente") == "hive"
    assert skill_3_seleccionar_motor("ventas_por_dia_semana") == "hive"
    assert skill_3_seleccionar_motor("ventas_por_tienda") == "spark"
    assert skill_3_seleccionar_motor("ranking_mensual_ventas") == "spark"


def test_skill_3_respeta_modo_manual():
    assert skill_3_seleccionar_motor("ventas_por_tienda", modo="hive") == "hive"
    assert skill_3_seleccionar_motor("ventas_por_tienda", modo="spark") == "spark"
    assert skill_3_seleccionar_motor("ventas_por_tienda", modo="both") == "both"


def test_skill_1_2_3_end_to_end_con_preguntas_reales():
    casos = [
        ("Cuales son los 5 productos con mas unidades vendidas?", "LIMIT 5", "spark"),
        ("Necesito comparar las ventas totales entre tiendas", "SUM", "spark"),
        ("Dame el ranking mensual de tiendas segun ventas", "RANK()", "spark"),
        ("Cuanto gasta en promedio cada cliente por compra?", "AVG", "hive"),
    ]

    for pregunta, fragmento_sql, motor_esperado in casos:
        sql, motor = skill_1_2_3(pregunta)
        assert fragmento_sql in sql
        assert "tpcds_bigdata.store_sales" in sql
        assert motor == motor_esperado




def test_motor_especificado_en_lenguaje_natural():
    _, motor = skill_1_2_3("Muestrame las ventas por tienda usando Hive")
    assert motor == "hive"

    _, motor = skill_1_2_3("Calcula el ticket promedio por cliente con Spark")
    assert motor == "spark"

    _, motor = skill_1_2_3("Quiero comparar las ventas por mes en Hive y Spark")
    assert motor == "both"

    _, motor = skill_1_2_3(
        "Muestrame las ventas por tienda usando Hive",
        modo="spark",
    )
    assert motor == "spark"

def test_errores_controlados():
    try:
        skill_1_identificar_intencion("Hola, puedes contarme un chiste?")
    except ValueError as exc:
        assert "intención" in str(exc)
    else:
        raise AssertionError("Se esperaba ValueError para una pregunta no analitica")

    try:
        skill_3_seleccionar_motor("ventas_por_tienda", modo="rapido")
    except ValueError as exc:
        assert "Modo" in str(exc)
    else:
        raise AssertionError("Se esperaba ValueError para modo invalido")




def test_plan_dinamico_genera_sql_nuevo_validado():
    plan = {
        "tipo": "dinamica",
        "intencion": "rentabilidad_por_estado",
        "sql": (
            "SELECT s.s_state, "
            "SUM(COALESCE(ss.ss_net_profit, 0)) AS utilidad_total "
            "FROM tpcds_bigdata.store_sales ss "
            "JOIN tpcds_bigdata.store s ON ss.ss_store_sk = s.s_store_sk "
            "GROUP BY s.s_state ORDER BY utilidad_total DESC"
        ),
        "motor": "spark",
    }

    sql, motor = _resolver_plan(plan)
    assert "ss_net_profit" in sql
    assert "tpcds_bigdata.store" in sql
    assert motor == "spark"


def test_plan_de_catalogo_reutiliza_sql_aprobado():
    sql, motor = _resolver_plan(
        {
            "tipo": "catalogo",
            "intencion": "ventas_por_mes",
            "sql": None,
            "motor": "spark",
        }
    )
    assert "tpcds_bigdata.date_dim" in sql
    assert motor == "spark"


def test_plan_dinamico_rechaza_sql_peligroso_o_tablas_inventadas():
    planes_invalidos = [
        {
            "tipo": "dinamica",
            "intencion": "borrar_datos",
            "sql": "SELECT * FROM tpcds_bigdata.customer; DROP TABLE tpcds_bigdata.customer",
            "motor": "hive",
        },
        {
            "tipo": "dinamica",
            "intencion": "ventas_web",
            "sql": "SELECT * FROM tpcds_bigdata.web_sales",
            "motor": "spark",
        },
    ]

    for plan in planes_invalidos:
        try:
            _resolver_plan(plan)
        except ValueError:
            pass
        else:
            raise AssertionError("Se esperaba rechazar el SQL dinamico invalido")

if __name__ == "__main__":
    test_normalizar_texto()
    test_skill_1_identifica_preguntas_reales_de_usuario()
    test_skill_1_tolera_variantes_cortas_y_modo_conversacional()
    test_skill_2_genera_sql_valido_para_todas_las_intenciones()
    test_skill_2_sql_contiene_tablas_esperadas_en_casos_clave()
    test_skill_3_auto_selecciona_motor_esperado()
    test_skill_3_respeta_modo_manual()
    test_skill_1_2_3_end_to_end_con_preguntas_reales()
    test_motor_especificado_en_lenguaje_natural()
    test_errores_controlados()
    test_plan_dinamico_genera_sql_nuevo_validado()
    test_plan_de_catalogo_reutiliza_sql_aprobado()
    test_plan_dinamico_rechaza_sql_peligroso_o_tablas_inventadas()

    preguntas = [
        "Cuales son los 5 productos con mas unidades vendidas?",
        "Necesito comparar las ventas totales entre tiendas",
        "Dame el ranking mensual de tiendas segun ventas",
        "Cuanto gasta en promedio cada cliente por compra?",
        "Estoy revisando el comportamiento general del negocio y quiero identificar, sin enfocarme todavía en clientes ni en tiendas específicas, cuáles son los artículos que realmente aportaron más dinero a la empresa; es decir, no me interesa solo saber qué productos se vendieron más veces, sino cuáles generaron el mayor ingreso total considerando todas las ventas registradas.",
    ]

    for pregunta in preguntas:
        sql, motor = skill_1_2_3(pregunta)
        print("=" * 80)
        print("Pregunta:", pregunta)
        print("Motor:", motor)
        print("SQL:")
        print(sql)
