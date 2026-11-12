# -*- coding: utf-8 -*-
"""Referencias adicionales y anexos del informe."""


NEW_REFERENCES = [
    "Akiba, T., Sano, S., Yanase, T., Ohta, T., & Koyama, M. (2019). Optuna: A next-generation hyperparameter optimization framework. Proceedings of the 25th ACM SIGKDD International Conference on Knowledge Discovery & Data Mining, 2623–2631. https://doi.org/10.1145/3292500.3330701",
    "Astral. (2024). Ruff documentation. https://docs.astral.sh/ruff/",
    "Breiman, L. (2001). Random forests. Machine Learning, 45(1), 5–32. https://doi.org/10.1023/A:1010933404324",
    "Chen, T., & Guestrin, C. (2016). XGBoost: A scalable tree boosting system. Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining, 785–794. https://doi.org/10.1145/2939672.2939785",
    "Congreso de la República del Perú. (2011). Ley N.° 29664, Ley que crea el Sistema Nacional de Gestión del Riesgo de Desastres (SINAGERD). https://www.gob.pe/institucion/pcm/normas-legales/2454640-29664",
    "European Space Agency. (2021). Copernicus DEM: Global and European Digital Elevation Model. https://doi.org/10.5270/ESA-c5d3d65",
    "Green API. (2024). Green API documentation. https://green-api.com/docs/",
    "Hernández-Sampieri, R., & Mendoza, C. P. (2018). Metodología de la investigación: Las rutas cuantitativa, cualitativa y mixta. McGraw-Hill.",
    "ISO/IEC. (2023). ISO/IEC 25010:2023. Systems and software Quality Requirements and Evaluation (SQuaRE) — Product quality model. https://www.iso.org/standard/78176.html",
    "Lundberg, S. M., & Lee, S.-I. (2017). A unified approach to interpreting model predictions. Advances in Neural Information Processing Systems, 30, 4765–4774. https://arxiv.org/abs/1705.07874",
    "Open-Meteo. (2024). Open-Meteo documentation. https://open-meteo.com/en/docs",
    "Roberts, D. R., Bahn, V., Ciuti, S., Boyce, M. S., Elith, J., Guillera-Arroita, G., Hauenstein, S., Lahoz-Monfort, J. J., Schröder, B., Thuiller, W., Warton, D. I., Wintle, B. A., Hartig, F., & Dormann, C. F. (2017). Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure. Ecography, 40(8), 913–929. https://doi.org/10.1111/ecog.02881",
    "Schwaber, K., & Sutherland, J. (2020). The Scrum Guide: The definitive guide to Scrum: The rules of the game. https://scrumguides.org/scrum-guide.html",
    "Wirth, R., & Hipp, J. (2000). CRISP-DM: Towards a standard process model for data mining. Proceedings of the 4th International Conference on the Practical Application of Knowledge Discovery and Data Mining, 29–39.",
]


def get_annexes():
    A = []

    # ------------------------------------------------------------------
    A.append({
        "title": "11.3. Anexo 03: Registro de incidentes",
        "blocks": [
            ("p", "El registro de incidentes documenta los eventos que afectaron la seguridad, la calidad o la operación del sistema, así como la acción correctiva y su estado. Se incluyen incidentes reales identificados durante la revisión técnica y la auditoría del repositorio."),
            ("t", [
                ["ID", "Fecha", "Tipo", "Descripción", "Severidad", "Acción correctiva", "Estado", "Responsable"],
                ["INC-01", "2026-09", "Seguridad", "Archivo .env versionado con claves reales de FIRMS, CDS y Green API", "Alta", "git rm --cached .env; .gitignore; .env.example; rotación de claves", "Mitigado; rotación pendiente", "Seguridad"],
                ["INC-02", "2026-09", "Seguridad", "CORS con allow_origins=*", "Alta", "Lista blanca ALLOWED_ORIGINS y configuración por entorno", "Cerrado", "Backend"],
                ["INC-03", "2026-09", "Seguridad", "Endpoints de alerta sin autenticación", "Alta", "X-API-Key y ADMIN_API_KEY; pruebas de 401", "Cerrado", "Backend"],
                ["INC-04", "2026-09", "Datos", "/risk/today usaba datos simulados o hardcodeados", "Alta", "Caché del dataset puntuado, muestra aleatoria con semilla 42 y stats reales", "Cerrado", "Datos / Backend"],
                ["INC-05", "2026-09", "Modelo", "Fuga de vecindario por groupby(spatial_block_id)", "Alta", "KNN geográfico con cKDTree, k=8, excluyendo la propia celda", "Cerrado", "ML"],
                ["INC-06", "2026-09", "Modelo", "mes_sin y mes_cos constantes con una sola fecha (train/serve skew)", "Media", "Variables eliminadas; FEATURE_ORDER con 18 features", "Cerrado", "ML"],
                ["INC-07", "2026-09", "Modelo", "Métricas infladas por usar risk_score como etiqueta", "Alta", "Etiqueta real FIRMS; ROC-AUC 0.649 y PR-AUC 0.0017", "Cerrado", "ML"],
                ["INC-08", "2026-09", "UI", "El portal afirmaba “24 h” y mostraba porcentajes engañosos", "Media", "Hero honesto, percentil y badge de riesgo", "Cerrado", "Frontend"],
                ["INC-09", "2026-09", "UI", "Inconsistencia entre “Naranja” y “Amarillo”", "Baja", "Unificación a Amarillo en portal y alertas", "Cerrado", "Frontend"],
                ["INC-10", "2026-09", "Operación", "Alertas de WhatsApp sin reintentos", "Media", "Retry con backoff y manejo de errores", "Cerrado", "Backend"],
                ["INC-11", "2026-09", "Calidad", "Archivos muertos y .pyc versionados", "Baja", "Limpieza del índice y de __pycache__", "Cerrado", "QA"],
                ["INC-12", "2026-10", "Calidad", "Ausencia de CI y de pruebas automatizadas", "Alta", "32 pruebas, ruff y GitHub Actions", "Cerrado", "QA"],
            ], 7.0),
            ("n", "Tabla A3.1. Registro de incidentes del proyecto."),
        ],
    })

    # ------------------------------------------------------------------
    A.append({
        "title": "11.4. Anexo 04: Registro de cambios",
        "blocks": [
            ("p", "El registro de cambios resume las versiones relevantes del sistema y su relación con los commits del repositorio. Las fechas corresponden al periodo del proyecto."),
            ("t", [
                ["Versión", "Fecha", "Cambio principal", "Archivos / commit", "Aprobación"],
                ["v1.0", "2026-08", "Versión inicial: README, portal y API básica", "b6176f0", "Acta de inicio"],
                ["v2.0", "2026-09", "Modelo LightGBM, mapa y alertas por WhatsApp", "3a96b62; a471b2f", "Revisión de sprint"],
                ["v2.1", "2026-09", "Corrección de coordenadas y ensemble", "ddda514; 373bae9", "Revisión de sprint"],
                ["v2.2", "2026-10", "Seguridad, honestidad del modelo y soporte multi-fecha", "5f54c85", "Revisión técnica"],
                ["v2.3.0", "2026-10-16", "Reentrenamiento espacial; 18 features; métricas honestas", "models/; data_pipeline/", "Modelo aprobado"],
                ["v2.3.1", "2026-10-21", "Catálogo de 74 historias de usuario", "docs/Historias_de_Usuario.*", "Pendiente"],
                ["v2.3.2", "2026-10-21", "Informe completado hasta 7.6.1, referencias y anexos", "docs/Informe_Proyecto_Final_2026-2_COMPLETADO.docx", "Pendiente"],
            ], 7.5),
            ("n", "Tabla A4.1. Registro de cambios."),
        ],
    })

    # ------------------------------------------------------------------
    A.append({
        "title": "11.5. Anexo 05: Requerimientos para el funcionamiento del producto",
        "blocks": [
            ("p", "Este anexo especifica los requisitos mínimos para instalar, ejecutar y mantener el sistema. Se organizan por hardware, software, datos, configuración, red y seguridad."),
            ("t", [
                ["Categoría", "Requisito", "Valor o detalle"],
                ["Hardware servidor", "CPU, RAM y disco", "2 vCPU, 4 GB de RAM, 20 GB de SSD"],
                ["Hardware cliente", "Equipo del usuario", "PC o smartphone con 2 GB de RAM y navegador actualizado"],
                ["Sistema operativo", "Servidor", "Linux (recomendado) o Windows con Docker"],
                ["Software", "Runtime y contenedores", "Python 3.11, Docker 24+, Docker Compose v2"],
                ["Datos", "Dataset y modelo", "data/dataset.parquet; models/lightgbm_wildfire.pkl; models/model_metadata.json"],
                ["Variables de entorno", "Configuración", "FIRMS_MAP_KEY; ADMIN_API_KEY; ALLOWED_ORIGINS; GREEN_API_INSTANCE_ID; GREEN_API_TOKEN"],
                ["Puertos", "Servicios", "8000 (API); 5050 (portal local); 443 (HTTPS en producción)"],
                ["Red", "Conectividad", "Salida HTTPS a FIRMS, Open-Meteo, Copernicus y OSM; 1 Mbps mínimo por cliente"],
                ["Seguridad", "Controles", "TLS; X-API-Key; CORS restringido; rate limit; respaldos"],
                ["Navegadores", "Compatibilidad", "Chrome, Edge, Firefox y Safari actualizados"],
                ["Licencia", "Uso", "MIT; datos sujetos a las licencias de cada fuente"],
                ["Almacenamiento", "Espacio", "50 MB para datos y 20 MB para el modelo, aproximadamente"],
                ["Arranque", "Tiempo", "Menos de 5 s con el modelo en caché"],
            ], 8.0),
            ("n", "Tabla A5.1. Requerimientos para el funcionamiento del producto."),
        ],
    })

    # ------------------------------------------------------------------
    A.append({
        "title": "11.6. Anexo 06: Instrumentos",
        "blocks": [
            ("p", "Los instrumentos se diseñaron para medir, por un lado, el comportamiento técnico del sistema y, por otro, la percepción de usabilidad de los usuarios. Se aplicarán con consentimiento informado y de forma anónima."),
            ("h", "6.1. Ficha de observación técnica"),
            ("p", "La ficha registra los indicadores verificables del sistema. Cada valor debe acompañarse de la fecha, el comando o la fuente de la medición."),
            ("t", [
                ["N.º", "Indicador", "Unidad", "Valor", "Fuente"],
                ["1", "Fuentes de datos integradas", "N.º", "5", "Pipeline"],
                ["2", "Registros del dataset", "Filas", "68 187", "dataset.parquet"],
                ["3", "Variables predictoras", "N.º", "18", "FEATURE_ORDER"],
                ["4", "Positivos (focos)", "N.º", "45", "target"],
                ["5", "Prevalencia", "%", "0,066", "target"],
                ["6", "Bloques espaciales", "N.º", "32", "spatial_block_id"],
                ["7", "ROC-AUC espacial", "0–1", "0,649", "model_metadata.json"],
                ["8", "PR-AUC", "0–1", "0,0017", "model_metadata.json"],
                ["9", "Recall@Top-10 %", "%", "19,44", "model_metadata.json"],
                ["10", "Latencia /predict", "ms", "32,3", "Prueba de carga"],
                ["11", "Pruebas aprobadas", "N.º", "32/32", "pytest"],
                ["12", "Errores de consola", "N.º", "0", "DevTools"],
            ], 8.5),
            ("n", "Tabla A6.1. Ficha de observación técnica."),
            ("h", "6.2. Cuestionario de usabilidad"),
            ("p", "Instrucciones: marque 1 (muy en desacuerdo), 2 (en desacuerdo), 3 (neutral), 4 (de acuerdo) o 5 (muy de acuerdo). El cuestionario es anónimo y toma aproximadamente 10 minutos."),
            ("t", [
                ["N.º", "Ítem", "1", "2", "3", "4", "5"],
                ["1", "El mapa de riesgo es fácil de entender.", "", "", "", "", ""],
                ["2", "Los colores Verde, Amarillo y Rojo se distinguen con claridad.", "", "", "", "", ""],
                ["3", "La fecha de actualización de los datos es visible.", "", "", "", "", ""],
                ["4", "La información de riesgo es útil para mi trabajo o comunidad.", "", "", "", "", ""],
                ["5", "El portal carga rápido en mi dispositivo.", "", "", "", "", ""],
                ["6", "El formulario de reporte ciudadano es fácil de usar.", "", "", "", "", ""],
                ["7", "Las alertas por WhatsApp son claras y oportunas.", "", "", "", "", ""],
                ["8", "El lenguaje del portal es comprensible.", "", "", "", "", ""],
                ["9", "La información ayuda a priorizar recursos de vigilancia.", "", "", "", "", ""],
                ["10", "Confío en la información presentada como estimación.", "", "", "", "", ""],
                ["11", "Recomendaría el sistema a otras personas o instituciones.", "", "", "", "", ""],
                ["12", "Puedo acceder al sistema desde mi teléfono o computadora.", "", "", "", "", ""],
            ], 8.0),
            ("n", "Tabla A6.2. Cuestionario de usabilidad (escala Likert de 5 puntos)."),
            ("p", "Preguntas abiertas: ¿Qué información le resultó más útil? ¿Qué parte del portal cambiaría? ¿Qué alerta o mensaje le generó dudas? ¿Qué necesitaría para usar el sistema en su comunidad?"),
            ("h", "6.3. Guía de entrevista semiestructurada"),
            ("b", "1. ¿Cómo realiza actualmente el monitoreo de incendios en su zona?"),
            ("b", "2. ¿Qué fuentes de información utiliza y con qué frecuencia?"),
            ("b", "3. ¿Qué dificultades encuentra para anticipar un incendio?"),
            ("b", "4. ¿Cómo se comunican las alertas en su comunidad?"),
            ("b", "5. ¿Qué información necesitaría para priorizar la vigilancia?"),
            ("b", "6. ¿Qué opina del mapa y de los colores Verde/Amarillo/Rojo?"),
            ("b", "7. ¿Qué riesgos ve en usar una estimación de riesgo?"),
            ("b", "8. ¿Qué condiciones deberían cumplirse para adoptar el sistema?"),
            ("h", "6.4. Ficha de validación por juicio de expertos"),
            ("t", [
                ["Criterio", "Descriptor", "Puntaje 1–5", "Observación"],
                ["Claridad", "El ítem se comprende sin ambigüedad.", "", ""],
                ["Pertinencia", "El ítem mide la dimensión o indicador previsto.", "", ""],
                ["Coherencia", "El ítem guarda relación con el objetivo de la investigación.", "", ""],
                ["Relevancia", "El ítem es necesario para evaluar el constructo.", "", ""],
                ["Suficiencia", "El conjunto de ítems cubre las dimensiones del constructo.", "", ""],
            ], 8.0),
            ("n", "Tabla A6.3. Ficha de validación por juicio de expertos."),
        ],
    })

    # ------------------------------------------------------------------
    A.append({
        "title": "11.7. Anexo 07: Validación de instrumentos",
        "blocks": [
            ("p", "La validación se realizará con tres expertos: uno en ingeniería de sistemas, uno en gestión del riesgo de desastres y uno en metodología de la investigación. Cada experto calificará claridad, pertinencia, coherencia, relevancia y suficiencia en una escala de 1 a 5. Con las calificaciones se calculará el coeficiente V de Aiken para cada ítem y el promedio por criterio."),
            ("h", "7.1. Perfil de los expertos"),
            ("t", [
                ["Código", "Especialidad", "Años de experiencia", "Relación con el proyecto"],
                ["E1", "Ingeniería de sistemas / software", "≥ 5", "Revisión de instrumentos técnicos"],
                ["E2", "Gestión del riesgo de desastres", "≥ 5", "Revisión de pertinencia operativa"],
                ["E3", "Metodología de la investigación", "≥ 5", "Revisión de coherencia y validez"],
            ], 8.5),
            ("n", "Tabla A7.1. Perfil de los expertos validadores (datos por completar)."),
            ("h", "7.2. Matriz de validación"),
            ("t", [
                ["Criterio", "E1", "E2", "E3", "V de Aiken", "Resultado"],
                ["Claridad", "", "", "", "", "Pendiente"],
                ["Pertinencia", "", "", "", "", "Pendiente"],
                ["Coherencia", "", "", "", "", "Pendiente"],
                ["Relevancia", "", "", "", "", "Pendiente"],
                ["Suficiencia", "", "", "", "", "Pendiente"],
            ], 8.5),
            ("n", "Tabla A7.2. Matriz de validación por juicio de expertos (completar con las calificaciones)."),
            ("p", "La V de Aiken se calcula como V = (S) / (n × (c − 1)), donde S es la suma de las calificaciones menos el mínimo posible, n es el número de expertos y c es el número de categorías de la escala. Se considera aceptable un valor igual o superior a 0,80. Si un ítem obtiene un valor menor, se revisa y se corrige antes de la aplicación."),
            ("h", "7.3. Confiabilidad"),
            ("p", "Para el cuestionario de usabilidad se aplicará una prueba piloto a 10 participantes con características similares a la población objetivo. Se calculará el coeficiente Alfa de Cronbach con la fórmula estándar. Se considerará aceptable un valor igual o superior a 0,70; entre 0,80 y 0,90 se considerará bueno."),
            ("t", [
                ["Rango de Alfa de Cronbach", "Interpretación"],
                ["< 0,70", "Inaceptable; revisar ítems"],
                ["0,70 – 0,79", "Aceptable"],
                ["0,80 – 0,90", "Bueno"],
                ["> 0,90", "Excelente; revisar redundancia"],
            ], 9.0),
            ("n", "Tabla A7.3. Interpretación del Alfa de Cronbach."),
            ("p", "Para las fichas de observación técnica, la confiabilidad se verificará repitiendo la medición en las mismas condiciones y comparando los valores de latencia, número de registros, cobertura y métricas del modelo. Se reportará la variación porcentual entre repeticiones."),
        ],
    })

    # ------------------------------------------------------------------
    A.append({
        "title": "11.8. Anexo 08: Toma de datos del OE01",
        "blocks": [
            ("p", "La toma de datos del Objetivo Específico 01 se realizó en dos componentes: el diagnóstico del proceso y la línea base técnica del modelo. El registro de causas se elaboró a partir de la observación del proceso, los reportes de incidentes y la revisión de fuentes; la línea base técnica se obtuvo del dataset y de los metadatos del modelo."),
            ("h", "8.1. Registro de causas priorizadas (Pareto)"),
            ("t", [
                ["Código", "Causa", "Frecuencia", "Porcentaje", "Acumulado", "Impacto"],
                ["P1", "Fragmentación y dispersión de datos heterogéneos", "38", "38 %", "38 %", "Alto"],
                ["P2", "Información desactualizada y retraso de reportes", "26", "26 %", "64 %", "Alto"],
                ["P3", "Falta de integración atmosférica y geoespacial", "16", "16 %", "80 %", "Alto"],
                ["P4", "Alertas tardías y poco comprensibles", "12", "12 %", "92 %", "Medio"],
                ["P5", "Dificultad para priorizar recursos", "8", "8 %", "100 %", "Medio"],
                ["Total", "—", "100", "100 %", "—", "—"],
            ], 8.5),
            ("n", "Tabla A8.1. Registro de causas priorizadas del diagnóstico."),
            ("h", "8.2. Procedimiento de toma de datos"),
            ("b", "Periodo: fase de diagnóstico del proyecto (semanas 1–4)."),
            ("b", "Fuentes: registro de incidentes del proyecto, reportes de CENEPRED e INDECI, revisión de fuentes satelitales y observación del proceso de monitoreo."),
            ("b", "Unidad de análisis: incidencia operativa o causa de ineficiencia del proceso."),
            ("b", "Instrumento: ficha de registro de causas y diagrama de Pareto."),
            ("b", "Responsable: equipo de análisis de datos y gestión de riesgos."),
            ("b", "Control de calidad: doble revisión de la clasificación y verificación del acumulado (100 %)."),
            ("h", "8.3. Línea base técnica"),
            ("t", [
                ["Indicador", "Valor", "Fuente"],
                ["Registros del dataset", "68 187", "data/dataset.parquet"],
                ["Columnas", "30", "data/dataset.parquet"],
                ["Variables del modelo", "18", "app/model.py"],
                ["Positivos", "45", "target"],
                ["Prevalencia", "0,066 %", "target"],
                ["Bloques espaciales", "32", "spatial_block_id"],
                ["ROC-AUC espacial", "0,649 ± 0,069", "models/model_metadata.json"],
                ["PR-AUC", "0,0017", "models/model_metadata.json"],
                ["Recall@Top-10 %", "19,44 %", "models/model_metadata.json"],
                ["Recall@Top-20 %", "45,11 %", "models/model_metadata.json"],
            ], 9.0),
            ("n", "Tabla A8.2. Línea base técnica del OE01."),
        ],
    })

    # ------------------------------------------------------------------
    A.append({
        "title": "11.9. Anexo 09: Entregables de la metodología",
        "blocks": [
            ("p", "Los entregables se organizaron por fase de la metodología híbrida. La tabla indica la ubicación en el repositorio y el estado de cada producto."),
            ("t", [
                ["Fase", "Entregable", "Ubicación", "Estado"],
                ["Inicio", "Acta, stakeholders y cronograma", "docs/", "Completado"],
                ["Requisitos", "74 historias de usuario y backlog", "docs/Historias_de_Usuario.md; .csv", "Completado"],
                ["Datos", "Diccionario, dataset y ETL", "data/; data_pipeline/", "Completado"],
                ["Modelo", "Scripts, modelo, metadatos y métricas", "data_pipeline/train_model.py; models/", "Completado"],
                ["API", "Endpoints, OpenAPI y seguridad", "app/", "Completado"],
                ["Portal", "HTML, CSS, JavaScript y mapa", "web/", "Completado"],
                ["Pruebas", "32 pruebas y CI", "tests/; .github/workflows/ci.yml", "Completado"],
                ["Despliegue", "Docker, compose y manual", "Dockerfile; docker-compose.yml; README.md", "Completado"],
                ["Gestión", "Riesgos, incidentes y cambios", "docs/; anexos 03 y 04", "Completado"],
                ["Informe", "Documento final y anexos", "docs/Informe_Proyecto_Final_2026-2_COMPLETADO.docx", "En revisión"],
            ], 8.0),
            ("n", "Tabla A9.1. Entregables de la metodología."),
        ],
    })

    # ------------------------------------------------------------------
    A.append({
        "title": "11.10. Anexo 10: Carta de presentación",
        "blocks": [
            ("p", "La carta se presenta como modelo para solicitar acceso a información pública, colaboración o validación con municipios, oficinas de Gestión del Riesgo de Desastres, bomberos, brigadas o comunidades organizadas. El sistema es abierto, no tiene fines comerciales y no representa a una entidad."),
            ("p", "Cajamarca, ____ de ____________ de 2026"),
            ("p", "Señor(a) ____________________________________"),
            ("p", "Cargo: ______________________________________"),
            ("p", "Institución: _________________________________"),
            ("p", "Presente. -"),
            ("p", "Asunto: Presentación del proyecto “Sistema web para la predicción de incendios forestales mediante fusión de sensores remotos y variables atmosféricas en la provincia de Cajamarca” y solicitud de colaboración para validación."),
            ("p", "De mi consideración:"),
            ("p", "Por medio de la presente, el equipo de estudiantes de la carrera de Ingeniería de Sistemas Computacionales de la Universidad Privada del Norte tiene el agrado de presentar el proyecto AlertaForestal Perú, una plataforma abierta y gratuita que estima un índice diario de susceptibilidad a incendios forestales en la provincia de Cajamarca. El sistema integra focos de calor satelitales, variables atmosféricas, topografía, vegetación y proximidad a vías y poblados, y presenta el resultado en un mapa interactivo con tres niveles de referencia: Verde, Amarillo y Rojo."),
            ("p", "El proyecto tiene fines académicos y sociales. No representa a ninguna entidad, no comercializa datos ni servicios y no sustituye los protocolos oficiales de prevención, respuesta o alerta. Su propósito es aportar información complementaria para la vigilancia preventiva y la priorización de recursos."),
            ("p", "En ese marco, solicitamos su colaboración para: (a) acceder a información pública disponible sobre incendios y condiciones ambientales de la zona; (b) participar en una entrevista o encuesta de usabilidad; y (c) validar, si corresponde, la utilidad del sistema en su ámbito de competencia. La participación es voluntaria, anónima y puede retirarse en cualquier momento."),
            ("p", "Agradecemos de antemano su atención y quedamos a disposición para ampliar la información o realizar una demostración del sistema."),
            ("p", "Atentamente,"),
            ("p", "____________________________________"),
            ("p", "CAMPOS SILVA, Fran Antony"),
            ("p", "____________________________________"),
            ("p", "CHAVEZ MARIN, Marco Antonio"),
            ("p", "____________________________________"),
            ("p", "GUEVARA FORES, Luis Miguel"),
            ("p", "____________________________________"),
            ("p", "LLANOS MENDOZA, Lenis Jhonatan"),
            ("p", "____________________________________"),
            ("p", "MEDINA CARUAJULCA, Segundo Daniel"),
            ("p", "DNI: __________________  Teléfono: __________________  Correo: __________________"),
            ("n", "Nota: completar los datos institucionales y de contacto antes de la presentación. La carta puede adaptarse para una municipalidad, una oficina de GRD, una compañía de bomberos, una ronda campesina o una ONG."),
        ],
    })

    return A
