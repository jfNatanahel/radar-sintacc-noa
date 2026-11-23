"""Extracción: de dónde salen los datos crudos.

Regla R1: los datos entran al Actor SOLO por el SDK de Apify (nada de urllib, requests,
httpx ni open() sobre fuentes externas). Así cada entrada queda trazable en la plataforma.

Dos fuentes posibles (parámetro `source`):
- "csv":   los CSV del 12/11, guardados en el key-value store `STORE_ENTRADA` de la cuenta
           (se suben una sola vez con scripts/subir_csv_a_apify.py). Rápido y barato: demo.
- "apify": llama a los extractores de Apify (Mercado Libre y Google Maps) y trae datos nuevos.
"""

import io

import pandas as pd
from apify import Actor

from . import reglas

MAPS_ACTOR = "compass/crawler-google-places"

# Key-value store con los CSV ya extraídos. Nombre fijo: la entrada del Actor no puede
# apuntar a otro lugar (no hay URLs en el input).
STORE_ENTRADA = "radar-sintacc-entrada"
CLAVE_ML = "ml_unificado.csv"
CLAVE_MAPS = "maps_unificado.csv"
CLAVE_ANMAT = "anmat_listado.csv"   # columnas marca, producto (scripts/subir_csv_a_apify.py --anmat)

COLUMNAS_ML = ["idPublicacion", "articuloTitulo", "nuevoPrecio", "produtoDomainID", "categoria"]
COLUMNAS_MAPS = ["placeId", "title", "categoryName", "state", "countryCode", "reviewsCount"]


AYUDA_ENTRADA = "Subirlo con scripts/subir_csv_a_apify.py."


def csv_a_tabla(contenido: bytes | str | None, origen: str, ayuda: str = AYUDA_ENTRADA) -> pd.DataFrame:
    """Convierte el contenido de un registro del store en tabla. Falla claro si no existe."""
    if contenido is None:
        raise ValueError(f"No está {origen}. {ayuda}")
    if isinstance(contenido, str):
        contenido = contenido.encode("utf-8")
    return pd.read_csv(io.BytesIO(contenido), low_memory=False)


async def leer_csv_store(clave: str, store: str = STORE_ENTRADA, ayuda: str = AYUDA_ENTRADA,
                         store_id: str | None = None) -> pd.DataFrame:
    """Lee un CSV de un key-value store, por ID (si viene en la entrada) o por nombre.

    Con permisos limitados, Apify solo deja abrir los stores que creó el propio Actor o los que
    el usuario le pasa en la entrada (campo `csvStore`). Por eso el store de entrada va por ID.
    """
    kv = await (Actor.open_key_value_store(id=store_id) if store_id
                else Actor.open_key_value_store(name=store))
    origen = f"'{clave}' en el store '{store_id or store}'"
    return csv_a_tabla(await kv.get_value(clave), origen, ayuda)


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


async def obtener_datos(entrada: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve (Mercado Libre crudo, Google Maps crudo) según `source`, con columnas validadas."""
    fuente = entrada.get("source", "csv")
    if fuente == "apify":
        if not entrada.get("mlActorId") or not entrada.get("mlInput"):
            raise ValueError("source 'apify' necesita mlActorId y mlInput (extractor de Mercado Libre).")
        ml = await mercado_libre_apify(entrada["mlActorId"], entrada["mlInput"],
                                       entrada.get("productos", list(reglas.PRODUCTOS)))
        maps = await google_maps_apify(entrada.get("provincias", list(reglas.PROVINCIAS)),
                                       int(entrada.get("maxPorBusqueda", 40)))
    elif fuente == "csv":
        store_id = entrada.get("csvStore")
        ml = await leer_csv_store(CLAVE_ML, store_id=store_id)
        maps = await leer_csv_store(CLAVE_MAPS, store_id=store_id)
    else:
        raise ValueError(f"Fuente desconocida: {fuente!r}. Usar 'csv' o 'apify'.")
    validar_columnas(ml, COLUMNAS_ML, "Mercado Libre")
    validar_columnas(maps, COLUMNAS_MAPS, "Google Maps")
    return ml, maps


async def leer_anmat(store_id: str | None) -> pd.DataFrame | None:
    """Listado de ANMAT del store de entrada. Es opcional: si no está, devuelve None."""
    if not store_id:
        return None
    kv = await Actor.open_key_value_store(id=store_id)
    contenido = await kv.get_value(CLAVE_ANMAT)
    return None if contenido is None else csv_a_tabla(contenido, CLAVE_ANMAT)
