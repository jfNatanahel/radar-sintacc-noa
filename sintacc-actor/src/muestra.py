"""Separación 90 % (trabajo) / 10 % (reservado), igual que en el Colab.

El 10 % reservado no se usa para el EDA ni para elegir features: queda para evaluar el
modelo del Producto 2 con datos que nunca vio. Sorteo al azar con semilla fija dentro de
cada grupo, así siempre da el mismo resultado y el 10 % tiene la misma mezcla que el total.
"""

import pandas as pd

from . import reglas


def sortear(df: pd.DataFrame, estratos: list[str]) -> pd.Series:
    """Devuelve una serie con "trabajo" o "reservado" para cada fila."""
    reservado = df.groupby(estratos, group_keys=False).sample(
        frac=reglas.FRACCION_RESERVA, random_state=reglas.SEMILLA).index
    return pd.Series("trabajo", index=df.index).where(~df.index.isin(reservado), "reservado")
