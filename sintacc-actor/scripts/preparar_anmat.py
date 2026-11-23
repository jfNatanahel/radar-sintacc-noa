"""Convierte el Listado de Alimentos Libres de Gluten de ANMAT a anmat_listado.csv (marca, producto).

Acepta el archivo de datos.gob.ar (CSV o JSON) o un Excel. Busca la columna de marca y arma
"producto" con el nombre de fantasía y la denominación. Se corre FUERA del Actor; el resultado se
sube al store de entrada con scripts/subir_csv_a_apify.py --anmat (el Actor lo lee por el SDK, R1).

    python scripts/preparar_anmat.py listado_anmat.(csv|json|xlsx) anmat_listado.csv
"""

import sys
from pathlib import Path

import pandas as pd


def leer(ruta: str) -> pd.DataFrame:
    p = Path(ruta)
    if p.suffix.lower() == ".json":
        datos = pd.read_json(p)
        return pd.json_normalize(datos.to_dict("records")) if isinstance(datos, pd.DataFrame) else datos
    if p.suffix.lower() in (".xlsx", ".xls"):
        return pd.read_excel(p)
    for sep in (",", ";", "\t"):
        df = pd.read_csv(p, sep=sep, low_memory=False, encoding_errors="replace")
        if df.shape[1] > 1:
            return df
    return df


def _columna(df: pd.DataFrame, *claves: str) -> str | None:
    for clave in claves:
        for c in df.columns:
            if clave in c.lower():
                return c
    return None


def convertir(df: pd.DataFrame) -> pd.DataFrame:
    """Una fila por (marca, producto). Solo productos vigentes y activos; las marcas compuestas
    ("NESTLÉ - FRIGOR - TORPEDO") se separan; "NO REGISTRA" se ignora."""
    marca = _columna(df, "marca")
    if marca is None:
        sys.exit(f"No encuentro la columna de marca. Columnas: {list(df.columns)}")
    estado, activo = _columna(df, "estado"), _columna(df, "activo")
    if estado:
        df = df[df[estado].astype(str).str.upper().str.strip() == "VIGENTE"]
    if activo:
        df = df[df[activo].astype(str).str.lower().str.strip().isin(["sí", "si", "true", "1"])]
    partes = [c for c in (_columna(df, "fantasia"), _columna(df, "denominacion", "denominación", "producto"))
              if c is not None]
    textos = df[partes].fillna("").astype(str).replace(r"(?i)^\s*no registra\s*$", "", regex=True)
    producto = textos.agg(" ".join, axis=1).str.replace(r"\s+", " ", regex=True).str.strip()
    tipo = _columna(df, "tipoproducto", "tipo")
    out = pd.DataFrame({"marca": df[marca].astype(str), "producto": producto,
                        "tipo": df[tipo].astype(str) if tipo else ""})
    out["marca"] = out["marca"].str.split(r"\s+-\s+|/")
    out = out.explode("marca")
    out["marca"] = out["marca"].str.strip()
    return out[(out["marca"] != "") & (out["producto"] != "")].drop_duplicates()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    tabla = convertir(leer(sys.argv[1]))
    tabla.to_csv(sys.argv[2], index=False)
    print(f"{len(tabla)} productos de {tabla['marca'].nunique()} marcas -> {sys.argv[2]}")
