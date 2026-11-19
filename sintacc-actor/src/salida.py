"""Salida: arma lo que el Actor publica. Funciones puras (sin Apify), probadas en tests/test_salida.py."""

import io

import pandas as pd

# Tablas de indicadores que van al dataset, con la clave del RESUMEN de donde salen
TABLAS_KPI = {
    "kpi_categoria": "precio_kg_por_categoria",
    "kpi_provincia": "oferta_por_provincia",
    "kpi_demanda": "demanda_por_grupo",
}


def _filas(df: pd.DataFrame, tabla: str, fecha: str) -> list[dict]:
    df = df.astype(object).where(df.notna(), None)
    return [{"tabla": tabla, "fecha_corrida": fecha, **r} for r in df.to_dict("records")]


def filas_dataset(ml: pd.DataFrame, maps: pd.DataFrame, resumen: dict, fecha: str) -> list[dict]:
    """Una fila por registro; la columna `tabla` dice a qué tabla va (así las separa Make)."""
    filas = _filas(ml, "productos", fecha) + _filas(maps, "locales", fecha)
    for tabla, clave in TABLAS_KPI.items():
        filas += [{"tabla": tabla, "fecha_corrida": fecha, **k} for k in resumen[clave]]
    return filas


def unir_historial(anterior: bytes | str | None, resumen: dict, fecha: str) -> pd.DataFrame:
    """Suma los indicadores por categoría de esta corrida al historial.

    Si ya había una corrida con la misma fecha, se reemplaza (no se duplica).
    """
    kpis = pd.DataFrame(resumen["precio_kg_por_categoria"])
    kpis.insert(0, "fecha_corrida", fecha)
    if isinstance(anterior, bytes):
        anterior = anterior.decode("utf-8")
    if not anterior:
        return kpis
    previo = pd.read_csv(io.StringIO(anterior))
    return pd.concat([previo[previo["fecha_corrida"] != fecha], kpis], ignore_index=True)
