"""Carga y uso de los modelos entrenados por Data Science (Producto 2).

R2: el Actor no entrena. Solo carga el Pipeline ya entrenado y llama a predict.
R3: el modelo vive en la carpeta modelos/ del repo (versión fija y auditable en Git).
    No se descarga ni se crea por script. Si falta, el Actor falla con un mensaje claro.

Cada archivo es un Pipeline de scikit-learn (transformaciones + Random Forest) guardado con
joblib en el Colab (Módulo 5). Recibe las columnas tal como salen de analytics y predice el
objetivo en log1p, así que se vuelve a la escala original con expm1.
"""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd

CARPETA = Path(__file__).resolve().parent.parent / "modelos"

MODELO_ML = "modelo_ml.pkl"
FEATURES_ML = ["peso_total_kg", "unidades_pack", "envio_gratis", "descuento_pct", "categoria"]

MODELO_MAPS = "modelo_maps.pkl"
FEATURES_MAPS = ["cantidad_fotos", "sin_tacc_2km", "sin_tacc_busqueda", "sin_tacc_confirmado",
                 "calificacion", "tipo_local", "provincia"]


def cargar(nombre: str, carpeta: Path = CARPETA):
    ruta = carpeta / nombre
    if not ruta.exists():
        raise FileNotFoundError(
            f"Falta el modelo {ruta.name} en {carpeta.name}/. Lo entrena Data Science en el Colab "
            f"(Módulo 5) y se sube al repo; el Actor no lo descarga ni lo entrena (R2 y R3).")
    return joblib.load(ruta)


def predecir(pipeline, df: pd.DataFrame, features: list[str]) -> pd.Series:
    """Predicción en la escala original (expm1 de la salida en log1p)."""
    faltan = [c for c in features if c not in df.columns]
    if faltan:
        raise ValueError(f"Faltan columnas para el modelo: {faltan}")
    return pd.Series(np.expm1(pipeline.predict(df[features])), index=df.index)
