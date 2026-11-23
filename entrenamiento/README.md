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

**Métrica:** es regresión, así que no se usa accuracy. Se elige con validación cruzada de 5 partes **dentro del 90 % de trabajo** (R² en log y MAE / RMSE en la escala original). Cada candidato se evalúa **una sola vez** en el 10 % reservado, para reportar; la elección se hace por validación cruzada, nunca por el 10 %.

**Modelo en uso: Random Forest** (decisión de la DS). En la validación, Random Forest y Gradient Boosting quedan empatados (0,840 contra 0,845, dentro del ruido entre semillas), así que se mantuvo el RF: ya estaba exportado, reproduce el R² del Colab y es el mejor en Google Maps. Por eso `resultados.json` dice "mejor: Gradient Boosting" (el script desempata solo por R²), pero el Actor usa el RF. **Ojo:** `--exportar` reemplaza `modelos/modelo_ml.pkl` por el "mejor" del script; no correrlo sin acordarlo con la DS.

```bash
pip install -r sintacc-actor/requirements-dev.txt
python entrenamiento/comparar_modelos.py ml_sintacc_unificado.csv maps_unificado.csv            # compara
python entrenamiento/comparar_modelos.py ml_sintacc_unificado.csv maps_unificado.csv --exportar # + exporta el mejor a modelos/
```

Los resultados de la última corrida están en `resultados.json`.
