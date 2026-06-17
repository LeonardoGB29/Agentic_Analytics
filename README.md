# Agente Analitico Retail TPC-DS

Este modulo implementa las Skills 1, 2 y 3 para un proyecto de Big Data Retail
con TPC-DS sobre Hive y Spark.

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

Las Skills 1, 2 y 3 usan Gemini mediante `google-generativeai`.

Instala dependencias:

```bash
pip install -r backend/requirements.txt
```

Configura tu API key de Google AI Studio:

```bash
set GEMINI_API_KEY=tu_api_key
```

Opcionalmente puedes elegir el modelo:

```bash
set GEMINI_MODEL=gemini-1.5-flash
```

Si no hay API key o Gemini devuelve una respuesta invalida, el modulo usa el
catalogo local como respaldo para no enviar SQL roto a la Skill 4.

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
