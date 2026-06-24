# Agente Analitico Retail TPC-DS

Este modulo implementa las Skills 1, 2 y 3 para un proyecto de Big Data Retail
con TPC-DS sobre Hive y Spark.

Para levantar el proyecto completo en Amazon EMR con S3, Hive, Spark, backend,
frontend y Gemini, revisar [GUIA_EMR.md](GUIA_EMR.md).

## Que hace

`backend/skills_1_2_3.py` recibe una pregunta en lenguaje natural, identifica la
intencion analitica, genera una consulta SQL compatible con Hive/Spark SQL y
selecciona el motor de ejecucion.

El modulo no ejecuta consultas, no se conecta a Hive, no se conecta a Spark y no
solo devuelve:

```python
sql: str
motor: str
```

## Configuracion de Gemini

Las Skills 1, 2 y 3 usan Gemini mediante la API REST oficial, sin depender del
SDK `google-genai`, para mantener compatibilidad con Python 3.7 en Amazon EMR.

Instala dependencias:

```bash
pip install -r backend/requirements.txt
```

Configura tu API key de Google AI Studio:

```bash
export GEMINI_API_KEY=tu_api_key
```

Opcionalmente puedes elegir el modelo:

```bash
export GEMINI_MODEL=gemini-3.5-flash
```

Si no hay API key o Gemini devuelve una respuesta invalida, el modulo usa el
catalogo local como respaldo para no enviar SQL roto a la Skill 4.

## Optimizacion de cuota

La funcion principal `skill_1_2_3()` esta optimizada para no hacer tres llamadas
a Gemini por pregunta. En el flujo normal hace como maximo una llamada a Gemini
para resolver:

```text
pregunta -> intencion + motor
```

Luego genera el SQL desde el catalogo local validado. Esto ahorra cuota y evita
que un SQL mal formado del LLM llegue a Hive o Spark.

Las funciones individuales `skill_1_identificar_intencion`,
`skill_2_generar_sql` y `skill_3_seleccionar_motor` siguen existiendo para
probar cada skill por separado, pero para el pipeline real se debe usar:

```python
from backend.skills_1_2_3 import skill_1_2_3

sql, motor = skill_1_2_3("Que productos generaron mas dinero?")
```

Para correr pruebas sin gastar cuota de Gemini:

```bash
export GEMINI_DESACTIVADO=1
python backend/test_skills.py
```

Para volver a usar Gemini, elimina esa variable en la terminal actual:

```bash
unset GEMINI_DESACTIVADO
```

## Consultas fuera del catalogo

El agente usa un flujo hibrido en una sola llamada a Gemini:

1. Si la pregunta coincide con una intencion conocida, Gemini devuelve
   `tipo="catalogo"` y se usa el SQL aprobado en `skill2.py`.
2. Si es una pregunta analitica nueva que puede resolverse con las cinco tablas,
   Gemini devuelve `tipo="dinamica"`, genera el SQL y selecciona Hive o Spark.
3. Si la pregunta no es analitica o requiere columnas que no existen, devuelve
   `tipo="no_analitica"` y el sistema la rechaza.

El SQL dinamico se valida antes de llegar a Skill 4. Solo se permiten consultas
`SELECT`/`WITH`, las tablas de `tpcds_parquet` y una unica sentencia. Se
rechazan DDL, DML, comentarios, tablas inventadas y operaciones destructivas.

## Archivos

```text
backend/gemini_utils.py  # configuracion comun de Gemini
backend/skill1.py        # Skill 1: interpretacion de intencion con Gemini
backend/skill2.py        # Skill 2: generacion de SQL con Gemini
backend/skill3.py        # Skill 3: seleccion de motor con Gemini
backend/skills_1_2_3.py  # orquestador que devuelve (sql, motor)
backend/test_skills.py   # pruebas simples con assert
```

## Ejemplo de uso

```python
from backend.skills_1_2_3 import skill_1_2_3

pregunta = "Que tienda tuvo mayores ventas?"
sql, motor = skill_1_2_3(pregunta, modo="both")

resultado = skill_4_ejecutar(sql, motor, spark)
```

`modo` puede ser `"auto"`, `"hive"`, `"spark"` o `"both"`. En modo automatico,
la Skill 3 envia consultas pesadas a Spark y consultas simples a Hive.

## Pruebas

```bash
python backend/test_skills.py
```
