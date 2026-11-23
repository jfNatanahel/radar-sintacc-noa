"""Kit "Menú Sin TACC": cuánto le cuesta a un local cada plato base sin TACC y cuánto ahorra
comprando la mejor oportunidad del semáforo (Producto 2).

- Precio típico: mediana del precio por kg minorista de la categoría (lo que paga un local que
  compra por unidad), sin las publicaciones marcadas "revisar".
- Precio con el radar: la oportunidad verde más barata por kg de esa categoría (una publicación
  concreta, con nombre y link por idPublicacion).
Es un ahorro POTENCIAL: no incluye envío ni stock, y lo verde es barato porque se eligió por barato.
"""

import pandas as pd

from . import reglas


def costeo(insights: pd.DataFrame, recetas: list[dict] = reglas.RECETAS) -> pd.DataFrame:
    """Una fila por plato con el costo por porción típico y con el radar, y el ahorro por mes."""
    confiables = insights[insights["semaforo"] != "revisar"]
    tipico = (confiables[confiables["venta_por_mayor"] == 0]
              .groupby("categoria")["precio_por_kg"].median())
    # Solo se recomienda lo "barato y seguro": verde y validado en ANMAT (si se cargó el listado)
    elegibles = insights["recomendado"] == 1 if "recomendado" in insights else insights["semaforo"] == "verde"
    verdes = insights[elegibles].sort_values("precio_por_kg")

    filas = []
    for r in recetas:
        cat = r["insumo"]
        candidatos = verdes[verdes["categoria"] == cat]
        if r.get("titulo"):
            candidatos = candidatos[candidatos["articuloTitulo"].str.contains(r["titulo"], case=False, regex=True)]
        mejor = candidatos.head(1).set_index("categoria")
        r = {k: v for k, v in r.items() if k != "titulo"}
        kg_tipico = tipico.get(cat)
        fila = {**r, "precio_kg_tipico": kg_tipico,
                "costo_porcion_tipico": round(kg_tipico * r["kg_porcion"]) if pd.notna(kg_tipico) else None}
        if cat in mejor.index:
            m = mejor.loc[cat]
            kg_radar = min(m["precio_por_kg"], kg_tipico) if pd.notna(kg_tipico) else m["precio_por_kg"]
            costo_radar = round(kg_radar * r["kg_porcion"])
            fila.update({
                "precio_kg_radar": kg_radar, "costo_porcion_radar": costo_radar,
                "publicacion_recomendada": m["articuloTitulo"], "idPublicacion": m["idPublicacion"],
                "precio_publicacion": m["precio"],
            })
            if fila["costo_porcion_tipico"] is not None:
                ahorro = fila["costo_porcion_tipico"] - costo_radar
                fila.update({"ahorro_porcion": ahorro,
                             "ahorro_pct": round(100 * ahorro / fila["costo_porcion_tipico"], 1),
                             "ahorro_mes": ahorro * r["porciones_mes"]})
        filas.append(fila)
    return pd.DataFrame(filas)


def resumen(menu: pd.DataFrame) -> dict:
    total_tipico = float((menu["costo_porcion_tipico"] * menu["porciones_mes"]).sum())
    total_radar = float((menu["costo_porcion_radar"] * menu["porciones_mes"]).sum())
    return {
        "platos": int(len(menu)),
        "costo_insumos_mes_tipico": round(total_tipico),
        "costo_insumos_mes_radar": round(total_radar),
        "ahorro_mes": round(total_tipico - total_radar),
        "ahorro_pct": round(100 * (total_tipico - total_radar) / total_tipico, 1) if total_tipico else None,
    }
