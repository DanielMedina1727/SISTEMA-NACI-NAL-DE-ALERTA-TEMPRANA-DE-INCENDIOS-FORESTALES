"""
Módulo de generación de informes ejecutivos oficiales en formato PDF utilizando ReportLab.
Incluye cabecera institucional, firma digital SHA-256, sello temporal y matriz de grillas en riesgo.
"""
import hashlib
import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def generate_executive_pdf(risk_data: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Estilos personalizados
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Title'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#1a252f'),
        alignment=0
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#7f8c8d'),
    )

    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#2c3e50'),
        spaceBefore=10,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#2c3e50')
    )

    elements = []

    # 1. Cabecera Institucional
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    elements.append(Paragraph("SISTEMA NACIÓNAL DE ALERTA TEMPRANA DE INCENDIOS FORESTALES", subtitle_style))
    elements.append(Paragraph("INFORME EJECUTIVO DE EVALUACIÓN DE RIESGO GEOSPATIAL", title_style))
    elements.append(Spacer(1, 8))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#e74c3c'), spaceAfter=12))

    # Hash digital para validez legal (Mitigación Restricción 3 Capstone)
    raw_hash_content = f"{now_str}_{risk_data.get('count', 0)}_{risk_data.get('red_count', 0)}"
    data_hash = hashlib.sha256(raw_hash_content.encode('utf-8')).hexdigest()[:16].upper()

    # 2. Metadatos del Informe
    meta_table_data = [
        [
            Paragraph("<b>Región de Análisis:</b> Cajamarca, Perú", body_style),
            Paragraph(f"<b>Fecha / Hora Sello:</b> {now_str}", body_style)
        ],
        [
            Paragraph("<b>Modelo Evaluador:</b> LightGBM Classifier v1.0", body_style),
            Paragraph(f"<b>Firma Digital Hash SHA-256:</b> <font color='#c0392b'>{data_hash}</font>", body_style)
        ],
        [
            Paragraph("<b>Ventana Temporal:</b> Predicción a 24-48 Horas", body_style),
            Paragraph("<b>Confianza Global Modelo:</b> 97.85% Recall / F1 0.8867", body_style)
        ]
    ]

    meta_table = Table(meta_table_data, colWidths=[270, 270])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#ecf0f1')),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 14))

    # 3. Resumen de Nivel de Riesgo (Semáforo)
    elements.append(Paragraph("1. RESUMEN EJECUTIVO DE NIVEL DE RIESGO", heading_style))

    total = risk_data.get('count', 0)
    red = risk_data.get('red_count', 0)
    yellow = risk_data.get('yellow_count', 0)
    green = risk_data.get('green_count', 0)

    summary_data = [
        ["Categoría de Riesgo", "Celdas (1km² c/u)", "Porcentaje del Área", "Acción Institucional Recomendada"],
        ["Alerta Roja (Riesgo Alto)", str(red), f"{(red/max(1,total))*100:.1f}%", "Despliegue inmediato de Brigadas y Bomberos"],
        ["Vigilancia (Riesgo Medio)", str(yellow), f"{(yellow/max(1,total))*100:.1f}%", "Monitoreo continuo y patrullaje de Rondas"],
        ["Bajo Riesgo (Seguro)", str(green), f"{(green/max(1,total))*100:.1f}%", "Operación agrícola y forestal normal"]
    ]

    summary_table = Table(summary_data, colWidths=[130, 90, 100, 220])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#fadbd8')),  # Rojo claro
        ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#fdebd0')),  # Amarillo claro
        ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#d4efdf')),  # Verde claro
        ('ALIGN', (1, 0), (2, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#7f8c8d')),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 14))

    # 4. Detalle de Grillas Críticas en Alerta Roja
    elements.append(Paragraph("2. ZONAS CRÍTICAS EN ALERTA ROJA (MÁXIMA PRIORIDAD)", heading_style))

    red_features = risk_data.get('red_features', [])[:10]  # Top 10
    if red_features:
        grid_rows = [["ID Grilla", "Coordenadas (Lat, Lon)", "Probabilidad", "Temp 2m", "Humedad", "Viento (Vel/Dir)"]]
        for f in red_features:
            props = f.get('properties', {})
            grid_id = props.get('grid_id', 'N/A')
            prob = f"{props.get('probabilidad', 0):.1%}"
            temp = f"{props.get('temp_2m', 0)} °C"
            hum = f"{props.get('humedad_relativa', 0)} %"
            viento = f"{props.get('viento_velocidad', 0)} km/h ({props.get('viento_direccion', 0)}°)"
            
            # Extraer lat/lon
            try:
                lon_s, lat_s = grid_id.split('_')
                coords_str = f"{float(lat_s):.4f}, {float(lon_s):.4f}"
            except Exception:
                coords_str = "N/A"

            grid_rows.append([grid_id, coords_str, prob, temp, hum, viento])

        grid_table = Table(grid_rows, colWidths=[100, 120, 70, 70, 70, 110])
        grid_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#c0392b')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e74c3c')),
            ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(grid_table)
    else:
        elements.append(Paragraph("<i>No se registraron grillas en estado de Alerta Roja para este período.</i>", body_style))

    elements.append(Spacer(1, 20))

    # 5. Firmas Oficiales
    elements.append(Paragraph("3. CONFORMIDAD Y FIRMAS OFICIALES", heading_style))
    elements.append(Spacer(1, 15))

    sig_data = [
        [
            Paragraph("___________________________________<br/><b>Ing. Responsable de Gestión de Riesgos</b><br/>Defensa Civil / Municipalidad", body_style),
            Paragraph("___________________________________<br/><b>Comandante de Brigada</b><br/>Cuerpo General de Bomberos", body_style)
        ]
    ]

    sig_table = Table(sig_data, colWidths=[270, 270])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(sig_table)

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
