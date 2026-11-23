"""ETL del Dataset 1: Mercado Libre (insumos sin TACC).

Orden acordado con Data Science (16/11 y 18/11):
limpieza -> sorteo del 10 % (por categoría de búsqueda) -> categoría de Mercado Libre -> exclusiones -> lectura del título -> correcciones manuales
-> venta por mayor -> peso faltante (mediana de la unidad de la categoría, solo con el 90 %)
-> precio por kg -> marca de outliers (límites fijos).
"""

import numpy as np
import pandas as pd

from . import reglas
from .muestra import sortear
from .parseo import normalizar, peso_unidad_kg, unidades_pack


def limpiar(crudo: pd.DataFrame) -> pd.DataFrame:
    """Unifica categorías, saca duplicados y deja solo los insumos del proyecto."""
    ml = crudo.copy()
    ml["idPublicacion"] = ml["idPublicacion"].astype(str).str.strip()
    ml["categoria_busqueda"] = ml["categoria"].astype(str).str.replace(r"\d", "", regex=True).str.strip()
    ml = ml.drop_duplicates(subset="idPublicacion")
    ml = ml[ml["produtoDomainID"].isin(reglas.CATEGORIAS_ML_OK)]
    ml = ml[~ml["articuloTitulo"].str.lower().str.contains(reglas.EXCLUIR_ML)]
    return ml.reset_index(drop=True)


def categorizar(ml: pd.DataFrame) -> pd.DataFrame:
    """Categoría del producto según Mercado Libre (produtoDomainID) + féculas forzadas a harina (DS, 18/11).

    Se aplica después del sorteo: el 90/10 se hace con la categoría de búsqueda.
    """
    ml = ml.copy()
    ml["categoria"] = ml["produtoDomainID"].map(reglas.CATEGORIA_POR_DOMINIO)
    forzada = ml["idPublicacion"].map(reglas.CATEGORIA_FORZADA)
    ml["categoria"] = forzada.fillna(ml["categoria"])
    return ml


def excluir(ml: pd.DataFrame) -> pd.DataFrame:
    """Exclusiones del 16/11, aplicadas después del sorteo (misma regla para el 90 % y el 10 %)."""
    titulo = ml["articuloTitulo"].map(normalizar)
    nugget = titulo.str.contains(reglas.EXCLUIR_NUGGET) & ~titulo.str.contains(reglas.SALVA_NUGGET)
    fuera = ml["idPublicacion"].isin(reglas.EXCLUIR_IDS_ML)
    return ml[~(nugget | fuera)].reset_index(drop=True)


def _a_numero(serie: pd.Series) -> pd.Series:
    return pd.to_numeric(serie, errors="coerce")


def _a_bool(serie: pd.Series) -> pd.Series:
    return serie.astype(str).str.lower().eq("true").astype(int)


def crear_features(ml: pd.DataFrame) -> pd.DataFrame:
    """Crea las features, precio_por_kg y las marcas de calidad (peso_imputado, outlier_precio_kg)."""
    ml = ml.copy()
    ml["precio"] = _a_numero(ml["nuevoPrecio"])
    ml = ml[ml["precio"] > 0].copy()

    # 1. Lectura del título
    ml["peso_unidad_kg"] = ml["articuloTitulo"].apply(peso_unidad_kg)
    ml["unidades_pack"] = ml["articuloTitulo"].apply(unidades_pack)
    fuera = ~ml["peso_unidad_kg"].between(reglas.PESO_MIN_KG, reglas.PESO_MAX_KG)
    ml.loc[fuera, "peso_unidad_kg"] = np.nan  # peso imposible = mal leído

    # 2. Correcciones manuales verificadas por DS
    ids = ml["idPublicacion"]
    pack = ids.map(reglas.CORRECCION_PACK)
    ml["unidades_pack"] = pack.fillna(ml["unidades_pack"]).astype(int)
    peso = ids.map(reglas.CORRECCION_PESO_KG)
    ml["peso_unidad_kg"] = peso.fillna(ml["peso_unidad_kg"])

    # 3. Venta por mayor
    ml["venta_por_mayor"] = (ml["unidades_pack"] >= reglas.UNIDADES_MAYORISTA).astype(int)

    # 4. Peso faltante: mediana del peso de UNA unidad de la categoría, calculada SOLO con el 90 %
    ml["peso_imputado"] = ml["peso_unidad_kg"].isna().astype(int)
    medianas = ml[ml["muestra"] == "trabajo"].groupby("categoria")["peso_unidad_kg"].median()
    ml["peso_unidad_kg"] = ml["peso_unidad_kg"].fillna(ml["categoria"].map(medianas))
    ml["peso_total_kg"] = ml["peso_unidad_kg"] * ml["unidades_pack"]

    ml["descuento_pct"] = ml["precioDiscount"].astype(str).str.extract(r"(\d+)")[0].astype(float).fillna(0)
    ml["envio_gratis"] = _a_bool(ml["envioGratis"])
    ml["tienda_oficial"] = _a_bool(ml["esTiendaOficial"])
    ml["cantidad_vendida"] = _a_numero(ml["cantidadVendida"]).fillna(0)
    ml["cantidad_evaluaciones"] = _a_numero(ml["numeroEvaluaciones"]).fillna(0)
    ml["stock_bajo"] = ml["highlight"].astype(str).str.upper().str.contains("ÚLTIMA").astype(int)

    # Features del modelo en logaritmo (Bloque 5): peso_log y unidades_log. Objetivo: log1p(precio).
    ml["peso_log"] = np.log1p(ml["peso_total_kg"])
    ml["unidades_log"] = np.log1p(ml["unidades_pack"])

    # 5. Solo para análisis de competitividad: NO es feature del modelo (depende del precio)
    ml["precio_por_kg"] = ml["precio"] / ml["peso_total_kg"]
    limites = ml["categoria"].map(reglas.LIMITES_PRECIO_KG)
    bajo = limites.map(lambda x: x[0] if isinstance(x, tuple) else np.nan)
    alto = limites.map(lambda x: x[1] if isinstance(x, tuple) else np.nan)
    ml["outlier_precio_kg"] = (~ml["precio_por_kg"].between(bajo, alto)).astype(int)

    columnas = [
        "idPublicacion", "articuloTitulo", "categoria", "categoria_busqueda", "muestra", "precio",
        # features del modelo (5): peso_log, unidades_log, envio_gratis, descuento_pct, categoria
        "peso_log", "unidades_log", "envio_gratis", "descuento_pct",
        # columnas que el dashboard necesita aunque no sean features (Bloque 5, punto 9)
        "peso_total_kg", "unidades_pack", "venta_por_mayor", "tienda_oficial",
        "cantidad_vendida", "cantidad_evaluaciones", "stock_bajo",
        "precio_por_kg", "peso_imputado", "outlier_precio_kg",
    ]
    return ml[columnas].reset_index(drop=True)


def procesar(crudo: pd.DataFrame) -> pd.DataFrame:
    limpio = limpiar(crudo)
    limpio["muestra"] = sortear(limpio, reglas.ESTRATOS_ML)
    return crear_features(excluir(categorizar(limpio)))
