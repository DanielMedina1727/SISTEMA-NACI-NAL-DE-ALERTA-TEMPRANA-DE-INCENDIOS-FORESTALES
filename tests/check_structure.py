from pathlib import Path
ROOT = Path('.')
APP = ROOT / 'app'
dirs = [d for d in ['app','web','data_pipeline','airflow','dashboard','data','models','tests'] if (ROOT/d).exists()]
files = [f for f in ['main.py','model.py','propagation.py','scheduler.py','pdf_generator.py','whatsapp_alerts.py'] if (APP/f).exists()]
req = ROOT / 'requirements.txt'
lines = [l for l in req.read_text(encoding='utf-8').splitlines() if l.strip() and not l.startswith('#')] if req.exists() else []
env_c = (ROOT/'.env.example').read_text(encoding='utf-8')
creds_exposed = any(k in env_c for k in ['a86632ae','bd46e923','minioadmin'])
mc = (APP/'main.py').read_text(encoding='utf-8')
key_in_code = 'a86632ae' in mc
pq = ROOT/'data'/'dataset.parquet'
cv = ROOT/'data'/'dataset.csv'
df_path = ROOT/'Dockerfile'
dc = df_path.read_text(encoding='utf-8') if df_path.exists() else ''
tests = list((ROOT/'tests').glob('*.py'))
req_c = req.read_text(encoding='utf-8').lower() if req.exists() else ''
print(f"DIRS: {len(dirs)}/8 => {dirs}")
print(f"APP_FILES: {len(files)}/6 => {files}")
print(f"REQUIREMENTS: {len(lines)} deps")
print(f"ENV_CREDS_EXPOSED: {creds_exposed}")
print(f"KEY_IN_CODE: {key_in_code}")
print(f"PARQUET_MB: {pq.stat().st_size//1024//1024}")
print(f"CSV_MB: {cv.stat().st_size//1024//1024}")
df_instrs = [i for i in ['FROM','WORKDIR','COPY','CMD'] if i in dc]
print(f"DOCKERFILE_INSTRS: {df_instrs}")
print(f"TESTS_COUNT: {len(tests)}")
print(f"DOCKER_COMPOSE: {(ROOT/'docker-compose.yml').exists()}")
print(f"FASTAPI_IN_REQ: {'fastapi' in req_c}")
print(f"LIGHTGBM_IN_REQ: {'lightgbm' in req_c}")
print(f"GEOPANDAS_IN_REQ: {'geopandas' in req_c}")
print(f"APSCHEDULER_IN_REQ: {'apscheduler' in req_c}")
for f in ['main.py','model.py','propagation.py']:
    c = (APP/f).read_text(encoding='utf-8')
    has_doc = '"""' in c
    has_pathlib = 'Path(' in c or 'from pathlib' in c
    has_env = 'os.getenv' in c
    print(f"  {f}: docstring={has_doc} pathlib={has_pathlib} getenv={has_env}")
