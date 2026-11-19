# Informe de Resultados de Responsabilidad Social y Ética Profesional

> **Curso:** Capstone Project Sistemas (INVE1535 — 10° Ciclo, 2026-2, UPN)
> **Evidencia del Sílabo:** Semanas 12 y 13 (Presentación de resultados de responsabilidad social; impacto social, económico, ambiental, legal/profesional y tecnológico)

---

## 1. Alineamiento con Responsabilidad Social Universitaria y ODS

Aunque la ficha general del sílabo indica "ODS: No aplica" a nivel genérico de asignatura, la Ficha de Práctica de Campo (Semana 1 y Semana 13) establece documentar el impacto social/ambiental y los ODS cuando aplique. El proyecto **AlertaForestal Perú** contribuye directamente a:

- **ODS 13 — Acción por el Clima:** Fortalece la capacidad de prevención y adaptación ante incendios forestales agravados por sequía y variabilidad climática en los Andes del norte del Perú (Cajamarca).
- **ODS 15 — Vida de Ecosistemas Terrestres:** Apoya la conservación de bosques, pastizales altoandinos y suelos agrícolas frente a la degradación por incendios forestales.
- **ODS 11 — Ciudades y Comunidades Sostenibles:** Promueve comunidades rurales más resilientes mediante alerta temprana gratuita y sin brecha digital.

---

## 2. Acciones Concretas de Responsabilidad Social Implementadas en el Producto

1. **Acceso universal, gratuito y sin registro:** El portal ciudadano desplegado en Render (`https://alerta-temprana-de-incendios-forestales.onrender.com/web/`) no requiere login, pago ni instalación de apps, eliminando barreras económicas y tecnológicas para pobladores rurales.
2. **Inclusión digital y alfabetización del riesgo:** Se diseñó la sección *"Cómo usar el sistema"* en 4 pasos simples, un semáforo visual universal (Verde/Amarillo/Rojo), directorio de emergencias (Bomberos 116, INDECI 115, SERFOR 0800-11-070) y difusión por **WhatsApp** (el canal más utilizado en zonas rurales de Cajamarca) en 6 grupos provinciales.
3. **Licencia abierta (MIT) y transparencia científica:** Código, datos y métricas honestas (incluyendo sus limitaciones: ROC-AUC 0.649, prevalencia 0.066%, Top-1% cercano al azar) publicados abiertamente para evitar alarmismo o falsa confianza.
4. **Protección de datos personales desde el diseño (Ley N.° 29733 y D.S. N.° 016-2024-JUS):** El formulario de reporte ciudadano **no solicita nombre, DNI, correo ni teléfono** (verificado por prueba automatizada `test_cr08_citizen_report_data_minimization`).

---

## 3. Matriz Consolidada de Impactos y Mitigaciones (Semana 13)

| Dimensión | Impacto Positivo Verificado | Riesgo / Límite Identificado | Medida de Mitigación Aplicada |
|---|---|---|---|
| **Social** | Democratiza el acceso a información preventiva de incendios en Cajamarca y facilita el reporte ciudadano georreferenciado. | Brecha de conectividad rural y posible confusión de alertas preventivas con incendios confirmados. | Mensajes breves por WhatsApp, semáforo llano, etiquetas explícitas *"riesgo estimado"* y *"requiere verificación"*. |
| **Ambiental** | Focaliza la vigilancia preventiva en el Top-10% / Top-20% de mayor susceptibilidad (capturando hasta 45.11% de focos). | No extingue incendios ni captura aún el vigor real de combustible vía NDVI (importancia SHAP = 0). | Declarado explícitamente como herramienta de apoyo; recomendada auditoría NDVI y panel multi-fecha. |
| **Económico** | Costo de licencias S/ 0 (software libre y datos abiertos); costo operativo estimado S/ 180/mes frente a S/ 3 520/mes de consolidación manual. | Dependencia de planes gratuitos (Render, Green API) y mantenimiento voluntario. | Contenedor Docker portable a cualquier servidor municipal o universitario de bajo costo. |
| **Legal / Profesional** | Cumplimiento de minimización de datos (Ley 29733), cabeceras de seguridad, CORS restringido y API Key en endpoints sensibles. | Incidente histórico INC-01 (`.env` versionado) y `ADMIN_API_KEY` opcional en modo demo. | Retiro de `.env` del índice Git, `.gitignore`, `.env.example`, rotación obligatoria de claves documentada. |
| **Tecnológico** | Fusión reproducible de 5 fuentes heterogéneas, 58 pruebas automatizadas (4 niveles), CI/CD y límite departamental oficial INEI (118 vértices). | Entrenamiento con una sola fecha de referencia (45 positivos reales). | Pipeline ya soporta `--ref-dates` y `--start-date` para escalamiento multi-temporal. |

---

## 4. Juicio Profesional Sustentado

Con base en la evidencia técnica y ética recopilada, el equipo emite un **juicio profesional favorable condicionado**: la solución es viable para **despliegue piloto comunitario y académico de priorización preventiva con verificación humana**, pero **no debe operar como sistema oficial de alarma determinista** hasta completar la validación de campo con usuarios, la rotación definitiva de credenciales y el reentrenamiento con un panel multi-temporal de una temporada seca completa (mayo–noviembre).
