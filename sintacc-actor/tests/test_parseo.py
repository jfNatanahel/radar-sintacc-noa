"""Tests del parseo de títulos. Todos los casos son títulos reales del dataset (12/11/2026).

Correr con:  python -m pytest -q
"""

import pytest

from src.parseo import peso_unidad_kg, unidades_pack

PESOS = [
    ("Premezcla Para Ñoquis Delicel Sin Tacc 500g", 0.5),
    ("Premezcla Panificados Glutal 25 Kgs. Sin Tacc Sin Gluten", 25.0),   # antes daba 0.5
    ("Premezcla Panificados 5 Kgs. Sin Tacc Glutal", 5.0),
    ("Premezcla Universal Dimax X 1 Kilo", 1.0),
    ("Almidon de Maiz Mayana x 1 kg", 1.0),
    ("Harina Almendra Top Class X 300 Grs", 0.3),
    ("Harina Premezcla Celiaco Dicomere X450g - Pack", 0.45),
    ("Pack 6 X 1 Kgr Harina De Arroz Glutal Sin Tacc", 1.0),
    ("Harina De Arroz Integral Organico 1,5 kg", 1.5),
    ("Fideos Spaghetti Libre De Gluten Matarazzo X500g", 0.5),
    ("Pack 5 Harina De Maní - Natural Pop - Sin Tacc", None),
]

PACKS = [
    ("Premezcla Universal Delicel Libre De Gluten 500g Pack X12", 12),
    ("Rebozador Sin Tacc Gluten Bajo Sodio Doña Pacha 500gr X 20", 20),   # antes daba 1
    ("Pack X 5 Rebozador De Arroz Natuzen X 240grs", 5),
    ("Pack 6 X 1 Kgr Harina De Arroz Glutal Sin Tacc", 6),
    ("Pack 12u Fideos De Arroz Finos Sin Tacc 200 Gr", 12),
    ("Dicomere - Pack X 3u Rebozador De Arroz Sin Tacc", 3),
    ("Harina De Arroz Dicomere 3 Unidades", 3),
    ("Rebozador Molto 1 Kilo X 5 Unidades", 5),
    ("Harina De Arroz Dimax 1kg Oferta X6 Unidades!!", 6),
    ("Fecula De Mandioca X 1kg 5 Unid | Sin Tacc", 5),
    ("Delicel Premezcla Ñoquis Sin Tacc Gluten Free 500gr X12u", 12),
    ("Premezcla De Pan Natuzen Sin Tacc 450gr X1u", 1),
    ("Premezcla Universal Dimax X 1 Kilo", 1),
    ("Almidon de Maiz Mayana x 1 kg", 1),
    ("Harina Almendra Top Class X 300 Grs", 1),
    ("Fideos Spaghetti Libre De Gluten Matarazzo X500g", 1),
    ("Pack X 5 Rebozador De Arroz Natuzen X 240grs", 5),
]


@pytest.mark.parametrize("titulo,esperado", PESOS)
def test_peso(titulo, esperado):
    assert peso_unidad_kg(titulo) == pytest.approx(esperado) if esperado else peso_unidad_kg(titulo) is None


@pytest.mark.parametrize("titulo,esperado", PACKS)
def test_pack(titulo, esperado):
    assert unidades_pack(titulo) == esperado
