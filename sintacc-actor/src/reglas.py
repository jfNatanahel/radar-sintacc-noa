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

# Categoría del producto = clasificación de Mercado Libre (produtoDomainID), no la palabra de
# búsqueda (DS, 18/11). La búsqueda mete ruido: fécula y harina de arveja caían en "pan",
# pasta Matarazzo en "harina". El sorteo 90/10 sigue usando la categoría de búsqueda
# (categoria_busqueda), para que el 10 % reservado sea el mismo que en el Colab.
CATEGORIA_POR_DOMINIO = {
    "MLA-PASTAS": "fideos",
    "MLA-FLOUR": "harina",
    "MLA-BREADS": "pan",
    "MLA-SALTY_PREMIXES": "premezcla",
    "MLA-SWEET_PREMIXES": "premezcla",
    "MLA-BREAD_CRUMBS": "rebozador",
}
# Féculas que Mercado Libre clasifica en otro dominio: van a harina (DS, 18/11)
CATEGORIA_FORZADA = {
    "MLA1345326206": "harina",
    "MLA1341298989": "harina",
    "MLA1373699734": "harina",
    "MLA1336027535": "harina",
}

# Productos fuera de alcance aunque estén en esas categorías
EXCLUIR_ML = ("pancake|omelette|falafel|levadura|huevo en polvo|alfajor|"
              "hamburguesa|buñuelo|pancho|salchicha")

# "nugget" sin "tacc", "gluten" o "celíaco" en el título queda afuera (DS, 16/11)
EXCLUIR_NUGGET = r"nugget"
SALVA_NUGGET = r"tacc|gluten|celiac"

# Publicaciones fuera de alcance revisadas a mano por DS el 16/11 (se aplican después del sorteo)
EXCLUIR_IDS_ML = {
    "MLA1420223627",  # pan de brea (asfalto)
    "MLA3883705424", "MLA2046043949",  # Molto X5 y X10
    "MLA1410486463",  # queso crema Tonadita
    "MLA3650583606",  # panko blanco
    "MLA880878959", "MLA843051276",  # Green Mills 350 g y 650 g
}

# Correcciones manuales verificadas en la publicación (DS, 16/11). Se aplican después de leer el título.
# unidades_pack: el precio es el de UNA unidad aunque el título diga pack, o el pack estaba mal leído.
CORRECCION_PACK = {
    "MLA1695005069": 1, "MLA3190142942": 1, "MLA2100085831": 1,
    "MLA3190389606": 1, "MLA4000481502": 1,
    "MLA1702182943": 12, "MLA3914510774": 3,
}
# peso de UNA unidad, en kg
CORRECCION_PESO_KG = {
    "MLA3785133802": 25, "MLA1110405149": 15, "MLA1587586569": 15,
    "MLA1606756347": 0.45, "MLA1606703695": 0.45,  # la segunda es inferida de la primera (no disponible)
    "MLA3342451372": 0.5, "MLA1702182943": 0.21, "MLA3914510774": 1,
}

# Desde cuántas unidades se considera compra por mayor
UNIDADES_MAYORISTA = 5

# Pesos fuera de este rango (kg) se consideran mal leídos del título
PESO_MIN_KG, PESO_MAX_KG = 0.05, 50

# Límites FIJOS de precio por kg ($) por categoría: Q1 - 1,5 IQR y Q3 + 1,5 IQR en logaritmo,
# calculados por DS con el 90 % de trabajo (16/11). Fuera de este rango -> outlier_precio_kg = 1.
# Es solo una marca para el dashboard: no se elimina ninguna fila.
LIMITES_PRECIO_KG = {
    "fideos": (7_328, 51_668),
    "harina": (1_558, 38_722),
    "pan": (9_358, 126_980),
    "premezcla": (3_291, 32_253),
    "rebozador": (5_325, 50_365),
}

# ---------------------------------------------------------------- Muestra 90 / 10
# El 10 % se reserva para evaluar el modelo del Producto 2 (nunca se usa para elegir features).
# Sorteo al azar con semilla fija, dentro de cada grupo, igual que en el Colab.
SEMILLA = 42
FRACCION_RESERVA = 0.10
ESTRATOS_ML = ["categoria_busqueda"]  # el sorteo usa la categoría de búsqueda (igual que el Colab)
ESTRATOS_MAPS = ["provincia", "sin_tacc_confirmado"]

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

# ---------------------------------------------------------------- Producto 2: semáforo de compra
# Referencia (plan B, sin modelo): mediana del precio por kg de su categoría y tipo de venta
# (minorista / mayorista), calculada solo con el 90 % de trabajo y sin outliers.
# Diferencia = precio_por_kg / referencia - 1.
# Los umbrales son simétricos en proporción: 0,75 veces lo normal (verde) y 1 / 0,75 = 1,33 veces
# (rojo). Con ±25 % el rojo quedaba más cerca que el verde: en la corrida del 19/11 daba
# 232 rojos contra 175 verdes con datos simétricos alrededor de la mediana.
SEMAFORO_VERDE = -0.25                         # 25 % o más por debajo de lo normal: oportunidad de compra
SEMAFORO_ROJO = 1 / (1 + SEMAFORO_VERDE) - 1   # ≈ +33 %: cara
# Si un grupo (categoría + tipo de venta) tiene menos publicaciones que esto,
# se usa la mediana de toda la categoría.
SEMAFORO_MIN_GRUPO = 5

# Modelo de Maps (complementario): un local es "por encima de lo esperado" si tiene al menos el
# doble de reseñas que las que predice el modelo (y "por debajo" si tiene la mitad o menos).
POPULARIDAD_ALTA = 2.0

# ---------------------------------------------------------------- Producto 2: costeador de menú
# Kit "Menú Sin TACC" (idea de Juan, 17/11): un plato base por insumo. Cantidad del insumo sin TACC
# por porción (kg) y porciones por mes. Son SUPUESTOS editables para un local chico (2 porciones
# por día de cada plato); el costo es solo el del insumo sin TACC, no el del plato completo.
RECETAS = [
    {"plato": "Fideos con salsa", "insumo": "fideos", "kg_porcion": 0.120, "porciones_mes": 60},
    {"plato": "Milanesa de pollo rebozada", "insumo": "rebozador", "kg_porcion": 0.040, "porciones_mes": 60},
    {"plato": "Pizza individual", "insumo": "premezcla", "kg_porcion": 0.120, "porciones_mes": 60},
    # "titulo" (opcional): el producto recomendado tiene que decir eso en el título. La categoría
    # harina incluye féculas y almidones, que solos no sirven para una masa.
    {"plato": "Tarta de verduras (masa)", "insumo": "harina", "kg_porcion": 0.060, "porciones_mes": 60,
     "titulo": r"harina"},
    {"plato": "Sándwich", "insumo": "pan", "kg_porcion": 0.100, "porciones_mes": 60},
]

# ---------------------------------------------------------------- Producto 2: validación ANMAT
# Similitud mínima (0 a 100, rapidfuzz token_set_ratio) entre el título y un producto registrado
# de la misma marca para considerarlo "validado". Debajo queda "marca_en_listado" (revisar a mano).
ANMAT_UMBRAL = 80
# Marcas que no se buscan en el título: muy cortas o palabras comunes que darían falsos positivos.
ANMAT_MARCA_MIN = 3
ANMAT_MARCAS_GENERICAS = {"sin tacc", "sin gluten", "libre de gluten", "harina", "premezcla", "pan",
                          "fideos", "arroz", "maiz", "natural", "la", "el", "de", "s a", "srl", "sa"}
