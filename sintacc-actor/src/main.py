"""Actor: Inteligencia competitiva sin TACC (NOA).

Regla R4: este archivo solo arma el Actor (entrada, push_data, set_value, estado y log).
La lógica vive en los módulos que importa.

Un Actor, dos operaciones (parámetro `operation`):
- "analytics": extracción + ETL + EDA -> tablas limpias e indicadores para el dashboard.
- "inference": Producto 2 -> semáforo de compra por publicación, a partir de lo que publicó "analytics".
"""

import time
from datetime import datetime, timezone

from apify import Actor

from . import eda, etl_maps, etl_ml, extraer, inferencia, salida

STORE_PUBLICO = "radar-sintacc"  # nombre fijo: Google Sheets (IMPORTDATA) lee siempre la misma URL


async def analytics(entrada: dict) -> None:
    inicio = time.time()
    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    ml_crudo, maps_crudo = await extraer.obtener_datos(entrada)
    Actor.log.info(f"Crudos: {len(ml_crudo)} publicaciones, {len(maps_crudo)} locales")

    ml = etl_ml.procesar(ml_crudo)
    maps, pasos = etl_maps.procesar(maps_crudo)
    resumen = eda.resumen(ml, maps, pasos)
    resumen["fecha_corrida"] = fecha
    Actor.log.info(f"Limpios: {len(ml)} publicaciones, {len(maps)} locales. Controles: {resumen['controles']}")

    # Dataset de la corrida
    await Actor.push_data(salida.filas_dataset(ml, maps, resumen, fecha))

    # Key-value store de la corrida
    await Actor.set_value("RESUMEN", resumen)
    await Actor.set_value("productos.csv", ml.to_csv(index=False), content_type="text/csv")
    await Actor.set_value("locales.csv", maps.to_csv(index=False), content_type="text/csv")

    # Key-value store público (última versión + historial de precios)
    store = await Actor.open_key_value_store(name=STORE_PUBLICO)
    historial = salida.unir_historial(await store.get_value("historial_kpi.csv"), resumen, fecha)
    await store.set_value("productos.csv", ml.to_csv(index=False), content_type="text/csv")
    await store.set_value("locales.csv", maps.to_csv(index=False), content_type="text/csv")
    await store.set_value("RESUMEN", resumen)
    await store.set_value("historial_kpi.csv", historial.to_csv(index=False), content_type="text/csv")
    Actor.log.info(f"Publicado en '{STORE_PUBLICO}' (historial_kpi: {len(historial)} filas)")

    await Actor.set_status_message(f"Listo: {len(ml)} publicaciones y {len(maps)} locales "
                                   f"en {time.time() - inicio:.1f} s")


async def inference(entrada: dict) -> None:
    inicio = time.time()
    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Reusa los datos del Producto 1: la última salida de "analytics" (por el SDK, R1)
    productos = await extraer.leer_csv_store("productos.csv", store=STORE_PUBLICO,
                                             ayuda="Correr primero la operación 'analytics'.")
    insights = inferencia.semaforo(productos)
    resumen = inferencia.resumen(insights)
    resumen["fecha_corrida"] = fecha
    Actor.log.info(f"Semáforo ({resumen['metodo']}): {resumen['total']}")

    await Actor.push_data(salida.filas_tabla(insights, "insights", fecha))
    await Actor.set_value("RESUMEN_INFERENCE", resumen)
    await Actor.set_value("insights.csv", insights.to_csv(index=False), content_type="text/csv")

    store = await Actor.open_key_value_store(name=STORE_PUBLICO)
    await store.set_value("insights.csv", insights.to_csv(index=False), content_type="text/csv")
    await store.set_value("RESUMEN_INFERENCE", resumen)

    await Actor.set_status_message(f"Listo: semáforo de {len(insights)} publicaciones "
                                   f"{resumen['total']} en {time.time() - inicio:.1f} s")


async def main() -> None:
    async with Actor:
        entrada = await Actor.get_input() or {}
        operacion = entrada.get("operation", "analytics")
        if operacion == "analytics":
            await analytics(entrada)
        elif operacion == "inference":
            await inference(entrada)
        else:
            await Actor.fail(status_message=f"Operación desconocida: {operacion!r}. Usar 'analytics' o 'inference'.")
