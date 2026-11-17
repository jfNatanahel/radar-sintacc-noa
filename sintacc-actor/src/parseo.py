"""Lectura de peso y unidades desde el título de Mercado Libre.

Mercado Libre no trae el peso ni el pack como columna: hay que sacarlos del título.
Son reglas (regex) porque el formato es corto y cerrado. Cada caso raro que
aparece se agrega primero como test en tests/test_parseo.py.

Reglas finales acordadas con Data Science el 16/11 (Documentación del CAPSTONE,
"16/11 - Cierre de la limpieza del Dataset 1", punto 2).
"""

import re
import unicodedata

UNIDAD_PESO = r"(?:kilogramos?|kilos?|kgr?s?|k|gramos?|grs?|g)"
_NUM = r"\d+(?:[.,]\d+)?"
# Otras unidades: un "x 3" seguido de una de estas no es un pack
_OTRA_UNIDAD = r"(?:ml|cc|lts?|litros?|l|cm|mm|m|oz)"
_NO_UNIDAD = rf"(?!\s*[.,]?\d)(?!\s*(?:{UNIDAD_PESO}|{_OTRA_UNIDAD})(?![a-z]))"

_PESO = re.compile(rf"({_NUM})\s*({UNIDAD_PESO})(?![a-z])")
# "3 x 5 kg": el peso que va después de "N x" es el de UNA unidad, aunque antes figure el total
_N_X_PESO = re.compile(rf"(?<![\d.,])\d{{1,2}}\s*x\s*({_NUM})\s*({UNIDAD_PESO})(?![a-z])")

# Patrones de pack, en orden de prioridad. Todos capturan la cantidad.
_PACKS = [
    # "pack x 12", "pack 6", "pack de 3", "caja x 10"
    re.compile(rf"(?:pack|caja)\s*(?:de\s*)?(?:x\s*)?(\d{{1,2}})(?!\d){_NO_UNIDAD}"),
    # "12 unidades", "3u", "x6 unidades", "15 paquetes"
    re.compile(r"(\d{1,2})\s*(?:u|un|und|unds|uni|unid|unids|unida|unidad|unidades|paquetes|paq|bolsas|packs?)(?![a-z])"),
    # "500gr x 20", "1 kilo x 5" -> número después de un peso
    re.compile(rf"\d\s*{UNIDAD_PESO}\.?\s*x\s*(\d{{1,2}})(?!\d){_NO_UNIDAD}"),
    # "6 x 1 kg", "3 x 5 kg", "10 x 400 g" en cualquier parte del título
    re.compile(rf"(?<![\d.,])(\d{{1,2}})\s*x\s*{_NUM}\s*{UNIDAD_PESO}(?![a-z])"),
    # "x14", "x 3" sueltos (no seguidos de un peso ni de otra unidad)
    re.compile(rf"(?<![a-z\d])x\s*(\d{{1,2}})(?!\d){_NO_UNIDAD}"),
    # "2x" al inicio del título
    re.compile(r"^(\d{1,2})\s*x(?![a-z\d])"),
]

PACK_MIN, PACK_MAX = 2, 50


def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes y con "c/u" separado del número anterior.

    También borra el número de modelo de los fideos ("N°7", "Nº 5", "Nro 3"), que no es un pack.
    """
    t = re.sub(r"\bn(?:ro|°|º|\.)\s*\d+", " ", str(texto).lower())
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s*c/u", " c/u", t).strip()


def peso_unidad_kg(titulo: str) -> float | None:
    """Peso de UNA unidad en kg. '500 gr' -> 0.5, '25 Kgs.' -> 25.0, '3k' -> 3.0. None si no figura."""
    t = normalizar(titulo)
    m = _N_X_PESO.search(t) or _PESO.search(t)
    if not m:
        return None
    n = float(m.group(1).replace(",", "."))
    return n if m.group(2).startswith("k") else n / 1000


def unidades_pack(titulo: str) -> int:
    """Cantidad de unidades del pack (de 2 a 50). Si el título no lo dice, 1."""
    t = normalizar(titulo)
    for patron in _PACKS:
        for m in patron.finditer(t):
            if PACK_MIN <= int(m.group(1)) <= PACK_MAX:
                return int(m.group(1))
    return 1
