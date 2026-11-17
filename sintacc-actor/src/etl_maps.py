"""ETL del Dataset 2: Google Maps (locales gastronómicos de Salta, Jujuy y La Rioja)."""

import re

import numpy as np
import pandas as pd

from . import reglas
from .muestra import sortear


def _texto(df: pd.DataFrame, *cols: str) -> pd.Series:
    t = pd.Series("", index=df.index)
    for c in cols:
        if c in df:
            t = t + " " + df[c].fillna("").astype(str)
    return t.str.lower()


def marcar_sin_tacc(crudo: pd.DataFrame) -> pd.DataFrame:
    """Dos niveles de evidencia, calculados ANTES de sacar duplicados.

    - sin_tacc_confirmado: el nombre o la categoría del local lo dicen.
    - sin_tacc_busqueda: solo apareció al buscar "... sin tacc" en Google (evidencia débil:
      Google también devuelve locales populares cercanos que no son aptos).
    """
    df = crudo.copy()
    df["sin_tacc_confirmado"] = _texto(df, "title", "categoryName").str.contains(reglas.PALABRAS_SIN_TACC)
    df["sin_tacc_busqueda"] = _texto(df, "searchString").str.contains(reglas.PALABRAS_SIN_TACC)
    if "sin_tacc" in df:  # CSV ya unificado por el Colab: trae la marca de búsqueda calculada
        df["sin_tacc_busqueda"] |= df["sin_tacc"].astype(str).str.lower().eq("true")
    for c in ["sin_tacc_confirmado", "sin_tacc_busqueda"]:
        df[c] = df.groupby("placeId")[c].transform("max")
    # Búsqueda = evidencia débil: solo si NO está confirmado (las dos marcas no se superponen)
    df["sin_tacc_busqueda"] &= ~df["sin_tacc_confirmado"]
    return df


def _ciudad_de_direccion(direccion) -> str | float:
    partes = [p.strip() for p in str(direccion).split(",")]
    if len(partes) >= 2:
        return re.sub(r"^[A-Z]?\d{3,4}[A-Z]{0,3}\s*", "", partes[-2]).strip()
    return np.nan


def limpiar(crudo: pd.DataFrame) -> tuple[pd.DataFrame, list[tuple[str, int]]]:
    """Devuelve el dataset limpio y el registro de cuántos quedan en cada paso."""
    df = marcar_sin_tacc(crudo).drop_duplicates(subset="placeId")
    pasos = [("Unificado y sin duplicados", len(df))]

    df = df[df["state"].isin(reglas.PROVINCIAS) & (df["countryCode"] == "AR")].copy()
    df["provincia"] = df["state"]
    pasos.append(("Solo Salta, Jujuy y La Rioja", len(df)))

    df["ciudad"] = df["city"].fillna(df["address"].apply(_ciudad_de_direccion)).astype(str)
    df.loc[df["ciudad"].str.lower().str.startswith("san salvador"), "ciudad"] = "San Salvador de Jujuy"
    df = df[df["ciudad"] == df["provincia"].map(reglas.PROVINCIAS)]
    pasos.append(("Solo capitales", len(df)))

    hotel = (df.get("hotelStars", pd.Series(index=df.index, dtype=str)).fillna("").astype(str).str.startswith("Hotel")
             | df["categoryName"].fillna("").str.contains("Hotel|Alojamiento", case=False))
    df = df[~hotel]
    pasos.append(("Sin alojamientos", len(df)))

    cerrado = (df.get("permanentlyClosed", False) == True) | (df.get("temporarilyClosed", False) == True)  # noqa: E712
    df = df[~cerrado]
    pasos.append(("Sin locales cerrados", len(df)))

    df = df[df["reviewsCount"].notna()]
    pasos.append(("Con cantidad de reseñas", len(df)))
    return df.reset_index(drop=True), pasos


def _tipo_local(categoria) -> str:
    c = str(categoria).lower()
    for tipo, patron in reglas.TIPOS_LOCAL.items():
        if re.search(patron, c):
            return tipo
    return "otro"


def _lat_lng(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Acepta la salida JSON de Apify (location: {lat, lng}) o el CSV aplanado (location/lat)."""
    if "location/lat" in df:
        return df["location/lat"], df["location/lng"]
    loc = df["location"].apply(lambda d: d if isinstance(d, dict) else {})
    return loc.apply(lambda d: d.get("lat")), loc.apply(lambda d: d.get("lng"))


def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi, dlmb = p2 - p1, np.radians(lon2) - np.radians(lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlmb / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.sqrt(a))


def crear_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["resenas"] = df["reviewsCount"].astype(int)
    df["calificacion"] = df["totalScore"]
    df["latitud"], df["longitud"] = _lat_lng(df)
    df["tipo_local"] = df["categoryName"].apply(_tipo_local)
    df["tiene_sitio_web"] = df["website"].notna().astype(int)
    df["cantidad_fotos"] = df.get("imagesCount", 0)
    df["sin_tacc_confirmado"] = df["sin_tacc_confirmado"].astype(int)
    df["sin_tacc_busqueda"] = df["sin_tacc_busqueda"].astype(int)
    df["fotos_log"] = np.log1p(df["cantidad_fotos"])
    # Color del mapa del dashboard: confirmado / búsqueda (evidencia débil) / ninguno
    df["grupo_sin_tacc"] = np.select([df["sin_tacc_confirmado"] == 1, df["sin_tacc_busqueda"] == 1],
                                     ["confirmado", "busqueda"], "ninguno")

    # Competencia cercana: locales con sin TACC CONFIRMADO a menos de 2 km, sin contar el propio.
    # Como en el Colab, solo cuentan como vecinos los locales del 90 % de trabajo.
    lat, lon = df["latitud"].to_numpy(float), df["longitud"].to_numpy(float)
    dist = haversine_km(lat[:, None], lon[:, None], lat[None, :], lon[None, :])
    np.fill_diagonal(dist, np.inf)
    trabajo = (df["muestra"] == "trabajo").to_numpy()
    confirmado = (df["sin_tacc_confirmado"] == 1).to_numpy()
    cerca = dist < reglas.RADIO_KM
    df["sin_tacc_2km"] = (cerca & (confirmado & trabajo)[None, :]).sum(axis=1)
    df["locales_2km"] = (cerca & trabajo[None, :]).sum(axis=1)

    columnas = [
        "placeId", "title", "muestra", "resenas",
        # features del modelo (7): fotos_log, sin_tacc_2km, sin_tacc_busqueda, sin_tacc_confirmado,
        # calificacion, tipo_local y provincia
        "fotos_log", "sin_tacc_2km", "sin_tacc_busqueda", "sin_tacc_confirmado",
        "calificacion", "tipo_local", "provincia",
        # columnas para el dashboard (mapa) y para el análisis (Bloque 5, punto 9)
        "latitud", "longitud", "grupo_sin_tacc", "ciudad", "cantidad_fotos", "tiene_sitio_web", "locales_2km",
    ]
    return df[columnas]


def procesar(crudo: pd.DataFrame) -> tuple[pd.DataFrame, list[tuple[str, int]]]:
    limpio, pasos = limpiar(crudo)
    limpio["sin_tacc_confirmado"] = limpio["sin_tacc_confirmado"].astype(int)
    limpio["muestra"] = sortear(limpio, reglas.ESTRATOS_MAPS)
    pasos.append(("90 % de trabajo (10 % reservado aparte)", int((limpio["muestra"] == "trabajo").sum())))
    return crear_features(limpio), pasos
