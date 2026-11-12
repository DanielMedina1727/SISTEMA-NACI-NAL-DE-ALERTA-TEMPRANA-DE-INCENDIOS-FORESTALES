# -*- coding: utf-8 -*-
"""Comprobaciones finales del informe y del PDF entregables."""
from __future__ import annotations

import re
import unicodedata
import zipfile
from pathlib import Path

import pymupdf
from docx import Document
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parent.parent
DOCX = ROOT / "docs" / "Informe_Proyecto_Final_2026-2_COMPLETADO.docx"
PDF = ROOT / "docs" / "Informe_Proyecto_Final_2026-2_COMPLETADO.pdf"


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", text).strip().lower()


def main() -> None:
    doc = Document(DOCX)
    z = zipfile.ZipFile(DOCX)
    comments = "word/comments.xml" in z.namelist()
    update_fields = doc.settings.element.find(qn("w:updateFields")) is not None

    pars = doc.paragraphs
    start = next(i for i, p in enumerate(pars) if p.text.strip().upper().startswith("REFERENCIAS"))
    end = next(i for i, p in enumerate(pars) if i > start and p.text.strip().upper().startswith("ANEXOS"))
    refs = [p.text.strip() for p in pars[start + 1 : end] if p.text.strip()]
    hanging = sum(
        1
        for p in pars[start + 1 : end]
        if p.paragraph_format.first_line_indent is not None
        and p.paragraph_format.first_line_indent.cm < 0
    )
    duplicate_keys = len(refs) - len({norm(r) for r in refs})

    all_text = "\n".join(p.text for p in pars)
    telegram = all_text.count("Telegram")
    smote = [p.text for p in pars if "SMOTE" in p.text.upper()]

    pdf = pymupdf.open(PDF)
    pages = pdf.page_count
    blank = [i + 1 for i in range(pages) if len(pdf[i].get_text().strip()) < 100]

    targets = {
        "Resumen": "I. RESUMEN",
        "Introducción": "II. INTRODUCCI",
        "Análisis": "III. AN",
        "Herramientas": "IV. HERRAMIENTAS",
        "Generación": "V. GENERACI",
        "Metodología": "VI. METODOLOG",
        "Resultados": "VII. RESULTADOS",
        "Recomendaciones": "VIII. RECOMENDACIONES",
        "Compromiso": "IX. COMPROMISO",
        "Referencias": "X. REFERENCIAS",
        "Anexos": "XI. ANEXOS",
        "Anexo 03": "11.3. Anexo 03",
        "Anexo 10": "11.10. Anexo 10",
    }
    actual: dict[str, list[int]] = {}
    for label, needle in targets.items():
        actual[label] = [i + 1 for i in range(pages) if pdf[i].search_for(needle)]

    print("=== DOCX ===")
    print(f"Párrafos: {len(pars)}; tablas de nivel superior: {len(doc.tables)}")
    print(f"Comentarios: {comments}; updateFields: {update_fields}")
    print(f"Referencias: {len(refs)}; con sangría colgante: {hanging}; duplicados: {duplicate_keys}")
    print(f"Primera referencia: {refs[0][:90]}")
    print(f"Última referencia: {refs[-1][:90]}")
    print(f"Telegram en el cuerpo: {telegram}")
    print(f"Menciones de SMOTE: {len(smote)}")
    for line in smote:
        print(f"  - {line[:220]}")
    print(f"Anexo 01 con enlace de video: {'Enlace del video' in all_text}")
    print(f"Anexo 02 con GitHub real: {'github.com/DanielMedina1727' in all_text}")
    print()
    print("=== PDF ===")
    print(f"Páginas: {pages}; páginas casi vacías: {blank}")
    for label, found in actual.items():
        print(f"{label}: {found}")
    print()
    print("=== TOC (página 2, texto) ===")
    print(pdf[1].get_text()[:2500])


if __name__ == "__main__":
    main()
