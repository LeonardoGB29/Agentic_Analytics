"""
datawarehouse_spark.py


Tablas creadas en la base de datos 'dw_retail':
  - dim_cliente   (dimensión de clientes)
  - dim_tienda    (dimensión de tiendas)
  - dim_producto  (dimensión de productos/items)
  - dim_fecha     (dimensión temporal)
  - fact_ventas   (tabla de hechos, particionada por anio_venta)

Uso:
  spark-submit --master yarn --deploy-mode client datawarehouse_spark.py
"""

import os
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window


# ── Cargar deploy.env ────────────────────────────────────────────────────────
def load_deploy_env():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    for _ in range(3):
        env_path = os.path.join(current_dir, "deploy.env")
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        os.environ[k] = v
            break
        current_dir = os.path.dirname(current_dir)

load_deploy_env()

S3_BUCKET = os.environ.get("S3_BUCKET", "s3://tpcds-bigdata-unsa-2026")
DW_OUTPUT = f"{S3_BUCKET}/dw_retail"

# ── Spark Session ────────────────────────────────────────────────────────────
spark = SparkSession.builder \
    .appName("DW Retail - Star Schema Builder") \
    .enableHiveSupport() \
    .getOrCreate()

spark.sql("CREATE DATABASE IF NOT EXISTS dw_retail")
spark.sql("USE tpcds_parquet")

print("=" * 60)
print(" Construyendo Data Warehouse Retail (dw_retail)")
print("=" * 60)


# ── 1. dim_cliente ───────────────────────────────────────────────────────────
print("\n>> Creando dim_cliente...")

customer = spark.table("customer")
address = spark.table("customer_address")
demographics = spark.table("customer_demographics")
household = spark.table("household_demographics")

dim_cliente = customer \
    .join(address, customer.c_current_addr_sk == address.ca_address_sk, "left") \
    .join(demographics, customer.c_current_cdemo_sk == demographics.cd_demo_sk, "left") \
    .join(household, customer.c_current_hdemo_sk == household.hd_demo_sk, "left") \
    .select(
        customer.c_customer_sk.alias("cliente_sk"),
        customer.c_customer_id.alias("cliente_id"),
        customer.c_salutation.alias("saludo"),
        customer.c_first_name.alias("nombre"),
        customer.c_last_name.alias("apellido"),
        F.concat(
            F.coalesce(customer.c_first_name, F.lit("")),
            F.lit(" "),
            F.coalesce(customer.c_last_name, F.lit(""))
        ).alias("nombre_completo"),
        customer.c_email_address.alias("email"),
        customer.c_birth_year.alias("anio_nacimiento"),
        customer.c_birth_country.alias("pais_nacimiento"),
        customer.c_preferred_cust_flag.alias("es_cliente_preferido"),
        address.ca_city.alias("ciudad"),
        address.ca_state.alias("estado"),
        address.ca_country.alias("pais"),
        address.ca_zip.alias("codigo_postal"),
        demographics.cd_gender.alias("genero"),
        demographics.cd_marital_status.alias("estado_civil"),
        demographics.cd_education_status.alias("nivel_educativo"),
        demographics.cd_credit_rating.alias("calificacion_crediticia"),
        household.hd_buy_potential.alias("potencial_compra"),
        household.hd_dep_count.alias("num_dependientes"),
        household.hd_vehicle_count.alias("num_vehiculos"),
    )

dim_cliente.write \
    .mode("overwrite") \
    .option("path", f"{DW_OUTPUT}/dim_cliente") \
    .saveAsTable("dw_retail.dim_cliente")

print(f"   dim_cliente: {dim_cliente.count()} filas")


# ── 2. dim_tienda ────────────────────────────────────────────────────────────
print("\n>> Creando dim_tienda...")

store = spark.table("store")

dim_tienda = store.select(
    store.s_store_sk.alias("tienda_sk"),
    store.s_store_id.alias("tienda_id"),
    store.s_store_name.alias("nombre_tienda"),
    store.s_number_employees.alias("num_empleados"),
    store.s_floor_space.alias("superficie_m2"),
    store.s_hours.alias("horario"),
    store.s_manager.alias("gerente"),
    store.s_city.alias("ciudad"),
    store.s_county.alias("condado"),
    store.s_state.alias("estado"),
    store.s_zip.alias("codigo_postal"),
    store.s_country.alias("pais"),
    store.s_market_id.alias("mercado_id"),
    store.s_market_desc.alias("mercado_desc"),
    store.s_division_name.alias("division"),
    store.s_company_name.alias("compania"),
    store.s_tax_precentage.alias("tasa_impuesto"),
)

dim_tienda.write \
    .mode("overwrite") \
    .option("path", f"{DW_OUTPUT}/dim_tienda") \
    .saveAsTable("dw_retail.dim_tienda")

print(f"   dim_tienda: {dim_tienda.count()} filas")


# ── 3. dim_producto ──────────────────────────────────────────────────────────
print("\n>> Creando dim_producto...")

item = spark.table("item")

dim_producto = item.select(
    item.i_item_sk.alias("producto_sk"),
    item.i_item_id.alias("producto_id"),
    F.coalesce(item.i_product_name, item.i_item_desc).alias("nombre_producto"),
    item.i_item_desc.alias("descripcion"),
    item.i_category.alias("categoria"),
    item.i_category_id.alias("categoria_id"),
    item.i_class.alias("clase"),
    item.i_class_id.alias("clase_id"),
    item.i_brand.alias("marca"),
    item.i_brand_id.alias("marca_id"),
    item.i_manufact.alias("fabricante"),
    item.i_manufact_id.alias("fabricante_id"),
    item.i_size.alias("talla"),
    item.i_color.alias("color"),
    item.i_units.alias("unidad_medida"),
    item.i_current_price.alias("precio_actual"),
    item.i_wholesale_cost.alias("costo_mayoreo"),
)

dim_producto.write \
    .mode("overwrite") \
    .option("path", f"{DW_OUTPUT}/dim_producto") \
    .saveAsTable("dw_retail.dim_producto")

print(f"   dim_producto: {dim_producto.count()} filas")


# ── 4. dim_fecha ─────────────────────────────────────────────────────────────
print("\n>> Creando dim_fecha...")

date_dim = spark.table("date_dim")

dim_fecha = date_dim.select(
    date_dim.d_date_sk.alias("fecha_sk"),
    date_dim.d_date.alias("fecha"),
    date_dim.d_year.alias("anio"),
    date_dim.d_moy.alias("mes"),
    date_dim.d_dom.alias("dia_mes"),
    date_dim.d_dow.alias("dia_semana_num"),
    date_dim.d_day_name.alias("dia_semana"),
    date_dim.d_qoy.alias("trimestre"),
    date_dim.d_quarter_name.alias("nombre_trimestre"),
    date_dim.d_week_seq.alias("semana_seq"),
    date_dim.d_holiday.alias("es_feriado"),
    date_dim.d_weekend.alias("es_fin_semana"),
    date_dim.d_current_day.alias("es_dia_actual"),
    date_dim.d_current_week.alias("es_semana_actual"),
    date_dim.d_current_month.alias("es_mes_actual"),
    date_dim.d_current_quarter.alias("es_trimestre_actual"),
    date_dim.d_current_year.alias("es_anio_actual"),
)

dim_fecha.write \
    .mode("overwrite") \
    .option("path", f"{DW_OUTPUT}/dim_fecha") \
    .saveAsTable("dw_retail.dim_fecha")

print(f"   dim_fecha: {dim_fecha.count()} filas")


# ── 5. fact_ventas (particionada por anio_venta) ─────────────────────────────
print("\n>> Creando fact_ventas (particionada por anio_venta)...")

store_sales = spark.table("store_sales")

# Agregar el año de venta desde date_dim
fact_ventas = store_sales \
    .join(date_dim.select("d_date_sk", "d_year"),
          store_sales.ss_sold_date_sk == date_dim.d_date_sk, "left") \
    .select(
        F.monotonically_increasing_id().alias("venta_sk"),
        store_sales.ss_customer_sk.alias("cliente_sk"),
        store_sales.ss_store_sk.alias("tienda_sk"),
        store_sales.ss_item_sk.alias("producto_sk"),
        store_sales.ss_sold_date_sk.alias("fecha_sk"),
        store_sales.ss_promo_sk.alias("promo_sk"),
        store_sales.ss_ticket_number.alias("ticket_number"),
        store_sales.ss_quantity.alias("cantidad"),
        store_sales.ss_sales_price.alias("precio_venta"),
        store_sales.ss_wholesale_cost.alias("costo_mayoreo"),
        store_sales.ss_ext_discount_amt.alias("descuento"),
        store_sales.ss_net_paid.alias("venta_neta"),
        store_sales.ss_net_paid_inc_tax.alias("venta_neta_con_impuesto"),
        store_sales.ss_ext_tax.alias("impuesto"),
        store_sales.ss_coupon_amt.alias("cupon"),
        store_sales.ss_net_profit.alias("ganancia_neta"),
        F.coalesce(date_dim.d_year, F.lit(0)).alias("anio_venta"),
    )

fact_ventas.write \
    .mode("overwrite") \
    .partitionBy("anio_venta") \
    .option("path", f"{DW_OUTPUT}/fact_ventas") \
    .saveAsTable("dw_retail.fact_ventas")

count_ventas = spark.table("dw_retail.fact_ventas").count()
print(f"   fact_ventas: {count_ventas} filas")


# ── Resumen ──────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print(" Data Warehouse Retail creado exitosamente")
print("=" * 60)

summary = spark.sql("""
    SELECT 'dim_cliente'  AS tabla, COUNT(*) AS filas FROM dw_retail.dim_cliente
    UNION ALL
    SELECT 'dim_tienda',  COUNT(*) FROM dw_retail.dim_tienda
    UNION ALL
    SELECT 'dim_producto', COUNT(*) FROM dw_retail.dim_producto
    UNION ALL
    SELECT 'dim_fecha',    COUNT(*) FROM dw_retail.dim_fecha
    UNION ALL
    SELECT 'fact_ventas',  COUNT(*) FROM dw_retail.fact_ventas
""")
summary.show(truncate=False)

# Mostrar particiones
print(">> Particiones de fact_ventas:")
spark.sql("SHOW PARTITIONS dw_retail.fact_ventas").show(truncate=False)

print(f">> Datos almacenados en: {DW_OUTPUT}/")
print(">> Listo.")
