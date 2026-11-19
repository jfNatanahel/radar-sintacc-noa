"""Tests de lo que publica el Actor (src/salida.py) y de la lectura de CSV del store (src/extraer.py)."""

import pandas as pd
import pytest

from src.extraer import csv_a_tabla
from src.salida import filas_dataset, unir_historial

RESUMEN = {
    "precio_kg_por_categoria": [{"categoria": "fideos", "minorista_kg": 21750, "mayorista_kg": 12500}],
    "oferta_por_provincia": [{"provincia": "Salta", "locales": 59}],
    "demanda_por_grupo": [{"grupo": "confirmado", "mediana_resenas": 10}],
}


def test_filas_dataset_marca_tabla_y_fecha():
    ml = pd.DataFrame({"idPublicacion": ["MLA1"], "precio": [100.0]})
    maps = pd.DataFrame({"placeId": ["p1"], "resenas": [None]})
    filas = filas_dataset(ml, maps, RESUMEN, "2026-11-19")
    assert [f["tabla"] for f in filas] == ["productos", "locales", "kpi_categoria", "kpi_provincia", "kpi_demanda"]
    assert all(f["fecha_corrida"] == "2026-11-19" for f in filas)
    assert filas[1]["resenas"] is None  # los vacíos salen como null, no como NaN


def test_historial_suma_corridas_y_no_duplica_la_fecha():
    primera = unir_historial(None, RESUMEN, "2026-11-17")
    assert len(primera) == 1
    segunda = unir_historial(primera.to_csv(index=False).encode(), RESUMEN, "2026-11-19")
    assert list(segunda["fecha_corrida"]) == ["2026-11-17", "2026-11-19"]
    repetida = unir_historial(segunda.to_csv(index=False), RESUMEN, "2026-11-19")
    assert len(repetida) == 2


def test_csv_del_store():
    assert csv_a_tabla(b"a,b\n1,2\n", "x").shape == (1, 2)
    assert csv_a_tabla("a,b\n1,2\n", "x").shape == (1, 2)
    with pytest.raises(ValueError, match="subir_csv_a_apify"):
        csv_a_tabla(None, "ml_unificado.csv")
