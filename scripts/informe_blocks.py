# -*- coding: utf-8 -*-
"""Bloques de contenido para completar el informe CAPSTONE.

Cada bloque es una tupla:
  ("p", texto)          párrafo normal
  ("b", texto)          viñeta
  ("h", texto)          subtítulo en negrita
  ("t", filas, tamaño)  tabla (la primera fila es cabecera)
  ("n", texto)          nota en cursiva
"""


def get_blocks():
    B = {}

    # ------------------------------------------------------------------
    # RESUMEN / ABSTRACT
    # ------------------------------------------------------------------
    B["resumen"] = [
        ("p", "El presente proyecto tuvo como objetivo determinar la influencia de un sistema web basado en sensores remotos y variables atmosféricas en la estimación del riesgo de incendios forestales en la provincia de Cajamarca. Para ello se diseñó e implementó AlertaForestal Perú, una plataforma abierta que integra focos de calor de NASA FIRMS (VIIRS), variables atmosféricas de ERA5 mediante Open-Meteo, elevación y pendiente de Copernicus DEM GLO-30, vegetación de Sentinel-2 L2A y proximidad a vías y poblados de OpenStreetMap. Con estas fuentes se construyó una grilla de 68 187 celdas de aproximadamente 1 km² y 18 variables predictoras. Se entrenó un ensamble de LightGBM, XGBoost y Random Forest con validación espacial 5-fold out-of-fold por bloques de 50 km, optimización de hiperparámetros con Optuna y análisis de interpretabilidad con SHAP."),
        ("p", "Los resultados obtenidos sin fuga espacial alcanzaron un ROC-AUC de 0,649 ± 0,069 y un PR-AUC de 0,0017 frente a una prevalencia de 0,066 %. El recall en el Top-1 % de celdas fue 1,05 %, en el Top-5 % 5,05 %, en el Top-10 % 19,44 % y en el Top-20 % 45,11 %; estos dos últimos valores representan entre 1,9 y 2,3 veces lo esperado por azar. El sistema se desplegó como API FastAPI con portal web ciudadano, mapa interactivo, reportes ciudadanos georreferenciados, alertas por WhatsApp y reportes PDF. Cuenta con 32 pruebas automatizadas, integración continua, análisis estático y contenedor Docker. Se concluye que la solución es técnicamente viable y útil como herramienta de priorización preventiva, pero no constituye un pronóstico determinista ni sustituye la verificación en campo; su valor operativo depende de comunicar el índice como un ranking relativo y de mantener una mejora continua de datos y validación."),
    ]
    B["palabras"] = [
        ("p", "Palabras clave: incendios forestales; alerta temprana; sensores remotos; aprendizaje automático; Cajamarca."),
    ]
    B["abstract"] = [
        ("p", "This project aimed to determine the influence of a web-based system built on remote sensors and atmospheric variables on wildfire risk estimation in the province of Cajamarca, Peru. We designed and implemented AlertaForestal Perú, an open platform that integrates NASA FIRMS (VIIRS) heat detections, ERA5 atmospheric variables through Open-Meteo, Copernicus DEM GLO-30 elevation and slope, Sentinel-2 L2A vegetation, and OpenStreetMap road and settlement proximity. These sources produced a grid of 68,187 cells of approximately 1 km² and 18 predictor variables. An ensemble of LightGBM, XGBoost and Random Forest was trained with a 5-fold spatial out-of-fold validation using 50 km blocks, Optuna hyperparameter optimization and SHAP interpretability analysis."),
        ("p", "Honest, leakage-free results reached a ROC-AUC of 0.649 ± 0.069 and a PR-AUC of 0.0017 against a prevalence of 0.066 %. Recall at the top 1 % of cells was 1.05 %, at the top 5 % 5.05 %, at the top 10 % 19.44 % and at the top 20 % 45.11 %; the last two figures are 1.9 to 2.3 times the random expectation. The system was deployed as a FastAPI service with a public web portal, interactive map, georeferenced citizen reports, WhatsApp alerts and PDF reports. It includes 32 automated tests, continuous integration, static analysis and a Docker container. We conclude that the solution is technically feasible and useful as a preventive prioritization tool, but it is not a deterministic forecast and does not replace field verification; its operational value depends on communicating the index as a relative ranking and on continuous data and validation improvements."),
    ]
    B["keywords"] = [
        ("p", "Keywords: wildfires; early warning; remote sensing; machine learning; Cajamarca."),
    ]

    # ------------------------------------------------------------------
    # 4.2 FUENTES DE DATOS
    # ------------------------------------------------------------------
    B["fuentes_datos"] = [
        ("p", "El sistema utiliza fuentes de datos abiertas y servicios externos. La mayor parte del pipeline no requiere credenciales; solo la descarga de focos de NASA FIRMS utiliza una clave gratuita que se mantiene en el backend. Las fuentes se citan conforme a sus licencias: NASA FIRMS (NASA, 2024), Open-Meteo (2024), Copernicus DEM (European Space Agency, 2021), Sentinel-2 (European Space Agency, 2024) y OpenStreetMap (OpenStreetMap Foundation, 2024). La Tabla 4.1 resume las fuentes, las variables utilizadas, su resolución y las precauciones adoptadas."),
        ("t", [
            ["Fuente", "Variables o uso", "Resolución y frecuencia", "Acceso", "Limitación"],
            ["NASA FIRMS (VIIRS/MODIS)", "Focos de calor y anomalías térmicas; etiqueta target del modelo", "~375 m (VIIRS); pasadas diarias", "API con clave gratuita", "No confirma un incendio en campo; puede haber falsos positivos y vacíos por nubosidad."],
            ["ERA5 vía Open-Meteo", "Temperatura a 2 m, humedad relativa, viento, lluvia, días sin lluvia y variables rezagadas", "~9–25 km; horaria/diaria", "API abierta", "Resolución mayor que la grilla; se interpola y se documenta la incertidumbre."],
            ["Copernicus DEM GLO-30", "Elevación, pendiente y orientación", "30 m", "Descarga abierta (AWS)", "Modelo digital del terreno; no describe la cobertura vegetal."],
            ["Sentinel-2 L2A (STAC AWS)", "NDVI y anomalía de NDVI", "10–20 m; revisita ~5 días", "STAC abierto", "Nubosidad y disponibilidad temporal variable."],
            ["OpenStreetMap Overpass", "Distancia a vías y a centros poblados", "Vectorial", "API abierta con uso justo", "Cobertura variable; se registra la fecha de descarga."],
            ["CENEPRED / INEI", "Contexto de riesgo, población y vivienda", "Documentos y capas", "Público", "No se usa como variable del modelo; solo como contexto y validación."],
        ], 7.5),
        ("n", "Tabla 4.1. Fuentes de datos y servicios externos del sistema."),
    ]

    # ------------------------------------------------------------------
    # 4.3 HARDWARE
    # ------------------------------------------------------------------
    B["hardware"] = [
        ("p", "El proyecto se ejecutó con equipos de cómputo personales y un servidor virtual de bajo costo. La Tabla 4.2 presenta los requerimientos de hardware utilizados y los mínimos recomendados para replicar el sistema."),
        ("t", [
            ["Equipo", "Uso", "Requisito mínimo"],
            ["Laptop o PC de desarrollo", "Preparación de datos, entrenamiento y pruebas", "4 núcleos, 8 GB de RAM, 20 GB de disco libre"],
            ["Servidor o máquina virtual", "API, modelo y portal", "2 vCPU, 4 GB de RAM, 20 GB de SSD"],
            ["Teléfono inteligente", "Consulta del portal y reporte ciudadano", "Navegador actualizado, GPS y cámara"],
            ["GPS de campo (opcional)", "Verificación de coordenadas y validación", "Precisión de al menos 10 m"],
            ["Conectividad", "Descarga de datos y acceso al portal", "1 Mbps para cliente; 5 Mbps para servidor"],
        ], 8.5),
        ("n", "Tabla 4.2. Hardware utilizado y requerimientos mínimos."),
    ]

    # ------------------------------------------------------------------
    # 4.5–4.8
    # ------------------------------------------------------------------
    B["metodologias"] = [
        ("p", "Para seleccionar el marco de trabajo se compararon cuatro enfoques ágiles y un marco de proceso de ciencia de datos. Scrum aporta iteraciones cortas y entregables verificables; Kanban facilita el flujo continuo y la gestión del trabajo pendiente; XP refuerza las pruebas y la integración continua; CRISP-DM organiza el ciclo de vida de los datos en seis fases y pone énfasis en la comprensión del negocio y en la evaluación. La Tabla 4.3 sintetiza la comparación."),
        ("t", [
            ["Marco", "Fortalezas", "Limitaciones", "Uso en el proyecto"],
            ["CRISP-DM", "Ciclo de vida completo de datos; fases claras; evaluación explícita", "Poco ágil si se aplica de forma rígida", "Columna vertebral para datos, modelado y evaluación"],
            ["Scrum", "Iteraciones, roles definidos, entregables y revisiones", "Requiere disponibilidad del equipo y del cliente", "Gestión de sprints de desarrollo"],
            ["Kanban", "Flujo continuo, límites de trabajo en curso, flexibilidad", "Menor planificación de largo plazo", "Mantenimiento y atención de incidencias"],
            ["XP", "Pruebas automatizadas, integración continua, refactorización", "Exigente en disciplina y tiempo", "Aplicado parcialmente: pytest, CI y revisión de código"],
            ["ISO/IEC 25010", "Modelo de calidad del producto y criterios verificables", "No es un proceso de desarrollo", "Evaluación de calidad y auditorías"],
            ["Modelo C4", "Vistas de arquitectura desde contexto hasta código", "Requiere mantenimiento de diagramas", "Documentación de arquitectura"],
        ], 8.0),
        ("n", "Tabla 4.3. Comparación de metodologías y estándares de ingeniería."),
        ("p", "Se adoptó un enfoque híbrido: CRISP-DM para el ciclo de vida de los datos y del modelo, y Scrum para la construcción del producto software. Este enfoque permitió alternar entregables de datos (dataset, features, modelo) con entregables de software (API, portal, pruebas) sin perder trazabilidad. La selección se justifica porque el proyecto combina una componente experimental —con métricas que deben evaluarse sin fuga espacial— y una componente de producto —con requisitos de usabilidad, seguridad y despliegue—."),
    ]

    B["seleccion_herramientas"] = [
        ("p", "La selección de herramientas se realizó por requisito y no por preferencia. La Tabla 4.4 relaciona cada necesidad técnica con la herramienta adoptada y su justificación."),
        ("t", [
            ["Requisito", "Herramienta seleccionada", "Justificación"],
            ["Procesamiento de datos y modelado", "Python 3.11, pandas, NumPy, scikit-learn", "Ecosistema maduro, gratuito y reproducible"],
            ["Series geoespaciales", "GeoPandas, Shapely, rasterio, SciPy", "Lectura de rásteres, geometrías y cálculo de distancias"],
            ["Modelo predictivo", "LightGBM, XGBoost, Random Forest", "Buen desempeño en datos tabulares y bajo costo de inferencia"],
            ["Optimización e interpretabilidad", "Optuna, SHAP", "Búsqueda de hiperparámetros y explicación de predicciones"],
            ["API y validación", "FastAPI, Uvicorn, Pydantic", "API REST con OpenAPI, tipado y alto rendimiento"],
            ["Orquestación", "Apache Airflow", "DAG diario con tareas de descarga, grilla, entrenamiento y alertas"],
            ["Almacenamiento", "Parquet/CSV (PostgreSQL/PostGIS opcional)", "Simplicidad de despliegue; PostGIS queda para despliegues institucionales"],
            ["Portal y mapas", "HTML, CSS, JavaScript, Leaflet", "Portal ligero, sin instalación y compatible con móviles"],
            ["Reportes", "ReportLab", "Generación de PDF ejecutivos"],
            ["Alertas", "Green API (WhatsApp), APScheduler", "Canal comunitario y envío programado"],
            ["Calidad", "pytest, ruff, GitHub Actions, Locust", "Pruebas, lint, integración continua y carga"],
            ["Despliegue", "Docker, Docker Compose", "Portabilidad y reproducibilidad"],
        ], 8.0),
        ("n", "Tabla 4.4. Selección fundamentada de herramientas."),
        ("n", "Nota de implementación: la versión final del prototipo almacena los datos en archivos Parquet/CSV y utiliza un portal HTML/CSS/JS con Leaflet. PostgreSQL/PostGIS y Streamlit se mantienen como alternativas de despliegue institucional, no como dependencias obligatorias del sistema."),
    ]

    B["uso_herramientas"] = [
        ("p", "El uso de las herramientas se organizó en tres momentos verificables:"),
        ("b", "Recolección: los scripts fetch_firms.py, real_features.py y grid_builder.py descargan y validan las fuentes; se verifican el bounding box de Cajamarca, el rango de fechas, los duplicados y los valores faltantes antes de incorporar los registros."),
        ("b", "Análisis: se realizó análisis exploratorio, correlación de variables, revisión de la distribución del target y análisis de importancia con SHAP; las métricas se calcularon con validación espacial y no con una partición aleatoria."),
        ("b", "Procesamiento: el pipeline se orquestó con Airflow y se almacenó en Parquet; el modelo, sus metadatos y los umbrales se versionaron en models/. Cada ejecución deja un registro de fecha, versión y métricas."),
        ("b", "Buenas prácticas: las credenciales se gestionan con variables de entorno; no se versiona .env; los datos personales se minimizan; las fuentes se citan y se respetan sus licencias."),
    ]

    B["requisitos_servidor"] = [
        ("p", "Los requisitos se separaron por cliente, servidor, datos y seguridad para facilitar la replicación del sistema en otros entornos."),
        ("t", [
            ["Categoría", "Requisito"],
            ["Cliente", "Navegador Chrome, Edge, Firefox o Safari actualizado; JavaScript habilitado; 2 GB de RAM; pantalla desde 360 px; conexión de al menos 1 Mbps"],
            ["Servidor", "Linux o Windows; Python 3.11; Docker 24+; 2 vCPU; 4 GB de RAM; 20 GB de SSD; puertos 8000 (API) y 5050 (portal local)"],
            ["Datos", "data/dataset.parquet (68 187 filas × 30 columnas); models/lightgbm_wildfire.pkl; models/model_metadata.json"],
            ["Variables de entorno", "FIRMS_MAP_KEY (opcional), ADMIN_API_KEY, ALLOWED_ORIGINS, GREEN_API_INSTANCE_ID y GREEN_API_TOKEN (opcionales)"],
            ["Seguridad", "TLS en producción; X-API-Key en endpoints de alerta; CORS restringido; rate limit en reportes ciudadanos"],
            ["Accesibilidad", "Contraste suficiente, textos alternativos, navegación por teclado y lenguaje claro"],
        ], 8.5),
        ("n", "Tabla 4.5. Requisitos de usuario final, servidor, datos y seguridad."),
    ]

    # ------------------------------------------------------------------
    # 5.6 REQUERIMIENTOS E HISTORIAS
    # ------------------------------------------------------------------
    B["requerimientos"] = [
        ("p", "Los requerimientos se derivaron del diagnóstico y se organizaron en funcionales (RF) y no funcionales (RNF). El catálogo completo de 74 historias de usuario —66 HU y 8 RNF—, con criterios de aceptación, prioridad MoSCoW y trazabilidad, se encuentra en docs/Historias_de_Usuario.md y en la versión tabular docs/Historias_de_Usuario.csv. La distribución es 33 Must, 30 Should y 11 Could, agrupadas en 14 épicas."),
        ("t", [
            ["ID", "Requerimiento funcional", "Prioridad", "Trazabilidad"],
            ["RF-01", "Descargar focos de calor de NASA FIRMS y usarlos como etiqueta", "Must", "fetch_firms.py; data_pipeline/"],
            ["RF-02", "Integrar variables atmosféricas de ERA5/Open-Meteo", "Must", "real_features.py"],
            ["RF-03", "Integrar DEM, NDVI y proximidad a vías y poblados", "Must", "real_features.py; grid_builder.py"],
            ["RF-04", "Construir una grilla de ~1 km² para Cajamarca", "Must", "grid_builder.py"],
            ["RF-05", "Entrenar y versionar un modelo de riesgo", "Must", "train_model.py; models/"],
            ["RF-06", "Publicar predicciones y metadatos mediante API REST", "Must", "app/main.py; /predict"],
            ["RF-07", "Ofrecer un portal ciudadano sin registro", "Must", "web/index.html"],
            ["RF-08", "Visualizar el riesgo en un mapa interactivo", "Must", "web/app.js; /risk/today"],
            ["RF-09", "Permitir reportes ciudadanos georreferenciados", "Should", "/report/citizen; /report/recent"],
            ["RF-10", "Enviar alertas y resumen diario por WhatsApp", "Should", "app/scheduler.py; app/whatsapp_alerts.py"],
            ["RF-11", "Generar reportes ejecutivos en PDF", "Should", "/report/pdf; app/pdf_generator.py"],
            ["RF-12", "Exponer estado, importancia de variables y matriz social", "Could", "/alert/status; /model/importance; /social/matrix"],
        ], 7.5),
        ("n", "Tabla 5.1. Requerimientos funcionales principales."),
        ("t", [
            ["ID", "Requerimiento no funcional", "Métrica o criterio"],
            ["RNF-01", "Rendimiento", "/predict ≈ 32 ms; /risk/today 35–474 ms según el límite solicitado"],
            ["RNF-02", "Disponibilidad", "Healthcheck /health; reinicio automático del contenedor"],
            ["RNF-03", "Seguridad", "API key, CORS restringido, rate limit y validación de coordenadas"],
            ["RNF-04", "Usabilidad", "Semáforo Verde/Amarillo/Rojo, percentil y fecha de actualización visibles"],
            ["RNF-05", "Mantenibilidad", "32 pruebas, ruff, CI y módulos desacoplados"],
            ["RNF-06", "Portabilidad", "Docker, Python 3.11 y datos abiertos"],
        ], 8.0),
        ("n", "Tabla 5.2. Requerimientos no funcionales."),
        ("p", "La priorización MoSCoW se utilizó para delimitar el producto mínimo viable: los requerimientos Must corresponden a la ingestión, el modelo, la API, el portal y la seguridad; los Should incorporan reportes ciudadanos, alertas y PDF; los Could quedan como mejoras de transparencia y explotación de datos. Cada historia incluye criterios de aceptación verificables y una columna de trazabilidad con el módulo o endpoint que la implementa."),
    ]

    # ------------------------------------------------------------------
    # 5.12 GESTIÓN DE RIESGOS
    # ------------------------------------------------------------------
    B["roles_riesgos"] = [
        ("p", "Los roles se asignaron de forma rotativa entre los cinco integrantes del equipo. La Tabla 5.3 describe las responsabilidades y el entregable principal de cada rol; la asignación nominal se registra en el acta de constitución del proyecto (Anexo 09)."),
        ("t", [
            ["Rol", "Responsabilidad", "Entregable principal"],
            ["Líder de proyecto / Scrum Master", "Planificación, gestión de riesgos, comunicación y seguimiento", "Cronograma, actas y matriz de riesgos"],
            ["Ingeniero/a de datos", "ETL, calidad de datos, orquestación y almacenamiento", "Dataset, DAG y diccionario de datos"],
            ["Científico/a de datos", "Features, modelo, validación espacial, métricas y SHAP", "Modelo versionado y metadatos"],
            ["Desarrollador/a backend", "API, seguridad, alertas, PDF y pruebas de integración", "Servicio FastAPI y pruebas"],
            ["Desarrollador/a frontend", "Portal, mapas, accesibilidad y reporte ciudadano", "Portal web y evidencias de navegador"],
            ["QA / seguridad", "Pruebas, auditorías, lint, CI y revisión de dependencias", "Informe de pruebas y pipeline CI"],
        ], 8.5),
        ("n", "Tabla 5.3. Roles y responsabilidades del plan de gestión de riesgos."),
    ]

    B["presupuesto_riesgos"] = [
        ("p", "El presupuesto se estimó con precios de referencia de servicios cloud y conectividad en Perú. Los equipos de cómputo son de propiedad del equipo, por lo que se registran como recurso valorizado y no como desembolso. La Tabla 5.4 presenta el detalle."),
        ("t", [
            ["Rubro", "Descripción", "Cantidad", "Costo unitario (S/)", "Costo total (S/)"],
            ["Equipos de cómputo", "5 laptops de desarrollo (valorizadas)", "5", "3 000", "15 000"],
            ["Internet", "Servicio de banda ancha durante 6 meses", "6", "100", "600"],
            ["Servidor virtual", "2 vCPU, 4 GB RAM, 20 GB SSD, 6 meses", "6", "70", "420"],
            ["Dominio", "Dominio .pe por un año", "1", "120", "120"],
            ["Certificado TLS", "Let's Encrypt", "1", "0", "0"],
            ["Datos y APIs", "NASA FIRMS, Open-Meteo, Copernicus, Sentinel-2, OSM", "1", "0", "0"],
            ["Validación y capacitación", "Materiales y sesiones con actores locales", "1", "300", "300"],
            ["Imprevistos", "10 % del presupuesto operativo", "1", "144", "144"],
            ["Total operativo", "Sin equipos de cómputo", "", "", "1 584"],
            ["Total valorizado", "Incluye equipos de cómputo", "", "", "16 584"],
        ], 8.0),
        ("n", "Tabla 5.4. Presupuesto estimado del proyecto (S/)."),
    ]

    B["matriz_riesgos"] = [
        ("p", "La matriz de riesgos prioriza los eventos que podrían afectar el alcance, la calidad o la seguridad del sistema. La severidad se calcula como probabilidad × impacto en una escala de 1 a 5."),
        ("t", [
            ["ID", "Riesgo", "Prob.", "Impacto", "Severidad", "Mitigación", "Responsable"],
            ["R-01", "Datos incompletos, inconsistentes o desactualizados", "4", "4", "16", "Validación de esquema, registro de faltantes, reintentos y copias históricas", "Datos"],
            ["R-02", "Bajo desempeño por desbalance extremo (45 positivos)", "5", "5", "25", "Pesos de clase acotados, validación espacial, métricas top-k y PR-AUC", "ML"],
            ["R-03", "Falsos positivos o falsos negativos", "4", "5", "20", "Comunicar el índice como estimación; percentil y fecha visibles; verificación humana", "ML / Producto"],
            ["R-04", "Exposición de claves o credenciales", "3", "5", "15", "Variables de entorno, .env no versionado, rotación y revisión de historial", "Seguridad"],
            ["R-05", "Caída de servicios externos o del servidor", "3", "3", "9", "Reintentos, healthcheck, monitoreo y respaldos", "Backend"],
            ["R-06", "Bajo uso por parte de la comunidad", "3", "4", "12", "Portal ligero, WhatsApp, lenguaje claro y validación con usuarios", "Producto"],
            ["R-07", "Interpretación de la alerta como confirmación de incendio", "4", "4", "16", "Etiquetas “riesgo estimado” y “alerta preventiva”; no usar como certeza", "Producto"],
            ["R-08", "Retraso en el cronograma académico", "3", "3", "9", "Backlog priorizado, sprints semanales y revisiones", "PM"],
        ], 7.5),
        ("n", "Tabla 5.5. Matriz de riesgos del proyecto."),
    ]

    # ------------------------------------------------------------------
    # 5.13 INTERESADOS (tablas existentes)
    # ------------------------------------------------------------------
    B["stakeholders"] = [
        ["Público general y comunidades rurales", "Ciudadanía", "Beneficiario primario", "Acceso libre, información clara y sin registro", "Uso y difusión", "Partidario", "Bajo", "Alto"],
        ["Rondas campesinas y comités vecinales", "Organizaciones comunitarias", "Usuario y difusor", "Alertas simples por WhatsApp y reporte de focos", "Operación", "Partidario", "Medio", "Alto"],
        ["Bomberos, brigadistas y Defensa Civil", "Entidades de respuesta", "Usuario operativo", "Mapas, coordenadas y reportes PDF", "Validación y operación", "Partidario", "Medio", "Alto"],
        ["Municipalidades y oficinas de GRD", "Gobiernos locales", "Aliado potencial", "API, reportes y capacitación", "Planificación", "Neutral", "Medio", "Medio"],
        ["INDECI, SERFOR y CENEPRED", "Entidades técnicas", "Aliado técnico", "Datos, validación y buenas prácticas", "Prevención", "Neutral", "Alto", "Medio"],
        ["Universidad Privada del Norte", "Academia", "Cliente académico", "Informe, código, demo y rigor metodológico", "Todas", "Partidario", "Alto", "Alto"],
        ["ONG, academia y periodistas", "Sociedad civil", "Usuario secundario", "Datos abiertos y transparencia", "Difusión", "Partidario", "Bajo", "Medio"],
        ["Desarrolladores open source", "Comunidad técnica", "Colaborador", "Repositorio, issues y CI", "Mantenimiento", "Partidario", "Bajo", "Medio"],
        ["NASA, Copernicus y OSM", "Proveedores de datos", "Fuente externa", "Disponibilidad y licencias", "Operación", "Neutral", "Alto", "Bajo"],
        ["Grupos de WhatsApp", "Canal comunitario", "Canal de difusión", "Mensajes claros y baja frecuencia", "Operación", "Partidario", "Bajo", "Alto"],
    ]

    B["impacto_stakeholders"] = [
        ["Público general", "Obtiene acceso gratuito a un mapa de riesgo comprensible y puede reportar focos sin registro."],
        ["Comunidades organizadas", "Reciben un insumo para autoorganizar la vigilancia y difundir alertas preventivas por sus propios canales."],
        ["Bomberos y brigadistas", "Pueden priorizar la verificación en zonas con mayor score, pero deben confirmar en campo antes de movilizar recursos."],
        ["Municipalidades y GRD", "Disponen de información territorial para planificación preventiva; el sistema no reemplaza sus protocolos ni decisiones."],
        ["INDECI, SERFOR y CENEPRED", "Pueden reutilizar datos y metodología; no se establece dependencia ni integración oficial."],
        ["Universidad", "Obtiene evidencia académica, código reproducible y un caso de estudio con métricas honestas."],
        ["ONG y periodistas", "Acceden a datos abiertos y a una declaración explícita de limitaciones para evitar titulares alarmistas."],
        ["Desarrolladores", "Pueden replicar, auditar y adaptar el sistema para otras regiones con la licencia MIT."],
        ["Proveedores de datos", "Su uso se realiza conforme a licencias y buenas prácticas de citación."],
        ["Grupos de WhatsApp", "Reciben mensajes breves y periódicos; la comunidad administra altas, bajas y moderación."],
    ]

    # ------------------------------------------------------------------
    # 5.14 PRESUPUESTO DEL PROYECTO
    # ------------------------------------------------------------------
    B["presupuesto_proyecto"] = [
        ("p", "El costo operativo del prototipo es bajo porque utiliza datos abiertos, software libre y planes gratuitos. La Tabla 5.6 resume la distribución del presupuesto operativo; el detalle por rubro se presentó en la Tabla 5.4."),
        ("t", [
            ["Categoría", "Monto (S/)", "Participación"],
            ["Infraestructura y conectividad", "1 020", "64,4 %"],
            ["Dominio y certificados", "120", "7,6 %"],
            ["Validación y capacitación", "300", "18,9 %"],
            ["Imprevistos", "144", "9,1 %"],
            ["Total operativo", "1 584", "100 %"],
        ], 9.0),
        ("n", "Tabla 5.6. Distribución del presupuesto operativo."),
        ("p", "El beneficio económico no se plantea como un ahorro contable directo, sino como una mejora en la asignación de recursos: el sistema permite priorizar la vigilancia en el Top-10 % o Top-20 % de celdas con mayor score, en lugar de monitorear de forma indiscriminada 67 640 celdas. Un ejercicio conservador con un analista y ocho horas diarias de consolidación manual permite estimar un costo evitado superior a S/ 3 000 mensuales; sin embargo, esta cifra es referencial y debe validarse con las entidades usuarias."),
    ]

    # ------------------------------------------------------------------
    # 5.15 PLAN DE SEGURIDAD
    # ------------------------------------------------------------------
    B["plan_seguridad"] = [
        ("p", "El plan de seguridad se organiza en tres capas —aplicación, datos e infraestructura— y se apoya en controles verificables. El canal de alertas utiliza Green API para WhatsApp (Green API, 2024). La Tabla 5.7 resume los controles implementados y su forma de verificación."),
        ("t", [
            ["Capa", "Control", "Implementación", "Verificación"],
            ["Aplicación", "Autenticación de endpoints de alerta", "Cabecera X-API-Key validada contra ADMIN_API_KEY", "Pruebas test_alerts_require_key_when_configured y test_alerts_reject_wrong_key"],
            ["Aplicación", "CORS restringido", "Lista blanca ALLOWED_ORIGINS; por defecto solo orígenes locales", "tests/test_security.py"],
            ["Aplicación", "Rate limit en reportes ciudadanos", "5 solicitudes por 600 s por IP", "test_rate_limit_blocks_after_max_calls"],
            ["Aplicación", "Validación de coordenadas", "Bounding box del Perú en /report/citizen", "test_report_citizen_rejects_coords_outside_peru"],
            ["Aplicación", "Validación de entrada", "Modelos Pydantic y límites de texto", "tests/test_api.py"],
            ["Aplicación", "Cabeceras de seguridad", "X-Content-Type-Options, X-Frame-Options, Referrer-Policy y CSP", "Middleware add_security_headers"],
            ["Datos", "Gestión de secretos", ".env fuera del repositorio; .env.example como plantilla", "git ls-files; revisión de historial"],
            ["Datos", "Minimización de datos personales", "Reportes sin nombre ni teléfono; solo zona, tipo y descripción opcional", "Revisión de CitizenReport"],
            ["Datos", "Respaldo y trazabilidad", "Copia de dataset, modelo y metadatos; grid_id y fecha en cada predicción", "Procedimiento de respaldo"],
            ["Infraestructura", "TLS y proxy inverso", "HTTPS en producción; HTTP solo en local", "Configuración del proxy"],
            ["Infraestructura", "Contenedor y healthcheck", "Docker con reinicio automático y /health cada 30 s", "docker-compose.yml"],
            ["Infraestructura", "Dependencias y calidad", "CI con ruff y pytest; revisión de dependencias", ".github/workflows/ci.yml"],
        ], 7.5),
        ("n", "Tabla 5.7. Controles de seguridad por capa."),
        ("p", "Se identificó un incidente de seguridad relevante: el archivo .env estuvo versionado en el repositorio con claves reales. Como medida correctiva se retiró del índice de Git, se agregó a .gitignore y se creó .env.example. La rotación de las claves expuestas es obligatoria; además, se recomienda purgar el historial con git filter-repo si el repositorio se hace público. El sistema no almacena datos personales de los reportantes y no publica direcciones IP."),
    ]

    # ------------------------------------------------------------------
    # 5.16 PLAN DE CALIDAD (reemplaza tabla 15)
    # ------------------------------------------------------------------
    B["plan_calidad"] = [
        ("p", "El plan de calidad se alinea con ISO/IEC 25010 (ISO/IEC, 2023) y con las prácticas de ingeniería del repositorio, incluido el análisis estático con ruff (Astral, 2024). La Tabla 5.8 resume los componentes del plan."),
        ("t", [
            ["Componente", "Definición"],
            ["Objetivo", "Garantizar que el software cumpla los requisitos funcionales, no funcionales y de satisfacción, con evidencia verificable."],
            ["Estándares", "ISO/IEC 25010 (calidad del producto), OpenAPI 3.1 (contrato de API), PEP 8/ruff (estilo), MIT (licencia)."],
            ["Procesos", "Revisión de código, integración continua, pruebas unitarias, de integración, de aceptación y de carga; auditorías internas."],
            ["Roles", "QA/seguridad coordina el plan; backend, frontend y datos ejecutan las pruebas de su módulo."],
            ["Herramientas", "pytest, ruff, GitHub Actions, Locust, auditorías audit_quick.py, audit_final.py e iso25010_audit.py, navegador con DevTools."],
            ["Métricas", "32/32 pruebas aprobadas; 0 errores de ruff; 85/85 audit_quick; 106/106 audit_final; 133/133 ISO 25010; 0 errores de consola y 0 solicitudes fallidas en el portal; /predict ≈ 32 ms."],
            ["Riesgos", "Baja cobertura de casos límite, cambios en fuentes externas y regresiones; se controlan con CI, datos de prueba y revisión de cambios."],
            ["Evidencia", "tests/, .github/workflows/ci.yml, docs/ y registros de ejecución."],
        ], 9.0),
        ("n", "Tabla 5.8. Plan de calidad del software."),
    ]

    return B
