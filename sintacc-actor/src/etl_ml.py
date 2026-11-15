"""ETL del Dataset 1: Mercado Libre (insumos sin TACC)."""

import numpy as np
import pandas as pd

from . import reglas
from .parseo import peso_unidad_kg, unidades_pack


def limpiar(crudo: pd.DataFrame) -> pd.DataFrame:
    """Unifica categorías, saca duplicados y deja solo los insumos del proyecto."""
    ml = crudo.copy()
    ml["categoria"] = ml["categoria"].astype(str).str.replace(r"\d", "", regex=True).str.strip()
    ml = ml.drop_duplicates(subset="idPublicacion")
    ml = ml[ml["produtoDomainID"].isin(reglas.CATEGORIAS_ML_OK)]
    ml = ml[~ml["articuloTitulo"].str.lower().str.contains(reglas.EXCLUIR_ML)]
    return ml.reset_index(drop=True)


def _a_numero(serie: pd.Series) -> pd.Series:
    return pd.to_numeric(serie, errors="coerce")


def _a_bool(serie: pd.Series) -> pd.Series:
    return serie.astype(str).str.lower().eq("true").astype(int)


def crear_features(ml: pd.DataFrame) -> pd.DataFrame:
    """Crea las 10 features + precio_por_kg y marca valores dudosos."""
    ml = ml.copy()
    ml["precio"] = _a_numero(ml["nuevoPrecio"])
    ml = ml[ml["precio"] > 0]

    ml["peso_unidad_kg"] = ml["articuloTitulo"].apply(peso_unidad_kg)
    ml["unidades_pack"] = ml["articuloTitulo"].apply(unidades_pack)
    # Peso imposible = mal leído -> se trata como vacío
    fuera = ~ml["peso_unidad_kg"].between(reglas.PESO_MIN_KG, reglas.PESO_MAX_KG)
    ml.loc[fuera, "peso_unidad_kg"] = np.nan
    # Si falta, se usa la mediana del peso de UNA unidad de su categoría (y después se multiplica por el pack)
    ml["peso_imputado"] = ml["peso_unidad_kg"].isna().astype(int)
    ml["peso_unidad_kg"] = ml.groupby("categoria")["peso_unidad_kg"].transform(lambda x: x.fillna(x.median()))
    ml["peso_total_kg"] = ml["peso_unidad_kg"] * ml["unidades_pack"]

    ml["venta_por_mayor"] = (ml["unidades_pack"] >= reglas.UNIDADES_MAYORISTA).astype(int)
    ml["descuento_pct"] = ml["precioDiscount"].astype(str).str.extract(r"(\d+)")[0].astype(float).fillna(0)
    ml["envio_gratis"] = _a_bool(ml["envioGratis"])
    ml["tienda_oficial"] = _a_bool(ml["esTiendaOficial"])
    ml["cantidad_vendida"] = _a_numero(ml["cantidadVendida"]).fillna(0)
    ml["cantidad_evaluaciones"] = _a_numero(ml["numeroEvaluaciones"]).fillna(0)
    ml["stock_bajo"] = ml["highlight"].astype(str).str.upper().str.contains("ÚLTIMA").astype(int)

    # Solo para análisis de competitividad: NO es feature del modelo (depende del precio)
    ml["precio_por_kg"] = ml["precio"] / ml["peso_total_kg"]
    ml["outlier_precio_kg"] = _marcar_outliers(ml, "precio_por_kg", "categoria")

    columnas = ["idPublicacion", "articuloTitulo", "categoria", "precio", "peso_total_kg",
                "unidades_pack", "venta_por_mayor", "descuento_pct", "envio_gratis",
                "tienda_oficial", "cantidad_vendida", "cantidad_evaluaciones", "stock_bajo",
                "precio_por_kg", "peso_imputado", "outlier_precio_kg"]
    return ml[columnas].reset_index(drop=True)


def _marcar_outliers(df: pd.DataFrame, col: str, grupo: str) -> pd.Series:
    """1 si el valor está fuera del rango intercuartílico ampliado de su grupo."""
    def regla(x):
        q1, q3 = x.quantile([0.25, 0.75])
        k = reglas.IQR_K * (q3 - q1)
        return (~x.between(q1 - k, q3 + k)).astype(int)
    return df.groupby(grupo)[col].transform(regla)


def procesar(crudo: pd.DataFrame) -> pd.DataFrame:
    return crear_features(limpiar(crudo))
