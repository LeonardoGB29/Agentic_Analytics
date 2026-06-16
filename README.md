# Agente Analítico — Retail TPC-DS

Agente que traduce preguntas en lenguaje natural a SQL y las ejecuta en
**Apache Hive** / **Apache Spark** sobre datos TPC-DS, con apoyo de un LLM
(Gemini). Interfaz web + API en Python.

## Estructura

```
trabajo_parcial_2/
├── frontend/
│   └── index.html          # interfaz completa (HTML + CSS + JS, sin frameworks)
├── backend/
│   ├── server.py           # API Flask: sirve el frontend y /api/query
│   ├── skill4.py           # ejecución de consultas en Hive y Spark
│   ├── skill5.py           # presentación de resultados (skill_5_to_json)
│   └── requirements.txt    # dependencias de Python
└── README.md
```

## 1. Solo frontend (rápido, sin instalar nada)

`frontend/index.html` es autónomo: no necesita servidor, dependencias ni
internet. Usa datos de ejemplo (mock).

> **Doble clic en `frontend/index.html`** y se abre en el navegador.

O desde la terminal:

```bash
open frontend/index.html          # macOS
```

## 2. Frontend + backend (sistema completo)

```bash
python3 -m venv venv
venv/bin/pip install -r backend/requirements.txt
venv/bin/python backend/server.py
```

Luego abre **http://localhost:5000**.

El frontend detecta solo si está servido por HTTP: en ese caso llama al API real
(`/api/query`) en vez de usar los datos mock. Si el backend falla, vuelve
automáticamente a los datos mock.

## Flujo del agente

`pregunta → skill1 (intención) → skill2 (SQL) → skill3 (motor) → skill4 (Hive/Spark) → skill5 (presentación) → UI`

Hoy `skill1`, `skill2` y `skill3` están como *stub* en `server.py`; reemplaza
cada bloque marcado con la llamada real (Gemini / selección de motor) cuando esté
disponible. `skill4` y `skill5` ya son el código real.
