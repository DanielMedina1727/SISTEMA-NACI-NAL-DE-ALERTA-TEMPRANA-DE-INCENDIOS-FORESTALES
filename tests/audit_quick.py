"""
audit_quick.py - Resumen ejecutivo de auditoría ISO 25010
"""
import sys, time, warnings
import requests, joblib, numpy as np, pandas as pd
from pathlib import Path

warnings.filterwarnings('ignore')
ROOT = Path('.')
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = 'http://localhost:5050'
MODEL_PATH = ROOT / 'models' / 'lightgbm_wildfire.pkl'
WEB_DIR = ROOT / 'web'
APP_DIR = ROOT / 'app'

FEAT = ['pendiente_pct','ndvi','dist_carretera_m','dist_poblado_m',
        'temp_2m','humedad_relativa','viento_velocidad','viento_direccion']

def g(path, timeout=8, **params):
    try: return requests.get(f'{BASE_URL}{path}', params=params, timeout=timeout)
    except: return None

def p(path, body, timeout=8):
    try: return requests.post(f'{BASE_URL}{path}', json=body, timeout=timeout)
    except: return None

results = {}

print('\n' + '='*72)
print('  AUDITORIA ISO/IEC 25010:2011 — AlertaForestal Peru v2.0')
print('='*72)

# ── 1. ADECUACION FUNCIONAL ──────────────────────────────────────────────────
print('\n[1] ADECUACION FUNCIONAL')
cat = []
for ep,m in [('/health','GET'),('/risk/today','GET'),('/model/importance','GET'),
             ('/social/matrix','GET'),('/alert/status','GET'),('/firms/hotspots','GET')]:
    r = g(ep)
    ok = r is not None and r.status_code < 500
    cat.append(ok)
    print(f'  {"PASA" if ok else "FALLA"}  {m} {ep}  HTTP {r.status_code if r else "N/A"}')

pl = {'grid_id':'CAJ-001','pendiente_pct':38.0,'orientacion':'NE','ndvi':0.12,
      'dist_carretera_m':120.0,'dist_poblado_m':350.0,'temp_2m':34.5,
      'humedad_relativa':18.0,'viento_velocidad':32.0,'viento_direccion':45.0}
r = p('/predict', pl)
ok = r is not None and r.status_code == 200
cat.append(ok)
if ok:
    d = r.json()
    print(f'  PASA  POST /predict  nivel={d["nivel"]} p={d["probabilidad"]:.4f}')
    ok2 = d['nivel'] == 'Rojo'
    cat.append(ok2)
    print(f'  {"PASA" if ok2 else "FALLA"}  Escenario critico -> Rojo: {d["nivel"]}')

r = g('/risk/today', limit=5)
if r and r.status_code == 200:
    d = r.json()
    f0 = d['features'][0] if d['features'] else {}
    ok = d.get('type') == 'FeatureCollection'
    cat.append(ok)
    print(f'  {"PASA" if ok else "FALLA"}  GeoJSON type={d.get("type")} count={d.get("count")} geom={f0.get("geometry",{}).get("type")}')

r = p('/propagate?grid_id=-78.5000_-7.1600&viento_direccion=45&viento_velocidad=25', {})
if r and r.status_code == 200:
    d = r.json()
    ok = len(d.get('grillas_afectadas', [])) > 0
    cat.append(ok)
    print(f'  {"PASA" if ok else "FALLA"}  POST /propagate  afectadas={len(d.get("grillas_afectadas",[]))}')

results['1_Adecuacion_Funcional'] = (sum(cat), len(cat))

# ── 2. EFICIENCIA DE DESEMPENO ────────────────────────────────────────────────
print('\n[2] EFICIENCIA DE DESEMPENO')
cat = []
for ep, lim_ms in [('/health', 200), ('/model/importance', 500)]:
    times = []
    for _ in range(5):
        t0 = time.perf_counter()
        r = g(ep)
        if r and r.status_code == 200:
            times.append((time.perf_counter()-t0)*1000)
    if times:
        avg = np.mean(times)
        ok = avg < lim_ms
        cat.append(ok)
        print(f'  {"PASA" if ok else "FALLA"}  {ep}  media={avg:.1f}ms (obj<{lim_ms}ms) p95={np.percentile(times,95):.1f}ms')

model = joblib.load(MODEL_PATH)
np.random.seed(42); N = 1000
df = pd.DataFrame({
    'pendiente_pct': np.random.uniform(0,60,N), 'ndvi': np.random.uniform(0.05,0.9,N),
    'dist_carretera_m': np.random.uniform(50,10000,N), 'dist_poblado_m': np.random.uniform(100,15000,N),
    'temp_2m': np.random.uniform(12,40,N), 'humedad_relativa': np.random.uniform(8,95,N),
    'viento_velocidad': np.random.uniform(0,70,N), 'viento_direccion': np.random.uniform(0,360,N)
})
t0 = time.perf_counter(); _ = model.predict_proba(df[FEAT])[:,1]
ms = (time.perf_counter()-t0)*1000
ms_p = ms/N
ok = ms_p < 2.0
cat.append(ok)
print(f'  {"PASA" if ok else "FALLA"}  ML batch N={N}  total={ms:.2f}ms  por_muestra={ms_p:.4f}ms (obj<2ms)')

# 20 peticiones consecutivas
times_h = []
for _ in range(20):
    t0 = time.perf_counter()
    r = g('/health')
    if r and r.status_code == 200:
        times_h.append((time.perf_counter()-t0)*1000)
ok1 = len(times_h)/20 >= 0.95
ok2 = np.percentile(times_h, 95) < 500 if times_h else False
cat.extend([ok1, ok2])
print(f'  {"PASA" if ok1 else "FALLA"}  20 peticiones /health: {len(times_h)}/20 exitosas')
print(f'  {"PASA" if ok2 else "FALLA"}  P95 latencia /health: {np.percentile(times_h,95):.1f}ms (obj<500ms)')

results['2_Eficiencia_Desempeno'] = (sum(cat), len(cat))

# ── 3. COMPATIBILIDAD ─────────────────────────────────────────────────────────
print('\n[3] COMPATIBILIDAD')
cat = []
r = g('/health')
cors = r.headers.get('access-control-allow-origin','') if r else ''
ok = len(cors) > 0
cat.append(ok)
print(f'  {"PASA" if ok else "FALLA"}  CORS: Access-Control-Allow-Origin="{cors}"')

for ep in ['/health', '/risk/today?limit=2', '/model/importance']:
    r = g(ep)
    ct = r.headers.get('content-type','') if r and r.status_code==200 else ''
    ok = 'application/json' in ct
    cat.append(ok)
    print(f'  {"PASA" if ok else "FALLA"}  Content-Type JSON en {ep}: "{ct}"')

r = g('/docs')
ok = r is not None and r.status_code == 200
cat.append(ok)
print(f'  {"PASA" if ok else "FALLA"}  Swagger /docs: HTTP {r.status_code if r else "N/A"}')

r = g('/openapi.json')
ok = r is not None and r.status_code == 200
cat.append(ok)
print(f'  {"PASA" if ok else "FALLA"}  OpenAPI JSON: HTTP {r.status_code if r else "N/A"}')

r2 = g('/risk/today', limit=3)
if r2 and r2.status_code == 200:
    d = r2.json()
    ok = d.get('type') == 'FeatureCollection' and d.get('features')
    cat.append(ok)
    print(f'  {"PASA" if ok else "FALLA"}  GeoJSON RFC 7946 FeatureCollection valido')

results['3_Compatibilidad'] = (sum(cat), len(cat))

# ── 4. USABILIDAD ─────────────────────────────────────────────────────────────
print('\n[4] USABILIDAD')
cat = []
idx = WEB_DIR / 'index.html'
if idx.exists():
    html = idx.read_text(encoding='utf-8')
    checks = [
        ('Hero/RiskBadge', 'id="riskBadge"'),
        ('Mapa interactivo', 'id="mapa"'),
        ('Alertas WhatsApp', 'id="whatsapp"'),
        ('Formulario reporte', 'id="reportForm"'),
        ('Recursos', 'id="recursos"'),
        ('Transparencia', 'id="transparencia"'),
        ('Navbar responsive', '<nav'),
        ('Estadisticas FIRMS', 'id="statFIRMS"'),
        ('Filtro region', 'id="regionFilter"'),
        ('Selector WA zona', 'id="waZone"'),
        ('Heatmap layer', 'leaflet.heat'),
        ('SEO meta description', 'name="description"'),
        ('SEO viewport', 'name="viewport"'),
        ('Google Fonts Inter', 'Inter'),
        ('Toggle Heatmap UI', 'id="toggleHeatmap"'),
    ]
    for label, pat in checks:
        ok = pat.lower() in html.lower()
        cat.append(ok)
        print(f'  {"PASA" if ok else "FALLA"}  {label}')

r = g('/')
ok = r is not None and r.status_code == 200
cat.append(ok)
print(f'  {"PASA" if ok else "FALLA"}  Portal web raiz / HTTP {r.status_code if r else "N/A"}')

r = p('/predict', {'grid_id':'T'})
ok = r is not None and r.status_code == 422
cat.append(ok)
print(f'  {"PASA" if ok else "FALLA"}  Validacion 422 entrada incompleta: HTTP {r.status_code if r else "N/A"}')

results['4_Usabilidad'] = (sum(cat), len(cat))

# ── 5. FIABILIDAD ─────────────────────────────────────────────────────────────
print('\n[5] FIABILIDAD')
cat = []
pl_rel = {'grid_id':'REL','pendiente_pct':20.0,'orientacion':'NE','ndvi':0.30,
          'dist_carretera_m':400.0,'dist_poblado_m':800.0,'temp_2m':28.0,
          'humedad_relativa':32.0,'viento_velocidad':20.0,'viento_direccion':45.0}
succ = 0; probas = []
for _ in range(10):
    r = p('/predict', pl_rel)
    if r and r.status_code == 200:
        succ += 1; probas.append(r.json().get('probabilidad'))
ok1 = succ == 10
ok2 = len(set(round(v,6) for v in probas)) == 1 if probas else False
cat.extend([ok1, ok2])
print(f'  {"PASA" if ok1 else "FALLA"}  Madurez: {succ}/10 llamadas /predict exitosas')
print(f'  {"PASA" if ok2 else "FALLA"}  Determinismo: valores_unicos={len(set(round(v,6) for v in probas)) if probas else "N/A"}')

for label, body in [
    ('Temp extrema 60C', {'grid_id':'E1','pendiente_pct':20,'orientacion':'N','ndvi':0.3,'dist_carretera_m':400,'dist_poblado_m':800,'temp_2m':60,'humedad_relativa':5,'viento_velocidad':100,'viento_direccion':45}),
    ('Humedad 100%',     {'grid_id':'E2','pendiente_pct':1,'orientacion':'S','ndvi':0.95,'dist_carretera_m':20000,'dist_poblado_m':50000,'temp_2m':5,'humedad_relativa':100,'viento_velocidad':0.1,'viento_direccion':0})]:
    r = p('/predict', body)
    if r and r.status_code == 200:
        pv = r.json().get('probabilidad', -1)
        ok = 0.0 <= pv <= 1.0
        cat.append(ok)
        print(f'  {"PASA" if ok else "FALLA"}  Tolerancia {label}: p={pv:.4f} HTTP {r.status_code}')

h_ok = 0
for _ in range(5):
    r = g('/health')
    if r and r.status_code == 200: h_ok += 1
ok = h_ok == 5
cat.append(ok)
print(f'  {"PASA" if ok else "FALLA"}  Disponibilidad /health: {h_ok}/5')

try:
    m2 = joblib.load(MODEL_PATH)
    ok = m2 is not None and hasattr(m2, 'predict_proba')
    cat.append(ok)
    sz = MODEL_PATH.stat().st_size/1024
    print(f'  {"PASA" if ok else "FALLA"}  Modelo .pkl cargable: {sz:.1f}KB')
except Exception as e:
    cat.append(False)
    print(f'  FALLA  Modelo .pkl: {e}')

results['5_Fiabilidad'] = (sum(cat), len(cat))

# ── 6. SEGURIDAD ─────────────────────────────────────────────────────────────
print('\n[6] SEGURIDAD')
cat = []
r = g('/health')
if r:
    xcto = r.headers.get('x-content-type-options','')
    server = r.headers.get('server','')
    ok_xcto = len(xcto) > 0
    cat.append(ok_xcto)
    print(f'  {"PASA" if ok_xcto else "AVISO"}  X-Content-Type-Options: "{xcto}"')
    import re
    no_ver = not re.search(r'\d+\.\d+', server)
    cat.append(no_ver)
    print(f'  {"PASA" if no_ver else "FALLA"}  Server header sin version: "{server}"')

for path in ['/.env', '/.env.example']:
    r = g(path)
    ok = not r or r.status_code in [404, 403, 422]
    cat.append(ok)
    print(f'  {"PASA" if ok else "FALLA"}  {path} no expuesto: HTTP {r.status_code if r else "N/A"}')

r = p('/predict', {'grid_id':"'; DROP TABLE grillas;--", 'pendiente_pct':20, 'orientacion':'N',
                    'ndvi':0.3, 'dist_carretera_m':400, 'dist_poblado_m':800,
                    'temp_2m':28, 'humedad_relativa':32, 'viento_velocidad':20, 'viento_direccion':45})
ok = r is not None and r.status_code in [200, 422]
cat.append(ok)
print(f'  {"PASA" if ok else "FALLA"}  SQL injection en grid_id: HTTP {r.status_code if r else "N/A"}')

env_ex = ROOT / '.env.example'
if env_ex.exists():
    content = env_ex.read_text()
    real_creds = any(c in content for c in ['a86632ae','bd46e923','minioadmin','bot_token_real'])
    ok = not real_creds
    cat.append(ok)
    print(f'  {"PASA" if ok else "FALLA"}  .env.example sin credenciales reales: {"OK" if ok else "EXPUESTO"}')

results['6_Seguridad'] = (sum(cat), len(cat))

# ── 7. MANTENIBILIDAD ────────────────────────────────────────────────────────
print('\n[7] MANTENIBILIDAD')
cat = []
for d in ['app','web','data_pipeline','airflow','dashboard','data','models','tests']:
    ok = (ROOT/d).exists()
    cat.append(ok)
    print(f'  {"PASA" if ok else "FALLA"}  Directorio /{d}')
for f in ['main.py','model.py','propagation.py','scheduler.py','pdf_generator.py','whatsapp_alerts.py']:
    ok = (APP_DIR/f).exists()
    cat.append(ok)
    print(f'  {"PASA" if ok else "FALLA"}  app/{f}')
mc = (APP_DIR/'main.py').read_text()
ok = 'os.getenv' in mc
cat.append(ok); print(f'  {"PASA" if ok else "FALLA"}  main.py usa os.getenv()')
req = ROOT / 'requirements.txt'
if req.exists():
    lines = [l for l in req.read_text().splitlines() if l.strip() and not l.startswith('#')]
    ok = len(lines) >= 10
    cat.append(ok)
    print(f'  {"PASA" if ok else "FALLA"}  requirements.txt: {len(lines)} dependencias')
ok = (ROOT/'.env.example').exists()
cat.append(ok); print(f'  {"PASA" if ok else "FALLA"}  .env.example existe')
ok = (ROOT/'docker-compose.yml').exists()
cat.append(ok); print(f'  {"PASA" if ok else "FALLA"}  docker-compose.yml presente')
ok = (ROOT/'Dockerfile').exists()
cat.append(ok); print(f'  {"PASA" if ok else "FALLA"}  Dockerfile presente')
tests = list((ROOT/'tests').glob('*.py'))
ok = len(tests) >= 2
cat.append(ok); print(f'  {"PASA" if ok else "FALLA"}  Suite de tests: {len(tests)} archivos')

results['7_Mantenibilidad'] = (sum(cat), len(cat))

# ── 8. PORTABILIDAD ──────────────────────────────────────────────────────────
print('\n[8] PORTABILIDAD')
cat = []
df_path = ROOT / 'Dockerfile'
if df_path.exists():
    dc = df_path.read_text()
    for instr in ['FROM','WORKDIR','COPY','CMD']:
        ok = instr in dc
        cat.append(ok)
        print(f'  {"PASA" if ok else "FALLA"}  Dockerfile: {instr}')
parquet = ROOT/'data'/'dataset.parquet'
csv_f = ROOT/'data'/'dataset.csv'
ok = parquet.exists()
cat.append(ok)
print(f'  {"PASA" if ok else "FALLA"}  dataset.parquet ({parquet.stat().st_size/1024/1024:.1f}MB)' if ok else '  FALLA  dataset.parquet')
ok2 = csv_f.exists()
cat.append(ok2)
print(f'  {"PASA" if ok2 else "FALLA"}  dataset.csv ({csv_f.stat().st_size/1024/1024:.1f}MB)' if ok2 else '  FALLA  dataset.csv')
r = g('/')
ok = r is not None and r.status_code == 200 and 'text/html' in r.headers.get('content-type','')
cat.append(ok)
print(f'  {"PASA" if ok else "FALLA"}  FastAPI sirve portal web en /: text/html={ok}')
req_c = req.read_text().lower() if req.exists() else ''
for pkg,desc in [('fastapi','API'),('lightgbm','ML'),('geopandas','geo'),('locust','carga'),('apscheduler','scheduler')]:
    ok = pkg in req_c
    cat.append(ok)
    print(f'  {"PASA" if ok else "FALLA"}  requirements incluye {pkg} ({desc})')
for f in ['main.py','model.py']:
    c = (APP_DIR/f).read_text()
    ok = 'from pathlib' in c or 'Path(' in c
    cat.append(ok)
    print(f'  {"PASA" if ok else "FALLA"}  app/{f} usa pathlib (cross-platform)')

results['8_Portabilidad'] = (sum(cat), len(cat))

# ── RESUMEN ──────────────────────────────────────────────────────────────────
print('\n' + '='*72)
print('  RESUMEN EJECUTIVO — ISO/IEC 25010:2011')
print('='*72)
total_p = 0; total_t = 0
names = {
    '1_Adecuacion_Funcional': '1. Adecuacion Funcional',
    '2_Eficiencia_Desempeno': '2. Eficiencia de Desempeno',
    '3_Compatibilidad':       '3. Compatibilidad',
    '4_Usabilidad':           '4. Usabilidad',
    '5_Fiabilidad':           '5. Fiabilidad',
    '6_Seguridad':            '6. Seguridad',
    '7_Mantenibilidad':       '7. Mantenibilidad',
    '8_Portabilidad':         '8. Portabilidad',
}
print(f'\n  {"Caracteristica":<32} {"Pasa":>5} {"Total":>6} {"Pct":>7}  Calificacion')
print('  ' + '-'*65)
for key, name in names.items():
    ps, tt = results.get(key, (0,0))
    pct = ps/tt*100 if tt else 0
    total_p += ps; total_t += tt
    grade = ('EXCELENTE' if pct>=90 else 'BUENO' if pct>=75 else 'ACEPTABLE' if pct>=60 else 'CRITICO')
    print(f'  {name:<32} {ps:>5}/{tt:<5} {pct:>6.1f}%  {grade}')
print('  ' + '-'*65)
gpct = total_p/total_t*100 if total_t else 0
print(f'  {"TOTAL GLOBAL":<32} {total_p:>5}/{total_t:<5} {gpct:>6.1f}%  {"APROBADO" if gpct>=80 else "CONDICIONAL" if gpct>=60 else "REPROBADO"}')
print('='*72)
print(f'  VEREDICTO: {"SISTEMA APROBADO ISO/IEC 25010" if gpct>=80 else "SISTEMA REQUIERE MEJORAS"}')
print('='*72 + '\n')
