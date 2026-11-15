"""Lectura de peso y unidades desde el título de Mercado Libre.

Mercado Libre no trae el peso ni el pack como columna: hay que sacarlos del título.
Son reglas (regex) porque el formato es corto y cerrado. Cada caso raro que
aparece se agrega primero como test en tests/test_parseo.py.
"""

import re
import unicodedata

UNIDAD_PESO = r"(?:kilogramos?|kilos?|kgr?s?|gramos?|grs?|g)"

_PESO = re.compile(rf"(\d+(?:[.,]\d+)?)\s*({UNIDAD_PESO})(?![a-z])")

# Patrones de pack, en orden de prioridad. Todos capturan la cantidad.
_PACKS = [
    # "pack x 12", "pack 6", "pack de 3"
    re.compile(r"pack\s*(?:de\s*)?(?:x\s*)?(\d{1,2})(?!\d)(?!\s*" + UNIDAD_PESO + r"(?![a-z]))"),
    # "12 unidades", "3u", "x6 unidades", "15 paquetes"
    re.compile(r"(\d{1,2})\s*(?:u|un|uni|unid|unidades|paquetes|paq|bolsas|packs?)(?![a-z])"),
    # "500gr x 20", "1 kilo x 5" -> número después de un peso
    re.compile(rf"\d\s*{UNIDAD_PESO}\.?\s*x\s*(\d{{1,2}})(?!\d)(?!\s*{UNIDAD_PESO}(?![a-z]))"),
    # "6 x 1 kg" al comienzo del título
    re.compile(rf"^(\d{{1,2}})\s*x\s*\d+(?:[.,]\d+)?\s*{UNIDAD_PESO}(?![a-z])"),
]


def normalizar(texto: str) -> str:
    """Minúsculas y sin acentos."""
    t = unicodedata.normalize("NFKD", str(texto).lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def peso_unidad_kg(titulo: str) -> float | None:
    """Peso de UNA unidad en kg. '500 gr' -> 0.5, '25 Kgs.' -> 25.0. None si no figura."""
    m = _PESO.search(normalizar(titulo))
    if not m:
        return None
    n = float(m.group(1).replace(",", "."))
    return n if m.group(2).startswith("k") else n / 1000


def unidades_pack(titulo: str) -> int:
    """Cantidad de unidades del pack. Si el título no lo dice, 1."""
    t = normalizar(titulo)
    for patron in _PACKS:
        m = patron.search(t)
        if m and 2 <= int(m.group(1)) <= 50:
            return int(m.group(1))
    return 1
