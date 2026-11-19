# Cumplimiento de lineamientos del Actor

Actor: `sintacc-actor` (Radar Sin TACC) · Punto de entrada: `src/main.py` · Revisión: 19/11/2026

## Resumen

El diagnóstico del 19/11 sobre el commit `ffdbc02` encontró dos incumplimientos. R1: la fuente `csv` bajaba los CSV desde Google Drive con `httpx`. R4: `main.py` tenía funciones de lógica. Los dos quedaron corregidos. R2 se cumple (el Actor no entrena). R3 se deja resuelta en el diseño de la operación `inference` (carpeta `modelos/`). Las cuatro reglas se controlan con `tests/test_lineamientos.py`.

| Regla | Qué exige | Antes (ffdbc02) | Ahora |
|---|---|---|---|
| R1 · Carga de datos | Datos solo por el SDK de Apify, sin urllib, requests, open() ni scraping de fuentes externas | INCUMPLE | CUMPLE |
| R2 · Entrenamiento | El modelo no se entrena dentro del Actor | CUMPLE | CUMPLE |
| R3 · Creación y carga | El modelo ya existe en la carpeta; no se crea ni se descarga | NO APLICA (sin modelo) | Diseñado: `modelos/` |
| R4 · Estructura | `main.py` solo arma el Actor e importa la lógica | PARCIAL | CUMPLE |

## R1 · Carga de datos

- **Hallazgo:** `extraer.py` (líneas 27–33) descargaba los CSV con `httpx.AsyncClient().get(...)` a partir de links de Drive que venían en el input (`mlCsvUrl`, `mapsCsvUrl`). Con una ruta local usaba `pd.read_csv(ruta)`. Además, el input permitía apuntar el Actor a cualquier URL.
- **Corrección:** los CSV del 12/11 se suben una sola vez al key-value store `radar-sintacc-entrada` con `scripts/subir_csv_a_apify.py`, que corre fuera del Actor. El Actor los lee con `Actor.open_key_value_store(name=...)`. Se eliminaron `httpx`, `_url_descarga`, `leer_csv` y los campos `mlCsvUrl` y `mapsCsvUrl`. Si falta un archivo, el Actor falla con un mensaje que dice cómo cargarlo.
- **Sin cambios:** la fuente `apify` ya cumplía (usa `Actor.call` y `Actor.apify_client`).

## R2 · Entrenamiento

- No hay ninguna llamada a `fit` en `src/`. El entrenamiento del Producto 2 se hace en el Colab con el 90 % de trabajo.

## R3 · Creación y carga del modelo

- La operación `inference` todavía no existe (falla con un mensaje claro).
- Diseño: el modelo entrenado se guarda en `sintacc-actor/modelos/` y entra al repo. El Actor lo carga desde una ruta fija relativa al código. No hay URL de modelo en el input. Ver `modelos/README.md`.

## R4 · Estructura

- **Hallazgo:** `main.py` tenía `obtener_datos` (elegir la fuente y validar columnas), `_filas` (transformar a filas del dataset) y la unión del historial con pandas dentro de `publicar`.
- **Corrección:**
  - `obtener_datos` pasó a `extraer.py`.
  - `_filas` y la unión del historial pasaron al módulo nuevo `salida.py`, con funciones puras y probadas en `tests/test_salida.py`.
  - `main.py` quedó con `main` y `analytics`: lee la entrada, llama a los módulos, publica con `push_data` y `set_value` e informa con `set_status_message` y el log. No importa pandas.

## Control automático

`tests/test_lineamientos.py` analiza el código fuente:

- R1: ningún módulo de `src/` importa `urllib`, `requests`, `httpx`, `aiohttp` ni `urllib3`, ni llama a `open()`.
- R2: no hay llamadas a `fit`, `fit_transform` ni `partial_fit`.
- R4: `main.py` solo define `main`, `analytics` o `inference`, y no importa pandas.

Se comprobó que estos tests fallan con el código anterior (R1 y R4) y pasan con el actual.

## Impacto operativo

- **Una vez:** correr `scripts/subir_csv_a_apify.py` con el token de Apify (variable de entorno, nunca en el código).
- **Make:** el módulo "Run an Actor" manda `{"operation": "analytics", "source": "csv"}`. Los campos `mlCsvUrl` y `mapsCsvUrl` ya no se usan y se pueden borrar del escenario.
- **Imagen del Actor:** `httpx` y `pytest` salieron de `requirements.txt`. Las herramientas de desarrollo están en `requirements-dev.txt`, y los tests y scripts quedan fuera de la imagen (`.dockerignore`).
