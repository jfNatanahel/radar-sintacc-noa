"""Sube los CSV unificados del 12/11 al key-value store que lee el Actor (fuente "csv").

Se corre UNA vez desde la compu, fuera del Actor. Así el Actor no descarga nada de
internet (regla R1): lee los datos por el SDK de Apify.

    pip install apify-client
    export APIFY_TOKEN=...            # Apify > Settings > API & Integrations (nunca en el código)
    python scripts/subir_csv_a_apify.py ml_sintacc_unificado.csv maps_unificado.csv
    python scripts/subir_csv_a_apify.py --anmat anmat_listado.csv     # listado de ANMAT (opcional)
"""

import os
import sys
from pathlib import Path

from apify_client import ApifyClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.extraer import CLAVE_ANMAT, CLAVE_MAPS, CLAVE_ML, STORE_ENTRADA  # noqa: E402


def main(archivos: list[tuple[str, str]]) -> None:
    token = os.environ.get("APIFY_TOKEN")
    if not token:
        sys.exit("Falta la variable de entorno APIFY_TOKEN.")
    cliente = ApifyClient(token)
    store = cliente.key_value_stores().get_or_create(name=STORE_ENTRADA)
    store_id = store.id if hasattr(store, "id") else store["id"]  # apify-client 3 devuelve un objeto
    for ruta, clave in archivos:
        contenido = Path(ruta).read_bytes()
        cliente.key_value_store(store_id).set_record(clave, contenido, content_type="text/csv")
        print(f"Subido {ruta} -> {STORE_ENTRADA}/{clave} ({len(contenido) / 1024:.0f} KB)")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--anmat":
        main([(sys.argv[2], CLAVE_ANMAT)])
    elif len(sys.argv) == 3:
        main([(sys.argv[1], CLAVE_ML), (sys.argv[2], CLAVE_MAPS)])
    else:
        sys.exit(__doc__)
