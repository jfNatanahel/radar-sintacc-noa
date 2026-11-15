"""Reglas de negocio del proyecto, separadas del código.

Todo lo que el equipo puede querer cambiar sin tocar la lógica vive acá:
palabras clave, categorías válidas, umbrales y provincias. (Feedback del 17/11:
separar código de reglas de negocio.)
"""

# ---------------------------------------------------------------- Mercado Libre
PRODUCTOS = ["premezcla", "harina", "fideos", "rebozador", "pan"]

# Búsquedas que se lanzan al extractor de Mercado Libre, por categoría
BUSQUEDAS_ML = {
    "premezcla": ["premezcla sin tacc"],
    "harina": ["harina sin tacc", "harina de arroz sin tacc"],
    "fideos": ["fideos sin tacc", "fideos de maiz sin tacc"],
    "rebozador": ["rebozador sin tacc", "rebozador de maiz sin tacc"],
    "pan": ["pan sin tacc", "pan lactal sin tacc"],
}

# Categorías de Mercado Libre que sí son insumos del proyecto
CATEGORIAS_ML_OK = [
    "MLA-SALTY_PREMIXES", "MLA-SWEET_PREMIXES", "MLA-PASTAS",
    "MLA-BREAD_CRUMBS", "MLA-BREADS", "MLA-FLOUR",
]

# Productos fuera de alcance aunque estén en esas categorías
EXCLUIR_ML = ("pancake|omelette|falafel|levadura|huevo en polvo|alfajor|"
              "hamburguesa|buñuelo|pancho|salchicha")

# Desde cuántas unidades se considera compra por mayor
UNIDADES_MAYORISTA = 5

# Pesos fuera de este rango (kg) se consideran mal leídos del título
PESO_MIN_KG, PESO_MAX_KG = 0.05, 50

# Un precio/kg fuera de [Q1 - k*IQR, Q3 + k*IQR] de su categoría se marca outlier
IQR_K = 1.5

# ---------------------------------------------------------------- Google Maps
PROVINCIAS = {"Salta": "Salta", "Jujuy": "San Salvador de Jujuy", "La Rioja": "La Rioja"}

BUSQUEDAS_MAPS = ["restaurante", "restaurante sin tacc", "cafetería",
                  "cafetería sin tacc", "panadería"]

# Texto que indica oferta sin TACC en nombre o categoría del local
PALABRAS_SIN_TACC = r"tacc|gluten|cel[ií]ac"

# Radio para contar competencia sin TACC cercana
RADIO_KM = 2.0

TIPOS_LOCAL = {
    "panadería": r"panader|pasteler|reposter|panific",
    "cafetería": r"cafeter|café|cafe\b|chocolater|tetería",
    "restaurante": (r"restaurante|parrilla|pizza|pizzer|hamburgues|bar\b|pub\b|snack|"
                    r"rotiser|comida|pollería|sándwich|cervecer"),
}
