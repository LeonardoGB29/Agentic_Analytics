import os
from pyspark.sql import SparkSession

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

PARTITION_KEYS = {
    "store_sales", "catalog_sales", "web_sales",
    "store_returns", "catalog_returns", "web_returns", "inventory"
}

for t in TABLES:
    print(f"Registrando tabla: {t}")
    # Spark infiere el esquema y las columnas directamente desde los archivos Parquet en S3
    spark.sql(f"""
        CREATE TABLE IF NOT EXISTS {t}
        USING PARQUET
        LOCATION '{BASE_OUTPUT}/{t}'
    """)
    if t in PARTITION_KEYS:
        print(f"Recuperando particiones para la tabla: {t}...")
        try:
            spark.sql(f"ALTER TABLE {t} RECOVER PARTITIONS")
            print(f"Particiones de {t} recuperadas.")
        except Exception as e:
            print(f"Error al recuperar particiones de {t}: {e}")
    print(f"Tabla {t} registrada con éxito.")
