from pathlib import Path
from datetime import datetime

root = Path('.')
output_file = root / 'CODIGO_COMPLETO_SISTEMA.txt'

files_to_include = [
    # 1. Configuración & Entorno
    ('CONFIGURACIÓN DEL PROYECTO', [
        'requirements.txt',
        '.env.example',
        'Dockerfile',
        'docker-compose.yml',
        '.gitignore',
    ]),
    # 2. Documentación
    ('DOCUMENTACIÓN DEL PROYECTO', [
        'README.md',
        'docs/Memoria_Tecnica_Capstone.md',
    ]),
    # 2b. Lanzadores / Utilidades de arranque
    ('LANZADORES / UTILIDADES DE ARRANQUE (.bat)', [
        'INICIAR_SERVIDOR_7AM.bat',
        'ENVIAR_ALERTAS_AHORA.bat',
    ]),
    # 3. Pipeline de Datos y Machine Learning
    ('PIPELINE DE DATOS Y MACHINE LEARNING (data_pipeline/)', [
        'data_pipeline/grid_builder.py',
        'data_pipeline/real_features.py',
        'data_pipeline/train_model.py',
        'data_pipeline/fetch_firms.py',
        'data_pipeline/fetch_era5.py',
    ]),
    # 3b. Modelo entrenado y metadatos
    ('MODELO ENTRENADO Y METADATOS (models/)', [
        'models/model_metadata.json',
    ]),
    # 4. Backend FastAPI & Alertas
    ('BACKEND API FASTAPI Y PROGRAMADOR (app/)', [
        'app/main.py',
        'app/model.py',
        'app/scheduler.py',
        'app/propagation.py',
        'app/pdf_generator.py',
        'app/whatsapp_alerts.py',
    ]),
    # 5. Dashboard Operativo
    ('DASHBOARD OPERATIVO STREAMLIT (dashboard/)', [
        'dashboard/app.py',
    ]),
    # 6. Frontend Web Ciudadano
    ('PORTAL WEB CIUDADANO (web/)', [
        'web/index.html',
        'web/app.js',
        'web/styles.css',
    ]),
    # 7. Orquestación Airflow
    ('ORQUESTACIÓN AIRFLOW (airflow/)', [
        'airflow/dags/pipeline_dag.py',
    ]),
    # 8. Notebooks y Análisis
    ('NOTEBOOKS Y ANÁLISIS (notebooks/)', [
        'notebooks/model_evaluation.py',
    ]),
    # 9. Scripts de Utilidad y Diagnóstico
    ('SCRIPTS DE UTILIDAD Y DIAGNÓSTICO (scripts/)', [
        'scripts/enviar_alertas_ahora.py',
        'scripts/generar_documento_codigo.py',
        'scripts/health_check.py',
        'scripts/test_alertas_diarias.py',
        'scripts/listar_grupos_alerta.py',
    ]),
    # 10. Pruebas y Auditoría de Calidad
    ('PRUEBAS Y AUDITORÍA (tests/)', [
        'tests/test_lightgbm_precision.py',
        'tests/audit_quick.py',
        'tests/audit_final.py',
        'tests/iso25010_audit.py',
        'tests/check_structure.py',
        'tests/locustfile.py',
    ]),
]

with open(output_file, 'w', encoding='utf-8') as out:
    out.write('=' * 90 + '\n')
    out.write('SISTEMA NACIONAL DE ALERTA TEMPRANA DE INCENDIOS FORESTALES\n')
    out.write('COMPILACIÓN COMPLETA DEL CÓDIGO FUENTE DEL SISTEMA\n')
    out.write(f'Fecha de generación: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
    out.write('=' * 90 + '\n\n')

    out.write('ÍNDICE DE CONTENIDOS:\n')
    idx = 1
    for section_name, flist in files_to_include:
        out.write(f'\n  [{section_name}]\n')
        for f in flist:
            p = root / f
            status = f'({p.stat().st_size:,} bytes)' if p.exists() else '(NO ENCONTRADO)'
            out.write(f'    {idx:02d}. {f} {status}\n')
            idx += 1
    out.write('\n' + '=' * 90 + '\n\n')

    file_num = 1
    for section_name, flist in files_to_include:
        out.write('\n' + '#' * 90 + '\n')
        out.write(f'### SECCIÓN: {section_name}\n')
        out.write('#' * 90 + '\n\n')

        for f in flist:
            p = root / f
            out.write('=' * 90 + '\n')
            out.write(f'ARCHIVO [{file_num:02d}]: {f}\n')
            out.write('=' * 90 + '\n')
            if p.exists():
                try:
                    content = p.read_text(encoding='utf-8', errors='replace')
                    out.write(content)
                    if not content.endswith('\n'):
                        out.write('\n')
                except Exception as e:
                    out.write(f'// Error al leer archivo: {e}\n')
            else:
                out.write('// Archivo no existe en el repositorio.\n')
            out.write('\n\n')
            file_num += 1

print(f'Done! File size: {output_file.stat().st_size:,} bytes')
