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
    # Reglas finales del 16/11
    ("Premezcla Verde Santa María 15 Unidades X1k C/u Sin Tacc", 1.0),          # "k" = kilo
    ("Harina De Arroz Dicomere X 1 K Pack X 6 Unidades Sin Tacc", 1.0),
    ("Premezcla Libre De Gluten 15 Kgs. Glutal 3x5 Kg. Panificados", 5.0),     # "N x peso": peso de la unidad
    ("Harina De Avena Cumana Libre De Gluten Sin Tacc 10 X 400 G", 0.4),
    ("2x Rebozador De Arroz Integral Con Sal All Rice 250gc/u - Fw", 0.25),    # "c/u" pegado al peso
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
    # Reglas finales del 16/11
    ("Premezcla Celíacos Especial Panificados Glutal 3 X 5 Kgs.", 3),
    ("Harina De Avena Cumana Libre De Gluten Sin Tacc 10 X 400 G", 10),
    ("2x Harina De Arroz Integral Organico Dicomere S/tacc 450g Fw", 2),
    ("3 X Rebozador De Arroz Natuzen Sin Tacc (240gr C/u) - Dw", 3),
    ("Premezcla Universal  Sin Tacc Delicel X500grs Caja X12unid", 12),
    ("Premezcla Santa María Deslactosada Sin Tacc 1kg ( X3 Unid )", 3),
    ("Fideos Arroz Coditos Blue Patna 500g Sin Tacc Huevo 6 Unidad", 6),
    ("Fideos De Arroz Pamperitos Blue Patna 500gr Sin Tacc 6 Unida Otra Razón", 6),
    ("Panko Sin Tacc Naccato - Rebozador Sin Tacc 12 Und X 300 Gr", 12),
    ("Premezcla Universal N°3 Delicel X500gr X1u", 1),                    # "N°3" no es pack
    ("Fideos Nº 5 Spaghetti 3 x 500g", 3),
]


@pytest.mark.parametrize("titulo,esperado", PESOS)
def test_peso(titulo, esperado):
    assert peso_unidad_kg(titulo) == pytest.approx(esperado) if esperado else peso_unidad_kg(titulo) is None


@pytest.mark.parametrize("titulo,esperado", PACKS)
def test_pack(titulo, esperado):
    assert unidades_pack(titulo) == esperado
