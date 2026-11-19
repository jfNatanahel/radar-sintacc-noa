"""Producto 2: de la información a las decisiones.

Semáforo de compra por publicación de Mercado Libre:
- verde:    precio por kg bastante por debajo de lo normal -> oportunidad de compra
- amarillo: precio normal
- rojo:     precio por kg bastante por encima de lo normal -> cara
- revisar:  el precio por kg no es confiable (peso estimado o valor extremo)

Método actual ("mediana_categoria", plan B): lo normal es la mediana del precio por kg de su
categoría y tipo de venta (minorista o mayorista). Cuando DS entregue el modelo, lo normal
pasa a ser el precio esperado por el modelo (ver modelos/README.md). El Actor no entrena (R2).
"""

import numpy as np
import pandas as pd

from . import reglas

METODO_MEDIANA = "mediana_categoria"


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
    tipo = "mayoristas" if fila["venta_por_mayor"] == 1 else "minoristas"
    if fila["semaforo"] == "verde":
        return f"{pct} % más barato por kg que la mediana de {fila['categoria']} ({tipo})"
    if fila["semaforo"] == "rojo":
        return f"{pct} % más caro por kg que la mediana de {fila['categoria']} ({tipo})"
    return f"Precio normal para {fila['categoria']} ({tipo})"


def semaforo(ml: pd.DataFrame) -> pd.DataFrame:
    """Una fila por publicación con su referencia, la diferencia y el color del semáforo."""
    ml = ml.copy()
    ml["referencia_kg"] = referencias_precio_kg(ml)
    diferencia = ml["precio_por_kg"] / ml["referencia_kg"] - 1
    revisar = (ml["peso_imputado"] == 1) | (ml["outlier_precio_kg"] == 1)
    ml["diferencia_pct"] = (diferencia * 100).round(1)
    ml["ahorro_por_kg"] = (ml["referencia_kg"] - ml["precio_por_kg"]).round(0)
    ml["semaforo"] = [_color(d, r) for d, r in zip(diferencia, revisar)]
    ml["motivo"] = ml.apply(_motivo, axis=1)
    ml["metodo"] = METODO_MEDIANA
    ml["referencia_kg"] = ml["referencia_kg"].round(0)
    ml.loc[revisar, ["diferencia_pct", "ahorro_por_kg"]] = np.nan

    columnas = ["idPublicacion", "articuloTitulo", "categoria", "venta_por_mayor", "muestra",
                "precio", "precio_por_kg", "referencia_kg", "diferencia_pct", "ahorro_por_kg",
                "semaforo", "motivo", "metodo"]
    orden = {"verde": 0, "amarillo": 1, "rojo": 2, "revisar": 3}
    return (ml[columnas].assign(_o=ml["semaforo"].map(orden))
            .sort_values(["_o", "diferencia_pct"]).drop(columns="_o").reset_index(drop=True))


def resumen(insights: pd.DataFrame) -> dict:
    """Cantidades por color, total y por categoría, y las 10 mejores oportunidades."""
    conteo = insights.groupby(["categoria", "semaforo"]).size().unstack(fill_value=0)
    verdes = insights[insights["semaforo"] == "verde"].nsmallest(10, "diferencia_pct")
    return {
        "metodo": METODO_MEDIANA,
        "umbrales_pct": {"verde": reglas.SEMAFORO_VERDE * 100, "rojo": reglas.SEMAFORO_ROJO * 100},
        "total": insights["semaforo"].value_counts().to_dict(),
        "por_categoria": conteo.reset_index().to_dict("records"),
        "mejores_oportunidades": verdes[["idPublicacion", "articuloTitulo", "categoria",
                                         "precio_por_kg", "referencia_kg", "diferencia_pct"]]
                                 .to_dict("records"),
    }
