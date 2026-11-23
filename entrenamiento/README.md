# entrenamiento/ (fuera del Actor)

El Actor de Apify es **solo de inferencia**: acá vive el entrenamiento, que nunca entra a la imagen del Actor (el build de Apify usa solo la carpeta `sintacc-actor`).

`comparar_modelos.py` compara los **5 candidatos** que pide la consigna, con los mismos datos y el mismo preprocesamiento que el Colab:

| Candidato | Modelo |
|---|---|
| Clásico 1 | Ridge (regresión lineal regularizada) |
| Clásico 2 | Árbol de decisión |
| Ensamble 1 | Random Forest |
| Ensamble 2 | Gradient Boosting |
| Red | MLPRegressor (scikit-learn) |

**Métrica:** es regresión, así que no se usa accuracy. Se elige con validación cruzada de 5 partes **dentro del 90 % de trabajo** (R² en log y MAE / RMSE en la escala original). El 10 % reservado se usa **una sola vez**, para reportar, nunca para elegir.

```bash
pip install -r sintacc-actor/requirements-dev.txt
python entrenamiento/comparar_modelos.py ml_sintacc_unificado.csv maps_unificado.csv            # compara
python entrenamiento/comparar_modelos.py ml_sintacc_unificado.csv maps_unificado.csv --exportar # + exporta el mejor a modelos/
```

Los resultados de la última corrida están en `resultados.json`.
