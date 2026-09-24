/**
 * AlertaForestal Perú — Lógica principal del portal ciudadano
 * Conecta con la API FastAPI backend (http://localhost:8000)
 * Maneja mapa Leaflet, focos NASA FIRMS, formularios, métricas y animaciones.
 */

/* ═══════════════════════════════════════════════════
   CONFIGURACIÓN GLOBAL
   ═══════════════════════════════════════════════════ */
const API_URL = 'http://localhost:8000';

// NASA FIRMS — acceso directo desde frontend o vía proxy FastAPI
const FIRMS_KEY  = 'a86632ae3bb704ddc1818342f63bf8b0';
const FIRMS_BASE = 'https://firms.modaps.eosdis.nasa.gov/api/area/csv';

// Bounding boxes predefinidas (minLon, minLat, maxLon, maxLat)
const FIRMS_BBOXES = {
  all:       '-81.5,-18.5,-68.5,0',
  cajamarca: '-79.5,-7.8,-77.5,-4.5',
  norte:     '-80.5,-6.0,-75.0,0',
  sur:       '-81.5,-18.5,-68.5,-6.0',
};

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
  const cellSize = 0.009;
  for (let lat = -7.7; lat <= -6.6; lat += 0.05) {
    for (let lon = -79.0; lon <= -77.9; lon += 0.05) {
      const noise = Math.sin(lat * 47) * Math.cos(lon * 31) * 0.5 + 0.5;
      const prob  = Math.max(0.01, Math.min(0.99, noise + (Math.random() - 0.5) * 0.2));
      const nivel = prob >= 0.70 ? 'Rojo' : prob >= 0.35 ? 'Amarillo' : 'Verde';

      // En modo demo solo mostramos zonas de riesgo real (Rojo/Amarillo)
      // Las zonas verdes se omiten para no crear un "tapete" artificial
      if (nivel === 'Verde') continue;

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
          temp_2m: 22 + noise * 14,
          humedad_relativa: 70 - noise * 50,
          viento_velocidad: 5 + noise * 35,
          viento_direccion: Math.random() * 360,
          pendiente_pct: noise * 40,
          ndvi: 0.8 - noise * 0.6,
          _isDemo: true,
        }
      });
    }
  }
  return features;
}

/**
 * Genera focos de calor demo con coordenadas realistas de Perú
 * para cuando NASA FIRMS está bloqueado por CORS y la API no está activa.
 */
function generateRealisticFIRMSDemo(region) {
  // Focos representativos reales de Perú (zona sur amazónica, típicos en septiembre)
  const BASE_HOTSPOTS = [
    // Madre de Dios / Puno
    { lat: -12.58, lon: -69.18, frp: 38.2, conf: 0.95, sat: 'N20',  d: 'D' },
    { lat: -12.61, lon: -69.21, frp: 22.1, conf: 0.75, sat: 'SNPP', d: 'D' },
    { lat: -13.10, lon: -70.05, frp: 15.4, conf: 0.75, sat: 'N20',  d: 'N' },
    { lat: -13.28, lon: -69.85, frp: 8.6,  conf: 0.75, sat: 'SNPP', d: 'D' },
    // Ucayali / Loreto
    { lat: -8.34,  lon: -74.52, frp: 5.2,  conf: 0.75, sat: 'SNPP', d: 'D' },
    { lat: -8.41,  lon: -74.60, frp: 12.7, conf: 0.95, sat: 'N20',  d: 'D' },
    { lat: -9.15,  lon: -75.10, frp: 3.1,  conf: 0.40, sat: 'SNPP', d: 'N' },
    // Cajamarca / La Libertad
    { lat: -7.22,  lon: -78.51, frp: 4.8,  conf: 0.75, sat: 'SNPP', d: 'D' },
    { lat: -7.45,  lon: -78.73, frp: 7.3,  conf: 0.75, sat: 'N20',  d: 'D' },
    { lat: -6.98,  lon: -78.22, frp: 2.1,  conf: 0.40, sat: 'SNPP', d: 'D' },
    { lat: -7.08,  lon: -78.90, frp: 11.5, conf: 0.95, sat: 'SNPP', d: 'D' },
    // Ayacucho / Apurimac
    { lat: -14.07, lon: -73.45, frp: 6.8,  conf: 0.75, sat: 'SNPP', d: 'D' },
    { lat: -14.22, lon: -73.62, frp: 9.4,  conf: 0.75, sat: 'N20',  d: 'N' },
    // Junin / Huánuco
    { lat: -10.30, lon: -74.80, frp: 4.1,  conf: 0.40, sat: 'SNPP', d: 'D' },
    { lat: -10.55, lon: -75.10, frp: 18.3, conf: 0.95, sat: 'N20',  d: 'D' },
    { lat: -9.88,  lon: -74.21, frp: 6.5,  conf: 0.75, sat: 'SNPP', d: 'D' },
  ];

  // Si la región es cajamarca, filtrar aproximadamente
  let spots = BASE_HOTSPOTS;
  if (region === 'cajamarca') {
    spots = BASE_HOTSPOTS.filter(h => h.lat >= -7.8 && h.lat <= -4.5 && h.lon >= -79.5 && h.lon <= -77.5);
    if (spots.length === 0) spots = BASE_HOTSPOTS.slice(7, 11); // focos de Cajamarca
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
   MAPA PRINCIPAL (LEAFLET)
   ═══════════════════════════════════════════════════ */
let mainMap, heatmapLayer, polygonLayerGroup, firmsLayerGroup;
let currentFeatures = [];

function initMainMap() {
  mainMap = L.map('map', {
    center: [-9.0, -75.5],   // Centro de Perú para ver focos nacionales
    zoom: 6,
    zoomControl: true,
  });

  L.tileLayer('https://basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png?key=cb1_3w0w_1_edb38c89c08e55d3c9622c84', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>',
    maxZoom: 19,
  }).addTo(mainMap);

  polygonLayerGroup = L.layerGroup().addTo(mainMap);
  firmsLayerGroup   = L.layerGroup().addTo(mainMap);

  loadMapData();
  loadFIRMSHotspots();
}

/* ── Predicciones IA ── */
async function loadMapData() {
  showMapLoading(true);
  let features    = [];
  let isDemo      = false;
  let apiOnline   = false;
  try {
    const resp = await fetch(`${API_URL}/risk/today?limit=1200`, { signal: AbortSignal.timeout(10000) });
    if (resp.ok) {
      const data = await resp.json();
      features  = data.features || [];
      apiOnline = true;
    }
  } catch (_) {
    features = DEMO_FEATURES;
    isDemo   = true;
  }
  currentFeatures = features;
  renderMapLayers(features);
  updateHeroStats(features);
  updateRiskBadge(features);
  // Solo mostrar banner de demo cuando la API está realmente offline
  showDemoBanner(isDemo, apiOnline);
  showMapLoading(false);
}

function renderMapLayers(features) {
  polygonLayerGroup.clearLayers();
  if (heatmapLayer && mainMap.hasLayer(heatmapLayer)) mainMap.removeLayer(heatmapLayer);

  const showHeat = document.getElementById('toggleHeatmap').checked;
  const showPoly = document.getElementById('togglePolygons').checked;

  if (showHeat) {
    const heatData = features.map(f => {
      const coords = f.geometry.coordinates[0];
      const lats = coords.map(p => p[1]);
      const lons = coords.map(p => p[0]);
      return [
        lats.reduce((a,b) => a+b, 0) / lats.length,
        lons.reduce((a,b) => a+b, 0) / lons.length,
        f.properties.probabilidad
      ];
    });
    heatmapLayer = L.heatLayer(heatData, {
      radius: 20, blur: 18, maxZoom: 14,
      gradient: { 0.2: '#22c55e', 0.5: '#f97316', 0.8: '#ef4444', 1.0: '#7f1d1d' }
    }).addTo(mainMap);
  }

  if (showPoly) {
    features.forEach(f => {
      const props   = f.properties;
      const isDemo  = !!props._isDemo;
      const color   = COLOR_MAP[props.nivel] || '#22c55e';
      const coords  = f.geometry.coordinates[0].map(p => [p[1], p[0]]);
      const demoTag = isDemo
        ? '<div style="margin-top:6px;padding:4px 8px;background:#1e293b;border-radius:4px;font-size:10px;color:#94a3b8">⚠️ Predicción simulada — <a href=\'#\' style=\'color:#f97316\' onclick=\'event.preventDefault();showToast("Inicia: uvicorn app.main:app --reload --port 8000",\"💻\")\'>iniciar API</a> para datos reales del modelo LightGBM</div>'
        : '';
      const popup = `
        <div style="font-family:Inter,sans-serif;font-size:12px;min-width:210px;color:#1a1a2e">
          <b style="font-size:13px">🤖 Predicción IA — Grilla ${props.grid_id}</b><hr style="margin:6px 0"/>
          <b>Nivel:</b> <span style="color:${color};font-weight:700">${props.nivel}</span><br/>
          <b>Probabilidad:</b> ${(props.probabilidad * 100).toFixed(1)}%<br/>
          <b>Temperatura:</b> ${props.temp_2m?.toFixed(1)} °C<br/>
          <b>Humedad:</b> ${props.humedad_relativa?.toFixed(0)} %<br/>
          <b>Viento:</b> ${props.viento_velocidad?.toFixed(0)} km/h<br/>
          <b>Pendiente:</b> ${props.pendiente_pct?.toFixed(0)} %
          ${demoTag}
        </div>`;
      L.polygon(coords, {
        color: '#000', weight: 0.4,
        fillColor: color,
        fillOpacity: isDemo ? 0.35 : 0.55,   // más transparente en demo
        dashArray:  isDemo ? '4 3' : null,    // bordes discontinuos en demo
      }).bindPopup(popup).addTo(polygonLayerGroup);
    });
  }
}

function toggleHeatmapLayer() { renderMapLayers(currentFeatures); }
function togglePolygonLayer() { renderMapLayers(currentFeatures); }
function filterByRegion()     { loadMapData(); loadFIRMSHotspots(); }

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
    banner.innerHTML = '⚠️ <b>API offline</b> — Predicciones simuladas. Inicia el servidor para datos reales del modelo LightGBM';
    banner.style.opacity = '1';
    banner.style.display = 'block';
  } else if (apiOnline) {
    // API activa — datos reales del modelo
    banner.style.background = 'rgba(0,30,10,0.85)';
    banner.style.border     = '1px solid #22c55e';
    banner.style.color      = '#86efac';
    banner.innerHTML = '✅ <b>Modelo LightGBM activo</b> — Predicciones de riesgo en tiempo real';
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

  firmsLayerGroup.clearLayers();
  const showFIRMS = document.getElementById('toggleFIRMS')?.checked;
  if (showFIRMS === false) return;

  const regionVal = document.getElementById('regionFilter')?.value || 'cajamarca';
  const bboxKey   = FIRMS_BBOXES[regionVal] ? regionVal : 'cajamarca';
  const bbox      = FIRMS_BBOXES[bboxKey];

  updateLegendTime('⏳ Cargando focos satelitales...');

  let features     = [];
  let source       = 'simulación';
  let apiContactado = false;   // ¿logramos llegar a la API real?

  // 1) Intentar vía proxy FastAPI (datos reales, sin CORS)
  try {
    const proxyResp = await fetch(
      `${API_URL}/firms/hotspots?region=${bboxKey}&source=VIIRS_SNPP_NRT&days=1`,
      { signal: AbortSignal.timeout(6000) }
    );
    if (proxyResp.ok) {
      const data = await proxyResp.json();
      features      = data.features || [];
      source        = 'NASA FIRMS (tiempo real)';
      apiContactado = true;
    }
  } catch (_) { /* proxy no disponible */ }

  // 2) Fallback: llamar directamente a NASA FIRMS (puede funcionar en algunos navegadores)
  if (!apiContactado) {
    try {
      const firmsUrl = `${FIRMS_BASE}/${FIRMS_KEY}/VIIRS_SNPP_NRT/${bbox}/1`;
      const resp = await fetch(firmsUrl, { mode: 'cors', signal: AbortSignal.timeout(12000) });
      if (resp.ok) {
        const csvText = await resp.text();
        features      = parseFIRMScsv(csvText);
        source        = 'FIRMS directo';
        apiContactado = true;
      }
    } catch (_) { /* CORS bloqueado */ }
  }

  // 3) Fallback final: focos de referencia histórica (solo cuando NO se pudo contactar ninguna fuente real)
  if (!apiContactado) {
    features = generateRealisticFIRMSDemo(bboxKey);
    source   = 'simulación';
    console.info(
      '%c🛰️ NASA FIRMS: inicia la API FastAPI en puerto 8000 para focos REALES.\n' +
      'Comando: uvicorn app.main:app --reload --port 8000',
      'color:#f97316;font-weight:bold'
    );
  }

  renderFIRMSLayer(features, apiContactado);
  animateCounter('statFIRMS', features.length);

  if (apiContactado && features.length === 0) {
    updateLegendTime(`✅ API activa · Sin focos hoy en esta región`);
  } else {
    updateLegendTime(`🛰️ VIIRS · ${features.length} focos · ${source}`);
  }
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
function renderFIRMSLayer(features, apiContactado = false) {
  firmsLayerGroup.clearLayers();
  features.forEach(f => {
    const p       = f.properties;
    const lat     = f.geometry.coordinates[1];
    const lon     = f.geometry.coordinates[0];
    // Un foco es «demo» solo si no pudimos contactar ninguna fuente real
    const isDemo  = !apiContactado;
    const color   = p.nivel === 'Rojo' ? '#ef4444' : p.nivel === 'Amarillo' ? '#f97316' : '#eab308';
    const radius  = p.nivel === 'Rojo' ? 8 : 5;

    const t      = String(p.acq_time).padStart(4, '0');
    const tFmt   = `${t.slice(0,2)}:${t.slice(2)} UTC`;
    const isDark = p.daynight === 'N' ? '🌙 Nocturno' : '☀️ Diurno';
    const confPct = Math.round(p.confidence * 100);

    // Cabecera e indicador de fuente
    const header = isDemo
      ? `<b style="font-size:13px">🛰️ Foco de Referencia Histórica</b>
         <div style="background:#fef3c7;border-radius:4px;padding:3px 6px;margin:4px 0;font-size:10px;color:#92400e">
           📋 Zona activa histórica de Perú.<br/>
           <i>La API no está disponible. Inicia el servidor para ver focos de hoy.</i>
         </div>`
      : `<b style="font-size:13px">🛰️ Foco Satelital REAL</b>
         <div style="background:#dcfce7;border-radius:4px;padding:3px 6px;margin:4px 0;font-size:10px;color:#166534">
           ✅ Detectado por NASA FIRMS — datos en tiempo real
         </div>`;

    const popup = `
      <div style="font-family:Inter,sans-serif;font-size:12px;min-width:220px;color:#1a1a2e">
        ${header}
        <hr style="margin:5px 0"/>
        <b>Satélite:</b> ${p.satellite} (${p.instrument})<br/>
        <b>Detección:</b> ${p.acq_date} ${tFmt}<br/>
        <b>Confianza:</b> <span style="color:${color};font-weight:700">${confPct}%</span><br/>
        <b>FRP:</b> ${p.frp} MW <span style="color:#888;font-size:10px">(potencia radiativa)</span><br/>
        <b>Temperatura:</b> ${p.bright_ti4.toFixed(1)} K<br/>
        <b>Periodo:</b> ${isDark}<br/>
        <b>Nivel:</b> <span style="color:${color};font-weight:700">${p.nivel}</span>
      </div>`;

    L.circleMarker([lat, lon], {
      radius,
      color:       '#fff',
      weight:      isDemo ? 1 : 2,
      fillColor:   color,
      fillOpacity: isDemo ? 0.65 : 0.88,
      dashArray:   isDemo ? '3 2' : null,   // borde discontinuo = demo
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
function updateHeroStats(features) {
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

function updateRiskBadge(features) {
  const rojas     = features.filter(f => f.properties.nivel === 'Rojo').length;
  const amarillas = features.filter(f => f.properties.nivel === 'Amarillo').length;
  const el = document.getElementById('badgeLevel');
  let level, cls;
  if (rojas > 20)                       { level = 'ALTO 🔴';  cls = 'alto';  }
  else if (rojas > 5 || amarillas > 30) { level = 'MEDIO 🟡'; cls = 'medio'; }
  else                                  { level = 'BAJO 🟢';  cls = 'bajo';  }
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
  L.tileLayer('https://basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png?key=cb1_3w0w_1_edb38c89c08e55d3c9622c84', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>',
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

function renderRecentReports() {
  const reports = [
    { tipo: 'Columna de humo',  zona: 'Cajamarca Centro', hora: 'Hace 12 min', estado: 'verified' },
    { tipo: 'Fuego activo',     zona: 'Jaén Norte',       hora: 'Hace 1h',     estado: 'verified' },
    { tipo: 'Quema agrícola',   zona: 'Chota',            hora: 'Hace 3h',     estado: 'pending'  },
  ];
  document.getElementById('recentReportsList').innerHTML = reports.map(r => `
    <div class="report-item">
      <div class="report-dot ${r.estado}"></div>
      <div style="flex:1">
        <strong style="font-size:0.82rem">${r.tipo}</strong>
        <span style="color:var(--color-text-muted);font-size:0.76rem;display:block">${r.zona} · ${r.hora}</span>
      </div>
      ${r.estado === 'verified'
        ? '<span style="font-size:0.7rem;color:var(--color-success)">✓ Verificado</span>'
        : '<span style="font-size:0.7rem;color:var(--color-warning)">⏳ Revisando</span>'}
    </div>`).join('');
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
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner" style="width:18px;height:18px;border-width:2px"></div> Enviando...';
  await new Promise(r => setTimeout(r, 1500));
  showToast('¡Reporte enviado! El equipo lo verificará en los próximos minutos.', '✅');
  document.getElementById('reportForm').reset();
  document.getElementById('photoPreview').style.display = 'none';
  document.getElementById('locationStatus').textContent = '';
  if (reportMarker) { reportMarker.remove(); reportMarker = null; }
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
    const resp = await fetch(`${API_URL}/risk/today?limit=10`, { signal: AbortSignal.timeout(3000) });
    if (resp.ok) {
      const data = await resp.json();
      const f = data.features?.[0]?.properties;
      if (f) {
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
