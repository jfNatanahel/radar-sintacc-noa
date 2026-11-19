# Inteligencia competitiva sin TACC · NOA

Actor de Apify que responde, para el rubro sin TACC en Salta, Jujuy y La Rioja:

- **¿Cuánto cuesta el kilo de cada insumo sin TACC y cuánto se ahorra comprando por mayor?** (Mercado Libre)
- **¿Qué locales ofrecen sin TACC y dónde no hay oferta?** (Google Maps)

Un Actor, dos operaciones:

| `operation` | Producto | Qué hace |
|---|---|---|
| `analytics` | Producto 1 | Extracción → ETL → EDA → tablas limpias + indicadores para el dashboard |
| `inference` | Producto 2 | (en desarrollo) |

## Arquitectura

```
Make (programado, semanal)
  └─> Actor  {operation: "analytics"}
        extraer.py   CSV del key-value store `radar-sintacc-entrada`  ó  extractores de Apify (Mercado Libre + Google Maps)
        etl_ml.py    limpieza + exclusiones + correcciones manuales + features + precio/kg + outliers
        etl_maps.py  limpieza + features + sin TACC (confirmado / por búsqueda) + competencia a 2 km
        muestra.py   90 % de trabajo / 10 % reservado (semilla 42, por grupo), igual que el Colab
        eda.py       indicadores de negocio
        reglas.py    reglas de negocio (palabras clave, umbrales, provincias), separadas del código
        salida.py    filas del dataset e historial de precios
  └─> Dataset (filas con columna `tabla`)
  └─> Key-value store `radar-sintacc` (URL fija): productos.csv, locales.csv, historial_kpi.csv, RESUMEN
        └─> Google Sheets (IMPORTDATA) ──> AppSheet
```

## Input

| Parámetro | Default | Descripción |
|---|---|---|
| `operation` | `analytics` | `analytics` o `inference` |
| `source` | `csv` | `csv`: los CSV del 12/11 guardados en el key-value store `radar-sintacc-entrada` (demo, casi sin costo). `apify`: extracción nueva |
| `mlActorId` / `mlInput` | — | Extractor de Mercado Libre y su input, con `{busqueda}` donde va el texto (fuente `apify`) |
| `productos` | los 5 | premezcla, harina, fideos, rebozador, pan |
| `provincias` | las 3 | Salta, Jujuy, La Rioja (se busca en la capital) |
| `maxPorBusqueda` | 40 | Locales por búsqueda en Google Maps (controla el costo) |

```json
{
  "operation": "analytics",
  "source": "csv"
}
```

## Output

**Dataset**: una fila por registro; la columna `tabla` indica a qué tabla pertenece:

- `productos`: una publicación limpia. Columna `muestra` = `trabajo` (90 %) o `reservado` (10 %).
  - Features del modelo (5): `peso_log`, `unidades_log`, `envio_gratis`, `descuento_pct`, `categoria`. Objetivo: `log1p(precio)`.
  - Para el dashboard: `venta_por_mayor`, `cantidad_vendida`, `cantidad_evaluaciones`, `tienda_oficial`, `precio_por_kg`, `peso_imputado`, `outlier_precio_kg` (y `peso_total_kg`, `unidades_pack`, `stock_bajo`).
- `locales`: un local limpio, con `muestra`.
  - Features del modelo (7): `fotos_log`, `sin_tacc_2km`, `sin_tacc_busqueda`, `sin_tacc_confirmado`, `calificacion`, `tipo_local`, `provincia`. Objetivo: `log1p(resenas)`.
  - Para el dashboard: `latitud`, `longitud`, `resenas`, `grupo_sin_tacc` (confirmado / busqueda / ninguno, para el color del mapa).
- `kpi_categoria`: precio/kg minorista y mayorista y % de ahorro por categoría
- `kpi_provincia`: locales y % con sin TACC confirmado por provincia
- `kpi_demanda`: mediana de reseñas por grupo sin TACC, total y por provincia

`tipo_local`, `provincia` y `categoria` se pasan a columnas de 0 y 1 recién al entrenar el modelo (Producto 2). Al evaluar con el 10 % reservado se aplican las mismas transformaciones.

Todas llevan `fecha_corrida`: cada ejecución semanal suma historia, y eso permite ver cambios de precio.

**Key-value store**: `RESUMEN` (todos los indicadores en JSON, incluidos los más vendidos y las zonas sin oferta, y los números de `controles`), `productos.csv` y `locales.csv`.

Con los CSV del 12/11 los controles tienen que dar lo mismo que el Colab: 831 publicaciones (748 de trabajo, 91 por mayor, 85 con peso imputado, 19 outliers) y 407 locales (366 de trabajo, 10 confirmados, 90 por búsqueda). Lo verifica `tests/test_controles.py`.

## Decisiones de datos

Todas acordadas con Data Science (registro de decisiones en la Documentación del CAPSTONE, 15/11 y 16/11).

- **Orden:** limpieza → sorteo del 10 % → exclusiones → lectura del título → correcciones manuales → venta por mayor → peso faltante → precio/kg → outliers.
- **Peso y pack** salen del título con reglas (`parseo.py`), probadas con títulos reales en `tests/test_parseo.py`. En "3 x 5 kg" el peso es el de una unidad. Si el peso de una unidad no figura, se completa con la mediana de su categoría (calculada solo con el 90 %) y queda marcado en `peso_imputado`.
- **Correcciones manuales y exclusiones** (13 publicaciones corregidas y 8 excluidas, revisadas una por una) están en `reglas.py`, por código de publicación.
- **Precio/kg** se usa para el análisis, no como feature del modelo (depende del precio, que es la variable objetivo). Se marca `outlier_precio_kg` con límites fijos por categoría (`reglas.LIMITES_PRECIO_KG`); no se elimina ninguna fila y los marcados no entran en los indicadores.
- **Sin TACC** tiene dos niveles. Es *confirmado* si el nombre o la categoría lo dicen. Es *por búsqueda* si el local solo apareció al buscar "sin tacc" en Google, que también devuelve locales cercanos no aptos. La competencia a 2 km cuenta solo los confirmados.
- Si un extractor devuelve 0 filas o le faltan columnas (por ejemplo, porque cambió la página), el Actor falla con un mensaje claro en lugar de publicar datos rotos.

## Limitaciones

- Mercado Libre no informa la provincia del vendedor: los precios son de referencia nacional.
- "Sin TACC" en Mercado Libre no garantiza certificación ANMAT.
- La cantidad de reseñas mide popularidad, no ventas.
- Solo se cubren las capitales, y Jujuy concentra la mayoría de los locales.

## Lineamientos del Actor (R1 a R4)

| Regla | Qué exige | Cómo se cumple |
|---|---|---|
| R1 · Carga de datos | Datos solo por el SDK de Apify | `source: csv` lee el key-value store `radar-sintacc-entrada`; `source: apify` usa `Actor.call`. Sin urllib, requests, httpx ni open(). El input no acepta URLs. |
| R2 · Entrenamiento | El Actor no entrena | No hay ningún `fit`. Se entrena en el Colab. |
| R3 · Carga del modelo | El modelo ya está en una carpeta | `modelos/` (ver su README). No se descarga ni se crea por script. |
| R4 · Estructura | `main.py` solo arma el Actor | `main.py` lee la entrada, llama a los módulos y publica. La lógica está en `extraer`, `etl_*`, `eda` y `salida`. |

`tests/test_lineamientos.py` revisa el código fuente y falla si alguna regla se rompe. Detalle en `docs/lineamientos.md` del repo.

## Correr localmente

```bash
pip install -r requirements-dev.txt
python -m pytest -q                                   # parseo, salida y lineamientos
RADAR_ML_CSV=ml.csv RADAR_MAPS_CSV=maps.csv python -m pytest -q   # + controles contra el Colab
```

### Cargar los CSV del 12/11 en Apify (una sola vez)

```bash
export APIFY_TOKEN=...      # nunca en el código
python scripts/subir_csv_a_apify.py ml_sintacc_unificado.csv maps_unificado.csv
```

Después, el Actor se corre con `{"operation": "analytics", "source": "csv"}`.

## Estructura

```
.actor/        actor.json, input_schema.json
src/           main.py (solo arma el Actor)
               extraer.py · etl_ml.py · etl_maps.py · muestra.py · parseo.py · eda.py · salida.py
               reglas.py (reglas de negocio)
modelos/       modelos ya entrenados para inference (Producto 2)
scripts/       subir_csv_a_apify.py (se corre fuera del Actor)
tests/         test_parseo.py · test_controles.py · test_salida.py · test_lineamientos.py
requirements.txt (imagen del Actor) · requirements-dev.txt (tests y scripts)
```
