import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, Polygon
import re
import requests
import json
import urllib.parse
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import Update
import os
import logging

# Configurar logging para depuración
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuración del bot de Telegram
TOKEN = os.getenv("TOKEN")

# Verificar token al inicio
if not TOKEN:
    logger.error("❌ Error: No se encontró el Bot Token. Configura la variable de entorno TOKEN.")
    print("❌ Error: No se encontró el Bot Token. Configura la variable de entorno TOKEN.")
    exit(1)

# --- DEFINICIÓN DE POLÍGONOS DIRECTAMENTE EN EL CÓDIGO ---
# IMPORTANTE: DEBES REEMPLAZAR ESTA LISTA CON TODOS TUS POLÍGONOS REALES.
# Cada diccionario en la lista debe tener:
# "nombre_operacion": El nombre del barrio/operación que coincide con tu lógica de clasificación.
# "coordenadas": Una lista de tuplas (longitud, latitud) que definen el polígono.
POLIGONOS_DEFINIDOS = [
    {
        "nombre_operacion": "Almagro", # Este nombre debe coincidir con las claves de MAPEO_ZONAS_ESTATICO
        "coordenadas": [
            (-58.448044, -34.621039), (-58.447755, -34.621588), (-58.446835, -34.621211),
            (-58.447089, -34.620792), (-58.44676, -34.620654), (-58.445994, -34.62041),
            (-58.445894, -34.620453), (-58.445252, -34.620212), (-58.445201, -34.620115),
            (-58.445167, -34.619964), (-58.444178, -34.61953), (-58.442295, -34.618704),
            (-58.44176, -34.61847), (-58.440903, -34.618094), (-58.439893, -34.617651),
            (-58.439911, -34.617608), (-58.439854, -34.617517), (-58.439923, -34.617271),
            (-58.439145, -34.616937), (-58.439041, -34.617137), (-58.438923, -34.617179),
            (-58.438732, -34.617095), (-58.437566, -34.616588), (-58.437529, -34.616741),
            (-58.437407, -34.616693), (-58.437436, -34.616632), (-58.437304, -34.616579),
            (-58.437114, -34.61658), (-58.436328, -34.616249), (-58.43643, -34.616037),
            (-58.436267, -34.615971), (-58.434013, -34.615056), (-58.433904, -34.615005),
            (-58.433814, -34.615042), (-58.433706, -34.614989), (-58.433608, -34.61502),
            (-58.432559, -34.614571), (-58.432523, -34.614465), (-58.432345, -34.614403),
            (-58.432234, -34.614435), (-58.430955, -34.613844), (-58.430431, -34.613602),
            (-58.430375, -34.613523), (-58.430199, -34.613436), (-58.430194, -34.613523),
            (-58.430145, -34.613556), (-58.43013, -34.613945), (-58.430177, -34.61401),
            (-58.430352, -34.614093), (-58.430445, -34.614238), (-58.430407, -34.614813),
            (-58.430382, -34.615187), (-58.430308, -34.615257), (-58.430206, -34.615483),
            (-58.429469, -34.615151), (-58.429306, -34.615842), (-58.429043, -34.617101),
            (-58.428876, -34.617901), (-58.428798, -34.618253), (-58.42866, -34.618833),
            (-58.428259, -34.620678), (-58.42794, -34.622163), (-58.424144, -34.621604),
            (-58.422233, -34.621454), (-58.422202, -34.621413), (-58.422091, -34.621447),
            (-58.421315, -34.621396), (-58.421214, -34.621409), (-58.420826, -34.621379),
            (-58.420665, -34.621348), (-58.420348, -34.621319), (-58.419548, -34.621245),
            (-58.418367, -34.62118), (-58.416597, -34.621083), (-58.415258, -34.62097),
            (-58.413982, -34.620861), (-58.412477, -34.620734), (-58.410846, -34.620428),
            (-58.409268, -34.620131), (-58.4079, -34.619798), (-58.403898, -34.618931),
            (-58.400513, -34.618731), (-58.397776, -34.618567), (-58.397794, -34.618338),
            (-58.396631, -34.618262), (-58.396547, -34.618329), (-58.396503, -34.618465),
            (-58.395009, -34.618411), (-58.394784, -34.618401), (-58.393552, -34.618345),
            (-58.392105, -34.618276), (-58.392079, -34.617007), (-58.392055, -34.615849),
            (-58.392074, -34.615045), (-58.392084, -34.613943), (-58.392136, -34.612832),
            (-58.392139, -34.612771), (-58.392189, -34.611589), (-58.392237, -34.610433),
            (-58.392246, -34.610333), (-58.392124, -34.610263), (-58.392183, -34.609313),
            (-58.392186, -34.609285), (-58.392295, -34.608077), (-58.392595, -34.604639),
            (-58.392609, -34.604485), (-58.39276, -34.603185), (-58.392882, -34.602139),
            (-58.393026, -34.600925), (-58.393164, -34.599766), (-58.393182, -34.599608),
            (-58.396017, -34.599727), (-58.396177, -34.599733), (-58.397478, -34.599794),
            (-58.398947, -34.59981), (-58.399174, -34.599785), (-58.401309, -34.599552),
            (-58.402342, -34.599454), (-58.402779, -34.599231), (-58.403963, -34.598549),
            (-58.404121, -34.598458), (-58.404087, -34.598362), (-58.403842, -34.597682),
            (-58.403738, -34.597388), (-58.403469, -34.596635), (-58.403405, -34.596453),
            (-58.403518, -34.596412), (-58.403554, -34.59634), (-58.404443, -34.59605),
            (-58.404403, -34.595388), (-58.404449, -34.595317), (-58.404371, -34.59515),
            (-58.40456, -34.595058), (-58.404606, -34.59488), (-58.405729, -34.594292),
            (-58.406065, -34.594117), (-58.406283, -34.594141), (-58.406444, -34.594056),
            (-58.406603, -34.594219), (-58.406726, -34.594239), (-58.407471, -34.593842),
            (-58.407506, -34.593707), (-58.40748, -34.593503), (-58.407697, -34.593386),
            (-58.407724, -34.593259), (-58.408433, -34.592901), (-58.408553, -34.592926),
            (-58.4088, -34.592906), (-58.408878, -34.592776), (-58.40977, -34.592659),
            (-58.409919, -34.592716), (-58.410126, -34.592669), (-58.410226, -34.592817),
            (-58.410355, -34.592859), (-58.411153, -34.592672), (-58.411055, -34.592444),
            (-58.41108, -34.592309), (-58.411664, -34.592135), (-58.41179, -34.592154),
            (-58.412001, -34.592024), (-58.412012, -34.591887), (-58.41238, -34.591627),
            (-58.411504, -34.590604), (-58.411539, -34.590459), (-58.411641, -34.59036),
            (-58.413193, -34.59221), (-58.413939, -34.593101), (-58.413824, -34.593193),
            (-58.41381, -34.593318), (-58.413601, -34.593487), (-58.414206, -34.594253),
            (-58.414362, -34.594419), (-58.414471, -34.594418), (-58.414568, -34.594372),
            (-58.414777, -34.594368), (-58.414851, -34.594411), (-58.414928, -34.594612),
            (-58.414868, -34.594691), (-58.41495, -34.594947), (-58.41673, -34.594903),
            (-58.416822, -34.595345), (-58.416954, -34.595421), (-58.416865, -34.595606),
            (-58.416791, -34.595661), (-58.416912, -34.596507), (-58.417039, -34.596567),
            (-58.417072, -34.596754), (-58.416988, -34.596827), (-58.417118, -34.597623),
            (-58.417243, -34.597698), (-58.417258, -34.597853), (-58.417275, -34.597853),
            (-58.420275, -34.597794), (-58.422651, -34.597802), (-58.42331, -34.597804),
            (-58.42355, -34.597739), (-58.423528, -34.59786), (-58.426669, -34.597916),
            (-58.429222, -34.598919), (-58.429858, -34.599403), (-58.430303, -34.599843),
            (-58.432143, -34.601919), (-58.432291, -34.602086), (-58.432608, -34.602009),
            (-58.433481, -34.601708), (-58.433569, -34.601806), (-58.433567, -34.601881),
            (-58.433634, -34.601918), (-58.433169, -34.602357), (-58.433192, -34.602452),
            (-58.433141, -34.60253), (-58.433517, -34.602715), (-58.435337, -34.603617),
            (-58.436124, -34.604008), (-58.436085, -34.604083), (-58.436544, -34.604273),
            (-58.43924, -34.605553), (-58.441577, -34.606203), (-58.443101, -34.606622),
            (-58.445876, -34.607384), (-58.446164, -34.607396), (-58.446123, -34.607741),
            (-58.445471, -34.607853), (-58.444641, -34.608995), (-58.444781, -34.609179),
            (-58.444806, -34.609289), (-58.445199, -34.609439), (-58.445343, -34.609396),
            (-58.445533, -34.609469), (-58.445556, -34.609558), (-58.445678, -34.609601),
            (-58.445752, -34.609554), (-58.445952, -34.60963), (-58.445977, -34.609727),
            (-58.44619, -34.609807), (-58.446287, -34.60976), (-58.446461, -34.609827),
            (-58.446492, -34.609919), (-58.446627, -34.609964), (-58.446696, -34.609918),
            (-58.44694, -34.610011), (-58.447041, -34.610124), (-58.447046, -34.611033),
            (-58.447619, -34.61125), (-58.447645, -34.61132), (-58.447821, -34.611386),
            (-58.447716, -34.611559), (-58.447742, -34.611624), (-58.447318, -34.612364),
            (-58.447227, -34.612371), (-58.447052, -34.612304), (-58.447034, -34.612246),
            (-58.446949, -34.612216), (-58.446896, -34.612245), (-58.44685, -34.612446),
            (-58.446888, -34.612512), (-58.447822, -34.612891), (-58.447908, -34.612868),
            (-58.448159, -34.612968), (-58.448177, -34.613028), (-58.447716, -34.613805),
            (-58.447641, -34.613824), (-58.447527, -34.614012), (-58.447546, -34.614077),
            (-58.447068, -34.614883), (-58.446988, -34.614906), (-58.446764, -34.61481),
            (-58.446773, -34.615032), (-58.446861, -34.615132), (-58.446904, -34.615737),
            (-58.44684, -34.615802), (-58.446845, -34.616015), (-58.446917, -34.616061),
            (-58.446895, -34.616552), (-58.446811, -34.616603), (-58.446798, -34.616793),
            (-58.446858, -34.616842), (-58.446812, -34.617493), (-58.446748, -34.617533),
            (-58.446723, -34.617715), (-58.446792, -34.61781), (-58.446707, -34.618596),
            (-58.446387, -34.620366), (-58.448044, -34.621039)
        ]
    },
    # AQUI DEBES AGREGAR EL RESTO DE TUS POLIGONOS SIGUIENDO EL MISMO FORMATO:
    # {
    #     "nombre_operacion": "Otro Barrio",
    #     "coordenadas": [ (lon1, lat1), (lon2, lat2), ... ]
    # },
    # ...
]

# --- MAPEO DE OPERACIONES A ZONAS (Norte/Sur) DIRECTAMENTE EN EL CÓDIGO ---
# IMPORTANTE: DEBES REEMPLAZAR ESTE DICCIONARIO CON TU MAPEO COMPLETO.
# La clave debe ser el 'nombre_operacion' que usas en POLIGONOS_DEFINIDOS.
MAPEO_ZONAS_ESTATICO = {
    "Almagro": "Capital Sur",
    "Villa Crespo": "Capital Norte", # EJEMPLO: Reemplaza con tus datos reales
    "Palermo": "Capital Norte",      # EJEMPLO: Reemplaza con tus datos reales
    "San Telmo": "Capital Sur",      # EJEMPLO: Reemplaza con tus datos reales
    # ... agrega aquí todas tus operaciones/barrios y su clasificación
}


# Diccionario de correcciones para nombres de calles (se mantiene)
# Este diccionario es bastante extenso y puede ser externalizado a un archivo si es muy grande.
CORRECCIONES_CALLES = {
    "MACHU PICHU": "Machu Picchu", "11 DE MAYO": "Once de Mayo", "ULLA ULLA": "Ulla Ulla",
    "TALAMPAYA": "Talampaya", "AMOR PORTEÑO": "Amor Porteño", "EVITA": "Evita",
    "SUCRE MRCAL A J DE": "Sucre", "URQUIZA JUSTO JOSE DE": "Justo José de Urquiza",
    "CORREA CIRILO": "Cirilo Correa", "ROCA JULIO A": "Julio Argentino Roca",
    "CHACABUCO": "Chacabuco", "PEREZ AMARANTE ANTONIO": "Antonio Perez Amarante",
    "ROCHA JUAN JOSE DE": "Juan Jose de Rocha", "DE LA SERNA RAFAEL": "Rafael de la Serna",
    "DIAZ FELIX DE": "Félix de Díaz", "HERRERA SANTIAGO": "Santiago Herrera",
    "RAMOS MEJIA JOSE M": "José María Ramos Mejía", "ESPARZA JUAN": "Juan de Esparza",
    "ARENALES JUAN A": "Juan Antonio Arenales", "LOZANO PEDRO DE": "Pedro de Lozano",
    "ALTO DE LA SIERRA": "Alto de la Sierra", "CAÑADA DE GOMEZ": "Cañada de Gómez",
    "CIUDAD DE CARACAS": "Ciudad de Caracas", "GUALEGUAYCHU": "Gualeguaychú",
    "LUJAN": "Luján", "TUCUMAN": "Tucumán", "RIVADAVIA BERNARDINO": "Bernardino Rivadavia",
    "SAN MARTIN JOSE FCO DE": "José de San Martín", "BELGRANO MANUEL": "Manuel Belgrano",
    "SANTA FE": "Santa Fe", "CORDOBA": "Córdoba", "ENTRE RIOS": "Entre Ríos",
    "CORRIENTES": "Corrientes", "JUJUY": "Jujuy", "SALTA": "Salta", "MENDOZA": "Mendoza",
    "NEUQUEN": "Neuquén", "BUENOS AIRES": "Buenos Aires", "LA PAMPA": "La Pampa",
    "RIO NEGRO": "Río Negro", "CHUBUT": "Chubut", "SAN LUIS": "San Luis", "SAN JUAN": "San Juan",
    "LA RIOJA": "La Rioja", "CATAMARCA": "Catamarca", "SANTIAGO DEL ESTERO": "Santiago del Estero",
    "CHACO": "Chaco", "FORMOSA": "Formosa", "MISIONES": "Misiones",
    "TIERRA DEL FUEGO": "Tierra del Fuego", "URUGUAY": "Uruguay", "PARAGUAY": "Paraguay",
    "BOLIVIA": "Bolivia", "CHILE": "Chile", "BRASIL": "Brasil", "COLOMBIA": "Colombia",
    "PERU": "Perú", "ECUADOR": "Ecuador", "VENEZUELA": "Venezuela", "MEXICO": "México",
    "CANADA": "Canadá", "ESTADOS UNIDOS": "Estados Unidos", "ESPAÑA": "España", "ITALIA": "Italia",
    "FRANCIA": "Francia", "ALEMANIA": "Alemania", "INGLATERRA": "Inglaterra", "RUSIA": "Rusia",
    "CHINA": "China", "JAPON": "Japón", "INDIA": "India", "AUSTRALIA": "Australia",
    "EGIPTO": "Egipto", "SUDAFRICA": "Sudáfrica", "NIGERIA": "Nigeria", "KENIA": "Kenia",
    "ETIOPIA": "Etiopía", "MARRUECOS": "Marruecos", "ARGELIA": "Argelia", "SUDAN": "Sudán",
    "MADAGASCAR": "Madagascar", "CONGO": "Congo", "TANZANIA": "Tanzania", "UGANDA": "Uganda",
    "MOZAMBIQUE": "Mozambique", "ZIMBABWE": "Zimbabue", "ZAMBIA": "Zambia", "ANGOLA": "Angola",
    "CAMERUN": "Camerún", "COSTA DE MARFIL": "Costa de Marfil", "GHANA": "Ghana",
    "SENEGAL": "Senegal", "MALI": "Malí", "NIGER": "Níger", "BURKINA FASO": "Burkina Faso",
    "CHAD": "Chad", "SOMALIA": "Somalia", "LIBIA": "Libia", "TUNEZ": "Túnez", "SIRIA": "Siria",
    "IRAQ": "Iraq", "IRAN": "Irán", "ARABIA SAUDITA": "Arabia Saudita", "TURQUIA": "Turquía",
    "GRECIA": "Grecia", "POLONIA": "Polonia", "UCRANIA": "Ucrania", "SUECIA": "Suecia",
    "NORUEGA": "Noruega", "FINLANDIA": "Finlandia", "DINAMARCA": "Dinamarca", "HOLANDA": "Holanda",
    "BELGICA": "Bélgica", "SUIZA": "Suiza", "AUSTRIA": "Austria", "PORTUGAL": "Portugal",
    "IRLANDA": "Irlanda", "ESCOCIA": "Escocia", "GALES": "Gales", "AFGANISTAN": "Afganistán",
    "PAKISTAN": "Pakistán", "BANGLADESH": "Bangladesh", "SRI LANKA": "Sri Lanka",
    "NEPAL": "Nepal", "BHUTAN": "Bután", "MYANMAR": "Myanmar", "TAILANDIA": "Tailandia",
    "VIETNAM": "Vietnam", "LAOS": "Laos", "CAMBOYA": "Camboya", "MALASIA": "Malasia",
    "INDONESIA": "Indonesia", "FILIPINAS": "Filipinas", "SINGAPUR": "Singapur", "BRUNEI": "Brunéi",
    "TIMOR ORIENTAL": "Timor Oriental", "PAPUA NUEVA GUINEA": "Papúa Nueva Guinea",
    "NUEVA ZELANDIA": "Nueva Zelanda", "FIJI": "Fiyi", "SAMOA": "Samoa", "TONGA": "Tonga",
    "VANUATU": "Vanuatu", "ISLAS SALOMON": "Islas Salomón", "MICRONESIA": "Micronesia",
    "MARSHALL": "Marshall", "KIRIBATI": "Kiribati", "NAURU": "Nauru", "TUVALU": "Tuvalu",
    "PALAU": "Palaos", "ISLAS COOK": "Islas Cook", "NIUE": "Niue", "TOKELAU": "Tokelau",
    "WALLIS Y FUTUNA": "Wallis y Futuna", "NUEVA CALEDONIA": "Nueva Caledonia",
    "POLINESIA FRANCESA": "Polinesia Francesa", "ISLAS MALVINAS": "Islas Malvinas"
}


# --- Carga y preparación de datos (GLOBALMENTE al inicio del script) ---
# Esto asegura que los datos se carguen y preparen solo una vez cuando el bot se inicia.
gdf_poligonos = None

try:
    logger.info("Construyendo GeoDataFrame de polígonos desde datos definidos en el script...")
    # Crear una lista de diccionarios para el GeoDataFrame
    polygons_data = []
    for operacion_data in POLIGONOS_DEFINIDOS:
        nombre = operacion_data["nombre_operacion"]
        coords = operacion_data["coordenadas"]
        polygons_data.append({'Operacion': nombre, 'geometry': Polygon(coords)})

    # Crear el GeoDataFrame
    gdf_poligonos = gpd.GeoDataFrame(polygons_data, crs="EPSG:4326") # CRS para lat/lon
    logger.info(f"Polígonos cargados y GeoDataFrame construido exitosamente. Cantidad de polígonos: {len(gdf_poligonos)}")
except Exception as e:
    logger.error(f"Error CRÍTICO al construir GeoDataFrame de polígonos: {e}", exc_info=True)
    print(f"❌ Error CRÍTICO: No se pudieron construir los polígonos desde la definición en el script. Revise el formato de 'POLIGONOS_DEFINIDOS'.")
    exit(1)


# --- Funciones de Normalización y Geocodificación ---

def limpiar_direccion(direccion: str) -> str:
    """Limpia la dirección removiendo caracteres especiales y duplicados de espacio."""
    direccion = re.sub(r'[^a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s]', '', direccion)
    direccion = re.sub(r'\s+', ' ', direccion).strip()
    return direccion

def separar_direccion_altura(direccion_limpia: str) -> tuple[str, str]:
    """Separa la dirección en nombre de calle y altura."""
    match = re.search(r'(\d+)$', direccion_limpia)
    if match:
        altura = match.group(1)
        direccion = direccion_limpia[:match.start()].strip()
    else:
        altura = ""
        direccion = direccion_limpia
    return direccion, altura

def normalizar_nombre_calle(nombre_calle: str) -> str:
    """Normaliza el nombre de la calle usando el diccionario de correcciones."""
    return CORRECCIONES_CALLES.get(nombre_calle.upper(), nombre_calle)

def normalizar_direccion(direccion: str, altura: str, errores: list, original_input: str) -> tuple[str, float | None, float | None, str | None]:
    """
    Normaliza la dirección utilizando la API de Nominatim y retorna
    la dirección normalizada, coordenadas y el nombre del barrio.
    """
    logger.info(f"Normalizando dirección: {direccion}, altura: {altura}")

    # Conectar con sesión de requests con reintentos
    session = requests.Session()
    retry = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    # Construir la consulta para Nominatim
    query_parts = [direccion]
    if altura:
        query_parts.insert(0, altura) # La altura va antes del nombre de la calle en Nominatim

    # Asegúrate de especificar una localidad para mejorar la precisión
    query_parts.append("Ciudad Autónoma de Buenos Aires, Argentina") # Añadir CABA para mejor geocodificación

    query = ", ".join(query_parts)
    encoded_query = urllib.parse.quote(query)
    url = f"https://nominatim.openstreetmap.org/search?q={encoded_query}&format=json&limit=1&addressdetails=1"

    logger.info(f"Consulta a Nominatim: {url}")

    try:
        headers = {'User-Agent': 'BotClasificadorDirecciones/1.0'} # Requerido por Nominatim
        response = session.get(url, headers=headers, timeout=10) # Timeout para evitar esperas infinitas
        response.raise_for_status() # Lanza una excepción para errores HTTP (4xx o 5xx)
        data = response.json()

        if data and len(data) > 0:
            result = data[0]
            lat = float(result.get('lat'))
            lon = float(result.get('lon'))
            display_name = result.get('display_name', original_input)
            # Intentar obtener el barrio de 'address' si está disponible
            barrio = result.get('address', {}).get('suburb') or \
                     result.get('address', {}).get('neighbourhood') or \
                     result.get('address', {}).get('city_district') or \
                     result.get('address', {}).get('town')
            logger.info(f"Normalización exitosa: {display_name}, Lat: {lat}, Lon: {lon}, Barrio Nominatim: {barrio}")
            return display_name, lon, lat, barrio # Retornar lon, lat porque geopandas espera (x, y) = (lon, lat)
        else:
            errores.append(f"No se encontraron resultados para '{original_input}'.")
            logger.warning(f"No se encontraron resultados para '{original_input}'.")
            return original_input, None, None, None
    except requests.exceptions.RequestException as e:
        errores.append(f"Error de conexión al normalizar la dirección: {e}")
        logger.error(f"Error de conexión al normalizar la dirección '{original_input}': {e}")
        return original_input, None, None, None
    except json.JSONDecodeError as e:
        errores.append(f"Error al decodificar la respuesta JSON de la API: {e}")
        logger.error(f"Error JSON al normalizar la dirección '{original_input}': {e}")
        return original_input, None, None, None
    except Exception as e:
        errores.append(f"Ocurrió un error inesperado al normalizar la dirección: {e}")
        logger.error(f"Error inesperado al normalizar la dirección '{original_input}': {e}")
        return original_input, None, None, None
    finally:
        time.sleep(1) # Espera 1 segundo para cumplir con las políticas de uso de Nominatim


# --- Funciones de Clasificación Geográfica ---

def encontrar_operacion(x: float, y: float, gdf_poligonos: gpd.GeoDataFrame) -> str:
    """
    Encuentra la operación (barrio) a la que pertenece un punto (x, y) según los polígonos definidos.
    Args:
        x (float): Longitud del punto.
        y (float): Latitud del punto.
        gdf_poligonos (gpd.GeoDataFrame): GeoDataFrame con los polígonos y sus propiedades.
    Returns:
        str: El valor de la columna 'Operacion' para el polígono que contiene el punto,
             o "Barrio no clasificado por polígono" si no se encuentra.
    """
    point = Point(x, y)
    for index, row in gdf_poligonos.iterrows():
        # 'Operacion' es la columna creada a partir de 'nombre_operacion' en POLIGONOS_DEFINIDOS
        if row['geometry'].contains(point):
            return row['Operacion']
    return "Barrio no clasificado por polígono"


def clasificar_zona(operacion_o_barrio: str) -> str:
    """
    Clasifica una operación/barrio en 'Capital Norte', 'Capital Sur' o 'Desconocido'
    utilizando el diccionario MAPEO_ZONAS_ESTATICO.
    """
    return MAPEO_ZONAS_ESTATICO.get(operacion_o_barrio, "Desconocido")


# --- Funciones de Manejo de Comandos de Telegram ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envía un mensaje de bienvenida cuando el comando /start es emitido."""
    user = update.effective_user
    logger.info(f"Comando /start recibido de {user.full_name}")
    await update.message.reply_html(
        f"¡Hola {user.mention_html()}!\n"
        "Soy un bot que clasifica direcciones de CABA. "
        "Envíame una dirección (ej. 'Av. Corrientes 1234') y te diré si es Capital Norte o Sur, y a qué operación/barrio pertenece."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja los mensajes de texto, normaliza la dirección y clasifica la zona."""
    incoming_msg = update.message.text
    logger.info(f"Mensaje recibido: {incoming_msg}")
    errores = []

    # Limpiar y separar dirección y altura
    direccion_limpia = limpiar_direccion(incoming_msg)
    direccion_calle, altura = separar_direccion_altura(direccion_limpia)

    # Normalizar dirección y obtener coordenadas y barrio de Nominatim
    direccion_normalizada_display, x, y, barrio_nominatim = normalizar_direccion(direccion_calle, altura, errores, incoming_msg)

    # Determinar operación y zona
    if x is not None and y is not None:
        # Encontrar la "Operacion" dentro de los polígonos definidos
        operacion_encontrada_por_poligono = encontrar_operacion(x, y, gdf_poligonos)

        # Clasificar la "Zona" (Norte/Sur) usando el diccionario estático
        zona = clasificar_zona(operacion_encontrada_por_poligono)

        # --- AQUÍ ESTÁ EL MENSAJE MODIFICADO ---
        respuesta = (
            f"La dirección '{direccion_normalizada_display}' "
            f"pertenece al polígono *{operacion_encontrada_por_poligono}* "
            f"dentro de *{zona}*."
        )
    else:
        # Si hubo errores en la normalización, se añaden a 'errores'. Se muestra el primer error.
        error_msg = errores[0] if errores else "No se pudo normalizar la dirección. Asegúrate de que sea una dirección de CABA válida."
        respuesta = f"No se pudo clasificar la dirección '{incoming_msg}'. {error_msg}"

    # Enviar respuesta
    logger.info(f"Enviando respuesta: {respuesta}")
    await update.message.reply_text(respuesta, parse_mode='Markdown')


def main():
    logger.info("Iniciando el bot...")
    print("🚀 Bot iniciado...")
    try:
        # Configurar el bot
        application = Application.builder().token(TOKEN).build()

        # Agregar manejadores
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        # Iniciar polling
        logger.info("Iniciando polling...")
        application.run_polling()
    except Exception as e:
        logger.critical(f"Error CRÍTICO en la ejecución principal del bot: {e}", exc_info=True)
        print(f"❌ Un error crítico detuvo el bot: {e}")

if __name__ == "__main__":
    main()
