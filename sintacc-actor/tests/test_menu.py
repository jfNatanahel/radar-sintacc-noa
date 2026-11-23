"""Tests del costeador de menú (src/menu.py)."""

import json

import pandas as pd

from src import menu

INSIGHTS = pd.DataFrame([
    # categoria, venta_por_mayor, semaforo, precio_por_kg, precio
    ("A1", "Fideos A", "fideos", 0, "amarillo", 20_000, 10_000),
    ("A2", "Fideos B", "fideos", 0, "amarillo", 22_000, 11_000),
    ("V1", "Fideos verde", "fideos", 0, "verde", 8_000, 4_000),
    ("V2", "Fideos verde caro", "fideos", 0, "verde", 9_000, 4_500),
    ("R1", "Fideos sin peso", "fideos", 0, "revisar", 1_000, 500),     # no cuenta para el típico
    ("M1", "Fideos pack", "fideos", 1, "amarillo", 12_000, 60_000),    # mayorista: no es el típico
], columns=["idPublicacion", "articuloTitulo", "categoria", "venta_por_mayor", "semaforo",
            "precio_por_kg", "precio"])

RECETA = [{"plato": "Fideos con salsa", "insumo": "fideos", "kg_porcion": 0.1, "porciones_mes": 30}]


def test_costeo_compara_tipico_contra_la_mejor_oportunidad():
    m = menu.costeo(INSIGHTS, RECETA).iloc[0]
    assert m["precio_kg_tipico"] == 14_500            # mediana minorista (verdes incluidos), sin "revisar" ni mayoristas
    assert m["costo_porcion_tipico"] == 1_450
    assert m["idPublicacion"] == "V1"                  # el verde más barato por kg
    assert m["costo_porcion_radar"] == 800
    assert m["ahorro_porcion"] == 650 and m["ahorro_mes"] == 19_500


def test_sin_oportunidad_se_cuenta_al_precio_tipico():
    filas = INSIGHTS.copy()
    filas["semaforo"] = filas["semaforo"].replace("verde", "amarillo")   # ningún verde
    m = menu.costeo(filas, RECETA).iloc[0]
    assert m["costo_porcion_radar"] == m["costo_porcion_tipico"] and m["ahorro_mes"] == 0
    assert menu.resumen(menu.costeo(filas, RECETA))["ahorro_mes"] == 0


def test_resumen_mensual_es_json():
    r = menu.resumen(menu.costeo(INSIGHTS, RECETA))
    assert r["ahorro_mes"] == 19_500 and r["ahorro_pct"] == 44.8
    json.dumps(r)


def test_filtro_por_titulo_en_la_receta():
    receta = [{"plato": "Fideos con salsa", "insumo": "fideos", "kg_porcion": 0.1, "porciones_mes": 30,
               "titulo": "caro"}]
    m = menu.costeo(INSIGHTS, receta).iloc[0]
    assert m["idPublicacion"] == "V2"                  # el único verde que dice "caro" en el título
