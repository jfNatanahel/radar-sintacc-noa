"""EDA: indicadores de negocio listos para el dashboard.

Cada función responde una pregunta de negocio del cliente.
"""

import pandas as pd


def precio_kg_por_categoria(ml: pd.DataFrame) -> list[dict]:
    """¿Cuánto cuesta el kilo de cada insumo y cuánto se ahorra comprando por mayor?"""
    base = ml[ml["outlier_precio_kg"] == 0]
    filas = []
    for cat, g in base.groupby("categoria"):
        menor = g.loc[g["venta_por_mayor"] == 0, "precio_por_kg"].median()
        mayor = g.loc[g["venta_por_mayor"] == 1, "precio_por_kg"].median()
        n_mayor = int((g["venta_por_mayor"] == 1).sum())
        ahorro = (1 - mayor / menor) * 100 if n_mayor >= 3 and menor else None
        filas.append({
            "categoria": cat,
            "publicaciones": len(g),
            "precio_kg_mediana": round(g["precio_por_kg"].median()),
            "precio_kg_minorista": round(menor) if pd.notna(menor) else None,
            "precio_kg_mayorista": round(mayor) if pd.notna(mayor) else None,
            "publicaciones_mayoristas": n_mayor,
            "ahorro_mayorista_pct": round(ahorro, 1) if ahorro is not None else None,
        })
    return filas


def mas_vendidos(ml: pd.DataFrame, n: int = 10) -> list[dict]:
    """¿Qué productos elige más el consumidor?"""
    cols = ["categoria", "articuloTitulo", "precio", "precio_por_kg", "cantidad_vendida"]
    return ml.sort_values("cantidad_vendida", ascending=False)[cols].head(n).round(0).to_dict("records")


def oferta_por_provincia(maps: pd.DataFrame) -> list[dict]:
    """¿Qué proporción de locales ofrece sin TACC en cada provincia?"""
    g = maps.groupby("provincia").agg(
        locales=("placeId", "count"),
        sin_tacc_confirmado=("sin_tacc_confirmado", "sum"),
        sin_tacc_busqueda=("sin_tacc_busqueda", "sum"),
        resenas_mediana=("resenas", "median"),
    ).reset_index()
    g["pct_confirmado"] = (100 * g["sin_tacc_confirmado"] / g["locales"]).round(1)
    return g.to_dict("records")


def oportunidad_por_tipo(maps: pd.DataFrame) -> list[dict]:
    """¿Qué tipo de local tiene más espacio para sumar sin TACC?"""
    g = maps.groupby("tipo_local").agg(
        locales=("placeId", "count"),
        con_sin_tacc=("sin_tacc_confirmado", "sum"),
        resenas_mediana=("resenas", "median"),
    ).reset_index()
    g["pct_sin_oferta"] = (100 * (1 - g["con_sin_tacc"] / g["locales"])).round(1)
    return g.sort_values("pct_sin_oferta", ascending=False).to_dict("records")


def zonas_sin_oferta(maps: pd.DataFrame, min_locales: int = 10) -> list[dict]:
    """Locales con mucha actividad alrededor pero ningún sin TACC confirmado a 2 km:
    candidatos a ser el primero en ofrecerlo (y clientes potenciales del distribuidor)."""
    z = maps[(maps["sin_tacc_2km"] == 0) & (maps["locales_2km"] >= min_locales)
             & (maps["sin_tacc_confirmado"] == 0)]
    cols = ["title", "provincia", "tipo_local", "resenas", "locales_2km", "latitud", "longitud"]
    return z.sort_values("resenas", ascending=False)[cols].head(20).to_dict("records")


def resumen(ml: pd.DataFrame, maps: pd.DataFrame, pasos_maps: list) -> dict:
    return {
        "registros": {"productos": len(ml), "locales": len(maps)},
        "calidad": {
            "productos_peso_imputado": int(ml["peso_imputado"].sum()),
            "productos_outlier_precio_kg": int(ml["outlier_precio_kg"].sum()),
            "limpieza_locales": [{"paso": p, "quedan": n} for p, n in pasos_maps],
        },
        "precio_kg_por_categoria": precio_kg_por_categoria(ml),
        "mas_vendidos": mas_vendidos(ml),
        "oferta_por_provincia": oferta_por_provincia(maps),
        "oportunidad_por_tipo": oportunidad_por_tipo(maps),
        "zonas_sin_oferta": zonas_sin_oferta(maps),
    }
