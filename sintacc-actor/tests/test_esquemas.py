"""Los esquemas del Actor (.actor/) son JSON válidos y nombran columnas que el código realmente produce."""

import json
import re
from pathlib import Path

ACTOR = Path(__file__).resolve().parents[1] / ".actor"
SRC = Path(__file__).resolve().parents[1] / "src"


def _json(nombre: str) -> dict:
    return json.loads((ACTOR / nombre).read_text(encoding="utf-8"))


def test_actor_json_apunta_a_los_esquemas():
    actor = _json("actor.json")
    for ruta in [actor["input"], actor["output"], actor["storages"]["dataset"]]:
        assert (ACTOR / ruta).exists(), ruta


def test_vistas_del_output_existen_en_el_dataset_schema():
    vistas = set(_json("dataset_schema.json")["views"])
    for prop in _json("output_schema.json")["properties"].values():
        m = re.search(r"view=(\w+)", prop["template"])
        if m:
            assert m.group(1) in vistas


def test_columnas_de_las_vistas_las_produce_el_codigo():
    codigo = " ".join(p.read_text(encoding="utf-8") for p in SRC.glob("*.py"))
    for nombre, vista in _json("dataset_schema.json")["views"].items():
        for campo in vista["transformation"]["fields"]:
            # aparece en el código como texto ("campo") o como clave de agg (campo=)
            assert f'"{campo}"' in codigo or f"{campo}=" in codigo, f"{nombre}: {campo}"
