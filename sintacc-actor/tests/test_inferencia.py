"""Tests del semáforo de compra (Producto 2, src/inferencia.py)."""

import json

import pandas as pd

from src import inferencia


def _productos() -> pd.DataFrame:
    """Harina minorista con mediana 10.000 $/kg en el 90 %, más casos borde."""
    filas = []
    for i, kg in enumerate([9_000, 9_500, 10_000, 10_500, 11_000]):  # referencia: 10.000
        filas.append(("T%d" % i, "harina", 0, "trabajo", kg, 0, 0))
    filas += [
        ("VERDE", "harina", 0, "trabajo", 7_000, 0, 0),     # -30 %
        ("ROJO", "harina", 0, "trabajo", 13_000, 0, 0),     # +30 %
        ("RES", "harina", 0, "reservado", 2_000, 0, 0),     # del 10 %: no mueve la referencia
        ("IMP", "harina", 0, "trabajo", 5_000, 1, 0),       # peso estimado
        ("OUT", "harina", 0, "trabajo", 90_000, 0, 1),      # outlier
        ("MAY", "harina", 1, "trabajo", 8_000, 0, 0),       # mayorista con grupo chico: usa la categoría
    ]
    df = pd.DataFrame(filas, columns=["idPublicacion", "categoria", "venta_por_mayor", "muestra",
                                      "precio_por_kg", "peso_imputado", "outlier_precio_kg"])
    df["articuloTitulo"] = "Harina " + df["idPublicacion"]
    df["precio"] = df["precio_por_kg"]
    return df


def test_colores_del_semaforo():
    s = inferencia.semaforo(_productos()).set_index("idPublicacion")
    assert s.loc["VERDE", "semaforo"] == "verde"
    assert s.loc["ROJO", "semaforo"] == "rojo"
    assert s.loc["T2", "semaforo"] == "amarillo"
    assert s.loc["IMP", "semaforo"] == "revisar" and "estimado" in s.loc["IMP", "motivo"]
    assert s.loc["OUT", "semaforo"] == "revisar"
    assert pd.isna(s.loc["OUT", "diferencia_pct"])


def test_referencia_solo_con_el_90_y_sin_outliers():
    s = inferencia.semaforo(_productos()).set_index("idPublicacion")
    # mediana de T0..T4, VERDE, ROJO, IMP: el reservado (2.000) y el outlier (90.000) no cuentan
    esperado = pd.Series([9_000, 9_500, 10_000, 10_500, 11_000, 7_000, 13_000, 5_000]).median()
    assert s.loc["VERDE", "referencia_kg"] == esperado
    assert s.loc["VERDE", "ahorro_por_kg"] == esperado - 7_000


def test_grupo_chico_usa_la_mediana_de_la_categoria():
    s = inferencia.semaforo(_productos()).set_index("idPublicacion")
    # mayoristas solo hay 1 (< SEMAFORO_MIN_GRUPO): referencia = mediana de toda la harina del 90 %
    categoria = pd.Series([9_000, 9_500, 10_000, 10_500, 11_000, 7_000, 13_000, 5_000, 8_000]).median()
    assert s.loc["MAY", "referencia_kg"] == categoria
    assert s.loc["MAY", "referencia_kg"] != s.loc["T0", "referencia_kg"]  # no usa la de minoristas


def test_resumen_se_puede_guardar_como_json():
    s = inferencia.semaforo(_productos())
    r = inferencia.resumen(s)
    assert r["total"]["verde"] >= 1
    json.dumps(r)  # Actor.set_value guarda JSON
