# modelos/

Modelos ya entrenados que usa la operación `inference` (Producto 2). El Actor **no entrena** (R2) y **no descarga** el modelo (R3): los carga desde esta carpeta, con una versión fija y auditable en Git. Si falta un archivo, el Actor falla con un mensaje claro.

| Archivo | Qué predice | Entrada (columnas tal como salen de `analytics`) | Modelo |
|---|---|---|---|
| `modelo_ml.pkl` | log1p(precio) → el Actor aplica expm1 | peso_total_kg, unidades_pack, envio_gratis, descuento_pct, categoria | Pipeline: log1p + columnas 0/1 + Random Forest (200 árboles, semilla 42) |
| `modelo_maps.pkl` | log1p(reseñas) | cantidad_fotos, sin_tacc_2km, sin_tacc_busqueda, sin_tacc_confirmado, calificacion, tipo_local, provincia | Pipeline: log1p + columnas 0/1 + Random Forest |

- **Origen:** Colab DataPatitos, Módulo 5 (Data Science, 22/11), exportados con joblib.
- **Versión:** scikit-learn **1.6.1**. `requirements.txt` fija la misma versión; si cambia, el archivo puede no cargar.
- **Verificación (23/11):** con los datos que genera el Actor, `modelo_ml.pkl` da R² 0,744 en el 10 % reservado, igual que en el Colab.

**Cómo se reemplaza un modelo:** reentrenar fuera del Actor (Colab o `entrenamiento/comparar_modelos.py --exportar`) → reemplazar el archivo acá → correr los tests → commit → build en Apify.
