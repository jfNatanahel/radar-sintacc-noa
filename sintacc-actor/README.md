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
        extraer.py   CSV de Drive  ó  extractores de Apify (Mercado Libre + Google Maps)
        etl_ml.py    limpieza + 10 features + precio/kg + outliers
        etl_maps.py  limpieza + features + sin TACC (confirmado / por búsqueda) + competencia a 2 km
        eda.py       indicadores de negocio
        reglas.py    reglas de negocio (palabras clave, umbrales, provincias), separadas del código
  └─> Dataset (filas con columna `tabla`) ──> Make ──> Google Sheets ──> Tableau
  └─> Key-value store: RESUMEN (JSON), productos.csv, locales.csv
```

## Input

| Parámetro | Default | Descripción |
|---|---|---|
| `operation` | `analytics` | `analytics` o `inference` |
| `source` | `csv` | `csv`: lee CSV ya extraídos (demo, casi sin costo). `apify`: extracción nueva |
| `mlCsvUrl` / `mapsCsvUrl` | — | Links públicos a los CSV unificados (fuente `csv`) |
| `mlActorId` / `mlInput` | — | Extractor de Mercado Libre y su input, con `{busqueda}` donde va el texto (fuente `apify`) |
| `productos` | los 5 | premezcla, harina, fideos, rebozador, pan |
| `provincias` | las 3 | Salta, Jujuy, La Rioja (se busca en la capital) |
| `maxPorBusqueda` | 40 | Locales por búsqueda en Google Maps (controla el costo) |

```json
{
  "operation": "analytics",
  "source": "csv",
  "mlCsvUrl": "https://drive.google.com/file/d/<id>/view",
  "mapsCsvUrl": "https://drive.google.com/file/d/<id>/view"
}
```

## Output

**Dataset**: una fila por registro; la columna `tabla` indica a qué tabla pertenece:

- `productos`: publicación limpia con features, `precio_por_kg`, `peso_imputado` y `outlier_precio_kg`
- `locales`: local limpio con `sin_tacc_confirmado`, `sin_tacc_busqueda`, `sin_tacc_2km` y `locales_2km`
- `kpi_categoria`: precio/kg minorista y mayorista y % de ahorro por categoría
- `kpi_provincia`: locales y % con sin TACC confirmado por provincia

Todas llevan `fecha_corrida`: cada ejecución semanal suma historia, y eso permite ver cambios de precio.

**Key-value store**: `RESUMEN` (todos los indicadores en JSON, incluidos los más vendidos y las zonas sin oferta), `productos.csv` y `locales.csv`.

## Decisiones de datos

- **Peso y pack** salen del título con reglas (`parseo.py`), probadas con títulos reales en `tests/test_parseo.py`. Si el peso de una unidad no figura o es imposible, se completa con la mediana de su categoría y queda marcado en `peso_imputado`.
- **Precio/kg** se usa para el análisis, no como feature del modelo (depende del precio, que es la variable objetivo). Los valores fuera del rango intercuartílico de su categoría se marcan en `outlier_precio_kg` y no entran en los indicadores.
- **Sin TACC** tiene dos niveles. Es *confirmado* si el nombre o la categoría lo dicen. Es *por búsqueda* si el local solo apareció al buscar "sin tacc" en Google, que también devuelve locales cercanos no aptos. La competencia a 2 km cuenta solo los confirmados.
- Si un extractor devuelve 0 filas o le faltan columnas (por ejemplo, porque cambió la página), el Actor falla con un mensaje claro en lugar de publicar datos rotos.

## Limitaciones

- Mercado Libre no informa la provincia del vendedor: los precios son de referencia nacional.
- "Sin TACC" en Mercado Libre no garantiza certificación ANMAT.
- La cantidad de reseñas mide popularidad, no ventas.
- Solo se cubren las capitales, y Jujuy concentra la mayoría de los locales.

## Correr localmente

```bash
pip install -r requirements.txt
python -m pytest -q          # tests de parseo
apify run --input '{"operation":"analytics","source":"csv","mlCsvUrl":"data/ml.csv","mapsCsvUrl":"data/maps.csv"}'
```

## Estructura

```
.actor/        actor.json, input_schema.json
src/           main.py · extraer.py · etl_ml.py · etl_maps.py · eda.py · parseo.py · reglas.py
tests/         test_parseo.py
```
