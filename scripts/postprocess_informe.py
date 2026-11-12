# -*- coding: utf-8 -*-
"""Reaplica propiedades de tabla que Word elimina al actualizar el TOC.

Word tiende a reconstruir algunas tablas (en especial la de hardware, que está
dentro de un SDT) y pierde ``w:tblHeader`` y ``w:cantSplit``. Este script se
ejecuta después de actualizar el índice y antes de exportar el PDF.
"""
from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.table import Table

ROOT = Path(__file__).resolve().parent.parent
DOCX = ROOT / "docs" / "Informe_Proyecto_Final_2026-2_COMPLETADO.docx"


def repeat_header(table: Table) -> None:
    tr_pr = table.rows[0]._tr.get_or_add_trPr()
    if tr_pr.find(qn("w:tblHeader")) is not None:
        return
    header = OxmlElement("w:tblHeader")
    header.set(qn("w:val"), "true")
    tr_pr.append(header)


def keep_rows_together(table: Table) -> None:
    for row in table.rows:
        tr_pr = row._tr.get_or_add_trPr()
        if tr_pr.find(qn("w:cantSplit")) is None:
            cant_split = OxmlElement("w:cantSplit")
            cant_split.set(qn("w:val"), "true")
            tr_pr.append(cant_split)


def main() -> None:
    doc = Document(DOCX)

    # El TOC ya quedó actualizado y guardado; no conviene que Word lo vuelva
    # a actualizar al abrir el archivo, porque al hacerlo reconstruye algunas
    # tablas y pierde la repetición de encabezados.
    settings = doc.settings.element
    for update in settings.findall(qn("w:updateFields")):
        settings.remove(update)

    # Abreviar dos etiquetas de la tabla de hardware para que no se partan
    # a mitad de palabra en columnas estrechas.
    replacements = {
        "2 vCPU, 4 GB RAM, 20 GB almacenamiento": "2 vCPU, 4 GB RAM, 20 GB de disco",
        "Almacenamiento de respaldo": "Disco de respaldo",
        "Plataforma de automatización": "Plataforma ETL",
        "Documentación de API": "Documentación",
    }

    total = 0
    hardware = 0
    for tbl in doc.element.body.iter(qn("w:tbl")):
        table = Table(tbl, doc._body)
        if len(table.rows) < 2:
            continue
        for row in table.rows:
            for cell in row.cells:
                for par in cell.paragraphs:
                    for run in par.runs:
                        for old, new in replacements.items():
                            if old in run.text:
                                run.text = run.text.replace(old, new)
        repeat_header(table)
        total += 1
        if len(table.columns) == 5 and table.rows[0].cells[0].text.strip() == "Recurso":
            keep_rows_together(table)
            hardware += 1

    # Mantener el bloque de firmas de la carta de presentación en una sola página.
    for par in doc.paragraphs:
        if par.text.strip().lower() == "atentamente,":
            par.paragraph_format.page_break_before = True
            break

    doc.save(DOCX)
    print(f"Tablas con encabezado repetido: {total}; tablas de hardware ajustadas: {hardware}")


if __name__ == "__main__":
    main()
