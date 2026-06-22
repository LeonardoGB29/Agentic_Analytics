# pandas y matplotlib se importan de forma perezosa dentro de skill_5_presentar:
# skill_5_to_json (lo que usa el servidor) no los necesita, y asi evitamos
# requerirlos en el driver del cluster.


# ── helpers ───────────────────────────────────────────────────────────────────

def _fmt_num(n):
    """Format a number with space thousands separator."""
    try:
        return '{:,}'.format(int(float(n))).replace(',', ' ')
    except (ValueError, TypeError):
        return str(n)


def skill_5_to_json(resultado, sql: str, engine: str, meta: dict) -> dict:
    """
    Converts the output of skill4 into the JSON contract expected by the frontend.

    resultado:
        • dict {"hive": {"cols", "rows", "tiempo"}, "spark": {...}}  → ambos motores
        • tuple (cols, rows, tiempo)                                  → motor único

    meta (provided by skill2/LLM or stub):
        heroUnit, heroLabel, summary, matched, chartTitle,
        chart: list of (label, numeric_value)
    """
    if isinstance(resultado, dict) and 'hive' in resultado:
        hive_time  = resultado['hive']['tiempo']
        spark_time = resultado['spark']['tiempo']
        cols = resultado['hive']['cols']
        rows = resultado['hive']['rows']
    else:
        cols, rows, t = resultado
        hive_time  = t if engine == 'hive'  else None
        spark_time = t if engine == 'spark' else None

    chart_raw = meta.get('chart', [])
    chart = [
        {'label': item[0], 'value': item[1], 'valueFmt': _fmt_num(item[1])}
        for item in chart_raw
    ]

    # heroValue lo decide el meta (la columna relevante varia por consulta);
    # si no viene, caemos al segundo campo de la primera fila.
    hero_raw = meta.get('heroValue')
    if hero_raw is None:
        hero_raw = rows[0][1] if rows else '—'

    return {
        'heroValue':  hero_raw,
        'heroUnit':   meta.get('heroUnit', ''),
        'heroLabel':  meta.get('heroLabel', ''),
        'summary':    meta.get('summary', ''),
        'sql':        sql,
        'hive':       hive_time,
        'spark':      spark_time,
        'matched':    meta.get('matched', len(list(rows))),
        'cols':       [str(c).split('.')[-1] for c in cols],
        'rows':       [list(r) for r in rows],
        'chartTitle': meta.get('chartTitle', ''),
        'chart':      chart,
    }


# ── original skill (unchanged) ────────────────────────────────────────────────

def skill_5_presentar(resultado):
    import pandas as pd
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    # Caso comparación (both): graficar métricas Hive vs Spark
    if isinstance(resultado, dict) and "hive" in resultado:
        met_h = resultado["hive"]["metricas"]
        met_s = resultado["spark"]["metricas"]

        metricas = ["tiempo", "cpu", "memoria"]
        # solo grafica las métricas que tienen valor en ambos motores
        disponibles = [m for m in metricas
                       if met_h.get(m) is not None and met_s.get(m) is not None]

        fig, axes = plt.subplots(1, len(disponibles), figsize=(5*len(disponibles), 4))
        if len(disponibles) == 1:
            axes = [axes]
        for ax, m in zip(axes, disponibles):
            ax.bar(["Hive", "Spark"], [met_h[m], met_s[m]],
                   color=["#F2A900", "#E25A1C"])
            ax.set_title(m.capitalize())
        plt.tight_layout()
        plt.savefig("comparacion_motores.png", dpi=120)

        # tabla de resultados (de uno cualquiera; deberían coincidir)
        df = pd.DataFrame(resultado["hive"]["rows"], columns=resultado["hive"]["cols"])
        return df

    # Caso motor único: tabla + gráfico de datos SOLO si aplica
    cols, rows, met = resultado
    df = pd.DataFrame(rows, columns=cols)
    print(df.to_string(index=False))

    # graficar datos de negocio solo si: 2 columnas y >1 fila (etiqueta + número)
    if df.shape[1] == 2 and df.shape[0] > 1:
        df.plot(x=df.columns[0], y=df.columns[1], kind="bar", legend=False)
        plt.tight_layout()
        plt.savefig("resultado.png", dpi=120)
    return df