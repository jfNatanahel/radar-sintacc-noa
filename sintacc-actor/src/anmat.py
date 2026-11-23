"""Validación de los productos contra el Listado Integrado de Alimentos Libres de Gluten (ANMAT).

Problema: que el título de Mercado Libre diga "sin TACC" lo escribe el vendedor; no garantiza que el
producto esté autorizado. Para un producto pensado para celíacos, recomendar uno que no lo es es el
peor error posible. El semáforo pasa de "barato" a "barato y seguro".

Mercado Libre no trae la marca (productoMarca viene vacío), así que se cruza por el título:
1. Marca: una marca del listado que aparece en el título (palabra completa).
2. Producto: palabras clave del título (sin marca, pesos, packs, formas de pasta ni "sin tacc").
   Se busca el producto registrado de esa marca que contiene más de esas palabras (rapidfuzz para
   tolerar tipeos, como en el notebook del docente). Validado: al menos 2 palabras clave y el 75 %.

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


def _claves(texto: str) -> list[str]:
    palabras = [reglas.ANMAT_SINONIMOS.get(p, p) for p in texto.split()]
    vistas: list[str] = []
    for p in palabras:
        if p not in reglas.ANMAT_RUIDO and not any(ch.isdigit() for ch in p) and len(p) > 2 and p not in vistas:
            vistas.append(p)
    return vistas


def _cobertura(claves: list[str], producto: str) -> tuple[int, float]:
    """Cuántas palabras clave del título están en el producto (con tolerancia a tipeos)."""
    palabras = {reglas.ANMAT_SINONIMOS.get(p, p) for p in producto.split()}
    presentes = sum(1 for c in claves
                    if c in palabras or (process.extractOne(c, palabras, scorer=fuzz.ratio) or ("", 0))[1]
                    >= reglas.ANMAT_SIMILITUD_PALABRA)
    return presentes, presentes / len(claves) if claves else 0.0


def validar(productos: pd.DataFrame, listado: dict[str, list[str]] | None) -> pd.DataFrame:
    """Devuelve idPublicacion, anmat, anmat_marca, anmat_producto y anmat_similitud (0 a 100)."""
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
        claves = _claves(f" {titulo} ".replace(f" {marca} ", " "))
        mejor, mejor_n, mejor_cob = None, 0, 0.0
        for producto in listado[marca]:
            n, cob = _cobertura(claves, producto)
            if (n, cob) > (mejor_n, mejor_cob):
                mejor, mejor_n, mejor_cob = producto, n, cob
        ok = mejor_n >= reglas.ANMAT_MIN_CLAVES and mejor_cob >= reglas.ANMAT_COBERTURA
        filas.append((pid, VALIDADO if ok else MARCA, marca, mejor, round(100 * mejor_cob)))
    return pd.DataFrame(filas, columns=["idPublicacion", "anmat", "anmat_marca", "anmat_producto",
                                        "anmat_similitud"])
