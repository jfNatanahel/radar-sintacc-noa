# Inteligencia competitiva sin TACC · NOA

Actor de Apify que responde, para el rubro sin TACC en Salta, Jujuy y La Rioja:

- **¿Cuánto cuesta el kilo de cada insumo sin TACC y cuánto se ahorra comprando por mayor?** (Mercado Libre)
- **¿Qué locales ofrecen sin TACC y dónde no hay oferta?** (Google Maps)

Un Actor, dos operaciones:

| `operation` | Producto | Qué hace |
|---|---|---|
| `analytics` | Producto 1 | Extracción → ETL → EDA → tablas limpias + indicadores para el dashboard |
| `inference` | Producto 2 | Semáforo de compra por publicación (verde / amarillo / rojo / revisar) a partir de la última salida de `analytics` |

## Arquitectura

```
Make (programado, semanal) · 6 operaciones por corrida
  1. Actor {operation: "analytics", source: "csv", csvStore: <ID>}
       extraer.py    CSV del store de entrada (por ID, solo lectura)  ó  extractores de Apify
       etl_ml.py     limpieza + exclusiones + correcciones manuales + features + precio/kg + outliers
       etl_maps.py   limpieza + features + sin TACC (confirmado / por búsqueda) + competencia a 2 km
       muestra.py    90 % de trabajo / 10 % reservado (semilla 42, por grupo), igual que el Colab
       eda.py        indicadores de negocio
       salida.py     filas del dataset e historial de precios
     └─> store `radar-sintacc`: productos.csv, locales.csv, historial_kpi.csv, RESUMEN
  2. Actor {operation: "inference"}
       inferencia.py semáforo de compra (lee productos.csv del paso 1)
     └─> store `radar-sintacc`: insights.csv, RESUMEN_INFERENCE
  3. Google Sheets (IMPORTDATA, una pestaña por archivo) ──> AppSheet (dashboard e insights)

  reglas.py: reglas de negocio (palabras clave, correcciones, límites, umbrales), separadas del código
  Filtro status = SUCCEEDED y Rollback: si el Actor falla, la Sheet no se toca
```

## Input

| Parámetro | Default | Descripción |
|---|---|---|
| `operation` | `analytics` | `analytics` o `inference` |
| `source` | `csv` | `csv`: los CSV del 12/11 guardados en el key-value store `radar-sintacc-entrada` (demo, casi sin costo). `apify`: extracción nueva |
| `csvStore` | — | ID del store `radar-sintacc-entrada` (fuente `csv`). Hace falta porque el Actor corre con **permisos limitados**: solo lee los stores que creó él o los que se le pasan en la entrada (solo lectura) |
| `mlActorId` / `mlInput` | — | Extractor de Mercado Libre y su input, con `{busqueda}` donde va el texto (fuente `apify`) |
| `productos` | los 5 | premezcla, harina, fideos, rebozador, pan |
| `provincias` | las 3 | Salta, Jujuy, La Rioja (se busca en la capital) |
| `maxPorBusqueda` | 40 | Locales por búsqueda en Google Maps (controla el costo) |

```json
{
  "operation": "analytics",
  "source": "csv",
  "csvStore": "<ID del store radar-sintacc-entrada>"
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

## Producto 2: operación `inference`

Lee `productos.csv` y `locales.csv` del store `radar-sintacc` (lo que dejó la última corrida de `analytics`) y aplica los modelos de Data Science, que están en `modelos/` (ver su README). No entrena (R2) ni descarga los modelos (R3).

**Semáforo de compra** (modelo de precio, `metodo = modelo_random_forest`): para cada publicación, el modelo calcula el **precio esperado** según su peso total, las unidades del pack, la categoría, el envío gratis y el descuento. Después lo compara con el precio real:

| Color | Cuándo | Para el cliente |
|---|---|---|
| verde | precio al menos 25 % por debajo del esperado (0,75 veces) | oportunidad de compra |
| amarillo | entre los dos umbrales | precio acorde |
| rojo | al menos 33 % por encima (1,33 veces = 1 ÷ 0,75) | cara |
| revisar | peso estimado o precio por kg fuera de rango | el precio por kg no es confiable |

**Plan B** (`{"operation": "inference", "metodo": "mediana"}`, `metodo = mediana_categoria`): compara contra la mediana del precio por kg de su categoría y tipo de venta (90 % de trabajo, sin outliers). Sirve si el modelo no está disponible. Mezcla productos distintos dentro de una categoría, por eso el método principal es el modelo.

**Popularidad de locales** (modelo de reseñas): compara las reseñas reales de cada local con las esperadas según sus fotos, su calificación, su oferta sin TACC, su tipo y su provincia. "Por encima de lo esperado" quiere decir el doble o más; "por debajo", la mitad o menos.

**Salida:**
- **Dataset:** filas con `tabla = insights` y `tabla = popularidad`.
- **Archivos:** `insights.csv`, `popularidad.csv` y `RESUMEN_INFERENCE`, en el store de la corrida y en `radar-sintacc`.
- **Columnas de insights:** `idPublicacion`, `articuloTitulo`, `categoria`, `venta_por_mayor`, `muestra`, `precio`, `precio_esperado`, `precio_por_kg`, `referencia_kg` (esperado por kg), `diferencia_pct`, `ahorro_por_kg`, `semaforo`, `motivo`, `metodo`.

**Salvedades:**
- Es un **ahorro potencial**, no demostrado: lo verde es más barato porque se eligió por barato.
- El modelo se entrenó con el 90 % de trabajo. En esas publicaciones el precio esperado se parece más al real, así que el semáforo es conservador.

## Uso por API

**Documentación (GET):** este README es la documentación del Actor; también se obtiene por API:

```bash
curl "https://api.apify.com/v2/acts/jfnatanahel~radar-sintacc-noa?token=$APIFY_TOKEN"
```

**Ejecutar (POST)** y recibir los resultados en la misma respuesta:

```bash
# Producto 1: ETL + EDA
curl -X POST "https://api.apify.com/v2/acts/jfnatanahel~radar-sintacc-noa/run-sync-get-dataset-items?token=$APIFY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"operation": "analytics", "source": "csv", "csvStore": "<ID del store de entrada>"}'

# Producto 2: semáforo de compra (usa la última salida de analytics)
curl -X POST "https://api.apify.com/v2/acts/jfnatanahel~radar-sintacc-noa/run-sync-get-dataset-items?token=$APIFY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"operation": "inference"}'
```

El token va siempre en una variable de entorno, nunca en el código.

## Costos

| Operación | Tiempo | Costo por corrida | Por mes (semanal) |
|---|---|---|---|
| `analytics` (fuente csv) | 4 a 8 s | USD 0,007 (medido en 5 corridas, 17/11) | ≈ USD 0,03 |
| `inference` | ≈ 5 s | USD 0,005 (medido, 19/11) | ≈ USD 0,02 |
| Make | 6 operaciones | plan gratis (1.000 por mes) | ≈ 26 operaciones |

Entra en el crédito gratis de Apify (USD 5 por mes). La fuente `apify` (extracción nueva) suma el costo de los extractores de Mercado Libre y Google Maps, que todavía no se midió. El precio de venta por corrida (Apify Store) se define con el modelo de negocio; referencia de clase: costo × 2,5 (margen del 60 %).

## Decisiones de datos

Todas acordadas con Data Science (registro de decisiones en la Documentación del CAPSTONE, 15/11 y 16/11).

- **Orden:** limpieza → sorteo del 10 % → exclusiones → lectura del título → correcciones manuales → venta por mayor → peso faltante → precio/kg → outliers.
- **Categoría** = la clasificación de Mercado Libre (`produtoDomainID`: pastas → fideos, harinas → harina, panes → pan, premezclas dulces y saladas → premezcla, pan rallado → rebozador), más 4 féculas que van a harina (DS, 18/11). La palabra de búsqueda metía ruido (fécula y harina de arveja caían en "pan"). Se conserva en `categoria_busqueda`, porque el sorteo 90/10 se hace con ella y así el 10 % reservado es el mismo que en el Colab.
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
.actor/        actor.json, input_schema.json, output_schema.json, dataset_schema.json (vistas del Output)
src/           main.py (solo arma el Actor)
               extraer.py · etl_ml.py · etl_maps.py · muestra.py · parseo.py · eda.py · salida.py · inferencia.py
               reglas.py (reglas de negocio)
modelos/       modelos ya entrenados para inference (Producto 2)
scripts/       subir_csv_a_apify.py (se corre fuera del Actor)
tests/         test_parseo.py · test_controles.py · test_salida.py · test_inferencia.py · test_lineamientos.py · test_esquemas.py
requirements.txt (imagen del Actor, versiones fijas) · requirements-dev.txt (tests y scripts)
```
