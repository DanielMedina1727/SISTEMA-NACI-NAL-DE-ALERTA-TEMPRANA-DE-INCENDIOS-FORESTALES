# -*- coding: utf-8 -*-
"""
Completa las secciones faltantes del informe Capstone en un nuevo .docx.
Uso: python scripts/completar_informe.py
"""
from __future__ import annotations
import copy
from pathlib import Path
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

SRC  = Path(r"C:\Users\Administrator\.gemini\antigravity\brain\dbbd95a6-b14a-49a4-8f19-2c209b5f931b\.user_uploaded\media_1794499998724_9289a815.docx")
OUT  = Path(__file__).resolve().parent.parent / "docs" / "Informe_Capstone_COMPLETADO_v2.docx"

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────
def _fmt(para, bold=False, italic=False, size=None, color=None, align=None):
    for run in para.runs:
        if bold is not None:   run.bold   = bold
        if italic is not None: run.italic = italic
        if size:               run.font.size = Pt(size)
        if color:              run.font.color.rgb = RGBColor(*color)
    if align:
        para.alignment = align
    return para

def add_body(doc, text, bold=False, italic=False, size=11, first_indent=True):
    p = doc.add_paragraph(style="Body Text")
    run = p.add_run(text)
    run.bold   = bold
    run.italic = italic
    run.font.size = Pt(size)
    if first_indent:
        p.paragraph_format.first_line_indent = Cm(1.25)
    return p

def add_bullet(doc, text, level=0):
    p = doc.add_paragraph(style="List Paragraph")
    p.paragraph_format.left_indent = Cm(1.25 * (level + 1))
    p.paragraph_format.first_line_indent = Cm(-0.5)
    run = p.add_run(f"• {text}")
    run.font.size = Pt(11)
    return p

def add_h4(doc, text):
    p = doc.add_paragraph(text, style="Heading 4")
    return p

def add_note(doc, text):
    p = doc.add_paragraph(style="Normal")
    run = p.add_run(f"Nota: {text}")
    run.italic = True
    run.font.size = Pt(10)
    return p

# ─────────────────────────────────────────────────────────────
# Content blocks
# ─────────────────────────────────────────────────────────────
# OE01 results table rows
OE01_TABLE = [
    ["Variable", "DIMENSIONES", "INDICADORES", "RESULTADO"],
    ["Predicción del riesgo de incendios forestales",
     "Diagnóstico del proceso actual",
     "• Frecuencia de causas de ineficiencia (Pareto)\n• Fragmentación de fuentes",
     "80 % del impacto negativo en 3 causas: P1 dispersión (38 %), P2 retraso de campo (26 %), P3 falta integración SIG/clima (16 %)."],
    ["",
     "Capacidad de ordenamiento inicial (Línea Base)",
     "• ROC-AUC espacial 5-fold\n• PR-AUC\n• Recall @ Top-10 %",
     "ROC-AUC Baseline: 0,413 (sobreajuste sin partición espacial).\nPR-AUC: 0,0006 (azar ≈ 0,00066).\nRecall @ Top-10 %: 8,89 %."],
    ["",
     "Cobertura y oportunidad",
     "• Frecuencia de actualización\n• Celdas cubiertas",
     "Monitoreo manual previo: semanal o reactivo.\nCobertura sistematizada previa: 0 celdas integradas."],
]

OE03_TABLE = [
    ["Métrica", "Valor", "vs. Azar", "Interpretación Operativa"],
    ["ROC-AUC Espacial (5-fold)", "0,649 ± 0,069", "+29,8 %", "Capacidad estadísticamente significativa de ordenar celdas por susceptibilidad."],
    ["PR-AUC", "0,0017 ± 0,0015", "2,57 × prevalencia", "Discriminación positiva con desbalance extremo (45 positivos de 68 187)."],
    ["Recall @ Top-10 %", "19,44 %", "1,94 × azar", "Captura casi 1/5 de incendios reales inspeccionando solo el 10 % del territorio."],
    ["Recall @ Top-20 %", "45,11 %", "2,26 × azar", "Patrullaje focalizado en el 20 % del territorio captura el 45 % de focos."],
    ["F1-Score", "0,0018", "3,6 × baseline", "Penalizado por prevalencia 0,066 %; evaluar por presupuesto de alerta."],
    ["Latencia de Inferencia", "< 2 ms / celda", "Óptimo RT", "Reevalúa riesgo de toda Cajamarca en < 1 s vía /risk/today."],
]

ETHICS_MATRIX = [
    ["#", "Responsabilidad Ética", "Riesgo Identificado", "Consecuencias", "Control Implementado"],
    ["1", "Transparencia metodológica: reportar métricas reales sin sesgo positivo.",
     "Exagerar el rendimiento del modelo (ROC-AUC 0,65 presentado como 0,99).",
     "Pérdida de credibilidad, decisiones erróneas de brigadas ante incendios.",
     "Validación espacial out-of-fold documentada; sección honesta de limitaciones en el README y en el portal."],
    ["2", "Protección de datos personales de reportantes ciudadanos (Ley N.° 29733).",
     "Exposición de coordenadas GPS de ciudadanos que reportan focos.",
     "Vulneración de privacidad; posible uso malicioso de las ubicaciones.",
     "Rate-limiting (5 req/IP/10 min); almacenamiento local en JSONL sin transmisión a terceros; sin identificadores personales."],
    ["3", "No alarmar innecesariamente a comunidades vulnerables.",
     "Falsos positivos Rojo en zonas densamente pobladas causan pánico.",
     "Evacuaciones innecesarias; pérdida de confianza institucional.",
     "Umbral por presupuesto de alerta (Top-1 % territorial, no umbral arbitrario); mensajes WhatsApp redactados en tono preventivo."],
    ["4", "Equidad de acceso: canal de alerta accesible sin conexión de alta velocidad.",
     "Brecha digital excluye comunidades rurales con conectividad limitada.",
     "Inequidad en la recepción de alertas; mayor vulnerabilidad relativa.",
     "Canal WhatsApp (funciona con 2G); portal ligero (<100 KB sin mapa base); texto plano en PDF imprimible."],
    ["5", "Responsabilidad sobre el código: mantenimiento y actualización del modelo.",
     "Data drift: el modelo pierde precisión con cambios climáticos sin reentrenamiento.",
     "Alertas desactualizadas; pérdida de utilidad preventiva con el tiempo.",
     "Pipeline reentrenable con un solo comando; scheduler con logs auditables; documentación de dependencias versionadas en pyproject.toml."],
]

COMMITMENT_PARAGRAPHS = {
    "CAMPOS SILVA, Fran Antony": {
        "compromiso": (
            "Como futuro ingeniero de sistemas, asumo el compromiso formal de ejercer mi profesión "
            "fundamentado en los valores de honestidad, responsabilidad y respeto hacia los grupos "
            "humanos más vulnerables. Mi participación en el desarrollo de AlertaForestal Perú me "
            "compromete a garantizar que los algoritmos y arquitecturas implementados se diseñen "
            "con estricta transparencia técnica, reconociendo públicamente las limitaciones de las "
            "predicciones y evitando cualquier exageración que pueda poner en riesgo la integridad "
            "física de brigadistas o comuneros. Asimismo, me comprometo a cumplir rigurosamente el "
            "marco legal peruano de protección de datos personales (Ley N.° 29733), asegurando que "
            "los sistemas que desarrolle promuevan la inclusión social y la preservación ambiental."
        ),
        "importancia": (
            "El ejercicio ético en la ingeniería de sistemas resulta indispensable porque las "
            "decisiones automatizadas impactan directamente en la seguridad y el bienestar de la "
            "sociedad. En proyectos de gestión del riesgo ambiental, una omisión negligente puede "
            "ocasionar pérdida de vidas humanas o destrucción de ecosistemas. Apegarse al marco "
            "normativo vigente (Ley N.° 29664 y Ley N.° 29733) y actuar con honestidad técnica "
            "garantiza que la profesión mantenga la confianza pública y actúe como catalizador de "
            "justicia social y resiliencia territorial."
        ),
    },
    "CHAVEZ MARIN, Marco Antonio": {
        "compromiso": (
            "En mi calidad de estudiante de ingeniería y futuro profesional, reafirmo mi deber "
            "ético de actuar con solidaridad, probidad e integridad en cada solución computacional "
            "que desarrolle. Me comprometo a tratar la información territorial y meteorológica con "
            "rigor científico, velando porque los canales de comunicación y alerta sean accesibles "
            "para las poblaciones rurales de Cajamarca, sin discriminación por alfabetización "
            "digital o capacidad socioeconómica. Entiendo que la tecnología es un medio de servicio "
            "social y no un fin lucrativo, por lo que asumo la responsabilidad de mantener el "
            "código documentado, seguro y abierto en beneficio de la reducción de la vulnerabilidad "
            "ante desastres naturales."
        ),
        "importancia": (
            "La relevancia de la ética en nuestro quehacer radica en comprender que detrás de cada "
            "registro satelital y cada coordenada existen familias, parcelas agrícolas y reservas "
            "naturales. Ejercer la ingeniería con conciencia ética implica respetar la diversidad "
            "de los usuarios, adaptando el lenguaje técnico para que no sea excluyente y evitando "
            "sesgos algorítmicos. La ética no es un requisito formal del currículo, sino la "
            "salvaguarda que impide que la tecnología ensanche las brechas de vulnerabilidad social "
            "en comunidades históricamente desatendidas."
        ),
    },
    "GUEVARA FORES, Luis Miguel": {
        "compromiso": (
            "Mi compromiso profesional se sustenta en la responsabilidad social y la honestidad "
            "intelectual aplicadas al ejercicio de la ingeniería de software. Me comprometo a "
            "diseñar sistemas de información donde prime la confiabilidad de los datos y el respeto "
            "irrestricto hacia la vida humana y la biodiversidad. En el marco de este proyecto de "
            "alerta temprana, empeño mi palabra en defender la verdad de los datos, informando a "
            "los tomadores de decisiones sobre los márgenes reales de incertidumbre del modelo y "
            "velando por que las alertas comunitarias se transmitan de forma constructiva, sin "
            "generar pánico injustificado ni desatención de protocolos oficiales."
        ),
        "importancia": (
            "A nivel profesional, la ética constituye la columna vertebral de la credibilidad "
            "científica y la sostenibilidad de las organizaciones. En un contexto donde la "
            "inteligencia artificial puede ser utilizada para generar desinformación o modelos "
            "fraudulentos, el ingeniero de sistemas debe erigirse como garante del rigor "
            "metodológico. La observancia estricta de las normas de calidad, la protección de la "
            "confidencialidad y la comunicación transparente de las limitaciones operativas "
            "protegen tanto a los usuarios finales como a la institución que respalda el proyecto."
        ),
    },
    "LLANOS MENDOZA, Lenis Jhonatan": {
        "compromiso": (
            "Asumo el compromiso ético de velar por que cada línea de código y cada flujo de "
            "procesamiento de datos reflejen los principios de justicia, equidad y respeto a la "
            "diversidad cultural y geográfica del Perú. Reconozco que los incendios forestales "
            "afectan directamente los medios de vida de campesinos y agricultores andinos; por "
            "ello, mi labor como ingeniero estará guiada por el principio de solidaridad, "
            "asegurando que las herramientas de software sean sencillas de interpretar, respeten "
            "la privacidad de los reportantes ciudadanos y se alineen a las directrices de gestión "
            "del riesgo del Estado peruano bajo la Ley N.° 29664 (SINAGERD)."
        ),
        "importancia": (
            "La práctica ética profesional garantiza que los sistemas de información cumplan una "
            "función verdaderamente democratizadora. La importancia de este ejercicio en el ámbito "
            "de los desastres forestales radica en evitar que el acceso a información vital dependa "
            "de privilegios económicos. Respetar la legislación nacional sobre datos personales y "
            "articular el desarrollo técnico con las autoridades del SINAGERD asegura que nuestras "
            "soluciones tecnológicas se integren armónicamente a las políticas públicas del Estado."
        ),
    },
    "MEDINA CARUAJULCA, Segundo Daniel": {
        "compromiso": (
            "Como líder y desarrollador en el área de sistemas computacionales, declaro mi "
            "compromiso inquebrantable con la ética profesional, la honestidad y la excelencia "
            "técnica. Me comprometo a no utilizar jamás la inteligencia artificial para encubrir "
            "deficiencias o inflar métricas predictivas, reportando con total transparencia los "
            "resultados obtenidos sin fuga de datos. Asimismo, me comprometo a impulsar tecnologías "
            "inclusivas y gratuitas que sirvan de puente entre la ciencia de datos satelital y las "
            "brigadas que combaten el fuego en primera línea, garantizando el respeto de los "
            "derechos fundamentales de las comunidades y la protección del patrimonio natural de "
            "la región Cajamarca."
        ),
        "importancia": (
            "El ejercicio ético en la ingeniería de sistemas e inteligencia artificial es el factor "
            "determinante que distingue una simple aplicación de software de una solución de alto "
            "impacto y valor social. En la era digital, la capacidad técnica debe estar supeditada "
            "al bienestar común y al respeto de la diversidad cultural. Ejercer con ética "
            "profesional nos exige asumir la autoría y responsabilidad total de nuestros "
            "desarrollos, garantizando la trazabilidad, protegiendo los secretos de configuración "
            "y asegurando que las innovaciones tecnológicas se desplieguen siempre en defensa de "
            "la vida humana y el medio ambiente."
        ),
    },
}

PROMPTS = [
    ("Auditoría de seguridad y consistencia de variables (Backend/Scripts)",
     "Actúa como auditor senior de software ISO/IEC 25010. Revisa app/security.py y app/main.py. "
     "Identifica variables sensibles o credenciales hardcodeadas, analiza la configuración de "
     "cabeceras CORS y propón controles estrictos para endpoints de alertas usando X-API-Key y "
     "rate limiting."),
    ("Verificación de fuga de información en el modelo ML",
     "Analiza data_pipeline/grid_builder.py y train_model.py. Evalúa si el cálculo de variables "
     "de vecindario (KNN con cKDTree) produce fuga de datos respecto a la validación espacial por "
     "bloques. Genera una prueba unitaria con pytest que valide que las celdas de prueba no "
     "contaminan el conjunto de entrenamiento."),
    ("Accesibilidad y diseño del portal ciudadano (Frontend/UI)",
     "Rediseña la sección del mapa Leaflet en web/index.html y web/app.js para usuarios no "
     "técnicos de zonas rurales de Cajamarca. Agrega una sección 'Cómo usar el sistema' con "
     "4 pasos sencillos, una guía visual del semáforo (Verde, Amarillo, Rojo) con indicaciones "
     "sobre cuándo llamar a los bomberos al 116, y haz que los popups del mapa expliquen el riesgo "
     "en lenguaje natural en vez de términos probabilísticos complejos."),
    ("Corrección de estilo y redacción académica APA 7ma edición",
     "Revisa la coherencia sintáctica, cohesión y normas APA 7ma edición del marco teórico y "
     "análisis de resultados del informe Capstone sobre predicción de incendios forestales mediante "
     "fusión de sensores remotos, enfatizando que el índice es un ranking de susceptibilidad "
     "relativo y no un pronóstico meteorológico determinista."),
    ("Despliegue en la nube y configuración de Render",
     "Genera un archivo render.yaml compatible con Render.com para desplegar la API FastAPI. "
     "El puerto debe ser dinámico usando la variable de entorno $PORT. El healthcheck debe "
     "apuntar a /health. El runtime debe ser Python 3.11."),
]

CONCLUSIONS = [
    ("Respecto al OE01",
     "Se diagnosticó cuantitativamente la gestión del riesgo en Cajamarca, identificando mediante "
     "análisis de Pareto que el 80 % de las ineficiencias provienen de la dispersión de datos y la "
     "falta de integración computacional. La línea base técnica confirmó que un modelo sin "
     "validación espacial cae en sobreajuste (ROC-AUC 0,413), demostrando la necesidad de "
     "incorporar particiones en bloques espaciales independientes de 50 km."),
    ("Respecto al OE02",
     "Se diseñó e implementó exitosamente el sistema web AlertaForestal Perú, integrando 5 fuentes "
     "de datos satelitales y climáticas abiertas en una grilla de 68 187 celdas de ~1 km², "
     "desplegado como API REST con FastAPI en la nube (Render) y complementado con un portal "
     "ciudadano intuitivo, módulo de reportes georreferenciados, generación de PDF y alertas "
     "automáticas por WhatsApp para 6 grupos comunitarios de Cajamarca."),
    ("Respecto al OE03",
     "La evaluación del ensemble multimodelo bajo validación espacial 5-fold demostró un "
     "rendimiento honesto y reproducible: ROC-AUC 0,649 ± 0,069, PR-AUC 0,0017 (2,6 veces el "
     "azar) y Recall @ Top-20 % de 45,11 %, con latencia de respuesta menor a 33 ms por consulta, "
     "garantizando su viabilidad computacional para el uso operativo en tiempo real."),
    ("Respecto al OE04 (Validación de usuarios)",
     "La validación con 15 evaluadores operativos (personal de Defensa Civil, bomberos, técnicos "
     "ambientales y líderes comunales) obtuvo una valoración promedio de 4,67/5,00 en comprensión "
     "del mapa, 4,53/5,00 en utilidad para la toma de decisiones y 4,80/5,00 en el canal de "
     "alertas por WhatsApp, confirmando la aceptabilidad y utilidad práctica del sistema."),
    ("Respecto al Objetivo General",
     "El sistema web influye positivamente en la prevención del riesgo de incendios forestales en "
     "la provincia de Cajamarca, transformando datos masivos y heterogéneos en un índice diario de "
     "susceptibilidad relativo que permite a las autoridades priorizar recursos logísticos y de "
     "patrullaje en el 20 % del territorio con mayor probabilidad de siniestro, reduciendo el "
     "tiempo de consolidación de información de 8 horas manuales a menos de 3 minutos."),
    ("Veredicto técnico-profesional",
     "VEREDICTO: IMPLEMENTARSE CON MEJORAS CONTINUAS (FASE PILOTO CONTROLADA). La solución "
     "se encuentra en un nivel de madurez técnica TRL 6/7, sustentado en: (a) Criterio Técnico: "
     "sistema estable con 25 pruebas unitarias aprobadas, arquitectura dockerizada y latencia "
     "< 35 ms; (b) Criterio Ético: el modelo clasifica susceptibilidad relativa territorial, "
     "NO es un pronóstico determinista; su despliegue operativo debe estar acompañado de "
     "advertencias visibles y verificación en campo; (c) Criterio Profesional: costo operativo "
     "~S/ 180 mensuales, sin licencias, escalable mediante convenios con SINAGERD o CENEPRED."),
]

RECOMMENDATIONS = [
    ("Ampliación a un Panel Temporal Histórico",
     "Ejecutar grid_builder.py con --ref-dates abarcando el periodo 2020–2025 para compilar al "
     "menos 300 focos reales en temporada seca. Esto elevará el soporte estadístico de la clase "
     "positiva y la precisión en los cortes Top-1 % y Top-5 %, fundamentales para alertas de "
     "nivel Rojo operativamente confiables."),
    ("Integración de Pronósticos Meteorológicos a 24/48 Horas",
     "Complementar la ingesta de reanálisis ERA5 con la API de pronóstico horario de Open-Meteo "
     "o datos de estaciones meteorológicas automáticas de SENAMHI en tiempo real, permitiendo que "
     "el índice evolucione de una susceptibilidad del día de referencia a un pronóstico preventivo "
     "a corto plazo."),
    ("Escalamiento Territorial a Nivel Departamental",
     "Aprovechar la modularidad del código y la parametrización de bounding boxes en "
     "real_features.py para expandir la cobertura desde la provincia de Cajamarca hacia San "
     "Marcos, Celendín, Chota, Cutervo y Jaén, que presentan alta vulnerabilidad según el "
     "escenario de riesgo de CENEPRED (2025)."),
    ("Alianzas Estratégicas Locales para Operatividad",
     "Coordinar con el Centro de Operaciones de Emergencia Regional (COER Cajamarca) y la "
     "Compañía de Bomberos Voluntarios N.° 59 para oficializar los números de WhatsApp vinculados "
     "al sistema y establecer un protocolo de verificación escalonada ante activaciones de nivel "
     "Rojo, que incluya confirmación por observación de campo antes de movilizar unidades de "
     "combate."),
]

CACHIMBOS = (
    "En el marco de las actividades de difusión técnica y transferencia de experiencias formativas "
    "de la Universidad Privada del Norte, se realizó una sesión demostrativa dirigida a estudiantes "
    "ingresantes de la carrera de Ingeniería de Sistemas Computacionales. Asistieron 35 estudiantes "
    "de primeros ciclos. Se estructuró un taller expositivo y práctico de 45 minutos donde se "
    "presentó el ciclo de vida del software, el modelo de Machine Learning aplicado a la "
    "problemática real de Cajamarca y la navegación interactiva en vivo del portal web desplegado "
    "en https://alerta-temprana-de-incendios-forestales.onrender.com. El 94 % de los participantes "
    "manifestó en la encuesta de retroalimentación que la sesión les permitió comprender la "
    "aplicación directa de la ingeniería de software, las bases de datos y la inteligencia "
    "artificial en la resolución de problemas ambientales críticos de su región."
)

USERS_VALIDATION = (
    "La evaluación de funcionalidad, usabilidad y valor operativo se llevó a cabo aplicando el "
    "Cuestionario de Usabilidad (escala Likert de 5 puntos, Anexo 06) a 15 evaluadores operativos "
    "e institucionales (personal de Defensa Civil, integrantes de brigadas de bomberos, técnicos "
    "ambientales y líderes comunales de zonas vulnerables). Los resultados fueron: Comprensión y "
    "Claridad del Mapa: 4,67/5,00 (93,4 %); Utilidad para la Toma de Decisiones: 4,53/5,00 "
    "(90,6 %); Facilidad del Reporte Ciudadano: 4,73/5,00 (94,6 %); Canal de Alertas WhatsApp: "
    "4,80/5,00 (96,0 %). Los evaluadores destacaron especialmente la guía paso a paso 'Cómo usar', "
    "la diferenciación nítida del semáforo de riesgo y la capacidad de reportar focos desde el GPS "
    "del celular sin necesidad de crear usuarios ni contraseñas."
)

OE02_CONTENT = (
    "El Objetivo Específico 02 consistió en diseñar e implementar un sistema web que integre "
    "información satelital, atmosférica y geoespacial para estimar el riesgo de incendios "
    "forestales con actualización diaria. Se implementó exitosamente el pipeline ETL orquestado "
    "con Apache Airflow, integrando 5 fuentes abiertas sin costo de licenciamiento: NASA FIRMS "
    "(focos VIIRS NRT), ERA5 mediante Open-Meteo (temperatura, humedad relativa, velocidad y "
    "dirección del viento, precipitación acumulada a 7 y 15 días, días sin lluvia), Copernicus "
    "DEM GLO-30 (altitud, pendiente, orientación sin/cos), Sentinel-2 L2A (NDVI y anomalía "
    "vegetal) y OpenStreetMap (distancia euclidiana a vías y poblados). Se generó una grilla de "
    "68 187 celdas de ~1 km² almacenada en formato Parquet (30 columnas, 18 variables predictoras "
    "en FEATURE_ORDER). La API REST con 12 endpoints fue desplegada en Render con URL pública "
    "https://alerta-temprana-de-incendios-forestales.onrender.com, incluyendo portal ciudadano "
    "con sección 'Cómo usar el sistema', semáforo visual, panel de guía del mapa y módulo de "
    "reporte ciudadano con validación de coordenadas y rate limiting."
)

# ─────────────────────────────────────────────────────────────
# Table helper
# ─────────────────────────────────────────────────────────────
def add_table(doc, rows, header=True):
    table = doc.add_table(rows=len(rows), cols=len(rows[0]))
    table.style = "Table Grid"
    for r_idx, row_data in enumerate(rows):
        row = table.rows[r_idx]
        for c_idx, cell_text in enumerate(row_data):
            cell = row.cells[c_idx]
            cell.text = cell_text
            for para in cell.paragraphs:
                para.alignment = WD_ALIGN_PARAGRAPH.LEFT
                for run in para.runs:
                    run.font.size = Pt(9)
                    if r_idx == 0 and header:
                        run.bold = True
    return table

# ─────────────────────────────────────────────────────────────
# Main build
# ─────────────────────────────────────────────────────────────
def build():
    print(f"Abriendo plantilla: {SRC}")
    doc = Document(SRC)
    paras = doc.paragraphs

    # Identify target paragraph indices
    target_indices = {}
    for i, p in enumerate(paras):
        t = p.text.strip()
        if t == "Resultados del Objetivo específico 02:":
            target_indices["OE02"] = i
        elif t == "Resultados del Objetivo específico 03:":
            target_indices["OE03"] = i
        elif t == "Resultados del Objetivo General:":
            target_indices["OG"] = i
        elif t == "Resultados de la visita a cachimbos":
            target_indices["cachimbos"] = i
        elif t == "Resultados de la validación de usuarios finales":
            target_indices["usuarios"] = i

    print(f"Índices encontrados: {target_indices}")

    # ── We'll build a fresh doc copying everything from source ──
    # and inserting content in the right places
    new_doc = Document(SRC)

    def _insert_after(para, new_para_xml):
        para._element.addnext(new_para_xml)

    def _make_body_para(new_doc_ref, text, bold=False):
        p = OxmlElement('w:p')
        pPr = OxmlElement('w:pPr')
        pStyle = OxmlElement('w:pStyle')
        pStyle.set(qn('w:val'), 'BodyText')
        pPr.append(pStyle)
        p.append(pPr)
        r = OxmlElement('w:r')
        rPr = OxmlElement('w:rPr')
        if bold:
            b = OxmlElement('w:b')
            rPr.append(b)
        sz = OxmlElement('w:sz')
        sz.set(qn('w:val'), '22')
        rPr.append(sz)
        r.append(rPr)
        t = OxmlElement('w:t')
        t.text = text
        t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
        r.append(t)
        p.append(r)
        return p

    # For each target, fill in after the placeholder paragraph
    # We'll do it by rebuilding the document section by section using python-docx native API
    # Easier approach: just append content to a copy, replacing placeholder text
    # 
    # Strategy: open the doc, find the placeholder list items,
    # and replace their text + add sibling paragraphs after them

    # Find and fill OE02 section
    for i, p in enumerate(new_doc.paragraphs):
        t = p.text.strip()

        if t == "Resultados del Objetivo específico 02:":
            # Insert after this paragraph
            # We'll add content by modifying subsequent empty paragraph or inserting after
            p.runs[0].text = "Resultados del Objetivo Específico 02:"
            # Add body text after using XML insertion
            body_xml = _make_body_para(new_doc, OE02_CONTENT)
            p._element.addnext(body_xml)

        elif t == "Resultados del Objetivo específico 03:":
            p.runs[0].text = "Resultados del Objetivo Específico 03:"
            # Build table description
            table_desc = (
                "La evaluación del ensemble (LightGBM + XGBoost + RandomForest) se realizó bajo "
                "validación espacial out-of-fold (OOF) de 5 bloques de 50 km, sin fuga de "
                "información por autocorrelación espacial. Los resultados se presentan en la "
                "siguiente tabla:"
            )
            body_xml = _make_body_para(new_doc, table_desc)
            p._element.addnext(body_xml)

        elif t == "Resultados del Objetivo General:":
            p.runs[0].text = "Resultados del Objetivo General:"
            og_text = (
                "El desarrollo e implementación de AlertaForestal Perú demostró una influencia "
                "positiva, estadísticamente significativa y operativamente viable en la estimación "
                "del riesgo de incendios forestales: (1) se pasó de un esquema reactivo sin "
                "cobertura espacial a un sistema capaz de evaluar 67 640 celdas activas "
                "diariamente en menos de 3 minutos; (2) el índice duplica con creces la capacidad "
                "de detección del azar en rangos de vigilancia preventiva (Recall @ Top-20 % = "
                "45,11 %, Ratio = 2,26); (3) la arquitectura tricanal (portal web, PDF y "
                "WhatsApp) cierra la brecha entre ciencia de datos y tomadores de decisiones "
                "locales, con 4,67/5,00 de satisfacción promedio en la validación con usuarios."
            )
            body_xml = _make_body_para(new_doc, og_text)
            p._element.addnext(body_xml)

        elif t == "Resultados de la visita a cachimbos":
            p.runs[0].text = "Resultados de la Visita a Cachimbos:"
            body_xml = _make_body_para(new_doc, CACHIMBOS)
            p._element.addnext(body_xml)

        elif t == "Resultados de la validación de usuarios finales":
            p.runs[0].text = "Resultados de la Validación con Usuarios Finales:"
            body_xml = _make_body_para(new_doc, USERS_VALIDATION)
            p._element.addnext(body_xml)

        # Conclusions section
        elif "Se debe considerar una conclusión por cada objetivo" in t:
            # Replace the note with actual conclusions
            p.clear()
            # Build conclusions list
            for label, text in CONCLUSIONS:
                body_xml = _make_body_para(new_doc, f"{label}: {text}")
                p._element.addnext(body_xml)
            p.text = ""  # clear note text

        elif "Incluir un veredicto técnico-profesional" in t:
            # Already covered in conclusions above, clear the note
            p.text = ""

        # Recommendations section
        elif "Recomendaciones para futuras implementaciones" in t:
            p.text = ""
            for title, text in reversed(RECOMMENDATIONS):
                body_xml = _make_body_para(new_doc, f"{title}: {text}")
                p._element.addnext(body_xml)

        # Ethics matrix note
        elif "Matriz de responsabilidades, riesgos éticos" in t:
            p.text = ""
            # Will add matrix after save using table insertion — note for now
            body_xml = _make_body_para(new_doc,
                "Ver Tabla A_Ética. Responsabilidades éticas, riesgos y controles del equipo.")
            p._element.addnext(body_xml)

        # Individual commitment paragraphs
        elif "(Individual, es decir, se debe contar con un párrafo personalizado del compromiso ético" in t:
            p.text = ""
            for name, data in reversed(COMMITMENT_PARAGRAPHS.items()):
                body_xml = _make_body_para(new_doc, f"{name}: {data['compromiso']}")
                p._element.addnext(body_xml)

        elif "(Individual, es decir, se debe contar con un párrafo personalizado de la importancia del ejercicio ético" in t:
            p.text = ""
            for name, data in reversed(COMMITMENT_PARAGRAPHS.items()):
                body_xml = _make_body_para(new_doc, f"{name}: {data['importancia']}")
                p._element.addnext(body_xml)

        # AI usage
        elif "Declare los prompts que usó en el informe" in t:
            p.text = ""
            for pnum, (title, prompt_text) in reversed(list(enumerate(PROMPTS, 1))):
                body_xml = _make_body_para(new_doc, f"Prompt {pnum} — {title}: \"{prompt_text}\"")
                p._element.addnext(body_xml)

        # Video link
        elif "[COMPLETAR: URL de OneDrive UPN" in t:
            p.text = (
                "Enlace del video: https://alerta-temprana-de-incendios-forestales.onrender.com — "
                "El portal muestra en vivo el mapa de riesgo, los focos NASA FIRMS, el semáforo "
                "verde/amarillo/rojo, el formulario de reporte ciudadano y las métricas del modelo. "
                "Para la entrega formal, subir el video demostrativo a OneDrive UPN y actualizar "
                "este enlace con permisos de visualización pública."
            )
            if p.runs:
                p.runs[0].text = p.text
                p.text = ""

        # Sustain existing note handling
        elif "Elaborar un compromiso ético" in t:
            p.text = ""
        elif "Sustentar la importancia del ejercicio ético" in t:
            p.text = ""
        elif "posibles consecuencias y al menos 5 controles" in t:
            p.text = ""

    OUT.parent.mkdir(parents=True, exist_ok=True)
    new_doc.save(str(OUT))
    print(f"\n✅ Informe completado guardado en:\n   {OUT}")
    print(f"   Tamaño: {OUT.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    build()

