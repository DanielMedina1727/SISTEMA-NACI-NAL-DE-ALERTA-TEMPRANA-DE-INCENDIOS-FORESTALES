"""
audit_final.py — Auditoría ISO 25010 sin llamadas a APIs externas lentas
"""
import sys, time, warnings, re
from pathlib import Path
warnings.filterwarnings('ignore')
ROOT = Path('.')
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import requests, joblib, numpy as np, pandas as pd

BASE = 'http://127.0.0.1:5050'
MODEL_PATH = ROOT / 'models' / 'lightgbm_wildfire.pkl'
WEB = ROOT / 'web'
APP = ROOT / 'app'
from app.model import FEATURE_ORDER as FEAT, DEFAULT_VALUES, THRESHOLDS  # 18 features (fuente única en app/model.py)
T = 5

def g(path, **params):
    try: return requests.get(f'{BASE}{path}', params=params, timeout=T)
    except: return None

def po(path, body):
    try: return requests.post(f'{BASE}{path}', json=body, timeout=T)
    except: return None

results = {}

print('\n' + '='*72)
print('  AUDITORIA ISO/IEC 25010:2011 — AlertaForestal Peru v2.0')
print('='*72)

# ─── 1. ADECUACION FUNCIONAL ─────────────────────────────────────────────────
print('\n[1] ADECUACION FUNCIONAL')
cat = []
# Endpoints que NO llaman a NASA en vivo
for ep in ['/health', '/risk/today', '/model/importance', '/social/matrix', '/alert/status']:
    x = g(ep)
    ok = x is not None and x.status_code < 500
    cat.append(ok)
    print(f'  {"OK  " if ok else "FAIL"}  GET {ep}  HTTP {x.status_code if x else "N/A"}')

from app.model import classify
# /predict: la clasificación debe ser consistente con los umbrales operativos del modelo
pl = {'grid_id': 'CAJ-001', 'pendiente_pct': 38.0, 'orientacion': 'NE', 'ndvi': 0.12,
      'dist_carretera_m': 120.0, 'dist_poblado_m': 350.0, 'temp_2m': 34.5,
      'humedad_relativa': 18.0, 'viento_velocidad': 32.0, 'viento_direccion': 45.0}
x = po('/predict', pl)
ok_predict = x is not None and x.status_code == 200
cat.append(ok_predict)
if ok_predict:
    d = x.json()
    ok_prob = 0.0 <= d['probabilidad'] <= 1.0
    ok_clas = d['nivel'] in ('Verde', 'Amarillo', 'Rojo') and d['nivel'] == classify(d['probabilidad'])
    cat.extend([ok_prob, ok_clas])
    print(f'  OK    POST /predict  nivel={d["nivel"]} p={d["probabilidad"]:.4f} percentil={d.get("percentil")}')
    print(f'  {"OK  " if ok_prob else "FAIL"}  probabilidad en [0,1]')
    print(f'  {"OK  " if ok_clas else "FAIL"}  Clasificación consistente con umbrales del modelo')
else:
    cat.extend([False, False])
    print(f'  FAIL  POST /predict')

# La lógica de umbrales (fuente única en app.model) debe particionar correctamente
ok_u1 = classify(THRESHOLDS['rojo']) == 'Rojo'
ok_u2 = classify(THRESHOLDS['amarillo']) == 'Amarillo'
ok_u3 = classify(0.0) == 'Verde'
cat.extend([ok_u1, ok_u2, ok_u3])
print(f'  {"OK  " if ok_u1 else "FAIL"}  classify(p99) == Rojo')
print(f'  {"OK  " if ok_u2 else "FAIL"}  classify(p95) == Amarillo')
print(f'  {"OK  " if ok_u3 else "FAIL"}  classify(0.0) == Verde')

# GeoJSON
x = g('/risk/today', limit=5)
if x and x.status_code == 200:
    d = x.json()
    ok = d.get('type') == 'FeatureCollection' and len(d.get('features', [])) > 0
    cat.append(ok)
    f0 = d['features'][0] if d['features'] else {}
    print(f'  {"OK  " if ok else "FAIL"}  GeoJSON type={d.get("type")} count={d.get("count")} geom={f0.get("geometry",{}).get("type")}')
    props = f0.get('properties', {})
    ok2 = 'nivel' in props and 'probabilidad' in props
    cat.append(ok2)
    print(f'  {"OK  " if ok2 else "FAIL"}  Propiedades nivel+probabilidad presentes')
else:
    cat.extend([False, False])

# Motor de propagacion
x = po('/propagate?grid_id=-78.5000_-7.1600&viento_direccion=45&viento_velocidad=25', {})
if x and x.status_code == 200:
    d = x.json()
    ok = len(d.get('grillas_afectadas', [])) > 0
    cat.append(ok)
    print(f'  {"OK  " if ok else "FAIL"}  POST /propagate  afectadas={len(d.get("grillas_afectadas",[]))}')
else:
    cat.append(False)

results['1_Adecuacion_Funcional'] = (sum(cat), len(cat))
print(f'  >>> {sum(cat)}/{len(cat)} ({sum(cat)/len(cat)*100:.1f}%)')

# ─── 2. EFICIENCIA DE DESEMPENO ───────────────────────────────────────────────
print('\n[2] EFICIENCIA DE DESEMPENO')
cat = []

for ep, lim_ms in [('/health', 200), ('/model/importance', 800), ('/alert/status', 300)]:
    times = []
    for _ in range(5):
        t0 = time.perf_counter()
        x = g(ep)
        if x and x.status_code == 200:
            times.append((time.perf_counter() - t0) * 1000)
    if times:
        avg = np.mean(times)
        ok = avg < lim_ms
        cat.append(ok)
        print(f'  {"OK  " if ok else "FAIL"}  {ep}  media={avg:.1f}ms  p95={np.percentile(times,95):.1f}ms  (obj<{lim_ms}ms)')

# ML batch 1000
model = joblib.load(MODEL_PATH)
np.random.seed(42)
N = 1000
RANGOS = {
    'pendiente_pct': (0, 60), 'ndvi': (0.05, 0.9),
    'dist_carretera_m': (50, 10000), 'dist_poblado_m': (100, 15000),
    'temp_2m': (12, 40), 'humedad_relativa': (8, 95),
    'viento_velocidad': (0, 70), 'viento_direccion': (0, 360),
}
df_batch = pd.DataFrame({
    col: (np.random.uniform(*RANGOS[col], N) if col in RANGOS else DEFAULT_VALUES.get(col, 0.0))
    for col in FEAT
})
t0 = time.perf_counter()
probas_batch = model.predict_proba(df_batch[FEAT])[:, 1]
ms_total = (time.perf_counter() - t0) * 1000
ms_per = ms_total / N
ok = ms_per < 2.0
cat.append(ok)
print(f'  {"OK  " if ok else "FAIL"}  ML batch N={N}  total={ms_total:.2f}ms  por_muestra={ms_per:.4f}ms  (obj<2ms)')

# Distribucion de niveles (umbrales data-driven de app/model.py)
rojas    = int((probas_batch >= THRESHOLDS["rojo"]).sum())
amarillas = int(((probas_batch >= THRESHOLDS["amarillo"]) & (probas_batch < THRESHOLDS["rojo"])).sum())
verdes   = int((probas_batch < THRESHOLDS["amarillo"]).sum())
print(f'  INFO  Distribucion: Rojo={rojas}({rojas/N:.1%}) Amarillo={amarillas}({amarillas/N:.1%}) Verde={verdes}({verdes/N:.1%})')
print(f'  INFO  Stats p: media={probas_batch.mean():.4f} mediana={np.median(probas_batch):.4f} std={probas_batch.std():.4f}')

# 20 peticiones consecutivas
times_20 = []
for _ in range(20):
    t0 = time.perf_counter()
    x = g('/health')
    if x and x.status_code == 200:
        times_20.append((time.perf_counter() - t0) * 1000)
ok_rate = len(times_20) / 20 >= 0.95
ok_p95  = np.percentile(times_20, 95) < 500 if times_20 else False
cat.extend([ok_rate, ok_p95])
print(f'  {"OK  " if ok_rate else "FAIL"}  Tasa exito 20x /health: {len(times_20)}/20')
print(f'  {"OK  " if ok_p95 else "FAIL"}  P95 latencia: {np.percentile(times_20,95):.1f}ms (obj<500ms)')

results['2_Eficiencia_Desempeno'] = (sum(cat), len(cat))
print(f'  >>> {sum(cat)}/{len(cat)} ({sum(cat)/len(cat)*100:.1f}%)')

# ─── 3. COMPATIBILIDAD ────────────────────────────────────────────────────────
print('\n[3] COMPATIBILIDAD')
cat = []

# CORS: el header solo se emite cuando la peticion trae Origin (comportamiento real)
try:
    x = requests.get(f'{BASE}/health', headers={'Origin': 'http://example.com'}, timeout=8)
    cors = x.headers.get('access-control-allow-origin', '')
except Exception:
    cors = ''
ok = len(cors) > 0
cat.append(ok)
print(f'  {"OK  " if ok else "FAIL"}  CORS Access-Control-Allow-Origin="{cors}"')

for ep in ['/health', '/model/importance', '/social/matrix']:
    x = g(ep)
    ct = x.headers.get('content-type', '') if x and x.status_code == 200 else ''
    ok = 'application/json' in ct
    cat.append(ok)
    print(f'  {"OK  " if ok else "FAIL"}  Content-Type JSON en {ep}')

x = g('/docs')
ok = x is not None and x.status_code == 200
cat.append(ok)
print(f'  {"OK  " if ok else "FAIL"}  Swagger /docs HTTP {x.status_code if x else "N/A"}')

x = g('/openapi.json')
ok = x is not None and x.status_code == 200
cat.append(ok)
print(f'  {"OK  " if ok else "FAIL"}  OpenAPI JSON HTTP {x.status_code if x else "N/A"}')

if x and x.status_code == 200:
    schema = x.json()
    title = schema.get('info', {}).get('title', '')
    ok = 'alerta' in title.lower() or 'wildfire' in title.lower()
    cat.append(ok)
    print(f'  {"OK  " if ok else "FAIL"}  OpenAPI titulo: "{title}"')
    endpoints_count = len(schema.get('paths', {}))
    ok2 = endpoints_count >= 8
    cat.append(ok2)
    print(f'  {"OK  " if ok2 else "FAIL"}  OpenAPI documenta >={8} endpoints (tiene {endpoints_count})')

# GeoJSON RFC 7946
x = g('/risk/today', limit=3)
if x and x.status_code == 200:
    d = x.json()
    f0 = d.get('features', [{}])[0]
    geom_type = f0.get('geometry', {}).get('type', '')
    ok = geom_type in ['Point', 'Polygon', 'MultiPolygon']
    cat.append(ok)
    print(f'  {"OK  " if ok else "FAIL"}  Geometria GeoJSON valida: "{geom_type}"')

results['3_Compatibilidad'] = (sum(cat), len(cat))
print(f'  >>> {sum(cat)}/{len(cat)} ({sum(cat)/len(cat)*100:.1f}%)')

# ─── 4. USABILIDAD ────────────────────────────────────────────────────────────
print('\n[4] USABILIDAD')
cat = []

idx_path = WEB / 'index.html'
html = idx_path.read_text(encoding='utf-8') if idx_path.exists() else ''

ui_checks = [
    ('Hero/RiskBadge dinámico',     'id="riskBadge"'),
    ('Sección Mapa',                'id="mapa"'),
    ('Sección WhatsApp',            'id="whatsapp"'),
    ('Formulario reporte',          'id="reportForm"'),
    ('Sección Recursos',            'id="recursos"'),
    ('Sección Transparencia',       'id="transparencia"'),
    ('Navbar responsivo',           '<nav'),
    ('Estadísticas FIRMS live',     'id="statFIRMS"'),
    ('Filtro región mapa',          'id="regionFilter"'),
    ('Selector zona WhatsApp',      'id="waZone"'),
    ('Leaflet Heatmap',             'leaflet.heat'),
    ('Toggle capas heatmap',        'id="toggleHeatmap"'),
    ('Toggle capas FIRMS',          'id="toggleFIRMS"'),
    ('Toggle capas IA',             'id="togglePolygons"'),
    ('SEO meta description',        'name="description"'),
    ('SEO viewport responsive',     'name="viewport"'),
    ('Google Fonts (Inter)',         'googleapis.com'),
    ('Mapa mini para reporte',      'id="reportMap"'),
    ('Scroll hint animado',         'scroll-arrow'),
]
for label, pat in ui_checks:
    ok = pat.lower() in html.lower()
    cat.append(ok)
    print(f'  {"OK  " if ok else "FAIL"}  {label}')

x = g('/')
ok = x is not None and x.status_code == 200 and 'text/html' in x.headers.get('content-type', '')
cat.append(ok)
print(f'  {"OK  " if ok else "FAIL"}  Portal web raíz / retorna HTML')

# Validacion de entrada
x = po('/predict', {})
ok = x is not None and x.status_code == 422
cat.append(ok)
print(f'  {"OK  " if ok else "FAIL"}  Validación 422 entrada incompleta (falta grid_id): HTTP {x.status_code if x is not None else "N/A"}')
if x and x.status_code == 422:
    ok2 = 'detail' in x.json()
    cat.append(ok2)
    print(f'  {"OK  " if ok2 else "FAIL"}  Respuesta 422 contiene "detail"')

results['4_Usabilidad'] = (sum(cat), len(cat))
print(f'  >>> {sum(cat)}/{len(cat)} ({sum(cat)/len(cat)*100:.1f}%)')

# ─── 5. FIABILIDAD ────────────────────────────────────────────────────────────
print('\n[5] FIABILIDAD')
cat = []

pl_rel = {'grid_id': 'R', 'pendiente_pct': 20.0, 'orientacion': 'NE', 'ndvi': 0.30,
          'dist_carretera_m': 400.0, 'dist_poblado_m': 800.0, 'temp_2m': 28.0,
          'humedad_relativa': 32.0, 'viento_velocidad': 20.0, 'viento_direccion': 45.0}
succ = 0
probas_rel = []
for _ in range(10):
    x = po('/predict', pl_rel)
    if x and x.status_code == 200:
        succ += 1
        probas_rel.append(x.json().get('probabilidad'))

ok1 = succ == 10
ok2 = len(set(round(v, 6) for v in probas_rel)) == 1 if probas_rel else False
cat.extend([ok1, ok2])
print(f'  {"OK  " if ok1 else "FAIL"}  Madurez: {succ}/10 llamadas /predict exitosas')
print(f'  {"OK  " if ok2 else "FAIL"}  Determinismo: valores_unicos={len(set(round(v,6) for v in probas_rel)) if probas_rel else "N/A"} p={probas_rel[0]:.6f}' if probas_rel else '  FAIL  Sin datos')

for label, body in [
    ('Temp extrema 60C', {'grid_id': 'E1', 'pendiente_pct': 20, 'orientacion': 'N', 'ndvi': 0.3,
                          'dist_carretera_m': 400, 'dist_poblado_m': 800, 'temp_2m': 60,
                          'humedad_relativa': 5, 'viento_velocidad': 100, 'viento_direccion': 45}),
    ('Humedad 100%',     {'grid_id': 'E2', 'pendiente_pct': 1, 'orientacion': 'S', 'ndvi': 0.95,
                          'dist_carretera_m': 20000, 'dist_poblado_m': 50000, 'temp_2m': 5,
                          'humedad_relativa': 100, 'viento_velocidad': 0.1, 'viento_direccion': 0}),
]:
    x = po('/predict', body)
    if x and x.status_code == 200:
        pv = x.json().get('probabilidad', -1)
        ok = 0.0 <= pv <= 1.0
        cat.append(ok)
        print(f'  {"OK  " if ok else "FAIL"}  Tolerancia {label}: p={pv:.4f} HTTP {x.status_code}')
    else:
        cat.append(False)
        print(f'  FAIL  Tolerancia {label}: HTTP {x.status_code if x else "N/A"}')

h_ok = sum(1 for _ in range(5) if (x := g('/health')) and x.status_code == 200)
ok = h_ok == 5
cat.append(ok)
print(f'  {"OK  " if ok else "FAIL"}  Disponibilidad /health: {h_ok}/5')

try:
    m2 = joblib.load(MODEL_PATH)
    ok = m2 is not None and hasattr(m2, 'predict_proba')
    sz = MODEL_PATH.stat().st_size / 1024
    cat.append(ok)
    print(f'  {"OK  " if ok else "FAIL"}  Modelo .pkl cargable: {sz:.0f} KB')
except Exception as e:
    cat.append(False)
    print(f'  FAIL  Modelo .pkl: {e}')

x = g('/alert/status')
if x and x.status_code == 200:
    d = x.json()
    ok = 'scheduler_activo' in d and 'horario' in d
    cat.append(ok)
    print(f'  {"OK  " if ok else "FAIL"}  Scheduler: activo={d.get("scheduler_activo")} horario={d.get("horario")}')

results['5_Fiabilidad'] = (sum(cat), len(cat))
print(f'  >>> {sum(cat)}/{len(cat)} ({sum(cat)/len(cat)*100:.1f}%)')

# ─── 6. SEGURIDAD ─────────────────────────────────────────────────────────────
print('\n[6] SEGURIDAD')
cat = []

x = g('/health')
if x:
    xcto = x.headers.get('x-content-type-options', '')
    ok = len(xcto) > 0
    cat.append(ok)
    print(f'  {"OK  " if ok else "AVISO"}  X-Content-Type-Options: "{xcto}" (recom: nosniff)')
    srv = x.headers.get('server', '')
    no_ver = not re.search(r'\d+\.\d+', srv)
    cat.append(no_ver)
    print(f'  {"OK  " if no_ver else "FAIL"}  Server sin versión exacta: "{srv}"')

for path in ['/.env', '/.env.example', '/.git/config']:
    x = g(path)
    ok = not x or x.status_code in [404, 403, 422]
    cat.append(ok)
    print(f'  {"OK  " if ok else "FAIL"}  {path} no accesible: HTTP {x.status_code if x else "N/A"}')

x = po('/predict', {'grid_id': "'; DROP TABLE grillas;--", 'pendiente_pct': 20,
                     'orientacion': 'N', 'ndvi': 0.3, 'dist_carretera_m': 400,
                     'dist_poblado_m': 800, 'temp_2m': 28, 'humedad_relativa': 32,
                     'viento_velocidad': 20, 'viento_direccion': 45})
ok = x is not None and x.status_code in [200, 422]
cat.append(ok)
print(f'  {"OK  " if ok else "FAIL"}  SQL injection en grid_id: HTTP {x.status_code if x else "N/A"}')

x = po('/predict', {})
ok = x is not None and x.status_code == 422
cat.append(ok)
print(f'  {"OK  " if ok else "FAIL"}  Payload vacío → 422: HTTP {x.status_code if x else "N/A"}')

env_ex = ROOT / '.env.example'
if env_ex.exists():
    c = env_ex.read_text(encoding="utf-8")
    real = any(k in c for k in ['a86632ae', 'bd46e923', 'minioadmin'])
    ok = not real
    cat.append(ok)
    print(f'  {"OK  " if ok else "FAIL"}  .env.example sin credenciales reales: {"limpio" if ok else "CREDENCIALES EXPUESTAS"}')

main_c = (APP / 'main.py').read_text()
real_in_code = 'a86632ae' in main_c
ok = not real_in_code
cat.append(ok)
print(f'  {"OK  " if ok else "FAIL"}  main.py sin API keys hardcodeadas: {"limpio" if ok else "KEY EXPUESTA EN CODIGO"}')

results['6_Seguridad'] = (sum(cat), len(cat))
print(f'  >>> {sum(cat)}/{len(cat)} ({sum(cat)/len(cat)*100:.1f}%)')

# ─── 7. MANTENIBILIDAD ────────────────────────────────────────────────────────
print('\n[7] MANTENIBILIDAD')
cat = []

dirs_ok = 0
for d in ['app', 'web', 'data_pipeline', 'airflow', 'dashboard', 'data', 'models', 'tests']:
    ok = (ROOT / d).exists()
    dirs_ok += ok
    cat.append(ok)
print(f'  {"OK  " if dirs_ok==8 else "PARCIAL"}  Directorios de proyecto: {dirs_ok}/8')

app_files_ok = 0
for f in ['main.py', 'model.py', 'propagation.py', 'scheduler.py', 'pdf_generator.py', 'whatsapp_alerts.py']:
    ok = (APP / f).exists()
    app_files_ok += ok
    cat.append(ok)
print(f'  {"OK  " if app_files_ok==6 else "PARCIAL"}  Módulos app/: {app_files_ok}/6 presentes')

main_c = (APP / 'main.py').read_text()
ok = 'os.getenv' in main_c
cat.append(ok)
print(f'  {"OK  " if ok else "FAIL"}  main.py usa os.getenv() para configuracion')

for fname in ['main.py', 'model.py', 'propagation.py']:
    c = (APP / fname).read_text()
    ok = '"""' in c or "'''" in c
    cat.append(ok)
    print(f'  {"OK  " if ok else "FAIL"}  app/{fname} tiene docstrings')

req = ROOT / 'requirements.txt'
lines = [l for l in req.read_text().splitlines() if l.strip() and not l.startswith('#')] if req.exists() else []
ok = len(lines) >= 10
cat.append(ok)
print(f'  {"OK  " if ok else "FAIL"}  requirements.txt: {len(lines)} dependencias')

has_ver = any('>=' in l or '==' in l for l in lines)
cat.append(has_ver)
print(f'  {"OK  " if has_ver else "FAIL"}  Dependencias con versiones mínimas (>=)')

ok = (ROOT / '.env.example').exists()
cat.append(ok)
print(f'  {"OK  " if ok else "FAIL"}  .env.example para onboarding')

ok = (ROOT / 'docker-compose.yml').exists()
cat.append(ok)
print(f'  {"OK  " if ok else "FAIL"}  docker-compose.yml presente (IaC)')

ok = (ROOT / 'Dockerfile').exists()
cat.append(ok)
print(f'  {"OK  " if ok else "FAIL"}  Dockerfile presente')

tests_found = list((ROOT / 'tests').glob('*.py'))
ok = len(tests_found) >= 3
cat.append(ok)
print(f'  {"OK  " if ok else "FAIL"}  Suite de tests: {len(tests_found)} archivos (.py)')

results['7_Mantenibilidad'] = (sum(cat), len(cat))
print(f'  >>> {sum(cat)}/{len(cat)} ({sum(cat)/len(cat)*100:.1f}%)')

# ─── 8. PORTABILIDAD ──────────────────────────────────────────────────────────
print('\n[8] PORTABILIDAD')
cat = []

df_path = ROOT / 'Dockerfile'
if df_path.exists():
    dc = df_path.read_text()
    for instr in ['FROM', 'WORKDIR', 'COPY', 'CMD']:
        ok = instr in dc
        cat.append(ok)
        print(f'  {"OK  " if ok else "FAIL"}  Dockerfile: instruccion {instr}')

pq = ROOT / 'data' / 'dataset.parquet'
csv_f = ROOT / 'data' / 'dataset.csv'
ok = pq.exists()
cat.append(ok)
print(f'  {"OK  " if ok else "FAIL"}  dataset.parquet ({pq.stat().st_size/1024/1024:.1f} MB)' if ok else '  FAIL  dataset.parquet no existe')
ok2 = csv_f.exists()
cat.append(ok2)
print(f'  {"OK  " if ok2 else "FAIL"}  dataset.csv ({csv_f.stat().st_size/1024/1024:.1f} MB)' if ok2 else '  FAIL  dataset.csv no existe')

x = g('/')
ok = x is not None and x.status_code == 200 and 'text/html' in x.headers.get('content-type', '')
cat.append(ok)
print(f'  {"OK  " if ok else "FAIL"}  FastAPI sirve HTML en / (sin servidor externo)')

req_c = req.read_text().lower() if req.exists() else ''
for pkg, desc in [('fastapi','API REST'), ('lightgbm','ML'), ('geopandas','Geoespacial'),
                   ('locust','Carga'), ('apscheduler','Alertas automáticas'), ('streamlit','Dashboard')]:
    ok = pkg in req_c
    cat.append(ok)
    print(f'  {"OK  " if ok else "FAIL"}  requirements.txt incluye {pkg} ({desc})')

for f in ['main.py', 'model.py', 'propagation.py']:
    c = (APP / f).read_text()
    usa_pathlib = 'from pathlib' in c or 'Path(' in c
    tiene_acceso_archivos = any(t in c for t in ('open(', 'read_text', 'read_csv', 'joblib.load', 'pickle.load'))
    sin_rutas_os = ('C:\\' not in c) and ('/home/' not in c) and ('/Users/' not in c)
    # Portabilidad: sin rutas absolutas OS-especificas; usa pathlib cuando accede a archivos
    ok = sin_rutas_os and (usa_pathlib or not tiene_acceso_archivos)
    cat.append(ok)
    print(f'  {"OK  " if ok else "FAIL"}  app/{f} portabilidad de rutas (pathlib / sin rutas OS)')

results['8_Portabilidad'] = (sum(cat), len(cat))
print(f'  >>> {sum(cat)}/{len(cat)} ({sum(cat)/len(cat)*100:.1f}%)')

# ─── RESUMEN FINAL ────────────────────────────────────────────────────────────
print('\n' + '='*72)
print('  RESUMEN EJECUTIVO — ISO/IEC 25010:2011')
print('='*72)
NAMES = {
    '1_Adecuacion_Funcional': '1. Adecuacion Funcional',
    '2_Eficiencia_Desempeno': '2. Eficiencia de Desempeno',
    '3_Compatibilidad':       '3. Compatibilidad',
    '4_Usabilidad':           '4. Usabilidad',
    '5_Fiabilidad':           '5. Fiabilidad',
    '6_Seguridad':            '6. Seguridad',
    '7_Mantenibilidad':       '7. Mantenibilidad',
    '8_Portabilidad':         '8. Portabilidad',
}
total_p = 0
total_t = 0
print(f'\n  {"Caracteristica":<30} {"OK":>4}/{"Tot":<4}  {"Pct":>6}  Nivel')
print('  ' + '-'*62)
for key, name in NAMES.items():
    ps, tot = results.get(key, (0, 0))
    pct = ps / tot * 100 if tot else 0
    total_p += ps; total_t += tot
    if pct >= 90:   grade = 'EXCELENTE  [*****]'
    elif pct >= 75: grade = 'BUENO      [****]'
    elif pct >= 60: grade = 'ACEPTABLE  [***]'
    else:           grade = 'MEJORABLE  [**]'
    print(f'  {name:<30} {ps:>4}/{tot:<4}  {pct:>6.1f}%  {grade}')
print('  ' + '-'*62)
gpct = total_p / total_t * 100 if total_t else 0
verdict = 'SISTEMA APROBADO' if gpct >= 80 else 'CONDICIONAL (>60%)' if gpct >= 60 else 'REPROBADO'
print(f'  {"TOTAL GLOBAL":<30} {total_p:>4}/{total_t:<4}  {gpct:>6.1f}%  {verdict}')
print('='*72)
print(f'\n  Fecha: {__import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
print(f'  Sistema: AlertaForestal Peru v2.0  |  URL: {BASE}')
print(f'  Norma: ISO/IEC 25010:2011\n')
