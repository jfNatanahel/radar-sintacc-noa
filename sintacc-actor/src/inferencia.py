"""Producto 2: de la información a las decisiones.

Semáforo de compra por publicación de Mercado Libre:
- verde:    precio por kg bastante por debajo de lo normal -> oportunidad de compra
- amarillo: precio normal
- rojo:     precio por kg bastante por encima de lo normal -> cara
- revisar:  el precio por kg no es confiable (peso estimado o valor extremo)

Dos formas de calcular "lo normal" (columna `metodo`):
- "modelo_random_forest" (principal): el precio esperado por el modelo de DS según el peso, el
  pack, la categoría, el envío gratis y el descuento. Compara cada publicación con lo que
  debería costar ella misma, no con un promedio que mezcla productos distintos.
- "mediana_categoria" (plan B, sin modelo): la mediana del precio por kg de su categoría y
  tipo de venta (minorista o mayorista).
El Actor no entrena (R2): el modelo llega ya entrenado en modelos/ (R3).
"""

import numpy as np
import pandas as pd

from . import reglas

METODO_MEDIANA = "mediana_categoria"
METODO_MODELO = "modelo_random_forest"


def referencias_precio_kg(ml: pd.DataFrame) -> pd.Series:
    """Precio por kg "normal" de cada publicación, según su categoría y tipo de venta.

    Se calcula solo con el 90 % de trabajo y sin outliers, para no usar el 10 % reservado.
    """
    base = ml[(ml["muestra"] == "trabajo") & (ml["outlier_precio_kg"] == 0)]
    por_grupo = base.groupby(["categoria", "venta_por_mayor"])["precio_por_kg"].agg(["median", "size"])
    por_grupo = por_grupo[por_grupo["size"] >= reglas.SEMAFORO_MIN_GRUPO]["median"]
    por_categoria = base.groupby("categoria")["precio_por_kg"].median()

    claves = pd.MultiIndex.from_frame(ml[["categoria", "venta_por_mayor"]])
    ref = pd.Series(por_grupo.reindex(claves).to_numpy(), index=ml.index)
    return ref.fillna(ml["categoria"].map(por_categoria))


def _color(diferencia: float, revisar: bool) -> str:
    if revisar or pd.isna(diferencia):
        return "revisar"
    if diferencia <= reglas.SEMAFORO_VERDE:
        return "verde"
    if diferencia >= reglas.SEMAFORO_ROJO:
        return "rojo"
    return "amarillo"


def _motivo(fila: pd.Series) -> str:
    if fila["peso_imputado"] == 1:
        return "Peso estimado: el título no dice el peso"
    if fila["outlier_precio_kg"] == 1:
        return "Precio por kg fuera de rango: revisar la publicación"
    pct = abs(round(fila["diferencia_pct"]))
    if fila["metodo"] == METODO_MODELO:
        if fila["semaforo"] == "verde":
            return f"{pct} % más barato que lo esperado para su peso, pack y categoría"
        if fila["semaforo"] == "rojo":
            return f"{pct} % más caro que lo esperado para su peso, pack y categoría"
        return "Precio acorde a lo esperado para su peso, pack y categoría"
    tipo = "mayoristas" if fila["venta_por_mayor"] == 1 else "minoristas"
    if fila["semaforo"] == "verde":
        return f"{pct} % más barato por kg que la mediana de {fila['categoria']} ({tipo})"
    if fila["semaforo"] == "rojo":
        return f"{pct} % más caro por kg que la mediana de {fila['categoria']} ({tipo})"
    return f"Precio normal para {fila['categoria']} ({tipo})"


def agregar_anmat(insights: pd.DataFrame, validacion: pd.DataFrame) -> pd.DataFrame:
    """Suma la validación ANMAT y `recomendado` = verde y validado ("barato y seguro")."""
    df = insights.merge(validacion, on="idPublicacion", how="left")
    sin_listado = (df["anmat"] == "sin_listado").all()
    df["recomendado"] = ((df["semaforo"] == "verde") & (sin_listado | (df["anmat"] == "validado"))).astype(int)
    if not sin_listado:
        nota = df["anmat"].map({"validado": " · validado en el listado ANMAT",
                                "marca_en_listado": " · la marca está en ANMAT, el producto no: verificar",
                                "no_encontrado": " · no figura en el listado ANMAT: no recomendar"})
        df["motivo"] = df["motivo"] + nota.where(df["semaforo"] != "revisar", "").fillna("")
    return df


def semaforo(ml: pd.DataFrame, precio_esperado: pd.Series | None = None) -> pd.DataFrame:
    """Una fila por publicación con su referencia, la diferencia y el color del semáforo.

    Con `precio_esperado` (predicción del modelo, en pesos) la referencia es esa publicación;
    sin él, la mediana de su categoría y tipo de venta (plan B).
    """
    ml = ml.copy()
    if precio_esperado is None:
        ml["metodo"] = METODO_MEDIANA
        ml["referencia_kg"] = referencias_precio_kg(ml)
        ml["precio_esperado"] = ml["referencia_kg"] * ml["peso_total_kg"]
    else:
        ml["metodo"] = METODO_MODELO
        ml["precio_esperado"] = precio_esperado
        ml["referencia_kg"] = ml["precio_esperado"] / ml["peso_total_kg"]
    diferencia = ml["precio_por_kg"] / ml["referencia_kg"] - 1
    revisar = (ml["peso_imputado"] == 1) | (ml["outlier_precio_kg"] == 1)
    ml["diferencia_pct"] = (diferencia * 100).round(1)
    ml["ahorro_por_kg"] = (ml["referencia_kg"] - ml["precio_por_kg"]).round(0)
    ml["semaforo"] = [_color(d, r) for d, r in zip(diferencia, revisar)]
    ml["motivo"] = ml.apply(_motivo, axis=1)
    ml["referencia_kg"] = ml["referencia_kg"].round(0)
    ml["precio_esperado"] = ml["precio_esperado"].round(0)
    ml["precio_por_kg"] = ml["precio_por_kg"].round(0)
    ml.loc[revisar, ["diferencia_pct", "ahorro_por_kg"]] = np.nan

    columnas = ["idPublicacion", "articuloTitulo", "categoria", "venta_por_mayor", "muestra",
                "precio", "precio_esperado", "precio_por_kg", "referencia_kg", "diferencia_pct", "ahorro_por_kg",
                "semaforo", "motivo", "metodo"]
    orden = {"verde": 0, "amarillo": 1, "rojo": 2, "revisar": 3}
    return (ml[columnas].assign(_o=ml["semaforo"].map(orden))
            .sort_values(["_o", "diferencia_pct"]).drop(columns="_o").reset_index(drop=True))


def resumen(insights: pd.DataFrame) -> dict:
    """Cantidades por color, total y por categoría, y las 10 mejores oportunidades."""
    conteo = insights.groupby(["categoria", "semaforo"]).size().unstack(fill_value=0)
    verdes = insights[insights["semaforo"] == "verde"].nsmallest(10, "diferencia_pct")
    return {
        "metodo": str(insights["metodo"].iloc[0]) if len(insights) else METODO_MEDIANA,
        "umbrales_pct": {"verde": reglas.SEMAFORO_VERDE * 100, "rojo": reglas.SEMAFORO_ROJO * 100},
        "total": {k: int(v) for k, v in insights["semaforo"].value_counts().items()},
        "anmat": ({k: int(v) for k, v in insights["anmat"].value_counts().items()}
                  if "anmat" in insights else None),
        "recomendados": int(insights["recomendado"].sum()) if "recomendado" in insights else None,
        "por_categoria": conteo.reset_index().to_dict("records"),
        "mejores_oportunidades": verdes[["idPublicacion", "articuloTitulo", "categoria", "precio",
                                         "precio_esperado", "precio_por_kg", "referencia_kg",
                                         "diferencia_pct"]]
                                 .to_dict("records"),
    }


def popularidad_locales(maps: pd.DataFrame, resenas_esperadas: pd.Series) -> pd.DataFrame:
    """Modelo complementario (Maps): reseñas reales contra las esperadas por el modelo.

    Las reseñas miden popularidad, no ventas. Un local con muchas más reseñas que las esperadas
    para sus fotos, calificación, tipo y provincia es más popular de lo que "debería": sirve para
    priorizar a qué locales ofrecerles los insumos (clientes potenciales con demanda visible).
    """
    m = maps.copy()
    m["resenas_esperadas"] = resenas_esperadas.round(0)
    razon = (m["resenas"] + 1) / (m["resenas_esperadas"] + 1)
    m["popularidad"] = np.select(
        [razon >= reglas.POPULARIDAD_ALTA, razon <= 1 / reglas.POPULARIDAD_ALTA],
        ["por encima de lo esperado", "por debajo de lo esperado"], "acorde a lo esperado")
    m["razon_resenas"] = razon.round(2)
    columnas = ["placeId", "title", "provincia", "tipo_local", "grupo_sin_tacc", "muestra",
                "resenas", "resenas_esperadas", "razon_resenas", "popularidad"]
    return m[columnas].sort_values("razon_resenas", ascending=False).reset_index(drop=True)


def conteo_popularidad(popularidad: pd.DataFrame) -> dict:
    return {k: int(v) for k, v in popularidad["popularidad"].value_counts().items()}
