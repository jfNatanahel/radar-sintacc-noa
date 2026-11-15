"""Actor: Inteligencia competitiva sin TACC (NOA).

Un Actor, dos operaciones (parámetro `operation`):
- "analytics": extracción + ETL + EDA -> tablas limpias e indicadores para el dashboard.
- "inference": Producto 2 (pendiente).
"""

import io
import time
from datetime import datetime, timezone

import pandas as pd
from apify import Actor

from . import eda, etl_maps, etl_ml, extraer

COLUMNAS_ML = ["idPublicacion", "articuloTitulo", "nuevoPrecio", "produtoDomainID", "categoria"]
COLUMNAS_MAPS = ["placeId", "title", "categoryName", "state", "countryCode", "reviewsCount"]


async def obtener_datos(entrada: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    if entrada.get("source", "csv") == "apify":
        ml = await extraer.mercado_libre_apify(entrada["mlActorId"], entrada["mlInput"],
                                               entrada.get("productos", list(etl_ml.reglas.PRODUCTOS)))
        maps = await extraer.google_maps_apify(entrada.get("provincias", ["Salta", "Jujuy", "La Rioja"]),
                                               int(entrada.get("maxPorBusqueda", 40)))
    else:
        ml = await extraer.leer_csv(entrada["mlCsvUrl"])
        maps = await extraer.leer_csv(entrada["mapsCsvUrl"])
    extraer.validar_columnas(ml, COLUMNAS_ML, "Mercado Libre")
    extraer.validar_columnas(maps, COLUMNAS_MAPS, "Google Maps")
    return ml, maps


def _filas(df: pd.DataFrame, tabla: str, fecha: str) -> list[dict]:
    df = df.astype(object).where(df.notna(), None)
    return [{"tabla": tabla, "fecha_corrida": fecha, **r} for r in df.to_dict("records")]


async def analytics(entrada: dict) -> None:
    inicio = time.time()
    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    ml_crudo, maps_crudo = await obtener_datos(entrada)
    Actor.log.info(f"Crudos: {len(ml_crudo)} publicaciones, {len(maps_crudo)} locales")

    ml = etl_ml.procesar(ml_crudo)
    maps, pasos = etl_maps.procesar(maps_crudo)
    resumen = eda.resumen(ml, maps, pasos)
    resumen["fecha_corrida"] = fecha
    Actor.log.info(f"Limpios: {len(ml)} publicaciones, {len(maps)} locales")

    # Dataset: una fila por registro, con la columna `tabla` para separarlas en Make
    await Actor.push_data(_filas(ml, "productos", fecha) + _filas(maps, "locales", fecha)
                          + [{"tabla": "kpi_categoria", "fecha_corrida": fecha, **k}
                             for k in resumen["precio_kg_por_categoria"]]
                          + [{"tabla": "kpi_provincia", "fecha_corrida": fecha, **k}
                             for k in resumen["oferta_por_provincia"]])

    # Key-value store de la corrida: archivos descargables
    await Actor.set_value("RESUMEN", resumen)
    await Actor.set_value("productos.csv", ml.to_csv(index=False), content_type="text/csv")
    await Actor.set_value("locales.csv", maps.to_csv(index=False), content_type="text/csv")

    # Key-value store con nombre fijo: siempre la misma URL, para que Google Sheets (IMPORTDATA)
    # y Tableau lean la última versión sin pasar fila por fila por Make.
    await publicar(ml, maps, resumen, fecha)

    Actor.log.info(f"Listo en {time.time() - inicio:.1f} s")


STORE_PUBLICO = "radar-sintacc"


async def publicar(ml: pd.DataFrame, maps: pd.DataFrame, resumen: dict, fecha: str) -> None:
    store = await Actor.open_key_value_store(name=STORE_PUBLICO)
    await store.set_value("productos.csv", ml.to_csv(index=False), content_type="text/csv")
    await store.set_value("locales.csv", maps.to_csv(index=False), content_type="text/csv")
    await store.set_value("RESUMEN", resumen)

    # Historial: cada corrida agrega sus indicadores por categoría con la fecha.
    # Así se ven los cambios de precio semana a semana (el dolor de Diana: "llego tarde").
    kpis = pd.DataFrame(resumen["precio_kg_por_categoria"])
    kpis.insert(0, "fecha_corrida", fecha)
    anterior = await store.get_value("historial_kpi.csv")
    if isinstance(anterior, bytes):
        anterior = anterior.decode("utf-8")
    if anterior:
        previo = pd.read_csv(io.StringIO(anterior))
        kpis = pd.concat([previo[previo["fecha_corrida"] != fecha], kpis], ignore_index=True)
    await store.set_value("historial_kpi.csv", kpis.to_csv(index=False), content_type="text/csv")

    Actor.log.info(f"Publicado en el store '{STORE_PUBLICO}': productos.csv, locales.csv, "
                   f"historial_kpi.csv ({len(kpis)} filas), RESUMEN")


async def main() -> None:
    async with Actor:
        entrada = await Actor.get_input() or {}
        operacion = entrada.get("operation", "analytics")
        if operacion == "analytics":
            await analytics(entrada)
        elif operacion == "inference":
            await Actor.fail(status_message="La operación 'inference' (Producto 2) todavía no está disponible.")
        else:
            await Actor.fail(status_message=f"Operación desconocida: {operacion!r}. Usar 'analytics' o 'inference'.")
