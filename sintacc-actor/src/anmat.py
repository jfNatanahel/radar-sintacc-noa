"""Validación de los productos contra el Listado Integrado de Alimentos Libres de Gluten (ANMAT).

Problema: que el título de Mercado Libre diga "sin TACC" lo escribe el vendedor; no garantiza que el
producto esté autorizado. Para un producto pensado para celíacos, recomendar uno que no lo es es el
peor error posible. El semáforo pasa de "barato" a "barato y seguro".

Mercado Libre no trae la marca (productoMarca viene vacío), así que se cruza por el título:
1. Marca: una marca del listado que aparece en el título (palabra completa).
2. Producto: dentro de esa marca, similitud del título con la denominación / nombre de fantasía
   registrados (rapidfuzz, como en el notebook del docente). Umbral en reglas.ANMAT_UMBRAL.

Niveles (columna `anmat`):
- validado:          marca y producto encontrados en el listado.
- marca_en_listado:  la marca tiene productos autorizados, pero este no se encontró: revisar a mano.
- no_encontrado:     la marca no figura en el listado (o el título no la dice).
- sin_listado:       no se cargó el listado (el Actor sigue funcionando, sin esta validación).
"""

import re
import unicodedata

import pandas as pd
from rapidfuzz import fuzz, process

from . import reglas

VALIDADO, MARCA, NO_ENCONTRADO, SIN_LISTADO = "validado", "marca_en_listado", "no_encontrado", "sin_listado"


def normalizar(texto) -> str:
    texto = unicodedata.normalize("NFKD", str(texto).lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", texto).strip()


def preparar_listado(listado: pd.DataFrame) -> dict[str, list[str]]:
    """{marca normalizada: [productos normalizados]} a partir de las columnas marca y producto."""
    df = listado.assign(marca=listado["marca"].map(normalizar), producto=listado["producto"].map(normalizar))
    df = df[df["marca"].str.len() >= reglas.ANMAT_MARCA_MIN]
    df = df[~df["marca"].isin(reglas.ANMAT_MARCAS_GENERICAS)]
    return df.groupby("marca")["producto"].apply(lambda s: sorted(set(s))).to_dict()


def _marca_en_titulo(titulo: str, marcas: list[str]) -> str | None:
    """La marca más larga del listado que aparece como palabra(s) completa(s) en el título."""
    t = f" {titulo} "
    encontradas = [m for m in marcas if f" {m} " in t]
    return max(encontradas, key=len) if encontradas else None


def validar(productos: pd.DataFrame, listado: dict[str, list[str]] | None) -> pd.DataFrame:
    """Devuelve idPublicacion, anmat, anmat_marca, anmat_producto y anmat_similitud."""
    if not listado:
        return pd.DataFrame({"idPublicacion": productos["idPublicacion"], "anmat": SIN_LISTADO,
                             "anmat_marca": None, "anmat_producto": None, "anmat_similitud": None})
    marcas = sorted(listado, key=len, reverse=True)
    filas = []
    for pid, titulo in zip(productos["idPublicacion"], productos["articuloTitulo"].map(normalizar)):
        marca = _marca_en_titulo(titulo, marcas)
        if marca is None:
            filas.append((pid, NO_ENCONTRADO, None, None, None))
            continue
        sin_marca = titulo.replace(marca, " ")
        mejor = process.extractOne(sin_marca, listado[marca], scorer=fuzz.token_set_ratio)
        if mejor and mejor[1] >= reglas.ANMAT_UMBRAL:
            filas.append((pid, VALIDADO, marca, mejor[0], round(mejor[1])))
        else:
            filas.append((pid, MARCA, marca, mejor[0] if mejor else None, round(mejor[1]) if mejor else None))
    return pd.DataFrame(filas, columns=["idPublicacion", "anmat", "anmat_marca", "anmat_producto",
                                        "anmat_similitud"])
