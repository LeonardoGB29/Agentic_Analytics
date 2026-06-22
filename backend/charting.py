from __future__ import annotations

from typing import Any


LABEL_HINTS = (
    "producto",
    "cliente",
    "store_name",
    "tienda",
    "dia_semana",
    "mes",
    "i_item_id",
    "s_store_id",
    "c_customer_id",
)
METRIC_HINTS = (
    "ventas_totales",
    "ingresos_totales",
    "ingreso_generado",
    "gasto_total",
    "ticket_promedio",
    "cantidad_vendida",
    "numero_compras",
)


def extraer_resultado_base(resultado) -> tuple[list[str], list[tuple]]:
    """
    Toma la salida de Skill 4 y devuelve columnas/filas para graficar.

    Si se ejecutaron ambos motores, usamos Spark como referencia visual porque
    suele ser el motor elegido para consultas pesadas. Hive queda disponible en
    tiempos de ejecucion.
    """
    if isinstance(resultado, dict):
        if "spark" in resultado:
            return resultado["spark"]["cols"], resultado["spark"]["rows"]
        if "hive" in resultado:
            return resultado["hive"]["cols"], resultado["hive"]["rows"]

    cols, rows, _tiempo = resultado
    return cols, rows


def construir_meta_graficos(cols: list[str], rows: list[Any]) -> dict:
    rows_list = [_row_to_list(row) for row in rows]
    if not rows_list:
        return {
            "heroValue": "-",
            "heroUnit": "",
            "heroLabel": "Sin resultados",
            "summary": "La consulta se ejecuto correctamente, pero no devolvio filas.",
            "matched": 0,
            "chartTitle": "Sin datos para graficar",
            "chart": [],
            "displayCols": [],
            "displayRows": [],
        }

    metric_idx = _encontrar_columna_metrica(cols, rows_list)
    label_idx = _encontrar_columna_etiqueta(cols, metric_idx)

    if metric_idx is None:
        return {
            "heroValue": str(rows_list[0][0]),
            "heroUnit": "",
            "heroLabel": "Resultado textual",
            "summary": f"La consulta devolvio {len(rows_list)} filas, pero no se detecto una metrica numerica para graficar.",
            "matched": len(rows_list),
            "chartTitle": "Resultados",
            "chart": [],
            "displayCols": cols[:2],
            "displayRows": [row[:2] for row in rows_list],
        }

    label_idx = 0 if label_idx is None else label_idx
    metric_name = cols[metric_idx]
    label_name = cols[label_idx]

    display_rows = [
        [_formatear_etiqueta(row[label_idx], label_name), _formatear_numero(row[metric_idx])]
        for row in rows_list
    ]
    chart = [
        (_formatear_etiqueta(row[label_idx], label_name), _to_number(row[metric_idx]))
        for row in rows_list[:8]
    ]

    readable_metric = _nombre_legible(metric_name)
    readable_label = _nombre_legible(label_name)
    top_label = display_rows[0][0]
    top_value = display_rows[0][1]

    return {
        "heroValue": top_value,
        "heroUnit": readable_metric,
        "heroLabel": f"{top_label} - valor principal",
        "summary": (
            f"La consulta devolvio {len(rows_list)} filas. "
            f"El valor principal corresponde a {top_label}, con {top_value} en {readable_metric}."
        ),
        "matched": len(rows_list),
        "chartTitle": f"{readable_metric} por {readable_label}",
        "chart": chart,
        "displayCols": [readable_label, readable_metric],
        "displayRows": display_rows,
    }


def _row_to_list(row: Any) -> list[Any]:
    if isinstance(row, dict):
        return list(row.values())
    if hasattr(row, "asDict"):
        return list(row.asDict().values())
    return list(row)


def _encontrar_columna_metrica(cols: list[str], rows: list[list[Any]]) -> int | None:
    for hint in METRIC_HINTS:
        for idx, col in enumerate(cols):
            if hint == col or hint in col:
                if _columna_es_numerica(rows, idx):
                    return idx

    for idx in range(len(cols) - 1, -1, -1):
        if _columna_es_numerica(rows, idx):
            return idx
    return None


def _encontrar_columna_etiqueta(cols: list[str], metric_idx: int | None) -> int | None:
    for hint in LABEL_HINTS:
        for idx, col in enumerate(cols):
            if idx != metric_idx and (hint == col or hint in col):
                return idx

    for idx, _col in enumerate(cols):
        if idx != metric_idx:
            return idx
    return None


def _columna_es_numerica(rows: list[list[Any]], idx: int) -> bool:
    muestras = rows[: min(10, len(rows))]
    if not muestras:
        return False
    return sum(_es_numero(row[idx]) for row in muestras) >= max(1, len(muestras) // 2)


def _es_numero(value: Any) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def _to_number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _formatear_numero(value: Any) -> str:
    number = _to_number(value)
    if abs(number - int(number)) < 0.005:
        return f"{int(number):,}".replace(",", " ")
    return f"{number:,.2f}".replace(",", " ")


def _formatear_etiqueta(value: Any, col_name: str) -> str:
    if col_name == "mes":
        meses = {
            1: "Enero",
            2: "Febrero",
            3: "Marzo",
            4: "Abril",
            5: "Mayo",
            6: "Junio",
            7: "Julio",
            8: "Agosto",
            9: "Septiembre",
            10: "Octubre",
            11: "Noviembre",
            12: "Diciembre",
        }
        try:
            return meses.get(int(value), str(value))
        except (TypeError, ValueError):
            return str(value)
    return str(value)


def _nombre_legible(col_name: str) -> str:
    nombres = {
        "s_store_name": "tienda",
        "s_store_id": "tienda",
        "i_item_id": "producto",
        "producto": "producto",
        "cliente": "cliente",
        "d_day_name": "dia",
        "dia_semana": "dia",
        "mes": "mes",
        "ventas_totales": "ventas totales",
        "ingresos_totales": "ingresos totales",
        "ingreso_generado": "ingreso generado",
        "gasto_total": "gasto total",
        "ticket_promedio": "ticket promedio",
        "cantidad_vendida": "cantidad vendida",
        "numero_compras": "numero de compras",
    }
    return nombres.get(col_name, col_name.replace("_", " "))
