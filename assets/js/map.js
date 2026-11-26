'use strict';


// 1. Centro del mapa y zoom inicial: Lalín.
const LALIN = [42.662257, -8.113559];
const ZOOM_INICIAL = 12;
const estado = document.getElementById('estado');

const mapa = L.map('map', { zoomControl: true }).setView(LALIN, ZOOM_INICIAL);

// 2. TRES CAPAS BASE. El mapa se puede abrir directamente como mapa.html.
// Las tres opciones se excluyen mutuamente y SOLO la primera está activa al inicio.
// No dependemos de las teselas de tile.openstreetmap.org (bloqueadas desde file:///).
const mapaCalles = L.tileLayer(
  'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
  { maxZoom: 19, attribution: 'Mapas &copy; Esri, HERE, Garmin; datos &copy; OpenStreetMap contributors' }
);
const mapaSatelite = L.tileLayer(
  'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
  { maxZoom: 19, attribution: 'Imágenes &copy; Esri, Vantor y GIS User Community' }
);

const topoPrincipal = L.tileLayer(
  'https://tile.opentopomap.org/{z}/{x}/{y}.png',
  { maxNativeZoom: 17, maxZoom: 19,
    attribution: 'Mapa: &copy; OpenTopoMap (CC BY-SA); datos &copy; OpenStreetMap contributors / SRTM' }
);
// Si OpenTopoMap está temporalmente indisponible, se muestra el relieve de ESRI.
const topoRespaldo = L.tileLayer(
  'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
  { maxZoom: 19, attribution: 'Mapa topográfico &copy; Esri; datos &copy; OpenStreetMap contributors' }
);
const mapaTopografico = L.layerGroup([topoPrincipal]);
let erroresTopograficos = 0;
let usandoRespaldoTopo = false;
topoPrincipal.on('tileerror', function() {
  erroresTopograficos++;
  if (!usandoRespaldoTopo && erroresTopograficos >= 3) {
    usandoRespaldoTopo = true;
    mapaTopografico.removeLayer(topoPrincipal);
    mapaTopografico.addLayer(topoRespaldo);
    console.warn('OpenTopoMap no responde: se muestra el mapa topográfico de Esri.');
  }
});
mapaCalles.addTo(mapa); // Sin overlays al iniciar.

// 3. Iconos 100 % personalizados (SVG incluidos en el ZIP).
function icono(ruta) {
  return L.icon({iconUrl: ruta, iconSize: [44, 54], iconAnchor: [22, 53], popupAnchor: [0, -46]});
}
const iconoLalin = icono('assets/icons/lalin.svg');
const iconoBK = icono('assets/icons/burger-king.svg');
const iconoMcD = icono('assets/icons/mcdonalds.svg');
const iconoKebab = icono('assets/icons/kebab.svg');

// Overlay 1: Lalín, en naranja, con popup de nombre y fotografía.
// La fotografía se guarda en local con preparar_datos.py. Si aún no está,
// se usa la referencia original de Wikimedia Commons (requiere Internet).
const popupLalin = `<div class="popup-nombre">Lalín · Pontevedra</div><p>Geographic reference point in central Galicia.</p><a href="https://commons.wikimedia.org/wiki/File:Praza_da_Vila.jpg" target="_blank" rel="noopener noreferrer">View photograph on Wikimedia Commons</a>`;
const capaPueblo = L.layerGroup([
  L.marker(LALIN, {icon: iconoLalin, title: 'Lalín'}).bindPopup(popupLalin, {maxWidth: 280})
]);

// Overlays 2 y 3: restaurantes normales y los mismos puntos clusterizados.
const capaRestaurantes = L.layerGroup();
const capaClusters = L.markerClusterGroup({
  maxClusterRadius: 58,
  chunkedLoading: true,
  iconCreateFunction: cluster => L.divIcon({
    html: `<div>${cluster.getChildCount()}</div>`, className:'cluster-personalizado', iconSize:[41,41]
  })
});

const capasBase = {
  'Esri Streets': mapaCalles,
  'Esri Satellite': mapaSatelite,
  'Topographic': mapaTopografico
};
const capasSuperpuestas = {
  'Lalín reference point': capaPueblo,
  'Individual locations': capaRestaurantes,
  'Clustered locations': capaClusters
};
L.control.layers(capasBase, capasSuperpuestas, {collapsed: window.innerWidth < 650, position:'topright'}).addTo(mapa);
L.control.scale({imperial:false}).addTo(mapa);
document.getElementById('volver-lalin').addEventListener('click', () => mapa.setView(LALIN, ZOOM_INICIAL));


function escaparHTML(valor) {
  return String(valor).replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
}

function tipoRestaurante(tags) {
  const texto = `${tags.brand || ''} ${tags.name || ''} ${tags['brand:en'] || ''}`;
  if (/burger\s*king/i.test(texto)) return 'burgerking';
  if (/mcdon/i.test(texto)) return 'mcdonalds';
  if (/kebab/i.test(`${tags.name || ''} ${tags.cuisine || ''}`)) return 'kebab';
  return null;
}

function popupParaRestaurante(tags, tipo) {
  const nombre = tipo === 'burgerking' ? 'Burger King'
    : tipo === 'mcdonalds' ? "McDonald's" : (tags.name || 'Unnamed kebab shop');
  // Segunda fila SOLO cuando OpenStreetMap tenga la etiqueta cuisine.
  const filaCocina = tags.cuisine ? `<tr><td>Cuisine: ${escaparHTML(tags.cuisine)}</td></tr>` : '';
  return `<table class="popup-tabla"><tbody><tr><td>${escaparHTML(nombre)}</td></tr>${filaCocina}</tbody></table>`;
}

function coordenadasOSM(elemento) {
  // node: lat/lon; way o relation: centro facilitado por "out center".
  const lat = elemento.lat ?? elemento.center?.lat;
  const lon = elemento.lon ?? elemento.center?.lon;
  return (Number.isFinite(lat) && Number.isFinite(lon)) ? [lat, lon] : null;
}

function volcarElementosOSM(elementos) {
  capaRestaurantes.clearLayers();
  capaClusters.clearLayers();
  const ids = new Set();
  const conteo = {burgerking:0, mcdonalds:0, kebab:0};
  const features = [];
  for (const elemento of elementos) {
    const identificador = `${elemento.type}/${elemento.id}`;
    if (ids.has(identificador)) continue; // Evita duplicados entre filtros Overpass.
    ids.add(identificador);
    const tags = elemento.tags || {};
    const tipo = tipoRestaurante(tags);
    if (!tipo) continue;
    const pos = coordenadasOSM(elemento);
    if (!pos) continue;
    // GeoJSON: longitude y despues latitude (al revés que L.marker).
    features.push({
      type: 'Feature',
      id: identificador,
      geometry: {type:'Point', coordinates:[pos[1], pos[0]]},
      properties: {...tags, tipoRestaurante: tipo}
    });
    conteo[tipo]++;
  }

  const restaurantesGeoJSON = {type:'FeatureCollection', features};
  
  function asociarPopup(feature, capa) {
    capa.bindPopup(popupParaRestaurante(feature.properties, feature.properties.tipoRestaurante));
  }
  function marcadorPersonalizado(feature, latlng) {
    const tipo = feature.properties.tipoRestaurante;
    const icon = tipo === 'burgerking' ? iconoBK : tipo === 'mcdonalds' ? iconoMcD : iconoKebab;
    return L.marker(latlng, {icon});
  }
  const opcionesGeoJSON = {onEachFeature: asociarPopup, pointToLayer: marcadorPersonalizado};
  capaRestaurantes.addLayer(L.geoJSON(restaurantesGeoJSON, opcionesGeoJSON));
  capaClusters.addLayer(L.geoJSON(restaurantesGeoJSON, opcionesGeoJSON));

  estado.classList.remove('error');
  document.getElementById('bk-count').textContent = conteo.burgerking;
  document.getElementById('mc-count').textContent = conteo.mcdonalds;
  document.getElementById('kebab-count').textContent = conteo.kebab;
  estado.textContent = `${features.length} mapped locations · OpenStreetMap snapshot · Use the layer selector to explore.`;
  if (features.length) mapa.fitBounds(L.geoJSON(restaurantesGeoJSON).getBounds(), {padding:[25,25]});
}

// 5. CARGAR DATOS LOCALES: los 160 elementos importados de GeoJSON.
// No consulta Overpass en cada apertura: el mapa funciona con data/puntos_osm.js.
if (Array.isArray(window.OSM_ELEMENTOS)) {
  volcarElementosOSM(window.OSM_ELEMENTOS);
  capaClusters.addTo(mapa);
  capaPueblo.addTo(mapa);
} else {
  estado.classList.add('error');
  estado.textContent = 'No data loaded. Run scripts/prepare_data.py to regenerate the dataset.';
}

  