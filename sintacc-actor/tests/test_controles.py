"""Controles de punta a punta contra los números de Data Science (Documentación del CAPSTONE, 16/11).

Necesitan los CSV unificados del 12/11. Si no están, el test se saltea:
    RADAR_ML_CSV=ml_sintacc_unificado.csv RADAR_MAPS_CSV=maps_unificado.csv python -m pytest -q
"""

import os

import pandas as pd
import pytest

from src import eda, etl_maps, etl_ml

ML_CSV, MAPS_CSV = os.environ.get("RADAR_ML_CSV"), os.environ.get("RADAR_MAPS_CSV")
pytestmark = pytest.mark.skipif(not (ML_CSV and MAPS_CSV), reason="faltan los CSV del 12/11")


def test_controles_16_11():
    ml = etl_ml.procesar(pd.read_csv(ML_CSV, low_memory=False))
    maps, _ = etl_maps.procesar(pd.read_csv(MAPS_CSV, low_memory=False))
    assert eda.controles(ml, maps) == {
        "productos_total": 831, "productos_trabajo": 748, "productos_reservados": 83,
        "trabajo_venta_por_mayor": 91, "trabajo_peso_imputado": 85, "trabajo_outlier_precio_kg": 16,  # 19 antes de la categoría de ML (DS, 18/11)
        "locales_total": 407, "locales_trabajo": 366, "locales_reservados": 41,
        "trabajo_sin_tacc_confirmado": 10, "trabajo_sin_tacc_busqueda": 90,
    }
