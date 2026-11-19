# modelos/

Acá van los modelos ya entrenados que usa la operación `inference` (Producto 2).

Reglas (lineamientos del Actor):

- **R2:** el Actor no entrena. El entrenamiento se hace en el Colab (Data Science) con el 90 % de trabajo.
- **R3:** el archivo del modelo vive en esta carpeta y entra al repo. El Actor lo carga desde una ruta fija
  (`Path(__file__).parent.parent / "modelos" / ...`), nunca lo descarga ni lo crea. Si falta, falla con un mensaje claro.

Para cambiar el modelo: reentrenar en el Colab → exportar el archivo → reemplazarlo acá → commit → build en Apify.
Cada versión del modelo queda fija y auditable en el historial de Git.

Archivos esperados (a definir con DS):

| Archivo | Objetivo | Features |
|---|---|---|
| `modelo_ml.pkl` | log1p(precio) | peso_log, unidades_log, envio_gratis, descuento_pct, categoria |
| `modelo_maps.pkl` | log1p(resenas) | fotos_log, sin_tacc_2km, sin_tacc_busqueda, sin_tacc_confirmado, calificacion, tipo_local, provincia |
