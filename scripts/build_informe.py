# -*- coding: utf-8 -*-
"""Genera la versión completada del informe CAPSTONE.

Uso:
    python scripts/build_informe.py

Requiere el documento plantilla en la ruta SRC y python-docx.
"""
from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from docx.table import Table
from docx.text.paragraph import Paragraph

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from informe_blocks import get_blocks  # noqa: E402
from informe_blocks2 import get_blocks2  # noqa: E402
from informe_blocks3 import NEW_REFERENCES, get_annexes  # noqa: E402

SRC = Path(r"C:\Users\Administrator\Downloads\2026-2_ISC-Informe_Proyecto Final_CAPST (1).docx")
OUT = ROOT / "docs" / "Informe_Proyecto_Final_2026-2_COMPLETADO.docx"
DOC_OBJ = None


# ----------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------
def set_text(par: Paragraph, text: str) -> Paragraph:
    # Elimina runs, hipervínculos, marcadores y cualquier otro contenido,
    # conservando únicamente las propiedades del párrafo (w:pPr).
    for child in list(par._p):
        if child.tag != qn("w:pPr"):
            par._p.remove(child)
    par.add_run(text)
    return par


def make_paragraph_after(cursor, text: str = "", style: str | None = None) -> Paragraph:
    p = OxmlElement("w:p")
    cursor.addnext(p)
    par = Paragraph(p, DOC_OBJ._body)
    if style:
        par.style = style
    if text:
        par.add_run(text)
    return par


def shade_cell(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def set_table_width(table, pct: int = 5000) -> None:
    tbl_pr = table._tbl.tblPr
    tbl_w = tbl_pr.find(qn("w:tblW"))
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.append(tbl_w)
    tbl_w.set(qn("w:type"), "pct")
    tbl_w.set(qn("w:w"), str(pct))


def repeat_header(table) -> None:
    tr_pr = table.rows[0]._tr.get_or_add_trPr()
    if tr_pr.find(qn("w:tblHeader")) is not None:
        return
    header = OxmlElement("w:tblHeader")
    header.set(qn("w:val"), "true")
    tr_pr.append(header)


def keep_rows_together(table) -> None:
    for row in table.rows:
        tr_pr = row._tr.get_or_add_trPr()
        if tr_pr.find(qn("w:cantSplit")) is None:
            cant_split = OxmlElement("w:cantSplit")
            cant_split.set(qn("w:val"), "true")
            tr_pr.append(cant_split)


def set_table_font_size(table, size: float) -> None:
    for row in table.rows:
        for cell in row.cells:
            for par in cell.paragraphs:
                for run in par.runs:
                    run.font.size = Pt(size)


def get_widths(header: list[str]):
    h = [c.strip() for c in header]
    if h[:2] == ["ID", "Fecha"]:
        return [1.2, 1.3, 1.5, 3.6, 1.6, 3.2, 1.6, 1.6]
    if h[:2] == ["N.º", "Ítem"]:
        return [1.0, 7.0, 1.2, 1.2, 1.2, 1.2, 1.2]
    if h[:2] == ["N.º", "Indicador"]:
        return [1.0, 3.8, 1.8, 3.0, 4.5]
    if len(h) == 2 and h == ["Categoría", "Requisito"]:
        return [4.0, 11.5]
    if len(h) == 3 and h == ["Categoría", "Requisito", "Valor o detalle"]:
        return [3.5, 4.0, 8.0]
    if len(h) == 4 and h[:2] == ["Criterio", "Descriptor"]:
        return [2.5, 6.0, 2.5, 5.0]
    if len(h) == 6 and h[:2] == ["Criterio", "E1"]:
        return [3.0, 1.5, 1.5, 1.5, 3.0, 4.0]
    if len(h) == 6 and h[:2] == ["Código", "Causa"]:
        return [1.5, 6.5, 2.0, 2.0, 2.0, 1.5]
    if len(h) == 4 and h[:2] == ["Fase", "Entregable"]:
        return [2.3, 6.1, 5.5, 2.0]
    if len(h) == 4 and h[:2] == ["Código", "Especialidad"]:
        return [1.5, 5.0, 2.0, 6.5]
    if len(h) == 5 and h[:2] == ["Versión", "Fecha"]:
        return [1.5, 1.5, 5.0, 5.0, 2.5]
    if len(h) == 8 and h[0] == "Nombre":
        return [2.1, 1.9, 1.8, 2.2, 2.1, 2.1, 1.7, 1.4]
    return None


def apply_widths(table, widths) -> None:
    if not widths:
        return
    table.autofit = False
    tbl_pr = table._tbl.tblPr
    if tbl_pr.find(qn("w:tblLayout")) is None:
        layout = OxmlElement("w:tblLayout")
        layout.set(qn("w:type"), "fixed")
        tbl_pr.append(layout)
    # Ajustar el ancho total de la tabla en twips (1 cm ≈ 567 twips)
    tbl_w = tbl_pr.find(qn("w:tblW"))
    if tbl_w is not None:
        tbl_w.set(qn("w:type"), "dxa")
        tbl_w.set(qn("w:w"), str(int(round(sum(widths) * 567))))
    for j, width in enumerate(widths):
        if j >= len(table.columns):
            break
        table.columns[j].width = Cm(width)
        for row in table.rows:
            row.cells[j].width = Cm(width)


def new_table_after(cursor, rows: list[list[str]], font_size: float = 8.5):
    n_rows = len(rows)
    n_cols = max(len(r) for r in rows)
    table = DOC_OBJ.add_table(rows=n_rows, cols=n_cols)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    set_table_width(table)
    cursor.addnext(table._tbl)
    for i, row in enumerate(rows):
        for j in range(n_cols):
            value = row[j] if j < len(row) else ""
            cell = table.cell(i, j)
            cell.text = ""
            par = cell.paragraphs[0]
            par.paragraph_format.space_before = Pt(0)
            par.paragraph_format.space_after = Pt(0)
            par.paragraph_format.line_spacing = 1.0
            run = par.add_run(str(value))
            run.font.size = Pt(font_size)
            if i == 0:
                run.bold = True
                shade_cell(cell, "D9E2F3")
    repeat_header(table)
    apply_widths(table, get_widths(rows[0]))
    return table


def add_block(cursor, block):
    kind = block[0]
    if kind == "t":
        rows = block[1]
        size = block[2] if len(block) > 2 else 8.5
        table = new_table_after(cursor, rows, size)
        return table._tbl
    text = block[1]
    if kind == "b" and not text[:1].isdigit() and not text.startswith("•"):
        text = "• " + text
    par = make_paragraph_after(cursor, text)
    if kind == "b":
        par.paragraph_format.left_indent = Cm(0.75)
        par.paragraph_format.first_line_indent = Cm(-0.35)
        par.paragraph_format.space_after = Pt(3)
    elif kind == "h":
        for run in par.runs:
            run.bold = True
            run.font.size = Pt(11.5)
        par.paragraph_format.space_before = Pt(8)
        par.paragraph_format.space_after = Pt(4)
        par.paragraph_format.keep_with_next = True
    elif kind == "n":
        for run in par.runs:
            run.italic = True
            run.font.size = Pt(9)
        par.alignment = WD_ALIGN_PARAGRAPH.LEFT
        par.paragraph_format.space_after = Pt(8)
    else:
        par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        par.paragraph_format.space_after = Pt(6)
    return par._p


def add_blocks(anchor_par: Paragraph, blocks) -> None:
    cursor = anchor_par._p
    for block in blocks:
        cursor = add_block(cursor, block)


def replace_and_add(anchor_par: Paragraph, blocks) -> None:
    """Reemplaza el texto del ancla con el primer bloque y añade el resto."""
    if not blocks:
        return
    first = blocks[0]
    if first[0] == "p":
        set_text(anchor_par, first[1])
        anchor_par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        rest = blocks[1:]
    else:
        rest = blocks
    add_blocks(anchor_par, rest)


def fill_table(table, rows, start_row: int = 1, font_size: float = 7.5) -> None:
    needed = start_row + len(rows)
    while len(table.rows) < needed:
        table.add_row()
    for i, row in enumerate(rows):
        for j, value in enumerate(row):
            if j >= len(table.columns):
                continue
            cell = table.cell(start_row + i, j)
            cell.text = ""
            par = cell.paragraphs[0]
            par.paragraph_format.space_before = Pt(0)
            par.paragraph_format.space_after = Pt(0)
            par.paragraph_format.line_spacing = 1.0
            run = par.add_run(str(value))
            run.font.size = Pt(font_size)


def delete_table(table) -> None:
    table._tbl.getparent().remove(table._tbl)


def make_unnumbered_heading(par: Paragraph) -> None:
    p_pr = par._p.pPr
    if p_pr is not None and p_pr.numPr is not None:
        p_pr.remove(p_pr.numPr)
    for run in par.runs:
        run.bold = True
        run.font.size = Pt(11.5)
    par.paragraph_format.space_before = Pt(8)
    par.paragraph_format.space_after = Pt(4)
    par.paragraph_format.keep_with_next = True


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return "".join(c for c in text.lower() if c.isalnum())


def main() -> None:
    global DOC_OBJ
    doc = Document(SRC)
    DOC_OBJ = doc
    # La plantilla trae márgenes con decimales (p. ej. 1700.787...), lo que
    # impide a python-docx calcular el ancho de tabla. Se normalizan a twips.
    for section in doc.sections:
        pg_mar = section._sectPr.find(qn("w:pgMar"))
        if pg_mar is not None:
            for key, value in list(pg_mar.attrib.items()):
                try:
                    pg_mar.set(key, str(int(round(float(value)))))
                except ValueError:
                    pass
        # Quitar los corchetes angulares del encabezado de la plantilla
        for header_par in section.header.paragraphs:
            for run in header_par.runs:
                run.text = run.text.replace("<", "").replace(">", "")
    P = list(doc.paragraphs)

    # Referencias a tablas existentes (antes de borrar o insertar)
    t_components = doc.tables[3]
    t_acceptance = doc.tables[8]
    t_project_risks = doc.tables[9]
    t_scope = doc.tables[10]
    t_stakeholders = doc.tables[12]
    t_impact = doc.tables[13]
    t_quality = doc.tables[14]
    t_baseline = doc.tables[15]
    t_ethics = doc.tables[16]

    # La tabla de hardware está dentro de un SDT; se mantiene unida y con
    # encabezado repetido para evitar filas partidas entre páginas.
    for tbl in doc.element.body.iter(qn("w:tbl")):
        table = Table(tbl, doc._body)
        if len(table.columns) == 5 and table.rows[0].cells[0].text.strip() == "Recurso":
            repeat_header(table)
            keep_rows_together(table)

    # Ajustar las columnas de las tablas de herramientas y fuentes para evitar
    # cortes de palabras en encabezados y nombres de herramientas.
    for tbl in doc.element.body.iter(qn("w:tbl")):
        table = Table(tbl, doc._body)
        header = [c.text.strip() for c in table.rows[0].cells]
        if len(header) >= 2 and header[0] == "Categoría" and header[1] == "Herramienta":
            apply_widths(table, [2.9, 2.5, 2.2, 3.5, 4.5])
            set_table_font_size(table, 9.5)
        elif len(header) >= 2 and header[0] == "Fuente o servicio":
            apply_widths(table, [3.2, 3.4, 2.2, 3.0, 3.8])
            set_table_font_size(table, 9.5)

    # El sistema final usa pesos de clase acotados, no SMOTE. Se corrige la
    # fila de la tabla de herramientas para no atribuirle una técnica no usada.
    for tbl in doc.element.body.iter(qn("w:tbl")):
        table = Table(tbl, doc._body)
        for row in table.rows:
            cells = row.cells
            if len(cells) >= 5 and cells[1].text.strip() == "Imbalanced-learn":
                replacements = [
                    (cells[1], "Imbalanced-learn", "Scikit-learn"),
                    (cells[3], "Uso de SMOTE y técnicas para clases minoritarias", "Pesos de clase acotados; sin SMOTE"),
                    (cells[4], "Lemaître et al. (2017)", "Pedregosa et al. (2011)"),
                ]
                for cell, old, new in replacements:
                    for par in cell.paragraphs:
                        for run in par.runs:
                            if old in run.text:
                                run.text = run.text.replace(old, new)

    # El canal de alertas implementado es WhatsApp (Green API), no Telegram.
    # Se corrigen las filas de las tablas que aún mencionaban Telegram.
    telegram_replacements = {
        "Telegram Bot API": "WhatsApp (Green API)",
        "Telegram (2024)": "Green API (2024)",
        "Android o iOS con Telegram": "Android o iOS con WhatsApp",
        "tokens de Telegram": "tokens de WhatsApp/Green API",
    }
    for tbl in doc.element.body.iter(qn("w:tbl")):
        table = Table(tbl, doc._body)
        for row in table.rows:
            for cell in row.cells:
                for par in cell.paragraphs:
                    for run in par.runs:
                        for old, new in telegram_replacements.items():
                            if old in run.text:
                                run.text = run.text.replace(old, new)

    blocks = {}
    blocks.update(get_blocks())
    blocks.update(get_blocks2())

    # ------------------------------------------------------------------
    # Resumen, palabras clave, abstract
    # ------------------------------------------------------------------
    # Eliminar los párrafos vacíos que la plantilla deja antes del resumen
    for par in P[69:83]:
        par._p.getparent().remove(par._p)
    replace_and_add(P[84], blocks["resumen"])
    replace_and_add(P[86], blocks["palabras"])
    set_text(P[88], "Abstract")
    for run in P[88].runs:
        run.bold = True
    P[88].alignment = WD_ALIGN_PARAGRAPH.LEFT
    add_blocks(P[88], blocks["abstract"])
    replace_and_add(P[90], blocks["keywords"])

    # ------------------------------------------------------------------
    # Correcciones de alcance y coherencia con el sistema implementado
    # ------------------------------------------------------------------
    set_text(P[115], "Frente a esta situación, el presente proyecto propone desarrollar una arquitectura de datos que integre información histórica de focos de calor, variables atmosféricas y características geoespaciales del territorio. Con dichos datos se entrenará un modelo predictivo capaz de clasificar grillas territoriales de ~1 km² en tres niveles de riesgo: Verde, Amarillo y Rojo. El índice se calcula para la fecha de referencia y se actualiza diariamente; el horizonte operativo de 24 horas corresponde al intervalo entre actualizaciones, no a un pronóstico meteorológico. Asimismo, la solución incorpora un portal geográfico para la visualización de resultados y un mecanismo de notificación dirigido a bomberos, brigadas, autoridades de gestión del riesgo y comunidades organizadas.")
    set_text(P[155], "La zona de influencia del proyecto se delimita geográficamente a la provincia de Cajamarca, ubicada en el departamento de Cajamarca, al norte del Perú. En este ámbito territorial se desarrollará y evaluará un sistema web para la estimación del riesgo de incendios forestales mediante la integración de información satelital, variables atmosféricas y datos geoespaciales. El sistema permitirá analizar el territorio mediante unidades espaciales de ~1 km², clasificando el riesgo en niveles Verde, Amarillo y Rojo para la fecha de referencia, con actualización diaria. Su alcance comprende el procesamiento de datos, la generación de mapas de riesgo y la comunicación de alertas preventivas, sin incluir actividades de extinción de incendios ni intervención física en campo. Los resultados del proyecto estarán circunscritos a la provincia de Cajamarca y no podrán generalizarse automáticamente a otras provincias o regiones sin una evaluación adicional.")
    set_text(P[190], "Diseñar e implementar un sistema web que integre información satelital, atmosférica y geoespacial para estimar el riesgo de incendios forestales en la provincia de Cajamarca, con actualización diaria y un horizonte operativo de 24 horas entre actualizaciones.")
    set_text(P[319], "A partir del contraste realizado entre los requisitos del sistema y los hallazgos diagnosticados en el estado actual, se evidencia que los requisitos críticos RE02, RE03 y RE04 no son cubiertos por la gestión operativa actual. Esto se fundamenta en la urgente necesidad de integrar información territorial y variables atmosféricas para la construcción de escenarios de riesgo, así como en la meta técnica del proyecto de clasificar grillas de ~1 km² en la provincia de Cajamarca (CENEPRED, 2025; Problemáticas para Proyecto Final Capstone 2, 2026).")
    set_text(P[469], "La alternativa seleccionada es una arquitectura de datos con predicción geoespacial y alertas preventivas. El sistema integra datos de focos de calor, variables atmosféricas y atributos territoriales para estimar el riesgo de incendios forestales en grillas de ~1 km² de la provincia de Cajamarca, para la fecha de referencia y con actualización diaria.")
    set_text(P[332], "El principal riesgo técnico es el desbalance de los datos, debido a que existen más registros de grillas sin incendio que registros con incendio. Se evaluó el sobremuestreo SMOTE (Lemaître et al., 2017), pero se descartó porque puede generar vecinos sintéticos que cruzan bloques espaciales y filtrar información; en su lugar se aplican pesos de clase acotados (scale_pos_weight) y se evalúa el modelo con PR-AUC, recall@top-k y F1, en lugar de depender únicamente de la exactitud global.")
    set_text(P[477], "Muestra el riesgo en un portal web geográfico y envía alertas por WhatsApp cuando una grilla se clasifica con riesgo alto.")
    set_text(P[474], "Almacena los registros espaciales y temporales en archivos Parquet/CSV y, opcionalmente, en PostgreSQL/PostGIS para despliegues institucionales.")

    # Eliminar instrucciones de plantilla que ya fueron reemplazadas por contenido
    for index in (400, 403):
        P[index]._p.getparent().remove(P[index]._p)

    # Nota de implementación después del párrafo de herramientas de software
    add_blocks(P[285], [("n", "Nota de implementación: la versión final del prototipo almacena los datos en archivos Parquet/CSV y utiliza un portal HTML/CSS/JS con Leaflet. PostgreSQL/PostGIS y Streamlit se mantienen como alternativas de despliegue institucional, no como dependencias obligatorias del sistema.")])

    # ------------------------------------------------------------------
    # 4. Herramientas
    # ------------------------------------------------------------------
    add_blocks(P[291], blocks["fuentes_datos"])
    add_blocks(P[293], blocks["hardware"])
    set_text(P[304], "4.5. Comparación de metodologías y estándares de ingeniería")
    make_unnumbered_heading(P[304])
    add_blocks(P[304], blocks["metodologias"])
    set_text(P[305], "4.6. Selección fundamentada de herramientas hardware y software")
    make_unnumbered_heading(P[305])
    add_blocks(P[305], blocks["seleccion_herramientas"])
    set_text(P[306], "4.7. Uso correcto de las herramientas: recolección, análisis y procesamiento")
    make_unnumbered_heading(P[306])
    add_blocks(P[306], blocks["uso_herramientas"])
    set_text(P[307], "4.8. Requisitos de usuario final y de servidor")
    make_unnumbered_heading(P[307])
    add_blocks(P[307], blocks["requisitos_servidor"])

    # ------------------------------------------------------------------
    # Tabla 4: componentes de la alternativa
    # ------------------------------------------------------------------
    for row in t_components.rows:
        if row.cells[0].text.strip().lower() == "almacenamiento":
            row.cells[1].text = "Parquet / CSV (PostgreSQL/PostGIS opcional)"
        if row.cells[0].text.strip().lower() == "modelo predictivo":
            row.cells[1].text = "Ensemble LightGBM + XGBoost + Random Forest"
            row.cells[2].text = "Clasificar el riesgo en Verde, Amarillo y Rojo"
    for extra in [
        ["Portal web", "HTML, CSS, JavaScript y Leaflet", "Visualizar el mapa y el riesgo"],
        ["Alertas", "WhatsApp (Green API) y APScheduler", "Difundir el resumen diario"],
        ["Calidad", "pytest, ruff y GitHub Actions", "Verificar el sistema"],
    ]:
        row = t_components.add_row()
        for j, value in enumerate(extra):
            cell = row.cells[j]
            cell.text = ""
            par = cell.paragraphs[0]
            par.paragraph_format.space_before = Pt(0)
            par.paragraph_format.space_after = Pt(0)
            run = par.add_run(value)
            run.font.size = Pt(8.5)
    apply_widths(t_components, [3.0, 6.5, 6.5])
    repeat_header(t_components)

    # ------------------------------------------------------------------
    # Tablas 9, 10 y 11: coherencia de criterios
    # ------------------------------------------------------------------
    for row in t_acceptance.rows:
        if row.cells[0].text.strip() == "CR03":
            row.cells[1].text = "El modelo genera una clasificación de riesgo para la fecha de referencia, con actualización diaria."
    for row in t_project_risks.rows:
        if row.cells[0].text.strip() == "R02":
            row.cells[4].text = "Aplicar pesos de clase acotados (scale_pos_weight), validación espacial y métricas top-k."
    for row in t_scope.rows:
        code = row.cells[0].text.strip()
        if code == "L02":
            row.cells[2].text = "El sistema estima un índice de susceptibilidad para la fecha de referencia; no pronostica las próximas 24 horas ni confirma un incendio activo."
        if code == "L06":
            row.cells[2].text = "La alerta por WhatsApp se implementa para fines de prototipo y depende de internet, disponibilidad del servicio y configuración de los usuarios."
    apply_widths(t_acceptance, [1.5, 7.5, 6.0])
    apply_widths(t_project_risks, [1.3, 4.5, 1.8, 1.8, 6.0])
    apply_widths(t_scope, [1.5, 3.0, 10.5])
    for table in (t_acceptance, t_project_risks, t_scope):
        repeat_header(table)

    # ------------------------------------------------------------------
    # 5.6 Requerimientos
    # ------------------------------------------------------------------
    add_blocks(P[429], blocks["requerimientos"])

    # ------------------------------------------------------------------
    # 5.12 Gestión de riesgos
    # ------------------------------------------------------------------
    add_blocks(P[501], blocks["roles_riesgos"])
    P[501]._p.getparent().remove(P[501]._p)
    add_blocks(P[504], blocks["presupuesto_riesgos"])
    P[504]._p.getparent().remove(P[504]._p)
    set_text(P[506], "Matriz de riesgos")
    add_blocks(P[506], blocks["matriz_riesgos"])

    # ------------------------------------------------------------------
    # 5.13 Interesados: llenar tablas existentes
    # ------------------------------------------------------------------
    P[510]._p.getparent().remove(P[510]._p)
    P[516]._p.getparent().remove(P[516]._p)
    fill_table(t_stakeholders, blocks["stakeholders"], start_row=1, font_size=7.0)
    fill_table(t_impact, blocks["impacto_stakeholders"], start_row=1, font_size=7.5)
    for cell in t_stakeholders.rows[0].cells:
        for par in cell.paragraphs:
            for run in par.runs:
                run.font.size = Pt(7.0)
    apply_widths(t_stakeholders, [2.1, 1.9, 1.8, 2.2, 2.1, 2.1, 1.7, 1.4])
    apply_widths(t_impact, [4.0, 11.0])
    repeat_header(t_stakeholders)
    repeat_header(t_impact)

    # ------------------------------------------------------------------
    # 5.14 Presupuesto y 5.15 Seguridad
    # ------------------------------------------------------------------
    set_text(P[521], "Resumen del presupuesto del proyecto")
    add_blocks(P[521], blocks["presupuesto_proyecto"])
    set_text(P[525], "Plan de seguridad de la aplicación, los datos y la infraestructura")
    add_blocks(P[525], blocks["plan_seguridad"])
    P[525]._p.getparent().remove(P[525]._p)

    # ------------------------------------------------------------------
    # 5.16 Calidad: reemplazar la tabla plantilla
    # ------------------------------------------------------------------
    delete_table(t_quality)
    add_blocks(P[528], blocks["plan_calidad"])

    # ------------------------------------------------------------------
    # 6. Metodología
    # ------------------------------------------------------------------
    add_blocks(P[533], blocks["metodologia"])
    add_blocks(P[539], blocks["planificacion"])
    add_blocks(P[540], blocks["analisis"])
    add_blocks(P[541], blocks["desarrollo"])
    set_text(P[542], "Resultados por etapa de la metodología")
    add_blocks(P[542], blocks["resultados_etapas"])
    set_text(P[543], "Protección de datos en el producto y en la investigación")
    add_blocks(P[543], blocks["proteccion_datos"])

    # 6.2 Pruebas
    add_blocks(P[547], blocks["pruebas_unitarias"])
    add_blocks(P[549], blocks["evidencia_unitarias"])
    add_blocks(P[551], blocks["pruebas_aceptacion"])
    add_blocks(P[554], blocks["evidencia_aceptacion"])

    # 6.3 Despliegue
    set_text(P[558], "Plan de despliegue")
    add_blocks(P[558], blocks["plan_despliegue"])
    set_text(P[559], "Proceso de despliegue")
    add_blocks(P[559], blocks["proceso_despliegue"])
    add_blocks(P[560], blocks["evidencia_despliegue"])

    # 6.4 Medición de la variable independiente
    set_text(P[564], "Resultados de la medición de la variable independiente")
    add_blocks(P[564], blocks["medicion_vi"])

    # Quitar instrucciones de plantilla que quedaron en la sección 6
    for index in (535, 536, 537, 538, 548, 553, 560):
        P[index]._p.getparent().remove(P[index]._p)
    # El título original ya existe; se elimina el duplicado
    P[564]._p.getparent().remove(P[564]._p)

    # ------------------------------------------------------------------
    # 7. Resultados
    # ------------------------------------------------------------------
    add_blocks(P[570], blocks["viabilidad_tecnica"])
    add_blocks(P[572], blocks["viabilidad_economica"])
    add_blocks(P[573], blocks["indicadores"])

    # Reemplazar la tabla 16 (línea base) por la nueva tabla del bloque
    delete_table(t_baseline)
    replace_and_add(P[575], blocks["linea_base"])

    add_blocks(P[577], blocks["sostenibilidad"])
    replace_and_add(P[579], blocks["discusion"])
    add_blocks(P[582], blocks["oe01"])

    # ------------------------------------------------------------------
    # 5.17 / 9. Matriz ética (tabla existente, se llena para no dejarla vacía)
    # ------------------------------------------------------------------
    ethics = [
        ["Transparencia sobre las limitaciones", "Sobrestimar la capacidad predictiva", "Falsa confianza y decisiones riesgosas", "Publicar ROC-AUC, PR-AUC, recall@top-k y percentil; aviso “no es certeza” en el portal y el PDF."],
        ["Protección de datos personales", "Recolectar o exponer datos innecesarios", "Sanción legal y daño reputacional", "Minimización, consentimiento, anonimización y .env fuera del repositorio."],
        ["Acceso equitativo", "Excluir a comunidades con baja conectividad", "Brecha digital y desigualdad", "Portal ligero, WhatsApp, lenguaje claro y uso sin registro."],
        ["Rigor científico", "Fuga de datos o métricas infladas", "Conclusiones inválidas y pérdida de credibilidad", "Validación espacial, código abierto, auditorías y revisión por pares."],
        ["Responsabilidad operativa", "Alertas sin verificación humana", "Movilización innecesaria o falsa seguridad", "Etiqueta “alerta preventiva”, protocolo de verificación y comunicación de incertidumbre."],
    ]
    fill_table(t_ethics, ethics, start_row=1, font_size=7.5)
    apply_widths(t_ethics, [4.0, 3.5, 3.5, 4.0])
    repeat_header(t_ethics)

    # ------------------------------------------------------------------
    # Referencias: quitar el marcador, añadir nuevas y ordenar
    # ------------------------------------------------------------------
    P[615].paragraph_format.page_break_before = True
    ref_pars = [
        P[i - 1]
        for i in range(617, 686)
        if P[i - 1].text.strip() and "Anotar los libros" not in P[i - 1].text
    ]
    refs = [p.text.strip() for p in ref_pars] + NEW_REFERENCES
    refs = [re.sub(r"(?<=[^\s(])https?://", " https://", ref) for ref in refs]
    refs = [re.sub(r"\s+", " ", ref).strip() for ref in refs]
    # Eliminar duplicados exactos
    seen = set()
    unique = []
    for ref in refs:
        key = normalize(ref)[:120]
        if key not in seen:
            seen.add(key)
            unique.append(ref)
    unique.sort(key=normalize)
    # El sistema no usa Telegram; se retira su referencia para no atribuirle
    # un canal de alertas que no forma parte de la implementación.
    unique = [ref for ref in unique if not ref.strip().startswith("Telegram.")]

    for i, par in enumerate(ref_pars):
        if i < len(unique):
            set_text(par, unique[i])
            par.paragraph_format.left_indent = Cm(1.25)
            par.paragraph_format.first_line_indent = Cm(-1.25)
            par.paragraph_format.space_after = Pt(6)
            par.alignment = WD_ALIGN_PARAGRAPH.LEFT
    # Insertar las referencias adicionales después de la última
    cursor = ref_pars[-1]._p
    for ref in unique[len(ref_pars):]:
        new_p = make_paragraph_after(cursor, ref)
        new_p.paragraph_format.left_indent = Cm(1.25)
        new_p.paragraph_format.first_line_indent = Cm(-1.25)
        new_p.paragraph_format.space_after = Pt(6)
        new_p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        cursor = new_p._p
    # Si hay menos referencias únicas que párrafos, eliminar los sobrantes
    for par in ref_pars[len(unique):]:
        par._p.getparent().remove(par._p)
    # Eliminar el párrafo marcador de la plantilla
    placeholder = P[685]
    if "Anotar los libros" in placeholder.text:
        placeholder._p.getparent().remove(placeholder._p)

    # ------------------------------------------------------------------
    # Anexos 01 y 02: reemplazar instrucciones por enlaces
    # ------------------------------------------------------------------
    P[687].paragraph_format.page_break_before = True
    set_text(P[690], "Enlace del video: [COMPLETAR: URL de OneDrive UPN con permisos de visualización]. El video debe mostrar el portal, el mapa, el reporte ciudadano, las alertas y la API.")
    set_text(P[694], "Repositorio: https://github.com/DanielMedina1727/SISTEMA-NACI-NAL-DE-ALERTA-TEMPRANA-DE-INCENDIOS-FORESTALES. El repositorio contiene el código fuente, los datos, el modelo, las pruebas y la documentación. Licencia MIT.")
    for par in (P[690], P[694]):
        par.alignment = WD_ALIGN_PARAGRAPH.LEFT

    # Eliminar las notas aclaratorias y los párrafos vacíos del final de la plantilla
    for par in P[695:]:
        par._p.getparent().remove(par._p)

    # Eliminar los índices vacíos de tablas, figuras y anexos
    for par in P:
        if par._p.getparent() is None:
            continue
        text = par.text.strip().upper()
        if text.startswith("ÍNDICE DE") or text.startswith("INDICE DE"):
            par._p.getparent().remove(par._p)

    # Solicitar a Word que actualice los campos (TOC) al abrir el documento
    settings = doc.settings.element
    if settings.find(qn("w:updateFields")) is None:
        update = OxmlElement("w:updateFields")
        update.set(qn("w:val"), "true")
        settings.append(update)

    # ------------------------------------------------------------------
    # Anexos 03–10
    # ------------------------------------------------------------------
    cursor = P[694]._p
    for annex in get_annexes():
        heading = make_paragraph_after(cursor, annex["title"], style="Heading 2")
        heading.paragraph_format.page_break_before = True
        cursor = heading._p
        for block in annex["blocks"]:
            cursor = add_block(cursor, block)

    # Homogeneizar el formato de los títulos de los anexos (el estilo Heading 2
    # de la plantilla es azul y subrayado, como un hipervínculo).
    for par in doc.paragraphs:
        if par.style.name == "Heading 2" and par.text.strip().startswith("11."):
            for run in par.runs:
                run.font.color.rgb = RGBColor(0, 0, 0)
                run.font.underline = False
                run.font.bold = True

    # Repetir el encabezado de todas las tablas que se parten entre páginas.
    for tbl in doc.element.body.iter(qn("w:tbl")):
        table = Table(tbl, doc._body)
        if len(table.rows) >= 2:
            repeat_header(table)

    # ------------------------------------------------------------------
    # Guardar
    # ------------------------------------------------------------------
    # Quitar párrafos vacíos que quedan entre el índice y el resumen
    # (Word los conserva al actualizar el TOC).
    final_pars = list(doc.paragraphs)
    for idx, par in enumerate(final_pars):
        if par.text.strip().startswith("RESUMEN"):
            j = idx - 1
            while j >= 0 and not final_pars[j].text.strip():
                final_pars[j]._p.getparent().remove(final_pars[j]._p)
                j -= 1
            par.paragraph_format.page_break_before = True
            break

    # Cambiar el campo TOC para que se base en los niveles de esquema
    # (Heading 1–3) y no en nombres de estilo localizados.
    for instr in doc.element.body.iter(qn("w:instrText")):
        if instr.text and "TOC" in instr.text:
            instr.text = ' TOC \\o "1-3" \\h \\z \\u'
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT)
    print(f"Informe generado: {OUT}")
    print(f"Párrafos: {len(doc.paragraphs)}; tablas: {len(doc.tables)}")


if __name__ == "__main__":
    main()
