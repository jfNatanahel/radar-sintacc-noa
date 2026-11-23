"""Tests de la validación contra el listado de ANMAT (src/anmat.py)."""

import pandas as pd

from src import anmat

LISTADO = pd.DataFrame({
    "marca": ["Dicomere", "Dicomere", "Glutal", "Natural Pop"],
    "producto": ["Harina de arroz", "Rebozador de arroz", "Premezcla para panificados", "Harina de arveja"],
})
PRODUCTOS = pd.DataFrame({
    "idPublicacion": ["A", "B", "C", "D", "E"],
    "articuloTitulo": [
        "Harina De Arroz Dicomere 1kg Sin Tacc Pack X 2 Unidades",   # marca + producto
        "Premezcla Panificados 5 Kgs. Sin Tacc Glutal",               # marca + producto
        "Glutal Fideos tirabuzón sin tacc 500 g",                      # marca sí, producto no
        "Fideos Matarazzo Sin Tacc 500g",                              # marca fuera del listado
        "Harina de arveja Natural Pop Sin TACC, 450 g",                # marca de dos palabras
    ],
})


def test_tres_niveles():
    r = anmat.validar(PRODUCTOS, anmat.preparar_listado(LISTADO)).set_index("idPublicacion")
    assert r.loc["A", "anmat"] == anmat.VALIDADO and r.loc["A", "anmat_marca"] == "dicomere"
    assert r.loc["B", "anmat"] == anmat.VALIDADO
    assert r.loc["C", "anmat"] == anmat.MARCA
    assert r.loc["D", "anmat"] == anmat.NO_ENCONTRADO
    assert r.loc["E", "anmat"] == anmat.VALIDADO and r.loc["E", "anmat_marca"] == "natural pop"


def test_sin_listado_no_rompe():
    r = anmat.validar(PRODUCTOS, None)
    assert (r["anmat"] == anmat.SIN_LISTADO).all()


def test_normalizar_saca_tildes_y_signos():
    assert anmat.normalizar("Fécula de Mandioca | SIN T.A.C.C.") == "fecula de mandioca sin t a c c"


def test_tolera_tipeos_y_marca_mas_larga():
    """'Harina de aroz' (con tipeo) valida; si dos marcas aparecen, gana la más larga."""
    listado = anmat.preparar_listado(pd.DataFrame({
        "marca": ["Natural", "Natural Pop"], "producto": ["Harina de arroz", "Harina de arroz"]}))
    prods = pd.DataFrame({"idPublicacion": ["X"], "articuloTitulo": ["Harina de aroz Natural Pop 500 g"]})
    r = anmat.validar(prods, listado).iloc[0]
    assert r["anmat"] == anmat.VALIDADO and r["anmat_marca"] == "natural pop"
