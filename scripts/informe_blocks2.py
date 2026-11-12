# -*- coding: utf-8 -*-
"""Bloques de contenido: metodología, resultados, referencias y anexos."""


def get_blocks2():
    B = {}

    # ------------------------------------------------------------------
    # 6.1 METODOLOGÍA
    # ------------------------------------------------------------------
    B["metodologia"] = [
        ("p", "La metodología se seleccionó después de comparar Scrum (Schwaber & Sutherland, 2020), Kanban, XP y CRISP-DM (Wirth & Hipp, 2000). Se adoptó un enfoque híbrido porque el proyecto requiere, por un lado, un proceso experimental riguroso para construir y evaluar el modelo y, por otro, iteraciones cortas para entregar API, portal y pruebas. CRISP-DM aporta las fases de comprensión del negocio, comprensión de los datos, preparación, modelado, evaluación y despliegue; Scrum aporta el backlog, los sprints semanales y las revisiones con entregables. La validación espacial sigue las recomendaciones de Roberts et al. (2017)."),
        ("t", [
            ["Fase CRISP-DM", "Actividades principales", "Artefactos", "Sprint"],
            ["Comprensión del negocio", "Diagnóstico, objetivos, stakeholders, requisitos y criterios de éxito", "Acta, matriz de consistencia, 74 historias de usuario", "S1–S2"],
            ["Comprensión de los datos", "Identificación de fuentes, diccionario, análisis exploratorio y calidad", "Diccionario de datos, EDA, reporte de fuentes", "S3"],
            ["Preparación de los datos", "Grilla, features, vecindario KNN, codificación circular del viento y panel temporal", "dataset.parquet, scripts de ETL", "S4–S5"],
            ["Modelado", "Baseline, ensemble, Optuna, validación espacial y SHAP", "Modelo versionado, metadatos, métricas", "S6–S8"],
            ["Evaluación", "ROC-AUC, PR-AUC, recall@top-k, comparación con línea base y análisis de limitaciones", "Informe de métricas y discusión", "S9"],
            ["Despliegue", "API, portal, seguridad, pruebas, CI y Docker", "Servicio, portal, tests y manual", "S10–S16"],
        ], 8.0),
        ("n", "Tabla 6.1. Fases, actividades y artefactos de la metodología híbrida."),
        ("p", "La selección se justifica por tres razones. Primera, el problema tiene una componente de datos dominante: sin una comprensión cuidadosa de las fuentes y de la etiqueta, cualquier métrica resulta engañosa. Segunda, el producto debe ser usable por público general, lo que exige iteraciones de interfaz y accesibilidad. Tercera, el equipo es pequeño y el plazo académico es limitado, por lo que Scrum permite priorizar un producto mínimo viable sin sacrificar la trazabilidad de los experimentos."),
    ]

    B["planificacion"] = [
        ("p", "La planificación se organizó en 16 semanas y ocho sprints de dos semanas. La Tabla 6.2 presenta el cronograma, las actividades y el entregable verificable de cada etapa."),
        ("t", [
            ["Fase / sprint", "Semanas", "Actividades", "Entregable"],
            ["S1. Inicio", "1–2", "Acta, stakeholders, objetivos, requisitos y historias de usuario", "Acta, backlog y catálogo de 74 historias"],
            ["S2. Datos", "3–4", "Descarga FIRMS, ERA5, DEM, NDVI y OSM; grilla y diccionario", "dataset.parquet y scripts ETL"],
            ["S3. Features", "5–6", "Vecindario KNN, viento sin/cos, lags, sequía y anomalía NDVI", "18 variables y análisis exploratorio"],
            ["S4. Modelo base", "7–8", "Baseline, partición espacial, primeras métricas", "Modelo v1 y reporte de línea base"],
            ["S5. Modelo final", "9–10", "Ensemble, Optuna, SHAP y umbrales por presupuesto de alerta", "Modelo v2.3.0 y metadatos"],
            ["S6. API y portal", "11–12", "Endpoints, portal, mapa, reportes y alertas", "API y portal funcionales"],
            ["S7. Calidad", "13–14", "Pruebas, seguridad, CI, auditorías y carga", "32 pruebas, CI y auditoría"],
            ["S8. Cierre", "15–16", "Despliegue, documentación, validación y presentación", "Informe, anexos y demo"],
        ], 8.5),
        ("n", "Tabla 6.2. Cronograma de desarrollo del producto."),
        ("p", "El seguimiento se realizó con un tablero Kanban en GitHub Projects, reuniones semanales y revisión de commits. Los hitos principales fueron: H1 requisitos definidos (S02), H2 datos integrados (S06), H3 modelo inicial (S09), H4 aplicación integrada (S12), H5 pruebas y seguridad (S14) y H6 entrega (S16)."),
    ]

    B["analisis"] = [
        ("p", "El análisis se centró en tres productos: el catálogo de requisitos, el modelo de datos y la arquitectura. Los requisitos se documentaron como historias de usuario con criterios de aceptación y prioridad MoSCoW; el catálogo completo está en docs/Historias_de_Usuario.md y su versión tabular en docs/Historias_de_Usuario.csv. El modelo de datos se describe en un diccionario con 30 columnas, tipos, unidades, fuentes y reglas de validación."),
        ("p", "La arquitectura se documentó con el modelo C4. El nivel de contexto identifica a los usuarios, las fuentes externas y los canales de difusión; el nivel de contenedores separa el portal, la API, el pipeline de datos y el almacenamiento; el nivel de componentes detalla los módulos de ingesta, features, modelo, seguridad, alertas y reportes. El contrato de la API se expone automáticamente con OpenAPI en /docs, lo que facilita las pruebas y la integración por terceros."),
        ("p", "También se realizó un análisis de riesgos y un análisis de impacto social, cultural, económico, político, legal, ambiental y de seguridad. Estos insumos se reflejan en las secciones 5.12 a 5.16 y en la matriz de responsabilidades éticas del informe."),
    ]

    B["desarrollo"] = [
        ("p", "El desarrollo se organizó en sprints de dos semanas con revisión al final de cada uno. El repositorio se estructuró en módulos desacoplados: app/ para la API y el modelo, data_pipeline/ para la ingesta y el entrenamiento, web/ para el portal, tests/ para las pruebas, airflow/ para la orquestación y scripts/ para utilidades. Cada cambio relevante se revisó con ruff y pytest antes de integrarse."),
        ("p", "Se aplicaron prácticas de ingeniería de software: control de versiones con Git, mensajes de commit descriptivos, revisión de código, funciones pequeñas, tipado en las interfaces, manejo de errores y registro de advertencias. El ensemble combina LightGBM (Ke et al., 2017), XGBoost (Chen & Guestrin, 2016) y Random Forest (Breiman, 2001); la optimización se realizó con Optuna (Akiba et al., 2019) y la interpretabilidad con SHAP (Lundberg & Lee, 2017). La versión final del modelo se identifica como v2.3.0-spatial-ensemble-real y se acompaña de sus metadatos, umbrales y métricas."),
        ("p", "La protección de datos se incorporó desde el diseño: no se solicitan nombres ni teléfonos en los reportes ciudadanos; las credenciales se leen de variables de entorno; el archivo .env no se versiona; los datos de entrenamiento son ambientales y geoespaciales, no personales; y las encuestas de validación se aplicarán con consentimiento informado y anonimización."),
    ]

    B["resultados_etapas"] = [
        ("p", "Cada sprint dejó un entregable verificable. La Tabla 6.3 resume los productos y su evidencia."),
        ("t", [
            ["Sprint", "Producto", "Evidencia", "Estado"],
            ["S1", "Requisitos y backlog", "docs/Historias_de_Usuario.md; docs/Historias_de_Usuario.csv", "Completado"],
            ["S2", "Pipeline de datos", "data_pipeline/fetch_firms.py; real_features.py; grid_builder.py", "Completado"],
            ["S3", "Dataset y features", "data/dataset.parquet; 68 187 × 30; 18 features", "Completado"],
            ["S4", "Modelo base", "models/model_metadata.json; métricas de línea base", "Completado"],
            ["S5", "Modelo final", "models/lightgbm_wildfire.pkl; ROC-AUC 0.649", "Completado"],
            ["S6", "API y portal", "app/main.py; web/index.html; web/app.js", "Completado"],
            ["S7", "Calidad y seguridad", "tests/; .github/workflows/ci.yml; auditorías", "Completado"],
            ["S8", "Despliegue y documentación", "Dockerfile; docker-compose.yml; README.md; informe", "En cierre"],
        ], 8.5),
        ("n", "Tabla 6.3. Entregables por sprint y evidencia."),
    ]

    B["proteccion_datos"] = [
        ("p", "La protección de datos se abordó en el producto y en la investigación:"),
        ("b", "Minimización: los reportes ciudadanos solo solicitan coordenadas, tipo de incidente, zona y una descripción opcional; no se piden nombres ni teléfonos."),
        ("b", "Consentimiento: las encuestas y entrevistas incluirán una hoja de consentimiento informado y la posibilidad de retirarse en cualquier momento."),
        ("b", "Anonimización: los resultados de validación se presentarán por rol o código, sin identificar a las personas."),
        ("b", "Seguridad: las claves se gestionan con variables de entorno; .env está fuera del repositorio; los endpoints sensibles exigen X-API-Key."),
        ("b", "Marco legal: se tomará como referencia la Ley N.° 29733 y su Reglamento (Ministerio de Justicia y Derechos Humanos, 2024), así como la Ley N.° 29664 del SINAGERD (Congreso de la República del Perú, 2011)."),
        ("b", "Retención: los reportes ciudadanos se conservan en un archivo JSONL con fines de trazabilidad y pueden depurarse por solicitud."),
    ]

    # ------------------------------------------------------------------
    # 6.2 PRUEBAS
    # ------------------------------------------------------------------
    B["pruebas_unitarias"] = [
        ("p", "Las pruebas unitarias y de integración se implementaron con pytest. Se ejecutan con el comando pytest -q y cubren el modelo, la API, la seguridad y el pipeline. La Tabla 6.4 resume la distribución."),
        ("t", [
            ["Archivo", "N.º de pruebas", "Qué cubre"],
            ["tests/test_model.py", "10", "Features, codificación del viento, defaults, umbrales, percentil, metadatos y comparación con el azar"],
            ["tests/test_api.py", "11", "Health, /risk/today, /predict, reportes ciudadanos, autenticación de alertas, OpenAPI e importancia"],
            ["tests/test_security.py", "6", "Validación de coordenadas, CORS y rate limit"],
            ["tests/test_pipeline.py", "5", "Vecindario KNN, independencia del bloque espacial, cercanía geográfica y codificación circular"],
            ["Total", "32", "Cobertura funcional y de regresión del sistema"],
        ], 8.5),
        ("n", "Tabla 6.4. Distribución de las pruebas automatizadas."),
        ("p", "La ejecución local reporta 32 pruebas aprobadas y ruff check . sin errores. La integración continua ejecuta ambos pasos en GitHub Actions para cada push y pull request a las ramas main y master."),
    ]

    B["evidencia_unitarias"] = [
        ("p", "La evidencia se encuentra en el directorio tests/ y en el workflow .github/workflows/ci.yml. Además de las pruebas, se ejecutaron auditorías internas: audit_quick.py (85/85), audit_final.py (106/106) e iso25010_audit.py (133/133), así como test_lightgbm_precision.py, que aprueba el modelo si supera la línea base aleatoria. Los resultados se registran en la consola y se pueden reproducir con los comandos indicados en el README."),
    ]

    B["pruebas_aceptacion"] = [
        ("p", "Las pruebas de aceptación verifican los criterios CR01–CR09 definidos en la sección 5. La Tabla 6.5 presenta el resultado obtenido y la evidencia."),
        ("t", [
            ["Criterio", "Descripción", "Resultado", "Evidencia"],
            ["CR01", "Integración de focos, atmósfera y capas geoespaciales", "Cumple", "5 fuentes; dataset de 30 columnas"],
            ["CR02", "Cobertura territorial de la provincia de Cajamarca", "Cumple", "67 640 celdas analizadas"],
            ["CR03", "Clasificación para la fecha de referencia con actualización diaria", "Parcial", "Índice de susceptibilidad; no es pronóstico a 24 h"],
            ["CR04", "Rendimiento predictivo medido con métricas", "Cumple", "ROC-AUC 0.649; PR-AUC 0.0017; recall@top-k"],
            ["CR05", "Visualización de mapa, categoría, coordenadas y fecha", "Cumple", "Portal web y /risk/today"],
            ["CR06", "Alertamiento ante celdas de riesgo alto", "Cumple", "WhatsApp y /alert/daily"],
            ["CR07", "Trazabilidad de cada predicción", "Cumple", "grid_id, probabilidad, percentil y metadata"],
            ["CR08", "Credenciales fuera del código y control de acceso", "Cumple", ".env no versionado; X-API-Key; CORS"],
            ["CR09", "Comprensión de la clasificación por usuarios", "Parcial", "Pruebas internas; validación con usuarios pendiente"],
        ], 8.0),
        ("n", "Tabla 6.5. Resultados de las pruebas de aceptación."),
    ]

    B["evidencia_aceptacion"] = [
        ("p", "La revisión del portal en navegador reportó 0 errores de consola y 0 solicitudes fallidas. Se verificaron la carga del mapa, los filtros por región y ventana de focos, el formulario de reporte ciudadano, la visualización del percentil y la fecha de actualización. Las auditorías de estructura, seguridad y calidad complementan la evidencia funcional."),
    ]

    # ------------------------------------------------------------------
    # 6.3 DESPLIEGUE
    # ------------------------------------------------------------------
    B["plan_despliegue"] = [
        ("p", "El despliegue se diseñó para ser reproducible en un servidor pequeño o en una máquina local. La Tabla 6.6 resume los componentes y su configuración."),
        ("t", [
            ["Componente", "Configuración"],
            ["Imagen", "Dockerfile basado en python:3.11-slim con GDAL y dependencias de requirements.txt"],
            ["Servicio", "docker-compose.yml con un único servicio api, puerto 8000 y reinicio unless-stopped"],
            ["Salud", "Healthcheck cada 30 s contra /health, con 3 reintentos y 20 s de espera inicial"],
            ["Configuración", "Variables de entorno en .env (no versionado); .env.example como plantilla"],
            ["Proxy y TLS", "Nginx o Caddy como proxy inverso con HTTPS en producción"],
            ["Integración continua", "GitHub Actions: ruff y pytest en cada push y pull request"],
            ["Respaldo", "Copia de data/, models/ y models/model_metadata.json antes de cada reentrenamiento"],
            ["Reversión", "Etiqueta de imagen y reversión de commit; el modelo anterior se conserva"],
        ], 8.5),
        ("n", "Tabla 6.6. Componentes del despliegue."),
        ("p", "El plan contempla tres entornos: local (uvicorn en el puerto 5050 para el portal y 8000 para la API), pruebas (contenedor con datos de muestra) y producción (contenedor con TLS y respaldos). La base de datos no es obligatoria: el sistema funciona con archivos Parquet/CSV; PostgreSQL/PostGIS queda como opción para despliegues institucionales que requieran consultas espaciales concurrentes."),
    ]

    B["proceso_despliegue"] = [
        ("p", "El proceso de despliegue consta de los siguientes pasos:"),
        ("b", "1. Clonar el repositorio y copiar .env.example a .env; completar FIRMS_MAP_KEY, ADMIN_API_KEY y, si se usan alertas, GREEN_API_INSTANCE_ID y GREEN_API_TOKEN."),
        ("b", "2. Verificar que data/dataset.parquet, models/lightgbm_wildfire.pkl y models/model_metadata.json estén presentes."),
        ("b", "3. Ejecutar docker compose up -d --build y esperar a que el healthcheck reporte healthy."),
        ("b", "4. Abrir http://localhost:8000/health y http://localhost:8000/docs para verificar la API; el portal se sirve en la raíz o en el puerto configurado."),
        ("b", "5. Ejecutar pytest -q y ruff check . antes de publicar una nueva versión."),
        ("b", "6. Configurar el proxy inverso con TLS y restringir ALLOWED_ORIGINS a los dominios reales."),
        ("b", "7. Programar el DAG de Airflow o el scheduler para la actualización diaria y el envío de alertas a las 07:00 (America/Lima)."),
    ]

    B["evidencia_despliegue"] = [
        ("p", "El sistema se ejecutó localmente con uvicorn en el puerto 5050 y con Docker en el puerto 8000. El portal mostró 0 errores de consola y 0 solicitudes fallidas; el endpoint /health respondió 200; /risk/today devolvió 67 640 celdas analizadas con 682 en Rojo, 2 722 en Amarillo y 64 236 en Verde. El repositorio público está disponible en https://github.com/DanielMedina1727/SISTEMA-NACI-NAL-DE-ALERTA-TEMPRANA-DE-INCENDIOS-FORESTALES y el video demostrativo se referencia en el Anexo 01."),
    ]

    # ------------------------------------------------------------------
    # 6.4 MEDICIÓN DE LA VARIABLE INDEPENDIENTE
    # ------------------------------------------------------------------
    B["medicion_vi"] = [
        ("p", "La variable independiente —sistema web basado en sensores remotos y variables atmosféricas— se midió con indicadores de integración, calidad, rendimiento, seguridad y usabilidad. La Tabla 6.7 presenta los valores obtenidos con los instrumentos de observación técnica."),
        ("t", [
            ["Dimensión", "Indicador", "Fórmula o criterio", "Valor obtenido", "Instrumento"],
            ["Integración de datos", "Fuentes integradas", "N.º de fuentes conectadas / 5", "5/5 (100 %)", "Ficha de observación"],
            ["Cobertura", "Celdas analizadas", "Celdas con score / celdas de la grilla", "67 640", "Ficha de observación"],
            ["Features", "Variables predictoras", "N.º de variables en FEATURE_ORDER", "18", "Metadatos del modelo"],
            ["Calidad", "Registros válidos", "Filas sin errores de esquema", "68 187", "Dataset"],
            ["Modelo", "ROC-AUC espacial", "Área bajo la curva ROC out-of-fold", "0,649 ± 0,069", "Metadatos"],
            ["Modelo", "PR-AUC", "Área bajo la curva precisión-recall", "0,0017", "Metadatos"],
            ["Modelo", "Recall@Top-10 %", "Positivos en el Top-10 % / total de positivos", "19,44 %", "Metadatos"],
            ["Rendimiento", "Latencia /predict", "Tiempo medio de 300 solicitudes", "32,3 ms", "Prueba de carga"],
            ["Rendimiento", "Latencia /risk/today", "Tiempo para 200 / 1 200 / 5 000 celdas", "35 / 127 / 474 ms", "Prueba de carga"],
            ["Calidad", "Pruebas aprobadas", "Pruebas pass / total", "32/32", "pytest"],
            ["Seguridad", "Controles verificados", "Pruebas de seguridad aprobadas", "6/6", "pytest"],
            ["Usabilidad", "Errores de consola", "Errores JS / solicitudes fallidas", "0 / 0", "DevTools"],
        ], 7.5),
        ("n", "Tabla 6.7. Medición de indicadores de la variable independiente."),
        ("p", "Los indicadores de usabilidad con usuarios se completarán con la aplicación del cuestionario del Anexo 06. Los valores presentados corresponden a la medición técnica del prototipo y a las pruebas internas de navegador."),
    ]

    # ------------------------------------------------------------------
    # 7. RESULTADOS
    # ------------------------------------------------------------------
    B["viabilidad_tecnica"] = [
        ("p", "La viabilidad técnica se evaluó con evidencia de ejecución, no con apreciaciones. El sistema procesa 68 187 celdas, entrena un ensemble con 18 variables y sirve predicciones en milisegundos; el portal y la API funcionan en un contenedor Docker y las pruebas automatizadas cubren los módulos críticos. La Tabla 7.1 resume los resultados."),
        ("t", [
            ["Dimensión", "Indicador", "Resultado", "Criterio", "Cumple"],
            ["Datos", "Fuentes integradas", "5/5", "Todas las fuentes del alcance", "Sí"],
            ["Datos", "Celdas y variables", "68 187 celdas; 18 features", "Grilla ~1 km²", "Sí"],
            ["Modelo", "ROC-AUC espacial", "0,649 ± 0,069", "> 0,60", "Sí"],
            ["Modelo", "PR-AUC", "0,0017", "> prevalencia (0,00066)", "Sí"],
            ["Modelo", "Recall@Top-10 %", "19,44 %", "> 10 % (azar)", "Sí"],
            ["Rendimiento", "Latencia /predict", "32,3 ms", "< 100 ms", "Sí"],
            ["Rendimiento", "Latencia /risk/today (1 200)", "127 ms", "< 1 s", "Sí"],
            ["Calidad", "Pruebas", "32/32", "100 %", "Sí"],
            ["Seguridad", "Controles", "API key, CORS, rate limit, bbox", "Controles activos", "Sí"],
            ["Portabilidad", "Despliegue", "Docker + Python 3.11", "Reproducible", "Sí"],
        ], 7.5),
        ("n", "Tabla 7.1. Viabilidad técnica y tecnológica."),
        ("p", "La conclusión técnica es que el sistema es viable para el alcance académico y para un despliegue piloto de bajo costo. No obstante, la viabilidad operativa completa requiere más fechas de entrenamiento, validación con usuarios y un protocolo de verificación en campo; estos aspectos se discuten en la sección 7.6."),
    ]

    B["viabilidad_economica"] = [
        ("p", "La viabilidad económica se analizó con un escenario conservador de costos operativos. El sistema utiliza datos abiertos y software libre, por lo que el gasto se concentra en conectividad, servidor y dominio. La Tabla 7.2 presenta el costo mensual y anual estimado."),
        ("t", [
            ["Rubro", "Costo mensual (S/)", "Costo anual (S/)", "Observación"],
            ["Servidor virtual (2 vCPU, 4 GB)", "70", "840", "Plan de bajo costo"],
            ["Dominio .pe", "10", "120", "Pago anual"],
            ["Internet", "100", "1 200", "Puede ser un servicio existente"],
            ["WhatsApp / Green API", "0", "0", "Plan gratuito para bajo volumen"],
            ["Datos y APIs", "0", "0", "NASA, Copernicus, Open-Meteo y OSM"],
            ["Mantenimiento y reentrenamiento", "0", "0", "Trabajo voluntario; 10 h/mes"],
            ["Total monetario", "180", "2 160", "Sin costo de licencias"],
        ], 8.5),
        ("n", "Tabla 7.2. Costo operativo estimado del sistema."),
        ("p", "El beneficio económico se expresa como costo evitado. Un escenario conservador de monitoreo manual —un analista durante ocho horas diarias, 22 días al mes, a S/ 20 por hora— representa cerca de S/ 3 520 mensuales. Si el sistema reduce esa carga a dos horas diarias de verificación, el ahorro potencial supera S/ 2 600 mensuales, además de la mejora en oportunidad. La cifra es referencial y debe validarse con las entidades que adopten el sistema; el valor principal es la priorización de recursos, no el ahorro contable."),
        ("p", "La inversión inicial es mínima porque no se requieren licencias, sensores propios ni infraestructura dedicada. El costo de oportunidad se concentra en el tiempo de mantenimiento y en la actualización de datos, que puede asumirse como trabajo voluntario o mediante un convenio de cooperación."),
    ]

    B["indicadores"] = [
        ("p", "Los indicadores se eligieron para reflejar el desempeño del modelo y del sistema, no solo la exactitud global. En un problema con 0,066 % de positivos, la exactitud es engañosa; por ello se reportan métricas libres de umbral y métricas de ranking. La Tabla 7.3 presenta los indicadores y sus valores."),
        ("t", [
            ["Indicador", "Fórmula", "Valor", "Interpretación"],
            ["ROC-AUC", "Área bajo la curva TPR vs. FPR", "0,649 ± 0,069", "Capacidad de ordenar positivos por encima de negativos; mejor que el azar (0,5)."],
            ["PR-AUC", "Área bajo la curva precisión-recall", "0,0017", "Bajo en términos absolutos, pero 2,6 veces la prevalencia."],
            ["Recall@Top-1 %", "Positivos en el Top-1 % / total", "1,05 %", "Casi igual al azar (1 %); el Top-1 % no es suficiente."],
            ["Recall@Top-5 %", "Positivos en el Top-5 % / total", "5,05 %", "Ligeramente superior al azar (5 %)."],
            ["Recall@Top-10 %", "Positivos en el Top-10 % / total", "19,44 %", "1,94 veces el azar; útil para priorización."],
            ["Recall@Top-20 %", "Positivos en el Top-20 % / total", "45,11 %", "2,26 veces el azar; mejor escenario operativo."],
            ["F1", "2PR / (P + R)", "0,0018", "Refleja el desbalance extremo; no debe usarse solo."],
            ["Latencia /predict", "Tiempo medio por solicitud", "32,3 ms", "Aceptable para uso interactivo."],
            ["Latencia /risk/today", "Tiempo para 1 200 celdas", "127 ms", "Aceptable para el portal."],
        ], 7.5),
        ("n", "Tabla 7.3. Indicadores y ratios del sistema."),
        ("p", "La lectura conjunta es importante: el modelo ordena mejor que el azar, pero su precisión absoluta es baja. El Top-1 % y el Top-5 % apenas superan el azar, mientras que el Top-10 % y el Top-20 % duplican la detección esperada. Por ello, el sistema debe comunicar el riesgo como un ranking y no como una probabilidad calibrada, y debe priorizar la vigilancia en los cortes del 10 % al 20 % antes que en alertas rojas indiscriminadas."),
    ]

    B["linea_base"] = [
        ("p", "La comparación con la línea base se realizó en dos niveles: el azar teórico y un modelo LightGBM de tutorial sin ajuste espacial. La Tabla 7.4 presenta los resultados. El modelo optimizado se evaluó con validación espacial 5-fold out-of-fold por bloques de 50 km, de modo que ninguna celda de prueba comparte vecindad con el entrenamiento."),
        ("t", [
            ["Indicador", "Línea base (azar)", "Baseline tutorial", "Resultado del sistema", "Variación"],
            ["ROC-AUC", "0,500", "0,413", "0,649", "+29,8 % vs. azar"],
            ["PR-AUC", "0,00066", "0,0006", "0,0017", "+157,6 % vs. prevalencia"],
            ["Recall@Top-10 %", "10,0 %", "—", "19,44 %", "+94,4 %"],
            ["Recall@Top-20 %", "20,0 %", "—", "45,11 %", "+125,6 %"],
            ["F1", "—", "0,0005", "0,0018", "3,6 veces"],
            ["Cobertura automatizada", "0 celdas", "—", "67 640 celdas", "100 % del área"],
        ], 8.0),
        ("n", "Tabla 7.4. Comparación con la línea base."),
        ("p", "La mejora es real pero modesta. El ROC-AUC de 0,649 indica una capacidad de ordenamiento superior al azar, aunque lejos de un sistema de alta precisión. El PR-AUC de 0,0017 es bajo en términos absolutos, pero 2,6 veces la prevalencia; con 45 positivos, este valor es más informativo que la exactitud o el F1. La cobertura de 67 640 celdas y la generación automática del mapa sustituyen un proceso manual que, en el mejor de los casos, se realizaba de forma semanal y sobre un conjunto limitado de reportes."),
        ("p", "La línea base tutorial confirma que un modelo mal configurado puede tener un ROC-AUC inferior al azar (0,413) y un F1 de 0,0005. Este resultado se incluyó deliberadamente para mostrar que la comparación no se limita a un modelo perfecto contra el azar, sino que también cuestiona las prácticas de entrenamiento sin validación espacial."),
    ]

    B["sostenibilidad"] = [
        ("p", "La sostenibilidad se evaluó en cinco dimensiones:"),
        ("b", "Técnica: el código es abierto, modular y reproducible; Docker y los tests permiten replicar el entorno; el pipeline admite nuevas fechas y fuentes. El mantenimiento requiere actualizar dependencias, reentrenar con nuevos focos y revisar métricas."),
        ("b", "Económica: el costo operativo es bajo (S/ 180 mensuales en el escenario estimado) y no hay licencias. Los servicios de datos son gratuitos o de uso justo. El riesgo es la dependencia de planes gratuitos y de la conectividad."),
        ("b", "Social: el acceso es libre, sin registro y desde el navegador; los grupos de WhatsApp se autoorganizan por la comunidad. La validación con usuarios y el lenguaje claro son condiciones para que el sistema no amplíe la brecha digital."),
        ("b", "Ambiental: el sistema no sustituye la prevención física, pero ayuda a focalizar vigilancia y recursos en las zonas con mayor score. Su beneficio ambiental es indirecto y depende de la acción de las comunidades y autoridades."),
        ("b", "Institucional: el sistema no pertenece a una entidad ni depende de un convenio; puede ser adoptado por municipios, ONG o universidades, o replicado para otra región. La API abierta facilita la integración, pero no se promete soporte institucional."),
        ("p", "Los principales riesgos de sostenibilidad son la actualización de datos, la rotación de claves, la deriva del modelo (data drift) y la continuidad del equipo voluntario. Se recomienda un plan de mantenimiento trimestral, un repositorio de incidencias y una revisión anual de métricas y fuentes."),
    ]

    B["discusion"] = [
        ("p", "Los resultados se discuten con los antecedentes revisados. Vera-Caro et al. (2026) muestran que la precisión técnica de un sistema de alerta no basta si la comunidad no comprende el riesgo; por ello el portal prioriza un semáforo simple, la fecha de actualización y un lenguaje que no promete certeza. Rubio et al. (2026), García et al. (2025) y Matamoros et al. (2025) demuestran que los sistemas IoT pueden alcanzar precisiones muy altas en condiciones controladas, pero requieren sensores físicos, calibración y mantenimiento; el presente sistema opta por datos satelitales y atmosféricos abiertos, con menor costo y menor resolución espacial."),
        ("p", "Brys (2026) advierte que el Fire Weather Index subestima el riesgo en vegetación heterogénea; el enfoque de aprendizaje automático con variables locales permite capturar interacciones no lineales, aunque con solo 45 positivos la capacidad de generalización es limitada. Cisneros Francia y Unsihuay Tovar (2026) enfatizan la verificación espacial de los pronósticos; este proyecto adopta esa lección mediante validación por bloques espaciales y reporte de métricas top-k, en lugar de una partición aleatoria."),
        ("p", "La contribución principal no es un modelo con precisión alta, sino un sistema completo, abierto y honesto: integra cinco fuentes, construye una grilla reproducible, entrena con validación espacial, sirve el resultado en una API y un portal, y documenta sus limitaciones. El ROC-AUC de 0,649 y el PR-AUC de 0,0017 son modestos, pero están por encima del azar y son coherentes con la literatura cuando hay pocos positivos y autocorrelación espacial."),
        ("p", "Las limitaciones son claras. Primera, el conjunto actual corresponde a una fecha de referencia; el pipeline admite --ref-dates y --start-date para construir un panel temporal, pero se necesitan más fechas para reducir el desajuste train/serve. Segunda, 45 positivos son insuficientes para una calibración estable; por ello se descartó la calibración de probabilidades y se adoptó un ranking por percentiles. Tercera, la etiqueta FIRMS no confirma incendios en campo; puede contener falsos positivos y omisiones. Cuarta, la validación con usuarios está pendiente y es indispensable para evaluar la comprensión y la confianza."),
        ("p", "El veredicto técnico-profesional es: implementar con mejoras. Se recomienda implementarlo como piloto en una provincia o cuenca, con un protocolo de verificación en campo, un plan de comunicación de incertidumbre y una revisión trimestral de métricas. No se recomienda presentarlo como sistema oficial de alerta ni como pronóstico determinista. Los tres criterios que sustentan el veredicto son: técnico (funciona, está probado y es reproducible), ético (declara sus límites y no genera falsa seguridad) y operativo (requiere validación y articulación con actores locales)."),
    ]

    B["oe01"] = [
        ("p", "El Objetivo Específico 01 consistió en diagnosticar los métodos actuales de estimación del riesgo de incendios forestales y establecer una línea base de evaluación en la provincia de Cajamarca. El diagnóstico se realizó con el diagrama de Pareto, el diagrama de Ishikawa, la revisión de fuentes y la medición técnica del prototipo. Los resultados se presentan a continuación."),
        ("h", "7.6.1.1. Diagnóstico de los métodos actuales"),
        ("p", "La Tabla 7.5 caracteriza los métodos disponibles antes del proyecto. Ninguno de ellos integra, en una sola plataforma abierta, focos satelitales, variables atmosféricas, topografía, vegetación e infraestructura con una salida diaria y comprensible para público general."),
        ("t", [
            ["Método", "Frecuencia", "Cobertura", "Limitación principal"],
            ["Reportes manuales de campo", "Irregular", "Local", "Depende de observación directa; llega tarde y con sesgo territorial."],
            ["Consulta de focos NASA FIRMS", "Diaria", "Regional", "Detecta anomalías térmicas; no estima riesgo futuro ni prioriza por probabilidad."],
            ["Índice FWI o criterios meteorológicos", "Diaria", "Global/regional", "Subestima vegetación heterogénea y no integra infraestructura local."],
            ["QGIS/ArcGIS de escritorio", "Por demanda", "Variable", "Requiere experticia, no automatiza ingestión ni alertas."],
            ["Hojas de cálculo y consolidación manual", "Semanal/mensual", "Parcial", "Fragmentación, errores y retraso; no es reproducible."],
            ["Sistema propuesto", "Diaria", "67 640 celdas", "Índice de susceptibilidad, no pronóstico; requiere verificación en campo."],
        ], 8.0),
        ("n", "Tabla 7.5. Diagnóstico de métodos actuales de estimación del riesgo."),
        ("p", "El diagnóstico cuantitativo del proceso identificó cinco causas priorizadas: fragmentación y dispersión de datos (P1, 38 %), información desactualizada y retraso de reportes (P2, 26 %), falta de integración atmosférica y geoespacial (P3, 16 %), alertas tardías y poco comprensibles (P4, 12 %) y dificultad para priorizar recursos (P5, 8 %). Las tres primeras concentran el 80 % del impacto, lo que justifica una solución de integración y automatización. El detalle del registro se presenta en el Anexo 08."),
        ("h", "7.6.1.2. Línea base de evaluación"),
        ("p", "La línea base se estableció con tres referencias: el azar teórico, un modelo LightGBM de tutorial sin ajuste espacial y el ensemble optimizado con validación espacial. La Tabla 7.6 presenta las métricas. El conjunto de datos tiene 68 187 celdas, 45 positivos (0,066 %) y 32 bloques espaciales; la validación usa 5 folds por bloques de 50 km."),
        ("t", [
            ["Modelo", "ROC-AUC", "PR-AUC", "Recall", "F1", "Observación"],
            ["Azar (prevalencia)", "0,500", "0,00066", "10 % en Top-10 %", "—", "Referencia teórica"],
            ["Baseline tutorial LightGBM", "0,413", "0,0006", "0,0889", "0,0005", "Sin ajuste espacial ni calibración"],
            ["Ensemble optimizado", "0,649 ± 0,069", "0,0017 ± 0,0015", "0,8444 al umbral 0,00156", "0,0018", "Validación espacial 5-fold"],
        ], 8.0),
        ("n", "Tabla 7.6. Línea base y resultados del modelo."),
        ("p", "El recall de 0,8444 corresponde al umbral operativo de 0,00156 en la escala out-of-fold; no debe confundirse con el recall en el Top-k. Para la operación se usan los cortes por presupuesto de alerta, que se presentan en la Tabla 7.7."),
        ("t", [
            ["Corte", "Recall del sistema", "Recall del azar", "Mejora relativa", "Lectura"],
            ["Top-1 %", "1,05 %", "1,00 %", "+5,0 %", "No supera sustancialmente el azar"],
            ["Top-5 %", "5,05 %", "5,00 %", "+1,0 %", "Prácticamente igual al azar"],
            ["Top-10 %", "19,44 %", "10,00 %", "+94,4 %", "Duplica la detección esperada"],
            ["Top-20 %", "45,11 %", "20,00 %", "+125,6 %", "Mejor escenario de priorización"],
        ], 8.5),
        ("n", "Tabla 7.7. Recall por corte de presupuesto de alerta."),
        ("h", "7.6.1.3. Resultados del diagnóstico"),
        ("p", "El diagnóstico confirma que los métodos actuales son reactivos, fragmentados y poco reproducibles. La línea base queda establecida con métricas honestas: ROC-AUC 0,649, PR-AUC 0,0017 y recall@Top-10 % 19,44 %. El sistema supera al azar en los cortes del 10 % y 20 %, pero no en el Top-1 % ni en el Top-5 %, lo que obliga a ajustar la expectativa operativa: el semáforo Rojo (Top-1 %) debe interpretarse como una señal de vigilancia prioritaria, no como una predicción de incendio."),
        ("p", "La principal brecha identificada es la cantidad de positivos y la cobertura temporal. Con 45 positivos y una sola fecha de referencia, el modelo aprende patrones espaciales, pero no la variabilidad estacional. El pipeline ya admite múltiples fechas (--ref-dates) y fechas de inicio para FIRMS (--start-date); la siguiente iteración debe construir un panel temporal con al menos una temporada seca completa y repetir la validación espacial."),
        ("h", "7.6.1.4. Conclusión del OE01"),
        ("p", "El OE01 se cumple en dos sentidos. Primero, se diagnosticaron los métodos actuales y se identificaron sus limitaciones con evidencia cuantitativa y cualitativa. Segundo, se estableció una línea base reproducible con métricas espaciales, un modelo de referencia y un conjunto de datos documentado. La línea base no demuestra que el sistema sea un predictor preciso; demuestra que es posible medir su desempeño de forma honesta y que el sistema mejora la priorización en los cortes del 10 % al 20 %."),
        ("p", "La conclusión operativa es que el sistema debe implementarse como piloto de priorización preventiva, acompañado de verificación en campo y de una comunicación explícita de incertidumbre. La conclusión metodológica es que el siguiente paso no es aumentar la complejidad del modelo, sino aumentar la cantidad y variedad de datos, validar con usuarios y medir el impacto en la vigilancia real."),
        ("n", "Nota de alcance: esta versión del informe desarrolla los apartados 7.1 a 7.6.1. Los resultados de los objetivos específicos 02, 03 y 04, la visita a cachimbos y la validación de usuarios finales (apartados 7.6.2 a 7.6.6) se completarán con la aplicación de los instrumentos de los Anexos 06 y 07."),
    ]

    return B
