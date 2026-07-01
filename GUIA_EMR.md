# Guia para levantar la app en Amazon EMR

Esta guia describe el flujo completo para probar el proyecto en un cluster Amazon
EMR con Spark, Hive, S3, Flask y Gemini.

## Requisitos

- Cluster Amazon EMR con Hadoop, Hive y Spark.
- Bucket S3 propio para almacenar los datos TPC-DS.
- Llave SSH `.pem` para entrar al nodo primary.
- Permisos IAM del cluster sobre el bucket S3.
- API key de Gemini.

Variables de referencia:

```bash
BUCKET=s3://NOMBRE_DE_SU_BUCKET
IP_PUBLICA_EMR=IP_DEL_NODO_PRIMARY
KEY_PEM=su_llave.pem
```

Ejemplo:

```bash
BUCKET=s3://tpcds-bigdata-daniel-2026
```

## 1. Conectarse al EMR

Desde la computadora local:

```bash
chmod 400 su_llave.pem
ssh -i su_llave.pem hadoop@IP_PUBLICA_EMR
```

Resultado esperado:

```text
[hadoop@ip-... ~]$
```

## 2. Instalar herramientas basicas

Dentro del EMR:

```bash
sudo yum install -y git gcc make flex bison byacc
```

Resultado esperado: el comando termina sin errores. Si indica que los paquetes ya
estan instalados, tambien esta bien.

## 3. Clonar el repositorio

```bash
cd ~
git clone https://github.com/KevinRodriguezLima/Agentic_Analytics.git
cd Agentic_Analytics
git checkout daniel_dev
git pull origin daniel_dev
```

Resultado esperado:

```text
Switched to branch 'daniel_dev'
Already up to date.
```

## 4. Cambiar rutas S3 al bucket propio

Desde `~/Agentic_Analytics`:

```bash
export OLD_BUCKET="s3://tpcds-bigdata-kevin-2026"
export NEW_BUCKET="s3://tpcds-bigdata-unsa-2026"

grep -R "$OLD_BUCKET" -n backend/data_generation
sed -i "s#$OLD_BUCKET#$NEW_BUCKET#g" backend/data_generation/*.py backend/data_generation/*.sh backend/data_generation/*.sql
grep -R "$NEW_BUCKET" -n backend/data_generation
```

Reemplazar `s3://NOMBRE_DE_SU_BUCKET` por el bucket real.

Resultado esperado: el ultimo `grep` debe mostrar rutas actualizadas en archivos
como:

```text
backend/data_generation/convertion.py
backend/data_generation/data_generation.sh
backend/data_generation/tablas.sql
backend/data_generation/tablas_hive_parquet.sql
backend/data_generation/subir_spark.py
```

## 5. Verificar acceso al bucket

```bash
aws s3 ls $NEW_BUCKET/
```

Resultado esperado:

- Si no muestra nada y no hay error, el bucket esta accesible y vacio.
- Si muestra `AccessDenied`, falta permiso IAM del cluster sobre ese bucket.

## 6. Generar datos TPC-DS y subirlos a S3

```bash
cd ~/Agentic_Analytics
bash backend/data_generation/data_generation.sh
```

Resultado esperado:

- Puede tardar varios minutos.
- Puede mostrar warnings de `gcc`; normalmente no son problema.
- Puede mostrar `ctags ... ignored`; normalmente no es problema.
- Debe generar tablas y subir archivos `.dat` a S3.

Validar:

```bash
aws s3 ls $NEW_BUCKET/data/ | head
aws s3 ls $NEW_BUCKET/data/store_sales/ | head
aws s3 ls $NEW_BUCKET/data/ --recursive --summarize | tail -5
```

Resultado esperado: carpetas como `customer/`, `item/`, `store_sales/`, etc.

## 7. Crear tablas Hive raw

```bash
cd ~/Agentic_Analytics
hive -f backend/data_generation/tablas.sql
```

Resultado esperado: muchos mensajes `OK`.

Validar:

```bash
hive -e "USE tpcds_bigdata; SHOW TABLES;"
hive -e "USE tpcds_bigdata; SELECT COUNT(*) FROM store_sales;"
hive -e "USE tpcds_bigdata; SELECT COUNT(*) FROM customer;"
hive -e "USE tpcds_bigdata; SELECT COUNT(*) FROM item;"
```

Resultado esperado aproximado para escala 10 GB:

```text
store_sales = 28800991
customer = 500000
item = 102000
```

## 8. Convertir datos a Parquet con Spark

```bash
cd ~/Agentic_Analytics/backend/data_generation
python3 generate_hive_parquet_sql.py
spark-submit --master yarn --deploy-mode client convertion.py
```

Resultado esperado:

- Spark procesa las tablas.
- Se crean carpetas en `$NEW_BUCKET/data_parquet/`.
- Puede tardar varios minutos.

Validar:

```bash
aws s3 ls $NEW_BUCKET/data_parquet/ | head
aws s3 ls $NEW_BUCKET/data_parquet/store_sales/ | head
```

Resultado esperado: debe verse `_SUCCESS` y archivos `.snappy.parquet`.

## 9. Crear tablas Hive sobre Parquet

```bash
cd ~/Agentic_Analytics/backend/data_generation
hive -f tablas_hive_parquet.sql
```

Validar:

```bash
hive -e "USE tpcds_parquet; SHOW TABLES;"
hive -e "USE tpcds_parquet; SELECT COUNT(*) FROM store_sales;"
hive -e "USE tpcds_parquet; SELECT COUNT(*) FROM customer;"
hive -e "USE tpcds_parquet; SELECT COUNT(*) FROM item;"
```

Resultado esperado: los conteos deben coincidir con las tablas raw:

```text
store_sales = 28800991
customer = 500000
item = 102000
```

## 9.5 Construir el Data Warehouse (esquema estrella)

Este paso crea la base `dw_retail` con 4 dimensiones y 1 tabla de hechos
particionada por año:

> Importante: el agente analitico usa `dw_retail` para generar y ejecutar sus
> consultas. Si se omite este paso, la UI puede levantar, pero las preguntas
> fallaran porque no existiran `dw_retail.fact_ventas` ni sus dimensiones.

**Opción A — Con Spark (recomendado):**

```bash
cd ~/Agentic_Analytics/backend/data_generation
spark-submit --master yarn --deploy-mode client datawarehouse_spark.py
```

**Opción B — Con Hive:**

```bash
cd ~/Agentic_Analytics/backend/data_generation
hive -f datawarehouse_hive.sql
```

Validar:

```bash
hive -e "USE dw_retail; SHOW TABLES;"
hive -e "USE dw_retail; SHOW PARTITIONS fact_ventas;"
hive -e "SELECT 'fact_ventas' AS t, COUNT(*) AS n FROM dw_retail.fact_ventas UNION ALL SELECT 'dim_cliente', COUNT(*) FROM dw_retail.dim_cliente UNION ALL SELECT 'dim_tienda', COUNT(*) FROM dw_retail.dim_tienda UNION ALL SELECT 'dim_producto', COUNT(*) FROM dw_retail.dim_producto UNION ALL SELECT 'dim_fecha', COUNT(*) FROM dw_retail.dim_fecha;"
```

Resultado esperado:

```text
fact_ventas  = 28800991
dim_cliente  = 500000
dim_tienda   ≈ 402
dim_producto = 102000
dim_fecha    = 73049
```

## 10. Instalar dependencias del backend

```bash
cd ~/Agentic_Analytics
python3 -m pip install --user -r backend/requirements.txt
```

Si aparece un warning sobre `/home/hadoop/.local/bin` fuera del `PATH`, no
afecta a esta ejecucion.

## 11. Configurar Gemini

No se debe commitear una API key real al repositorio. Configurar la variable en
la terminal del EMR:

```bash
export GEMINI_API_KEY="KEy SCRET"
unset GEMINI_DESACTIVADO
```

Validar Gemini:

```bash
PYTHONPATH=backend python3 -c "from gemini_utils import generar_texto_gemini; print(generar_texto_gemini('Responde solo: OK'))"
```

Resultado esperado:

```text
OK
```

Si falla, revisar la API key, permisos de salida a internet del cluster o modelo
configurado.

## 12. Levantar el servidor en EMR

```bash
cd ~/Agentic_Analytics
PYTHONPATH=backend python3 backend/server.py
```

Resultado esperado:

```text
* Running on http://127.0.0.1:5000
```

Dejar esta terminal abierta.

### Si estás conectado por SSM (sin SSH directo)

**Opción A — Port forwarding por SSM (recomendado, no requiere abrir puertos):**

En tu computadora local (con AWS CLI instalado):

```bash
aws ssm start-session \
  --target <INSTANCE_ID_DEL_MASTER> \
  --document-name AWS-StartPortForwardingSession \
  --parameters "portNumber=5000,localPortNumber=5001"
```

Reemplazar `<INSTANCE_ID_DEL_MASTER>` con el Instance ID EC2 del nodo master
(visible en EMR → Cluster → Summary, o en EC2 → Instances).

Luego abrir en el navegador local: `http://localhost:5001`

---

**Opción B — Escuchar en todas las interfaces (requiere puerto 5000 abierto en el Security Group):**

```bash
cd ~/Agentic_Analytics
SERVER_HOST=0.0.0.0 PYTHONPATH=backend python3 backend/server.py
```

Luego acceder desde el navegador con la IP pública del master:
`http://<IP_PUBLICA_EMR>:5000`

## 13. Abrir la UI desde la computadora local

En otra terminal local:

```bash
ssh -i su_llave.pem -L 5001:localhost:5000 hadoop@IP_PUBLICA_EMR
```

Luego abrir en el navegador local:

```text
http://localhost:5001
```

Importante: `http://localhost:5001` se abre en Safari, Chrome o Firefox. No se
ejecuta dentro de la terminal SSH.

## 14. Preguntas para probar

En la UI:

```text
Cuáles fueron los cinco productos mas vendidos?
Que tienda tuvo mayores ventas?
Cual fue el mes con mayores ingresos?
Cuales son los diez mejores clientes?
Que productos generaron mayores ingresos?
Ventas por mes
Ventas por dia de la semana
Ticket promedio por cliente
```

Resultado esperado:

- SQL generado.
- Tabla de resultados.
- Grafica.
- Tiempo de Hive vs Spark.

Ejemplo:

```text
Hive 24.8 s
Spark 6.3 s
Spark 3.9x mas rapido
```

## Problemas comunes

### `AccessDenied` al listar S3

El rol IAM del EMR no tiene permisos sobre el bucket. Dar permisos `s3:ListBucket`,
`s3:GetObject` y `s3:PutObject` para el bucket usado.

### `spark-submit: command not found`

El comando se esta ejecutando en la computadora local en vez del EMR. Debe correr
dentro de la terminal SSH del cluster.

### `aws: command not found`

Igual que lo anterior: normalmente se esta ejecutando fuera del EMR, o falta AWS
CLI en la maquina.

### `[Errno 32] Broken pipe` con `aws s3 ls ... | head`

Es normal. `head` corta la salida y `aws s3 ls` intenta seguir escribiendo.

### Error 500 en `/api/query`

Copiar el traceback completo de la terminal donde corre Flask. Ahi se ve si fallo
Gemini, Hive, Spark, una tabla o una consulta SQL.
