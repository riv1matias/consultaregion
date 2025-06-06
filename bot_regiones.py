import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, Polygon
import ast
import re
import requests
import json
import urllib.parse
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import Update

# Configuración del bot de Telegram (reemplaza con tu Bot Token)
TOKEN = "7402637120:AAHbqpPxN70Crvn49IVYW8JU70fgjdZboeI"  # Reemplaza con el token que obtuviste de BotFather

# Diccionario de correcciones para nombres de calles
CORRECCIONES_CALLES = {
    "MACHU PICHU": "Machu Picchu",
    "11 DE MAYO": "Once de Mayo",
    "ULLA ULLA": "Ulla Ulla",
    "TALAMPAYA": "Talampaya",
    "AMOR PORTEÑO": "Amor Porteño",
    "EVITA": "Evita",
    "SUCRE MRCAL A J DE": "Sucre",
    "URQUIZA JUSTO JOSE DE": "Justo José de Urquiza",
    "CORREA CIRILO": "Correa",
    "BERUTI ANTONIO": "Beruti",
    "VEDIA NICOLAS DE": "Vedia",
    "MAGARINO CERVANTES A": "Magariños Cervantes",
    "ANCHORENA TOMÁS MANUEL": "Tomás Manuel de Anchorena",
    "JOSÉ ANDRÉS PACHECO DE MELO": "José Andrés Pacheco de Melo",
    "AV. HIPÓLITO YRIGOYEN": "Hipólito Yrigoyen",
    "AV. ÁLVAREZ THOMAS": "Álvarez Thomas",
    "3 DE FEBRERO": "Tres de Febrero",
    "ACUÑA DE FIGUEROA, FRANCISCO": "Francisco Acuña de Figueroa"
}

# Definir zonas (corregido: Palermo en Capital Sur, Paternal solo en Capital Norte)
ZONAS = {
    'Capital Sur': ['Boedo', 'San Telmo', 'Almagro', 'Recoleta', 'Palermo'],
    'Capital Norte': ['Devoto', 'Paternal', 'Colegiales', 'Saavedra']
}

def clasificar_zona(operacion):
    if pd.isna(operacion) or operacion == "No ubicado":
        return "No clasificado"
    for zona, barrios in ZONAS.items():
        for barrio in barrios:
            if barrio.lower() in operacion.lower():
                return zona
    return "No clasificado"

def limpiar_direccion(direccion_completa):
    if pd.isna(direccion_completa):
        return ""
    direccion = direccion_completa.strip()
    direccion = re.sub(r'\s*/\s*ALT\s*/\s*', ' ', direccion, flags=re.IGNORECASE)
    direccion = direccion.replace("&", "y")
    direccion = re.sub(r',AV\.\s*', ' ', direccion, flags=re.IGNORECASE)
    direccion = re.sub(r'\s*MRCAL\s*[A-Z]*\s*DE\s*', ' ', direccion, flags=re.IGNORECASE)
    direccion = re.sub(r'\s*SUR\s*', ' ', direccion, flags=re.IGNORECASE)
    for incorrecto, correcto in CORRECCIONES_CALLES.items():
        direccion = re.sub(r'\b' + re.escape(incorrecto) + r'\b', correcto, direccion, flags=re.IGNORECASE)
    direccion = re.sub(r'\s+', ' ', direccion).strip()
    return direccion

def separar_direccion_altura(direccion_completa):
    pattern = r'^(.*?)\s*(\d+\w*)$'
    match = re.match(pattern, direccion_completa.strip(), re.IGNORECASE)
    if match:
        return match.group(1).strip(',').strip(), match.group(2).strip()
    else:
        return direccion_completa, ""

def normalizar_direccion(direccion, altura, errores, direccion_original, reintento=0):
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    session.mount('http://', HTTPAdapter(max_retries=retries))

    url_normalizar = "https://servicios.usig.buenosaires.gob.ar/normalizar/"
    url_geocodificar = "http://ws.usig.buenosaires.gob.ar/geocoder/2.2/geocoding"

    estrategias = [
        {"url": url_normalizar, "direccion": f"{direccion} {altura}, caba", "params": {"geocodificar": "true", "tipoResultado": "calle_altura"}},
        {"url": url_normalizar, "direccion": f"{direccion} {altura}, caba", "params": {"geocodificar": "true"}},
        {"url": url_normalizar, "direccion": f"{direccion} {altura}, caba", "params": {}},
    ]

    if reintento == 1:
        direccion_simplificada = "".join(direccion.split()[:1])
        estrategias = [
            {"url": url_normalizar, "direccion": f"{direccion_simplificada} {altura}, caba", "params": {"geocodificar": "true", "tipoResultado": "calle_altura"}}
        ]
    elif reintento == 2:
        direccion_reordenada = reordenar_calle(direccion)
        estrategias = [
            {"url": url_normalizar, "direccion": f"{direccion_reordenada} {altura}, caba", "params": {"geocodificar": "true", "tipoResultado": "calle_altura"}}
        ]
    elif reintento == 3:
        estrategias = [
            {"url": url_geocodificar, "direccion": f"{direccion}", "params": {"cod_calle": direccion.upper(), "altura": altura}}
        ]

    for estrategia in estrategias:
        url = estrategia["url"]
        direccion_completa = estrategia["direccion"]
        params = estrategia["params"]
        params["direccion"] = direccion_completa if url == url_normalizar else None
        direccion_codificada = urllib.parse.quote(direccion_completa) if url == url_normalizar else ""
        url_completa = f"{url}?{'&'.join(f'{k}={urllib.parse.quote(str(v))}' for k, v in params.items() if v)}"
        print(f"📍 Consultando (reintento {reintento}): {direccion_completa}")

        try:
            response = session.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            if url == url_normalizar and isinstance(data, dict) and data.get("direccionesNormalizadas"):
                dir_normalizada = data["direccionesNormalizadas"][0]
                calle_normalizada = dir_normalizada.get("calle", {}).get("nombre", direccion)
                altura_normalizada = dir_normalizada.get("altura", altura)
                coords = dir_normalizada.get("coordenadas", {})
                return f"{calle_normalizada} {altura_normalizada}".strip(), coords.get("x"), coords.get("y"), json.dumps(data, ensure_ascii=False)
            elif url == url_geocodificar and isinstance(data, dict):
                calle_normalizada = data.get("puerta", {}).get("calle", {}).get("nombre", direccion)
                altura_normalizada = data.get("puerta", {}).get("altura", {}).get("valor", altura)
                coords = data.get("puerta", {}).get("ubicacion", {})
                return f"{calle_normalizada} {altura_normalizada}".strip(), coords.get("x"), coords.get("y"), json.dumps(data, ensure_ascii=False)
            else:
                error_msg = f"No se encontró dirección normalizada."
                errores.append({
                    "direccion": direccion_completa,
                    "error": error_msg,
                    "original": direccion_original,
                    "reintento": reintento
                })

        except (requests.RequestException, json.JSONDecodeError) as e:
            error_msg = f"Error: {str(e)}"
            errores.append({
                "direccion": direccion_completa,
                "error": error_msg,
                "original": direccion_original,
                "reintento": reintento
            })
            time.sleep(3)

    return direccion_completa, None, None, ""

def reordenar_calle(direccion):
    palabras = direccion.split()
    if len(palabras) > 2:
        return f"{palabras[-1]} {' '.join(palabras[:-1])}"
    return direccion

# Cargar polígonos desde poligonos_operaciones.xlsx (local o GitHub)
def cargar_poligonos_excel(archivo_excel=None, url_github="https://github.com/riv1matias/consultaregion/blob/main/poligonos_operaciones.xlsx"):
    try:
        if url_github:
            response = requests.get(url_github)
            response.raise_for_status()
            with open('poligonos_operaciones.xlsx', 'wb') as f:
                f.write(response.content)
            archivo_excel = 'poligonos_operaciones.xlsx'
        df = pd.read_excel(archivo_excel)
        poligonos = []
        for _, row in df.iterrows():
            coords = ast.literal_eval(row['Coordenadas'])
            poligonos.append({
                "nombre_operacion": row['Nombre_Operacion'],
                "coordenadas": coords
            })
        return poligonos
    except FileNotFoundError:
        print("❌ Error: No se encontró 'poligonos_operaciones.xlsx'. Verifica la ruta o URL.")
        raise
    except Exception as e:
        print(f"❌ Error al procesar 'poligonos_operaciones.xlsx': {str(e)}")
        raise

# Crear GeoDataFrame con polígonos
def crear_gdf_poligonos(poligonos):
    geometries = [Polygon(coords) for coords in [p["coordenadas"] for p in poligonos]]
    gdf = gpd.GeoDataFrame(
        {"nombre_operacion": [p["nombre_operacion"] for p in poligonos]},
        geometry=geometries,
        crs="EPSG:4326"
    )
    return gdf

# Función para verificar si un punto está dentro de un polígono
def encontrar_operacion(x, y, gdf_poligonos):
    if pd.isna(x) or pd.isna(y):
        return "No ubicado"
    point = Point(x, y)
    for _, row in gdf_poligonos.iterrows():
        if row['geometry'].contains(point):
            return row['nombre_operacion']
    return "No ubicado"

# Cargar polígonos al iniciar el bot
try:
    # Opción 1: Cargar desde archivo local
    poligonos = cargar_poligonos_excel(archivo_excel='poligonos_operaciones.xlsx')
    # Opción 2: Cargar desde GitHub (descomenta y reemplaza con tu URL)
    # poligonos = cargar_poligonos_excel(url_github="https://raw.githubusercontent.com/TU_USUARIO/TU_REPOSITORIO/main/poligonos_operaciones.xlsx")
    gdf_poligonos = crear_gdf_poligonos(poligonos)
except Exception as e:
    print(f"❌ No se pudo cargar 'poligonos_operaciones.xlsx': {str(e)}")
    exit(1)

# Comandos del bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "¡Hola! Soy el bot Regiones. Envíame una dirección en CABA (por ejemplo, 'Av. Corrientes 1234') y te diré si pertenece a Capital Norte o Capital Sur."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    incoming_msg = update.message.text.strip()
    errores = []

    # Procesar la dirección
    direccion_limpia = limpiar_direccion(incoming_msg)
    direccion, altura = separar_direccion_altura(direccion_limpia)
    direccion_normalizada, x, y, _ = normalizar_direccion(direccion, altura, errores, incoming_msg)

    # Determinar operación y zona
    if x is not None and y is not None:
        operacion = encontrar_operacion(x, y, gdf_poligonos)
        zona = clasificar_zona(operacion)
        respuesta = f"La dirección {direccion_normalizada} pertenece a {zona} (Operación: {operacion})."
    else:
        respuesta = f"No se pudo normalizar la dirección '{incoming_msg}'. Por favor, intenta con un formato válido (ejemplo: 'Av. Corrientes 1234')."

    # Enviar respuesta
    await update.message.reply_text(respuesta)

def main():
    # Configurar el bot
    application = Application.builder().token(TOKEN).build()

    # Agregar manejadores
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Iniciar el bot
    print("🚀 Bot iniciado...")
    application.run_polling()

if __name__ == '__main__':
    main()
