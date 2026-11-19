/**
 * AlertaForestal Perú — Lógica principal del portal ciudadano
 * Conecta con la API FastAPI backend (http://localhost:8000)
 * Maneja mapa Leaflet, focos NASA FIRMS, formularios, métricas y animaciones.
 */

/* ═══════════════════════════════════════════════════
   CONFIGURACIÓN GLOBAL
   ═══════════════════════════════════════════════════ */
// Detección dinámica de API_URL: en producción usa el dominio actual (HTTPS/HTTP),
// y en entorno local usa http://127.0.0.1:5050
const API_URL = (typeof window !== 'undefined' && window.location && (window.location.protocol === 'http:' || window.location.protocol === 'https:'))
  ? window.location.origin
  : 'http://127.0.0.1:5050';

// NASA FIRMS — SIEMPRE vía proxy FastAPI (/firms/hotspots).
// La API key vive únicamente en el backend (FIRMS_MAP_KEY en .env); nunca se
// expone en el frontend.

// Bounding boxes predefinidas (minLon, minLat, maxLon, maxLat)
const FIRMS_BBOXES = {
  all:       '-81.5,-18.5,-68.5,0',
  cajamarca: '-79.4517,-7.7592,-77.7389,-4.5519',
  norte:     '-80.5,-6.0,-75.0,0',
  sur:       '-81.5,-18.5,-68.5,-6.0',
};

// Puntos cardinales de lectura y límites geográficos de Cajamarca
const CAJAMARCA_EXTREMES = [
  {
    cardinal: 'Norte',
    subtitle: 'Punto más septentrional',
    lat: -4.551944,
    lon: -78.707500,
    latDMS: '04° 33′ 07″ S',
    lonDMS: '78° 42′ 27″ O',
    desc: 'Frontera internacional con Ecuador, en la cordillera Campanquiz.',
    badgeColor: '#38bdf8'
  },
  {
    cardinal: 'Sur',
    subtitle: 'Punto más meridional',
    lat: -7.759167,
    lon: -78.220556,
    latDMS: '07° 45′ 33″ S',
    lonDMS: '78° 13′ 14″ O',
    desc: 'Límite con La Libertad.',
    badgeColor: '#f59e0b'
  },
  {
    cardinal: 'Este',
    subtitle: 'Punto más oriental',
    lat: -7.463056,
    lon: -77.738889,
    latDMS: '07° 27′ 47″ S',
    lonDMS: '77° 44′ 20″ O',
    desc: 'Punto sobre el río Marañón.',
    badgeColor: '#10b981'
  },
  {
    cardinal: 'Oeste',
    subtitle: 'Punto más occidental',
    lat: -6.394722,
    lon: -79.451667,
    latDMS: '06° 23′ 41″ S',
    lonDMS: '79° 27′ 06″ O',
    desc: 'Línea de cumbre del cerro Carrampón.',
    badgeColor: '#a855f7'
  }
];

const CAJAMARCA_BBOX = {
  south: -7.759167,
  north: -4.551944,
  west:  -79.451667,
  east:  -77.738889
};

// Sub-regiones y provincias de Cajamarca para navegación y filtro real del mapa IA
const AI_REGION_BBOX = {
  cajamarca:      { south: -7.7592, north: -4.5519, west: -79.4517, east: -77.7389 },
  prov_cajamarca: { south: -7.50,   north: -6.82,   west: -78.80,   east: -78.18   },
  chota:          { south: -6.78,   north: -6.20,   west: -79.22,   east: -78.30   },
  celendin:       { south: -7.20,   north: -6.50,   west: -78.35,   east: -77.82   },
  bambamarca:     { south: -6.92,   north: -6.50,   west: -78.82,   east: -78.35   },
  san_marcos:     { south: -7.58,   north: -7.12,   west: -78.35,   east: -77.80   },
  san_pablo:      { south: -7.30,   north: -6.92,   west: -78.98,   east: -78.55   },
  jaen:           { south: -6.05,   north: -5.30,   west: -79.35,   east: -78.55   },
  san_ignacio:    { south: -5.45,   north: -4.55,   west: -79.40,   east: -78.58   },
  cutervo:        { south: -6.48,   north: -5.92,   west: -79.15,   east: -78.42   },
  cajabamba:      { south: -7.76,   north: -7.35,   west: -78.38,   east: -77.85   },
  norte:          { south: -6.16,   north: -4.5519, west: -79.4517, east: -77.7389 },
  sur:            { south: -7.7592, north: -6.16,   west: -79.4517, east: -77.7389 },
  all:            null,
};
let currentRegion = 'cajamarca';

// Límite oficial del departamento de Cajamarca
// Fuente: INEI Perú / juaneladio/peru-geojson (peru_departamental_simple.geojson)
// 118 vértices — límite administrativo oficial
const CAJAMARCA_BORDER = [
  [-7.02568,-79.32259],[-6.99983,-79.29663],[-6.90134,-79.31101],[-6.85916,-79.26274],
  [-6.77697,-79.12085],[-6.70154,-79.14156],[-6.69563,-79.21379],[-6.67141,-79.22906],
  [-6.67567,-79.29642],[-6.54952,-79.36699],[-6.54073,-79.40328],[-6.47972,-79.43129],
  [-6.45188,-79.42289],[-6.39684,-79.45349],[-6.31043,-79.42266],[-6.30429,-79.35356],
  [-6.26306,-79.32179],[-6.22669,-79.25226],[-6.14673,-79.27253],[-6.05501,-79.22399],
  [-6.00246,-79.26434],[-5.97010,-79.41861],[-5.89363,-79.33407],[-5.79109,-79.38982],
  [-5.74951,-79.40069],[-5.60619,-79.37555],[-5.53702,-79.39832],[-5.51898,-79.27240],
  [-5.45813,-79.29770],[-5.31591,-79.32807],[-5.28863,-79.35905],[-5.23258,-79.34865],
  [-5.19052,-79.37841],[-5.11048,-79.29436],[-5.00136,-79.24509],[-4.96524,-79.21007],
  [-4.97105,-79.07354],[-5.01399,-79.01195],[-4.89702,-78.97389],[-4.89144,-78.89510],
  [-4.80801,-78.89169],[-4.79100,-78.91273],[-4.71406,-78.88275],[-4.65604,-78.83922],
  [-4.63747,-78.80252],[-4.62387,-78.70596],[-4.65798,-78.63794],[-4.73645,-78.64466],
  [-4.77339,-78.60065],[-4.96227,-78.64582],[-5.00053,-78.61963],[-5.06742,-78.65771],
  [-5.10408,-78.70062],[-5.17963,-78.70911],[-5.26749,-78.68424],[-5.30990,-78.60449],
  [-5.39928,-78.51840],[-5.45435,-78.51518],[-5.49909,-78.55852],[-5.60721,-78.60482],
  [-5.70705,-78.68380],[-5.83044,-78.71202],[-5.95556,-78.66032],[-6.01818,-78.61227],
  [-6.07654,-78.58944],[-6.07148,-78.51880],[-6.16569,-78.43816],[-6.31868,-78.33539],
  [-6.35098,-78.33373],[-6.39478,-78.25515],[-6.45702,-78.19003],[-6.52630,-78.13603],
  [-6.64233,-78.10760],[-6.67615,-78.05820],[-6.82230,-78.01406],[-6.97053,-77.99951],
  [-7.16681,-77.89787],[-7.22139,-77.88090],[-7.31003,-77.83105],[-7.39254,-77.81344],
  [-7.41846,-77.77199],[-7.46669,-77.74137],[-7.51438,-77.84417],[-7.58533,-77.87044],
  [-7.67907,-77.99864],[-7.69617,-78.08122],[-7.65401,-78.11605],[-7.75933,-78.22465],
  [-7.75352,-78.27242],[-7.69646,-78.30280],[-7.69963,-78.33014],[-7.63011,-78.38282],
  [-7.57401,-78.35679],[-7.50039,-78.35998],[-7.48507,-78.41563],[-7.55487,-78.49139],
  [-7.54856,-78.62457],[-7.52902,-78.64960],[-7.44550,-78.62984],[-7.41300,-78.66247],
  [-7.40198,-78.76012],[-7.43762,-78.84162],[-7.48410,-78.88669],[-7.53744,-78.89591],
  [-7.59842,-78.94434],[-7.65783,-78.96086],[-7.66095,-78.99215],[-7.59989,-79.04123],
  [-7.47271,-79.06543],[-7.43982,-79.15272],[-7.39541,-79.18818],[-7.38186,-79.25633],
  [-7.34726,-79.29312],[-7.33664,-79.34713],[-7.27506,-79.28263],[-7.19239,-79.26727],
  [-7.14715,-79.30530],[-7.02568,-79.32259]
];

/**
 * Ray-casting rápido: verifica si (lat, lon) está dentro del polígono oficial INEI de Cajamarca.
 */
function pointInCajamarca(lat, lon) {
  let inside = false;
  for (let i = 0, j = CAJAMARCA_BORDER.length - 1; i < CAJAMARCA_BORDER.length; j = i++) {
    const yi = CAJAMARCA_BORDER[i][0], xi = CAJAMARCA_BORDER[i][1];
    const yj = CAJAMARCA_BORDER[j][0], xj = CAJAMARCA_BORDER[j][1];
    const intersect = ((yi > lat) !== (yj > lat)) &&
      (lon < ((xj - xi) * (lat - yi)) / (yj - yi + 1e-12) + xi);
    if (intersect) inside = !inside;
  }
  return inside;
}

const COLOR_MAP = {
  Rojo:     '#ef4444',
  Amarillo: '#f97316',
  Verde:    '#22c55e',
};

// Datos demo para el mapa de predicción (fallback sin API)
const DEMO_FEATURES = generateDemoFeatures();

/* ═══════════════════════════════════════════════════
   GENERADOR DE DATOS DEMO (Predicción IA)
   ═══════════════════════════════════════════════════ */
function generateDemoFeatures() {
  const features = [];
  const step = 0.048;
  const cellSize = 0.048;
  
  // Recorrer la totalidad del cuadrante de Cajamarca (de Sur a Norte y de Oeste a Este)
  for (let lat = -7.72; lat <= -4.56; lat += step) {
    for (let lon = -79.42; lon <= -77.76; lon += step) {
      // Simulación física espacial basada en corredores secos interandinos y laderas
      const reliefNoise = Math.sin(lat * 9.2 + lon * 4.1) * 0.4;
      const thermalGrad = (lat + 7.7) * 0.15; // Variación térmica latitudinal
      const basinEffect = Math.cos(lon * 11.5) * 0.35; // Cuenca del Marañón y valles occidentales
      const spatialBias = Math.max(0, reliefNoise + thermalGrad + basinEffect);
      // Score en el MISMO rango que el modelo real (~0.0001 – 0.145), con sesgo a
      // valores bajos, para que el fallback offline se vea como el mapa real.
      const rawRisk     = 0.001 + Math.pow(Math.random(), 6) * 0.14 + spatialBias * 0.015;
      const prob        = Math.max(0.0001, Math.min(0.145, rawRisk));
      // Umbrales data-driven reales (presupuesto de alerta top 1% / 5%).
      const nivel       = prob >= 0.13 ? 'Rojo' : prob >= 0.094 ? 'Amarillo' : 'Verde';

      // Mostrar zonas rojas, amarillas y una selección de verdes para visualización equilibrada
      if (nivel === 'Verde' && Math.random() > 0.25) continue;

      features.push({
        type: 'Feature',
        geometry: {
          type: 'Polygon',
          coordinates: [[
            [lon - cellSize/2, lat - cellSize/2],
            [lon + cellSize/2, lat - cellSize/2],
            [lon + cellSize/2, lat + cellSize/2],
            [lon - cellSize/2, lat + cellSize/2],
            [lon - cellSize/2, lat - cellSize/2],
          ]]
        },
        properties: {
          grid_id: `${lon.toFixed(4)}_${lat.toFixed(4)}`,
          probabilidad: Math.round(prob * 10000) / 10000,
          nivel,
          temp_2m: Math.round((21.5 + (lat + 7.7) * 2.2 + Math.random() * 5) * 10) / 10,
          humedad_relativa: Math.round(Math.max(15, 65 - prob * 40 + Math.random() * 8)),
          viento_velocidad: Math.round(10 + prob * 25 + Math.random() * 12),
          viento_direccion: Math.round(Math.random() * 360),
          pendiente_pct: Math.round(12 + prob * 28 + Math.random() * 10),
          ndvi: Math.round(Math.max(0.1, 0.65 - prob * 0.45) * 100) / 100,
          _isDemo: true,
        }
      });
    }
  }
  return features;
}

/**
 * Genera focos de calor demo con coordenadas realistas de Perú
 * distribuidos por todo el territorio de Cajamarca (de frontera Norte a Sur)
 */
function generateRealisticFIRMSDemo(region) {
  const BASE_HOTSPOTS = [
    // Madre de Dios / Puno
    { lat: -12.58, lon: -69.18, frp: 38.2, conf: 0.95, sat: 'N20',  d: 'D' },
    { lat: -12.61, lon: -69.21, frp: 22.1, conf: 0.75, sat: 'SNPP', d: 'D' },
    { lat: -13.10, lon: -70.05, frp: 15.4, conf: 0.75, sat: 'N20',  d: 'N' },
    { lat: -13.28, lon: -69.85, frp: 8.6,  conf: 0.75, sat: 'SNPP', d: 'D' },
    // Ucayali / Loreto
    { lat: -8.34,  lon: -74.52, frp: 5.2,  conf: 0.75, sat: 'SNPP', d: 'D' },
    { lat: -8.41,  lon: -74.60, frp: 12.7, conf: 0.95, sat: 'N20',  d: 'D' },

    // CAJAMARCA — Focos satelitales distribuidos en todos los sectores:
    // 1. Sector Norte (San Ignacio / Jaén / Campanquiz / Frontera Ecuador)
    { lat: -4.62,  lon: -78.75, frp: 28.5, conf: 0.95, sat: 'VIIRS', d: 'D' },
    { lat: -4.95,  lon: -78.92, frp: 19.3, conf: 0.85, sat: 'SNPP',  d: 'D' },
    { lat: -5.32,  lon: -79.08, frp: 15.8, conf: 0.80, sat: 'N20',   d: 'D' },
    { lat: -5.70,  lon: -78.85, frp: 11.4, conf: 0.75, sat: 'SNPP',  d: 'D' },

    // 2. Sector Centro (Cutervo / Chota / Santa Cruz / Cerro Carrampón)
    { lat: -6.15,  lon: -78.65, frp: 22.0, conf: 0.95, sat: 'VIIRS', d: 'D' },
    { lat: -6.38,  lon: -79.35, frp: 18.2, conf: 0.90, sat: 'SNPP',  d: 'D' }, // Oeste (Carrampón)
    { lat: -6.52,  lon: -78.48, frp: 14.6, conf: 0.80, sat: 'N20',   d: 'N' },

    // 3. Sector Este (Cañón y Valle del Río Marañón / Celendín)
    { lat: -7.28,  lon: -77.82, frp: 31.4, conf: 0.95, sat: 'SNPP',  d: 'D' }, // Este (Marañón)
    { lat: -7.46,  lon: -77.78, frp: 24.2, conf: 0.90, sat: 'VIIRS', d: 'D' },

    // 4. Sector Sur (Cajamarca capital / San Marcos / Cajabamba / La Libertad)
    { lat: -7.15,  lon: -78.50, frp: 16.5, conf: 0.85, sat: 'VIIRS', d: 'D' },
    { lat: -7.45,  lon: -78.73, frp: 9.8,  conf: 0.75, sat: 'N20',   d: 'D' },
    { lat: -7.68,  lon: -78.20, frp: 17.1, conf: 0.90, sat: 'SNPP',  d: 'D' }, // Sur (Límite La Libertad)

    // Ayacucho / Apurimac
    { lat: -14.07, lon: -73.45, frp: 6.8,  conf: 0.75, sat: 'SNPP', d: 'D' },
    { lat: -14.22, lon: -73.62, frp: 9.4,  conf: 0.75, sat: 'N20',  d: 'N' },
  ];

  let spots = BASE_HOTSPOTS;
  if (region === 'cajamarca') {
    spots = BASE_HOTSPOTS.filter(h => h.lat >= -7.7592 && h.lat <= -4.5519 && h.lon >= -79.4517 && h.lon <= -77.7389);
  }

  const today = new Date();
  const dateStr = today.toISOString().slice(0, 10);

  return spots.map((h, i) => {
    // Añadir pequeña variación aleatoria para que no sean siempre iguales
    const jitterLat = (Math.random() - 0.5) * 0.05;
    const jitterLon = (Math.random() - 0.5) * 0.05;
    const nivel = (h.conf >= 0.75 && h.frp >= 5) ? 'Rojo'
                : (h.conf >= 0.50 || h.frp >= 1)  ? 'Amarillo'
                : 'Verde';
    return {
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [h.lon + jitterLon, h.lat + jitterLat] },
      properties: {
        satellite:  h.sat,
        instrument: 'VIIRS',
        acq_date:   dateStr,
        acq_time:   `${String(Math.floor(Math.random()*24)).padStart(2,'0')}${String(Math.floor(Math.random()*60)).padStart(2,'0')}`,
        frp:        h.frp,
        confidence: h.conf,
        bright_ti4: 310 + h.frp * 0.8,
        daynight:   h.d,
        nivel,
        source:     'VIIRS_SNPP_NRT (demo)',
      }
    };
  });
}

/* ═══════════════════════════════════════════════════
   MAPA PRINCIPAL (LEAFLET — PROFESIONAL v2.5.0)
   ═══════════════════════════════════════════════════ */
let mainMap, heatmapLayer, polygonLayerGroup, firmsLayerGroup, extremesLayerGroup;
let cajamarcaBorderLayer, propagationLayerGroup, userLocationMarker, mapCanvasRenderer;
let currentBaseLayer = null;
let currentFeatures = [];
let lastApiStats = null;

const BASEMAPS = {
  dark: {
    url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    attribution: '&copy; OpenStreetMap &copy; CARTO',
    maxZoom: 19,
  },
  satellite: {
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attribution: 'Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics',
    maxZoom: 18,
  },
  topo: {
    url: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
    attribution: 'Map data: &copy; OpenStreetMap, SRTM | Style: &copy; OpenTopoMap',
    maxZoom: 17,
  },
  streets: {
    url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; OpenStreetMap contributors',
    maxZoom: 19,
  },
};

function switchBasemap(key) {
  if (!mainMap || !BASEMAPS[key]) return;
  if (currentBaseLayer) mainMap.removeLayer(currentBaseLayer);
  const cfg = BASEMAPS[key];
  currentBaseLayer = L.tileLayer(cfg.url, {
    attribution: cfg.attribution,
    maxZoom: cfg.maxZoom,
  }).addTo(mainMap);
  currentBaseLayer.bringToBack();

  document.querySelectorAll('.basemap-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.basemap === key);
  });
}

function initMainMap() {
  // Centrado en el departamento de Cajamarca abarcando de Norte a Sur
  mainMap = L.map('map', {
    center: [-6.20, -78.60],
    zoom: 8,
    zoomControl: true,
    preferCanvas: true,
  });

  // Renderizador Canvas para miles de grillas fluidas sin bordes negros
  mapCanvasRenderer = L.canvas({ padding: 0.5 });

  // Mapa base oscuro por defecto (estándar COEN/EFFIS: resalta alertas Rojas/Amarillas)
  switchBasemap('dark');

  // Escala métrica profesional
  L.control.scale({ imperial: false, position: 'bottomleft' }).addTo(mainMap);

  cajamarcaBorderLayer  = L.layerGroup().addTo(mainMap);
  polygonLayerGroup     = L.layerGroup().addTo(mainMap);
  propagationLayerGroup = L.layerGroup().addTo(mainMap);
  firmsLayerGroup       = L.layerGroup().addTo(mainMap);
  extremesLayerGroup    = L.layerGroup().addTo(mainMap);

  // Paneles exclusivos de z-index para orden cartográfico limpio
  mainMap.createPane('borderPane');
  mainMap.getPane('borderPane').style.zIndex = '450';
  mainMap.createPane('propPane');
  mainMap.getPane('propPane').style.zIndex = '610';
  mainMap.createPane('firmsPane');
  mainMap.getPane('firmsPane').style.zIndex = '650';

  renderCajamarcaBorder();
  renderExtremesLayer();
  loadMapData();
  loadFIRMSHotspots();
}

/**
 * Dibuja siempre el contorno oficial INEI de Cajamarca (118 vértices) + máscara suave exterior
 */
function renderCajamarcaBorder() {
  if (!cajamarcaBorderLayer) return;
  cajamarcaBorderLayer.clearLayers();

  // Máscara exterior semitransparente (efecto spotlight sobre Cajamarca)
  const worldRing = [[-90, -180], [-90, 180], [90, 180], [90, -180]];
  L.polygon([worldRing, CAJAMARCA_BORDER], {
    pane: 'borderPane',
    stroke: false,
    fillColor: '#020617',
    fillOpacity: 0.34,
    interactive: false,
  }).addTo(cajamarcaBorderLayer);

  // Contorno oficial INEI en línea punteada roja
  L.polygon(CAJAMARCA_BORDER, {
    pane: 'borderPane',
    color: '#ef4444',
    weight: 2.2,
    dashArray: '7, 5',
    fill: false,
    interactive: false,
  }).addTo(cajamarcaBorderLayer);
}

/* ── Predicciones IA ── */
async function loadMapData() {
  showMapLoading(true);
  let features  = [];
  let isDemo    = false;
  let apiOnline = false;
  lastApiStats  = null;

  const viewMode   = document.getElementById('riskViewFilter')?.value || 'alerts';
  const onlyAlerts = viewMode === 'alerts';
  const reqLimit   = onlyAlerts ? 3500 : 1800;

  try {
    const resp = await fetch(
      `${API_URL}/risk/today?limit=${reqLimit}&only_alerts=${onlyAlerts}`,
      { signal: AbortSignal.timeout(12000) }
    );
    if (resp.ok) {
      const data   = await resp.json();
      features     = data.features || [];
      lastApiStats = data.stats || null;
      apiOnline    = true;
    }
  } catch (_) {
    features = DEMO_FEATURES;
    isDemo   = true;
  }

  // Recorte estricto al polígono oficial INEI de Cajamarca (cero puntos fuera del límite)
  features = features.filter(f => {
    const coords = f.geometry.coordinates[0];
    const lat = (coords[0][1] + coords[2][1]) / 2;
    const lon = (coords[0][0] + coords[2][0]) / 2;
    return pointInCajamarca(lat, lon);
  });

  features = applyRegionFilter(features);
  currentFeatures = features;
  renderMapLayers(features);
  updateHeroStats(features, lastApiStats);
  updateRiskBadge(features, lastApiStats);
  showDemoBanner(isDemo, apiOnline);
  showMapLoading(false);
}

function renderMapLayers(features) {
  polygonLayerGroup.clearLayers();
  if (heatmapLayer && mainMap.hasLayer(heatmapLayer)) mainMap.removeLayer(heatmapLayer);

  const showHeat = document.getElementById('toggleHeatmap').checked;
  const showPoly = document.getElementById('togglePolygons').checked;

  if (showHeat && features.length) {
    const heatData = features.map(f => {
      const coords = f.geometry.coordinates[0];
      const lat = (coords[0][1] + coords[2][1]) / 2;
      const lon = (coords[0][0] + coords[2][0]) / 2;
      // Escalar intensidad según nivel para que el mapa de calor destaque zonas críticas
      const w = f.properties.nivel === 'Rojo' ? 1.0 : f.properties.nivel === 'Amarillo' ? 0.55 : 0.18;
      return [lat, lon, w];
    });
    heatmapLayer = L.heatLayer(heatData, {
      radius: 22, blur: 18, maxZoom: 13, minOpacity: 0.25,
      gradient: { 0.2: '#22c55e', 0.55: '#f97316', 0.82: '#ef4444', 1.0: '#b91c1c' }
    }).addTo(mainMap);
  }

  if (showPoly) {
    features.forEach((f, idx) => {
      const props   = f.properties;
      const isDemo  = !!props._isDemo;
      const color   = COLOR_MAP[props.nivel] || '#22c55e';
      const coords  = f.geometry.coordinates[0].map(p => [p[1], p[0]]);
      const centerLat = (coords[0][0] + coords[2][0]) / 2;
      const centerLon = (coords[0][1] + coords[2][1]) / 2;
      const shapId  = `shapBox_${idx}_${Date.now() % 10000}`;

      const demoTag = isDemo
        ? '<div style="margin-top:6px;padding:4px 8px;background:#1e293b;border-radius:4px;font-size:10px;color:#94a3b8">⚠️ Predicción simulada — API offline</div>'
        : '';
      const ranking = (props.percentil != null)
        ? `<b>Ranking relativo:</b> Top <b>${Math.max(1, Math.round(100 - props.percentil))}%</b> de riesgo en Cajamarca<br/>`
        : '';

      const nivelExplicacion = {
        'Rojo':     '🔴 Condiciones muy peligrosas hoy. Evitar quemas y vigilar.',
        'Amarillo': '🟡 Condiciones de precaución. Mantener vigilancia.',
        'Verde':    '🟢 Condiciones normales. Sin alerta activa.',
      }[props.nivel] || '';

      const ndviStr = (props.ndvi != null) ? props.ndvi.toFixed(2) : '—';
      const vpdStr  = (props.vpd_kpa != null) ? `${props.vpd_kpa.toFixed(2)} kPa` : '—';
      const propBtn = (props.nivel === 'Rojo' || props.nivel === 'Amarillo')
        ? `<button type="button" onclick="simulatePropagation('${props.grid_id}', ${centerLat.toFixed(5)}, ${centerLon.toFixed(5)}, ${props.viento_direccion ?? 45}, ${props.viento_velocidad ?? 18})"
             style="margin-top:7px;width:100%;background:#ea580c;color:#fff;border:none;border-radius:6px;padding:6px 10px;font-size:11px;font-weight:700;cursor:pointer">
             💨 Simular propagación por viento
           </button>`
        : '';

      const popup = `
        <div style="font-family:Inter,sans-serif;font-size:12px;min-width:255px;color:#0f172a">
          <b style="font-size:13px">📍 Celda 1 km² — ${props.grid_id}</b><hr style="margin:6px 0"/>
          <div style="background:${color}22;border-left:3px solid ${color};border-radius:4px;padding:5px 8px;margin-bottom:7px">
            <b style="color:${color};font-size:13px">${props.nivel}</b> — ${nivelExplicacion}
          </div>
          ${ranking}
          <div id="${shapId}" style="margin:6px 0;padding:6px 8px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;font-size:11px">
            <b style="color:#334155">🔮 Factores clave (SHAP XAI):</b>
            <div style="color:#64748b;margin-top:3px">Calculando explicación en vivo...</div>
          </div>
          <details style="margin:4px 0">
            <summary style="cursor:pointer;color:#475569;font-size:11px;font-weight:600">🌦️ Variables físicas y satelitales</summary>
            <div style="padding:5px 0 2px 0;line-height:1.55">
              🌡️ <b>Temperatura:</b> ${props.temp_2m?.toFixed(1)} °C · 💧 <b>Humedad:</b> ${props.humedad_relativa?.toFixed(0)} %<br/>
              💨 <b>Viento:</b> ${props.viento_velocidad?.toFixed(0)} km/h (${props.viento_direccion?.toFixed(0) ?? 45}°)<br/>
              ⛰️ <b>Pendiente:</b> ${props.pendiente_pct?.toFixed(0)} % · 🌿 <b>NDVI Sentinel-2:</b> ${ndviStr}<br/>
              🔥 <b>Déficit presión vapor (VPD):</b> ${vpdStr}
            </div>
          </details>
          ${propBtn}
          ${demoTag}
        </div>`;

      const fillOp = props.nivel === 'Rojo' ? 0.68 : props.nivel === 'Amarillo' ? 0.48 : 0.24;
      const poly = L.polygon(coords, {
        renderer:    mapCanvasRenderer,
        stroke:      false,
        fillColor:   color,
        fillOpacity: fillOp,
      }).bindPopup(popup);

      poly.on('popupopen', () => {
        if (!isDemo) loadCellShap(shapId, props);
        else {
          const box = document.getElementById(shapId);
          if (box) box.innerHTML = '<b style="color:#334155">🔮 SHAP XAI:</b> <span style="color:#64748b">Disponible con API activa.</span>';
        }
      });

      poly.addTo(polygonLayerGroup);
    });
  }
}

/**
 * Consulta POST /predict para obtener los 3 factores SHAP reales que explican esta celda
 */
async function loadCellShap(boxId, props) {
  const box = document.getElementById(boxId);
  if (!box) return;
  try {
    const resp = await fetch(`${API_URL}/predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        grid_id:          props.grid_id,
        temp_2m:          props.temp_2m,
        humedad_relativa: props.humedad_relativa,
        viento_velocidad: props.viento_velocidad,
        viento_direccion: props.viento_direccion ?? 45.0,
        pendiente_pct:    props.pendiente_pct,
        ndvi:             props.ndvi ?? 0.4,
        dias_sin_lluvia:  props.dias_sin_lluvia ?? 10.0,
        dist_carretera_m: props.dist_carretera_m ?? 1000.0,
        dist_poblado_m:   props.dist_poblado_m ?? 1500.0,
        elevacion_m:      props.elevacion_m ?? 2500.0,
      }),
      signal: AbortSignal.timeout(6000),
    });
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    const data = await resp.json();
    const factors = data.factores_clave || [];
    if (!factors.length) {
      box.innerHTML = '<b style="color:#334155">🔮 Factores SHAP:</b> <span style="color:#64748b">Sin explicación disponible.</span>';
      return;
    }
    const rows = factors.map(fc => {
      const up = fc.efecto === 'aumenta_riesgo';
      const col = up ? '#dc2626' : '#16a34a';
      const arrow = up ? '▲' : '▼';
      return `<div style="display:flex;justify-content:space-between;gap:6px;margin-top:3px">
        <span><b style="color:${col}">${arrow}</b> ${fc.etiqueta}</span>
        <span style="color:${col};font-weight:700">${fc.impacto_shap >= 0 ? '+' : ''}${fc.impacto_shap.toFixed(2)}</span>
      </div>`;
    }).join('');
    box.innerHTML = `<b style="color:#1e293b">🔮 ¿Por qué este riesgo? (SHAP):</b>${rows}`;
  } catch (_) {
    box.innerHTML = '<b style="color:#334155">🔮 Factores SHAP:</b> <span style="color:#64748b">No se pudo calcular ahora.</span>';
  }
}

/**
 * Simula propagación del fuego por viento llamando a POST /propagate y la dibuja en el mapa
 */
async function simulatePropagation(gridId, lat, lon, vientoDir, vientoVel) {
  if (!mainMap || !propagationLayerGroup) return;
  clearPropagation();
  showToast('Simulando propagación espacial por viento...', '💨');

  try {
    const url = `${API_URL}/propagate?grid_id=${encodeURIComponent(gridId)}&viento_direccion=${encodeURIComponent(vientoDir)}&viento_velocidad=${encodeURIComponent(vientoVel)}`;
    const resp = await fetch(url, { method: 'POST', signal: AbortSignal.timeout(8000) });
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    const data = await resp.json();
    const affected = data.grillas_afectadas || [];

    const pathPoints = [[lat, lon]];
    // Marcador de origen
    L.circleMarker([lat, lon], {
      pane: 'propPane', radius: 8, color: '#fff', weight: 2,
      fillColor: '#dc2626', fillOpacity: 1,
    }).bindTooltip(`🔥 Origen (${gridId})`, { permanent: false }).addTo(propagationLayerGroup);

    affected.forEach((g, idx) => {
      const parts = String(g.grid_id).split('_');
      if (parts.length !== 2) return;
      const gLon = parseFloat(parts[0]);
      const gLat = parseFloat(parts[1]);
      if (isNaN(gLat) || isNaN(gLon)) return;
      pathPoints.push([gLat, gLon]);

      const half = 0.0045;
      L.rectangle([[gLat - half, gLon - half], [gLat + half, gLon + half]], {
        pane: 'propPane',
        color: '#facc15', weight: 2, dashArray: '4 3',
        fillColor: '#f97316', fillOpacity: Math.max(0.25, 0.65 - idx * 0.15),
      }).bindPopup(
        `<div style="font-family:Inter,sans-serif;font-size:12px;color:#0f172a">
           <b>💨 Propagación Paso ${idx + 1}</b><hr style="margin:4px 0"/>
           <b>Celda:</b> ${g.grid_id}<br/>
           <b>Dirección viento:</b> ${data.direccion_viento} (${data.velocidad_viento} km/h)<br/>
           <b>Prob. propagación:</b> <b>${Math.round((g.probabilidad_recibir_fuego || 0) * 100)}%</b>
         </div>`
      ).addTo(propagationLayerGroup);
    });

    if (pathPoints.length > 1) {
      L.polyline(pathPoints, {
        pane: 'propPane', color: '#facc15', weight: 3.5, dashArray: '8 6',
      }).addTo(propagationLayerGroup);
      mainMap.fitBounds(L.latLngBounds(pathPoints).pad(0.8), { maxZoom: 12 });
    }

    const chip = document.getElementById('propChip');
    const chipTxt = document.getElementById('propChipText');
    if (chip && chipTxt) {
      chipTxt.textContent = `💨 Propagación desde ${gridId} · Viento ${data.direccion_viento} (${data.velocidad_viento} km/h) · ${affected.length} zonas`;
      chip.classList.add('visible');
    }
    mainMap.closePopup();
  } catch (_) {
    showToast('No se pudo simular la propagación en este momento.', '⚠️');
  }
}

function clearPropagation() {
  if (propagationLayerGroup) propagationLayerGroup.clearLayers();
  const chip = document.getElementById('propChip');
  if (chip) chip.classList.remove('visible');
}

function toggleHeatmapLayer()  { renderMapLayers(currentFeatures); }
function togglePolygonLayer()  { renderMapLayers(currentFeatures); }
function toggleExtremesLayer() { renderExtremesLayer(); }

function toggleLegend() {
  const el = document.getElementById('mapLegend');
  const btn = document.getElementById('legendToggleBtn');
  if (!el || !btn) return;
  const collapsed = el.classList.toggle('collapsed');
  btn.textContent = collapsed ? '+' : '−';
}

function toggleMapFullscreen() {
  const wrapper = document.getElementById('mapWrapper');
  const btn = document.getElementById('btnFullscreen');
  if (!wrapper) return;
  const isFull = wrapper.classList.toggle('is-fullscreen');
  if (btn) btn.textContent = isFull ? '✕ Salir pantalla completa' : '⛶ Pantalla completa';
  setTimeout(() => mainMap?.invalidateSize(), 150);
}

function downloadExecutivePdf(e) {
  if (e) e.preventDefault();
  window.open(`${API_URL}/report/pdf`, '_blank', 'noopener');
  showToast('Generando informe ejecutivo PDF...', '📄');
}

function locateOnMainMap() {
  if (!navigator.geolocation) {
    showToast('Tu navegador no soporta geolocalización.', '⚠️');
    return;
  }
  navigator.geolocation.getCurrentPosition(
    pos => {
      const { latitude: lat, longitude: lon } = pos.coords;
      if (userLocationMarker) userLocationMarker.remove();
      userLocationMarker = L.circleMarker([lat, lon], {
        pane: 'firmsPane', radius: 9, color: '#fff', weight: 3,
        fillColor: '#38bdf8', fillOpacity: 0.95,
      }).bindPopup(`<b>📍 Tu ubicación actual</b><br/>${lat.toFixed(4)}, ${lon.toFixed(4)}`).addTo(mainMap);
      mainMap.flyTo([lat, lon], 11, { duration: 1.2 });
      userLocationMarker.openPopup();
    },
    () => showToast('No se pudo obtener tu ubicación GPS.', '⚠️')
  );
}

function filterByRegion() {
  currentRegion = document.getElementById('regionFilter')?.value || 'cajamarca';
  if (mainMap) {
    const bb = AI_REGION_BBOX[currentRegion];
    if (bb) {
      mainMap.flyToBounds([
        [bb.south, bb.west],
        [bb.north, bb.east]
      ], { duration: 1.1, padding: [24, 24] });
    } else {
      mainMap.flyTo([-9.0, -75.5], 6, { duration: 1.1 });
    }
  }
  loadMapData();
  loadFIRMSHotspots();
}

/**
 * Filtra las grillas del modelo por la provincia o sub-región seleccionada.
 */
function applyRegionFilter(features) {
  const bb = AI_REGION_BBOX[currentRegion];
  if (!bb) return features;
  return features.filter(f => {
    const coords = f.geometry.coordinates[0];
    const lat = (coords[0][1] + coords[2][1]) / 2;
    const lon = (coords[0][0] + coords[2][0]) / 2;
    return lat >= bb.south && lat <= bb.north && lon >= bb.west && lon <= bb.east;
  });
}

/**
 * Renderiza únicamente los 4 puntos cardinales extremos (capa opcional; el borde INEI siempre está visible)
 */
function renderExtremesLayer() {
  if (!extremesLayerGroup) return;
  extremesLayerGroup.clearLayers();

  const showExtremes = document.getElementById('toggleExtremes')?.checked ?? false;
  if (!showExtremes) return;

  CAJAMARCA_EXTREMES.forEach(pt => {
    const icon = L.divIcon({
      className: 'reading-point-marker',
      html: `
        <div style="
          background:#0f172a;
          border:2px solid ${pt.badgeColor};
          border-radius:20px;
          padding:3px 9px;
          color:#f8fafc;
          font-family:Inter,sans-serif;
          font-size:11px;
          font-weight:700;
          display:flex;
          align-items:center;
          gap:5px;
          box-shadow:0 4px 12px rgba(0,0,0,0.5);
          cursor:pointer;
          white-space:nowrap;
        ">
          <span style="width:7px;height:7px;border-radius:50%;background:${pt.badgeColor}"></span>
          <span>${pt.cardinal}: ${pt.subtitle.replace('Punto más ', '')}</span>
        </div>
      `,
      iconSize: [120, 26],
      iconAnchor: [60, 13]
    });

    const popupContent = `
      <div style="font-family:Inter,sans-serif;font-size:12px;min-width:260px;color:#0f172a;line-height:1.5">
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px">
          <span style="background:${pt.badgeColor};color:#fff;font-weight:700;font-size:11px;padding:2px 8px;border-radius:12px">
            ${pt.cardinal.toUpperCase()}
          </span>
          <b style="font-size:13px">${pt.subtitle}</b>
        </div>
        <hr style="margin:6px 0"/>
        <b>Latitud (DMS):</b> ${pt.latDMS} <span style="color:#64748b">(${pt.lat.toFixed(6)}°)</span><br/>
        <b>Longitud (DMS):</b> ${pt.lonDMS} <span style="color:#64748b">(${pt.lon.toFixed(6)}°)</span><br/>
        <div style="margin-top:8px;padding:6px 10px;background:#f8fafc;border-left:3px solid ${pt.badgeColor};border-radius:4px;font-size:11px;color:#334155">
          📍 <b>Hito geográfico:</b><br/>${pt.desc}
        </div>
      </div>
    `;

    L.marker([pt.lat, pt.lon], { icon })
      .bindPopup(popupContent)
      .addTo(extremesLayerGroup);
  });
}

/**
 * Muestra/oculta el banner de modo demo encima del mapa.
 * - isDemo=true       : API offline → banner naranja de aviso
 * - apiOnline=true    : API activa  → banner verde que se auto-oculta en 4s
 */
function showDemoBanner(isDemo, apiOnline = false) {
  let banner = document.getElementById('demoBanner');
  if (!banner) {
    banner = document.createElement('div');
    banner.id = 'demoBanner';
    banner.style.cssText = [
      'position:absolute', 'top:10px', 'left:50%', 'transform:translateX(-50%)',
      'z-index:1000', 'backdrop-filter:blur(8px)',
      'border-radius:8px', 'padding:8px 16px',
      'font-size:12px', 'font-family:Inter,sans-serif',
      'white-space:nowrap', 'pointer-events:none',
      'transition:opacity 0.5s ease',
    ].join(';');
    const wrapper = document.querySelector('.map-wrapper');
    if (wrapper) wrapper.style.position = 'relative';
    if (wrapper) wrapper.appendChild(banner);
  }

  if (isDemo) {
    // API offline — mostrando zonas simuladas
    banner.style.background = 'rgba(30,20,0,0.88)';
    banner.style.border     = '1px solid #f97316';
    banner.style.color      = '#fbbf24';
    banner.innerHTML = '⚠️ <b>API offline</b> — Predicciones simuladas. Inicia el servidor para datos reales del modelo de IA';
    banner.style.opacity = '1';
    banner.style.display = 'block';
  } else if (apiOnline) {
    // API activa — datos reales del modelo
    banner.style.background = 'rgba(0,30,10,0.85)';
    banner.style.border     = '1px solid #22c55e';
    banner.style.color      = '#86efac';
    banner.innerHTML = '✅ <b>Modelo de IA activo</b> — Predicciones de riesgo en tiempo real';
    banner.style.opacity = '1';
    banner.style.display = 'block';
    // Auto-ocultar tras 4 segundos
    setTimeout(() => { banner.style.opacity = '0'; }, 3500);
    setTimeout(() => { banner.style.display = 'none'; }, 4000);
  } else {
    banner.style.display = 'none';
  }
}

/* ═══════════════════════════════════════════════════
   NASA FIRMS — Focos de Calor Reales (VIIRS/MODIS)
   ═══════════════════════════════════════════════════ */
async function loadFIRMSHotspots() {
  if (!mainMap || !firmsLayerGroup) return;

  const showFIRMS = document.getElementById('toggleFIRMS')?.checked;
  if (showFIRMS === false) {
    firmsLayerGroup.clearLayers();
    return;
  }

  const regionVal = document.getElementById('regionFilter')?.value || 'cajamarca';
  const bboxKey   = FIRMS_BBOXES[regionVal] ? regionVal : 'cajamarca';
  const lookback  = parseInt(document.getElementById('timeFilter')?.value || '1', 10); // días (1-3)

  updateLegendTime('⏳ Sincronizando satélites VIIRS...');

  let features       = [];
  let sourceLabel    = 'simulación';
  let dataSourceType = 'offline'; // 'real_today' | 'real_recent' | 'zero_active' | 'offline'

  // 1) Intentar vía proxy FastAPI (datos reales de NASA FIRMS sin problemas de CORS)
  try {
    // Primero consultar la ventana seleccionada en el filtro (1-3 días)
    const proxyResp = await fetch(
      `${API_URL}/firms/hotspots?region=${bboxKey}&source=VIIRS_SNPP_NRT&days=${lookback}`,
      { signal: AbortSignal.timeout(5000) }
    );
    if (proxyResp.ok) {
      const data = await proxyResp.json();
      if (Array.isArray(data.features) && data.features.length > 0) {
        features       = data.features;
        sourceLabel    = 'NASA FIRMS (Hoy)';
        dataSourceType = 'real_today';
      } else {
        // Si hoy temprano aún no hubo pasadas satelitales con focos activos,
        // consultamos las últimas 48-72h para ver los focos satelitales reales detectados en Cajamarca
        try {
          const respReciente = await fetch(
            `${API_URL}/firms/hotspots?region=${bboxKey}&source=VIIRS_SNPP_NRT&days=3`,
            { signal: AbortSignal.timeout(5000) }
          );
          if (respReciente.ok) {
            const dataReciente = await respReciente.json();
            if (Array.isArray(dataReciente.features) && dataReciente.features.length > 0) {
              features       = dataReciente.features;
              sourceLabel    = 'NASA FIRMS (Últimas 48-72h)';
              dataSourceType = 'real_recent';
            }
          }
        } catch (_) {}

        // Si ni en 72h hay focos activos detectados por el satélite
        if (features.length === 0) {
          dataSourceType = 'zero_active';
          sourceLabel    = 'NASA FIRMS (0 fuegos activos en 72h)';
          features       = []; // Sin datos demo — mostrar mapa limpio
        }
      }
    }
  } catch (_) { /* Servidor offline */ }

  // 2) Si el backend está offline o sin clave FIRMS, mostrar mapa vacío con aviso claro
  if (features.length === 0) {
    sourceLabel    = dataSourceType === 'zero_active'
      ? 'NASA FIRMS · Sin focos activos detectados (últimas 72h)'
      : 'FIRMS sin clave NASA — configura FIRMS_MAP_KEY en Render';
    dataSourceType = dataSourceType || 'offline';
    features       = []; // No mostrar datos ficticios
  }

  // Renderizar de forma atómica (sin parpadeos)
  renderFIRMSLayer(features, dataSourceType);
  animateCounter('statFIRMS', features.length);
  updateLegendTime(`🛰️ VIIRS · ${features.length} focos · ${sourceLabel}`);
}

/* ── Parser CSV de NASA FIRMS ── */
function parseFIRMScsv(csvText) {
  const lines   = csvText.trim().split('\n');
  if (lines.length < 2) return [];
  const headers  = lines[0].split(',').map(h => h.trim());
  const features = [];
  const CMAP     = { l: 0.40, n: 0.75, h: 0.95 };

  for (let i = 1; i < lines.length; i++) {
    const vals = lines[i].split(',');
    const row  = {};
    headers.forEach((h, idx) => { row[h] = (vals[idx] || '').trim(); });
    try {
      const lat     = parseFloat(row.latitude);
      const lon     = parseFloat(row.longitude);
      const frp     = parseFloat(row.frp || 0);
      const confRaw = row.confidence || 'n';
      const conf    = CMAP[confRaw] ?? Math.min(parseFloat(confRaw || 75), 100) / 100;
      const nivel   = (conf >= 0.75 && frp >= 5) ? 'Rojo'
                    : (conf >= 0.50 || frp >= 1)  ? 'Amarillo' : 'Verde';
      if (isNaN(lat) || isNaN(lon)) continue;
      features.push({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [lon, lat] },
        properties: {
          satellite:  row.satellite  || 'S-NPP',
          instrument: row.instrument || 'VIIRS',
          acq_date:   row.acq_date   || '',
          acq_time:   row.acq_time   || '',
          frp:        Math.round(frp * 100) / 100,
          confidence: Math.round(conf * 100) / 100,
          bright_ti4: parseFloat(row.bright_ti4 || row.brightness || 0),
          daynight:   row.daynight   || 'D',
          nivel,
          source:     'VIIRS_SNPP_NRT',
        }
      });
    } catch (_) { continue; }
  }
  return features;
}

/* ── Renderizar focos como círculos en el mapa ── */
function renderFIRMSLayer(features, dataSourceType = 'offline') {
  firmsLayerGroup.clearLayers();

  // Si no hay focos, actualizar solo la leyenda — sin marcador flotante en el mapa
  if (features.length === 0) {
    const legendMsg = dataSourceType === 'zero_active'
      ? '🛰️ NASA FIRMS · Sin focos activos en Cajamarca (últimas 72h)'
      : '🛰️ NASA FIRMS · Sin clave API — agrega FIRMS_MAP_KEY en Render';
    updateLegendTime(legendMsg);
    return;
  }

  features.forEach(f => {
    const p       = f.properties;
    const lat     = f.geometry.coordinates[1];
    const lon     = f.geometry.coordinates[0];
    const isReal  = (dataSourceType === 'real_today' || dataSourceType === 'real_recent');
    const color   = p.nivel === 'Rojo' ? '#ef4444' : p.nivel === 'Amarillo' ? '#f97316' : '#eab308';
    const radius  = p.nivel === 'Rojo' ? 8 : 5;

    const t      = String(p.acq_time).padStart(4, '0');
    const tFmt   = `${t.slice(0,2)}:${t.slice(2)} UTC`;
    const isDark = p.daynight === 'N' ? '🌙 Nocturno' : '☀️ Diurno';
    const confPct = Math.round(p.confidence * 100);

    // Cabecera e indicador de fuente según el estado real
    let header = '';
    if (dataSourceType === 'real_today') {
      header = `
        <b style="font-size:13px">🛰️ Foco Satelital REAL (Hoy)</b>
        <div style="background:#dcfce7;border:1px solid #22c55e;border-radius:4px;padding:3px 6px;margin:4px 0;font-size:10px;color:#166534">
          ✅ <b>NASA FIRMS en tiempo real:</b> Detectado por satélite VIIRS hoy.
        </div>`;
    } else if (dataSourceType === 'real_recent') {
      header = `
        <b style="font-size:13px">🛰️ Foco Satelital REAL (Reciente)</b>
        <div style="background:#ecfdf5;border:1px solid #10b981;border-radius:4px;padding:3px 6px;margin:4px 0;font-size:10px;color:#065f46">
          ✅ <b>NASA FIRMS activo:</b> Detección satelital real de las últimas 48-72h.
        </div>`;
    } else if (dataSourceType === 'zero_active') {
      header = `
        <b style="font-size:13px">🛰️ Foco de Referencia Histórica</b>
        <div style="background:#eff6ff;border:1px solid #3b82f6;border-radius:4px;padding:3px 6px;margin:4px 0;font-size:10px;color:#1e40af">
          ℹ️ <b>NASA FIRMS Conectado:</b> 0 incendios activos detectados en Cajamarca hoy.<br/>
          <i>Punto referencial para calibración del visor.</i>
        </div>`;
    } else {
      header = `
        <b style="font-size:13px">🛰️ Foco Simulado (Modo Local Offline)</b>
        <div style="background:#fef3c7;border:1px solid #f59e0b;border-radius:4px;padding:3px 6px;margin:4px 0;font-size:10px;color:#92400e">
          ⚠️ <b>Servidor backend no detectado:</b> Inicia el servidor con <code>INICIAR_SERVIDOR_7AM.bat</code> para sincronizar con NASA FIRMS.
        </div>`;
    }

    const popup = `
      <div style="font-family:Inter,sans-serif;font-size:12px;min-width:230px;color:#1a1a2e">
        ${header}
        <hr style="margin:5px 0"/>
        🛰️ <b>Satélite:</b> ${p.satellite} (${p.instrument || 'VIIRS'})<br/>
        📅 <b>Detectado:</b> ${p.acq_date || 'Reciente'} a las ${tFmt}<br/>
        🔥 <b>Intensidad del fuego (FRP):</b> ${p.frp} MW
          <span style="color:#888;font-size:10px"> — valores &gt;10 MW suelen ser incendios forestales</span><br/>
        🌡️ <b>Temperatura de brillo:</b> ${p.bright_ti4 ? p.bright_ti4.toFixed(1) : '330.0'} K<br/>
        📊 <b>Confianza del satélite:</b> <span style="color:${color};font-weight:700">${confPct}%</span><br/>
        🕐 <b>Paso del satélite:</b> ${isDark}<br/>
        <div style="margin-top:6px;padding:4px 8px;background:${p.nivel==='Rojo'?'#fef2f2':'#fffbeb'};border-radius:4px;font-size:11px;color:#374151">
          ⚠️ Nivel de alerta: <strong style="color:${color}">${p.nivel}</strong>
          ${p.nivel==='Rojo' ? ' — Si hay humo visible, llama a Bomberos: <strong>116</strong>' : ''}
        </div>
      </div>`;

    L.circleMarker([lat, lon], {
      pane:        'firmsPane',
      radius,
      color:       '#fff',
      weight:      isReal ? 2.5 : 1.5,
      fillColor:   color,
      fillOpacity: 0.92,
      dashArray:   isReal ? null : '3 2',
    }).bindPopup(popup).addTo(firmsLayerGroup);
  });
}



function toggleFIRMSLayer() {
  const show = document.getElementById('toggleFIRMS').checked;
  if (show) loadFIRMSHotspots();
  else firmsLayerGroup.clearLayers();
}

/* ═══════════════════════════════════════════════════
   HERO STATS & RISK BADGE
   ═══════════════════════════════════════════════════ */
function updateHeroStats(features, stats = null) {
  if (stats && stats.total_analizado) {
    animateCounter('statRojas',     stats.rojo ?? 0);
    animateCounter('statAmarillas', stats.amarillo ?? 0);
    animateCounter('statTotal',     stats.total_analizado ?? 0);
    return;
  }
  animateCounter('statRojas',     features.filter(f => f.properties.nivel === 'Rojo').length);
  animateCounter('statAmarillas', features.filter(f => f.properties.nivel === 'Amarillo').length);
  animateCounter('statTotal',     features.length);
}

function animateCounter(id, target) {
  const el = document.getElementById(id);
  if (!el) return;
  let current = 0;
  const step = Math.max(1, Math.ceil(target / 40));
  const interval = setInterval(() => {
    current = Math.min(current + step, target);
    el.textContent = current.toLocaleString('es-PE');
    if (current >= target) clearInterval(interval);
  }, 30);
}

function updateRiskBadge(features, stats = null) {
  const total     = stats?.total_analizado ?? (features.length || 0);
  const rojas     = stats?.rojo ?? features.filter(f => f.properties.nivel === 'Rojo').length;
  const amarillas = stats?.amarillo ?? features.filter(f => f.properties.nivel === 'Amarillo').length;
  const pctRojas  = total ? (rojas / total) * 100 : 0;
  const el = document.getElementById('badgeLevel');
  // El semáforo se basa en la PROPORCIÓN real sobre todo el territorio analizado.
  // ALTO solo si ≥2% del departamento está en Rojo; MEDIO en operación normal (~1% Rojo).
  let level, cls;
  if (rojas > 0 && pctRojas >= 2.0)      { level = 'ALTO 🔴';  cls = 'alto';  }
  else if (rojas > 0 || amarillas >= 5)  { level = 'MEDIO 🟡'; cls = 'medio'; }
  else                                   { level = 'BAJO 🟢';  cls = 'bajo';  }
  el.textContent = level;
  el.className   = `badge-level ${cls}`;
}

function updateLegendTime(source) {
  const now = new Date().toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' });
  const el  = document.getElementById('legendUpdate');
  if (el) el.textContent = `${source} · ${now}`;
}

function showMapLoading(show) {
  const el = document.getElementById('mapLoading');
  if (show) el.classList.remove('hidden');
  else      el.classList.add('hidden');
}

/* ═══════════════════════════════════════════════════
   MAPA DE REPORTE
   ═══════════════════════════════════════════════════ */
let reportMap, reportMarker;

function initReportMap() {
  reportMap = L.map('reportMap', { center: [-7.16, -78.5], zoom: 9 });
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
  }).addTo(reportMap);

  reportMap.on('click', (e) => {
    const { lat, lng } = e.latlng;
    document.getElementById('reportLat').value = lat.toFixed(5);
    document.getElementById('reportLon').value = lng.toFixed(5);
    document.getElementById('locationStatus').textContent =
      `📍 Coordenadas fijadas: ${lat.toFixed(4)}, ${lng.toFixed(4)}`;
    if (reportMarker) reportMarker.remove();
    reportMarker = L.marker([lat, lng], {
      icon: L.divIcon({
        html: '<div style="font-size:24px;transform:translate(-50%,-100%)">📍</div>',
        className: '', iconSize: [0, 0]
      })
    }).addTo(reportMap);
  });

  renderRecentReports();
}

function useMyLocation() {
  if (!navigator.geolocation) {
    showToast('Tu navegador no soporta geolocalización.', '❌');
    return;
  }
  document.getElementById('locationStatus').textContent = '🔍 Obteniendo ubicación GPS...';
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      const lat = pos.coords.latitude, lng = pos.coords.longitude;
      document.getElementById('reportLat').value = lat.toFixed(5);
      document.getElementById('reportLon').value = lng.toFixed(5);
      document.getElementById('locationStatus').textContent =
        `✅ Ubicación GPS obtenida: ${lat.toFixed(4)}, ${lng.toFixed(4)}`;
      if (reportMap) {
        reportMap.setView([lat, lng], 13);
        if (reportMarker) reportMarker.remove();
        reportMarker = L.marker([lat, lng]).addTo(reportMap);
      }
    },
    () => {
      const el = document.getElementById('locationStatus');
      el.textContent = '⚠️ No se pudo obtener la ubicación. Usa el mapa o ingrésala manualmente.';
      el.style.color = 'var(--color-warning)';
    }
  );
}

async function renderRecentReports() {
  const listEl = document.getElementById('recentReportsList');
  if (!listEl) return;

  let reports = [];
  try {
    const resp = await fetch(`${API_URL}/report/recent?limit=5`, { signal: AbortSignal.timeout(5000) });
    if (resp.ok) {
      const data = await resp.json();
      reports = data.reports || [];
    }
  } catch (_) { /* API offline */ }

  if (!reports.length) {
    listEl.innerHTML = `
      <div class="report-item" style="opacity:.7">
        <div class="report-dot pending"></div>
        <div style="flex:1">
          <strong style="font-size:0.82rem">Aún no hay reportes registrados</strong>
          <span style="color:var(--color-text-muted);font-size:0.76rem;display:block">Los reportes enviados desde este formulario aparecerán aquí.</span>
        </div>
      </div>`;
    return;
  }

  listEl.innerHTML = reports.map(r => {
    const zone = r.zone || r.reporter_zone || `${Number(r.lat).toFixed(3)}, ${Number(r.lon).toFixed(3)}`;
    return `
      <div class="report-item">
        <div class="report-dot ${r.status === 'verified' ? 'verified' : 'pending'}"></div>
        <div style="flex:1">
          <strong style="font-size:0.82rem">${r.incident_label || r.incident_type}</strong>
          <span style="color:var(--color-text-muted);font-size:0.76rem;display:block">${zone} · ${timeAgo(r.timestamp)}</span>
        </div>
        <span style="font-size:0.7rem;color:var(--color-warning)">⏳ Revisando</span>
      </div>`;
  }).join('');
}

function timeAgo(iso) {
  if (!iso) return 'Reciente';
  const diffMin = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
  if (diffMin < 1)  return 'Hace instantes';
  if (diffMin < 60) return `Hace ${diffMin} min`;
  const h = Math.floor(diffMin / 60);
  if (h < 24) return `Hace ${h} h`;
  return `Hace ${Math.floor(h / 24)} d`;
}

async function submitReport(e) {
  e.preventDefault();
  const btn = document.getElementById('submitReportBtn');
  const lat  = document.getElementById('reportLat').value;
  const lon  = document.getElementById('reportLon').value;
  if (!lat || !lon) {
    showToast('Por favor, selecciona una ubicación en el mapa o ingresa las coordenadas.', '⚠️');
    return;
  }
  const incidentType = document.querySelector('input[name="incidentType"]:checked')?.value || 'fuego_activo';
  const description  = document.getElementById('reportDesc')?.value || '';

  btn.disabled = true;
  btn.innerHTML = '<div class="spinner" style="width:18px;height:18px;border-width:2px"></div> Enviando...';

  let ok = false;
  let data = null;
  try {
    const resp = await fetch(`${API_URL}/report/citizen`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        lat: parseFloat(lat),
        lon: parseFloat(lon),
        incident_type: incidentType,
        description,
      }),
      signal: AbortSignal.timeout(25000),
    });
    ok = resp.ok;
    data = await resp.json().catch(() => null);
  } catch (_) { ok = false; }

  if (ok) {
    const detectedZone = data?.zone;
    const waStatus = data?.whatsapp?.status;
    const waReason = data?.whatsapp?.reason;
    let message = '¡Reporte registrado! El equipo lo verificará con datos satelitales.';
    let icon = '✅';

    if (waStatus === 'sent') {
      message = `¡Reporte registrado! Alerta enviada al grupo de ${detectedZone}.`;
    } else if (waStatus === 'skipped') {
      icon = '⚠️';
      if (waReason === 'outside_zone') {
        message = '¡Reporte registrado! El punto está fuera de las zonas operativas; no se envió WhatsApp.';
      } else if (waReason === 'group_not_configured') {
        message = `¡Reporte registrado! El grupo de ${detectedZone || 'esa zona'} no está configurado; no se envió WhatsApp.`;
      } else {
        message = '¡Reporte registrado! No se envió WhatsApp.';
      }
    } else if (waStatus === 'error') {
      icon = '⚠️';
      message = '¡Reporte registrado! No se pudo enviar el WhatsApp, pero el reporte quedó guardado.';
    }

    showToast(message, icon);
    document.getElementById('reportForm').reset();
    document.getElementById('photoPreview').style.display = 'none';
    document.getElementById('locationStatus').textContent = '';
    if (reportMarker) { reportMarker.remove(); reportMarker = null; }
    renderRecentReports();  // refrescar la lista de reportes
  } else {
    const detail = data?.detail;
    showToast(
      detail ? `No se pudo enviar: ${detail}` : 'No se pudo enviar (API offline). Modo demo: revisa que el servidor esté activo.',
      '⚠️'
    );
  }
  btn.disabled = false;
  btn.innerHTML = '<span class="btn-icon">⚠️</span> Enviar Reporte Ciudadano';
}

function previewPhoto() {
  const file = document.getElementById('reportPhoto').files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (e) => {
    const img = document.getElementById('photoPreview');
    img.src   = e.target.result;
    img.style.display = 'block';
  };
  reader.readAsDataURL(file);
}

/* ═══════════════════════════════════════════════════
   WHATSAPP
   ═══════════════════════════════════════════════════ */
function joinWhatsApp(e) {
  e.preventDefault();
  const zone = document.getElementById('waZone').value;
  if (!zone) {
    showToast('Selecciona tu zona para obtener el enlace de alertas.', '⚠️');
    return;
  }
  showToast(`¡Enlace copiado! Únete al grupo de ${zone.charAt(0).toUpperCase() + zone.slice(1)}.`, '📲');
  generateQRPlaceholder(zone);
}

function generateQRPlaceholder(zone) {
  const grid = document.getElementById('qrCode');
  grid.innerHTML = '';
  const seed = zone.split('').reduce((a, c) => a + c.charCodeAt(0), 0);
  for (let i = 0; i < 100; i++) {
    const cell = document.createElement('div');
    const on   = ((seed * (i + 7)) % 17) < 9;
    cell.style.cssText = `background:${on ? '#000' : '#fff'};border-radius:1px`;
    grid.appendChild(cell);
  }
}

/* ═══════════════════════════════════════════════════
   RECURSOS — MODAL
   ═══════════════════════════════════════════════════ */
const RESOURCE_CONTENT = {
  'vivir-zona-riesgo': {
    title: '🏠 Si vives cerca de una zona de riesgo',
    body: `
      <h4>Preparación previa</h4>
      <ul style="margin:0.5rem 0 1rem 1rem;line-height:2">
        <li>Identifica las rutas de evacuación de tu zona.</li>
        <li>Ten un kit de emergencia: agua, documentos, medicamentos, linterna.</li>
        <li>Mantén el número de Defensa Civil local a mano: <strong>115</strong>.</li>
        <li>Limpia maleza seca a 10 metros alrededor de tu vivienda.</li>
      </ul>
      <h4>Durante un incendio cercano</h4>
      <ul style="margin:0.5rem 0 1rem 1rem;line-height:2">
        <li>Cierra ventanas y puertas para evitar entrada de humo.</li>
        <li>Sigue instrucciones de Defensa Civil y Bomberos.</li>
        <li>Evacua solo si te lo indican las autoridades.</li>
      </ul>
      <h4>Después del incendio</h4>
      <ul style="margin:0.5rem 0 1rem 1rem;line-height:2">
        <li>No regreses hasta que las autoridades lo declaren seguro.</li>
        <li>Reporta zonas aún activas en esta plataforma.</li>
      </ul>`
  },
  'prevenir-quemas': {
    title: '🚜 Prevenir incendios agrícolas y de pastizales',
    body: `
      <h4>Alternativas a la quema</h4>
      <ul style="margin:0.5rem 0 1rem 1rem;line-height:2">
        <li><strong>Compostaje:</strong> Convierte residuos vegetales en abono.</li>
        <li><strong>Rastrillado:</strong> Incorpora rastrojos al suelo directamente.</li>
        <li><strong>Biodigestión:</strong> Transforma residuos orgánicos en biogás.</li>
      </ul>
      <h4>Si debes realizar quema controlada</h4>
      <ul style="margin:0.5rem 0 1rem 1rem;line-height:2">
        <li>Obtén permiso de SERFOR o la autoridad local.</li>
        <li>Verifica que el viento sea mínimo (&lt; 10 km/h).</li>
        <li>Ten agua y herramientas de contención disponibles.</li>
        <li>Nunca quemes en días de calor extremo o sequía.</li>
      </ul>`
  },
  'numeros-emergencia': {
    title: '📞 Directorio de Emergencias — Perú',
    body: `
      <div style="display:grid;gap:0.75rem">
        ${[
          ['116',         '🚒 Bomberos',           'Emergencias por fuego e incendios'],
          ['105',         '👮 Policía Nacional',    'Seguridad y orden público'],
          ['115',         '🏥 Defensa Civil INDECI','Gestión de desastres y emergencias'],
          ['117',         '🚑 SAMU',                'Emergencias médicas y ambulancias'],
          ['0800-11-070', '🌿 SERFOR',              'Reporte de incendios forestales (gratuito)'],
        ].map(([num, name, desc]) => `
          <div style="background:var(--color-bg-3);border-radius:8px;padding:0.9rem;display:flex;gap:1rem;align-items:center">
            <strong style="font-size:1.5rem;color:var(--color-danger);min-width:90px">${num}</strong>
            <div><strong>${name}</strong><br/><span style="font-size:0.82rem;color:var(--color-text-muted)">${desc}</span></div>
          </div>`).join('')}
      </div>`
  },
  'mapa-condiciones': {
    title: '💨 Condiciones meteorológicas de riesgo',
    body: `<p style="color:var(--color-text-muted)">Condiciones que favorecen la propagación de incendios:</p>
      <ul style="margin:0.75rem 0 1rem 1rem;line-height:2">
        <li><strong>Temperatura:</strong> Mayor a 30°C</li>
        <li><strong>Humedad relativa:</strong> Menor al 30%</li>
        <li><strong>Velocidad del viento:</strong> Mayor a 25 km/h</li>
        <li><strong>Días sin lluvia:</strong> Más de 7 días consecutivos</li>
      </ul>
      <p style="color:var(--color-text-muted)">Datos de <strong>Copernicus ERA5</strong> — actualización cada 6 horas.</p>`
  }
};

function openResource(id) {
  const content = RESOURCE_CONTENT[id];
  if (!content) return;
  document.getElementById('modalBody').innerHTML = `
    <h2 style="font-family:'Space Grotesk',sans-serif;margin-bottom:1.25rem">${content.title}</h2>
    ${content.body}`;
  document.getElementById('resourceModal').classList.add('open');
  document.body.style.overflow = 'hidden';
}
function closeResource() {
  document.getElementById('resourceModal').classList.remove('open');
  document.body.style.overflow = '';
}

/* ═══════════════════════════════════════════════════
   CONDICIONES METEOROLÓGICAS
   ═══════════════════════════════════════════════════ */
async function loadWeatherData() {
  try {
    const resp = await fetch(`${API_URL}/risk/today?limit=200`, { signal: AbortSignal.timeout(4000) });
    if (resp.ok) {
      const data = await resp.json();
      const feats = data.features || [];
      if (feats.length) {
        // Mostrar la celda de MAYOR riesgo (no la primera arbitraria del arreglo).
        const best = feats.reduce((a, b) =>
          (b.properties.probabilidad > a.properties.probabilidad ? b : a));
        const f = best.properties;
        document.getElementById('wTemp').textContent     = `${f.temp_2m?.toFixed(1)}°C`;
        document.getElementById('wHumidity').textContent = `${f.humedad_relativa?.toFixed(0)}%`;
        document.getElementById('wWind').textContent     = `${f.viento_velocidad?.toFixed(0)} km/h`;
        const fwi = Math.round((f.temp_2m * 0.5 + f.viento_velocidad * 0.3) / (f.humedad_relativa * 0.05 + 1));
        document.getElementById('wFWI').textContent = fwi;
        return;
      }
    }
  } catch (_) {}
  // Demo
  document.getElementById('wTemp').textContent     = '28.4°C';
  document.getElementById('wHumidity').textContent = '32%';
  document.getElementById('wWind').textContent     = '22 km/h';
  document.getElementById('wFWI').textContent      = '74';
}

/* ═══════════════════════════════════════════════════
   FRESCURA DE DATOS (modelo)
   ═══════════════════════════════════════════════════ */
async function loadDataFreshness() {
  const el = document.getElementById('dataFreshness');
  const mapBadge = document.getElementById('mapModelBadge');
  try {
    const resp = await fetch(`${API_URL}/health`, { signal: AbortSignal.timeout(4000) });
    if (resp.ok) {
      const h = await resp.json();
      const train = h.training_date
        ? new Date(h.training_date).toLocaleDateString('es-PE', { day: '2-digit', month: 'short', year: 'numeric' })
        : '—';
      const th = h.thresholds || {};
      if (el) {
        el.textContent = `🤖 Modelo ${h.model_version || ''} · entrenado ${train}` +
          (th.rojo != null ? ` · umbral Rojo ≥ ${Number(th.rojo).toFixed(3)}` : '');
      }
      if (mapBadge) {
        mapBadge.textContent = `🤖 ${h.model_version || 'v2.5.0'} · 21 variables · NDVI Sentinel-2`;
      }
      return;
    }
  } catch (_) {}
  if (el) el.textContent = '🤖 Modelo offline — mostrando datos simulados (demo)';
  if (mapBadge) mapBadge.textContent = '⚠️ API offline · Modo demostración';
}

/* ═══════════════════════════════════════════════════
   IMPORTANCIA GLOBAL SHAP EN VIVO (/model/importance)
   ═══════════════════════════════════════════════════ */
const SHAP_LABELS = {
  dist_carretera_m:       'Proximidad a carreteras',
  lluvia_acum_15d:        'Lluvia acumulada (15 d)',
  indice_sequedad:        'Índice de sequedad (FWI)',
  ndvi:                   'Vegetación (NDVI Sentinel-2)',
  elevacion_m:            'Elevación del terreno',
  vpd_kpa:                'Déficit presión vapor (VPD)',
  viento_dir_cos:         'Dirección viento (N-S)',
  viento_dir_sin:         'Dirección viento (E-O)',
  dist_poblado_m:         'Proximidad a poblados',
  pendiente_pct:          'Pendiente del terreno',
  viento_pendiente:       'Viento × Pendiente',
  humedad_relativa:       'Humedad relativa',
  temp_2m:                'Temperatura a 2 m',
  lluvia_acum_7d:         'Lluvia acumulada (7 d)',
  ndvi_anomaly:           'Anomalía local NDVI',
  viento_velocidad:       'Velocidad del viento',
  dias_sin_lluvia:        'Días sin lluvia',
  humedad_vecindad_media: 'Humedad entorno cercano',
  temp_vecindad_media:    'Temperatura entorno cercano',
  temp_lag1:              'Temperatura día previo',
  humedad_lag1:           'Humedad día previo',
};

async function loadShapImportance() {
  const container = document.getElementById('shapImportanceList');
  if (!container) return;
  try {
    const resp = await fetch(`${API_URL}/model/importance`, { signal: AbortSignal.timeout(6000) });
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    const data = await resp.json();
    const top = (data.feature_importance || []).slice(0, 8);
    if (!top.length) return;
    const maxPct = Math.max(...top.map(x => x.percentage || 0), 1);
    container.innerHTML = top.map(item => {
      const label = SHAP_LABELS[item.feature] || item.feature;
      const pct   = Number(item.percentage || 0);
      const width = Math.max(4, Math.round((pct / maxPct) * 100));
      return `
        <div class="shap-row">
          <span class="shap-label" title="${item.feature}">${label}</span>
          <div class="shap-bar-track"><div class="shap-bar-fill" style="width:${width}%"></div></div>
          <span class="shap-pct">${pct.toFixed(1)}%</span>
        </div>`;
    }).join('');
  } catch (_) {
    container.innerHTML = '<p style="font-size:0.82rem;opacity:0.7">⚠️ Importancias SHAP disponibles cuando la API está activa.</p>';
  }
}

/* ═══════════════════════════════════════════════════
   GUÍA DE LECTURA DEL MAPA
   ═══════════════════════════════════════════════════ */
function toggleMapGuide() {
  const body = document.getElementById('mapGuideBody');
  const icon = document.getElementById('guideToggleIcon');
  if (!body) return;
  const isOpen = body.classList.toggle('open');
  if (icon) icon.textContent = isOpen ? '▲' : '▼';
}

/* ═══════════════════════════════════════════════════
   NAVBAR
   ═══════════════════════════════════════════════════ */
function initNavbar() {
  const navbar = document.getElementById('navbar');
  const toggle = document.getElementById('navToggle');
  const links  = document.getElementById('navLinks');
  window.addEventListener('scroll', () => navbar.classList.toggle('scrolled', window.scrollY > 20));
  toggle.addEventListener('click', () => links.classList.toggle('open'));
  links.querySelectorAll('a').forEach(a => a.addEventListener('click', () => links.classList.remove('open')));
}

function scrollToSection(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
}

/* ═══════════════════════════════════════════════════
   PARTÍCULAS HERO
   ═══════════════════════════════════════════════════ */
function initParticles() {
  const container = document.getElementById('particles');
  const colors = ['#f97316', '#ef4444', '#eab308'];
  for (let i = 0; i < 30; i++) {
    const p    = document.createElement('div');
    const size = Math.random() * 6 + 2;
    p.classList.add('particle');
    p.style.cssText = `
      width:${size}px;height:${size}px;
      left:${Math.random() * 100}%;
      background:${colors[Math.floor(Math.random() * colors.length)]};
      animation-duration:${Math.random() * 15 + 10}s;
      animation-delay:${Math.random() * 10}s;`;
    container.appendChild(p);
  }
}

/* ═══════════════════════════════════════════════════
   TOAST
   ═══════════════════════════════════════════════════ */
let toastTimeout;
function showToast(msg, icon = '✅') {
  const toast = document.getElementById('toast');
  document.getElementById('toastMsg').textContent  = msg;
  document.getElementById('toastIcon').textContent = icon;
  toast.classList.add('show');
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => toast.classList.remove('show'), 4000);
}

/* ═══════════════════════════════════════════════════
   SCROLL ANIMATIONS
   ═══════════════════════════════════════════════════ */
function initScrollAnimations() {
  const observer = new IntersectionObserver(
    entries => entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.style.opacity   = '1';
        e.target.style.transform = 'translateY(0)';
      }
    }),
    { threshold: 0.1, rootMargin: '0px 0px -50px 0px' }
  );
  document.querySelectorAll(
    '.resource-card, .flow-card, .transparency-card, .whatsapp-subscribe-card'
  ).forEach(el => {
    el.style.opacity    = '0';
    el.style.transform  = 'translateY(24px)';
    el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
    observer.observe(el);
  });
}

/* ═══════════════════════════════════════════════════
   INICIALIZACIÓN
   ═══════════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  initNavbar();
  initParticles();
  initScrollAnimations();
  loadWeatherData();
  loadDataFreshness();
  loadShapImportance();

  // Stats iniciales con datos demo
  updateHeroStats(DEMO_FEATURES);
  updateRiskBadge(DEMO_FEATURES);

  // Mapa principal — carga cuando la sección entra en pantalla
  const mapObs = new IntersectionObserver(entries => {
    if (entries[0].isIntersecting) {
      if (!mainMap) initMainMap();
      mapObs.disconnect();
    }
  }, { threshold: 0.1 });
  mapObs.observe(document.getElementById('mapa'));

  // Mapa de reporte — carga cuando la sección entra en pantalla
  const reportObs = new IntersectionObserver(entries => {
    if (entries[0].isIntersecting) {
      if (!reportMap) initReportMap();
      reportObs.disconnect();
    }
  }, { threshold: 0.05 });
  reportObs.observe(document.getElementById('reporte'));
});
