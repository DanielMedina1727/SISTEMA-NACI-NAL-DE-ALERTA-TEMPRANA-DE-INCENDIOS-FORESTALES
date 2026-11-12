"""Genera una compilación .txt de todo el código fuente del sistema.

Uso:
    python scripts/generar_documento_codigo.py

El archivo resultante se escribe en la raíz del proyecto como
``CODIGO_COMPLETO_SISTEMA.txt``. No incluye credenciales, datasets, modelos
binarios, documentos binarios ni cachés.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "CODIGO_COMPLETO_SISTEMA.txt"

SECTIONS: list[tuple[str, list[str]]] = [
    (
        "CONFIGURACIÓN DEL PROYECTO",
        [
            "requirements.txt",
            "requirements-dev.txt",
            "pyproject.toml",
            ".env.example",
            "Dockerfile",
            "docker-compose.yml",
            ".github/workflows/ci.yml",
            ".gitignore",
        ],
    ),
    (
        "DOCUMENTACIÓN DEL PROYECTO",
        [
            "README.md",
            "docs/Memoria_Tecnica_Capstone.md",
            "docs/Historias_de_Usuario.md",
            "docs/Historias_de_Usuario.csv",
        ],
    ),
    (
        "LANZADORES / UTILIDADES DE ARRANQUE (.bat)",
        [
            "INICIAR_SERVIDOR_7AM.bat",
            "ENVIAR_ALERTAS_AHORA.bat",
        ],
    ),
    (
        "PIPELINE DE DATOS Y MACHINE LEARNING (data_pipeline/)",
        [
            "data_pipeline/grid_builder.py",
            "data_pipeline/real_features.py",
            "data_pipeline/refresh_dataset.py",
            "data_pipeline/train_model.py",
            "data_pipeline/fetch_firms.py",
            "data_pipeline/fetch_era5.py",
        ],
    ),
    (
        "MODELO ENTRENADO Y METADATOS (models/)",
        [
            "models/model_metadata.json",
        ],
    ),
    (
        "BACKEND API FASTAPI Y PROGRAMADOR (app/)",
        [
            "app/main.py",
            "app/model.py",
            "app/security.py",
            "app/scheduler.py",
            "app/propagation.py",
            "app/pdf_generator.py",
            "app/whatsapp_alerts.py",
            "app/zones.py",
        ],
    ),
    (
        "DASHBOARD OPERATIVO STREAMLIT (dashboard/)",
        [
            "dashboard/app.py",
        ],
    ),
    (
        "PORTAL WEB CIUDADANO (web/)",
        [
            "web/index.html",
            "web/app.js",
            "web/styles.css",
        ],
    ),
    (
        "ORQUESTACIÓN AIRFLOW (airflow/)",
        [
            "airflow/dags/pipeline_dag.py",
        ],
    ),
    (
        "NOTEBOOKS Y ANÁLISIS (notebooks/)",
        [
            "notebooks/model_evaluation.py",
        ],
    ),
    (
        "SCRIPTS DE UTILIDAD, DIAGNÓSTICO E INFORMES (scripts/)",
        [
            "scripts/build_informe.py",
            "scripts/enviar_alertas_ahora.py",
            "scripts/final_checks.py",
            "scripts/generar_documento_codigo.py",
            "scripts/health_check.py",
            "scripts/informe_blocks.py",
            "scripts/informe_blocks2.py",
            "scripts/informe_blocks3.py",
            "scripts/listar_grupos_alerta.py",
            "scripts/postprocess_informe.py",
            "scripts/test_alertas_diarias.py",
        ],
    ),
    (
        "PRUEBAS Y AUDITORÍA (tests/)",
        [
            "tests/conftest.py",
            "tests/test_model.py",
            "tests/test_api.py",
            "tests/test_security.py",
            "tests/test_pipeline.py",
            "tests/test_lightgbm_precision.py",
            "tests/test_whatsapp_multi.py",
            "tests/audit_quick.py",
            "tests/audit_final.py",
            "tests/iso25010_audit.py",
            "tests/check_structure.py",
            "tests/locustfile.py",
        ],
    ),
]

EXCLUDED_NOTE = """\
Archivos excluidos deliberadamente:
  - .env (credenciales reales; solo se incluye .env.example con placeholders)
  - data/ (dataset, caché y reportes ciudadanos)
  - models/*.pkl, models/*.npz (modelos binarios)
  - docs/*.docx, docs/*.pdf (documentos binarios)
  - venv/, .git/, __pycache__/, .pytest_cache/, .ruff_cache/
"""


def _read_entry(relative_path: str) -> tuple[str, str | None, int, int]:
    path = ROOT / relative_path
    if not path.exists():
        return relative_path, None, 0, 0
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return relative_path, f"// Error al leer el archivo: {exc}\n", 0, 1
    lines = content.count("\n") + (0 if not content or content.endswith("\n") else 1)
    return relative_path, content, len(content.encode("utf-8")), lines


def main() -> None:
    records: list[tuple[str, str, str | None, int, int]] = []
    for section, files in SECTIONS:
        for relative_path in files:
            rel, content, size, lines = _read_entry(relative_path)
            records.append((section, rel, content, size, lines))

    total_files = len(records)
    total_lines = sum(record[4] for record in records)
    total_bytes = sum(record[3] for record in records)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines_out: list[str] = []
    lines_out.append("=" * 90)
    lines_out.append("SISTEMA NACIONAL DE ALERTA TEMPRANA DE INCENDIOS FORESTALES")
    lines_out.append("COMPILACIÓN COMPLETA DEL CÓDIGO FUENTE DEL SISTEMA")
    lines_out.append(f"Fecha de generación: {generated_at}")
    lines_out.append(f"Archivos incluidos: {total_files} | Líneas: {total_lines:,} | Bytes: {total_bytes:,}")
    lines_out.append("=" * 90)
    lines_out.append("")
    lines_out.append(EXCLUDED_NOTE)
    lines_out.append("")
    lines_out.append("ÍNDICE DE CONTENIDOS:")
    lines_out.append("")

    index = 1
    current_section = None
    for section, rel, _content, size, line_count in records:
        if section != current_section:
            lines_out.append(f"  [{section}]")
            current_section = section
        if _content is None:
            status = "(NO ENCONTRADO)"
        else:
            status = f"({size:,} bytes, {line_count:,} líneas)"
        lines_out.append(f"    {index:02d}. {rel} {status}")
        index += 1

    lines_out.append("")
    lines_out.append("=" * 90)
    lines_out.append("")

    file_number = 1
    current_section = None
    for section, rel, content, _size, _line_count in records:
        if section != current_section:
            lines_out.append("")
            lines_out.append("#" * 90)
            lines_out.append(f"### SECCIÓN: {section}")
            lines_out.append("#" * 90)
            lines_out.append("")
            current_section = section

        lines_out.append("=" * 90)
        lines_out.append(f"ARCHIVO [{file_number:02d}]: {rel}")
        lines_out.append("=" * 90)
        if content is None:
            lines_out.append("// Archivo no existe en el repositorio.")
        else:
            lines_out.append(content.rstrip("\n"))
        lines_out.append("")
        lines_out.append("")
        file_number += 1

    OUTPUT.write_text("\n".join(lines_out) + "\n", encoding="utf-8")
    print(f"Generado: {OUTPUT}")
    print(f"Archivos: {total_files} | Líneas: {total_lines:,} | Bytes: {total_bytes:,}")


if __name__ == "__main__":
    main()
