"""Actor: Inteligencia competitiva sin TACC (NOA).

Regla R4: este archivo solo arma el Actor (entrada, push_data, set_value, estado y log).
La lógica vive en los módulos que importa.

Un Actor, dos operaciones (parámetro `operation`):
- "analytics": extracción + ETL + EDA -> tablas limpias e indicadores para el dashboard.
- "inference": Producto 2 -> semáforo de compra por publicación, a partir de lo que publicó "analytics".
"""

import time
from datetime import datetime
from zoneinfo import ZoneInfo

from apify import Actor

from . import anmat, eda, etl_maps, etl_ml, extraer, inferencia, menu, modelo, salida

ZONA = ZoneInfo("America/Argentina/Buenos_Aires")  # la fecha de corrida es la de Argentina, no UTC
STORE_PUBLICO = "radar-sintacc"  # nombre fijo: Google Sheets (IMPORTDATA) lee siempre la misma URL


async def analytics(entrada: dict) -> None:
    inicio = time.time()
    fecha = datetime.now(ZONA).strftime("%Y-%m-%d")

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
    fecha = datetime.now(ZONA).strftime("%Y-%m-%d")
    usar_modelo = entrada.get("metodo", "modelo") == "modelo"

    # Reusa los datos del Producto 1: la última salida de "analytics" (por el SDK, R1)
    ayuda = "Correr primero la operación 'analytics'."
    productos = await extraer.leer_csv_store("productos.csv", store=STORE_PUBLICO, ayuda=ayuda)

    # Semáforo de compra: modelo de DS (R2: no entrena, R3: carga de modelos/) o plan B
    esperado = None
    if usar_modelo:
        pipeline = modelo.cargar(modelo.MODELO_ML)
        esperado = modelo.predecir(pipeline, productos, modelo.FEATURES_ML)
    insights = inferencia.semaforo(productos, precio_esperado=esperado)

    # "Barato y seguro": validación contra el listado de ANMAT (opcional, del store de entrada)
    listado = await extraer.leer_anmat(entrada.get("csvStore"))
    validacion = anmat.validar(insights, anmat.preparar_listado(listado) if listado is not None else None)
    insights = inferencia.agregar_anmat(insights, validacion)
    resumen = inferencia.resumen(insights)
    resumen["fecha_corrida"] = fecha
    Actor.log.info(f"Semáforo ({resumen['metodo']}): {resumen['total']} · ANMAT: {resumen['anmat']} · "
                   f"recomendados (verde y validado): {resumen['recomendados']}")

    filas = salida.filas_tabla(insights, "insights", fecha)
    store = await Actor.open_key_value_store(name=STORE_PUBLICO)

    # Kit "Menú Sin TACC": costo por plato con el precio típico y con la mejor oportunidad
    costeo = menu.costeo(insights)
    resumen["menu"] = menu.resumen(costeo)
    filas += salida.filas_tabla(costeo, "menu", fecha)
    await Actor.set_value("menu.csv", costeo.to_csv(index=False), content_type="text/csv")
    await store.set_value("menu.csv", costeo.to_csv(index=False), content_type="text/csv")
    Actor.log.info(f"Menú sin TACC: {resumen['menu']}")

    # Modelo complementario de Maps: popularidad real contra la esperada
    if usar_modelo:
        locales = await extraer.leer_csv_store("locales.csv", store=STORE_PUBLICO, ayuda=ayuda)
        resenas = modelo.predecir(modelo.cargar(modelo.MODELO_MAPS), locales, modelo.FEATURES_MAPS)
        popularidad = inferencia.popularidad_locales(locales, resenas)
        resumen["popularidad_locales"] = inferencia.conteo_popularidad(popularidad)
        filas += salida.filas_tabla(popularidad, "popularidad", fecha)
        await Actor.set_value("popularidad.csv", popularidad.to_csv(index=False), content_type="text/csv")
        await store.set_value("popularidad.csv", popularidad.to_csv(index=False), content_type="text/csv")
        Actor.log.info(f"Popularidad de locales (modelo Maps): {resumen['popularidad_locales']}")

    await Actor.push_data(filas)
    await Actor.set_value("RESUMEN_INFERENCE", resumen)
    await Actor.set_value("insights.csv", insights.to_csv(index=False), content_type="text/csv")
    await store.set_value("insights.csv", insights.to_csv(index=False), content_type="text/csv")
    await store.set_value("RESUMEN_INFERENCE", resumen)

    validados = (resumen["anmat"] or {}).get("validado", "sin listado")
    await Actor.set_status_message(
        f"Listo ({resumen['metodo']}): {len(insights)} publicaciones {resumen['total']} · "
        f"ANMAT validados: {validados} · recomendados: {resumen['recomendados']} · "
        f"menú: ahorro ${resumen['menu']['ahorro_mes']:,} por mes · {time.time() - inicio:.1f} s")


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
