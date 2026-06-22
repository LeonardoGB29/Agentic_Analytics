"""
Agente Analítico — API Server (REAL: Hive + Spark sobre el cluster EMR)

Pipeline: skill1 (intención) → skill2 (SQL) → skill3 (motor) → skill4 (ejecución
Hive/Spark) → skill5 (formato JSON para el frontend).

Se arranca con spark-submit (ver deploy.sh) para que la SparkSession use YARN y
el metastore de Hive (base tpcds_bigdata). La SparkSession se crea de forma
perezosa: solo cuando una consulta usa Spark.
"""

from flask import Flask, jsonify, request, send_from_directory
import os

try:
    from flask_cors import CORS
except ImportError:  # CORS es opcional (mismo origen al servir el frontend)
    CORS = None

try:
    from .skill1 import skill_1_identificar_intencion
    from .skill2 import skill_2_generar_sql
    from .skill3 import skill_3_seleccionar_motor
    from .skill4 import skill_4_ejecutar
    from .skill5 import skill_5_to_json
except ImportError:
    from skill1 import skill_1_identificar_intencion
    from skill2 import skill_2_generar_sql
    from skill3 import skill_3_seleccionar_motor
    from skill4 import skill_4_ejecutar
    from skill5 import skill_5_to_json

# El frontend vive en ../frontend (carpeta hermana de backend/)
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend')

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
if CORS is not None:
    CORS(app)


# ── SparkSession perezosa ─────────────────────────────────────────────────────
_spark = None


def get_spark():
    """Crea (una sola vez) la SparkSession con soporte Hive. Requiere correr
    bajo spark-submit (ver deploy.sh)."""
    global _spark
    if _spark is None:
        from pyspark.sql import SparkSession
        _spark = (
            SparkSession.builder
            .appName('AgenteAnaliticoRetail')
            .enableHiveSupport()
            .getOrCreate()
        )
    return _spark


# ── Presentación: cómo armar el meta del frontend por intención ───────────────
# Para cada intención sabemos qué columna es la etiqueta y cuál la medida
# numérica (segun el SQL de skill2). Asi heroValue/chart salen correctos.
MESES = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio',
         'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']

PRESENTACION = {
    'tienda_mayores_ventas':        {'label': 's_store_name', 'measure': 'ventas_totales',  'unit': 'ingresos',        'title': 'Tienda con mayores ventas'},
    'ventas_por_tienda':            {'label': 's_store_name', 'measure': 'ventas_totales',  'unit': 'ingresos',        'title': 'Ventas por tienda'},
    'cinco_productos_mas_vendidos': {'label': 'producto',     'measure': 'cantidad_vendida','unit': 'unidades',        'title': 'Top 5 productos más vendidos'},
    'top_productos_por_tienda':     {'label': 'producto',     'measure': 'cantidad_vendida','unit': 'unidades',        'title': 'Top productos por tienda'},
    'diez_mejores_clientes':        {'label': 'cliente',      'measure': 'gasto_total',     'unit': 'gasto',           'title': 'Diez mejores clientes'},
    'top_clientes_gasto_total':     {'label': 'cliente',      'measure': 'gasto_total',     'unit': 'gasto',           'title': 'Clientes por gasto total'},
    'top_20_clientes_compras':      {'label': 'cliente',      'measure': 'numero_compras',  'unit': 'compras',         'title': 'Top 20 clientes por compras'},
    'ticket_promedio_por_cliente':  {'label': 'cliente',      'measure': 'ticket_promedio', 'unit': 'ticket promedio', 'title': 'Ticket promedio por cliente'},
    'productos_mayor_ingreso':      {'label': 'producto',     'measure': 'ingreso_generado','unit': 'ingresos',        'title': 'Productos por ingreso'},
    'mes_mayores_ingresos':         {'label': 'mes',          'measure': 'ingresos_totales','unit': 'ingresos',        'title': 'Mes con mayores ingresos'},
    'ventas_por_mes':               {'label': 'mes',          'measure': 'ventas_totales',  'unit': 'ingresos',        'title': 'Ventas por mes'},
    'ventas_por_dia_semana':        {'label': 'dia_semana',   'measure': 'ventas_totales',  'unit': 'ingresos',        'title': 'Ventas por día de la semana'},
    'ranking_mensual_ventas':       {'label': 's_store_name', 'measure': 'ventas_totales',  'unit': 'ingresos',        'title': 'Ranking mensual de ventas'},
}


def _limpiar_cols(cols):
    """Quita el prefijo de tabla (s.s_store_name -> s_store_name)."""
    return [str(c).split('.')[-1] for c in cols]


def _cols_rows(resultado):
    """Extrae (cols, rows) de la salida de skill4, sea dict (both) o tupla."""
    if isinstance(resultado, dict) and 'hive' in resultado:
        d = resultado['hive']
        return _limpiar_cols(d['cols']), d['rows']
    cols, rows, _tiempo = resultado
    return _limpiar_cols(cols), rows


def _fmt_num(v):
    try:
        f = float(v)
        n = int(f) if f == int(f) else round(f, 2)
        return '{:,}'.format(n).replace(',', ' ')
    except (TypeError, ValueError):
        return str(v)


def _idx(cols, name, default):
    return cols.index(name) if name and name in cols else default


def construir_meta(cols, rows, intencion):
    """Genera el meta de presentación (heroValue, summary, chart, ...) a partir
    de los resultados reales de la consulta."""
    cfg = PRESENTACION.get(intencion, {})
    n = len(cols)
    measure_idx = _idx(cols, cfg.get('measure'), n - 1)
    label_idx = _idx(cols, cfg.get('label'), 0)
    unit = cfg.get('unit', '')
    title = cfg.get('title', intencion.replace('_', ' ').capitalize())
    es_mes = cfg.get('label') == 'mes'

    if not rows:
        return {'heroValue': '—', 'heroUnit': unit, 'heroLabel': title,
                'summary': 'La consulta no devolvió resultados.', 'matched': 0,
                'chartTitle': title, 'chart': []}

    def etiqueta(row):
        val = row[label_idx]
        if es_mes:
            try:
                return MESES[int(float(val))]
            except (ValueError, IndexError, TypeError):
                return 'Mes {}'.format(val)
        return str(val)

    chart = []
    for r in rows[:8]:
        try:
            valor = float(r[measure_idx])
        except (TypeError, ValueError):
            valor = 0.0
        chart.append((etiqueta(r), valor))

    top_label = etiqueta(rows[0])
    hero_val = _fmt_num(rows[0][measure_idx])
    return {
        'heroValue':  hero_val,
        'heroUnit':   unit,
        'heroLabel':  '{} — {}'.format(top_label, title.lower()),
        'summary':    '{}. «{}» encabeza con {} {}. Se analizaron {} filas.'.format(
                          title, top_label, hero_val, unit, len(rows)),
        'matched':    len(rows),
        'chartTitle': '{} · Top {}'.format(title, len(chart)),
        'chart':      chart,
    }


# ── Rutas ─────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'spark_iniciado': _spark is not None})


@app.route('/api/query', methods=['POST'])
def query():
    data = request.get_json(force=True) or {}
    question = (data.get('question') or '').strip()
    engine = (data.get('engine') or 'ambos').strip().lower()

    if not question:
        return jsonify({'error': 'empty question'}), 400

    # El frontend manda hive | spark | ambos. skill3 espera hive | spark | both.
    modo = 'both' if engine in ('ambos', 'both') else engine

    # ── skill1 → skill2 → skill3 ──
    try:
        intencion = skill_1_identificar_intencion(question)
        sql = skill_2_generar_sql(intencion)
        motor = skill_3_seleccionar_motor(intencion, modo)
    except ValueError as exc:
        return jsonify({'error': 'No pude interpretar la pregunta: {}'.format(exc)}), 422

    # ── skill4: ejecutar en Hive / Spark ──
    try:
        spark = get_spark() if motor in ('spark', 'both') else None
        resultado = skill_4_ejecutar(sql, motor, spark)
    except Exception as exc:  # noqa: BLE001 — devolvemos el error al frontend
        return jsonify({'error': 'Error ejecutando la consulta: {}'.format(exc),
                        'sql': sql, 'motor': motor}), 500

    # ── skill5: formatear para el frontend ──
    cols, rows = _cols_rows(resultado)
    meta = construir_meta(cols, rows, intencion)
    resp = skill_5_to_json(resultado=resultado, sql=sql, engine=motor, meta=meta)
    return jsonify(resp)


if __name__ == '__main__':
    # Configurable por entorno para desplegar en el cluster:
    #   APP_HOST=0.0.0.0  -> accesible desde fuera del nodo (deploy)
    #   APP_HOST=127.0.0.1 (default) -> solo local
    #   FLASK_DEBUG=1     -> reloader/debugger (solo local; nunca con Spark)
    host = os.environ.get('APP_HOST', '127.0.0.1')
    port = int(os.environ.get('APP_PORT', '5000'))
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    # threaded=False: el driver de Spark procesa una consulta a la vez.
    app.run(host=host, port=port, debug=debug, threaded=False)
