"""
Agente Analítico — API Server
Pipeline: skill1 (intent) → skill2 (SQL) → skill3 (engine) → skill4 (exec) → skill5 (present)

Skills 1-4 are stubbed below.  Replace each STUB block with the real call when
Hive / Spark / Gemini are available.  Skill 5 (skill_5_to_json) is already
wired and formats every response for the frontend.
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os

from skill5 import skill_5_to_json

# El frontend vive en ../frontend (carpeta hermana de backend/)
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend')

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
CORS(app)

# ── Stub catalogue (mirrors the original frontend RESPONSES) ──────────────────
# Keys match the intent labels returned by _infer_intent().
_STUBS = {
    'productos': {
        'sql': (
            "SELECT i.i_item_desc, SUM(ss.ss_quantity) AS unidades\n"
            "FROM store_sales ss\n"
            "JOIN item i ON ss.ss_item_sk = i.i_item_sk\n"
            "GROUP BY i.i_item_desc\n"
            "ORDER BY unidades DESC\n"
            "LIMIT 10"
        ),
        'hive_time': 24.8, 'spark_time': 6.3,
        'matched': 17920,
        'cols': ['producto', 'unidades'],
        'rows': [
            ['Producto A', '18 420'], ['Producto B', '15 310'],
            ['Producto C', '14 002'], ['Producto D', '11 890'],
            ['Producto E', '9 740'],  ['Producto F', '8 905'],
            ['Producto G', '7 612'],  ['Producto H', '6 480'],
            ['Producto I', '5 933'],  ['Producto J', '5 110'],
        ],
        'heroUnit':   'unidades',
        'heroLabel':  'Producto A — el más vendido del catálogo',
        'summary': (
            'El catálogo está muy concentrado: el Top 3 acumula casi el 45 % de las '
            'unidades. «Producto A» lidera con 18 420 unidades, un 20 % por encima del '
            'segundo. Conviene asegurar su disponibilidad de stock.'
        ),
        'chartTitle': 'Unidades vendidas · Top 8',
        'chart': [
            ('Producto A', 18420), ('Producto B', 15310),
            ('Producto C', 14002), ('Producto D', 11890),
            ('Producto E', 9740),  ('Producto F', 8905),
            ('Producto G', 7612),  ('Producto H', 6480),
        ],
    },

    'tienda': {
        'sql': (
            "SELECT s.s_store_name, SUM(ss.ss_net_paid) AS ingresos\n"
            "FROM store_sales ss\n"
            "JOIN store s ON ss.ss_store_sk = s.s_store_sk\n"
            "GROUP BY s.s_store_name\n"
            "ORDER BY ingresos DESC\n"
            "LIMIT 10"
        ),
        'hive_time': 31.2, 'spark_time': 7.9,
        'matched': 102,
        'cols': ['tienda', 'ingresos'],
        'rows': [
            ['Tienda Eastgate', '$2,84 M'], ['Tienda Lakeview',  '$2,51 M'],
            ['Tienda Northpark','$2,18 M'], ['Tienda Riverside',  '$1,97 M'],
            ['Tienda Summit',   '$1,64 M'], ['Tienda Brookside',  '$1,52 M'],
            ['Tienda Fairview', '$1,41 M'], ['Tienda Glenwood',   '$1,28 M'],
            ['Tienda Highgate', '$1,12 M'], ['Tienda Westend',    '$0,98 M'],
        ],
        'heroUnit':   'ingresos',
        'heroLabel':  'Tienda Eastgate — la #1 de la red',
        'summary': (
            'Las ventas están repartidas entre tiendas urbanas. «Eastgate» encabeza con '
            '$2,84 M, pero la diferencia con la quinta es de apenas 1,7×: una red '
            'equilibrada sin un único punto crítico.'
        ),
        'chartTitle': 'Ingresos por tienda · Top 8',
        'chart': [
            ('Eastgate',  2.84), ('Lakeview',  2.51),
            ('Northpark', 2.18), ('Riverside', 1.97),
            ('Summit',    1.64), ('Brookside', 1.52),
            ('Fairview',  1.41), ('Glenwood',  1.28),
        ],
    },

    'mes': {
        'sql': (
            "SELECT d.d_moy AS mes, SUM(ss.ss_net_paid) AS ingresos\n"
            "FROM store_sales ss\n"
            "JOIN date_dim d ON ss.ss_sold_date_sk = d.d_date_sk\n"
            "GROUP BY d.d_moy\n"
            "ORDER BY ingresos DESC"
        ),
        'hive_time': 19.5, 'spark_time': 5.1,
        'matched': 12,
        'cols': ['mes', 'ingresos'],
        'rows': [
            ['Diciembre',   '$4,12 M'], ['Noviembre',  '$3,68 M'],
            ['Julio',       '$2,94 M'], ['Agosto',     '$2,71 M'],
            ['Marzo',       '$2,40 M'], ['Octubre',    '$2,22 M'],
            ['Mayo',        '$2,05 M'], ['Junio',      '$1,98 M'],
            ['Abril',       '$1,86 M'], ['Septiembre', '$1,74 M'],
            ['Enero',       '$1,52 M'], ['Febrero',    '$1,38 M'],
        ],
        'heroUnit':   'ingresos',
        'heroLabel':  'Diciembre — mes pico del año',
        'summary': (
            'La estacionalidad es marcada: Diciembre concentra el pico de ingresos '
            '($4,12 M), un 12 % sobre Noviembre. El segundo semestre supera con claridad '
            'al primero: clave para planear inventario.'
        ),
        'chartTitle': 'Ingresos por mes · Top 8',
        'chart': [
            ('Diciembre', 4.12), ('Noviembre', 3.68),
            ('Julio',     2.94), ('Agosto',    2.71),
            ('Marzo',     2.40), ('Octubre',   2.22),
            ('Mayo',      2.05), ('Junio',     1.98),
        ],
    },

    'clientes': {
        'sql': (
            "SELECT c.c_first_name, c.c_last_name, SUM(ss.ss_net_paid) AS gasto\n"
            "FROM store_sales ss\n"
            "JOIN customer c ON ss.ss_customer_sk = c.c_customer_sk\n"
            "GROUP BY c.c_first_name, c.c_last_name\n"
            "ORDER BY gasto DESC\n"
            "LIMIT 10"
        ),
        'hive_time': 28.7, 'spark_time': 8.4,
        'matched': 24580,
        'cols': ['cliente', 'gasto'],
        'rows': [
            ['Claudia Martínez', '$48 920'], ['Diego Fuentes',   '$44 105'],
            ['Renata Ospina',    '$41 780'], ['Mateo Carvajal',  '$39 240'],
            ['Lucía Bermúdez',   '$36 510'], ['Andrés Pineda',   '$34 880'],
            ['Sofía Quintero',   '$32 145'], ['Tomás Vargas',    '$30 770'],
            ['Valentina Ríos',   '$28 990'], ['Camilo Herrera',  '$27 305'],
        ],
        'heroUnit':   'en compras',
        'heroLabel':  'Claudia Martínez — cliente top',
        'summary': (
            'La base de clientes tiene una cola larga: el mejor cliente gastó $48 920, '
            'pero ninguno supera el 0,3 % del total. No hay dependencia de cuentas '
            'individuales, lo que reduce el riesgo de concentración.'
        ),
        'chartTitle': 'Gasto por cliente · Top 8',
        'chart': [
            ('C. Martínez', 48920), ('D. Fuentes', 44105),
            ('R. Ospina',   41780), ('M. Carvajal',39240),
            ('L. Bermúdez', 36510), ('A. Pineda',  34880),
            ('S. Quintero', 32145), ('T. Vargas',  30770),
        ],
    },
}


# ── Skill 1 stub: intent detection ────────────────────────────────────────────
def _skill1_intent(question: str) -> str:
    """
    STUB — replace with a real Gemini call to classify intent:
        intent = skill_1_identificar_intencion(question)
    """
    t = question.lower()
    if 'cliente' in t:                      return 'clientes'
    if 'tienda' in t:                       return 'tienda'
    if 'mes' in t or 'mensual' in t:        return 'mes'
    if 'ingreso' in t:                      return 'mes'
    return 'productos'


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'engines': {'hive': True, 'spark': True}})


@app.route('/api/query', methods=['POST'])
def query():
    data     = request.get_json(force=True) or {}
    question = data.get('question', '').strip()
    engine   = data.get('engine', 'ambos')

    if not question:
        return jsonify({'error': 'empty question'}), 400

    # ── Skill 1: identify intent ───────────────────────────────────────────────
    intent = _skill1_intent(question)

    # ── Skill 2: generate SQL (STUB — replace with Gemini) ────────────────────
    # sql = skill_2_generar_sql(intent, schema=TPC_DS_SCHEMA, llm=gemini_client)
    stub = _STUBS[intent]
    sql  = stub['sql']

    # ── Skill 3: select engine (STUB) ─────────────────────────────────────────
    # motor = skill_3_seleccionar(question, preferred=engine)
    motor = engine

    # ── Skill 4: execute query (STUB — replace with real Hive/Spark) ──────────
    # from skill4 import skill_4_ejecutar
    # resultado = skill_4_ejecutar(sql, motor, spark_session)
    resultado = {
        'hive':  {'cols': stub['cols'], 'rows': stub['rows'], 'tiempo': stub['hive_time']},
        'spark': {'cols': stub['cols'], 'rows': stub['rows'], 'tiempo': stub['spark_time']},
    }

    # ── Skill 5: format for frontend ──────────────────────────────────────────
    resp = skill_5_to_json(
        resultado=resultado,
        sql=sql,
        engine=motor,
        meta={
            'heroUnit':   stub['heroUnit'],
            'heroLabel':  stub['heroLabel'],
            'summary':    stub['summary'],
            'matched':    stub['matched'],
            'chartTitle': stub['chartTitle'],
            'chart':      stub['chart'],
        },
    )
    return jsonify(resp)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
