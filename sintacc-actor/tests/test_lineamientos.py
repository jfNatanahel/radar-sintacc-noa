"""Controla los lineamientos del Actor (R1 a R4) leyendo el código fuente.

Si alguien vuelve a meter una descarga, un entrenamiento o lógica en main.py, el test falla.
"""

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
PROHIBIDOS_R1 = {"urllib", "requests", "httpx", "aiohttp", "urllib3"}


def _arbol(archivo: Path) -> ast.Module:
    return ast.parse(archivo.read_text(encoding="utf-8"))


def _modulos_importados(arbol: ast.Module) -> set[str]:
    nombres = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            nombres |= {a.name.split(".")[0] for a in nodo.names}
        elif isinstance(nodo, ast.ImportFrom) and nodo.module and nodo.level == 0:
            nombres.add(nodo.module.split(".")[0])
    return nombres


def _llamadas(arbol: ast.Module) -> set[str]:
    nombres = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Call):
            f = nodo.func
            nombres.add(f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", ""))
    return nombres


def test_r1_sin_descargas_ni_open():
    for archivo in SRC.glob("*.py"):
        arbol = _arbol(archivo)
        assert not (_modulos_importados(arbol) & PROHIBIDOS_R1), f"{archivo.name} importa una librería de red"
        assert "open" not in _llamadas(arbol), f"{archivo.name} abre archivos con open()"


def test_r2_no_entrena():
    for archivo in SRC.glob("*.py"):
        assert not ({"fit", "fit_transform", "partial_fit"} & _llamadas(_arbol(archivo))), \
            f"{archivo.name} entrena un modelo dentro del Actor"


def test_r4_main_solo_arma_el_actor():
    arbol = _arbol(SRC / "main.py")
    funciones = {n.name for n in arbol.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    assert funciones <= {"main", "analytics", "inference"}, f"main.py tiene lógica: {funciones}"
    assert "pandas" not in _modulos_importados(arbol), "main.py no debería transformar datos"
