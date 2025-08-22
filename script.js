document.addEventListener('DOMContentLoaded', () => {
    // --- ELEMENTOS DEL BUSCADOR 1 (DIRECCIÓN) ---
    const addressInput = document.getElementById('addressInput');
    const addressSearchButton = document.getElementById('addressSearchButton');
    const addressResultsDiv = document.getElementById('addressResults');

    // --- ELEMENTOS DEL BUSCADOR 2 (ZONA) ---
    const zoneInput = document.getElementById('zoneInput');
    const zoneSearchButton = document.getElementById('zoneSearchButton');
    const zoneResultsDiv = document.getElementById('zoneResults');

    const regionMapping = {
        'Paternal': 'Capital Norte', 'Saavedra': 'Capital Norte', 'Devoto': 'Capital Norte', 'Colegiales': 'Capital Norte',
        'Boedo': 'Capital Sur', 'San Telmo': 'Capital Sur', 'Almagro': 'Capital Sur', 'Palermo': 'Capital Sur', 'Recoleta': 'Capital Sur'
    };
    
    function normalizeAddress(address) {
        let cleanAddress = address.toUpperCase();
        const streetCorrections = { "MACHU PICHU": "Machu Picchu", "11 DE MAYO": "Once de Mayo", "ULLA ULLA": "Ulla Ulla", "TALAMPAYA": "Talampaya", "AMOR PORTEÑO": "Amor Porteño", "EVITA": "Evita", "SUCRE MRCAL A J DE": "Sucre", "URQUIZA JUSTO JOSE DE": "Justo José de Urquiza", "CORREA CIRILO": "Correa", "BERUTI ANTONIO": "Beruti", "VEDIA NICOLAS DE": "Vedia", "MAGARIÑOS CERVANTES": "Magariños Cervantes", "YUPANQUI ATAHUALPA": "Atahualpa Yupanqui", "DE ANDREA ANGEL": "Angel De Andrea", "DE LA SERNA GREGORIA": "Gregoria de la Serna", "DE ELIA FELIPE": "Felipe De Elia", "DIAZ VELEZ EUSTOQUIO": "Eustoquio Diaz Velez", "DEL CAMPO ANGEL": "Angel del Campo", "FALCON RAMON": "Ramon Falcon", "FIGUEROA ALCORTA": "Figueroa Alcorta", "GARCIA DEL RIO": "Garcia del Rio", "GUTIERREZ JOSE M": "Jose M Gutierrez", "HEREDIA JOSE": "Jose Heredia", "IRIGOYEN HIPOLITO": "Hipolito Yrigoyen", "LA FAYETTE": "Lafayette", "LAS HERAS": "Las Heras", "LE BRETON TOMAS": "Tomas Le Breton", "LUGONES LEOPOLDO": "Leopoldo Lugones", "MORETO CLAUDIO": "Claudio Moreto", "OBLIGADO RAFAEL": "Rafael Obligado", "PAZ SOLDAN": "Paz Soldan", "PEÑA LUIS": "Luis Peña", "ROCA JULIO": "Julio Roca", "SAENZ PEÑA": "Saenz Peña", "SAN MARTIN": "San Martin", "TORRE Y Tagle": "Torre Tagle" };
        for (const [key, value] of Object.entries(streetCorrections)) {
            if (cleanAddress.includes(key)) {
                cleanAddress = cleanAddress.replace(key, value);
            }
        }
        cleanAddress = cleanAddress.replace(/\s*\(.*?\)\s*/g, ' ').replace(/^\s*AV\.\s*|^\s*AV\s+/i, 'Avenida ').replace("CNEL.", "Coronel").replace("GRAL.", "General").replace("PRES.", "Presidente").replace("PTE.", "Presidente").replace("ING.", "Ingeniero").replace(/ y /gi, ' E ').replace(/[^a-zA-Z0-9\s]/g, '');
        return cleanAddress.trim().replace(/\s+/g, ' ');
    }

    function isPointInPolygon(point, polygon) {
        const [lon, lat] = point;
        let isInside = false;
        for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
            const [xi, yi] = polygon[i];
            const [xj, yj] = polygon[j];
            const intersect = ((yi > lat) !== (yj > lat)) && (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi);
            if (intersect) isInside = !isInside;
        }
        return isInside;
    }

    function findClosestZone(point, zones) {
        let closestZone = null;
        let minDistance = Infinity;
        const [lon1, lat1] = point;
        const validZones = zones.filter(zone => zone.nombre !== "Zona no identificada" && zone.centro);
        for (const zone of validZones) {
            const { lon: lon2, lat: lat2 } = zone.centro;
            const distance = Math.sqrt(Math.pow(lon1 - lon2, 2) + Math.pow(lat1 - lat2, 2));
            if (distance < minDistance) {
                minDistance = distance;
                closestZone = zone.nombre;
            }
        }
        return closestZone;
    }

    function findZone(point, zones, findClosestFallback = false) {
        if (!Array.isArray(zones)) return "Datos no cargados";
        let foundZoneName = null;
        for (const zone of zones) {
            if (isPointInPolygon(point, zone.coordenadas)) {
                foundZoneName = zone.nombre;
                break;
            }
        }
        if (findClosestFallback && (!foundZoneName || foundZoneName === "Zona no identificada")) {
             const closest = findClosestZone(point, zones);
             return `${closest} <i>(zona más cercana)</i>`;
        }
        return foundZoneName || "Fuera de área";
    }

    // --- LÓGICA BUSCADOR 1: POR DIRECCIÓN ---
    async function handleAddressSearch() {
        const rawAddress = addressInput.value.trim();
        if (!rawAddress) return;
        addressResultsDiv.innerHTML = `<div class="loading">Buscando...</div>`;
        const normalizedAddress = normalizeAddress(rawAddress);
        try {
            const apiUrl = `https://servicios.usig.buenosaires.gob.ar/normalizar?direccion=${encodeURIComponent(normalizedAddress)}, CABA`;
            const response = await fetch(apiUrl);
            const data = await response.json();
            if (data.direccionesNormalizadas && data.direccionesNormalizadas.length > 0) {
                const location = data.direccionesNormalizadas[0];
                const point = [parseFloat(location.coordenadas.x), parseFloat(location.coordenadas.y)];
                const zonaOp = findZone(point, zonasOperativas, true);
                const subregion = findZone(point, subregiones);
                const region = regionMapping[subregion] || (subregion === "Fuera de área" ? "Fuera de área" : "No definida");
                addressResultsDiv.innerHTML = `
                    <div class="result-item"><strong>Dirección:</strong> ${location.direccion}</div>
                    <div class="result-item"><strong>Zona Operativa:</strong> ${zonaOp}</div>
                    <div class="result-item"><strong>Subregión:</strong> ${subregion}</div>
                    <div class="result-item"><strong>Región:</strong> ${region}</div>`;
            } else {
                addressResultsDiv.innerHTML = `<div class="error">No se encontraron coordenadas para: "${normalizedAddress}".</div>`;
            }
        } catch (error) {
            addressResultsDiv.innerHTML = `<div class="error">Error al conectar con el servicio de direcciones.</div>`;
            console.error("Error:", error);
        }
    }

    // --- LÓGICA BUSCADOR 2: POR ZONA OPERATIVA ---
    function handleZoneSearch() {
        const zoneName = zoneInput.value.trim().toUpperCase();
        if (!zoneName) return;

        // 1. Encontrar la zona operativa en nuestros datos
        const foundZone = zonasOperativas.find(z => z.nombre.toUpperCase() === zoneName);

        if (!foundZone || !foundZone.centro) {
            zoneResultsDiv.innerHTML = `<div class="error">Zona Operativa no encontrada o sin datos de centro.</div>`;
            return;
        }

        // 2. Usar el centroide de la zona para ver en qué subregión cae
        const point = [foundZone.centro.lon, foundZone.centro.lat];
        const subregion = findZone(point, subregiones);
        const region = regionMapping[subregion] || (subregion === "Fuera de área" ? "Fuera de área" : "No definida");
        
        zoneResultsDiv.innerHTML = `
            <div class="result-item"><strong>Zona Operativa:</strong> ${foundZone.nombre}</div>
            <div class="result-item"><strong>Subregión:</strong> ${subregion}</div>
            <div class="result-item"><strong>Región:</strong> ${region}</div>`;
    }

    // --- EVENT LISTENERS ---
    addressSearchButton.addEventListener('click', handleAddressSearch);
    addressInput.addEventListener('keypress', (event) => { if (event.key === 'Enter') handleAddressSearch(); });

    zoneSearchButton.addEventListener('click', handleZoneSearch);
    zoneInput.addEventListener('keypress', (event) => { if (event.key === 'Enter') handleZoneSearch(); });
});