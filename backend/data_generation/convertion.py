import os
import re
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DecimalType, DateType

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

spark = SparkSession.builder \
    .appName("TPCDS DAT to Parquet") \
    .getOrCreate()

S3_BUCKET = os.environ.get("S3_BUCKET", "s3://tpcds-bigdata-unsa-2026")
BASE_INPUT = f"{S3_BUCKET}/data"
BASE_OUTPUT = f"{S3_BUCKET}/data_parquet"
SQL_FILE_PATH = "tablas.sql"

def parse_schemas_from_sql(sql_file_path):
    if not os.path.exists(sql_file_path):
        raise FileNotFoundError(f"No se encontró el archivo SQL en: {sql_file_path}")

    with open(sql_file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Expresión regular para encontrar bloques de CREATE EXTERNAL TABLE
    table_pattern = re.compile(
        r"CREATE\s+EXTERNAL\s+TABLE\s+IF\s+NOT\s+EXISTS\s+(\w+)\s*\((.*?)\)\s*ROW\s+FORMAT",
        re.IGNORECASE | re.DOTALL
    )

    schemas = {}
    for match in table_pattern.finditer(content):
        table_name = match.group(1).strip()
        columns_text = match.group(2).strip()
        
        fields = []
        for line in columns_text.split("\n"):
            line = line.strip()
            if not line or line.startswith("--"):
                continue
            
            # Quitar la coma final si existe
            if line.endswith(","):
                line = line[:-1].strip()
            
            parts = line.split()
            if len(parts) >= 2:
                col_name = parts[0].strip()
                col_type = parts[1].strip().lower()
                
                # Mapear tipo SQL a tipo PySpark
                if col_type == "int":
                    spark_type = IntegerType()
                elif col_type == "string":
                    spark_type = StringType()
                elif col_type == "date":
                    spark_type = DateType()
                elif col_type.startswith("decimal"):
                    dec_match = re.match(r"decimal\((\d+),(\d+)\)", col_type)
                    if dec_match:
                        p = int(dec_match.group(1))
                        s = int(dec_match.group(2))
                        spark_type = DecimalType(p, s)
                    else:
                        spark_type = DecimalType(7, 2)
                else:
                    spark_type = StringType()
                
                fields.append(StructField(col_name, spark_type, True))
        
        schemas[table_name] = StructType(fields)
    return schemas

# Cargar esquemas desde el archivo SQL
print(">> Cargando esquemas desde tablas.sql...")
table_schemas = parse_schemas_from_sql(SQL_FILE_PATH)
print(f">> Se cargaron {len(table_schemas)} esquemas de tablas.")

from pyspark.sql.functions import coalesce, lit

# Cargar date_dim primero y cachear para los joins de particiones
print(">> Cargando date_dim para joins de partición...")
try:
    date_dim_schema = table_schemas.get("date_dim")
    df_date_dim = spark.read \
        .option("sep", "|") \
        .option("header", "false") \
        .option("dateFormat", "yyyy-MM-dd") \
        .schema(date_dim_schema) \
        .csv(f"{BASE_INPUT}/date_dim")
    df_date_year = df_date_dim.select("d_date_sk", "d_year").cache()
except Exception as e:
    print(f"ADVERTENCIA -> No se pudo cachear date_dim: {e}. Se usará año default.")
    df_date_year = None

PARTITION_KEYS = {
    "store_sales": ("ss_sold_date_sk", "ss_sold_year"),
    "catalog_sales": ("cs_sold_date_sk", "cs_sold_year"),
    "web_sales": ("ws_sold_date_sk", "ws_sold_year"),
    "store_returns": ("sr_returned_date_sk", "sr_returned_year"),
    "catalog_returns": ("cr_returned_date_sk", "cr_returned_year"),
    "web_returns": ("wr_returned_date_sk", "wr_returned_year"),
    "inventory": ("inv_date_sk", "inv_year"),
}

for t, schema in table_schemas.items():
    print(f"Procesando tabla: {t}")

    try:
        # Leemos especificando el esquema correcto.
        # Al definir el esquema de N columnas, Spark descarta la columna vacía extra al final del archivo .dat (N+1).
        df = spark.read \
            .option("sep", "|") \
            .option("header", "false") \
            .option("dateFormat", "yyyy-MM-dd") \
            .schema(schema) \
            .csv(f"{BASE_INPUT}/{t}")

        if t in PARTITION_KEYS and df_date_year is not None:
            date_sk_col, partition_col = PARTITION_KEYS[t]
            df = df.join(df_date_year, df[date_sk_col] == df_date_year["d_date_sk"], "left") \
                   .withColumn(partition_col, coalesce(df_date_year["d_year"], lit(0))) \
                   .drop("d_date_sk", "d_year")

            df.write \
                .mode("overwrite") \
                .partitionBy(partition_col) \
                .parquet(f"{BASE_OUTPUT}/{t}")
            print(f"OK -> {t} convertido a Parquet particionado por {partition_col}.")
        else:
            df.write \
                .mode("overwrite") \
                .parquet(f"{BASE_OUTPUT}/{t}")
            print(f"OK -> {t} convertido a Parquet plano.")
    except Exception as e:
        if "PATH_NOT_FOUND" in str(e) or "does not exist" in str(e):
            print(f"ADVERTENCIA -> La ruta para la tabla '{t}' no existe en S3. Se omite.")
        else:
            print(f"ERROR -> Error al procesar la tabla '{t}': {e}")

