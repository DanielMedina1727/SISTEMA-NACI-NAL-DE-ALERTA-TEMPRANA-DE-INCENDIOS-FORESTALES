# 📋 Historias de Usuario — Sistema Nacional de Alerta Temprana de Incendios Forestales

> **Proyecto:** AlertaForestal Perú — Cajamarca
> **Versión del modelo en servicio:** `v2.3.0-spatial-ensemble-real`
> **Documento:** Catálogo de requisitos ágiles (historias de usuario)
> **Última actualización:** 2026-10-18

Este documento reúne **todas las historias de usuario** del sistema, organizadas por
**personas** y **épicas**, con criterios de aceptación, prioridad (MoSCoW) y
**trazabilidad** con los módulos y endpoints reales ya implementados.

---

## 🧭 Alcance y modelo de gobernanza

> **El sistema es abierto y de uso público.** No pertenece a una entidad, no se desarrolla por encargo de
> una institución y **no tiene cliente institucional**. Es un proyecto **ciudadano/académico** mantenido por un
> equipo **voluntario** y la comunidad.

- **Acceso libre y gratuito:** sin registro, sin login y sin costo para cualquier persona.
- **Sin dependencia institucional:** no representa ni depende de INDECI, SERFOR, municipios u ONG.
  Estas entidades aparecen como **usuarios secundarios / aliados potenciales** (pueden reutilizar la API),
  pero el sistema funciona igual sin ellas.
- **Código y datos abiertos (MIT):** cualquiera puede auditar, replicar, adaptar o desplegar su propia
  instancia (p. ej., otra región del país).
- **Canales comunitarios:** los grupos de WhatsApp son **autoorganizados por la comunidad**; el sistema
  solo publica el boletín, no son canales oficiales.

**Consecuencia en la priorización:** pesan más las historias de **acceso universal, usabilidad móvil,
transparencia y replicabilidad** que las de integración corporativa.

---

## 👥 Personas (actores)

| ID | Persona | Rol en el sistema |
|---|---|---|
| P1 | **Público general** | Cualquier persona (urbana o rural), sin registro ni conocimientos técnicos. **Usuario principal.** |
| P2 | **Comunidad organizada** (rondas campesinas, comités vecinales, líderes) | Se autoorganiza y difunde los avisos en su zona. |
| P3 | **Voluntario de respuesta** (brigadista, bombero voluntario, Defensa Civil) | Usa el mapa y las alertas como insumo; **no es el cliente**. |
| P4 | **Aliado institucional** (INDECI, SERFOR, municipalidad, ONG, universidad) | Usuario secundario y **aliado potencial**; puede consumir la API, pero el sistema **no depende** de ella. |
| P5 | **Comunidad técnica / educativa** (analistas, docentes, estudiantes) | Explora, valida, enseña y reutiliza los datos. |
| P6 | **Colaborador/a open source** | Contribuye al código, a los datos y a las correcciones. |
| P7 | **Mantenedor voluntario** | Despliega, mantiene y reentrena el servicio **sin pertenecer a una entidad**. |
| P8 | **Periodista / ONG / academia** | Busca transparencia y datos abiertos. |

**Prioridad (MoSCoW):** `Must` = imprescindible · `Should` = importante · `Could` = deseable.

---

## 🟢 ÉPICA 1 — Portal ciudadano y visualización del riesgo

### HU-01 · Consultar el riesgo del día · `Must`
**Como** ciudadano (P1), **quiero** ver de inmediato el **nivel de riesgo del día** (Verde/Amarillo/Rojo) en la portada, **para** saber cómo actuar.
- La portada muestra un *badge* con el nivel calculado por el modelo.
- Se actualiza al cargar la página.
- Si la API está offline, muestra un estado de aviso explícito.

### HU-02 · Entender qué significa cada color · `Must`
**Como** ciudadano (P1), **quiero** una **leyenda clara con los 3 niveles** (Verde/Amarillo/Rojo), **para** interpretar el mapa sin tecnicismos.
- Leyenda visible en el mapa.
- Sin el nivel "Naranja" (unificado en **Amarillo**).
- Texto en lenguaje llano.

### HU-03 · Ver el mapa de riesgo por grilla · `Must`
**Como** ciudadano (P1), **quiero** un **mapa interactivo con las celdas de ~1 km²** coloreadas por nivel, **para** ubicar las zonas más peligrosas.
- `GET /risk/today` devuelve GeoJSON.
- Cada celda incluye `nivel`, `probabilidad` y `percentil`.
- El mapa permite zoom y navegación.

### HU-04 · Filtrar por región · `Should`
**Como** ciudadano (P1), **quiero** **filtrar el mapa por región/provincia**, **para** ver solo mi zona.
- Selector de región operativo que reencuadra el mapa al *bounding box* correspondiente.

### HU-05 · Ver la distribución real del territorio · `Should`
**Como** ciudadano (P1), **quiero** saber **qué porcentaje del territorio está en cada nivel**, **para** dimensionar el riesgo global.
- El campo `stats` del endpoint muestra conteos reales (total, rojo, amarillo, verde).
- El mapa usa **muestreo uniforme honesto** (sin sobrerrepresentar alertas).

### HU-06 · Ampliar información de una celda · `Should`
**Como** ciudadano (P1), **quiero** **tocar una celda y ver su detalle**, **para** conocer por qué está marcada.
- Popup con nivel, percentil y variables relevantes.

### HU-07 · Saber si los datos están actualizados · `Should`
**Como** ciudadano (P1), **quiero** ver un **indicador de frescura de los datos** (versión del modelo y fecha de entrenamiento), **para** saber si la información es reciente.
- El pie de página muestra frescura obtenida de `GET /health` (`model_version`, `training_date`).

---

## 🛰️ ÉPICA 2 — Mapa y focos satelitales (NASA FIRMS)

### HU-08 · Ver focos de calor reales · `Must`
**Como** brigadista (P3), **quiero** ver los **focos de calor satelitales reales (VIIRS/MODIS)** sobre el mapa, **para** correlacionar el riesgo con incendios activos.
- Capa FIRMS vía proxy `GET /firms/hotspots`.
- El popup distingue `✅ Foco Satelital REAL`.

### HU-09 · Elegir la ventana temporal de focos · `Should`
**Como** brigadista (P3), **quiero** seleccionar la **ventana de focos (24/48/72 h)**, **para** ampliar o acotar la búsqueda.
- El filtro de tiempo se traduce en el parámetro `days` de la petición a FIRMS.

### HU-10 · Activar/desactivar capas · `Could`
**Como** ciudadano (P1), **quiero** **encender/apagar capas** (focos, grillas, calor), **para** limpiar el mapa.
- *Toggles* de capas funcionan de forma independiente.

### HU-11 · Proteger la clave de FIRMS · `Must`
**Como** operador MLOps (P7), **quiero** que la **API key de FIRMS nunca se exponga al frontend**, **para** evitar su robo o abuso.
- El frontend consume solo el proxy.
- La llave vive en `.env` del backend.
- No aparece en el código servido.

---

## 📣 ÉPICA 3 — Reportes ciudadanos

### HU-12 · Reportar un foco/humo · `Must`
**Como** ciudadano (P1), **quiero** **enviar un reporte ciudadano** (tipo de incidente, ubicación, zona), **para** alertar a las autoridades.
- `POST /report/citizen` persiste el reporte.
- Se guarda en `data/citizen_reports.jsonl`.
- Devuelve un `id`.

### HU-13 · Validar coordenadas · `Must`
**Como** operador MLOps (P7), **quiero** que los reportes **se validen geográficamente (bbox de Perú)**, **para** evitar datos basura de otros países.
- Coordenadas fuera de Perú → `422`.

### HU-14 · Limitar el spam · `Should`
**Como** operador MLOps (P7), **quiero** **rate-limit en los reportes** (5 por IP cada 10 min), **para** proteger el servicio.
- Sexta petición en la ventana → `429`.

### HU-15 · Ver reportes recientes · `Should`
**Como** brigadista (P3), **quiero** **ver los reportes ciudadanos más recientes**, **para** complementar la información satelital.
- `GET /report/recent` lista los últimos reportes con fecha, tipo, coordenadas y zona.

---

## 🔔 ÉPICA 4 — Alertas por WhatsApp y suscripción

### HU-16 · Recibir el resumen diario · `Must`
**Como** líder comunitario (P2), **quiero** **recibir un resumen diario de riesgo** a las 07:00 (Lima), **para** organizar la vigilancia de mi comunidad.
- El scheduler (`app/scheduler.py`) envía mensajes por zona/provincia.
- Hora `07:00` `America/Lima`.

### HU-17 · Unirme al grupo de mi provincia · `Should`
**Como** ciudadano (P1), **quiero** **suscribirme al grupo de WhatsApp de mi provincia**, **para** permanecer informado.
- Selector de provincia con enlaces reales a los grupos.

### HU-18 · Disparar una alerta manual de zona Roja · `Should`
**Como** brigadista (P3), **quiero** **disparar una alerta inmediata** cuando una zona está en Rojo, **para** movilizar a las brigadas.
- `POST /alert/whatsapp`.
- Requiere `X-API-Key` si `ADMIN_API_KEY` está definida.

### HU-19 · Enviar el boletín diario manualmente · `Could`
**Como** autoridad (P4), **quiero** **forzar el envío del resumen diario** fuera de horario, **para** casos de prueba o emergencia.
- `POST /alert/daily`; protegido por `X-API-Key`; devuelve confirmación.

### HU-20 · Consultar el estado del scheduler · `Should`
**Como** operador MLOps (P7), **quiero** **ver si el scheduler está activo y su próxima ejecución**, **para** verificar el automatismo.
- `GET /alert/status` devuelve estado, número de trabajos y próxima ejecución.

---

## 🔌 ÉPICA 5 — API pública e integración

### HU-21 · Inferencia individual · `Must`
**Como** desarrollador (P6), **quiero** **enviar variables de una celda y recibir probabilidad, percentil y nivel**, **para** integrar el modelo en otras apps.
- `POST /predict` valida entrada (Pydantic) y responde con los 3 campos.

### HU-22 · Simular propagación del fuego · `Should`
**Como** autoridad (P4), **quiero** **simular la propagación por viento y pendiente**, **para** estimar zonas amenazadas.
- `POST /propagate` devuelve trayectoria/área afectada.

### HU-23 · Descubrir la API (OpenAPI) · `Should`
**Como** desarrollador (P6), **quiero** **documentación automática de endpoints**, **para** integrarme rápido.
- Swagger en `/docs` y esquema en `/openapi.json`.

### HU-24 · Ver la importancia de variables · `Should`
**Como** analista (P5), **quiero** **ver la importancia de características (SHAP)**, **para** entender el modelo.
- `GET /model/importance`; `n_features = 18`.

### HU-25 · Consultar la matriz social y de restricciones · `Could`
**Como** autoridad (P4), **quiero** **ver la matriz de entorno social y mitigación**, **para** contextualizar la intervención.
- `GET /social/matrix` en formato consumible.

### HU-26 · Generar un informe ejecutivo en PDF · `Should`
**Como** autoridad (P4), **quiero** **descargar un PDF ejecutivo** con el resumen de riesgo, **para** presentarlo a autoridades.
- `GET /report/pdf` (reportlab) con conteos y celdas Rojo/Amarillo.

---

## ⚖️ ÉPICA 6 — Transparencia, honestidad del dato y avisos legales

### HU-27 · Saber que es un índice de susceptibilidad, no un pronóstico · `Must`
**Como** periodista/ONG (P8), **quiero** que el sistema **no afirme falsamente "24 h de anticipación"**, **para** que la comunicación sea honesta.
- README y portal hablan de *índice diario de susceptibilidad*.
- Sin promesas de horizonte temporal.

### HU-28 · No confundir percentil con probabilidad · `Must`
**Como** analista (P5), **quiero** ver **percentil y PR-AUC** en lugar de una probabilidad "calibrada" engañosa, **para** interpretar correctamente el resultado.
- `/predict` y el popup muestran percentil.
- El README reporta PR-AUC vs prevalencia.
- Tooltips explican Top-1%/Top-5%.

### HU-29 · Conocer las limitaciones y el aviso legal · `Must`
**Como** ciudadano (P1), **quiero** un **aviso legal** que aclare que es un proyecto académico y que no reemplaza a las líneas oficiales (116/115/0800), **para** no depender de él en una emergencia real.
- Aviso visible en el portal.
- El reporte ciudadano muestra el disclaimer.

### HU-30 · Datos abiertos y reutilizables · `Should`
**Como** periodista/ONG (P8), **quiero** **acceder a los datos y resultados sin restricción**, **para** análisis y periodismo.
- Endpoints de lectura abiertos.
- GeoJSON/JSON estándar.
- Licencia MIT documentada.

### HU-31 · Distinguir datos reales de simulados · `Must`
**Como** ciudadano (P1), **quiero** **saber si lo que veo es real o simulado**, **para** no tomar decisiones sobre datos ficticios.
- Banner/popup distintivo "API offline – datos de referencia".
- Focos reales etiquetados.

---

## 🚒 ÉPICA 7 — Prevención y respuesta operativa

### HU-32 · Priorizar zonas por presupuesto de alerta · `Should`
**Como** autoridad (P4), **quiero** que las zonas se prioricen por **Top-1% (Rojo) y Top-5% (Amarillo)**, **para** enfocar recursos limitados.
- `classify()` es fuente única de verdad de los umbrales.
- Usada por API, scheduler y dashboard.

### HU-33 · Alertar proactivamente a todos los grupos en Rojo · `Should`
**Como** brigadista (P3), **quiero** que **cuando hay Rojo se notifique a todos los grupos**, **para** máxima difusión.
- El scheduler diferencia el mensaje por nivel (Rojo/Amarillo/Verde).

### HU-34 · Mensajes de alerta diferenciados por nivel · `Could`
**Como** líder comunitario (P2), **quiero** **mensajes distintos según el nivel**, **para** entender la urgencia.
- Plantillas por nivel.
- Terminología unificada (sin "Naranja").

### HU-35 · Reintentar envíos fallidos · `Should`
**Como** operador MLOps (P7), **quiero** que los envíos de WhatsApp **reintenten con backoff**, **para** tolerar fallos de la red/proveedor.
- Reintentos ante 429/5xx con espera exponencial.

---

## 📊 ÉPICA 8 — Dashboard operacional

### HU-36 · Monitorear el riesgo en un panel operativo · `Should`
**Como** autoridad (P4), **quiero** un **dashboard con mapa de calor y semáforo**, **para** monitorear en sala de control.
- Streamlit con Folium/Plotly.
- Mapa de calor continuo + capa semáforo.

### HU-37 · Ajustar el umbral de sensibilidad · `Could`
**Como** analista (P5), **quiero** **ajustar el umbral de sensibilidad**, **para** explorar el comportamiento del modelo.
- Slider funcional que filtra celdas por probabilidad.

### HU-38 · Notificar desde el panel · `Should`
**Como** brigadista (P3), **quiero** **notificar a brigadas desde el dashboard**, **para** agilizar la respuesta.
- El botón envía `POST /alert/whatsapp` con la cabecera `X-API-Key`.
- Resultado real (no "simulado").

### HU-39 · Ver reportes ciudadanos en el panel · `Could`
**Como** brigadista (P3), **quiero** **ver los reportes ciudadanos** integrados en el dashboard, **para** cruzarlos con el riesgo.
- Tabla con `GET /report/recent`.

### HU-40 · No mostrar información ficticia · `Must`
**Como** operador MLOps (P7), **quiero** que el dashboard **no muestre registros de alertas inventados ni selects sin efecto**, **para** evitar decisiones basadas en datos falsos.
- Se eliminaron `horizonte_sel`/región sin función y el log de alertas *hardcodeado*.

---

## 🔬 ÉPICA 9 — Ciencia de datos y pipeline (analista)

### HU-41 · Construir el dataset desde fuentes reales · `Must`
**Como** analista (P5), **quiero** **generar la grilla con features reales** (DEM, Sentinel-2 NDVI, ERA5/Open-Meteo, OSM, FIRMS), **para** entrenar con datos verosímiles.
- `grid_builder.py` orquesta `real_features.py`; grillas ~1 km².
- Etiqueta honesta desde FIRMS (`fire_count > 0`).

### HU-42 · Evitar fuga de datos en el vecindario · `Must`
**Como** analista (P5), **quiero** que las medias de vecindario se calculen por **KNN geográfico (no por el bloque de validación)**, **para** una evaluación creíble.
- `cKDTree`, k=8, sin autovecino.
- Sin `groupby(spatial_block_id)`.

### HU-43 · Representar variables circulares correctamente · `Should`
**Como** analista (P5), **quiero** que la **dirección del viento** se codifique como `sin/cos`, **para** no tratar 359° y 1° como opuestos.
- `viento_dir_sin`, `viento_dir_cos` en `FEATURE_ORDER`.
- Se descartan features constantes (`mes_sin/cos`).

### HU-44 · Entrenar con validación espacial honesta · `Must`
**Como** analista (P5), **quiero** **validación cruzada espacial out-of-fold** y métricas honestas, **para** no autoengañarme.
- `GroupKFold` por bloques de 50 km.
- Reporta ROC-AUC, **PR-AUC**, recall por Top-K y umbrales OOF.

### HU-45 · Optimizar hiperparámetros · `Should`
**Como** analista (P5), **quiero** **búsqueda bayesiana (Optuna)** sobre ROC-AUC espacial, **para** mejorar el modelo.
- `train_model.py` con Optuna.
- `scale_pos_weight` acotado.

### HU-46 · Construir un panel multi-fecha · `Could`
**Como** analista (P5), **quiero** **construir datasets de varias fechas**, **para** reducir el desajuste train/serve.
- `fetch_firms.py --start-date` y `grid_builder.py --ref-dates`.

### HU-47 · Recalcular features sin re-descargar · `Could`
**Como** analista (P5), **quiero** **recalcular features derivadas** sobre el dataset existente, **para** iterar rápido sin red.
- `data_pipeline/refresh_dataset.py` regenera KNN/viento.

### HU-48 · Ejecutar el pipeline completo automatizado · `Should`
**Como** operador MLOps (P7), **quiero** un **DAG que descargue, reentrene, puntúe y alerte**, **para** operación diaria.
- `airflow/dags/pipeline_dag.py` con tareas reales encadenadas y agenda diaria.

---

## 🛠️ ÉPICA 10 — MLOps, administración y mantenimiento

### HU-49 · Conocer la versión y fecha del modelo · `Must`
**Como** operador MLOps (P7), **quiero** **consultar la versión y fecha de entrenamiento**, **para** auditar qué modelo está sirviendo.
- `GET /health` devuelve `model_version`, `training_date`, `thresholds`.

### HU-50 · Reentrenar y versionar el modelo · `Must`
**Como** operador MLOps (P7), **quiero** **reentrenar y registrar metadatos**, **para** trazabilidad MLOps.
- `models/model_metadata.json` con métricas, umbrales de servicio/OOF y versión.

### HU-51 · Ejecutar pruebas automatizadas y lint · `Must`
**Como** desarrollador (P6), **quiero** **CI con lint (ruff) y pruebas (pytest)**, **para** no romper el sistema al cambiar código.
- `.github/workflows/ci.yml`.
- 32 tests; `ruff` limpio.

### HU-52 · Desplegar con Docker · `Could`
**Como** operador MLOps (P7), **quiero** **levantar la API con Docker y healthcheck**, **para** despliegues reproducibles.
- `docker-compose.yml` solo con la API + `healthcheck` + `restart`.

### HU-53 · Documentar el sistema completo · `Should`
**Como** analista (P5), **quiero** un **volcado del código fuente** y memoria técnica, **para** revisión académica.
- `CODIGO_COMPLETO_SISTEMA.txt` y `docs/Memoria_Tecnica_Capstone.md` actualizados.

---

## 🔐 ÉPICA 11 — Seguridad y protección de datos

### HU-54 · Proteger los endpoints de alerta · `Must`
**Como** operador MLOps (P7), **quiero** que **/alert/* requiera API key**, **para** evitar envíos maliciosos de WhatsApp.
- `require_admin_key` (`X-API-Key`).
- `401` si la clave es incorrecta.

### HU-55 · CORS restringido · `Must`
**Como** operador MLOps (P7), **quiero** una **lista blanca de orígenes**, **para** reducir superficie de ataque.
- CORS configurable con `ALLOWED_ORIGINS`.
- Orígenes ajenos bloqueados.

### HU-56 · No versionar secretos · `Must`
**Como** operador MLOps (P7), **quiero** que **`.env` no esté en Git**, **para** no filtrar credenciales.
- `.env` en `.gitignore` y **fuera del índice**.
- `.env.example` sin credenciales reales.

### HU-57 · Gestionar mejor los secretos expuestos · `Must`
**Como** operador MLOps (P7), **quiero** **rotar las claves filtradas** (FIRMS, CDS, Green API), **para** cerrar el riesgo tras detectarlas en el historial.
- Claves regeneradas.
- Opcionalmente, purga del historial.

---

## ♿ ÉPICA 12 — Accesibilidad y usabilidad

### HU-58 · Usar el portal en el celular · `Must`
**Como** ciudadano (P1), **quiero** una **interfaz responsive**, **para** consultar desde mi teléfono.
- Layout adaptable.
- Mapa usable en pantallas pequeñas.

### HU-59 · Navegación sencilla y en español llano · `Must`
**Como** ciudadano (P1), **quiero** **lenguaje claro y accesos directos**, **para** usar el sistema sin capacitación.
- Secciones con anclas.
- Textos simples, sin jerga.

### HU-60 · Navegar con teclado y lectores de pantalla · `Should`
**Como** ciudadano con discapacidad (P1), **quiero** **accesibilidad básica (ARIA/contraste)**, **para** usar el sistema con apoyos.
- Contraste adecuado.
- Etiquetas accesibles en controles.

---

## 🌐 ÉPICA 13 — Apertura, comunidad y gobernanza

### HU-61 · Acceso libre sin registro · `Must`
**Como** público general (P1), **quiero** usar el sistema **sin crear cuenta ni pagar**, **para** beneficiarme de inmediato con el menor esfuerzo posible.
- Sin login, sin registro y sin costo.
- Acceso directo por navegador.

### HU-62 · Usar el sistema sin instalar una aplicación · `Must`
**Como** público general (P1), **quiero** acceder desde un **navegador web (móvil o PC)**, **para** no depender de tiendas de apps ni instalaciones.
- Portal web autosuficiente; no requiere instalar nada.

### HU-63 · Independencia de toda entidad · `Must`
**Como** periodista/ONG (P8), **quiero** que el sistema **no represente a una institución**, **para** confiar en su neutralidad e independencia.
- Sin login corporativo ni marca institucional.
- Se declara explícitamente como proyecto ciudadano/académico abierto.

### HU-64 · Replicar o desplegar mi propia instancia · `Should`
**Como** colaborador/a open source (P6) o comunidad técnica (P5), **quiero** **clonar y desplegar el sistema** para otra región, **para** adaptarlo a mi zona sin pedir permiso a nadie.
- Repositorio con instrucciones (Docker, CI); datos reemplazables; licencia MIT.

### HU-65 · Contribuir al proyecto abierto · `Could`
**Como** colaborador/a open source (P6), **quiero** **aportar código, datos o correcciones**, **para** mejorar un servicio de uso común.
- Repositorio público con issues/PR y guía de contribución.

### HU-66 · Autoorganizar el canal de avisos de mi comunidad · `Should`
**Como** comunidad organizada (P2), **quiero** **gestionar mi propio grupo de avisos**, **para** no depender de un tercero ni de una entidad.
- Los grupos son administrados por la comunidad; el sistema solo publica el boletín.
- El alta/baja del canal la controla la propia comunidad.

---

## 🧱 Historias no funcionales (atributos de calidad — ISO/IEC 25010)

| ID | Categoría | Como… | Quiero… | Criterio verificable |
|---|---|---|---|---|
| HUN-01 | Adecuación funcional | P4 | resultados correctos y completos | Auditorías `audit_*` al 100% |
| HUN-02 | Eficiencia | P6 | latencia baja | `/predict` < 2 ms/celda |
| HUN-03 | Compatibilidad | P6 | interoperabilidad estándar | JSON/GeoJSON, REST, CORS configurable |
| HUN-04 | Usabilidad | P1 | operabilidad sin fricción | Portal sin errores de consola; leyenda clara |
| HUN-05 | Fiabilidad | P7 | tolerancia a fallos | Reintentos WhatsApp; fallback honesto API offline |
| HUN-06 | Seguridad | P7 | protección de acceso | API key, rate-limit, validación de bbox, CORS |
| HUN-07 | Mantenibilidad | P6 | código mantenible y probado | ruff limpio, 32 tests, `FEATURE_ORDER` única fuente de verdad |
| HUN-08 | Portabilidad | P7 | despliegue portable | Docker + CI multi-entorno |

---

## 🔗 Matriz de trazabilidad (HU → módulo/endpoint)

| HU | Módulo / Endpoint |
|---|---|
| HU-01..07 | `web/index.html`, `web/app.js`, `GET /risk/today`, `GET /health` |
| HU-08..11 | `GET /firms/hotspots`, `web/app.js` |
| HU-12..15 | `POST /report/citizen`, `GET /report/recent`, `app/main.py` |
| HU-16..20 | `app/scheduler.py`, `POST /alert/whatsapp`, `POST /alert/daily`, `GET /alert/status` |
| HU-21..26 | `POST /predict`, `POST /propagate`, `/openapi.json`, `GET /model/importance`, `GET /social/matrix`, `GET /report/pdf` |
| HU-27..31 | `README.md`, portal, `app/model.py` (`classify`, percentiles) |
| HU-32..35 | `app/model.py`, `app/scheduler.py`, `app/whatsapp_alerts.py` |
| HU-36..40 | `dashboard/app.py`, `GET /report/recent` |
| HU-41..48 | `data_pipeline/*`, `airflow/dags/pipeline_dag.py` |
| HU-49..53 | `GET /health`, `models/model_metadata.json`, `pyproject.toml`, `.github/workflows/ci.yml`, `docker-compose.yml` |
| HU-54..57 | `app/security.py`, `.gitignore`, `.env.example` |
| HU-58..60 | `web/index.html`, `web/styles.css`, `web/app.js` |

---

## 📌 Priorización (MoSCoW) resumida

- **Must:** HU-01, HU-02, HU-03, HU-08, HU-11, HU-12, HU-13, HU-16, HU-21, HU-27, HU-28, HU-29, HU-31, HU-40, HU-41, HU-42, HU-44, HU-49, HU-50, HU-51, HU-54, HU-55, HU-56, HU-57, HU-58, HU-59, HU-61, HU-62, HU-63 · HUN-01, HUN-02, HUN-06, HUN-07, HUN-08
- **Should:** HU-04, HU-05, HU-06, HU-07, HU-09, HU-14, HU-15, HU-17, HU-18, HU-20, HU-22, HU-23, HU-24, HU-26, HU-30, HU-32, HU-33, HU-35, HU-36, HU-38, HU-43, HU-45, HU-48, HU-53, HU-60, HU-64, HU-66
- **Could:** HU-10, HU-19, HU-25, HU-34, HU-37, HU-39, HU-46, HU-47, HU-52, HU-65

---

## 📎 Notas de uso

- El formato sigue la plantilla **Connextra** ("Como … quiero … para …").
- El sistema es **abierto y sin cliente institucional** (ver *Alcance y modelo de gobernanza*); las "autoridades" (P4) figuran como **aliados potenciales**, no como dueños del producto.
- La columna de **trazabilidad** permite verificar que cada historia corresponde a funcionalidad **realmente implementada** (no aspiracional).
- La versión tabular para tablero (Jira/Trello/Plane) está en **`docs/Historias_de_Usuario.csv`**.
- Las historias `Must` constituyen el **MVP**; `Should`/`Could` forman el *backlog* de mejora.
