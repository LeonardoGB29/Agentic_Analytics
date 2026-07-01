import os
import re

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

S3_BUCKET = os.environ.get("S3_BUCKET", "s3://tpcds-bigdata-kevin-2026")
BUCKET_NAME = S3_BUCKET.replace("s3://", "").rstrip("/")

script_dir = os.path.dirname(os.path.abspath(__file__))
input_sql = os.path.join(script_dir, "tablas.sql")
output_sql = os.path.join(script_dir, "tablas_hive_parquet.sql")

print(f">> Leyendo {input_sql}...")
with open(input_sql, "r", encoding="utf-8") as f:
    sql_content = f.read()

# 1. Cambiar nombre de la base de datos a tpcds_parquet (opcional, para diferenciar)
sql_content = sql_content.replace("CREATE DATABASE IF NOT EXISTS tpcds_bigdata;", "CREATE DATABASE IF NOT EXISTS tpcds_parquet;")
sql_content = sql_content.replace("USE tpcds_bigdata;", "USE tpcds_parquet;")

# 2. Reemplazar la definición de formato y ubicación de las tablas
# Buscamos la estructura:
# ROW FORMAT DELIMITED FIELDS TERMINATED BY '|' 
# STORED AS TEXTFILE
# LOCATION 's3://tpcds-bigdata-kevin-2026/data/...';

# Expresión regular para capturar la definición de formato, almacenamiento y ubicación
pattern = re.compile(
    r"ROW FORMAT DELIMITED FIELDS TERMINATED BY '\|'\s*\n\s*STORED AS TEXTFILE\s*\n\s*LOCATION\s+'s3://[^/]+/data/([^']+)/';",
    re.IGNORECASE
)

# Reemplazamos por STORED AS PARQUET y apuntamos a data_parquet/
PARTITION_KEYS = {
    "store_sales": "ss_sold_year",
    "catalog_sales": "cs_sold_year",
    "web_sales": "ws_sold_year",
    "store_returns": "sr_returned_year",
    "catalog_returns": "cr_returned_year",
    "web_returns": "wr_returned_year",
    "inventory": "inv_year",
}

def replacer(match):
    table_name = match.group(1).strip()
    if table_name in PARTITION_KEYS:
        partition_col = PARTITION_KEYS[table_name]
        return f"PARTITIONED BY ({partition_col} int)\nSTORED AS PARQUET\nLOCATION '{S3_BUCKET}/data_parquet/{table_name}/';"
    else:
        return f"STORED AS PARQUET\nLOCATION '{S3_BUCKET}/data_parquet/{table_name}/';"

sql_content_parquet = pattern.sub(replacer, sql_content)

# Agregar MSCK REPAIR TABLE al final
repair_commands = "\n\n-- Reparar particiones en Hive Metastore\n"
for t in PARTITION_KEYS:
    repair_commands += f"MSCK REPAIR TABLE {t};\n"

sql_content_parquet += repair_commands

print(f">> Escribiendo {output_sql}...")
with open(output_sql, "w", encoding="utf-8") as f:
    f.write(sql_content_parquet)

print(">> ¡Listo! Se ha generado tablas_hive_parquet.sql correctamente.")
