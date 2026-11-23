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

import numpy as np
import pandas as pd
from rapidfuzz import fuzz, process

from . import reglas

VALIDADO, MARCA, NO_ENCONTRADO, SIN_LISTADO = "validado", "marca_en_listado", "no_encontrado", "sin_listado"


def normalizar(texto) -> str:
    texto = unicodedata.normalize("NFKD", str(texto).lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", texto).strip()


# Marcas diacríticas (tildes, diéresis, etc.) que deja la descomposición NFKD
_DIACRITICOS = r"[̀-ͯ᪰-᫿᷀-᷿⃐-⃿︠-︯]"


def normalizar_serie(textos: pd.Series) -> pd.Series:
    """`normalizar` vectorizado con los métodos .str de pandas (sin recorrer fila por fila)."""
    return (textos.astype(str).str.lower().str.normalize("NFKD")
            .str.replace(_DIACRITICOS, "", regex=True)
            .str.replace(r"[^a-z0-9]+", " ", regex=True).str.strip())


def preparar_listado(listado: pd.DataFrame) -> dict[str, list[str]]:
    """{marca normalizada: [productos normalizados]} a partir de las columnas marca y producto."""
    df = listado.assign(marca=normalizar_serie(listado["marca"]), producto=normalizar_serie(listado["producto"]))
    df = df[df["marca"].str.len() >= reglas.ANMAT_MARCA_MIN]
    df = df[~df["marca"].isin(reglas.ANMAT_MARCAS_GENERICAS)]
    return df.groupby("marca")["producto"].apply(lambda s: sorted(set(s))).to_dict()


class _IndiceMarcas:
    """Busca la marca del título por n-gramas en un set: O(palabras del título), no O(marcas).

    Antes se recorrían las ~4.700 marcas por cada título (831 × 4.700 búsquedas de texto).
    Ahora se arman los n-gramas del título (de 1 a la cantidad de palabras de la marca más larga)
    y se buscan en un set. Mismo resultado: la marca más larga y, a igual largo, la primera en orden
    alfabético.
    """

    def __init__(self, marcas):
        orden = sorted(marcas, key=len, reverse=True)
        self.posicion = {m: i for i, m in enumerate(orden)}
        self.max_palabras = max((len(m.split()) for m in orden), default=0)

    def buscar(self, titulo: str) -> str | None:
        p = titulo.split()
        ngramas = {" ".join(p[i:i + n]) for n in range(1, self.max_palabras + 1) for i in range(len(p) - n + 1)}
        encontradas = ngramas & self.posicion.keys()
        return min(encontradas, key=self.posicion.__getitem__) if encontradas else None


class _IndiceProductos:
    """Matriz palabra × producto de UNA marca, para medir la cobertura de todos sus productos juntos.

    Antes, por cada título se recorría cada producto de la marca y, por cada palabra clave, se
    buscaba la más parecida entre las palabras del producto (títulos × productos × claves).
    Ahora la similitud se calcula una vez entre las claves y el vocabulario de la marca
    (`rapidfuzz.process.cdist`, en C) y la cobertura de todos los productos sale de un producto de
    matrices. Se arma solo para las marcas que aparecen en los títulos y se reutiliza.
    """

    def __init__(self, productos: list[str]):
        self.productos = productos
        palabras = [{reglas.ANMAT_SINONIMOS.get(w, w) for w in prod.split()} for prod in productos]
        self.vocabulario = sorted(set().union(*palabras))
        col = {w: j for j, w in enumerate(self.vocabulario)}
        self.matriz = np.zeros((len(self.vocabulario), len(productos)), dtype=np.int32)
        for k, ws in enumerate(palabras):
            self.matriz[[col[w] for w in ws], k] = 1

    def mejor(self, claves: list[str]) -> tuple[str | None, int, float]:
        """Producto con más palabras clave presentes (a igual cantidad, el primero), cantidad y cobertura."""
        if not claves or not self.vocabulario:
            return None, 0, 0.0
        parecidas = process.cdist(claves, self.vocabulario, scorer=fuzz.ratio, dtype=np.float64,
                                  score_cutoff=reglas.ANMAT_SIMILITUD_PALABRA) > 0
        presentes = ((parecidas.astype(np.int32) @ self.matriz) > 0).sum(axis=0)
        k = int(presentes.argmax())  # argmax devuelve el primero si hay empate
        n = int(presentes[k])
        return (self.productos[k], n, n / len(claves)) if n else (None, 0, 0.0)


def _claves(texto: str) -> list[str]:
    palabras = [reglas.ANMAT_SINONIMOS.get(p, p) for p in texto.split()]
    vistas: list[str] = []
    for p in palabras:
        if p not in reglas.ANMAT_RUIDO and not any(ch.isdigit() for ch in p) and len(p) > 2 and p not in vistas:
            vistas.append(p)
    return vistas


def validar(productos: pd.DataFrame, listado: dict[str, list[str]] | None) -> pd.DataFrame:
    """Devuelve idPublicacion, anmat, anmat_marca, anmat_producto y anmat_similitud (0 a 100)."""
    if not listado:
        return pd.DataFrame({"idPublicacion": productos["idPublicacion"], "anmat": SIN_LISTADO,
                             "anmat_marca": None, "anmat_producto": None, "anmat_similitud": None})
    marcas = _IndiceMarcas(listado)
    por_marca: dict[str, _IndiceProductos] = {}  # se arma solo para las marcas que aparecen
    filas = []
    for pid, titulo in zip(productos["idPublicacion"], normalizar_serie(productos["articuloTitulo"])):
        marca = marcas.buscar(titulo)
        if marca is None:
            filas.append((pid, NO_ENCONTRADO, None, None, None))
            continue
        claves = _claves(f" {titulo} ".replace(f" {marca} ", " "))
        if marca not in por_marca:
            por_marca[marca] = _IndiceProductos(listado[marca])
        mejor, mejor_n, mejor_cob = por_marca[marca].mejor(claves)
        ok = mejor_n >= reglas.ANMAT_MIN_CLAVES and mejor_cob >= reglas.ANMAT_COBERTURA
        filas.append((pid, VALIDADO if ok else MARCA, marca, mejor, round(100 * mejor_cob)))
    return pd.DataFrame(filas, columns=["idPublicacion", "anmat", "anmat_marca", "anmat_producto",
                                        "anmat_similitud"])
