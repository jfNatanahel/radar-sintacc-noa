"""Extracción: de dónde salen los datos crudos.

Dos fuentes posibles (parámetro `source`):
- "csv":   lee CSV ya extraídos (links públicos de Drive). Rápido y barato: ideal para la demo.
- "apify": llama a los extractores de Apify (Mercado Libre y Google Maps) y trae datos nuevos.
"""

import io

import httpx
import pandas as pd
from apify import Actor

from . import reglas

MAPS_ACTOR = "compass/crawler-google-places"


def _url_descarga(url: str) -> str:
    """Convierte un link de Drive 'compartir' en link de descarga directa."""
    if "drive.google.com" in url and "/d/" in url:
        file_id = url.split("/d/")[1].split("/")[0]
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    return url


async def leer_csv(url: str) -> pd.DataFrame:
    if not url.startswith("http"):  # archivo local (pruebas con `apify run`)
        return pd.read_csv(url, low_memory=False)
    async with httpx.AsyncClient(follow_redirects=True, timeout=60) as client:
        r = await client.get(_url_descarga(url))
        r.raise_for_status()
    return pd.read_csv(io.BytesIO(r.content), low_memory=False)


async def _correr_actor(actor_id: str, entrada: dict) -> list[dict]:
    Actor.log.info(f"Llamando a {actor_id}: {entrada}")
    run = await Actor.call(actor_id, run_input=entrada)
    if run is None:
        raise RuntimeError(f"El extractor {actor_id} no devolvió una corrida")
    dataset_id = getattr(run, "default_dataset_id", None) or run["defaultDatasetId"]
    pagina = await Actor.apify_client.dataset(dataset_id).list_items()
    return pagina.items


async def mercado_libre_apify(actor_id: str, plantilla: dict, productos: list[str]) -> pd.DataFrame:
    """Una corrida por búsqueda. `plantilla` es el input del extractor con "{busqueda}" donde va el texto."""
    tablas = []
    for categoria in productos:
        for busqueda in reglas.BUSQUEDAS_ML[categoria]:
            entrada = {k: (v.replace("{busqueda}", busqueda) if isinstance(v, str) else v)
                       for k, v in plantilla.items()}
            df = pd.DataFrame(await _correr_actor(actor_id, entrada))
            df["categoria"] = categoria
            tablas.append(df)
    return pd.concat(tablas, ignore_index=True)


async def google_maps_apify(provincias: list[str], max_por_busqueda: int) -> pd.DataFrame:
    tablas = []
    for provincia in provincias:
        capital = reglas.PROVINCIAS[provincia]
        items = await _correr_actor(MAPS_ACTOR, {
            "searchStringsArray": reglas.BUSQUEDAS_MAPS,
            "locationQuery": f"{capital}, {provincia}, Argentina",
            "maxCrawledPlacesPerSearch": max_por_busqueda,
            "language": "es",
        })
        tablas.append(pd.DataFrame(items))
    return pd.concat(tablas, ignore_index=True)


def validar_columnas(df: pd.DataFrame, requeridas: list[str], fuente: str) -> None:
    """Si la página cambió y el extractor ya no trae las columnas, frenamos con un error claro."""
    faltan = [c for c in requeridas if c not in df.columns]
    if df.empty or faltan:
        raise ValueError(f"{fuente}: {len(df)} filas, faltan columnas {faltan}. "
                         f"¿Cambió la página o el extractor?")
