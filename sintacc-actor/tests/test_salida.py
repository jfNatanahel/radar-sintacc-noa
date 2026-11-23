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


def test_modelo_falta_da_un_error_claro(tmp_path):
    import pytest
    from src import modelo
    with pytest.raises(FileNotFoundError, match="R2 y R3"):
        modelo.cargar("no_existe.pkl", carpeta=tmp_path)


def test_modelo_carga_un_pipeline_y_vuelve_a_pesos(tmp_path):
    """Simula el .pkl de DS: un Pipeline entrenado afuera (acá, en el test) que predice log1p."""
    import joblib
    import numpy as np
    from sklearn.compose import ColumnTransformer
    from sklearn.linear_model import LinearRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder
    from src import modelo
    df = pd.DataFrame({"peso_total_kg": [0.5, 1, 2, 5], "unidades_pack": [1, 1, 2, 5],
                       "envio_gratis": [0, 1, 1, 1], "descuento_pct": [0, 10, 0, 5],
                       "categoria": ["harina", "harina", "fideos", "fideos"]})
    y = np.log1p([1000, 2000, 4000, 10000])
    pre = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore"), ["categoria"])],
                            remainder="passthrough")
    joblib.dump(Pipeline([("pre", pre), ("m", LinearRegression())]).fit(df, y), tmp_path / "m.pkl")
    pred = modelo.predecir(modelo.cargar("m.pkl", carpeta=tmp_path), df, modelo.FEATURES_ML)
    assert pred.round(0).tolist() == [1000, 2000, 4000, 10000]
