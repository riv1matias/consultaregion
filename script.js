// script.js

// Referencias a elementos del DOM
const addressForm = document.getElementById('addressForm');
const streetInput = document.getElementById('street');
const numberInput = document.getElementById('number');
const resultDiv = document.getElementById('result');
const loadingDiv = document.getElementById('loading');
const mapDiv = document.getElementById('map');

// Variable global para almacenar los polígonos cargados
let geoJsonPolygons = null;
let map = null; // Variable para el mapa Leaflet
let markerLayer = null; // Capa para el marcador del punto
let polygonLayer = null; // Capa para el polígono

// Diccionario de correcciones de calles (vacío según tu solicitud)
const CORRECCIONES_CALLES = {};

/**
 * Normaliza el nombre de una calle.
 * Elimina espacios extra, convierte a mayúsculas y aplica correcciones.
 * @param {string} calle - El nombre de la calle a normalizar.
 * @returns {string} La calle normalizada.
 */
function normalizarCalle(calle) {
    if (!calle) return "";
    calle = calle.trim();
    calle = calle.replace(/\s+/g, ' ');
    calle = calle.toUpperCase();
    return calle;
}

/**
 * Normaliza una dirección y la geocodifica usando Nominatim.
 * @param {string} direccion - El nombre de la calle.
 * @param {string} altura - La altura de la dirección.
 * @returns {Promise<Object|null>} Un objeto con lat, lon, y direccion_normalizada o null si falla.
 */
async function normalizarDireccion(direccion, altura) {
    let direccion_normalizada = `${normalizarCalle(direccion)} ${altura}`; // Declarada fuera del try

    if (!/^\d+$/.test(altura)) {
        console.error(`La altura '${altura}' no es un número válido.`);
        return null;
    }

    const encodedAddress = encodeURIComponent(`${direccion_normalizada}, CABA`);
    const url = `https://nominatim.openstreetmap.org/search?q=${encodedAddress}&format=json&limit=1&addressdetails=1`;
    const headers = { 'User-Agent': 'WebBotRegiones/1.0 (tu-email@example.com)' };

    try {
        const response = await fetch(url, { headers, timeout: 10000 });
        if (!response.ok) throw new Error(`Error HTTP: ${response.status} - ${response.statusText}`);
        const data = await response.json();

        if (data && data.length > 0) {
            const lat = parseFloat(data[0].lat);
            const lon = parseFloat(data[0].lon);
            return { direccion_normalizada, lat, lon };
        } else {
            console.warn(`Nominatim no encontró resultados para: ${direccion_normalizada}`);
            return null;
        }
    } catch (error) {
        console.error(`Error al normalizar dirección '${direccion_normalizada}':`, error);
        return null;
    }
}

/**
 * Carga el archivo GeoJSON de polígonos.
 * @returns {Promise<Object|null>} El objeto GeoJSON o null si falla.
 */
async function loadGeoJsonPolygons() {
    if (geoJsonPolygons) return geoJsonPolygons;
    try {
        const response = await fetch('poligonos_zonas.geojson');
        if (!response.ok) throw new Error(`Error al cargar GeoJSON: ${response.status} - ${response.statusText}`);
        geoJsonPolygons = await response.json();
        console.log("Polígonos GeoJSON cargados exitosamente.");
        return geoJsonPolygons;
    } catch (error) {
        console.error("Error al cargar el archivo GeoJSON:", error);
        throw error;
    }
}

/**
 * Encuentra a qué operación (polígono) pertenece un punto y devuelve el polígono.
 * @param {number} lon - Longitud del punto.
 * @param {number} lat - Latitud del punto.
 * @param {Object} geoJson - El objeto GeoJSON con los polígonos.
 * @returns {Object} Objeto con el nombre de la operación y el polígono.
 */
function encontrarOperacion(lon, lat, geoJson) {
    const point = turf.point([lon, lat]);
    for (const feature of geoJson.features) {
        if (feature.geometry && (feature.geometry.type === 'Polygon' || feature.geometry.type === 'MultiPolygon')) {
            if (turf.booleanPointInPolygon(point, feature.geometry)) {
                const operacion = feature.properties.operacion || "Operación sin nombre";
                console.log(`Operación encontrada: ${operacion}`);
                return { operacion, poligono: feature.geometry };
            }
        }
    }
    console.log("No se encontró ninguna operación para el punto.");
    return { operacion: "Desconocida", poligono: null };
}

/**
 * Calcula la distancia del punto al borde del polígono más cercano.
 * @param {number} lon - Longitud del punto.
 * @param {number} lat - Latitud del punto.
 * @param {Object} poligono - El polígono GeoJSON.
 * @returns {string} Mensaje sobre la distancia al borde (solo si < 100m).
 */
function calcularDistanciaAlBorde(lon, lat, poligono) {
    if (!poligono) return "";
    const point = turf.point([lon, lat]);
    const distancia = turf.pointToLineDistance(point, turf.polygonToLine(poligono), { units: 'meters' });
    if (distancia < 100) { // Umbral de 100 metros
        return `<br>El punto está a ${Math.round(distancia)} metros del límite del polígono.`;
    }
    return "";
}

/**
 * Clasifica la operación en una zona más general.
 * @param {string} operacion - El nombre de la operación.
 * @returns {string} La clasificación de la zona.
 */
function clasificarZona(operacion) {
    const operacionUpper = operacion.toUpperCase();
    const capitalSurZonas = ["ALMAGRO", "BOEDO", "SAN TELMO", "RECOLETA", "PALERMO"];
    const capitalNorteZonas = ["DEVOTO", "PATERNAL", "COLEGIALES", "SAAVEDRA"];
    if (capitalSurZonas.includes(operacionUpper)) return "Capital Sur";
    else if (capitalNorteZonas.includes(operacionUpper)) return "Capital Norte";
    else return "No se encontró en polígono";
}

/**
 * Inicializa o reinicia el mapa Leaflet.
 */
function inicializarMapa() {
    if (!map) {
        map = L.map('map').setView([-34.6037, -58.3816], 12); // Centro en CABA
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);
    } else {
        map.eachLayer((layer) => {
            if (layer instanceof L.TileLayer) return; // Preservar la capa de tiles
            map.removeLayer(layer);
        });
    }
}

// Manejador del envío del formulario
addressForm.addEventListener('submit', async (event) => {
    event.preventDefault();

    const street = streetInput.value;
    const number = numberInput.value;

    resultDiv.innerHTML = "";
    mapDiv.style.display = 'none';
    loadingDiv.style.display = 'block';

    try {
        const polygons = await loadGeoJsonPolygons();
        if (!polygons) {
            resultDiv.innerHTML = "<span class='error'>Error: No se pudieron cargar los datos de los polígonos.</span>";
            loadingDiv.style.display = 'none';
            return;
        }

        const geoResult = await normalizarDireccion(street, number);
        if (geoResult) {
            const { direccion_normalizada, lat, lon } = geoResult;
            const { operacion, poligono } = encontrarOperacion(lon, lat, polygons);
            const zona = clasificarZona(operacion);
            const mensajeDistancia = calcularDistanciaAlBorde(lon, lat, poligono);

            resultDiv.innerHTML = `
                La dirección *${direccion_normalizada}*<br>
                pertenece al polígono: <strong>${operacion}</strong><br>
                Clasificación de zona: <strong>${zona}</strong>${mensajeDistancia}
            `;

            inicializarMapa();
            mapDiv.style.display = 'block';

            // Limpiar capas anteriores
            if (markerLayer) map.removeLayer(markerLayer);
            if (polygonLayer) map.removeLayer(polygonLayer);

            // Agregar marcador
            markerLayer = L.marker([lat, lon]).addTo(map)
                .bindPopup(direccion_normalizada)
                .openPopup();
            console.log(`Marcador agregado en [${lat}, ${lon}]`);

            // Agregar polígono
            if (poligono) {
                polygonLayer = L.geoJSON(poligono, {
                    style: { color: '#007bff', weight: 2, fillOpacity: 0.2 }
                }).addTo(map);
                console.log("Polígono agregado al mapa");
            } else {
                console.log("No se encontró polígono para mostrar");
            }

            // Ajustar vista del mapa
            if (poligono && polygonLayer) {
                const group = L.featureGroup([markerLayer, polygonLayer]);
                map.fitBounds(group.getBounds(), { padding: [50, 50] });
                console.log("Mapa ajustado a los límites del polígono y marcador");
            } else {
                map.setView([lat, lon], 15);
                console.log("Mapa centrado en el marcador con zoom 15");
            }
        } else {
            resultDiv.innerHTML = "<span class='error'>No se pudo encontrar una ubicación precisa para la dirección ingresada. Intenta con otro formato o revisa la dirección.</span>";
        }
    } catch (error) {
        console.error("Error general en el proceso:", error);
        resultDiv.innerHTML = `<span class='error'>Ocurrió un error inesperado: ${error.message || 'Por favor, inténtalo de nuevo.'}</span>`;
    } finally {
        loadingDiv.style.display = 'none';
    }
});

// Inicializar el mapa al cargar la página
inicializarMapa();