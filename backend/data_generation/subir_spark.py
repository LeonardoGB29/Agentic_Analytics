import os
from pyspark.sql import SparkSession

# Iniciamos sesión de Spark con soporte para Hive Metastore
spark = SparkSession.builder \
    .appName("Register TPC-DS Parquet Tables") \
    .enableHiveSupport() \
    .getOrCreate()

# Crear la base de datos para Parquet
spark.sql("CREATE DATABASE IF NOT EXISTS tpcds_parquet")
spark.sql("USE tpcds_parquet")


BASE_OUTPUT = f"{os.environ.get('S3_BUCKET', 's3://tpcds-bigdata-unsa-2026')}/data_parquet"

# Lista de todas las tablas que convertiste
TABLES = [
    "call_center", "catalog_page", "catalog_sales", "customer",
    "customer_address", "customer_demographics", "date_dim",
    "household_demographics", "income_band", "inventory", "item",
    "promotion", "reason", "ship_mode", "store", "store_sales",
    "time_dim", "warehouse", "web_page", "web_sales", "web_site",
    "catalog_returns", "web_returns", "store_returns"
]

for t in TABLES:
    print(f"Registrando tabla: {t}")
    # Spark infiere el esquema y las columnas directamente desde los archivos Parquet en S3
    spark.sql(f"""
        CREATE TABLE IF NOT EXISTS {t}
        USING PARQUET
        LOCATION '{BASE_OUTPUT}/{t}'
    """)
    print(f"Tabla {t} registrada con éxito.")
