import os
import re

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
    rf"ROW FORMAT DELIMITED FIELDS TERMINATED BY '\|'\s*\n\s*STORED AS TEXTFILE\s*\n\s*LOCATION\s+'s3://{re.escape(BUCKET_NAME)}/data/([^']+)/';",
    re.IGNORECASE
)

# Reemplazamos por STORED AS PARQUET y apuntamos a data_parquet/
def replacer(match):
    table_name = match.group(1)
    return f"STORED AS PARQUET\nLOCATION '{S3_BUCKET}/data_parquet/{table_name}/';"

sql_content_parquet = pattern.sub(replacer, sql_content)

print(f">> Escribiendo {output_sql}...")
with open(output_sql, "w", encoding="utf-8") as f:
    f.write(sql_content_parquet)

print(">> ¡Listo! Se ha generado tablas_hive_parquet.sql correctamente.")
