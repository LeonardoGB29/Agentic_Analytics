# ── helpers ───────────────────────────────────────────────────────────────────

def _fmt_num(n):
    """Format a number with space thousands separator."""
    try:
        number = float(n)
    except (ValueError, TypeError):
        return str(n)
    if abs(number - int(number)) < 0.005:
        return '{:,}'.format(int(number)).replace(',', ' ')
    return f"{number:,.2f}".replace(",", " ")


def skill_5_to_json(resultado, sql: str, engine: str, meta: dict) -> dict:
    """
    Converts the output of skill4 into the JSON contract expected by the frontend.

    resultado:
        • dict {"hive": {"cols", "rows", "tiempo", "cpu", "mem"},
                "spark": {...}}                                     → ambos motores
        • dict {"cols", "rows", "tiempo", "cpu", "mem"}              → motor único

    meta (provided by skill2/LLM or stub):
        heroUnit, heroLabel, summary, matched, chartTitle,
        chart: list of (label, numeric_value)
    """
    if isinstance(resultado, dict) and 'hive' in resultado and 'spark' in resultado:
        hive_time  = resultado['hive']['tiempo']
        spark_time = resultado['spark']['tiempo']
        hive_cpu   = resultado['hive'].get('cpu')
        hive_mem   = resultado['hive'].get('mem')
        spark_cpu  = resultado['spark'].get('cpu')
        spark_mem  = resultado['spark'].get('mem')
        cols = resultado['hive']['cols']
        rows = resultado['hive']['rows']
    elif isinstance(resultado, dict) and 'cols' in resultado:
        cols = resultado['cols']
        rows = resultado['rows']
        t = resultado['tiempo']
        hive_time  = t if engine == 'hive'  else None
        spark_time = t if engine == 'spark' else None
        hive_cpu   = resultado.get('cpu') if engine == 'hive'  else None
        hive_mem   = resultado.get('mem') if engine == 'hive'  else None
        spark_cpu  = resultado.get('cpu') if engine == 'spark' else None
        spark_mem  = resultado.get('mem') if engine == 'spark' else None
    else:
        # Legacy tuple fallback (cols, rows, tiempo)
        cols, rows, t = resultado
        hive_time  = t if engine == 'hive'  else None
        spark_time = t if engine == 'spark' else None
        hive_cpu = hive_mem = spark_cpu = spark_mem = None

    chart_raw = meta.get('chart', [])
    chart = [
        {'label': item[0], 'value': item[1], 'valueFmt': _fmt_num(item[1])}
        for item in chart_raw
    ]

    display_cols = meta.get('displayCols') or list(cols)
    display_rows = meta.get('displayRows') or [list(r) for r in rows]
    hero_raw = meta.get('heroValue') or (display_rows[0][1] if display_rows and len(display_rows[0]) > 1 else '—')

    return {
        'heroValue':  hero_raw,
        'heroUnit':   meta.get('heroUnit', ''),
        'heroLabel':  meta.get('heroLabel', ''),
        'summary':    meta.get('summary', ''),
        'sql':        sql,
        'hive':       hive_time,
        'spark':      spark_time,
        'hive_cpu':   round(hive_cpu, 1) if hive_cpu is not None else None,
        'hive_mem':   round(hive_mem, 1) if hive_mem is not None else None,
        'spark_cpu':  round(spark_cpu, 1) if spark_cpu is not None else None,
        'spark_mem':  round(spark_mem, 1) if spark_mem is not None else None,
        'matched':    meta.get('matched', len(list(rows))),
        'cols':       list(display_cols),
        'rows':       [list(r) for r in display_rows],
        'chartTitle': meta.get('chartTitle', ''),
        'chart':      chart,
    }


# ── original skill (unchanged) ────────────────────────────────────────────────

def skill_5_presentar(resultado):
    import matplotlib.pyplot as plt
    import pandas as pd

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
