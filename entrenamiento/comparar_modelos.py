"""Comparación de 5 modelos candidatos (pedido de la profe) — FUERA del Actor.

El Actor de Apify es solo de inferencia (R2): no entrena ni incluye batch iterators.
Este script corre en la compu o en el Colab, elige el mejor modelo y lo exporta a
sintacc-actor/modelos/ para que el Actor solo lo cargue (R3).

Candidatos (los mismos para los dos problemas):
  1. Clásico 1   Ridge (regresión lineal regularizada)
  2. Clásico 2   Árbol de decisión
  3. Ensamble 1  Random Forest (el modelo actual de DS)
  4. Ensamble 2  Gradient Boosting
  5. Red         MLPRegressor de scikit-learn

Métrica: es regresión, así que no se usa accuracy. Se elige con validación cruzada de 5 partes
DENTRO del 90 % de trabajo (R² en log y MAE en la escala original). El 10 % reservado se usa
una sola vez, al final, para reportar el modelo elegido sin haberlo mirado para elegir.

Uso:
    python entrenamiento/comparar_modelos.py ml_sintacc_unificado.csv maps_unificado.csv [--exportar]
"""

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeRegressor

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "sintacc-actor"))
from src import etl_maps, etl_ml  # noqa: E402  (mismo ETL que el Actor: mismos datos que el Colab)

SEMILLA = 42

PROBLEMAS = {
    "ml": {
        "objetivo": "precio", "archivo": "modelo_ml.pkl",
        "log": ["peso_total_kg", "unidades_pack"], "num": ["envio_gratis", "descuento_pct"],
        "cat": ["categoria"],
    },
    "maps": {
        "objetivo": "resenas", "archivo": "modelo_maps.pkl",
        "log": ["cantidad_fotos"],
        "num": ["sin_tacc_2km", "sin_tacc_busqueda", "sin_tacc_confirmado", "calificacion"],
        "cat": ["tipo_local", "provincia"],
    },
}


def preprocesamiento(p: dict, escalar: bool) -> ColumnTransformer:
    """El mismo que el Pipeline de DS (log1p + 0/1 por categoría). Ridge y MLP además escalan."""
    log = [FunctionTransformer(np.log1p, feature_names_out="one-to-one")]
    num = [FunctionTransformer(feature_names_out="one-to-one")]
    if escalar:
        log.append(StandardScaler())
        num.append(StandardScaler())
    return ColumnTransformer([
        ("log", Pipeline([(f"p{i}", t) for i, t in enumerate(log)]), p["log"]),
        ("num", Pipeline([(f"p{i}", t) for i, t in enumerate(num)]), p["num"]),
        ("cat", OneHotEncoder(handle_unknown="ignore"), p["cat"]),
    ])


def candidatos(p: dict) -> dict:
    return {
        "Clásico 1 · Ridge": Pipeline([("pre", preprocesamiento(p, True)), ("modelo", Ridge(alpha=1.0))]),
        "Clásico 2 · Árbol de decisión": Pipeline([("pre", preprocesamiento(p, False)), (
            "modelo", DecisionTreeRegressor(min_samples_leaf=5, random_state=SEMILLA))]),
        "Ensamble 1 · Random Forest": Pipeline([("pre", preprocesamiento(p, False)), (
            "modelo", RandomForestRegressor(n_estimators=200, random_state=SEMILLA, n_jobs=-1))]),
        "Ensamble 2 · Gradient Boosting": Pipeline([("pre", preprocesamiento(p, False)), (
            "modelo", GradientBoostingRegressor(random_state=SEMILLA))]),
        "Red · MLP": Pipeline([("pre", preprocesamiento(p, True)), ("modelo", MLPRegressor(
            hidden_layer_sizes=(32, 16), alpha=1e-3, max_iter=3000, early_stopping=True,
            random_state=SEMILLA))]),
    }


def _metricas(y_log: pd.Series, pred_log: np.ndarray) -> dict:
    real, pred = np.expm1(y_log), np.expm1(pred_log)
    return {"r2_log": round(r2_score(y_log, pred_log), 3),
            "mae": round(mean_absolute_error(real, pred), 1),
            "rmse": round(float(np.sqrt(mean_squared_error(real, pred))), 1)}


def comparar(df: pd.DataFrame, nombre: str) -> dict:
    p = PROBLEMAS[nombre]
    features = p["log"] + p["num"] + p["cat"]
    trabajo, reservado = df[df["muestra"] == "trabajo"], df[df["muestra"] == "reservado"]
    y_tr, y_res = np.log1p(trabajo[p["objetivo"]]), np.log1p(reservado[p["objetivo"]])
    cv = KFold(n_splits=5, shuffle=True, random_state=SEMILLA)

    tabla = {}
    for etiqueta, modelo in candidatos(p).items():
        pred = cross_val_predict(modelo, trabajo[features], y_tr, cv=cv)
        tabla[etiqueta] = {"cv": _metricas(y_tr, pred)}
    # Elección: mayor R² en validación cruzada; desempate por menor MAE
    mejor = max(tabla, key=lambda k: (tabla[k]["cv"]["r2_log"], -tabla[k]["cv"]["mae"]))
    for etiqueta, modelo in candidatos(p).items():  # reservado: se reporta, no se usa para elegir
        ajustado = modelo.fit(trabajo[features], y_tr)
        tabla[etiqueta]["reservado"] = _metricas(y_res, ajustado.predict(reservado[features]))
        if etiqueta == mejor:
            tabla[etiqueta]["modelo"] = ajustado
    return {"tabla": tabla, "mejor": mejor, "n": {"trabajo": len(trabajo), "reservado": len(reservado)}}


def main(ml_csv: str, maps_csv: str, exportar: bool) -> None:
    ml = etl_ml.procesar(pd.read_csv(ml_csv, low_memory=False))
    maps, _ = etl_maps.procesar(pd.read_csv(maps_csv, low_memory=False))
    informe = {}
    for nombre, df in [("ml", ml), ("maps", maps)]:
        r = comparar(df, nombre)
        print(f"\n=== {nombre} (objetivo log1p {PROBLEMAS[nombre]['objetivo']}) · n = {r['n']} ===")
        print(f"{'Modelo':32} {'R² CV':>7} {'MAE CV':>9} {'RMSE CV':>9} | {'R² 10%':>7} {'MAE 10%':>9} {'RMSE 10%':>9}")
        for etiqueta, m in r["tabla"].items():
            cv, res = m["cv"], m["reservado"]
            marca = "  ← mejor" if etiqueta == r["mejor"] else ""
            print(f"{etiqueta:32} {cv['r2_log']:>7} {cv['mae']:>9} {cv['rmse']:>9} | "
                  f"{res['r2_log']:>7} {res['mae']:>9} {res['rmse']:>9}{marca}")
        informe[nombre] = {"mejor": r["mejor"], "n": r["n"],
                           "tabla": {k: {"cv": v["cv"], "reservado": v["reservado"]} for k, v in r["tabla"].items()}}
        if exportar:
            destino = RAIZ / "sintacc-actor" / "modelos" / PROBLEMAS[nombre]["archivo"]
            joblib.dump(r["tabla"][r["mejor"]]["modelo"], destino, compress=3)
            print(f"Exportado: {destino.relative_to(RAIZ)}")
    salida = RAIZ / "entrenamiento" / "resultados.json"
    salida.write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nResultados en {salida.relative_to(RAIZ)}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 2:
        sys.exit(__doc__)
    main(args[0], args[1], "--exportar" in sys.argv)
