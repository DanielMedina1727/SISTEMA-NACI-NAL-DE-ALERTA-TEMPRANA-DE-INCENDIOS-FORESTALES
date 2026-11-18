# Variables de Entorno requeridas en Render

Configúralas en **Render → tu servicio → Environment → Add Environment Variable**.

## ✅ Obligatorias para WhatsApp (Green API)

| Variable | Descripción | Dónde obtenerla |
|---|---|---|
| `GREEN_API_INSTANCE_ID` | ID de instancia Green API | [app.green-api.com](https://app.green-api.com) → Mi instancia |
| `GREEN_API_TOKEN` | Token de autenticación Green API | [app.green-api.com](https://app.green-api.com) → Mi instancia |
| `WA_GROUP_CAJAMARCA` | ChatID del grupo WhatsApp de Cajamarca | Verde en la app de WhatsApp → ver info del grupo |
| `WA_GROUP_SAN_MARCOS` | ChatID del grupo de San Marcos | Ídem |
| `WA_GROUP_SAN_PABLO` | ChatID del grupo de San Pablo | Ídem |
| `WA_GROUP_BAMBAMARCA` | ChatID del grupo de Bambamarca | Ídem |
| `WA_GROUP_CELENDIN` | ChatID del grupo de Celendín | Ídem |
| `WA_GROUP_CHOTA` | ChatID del grupo de Chota | Ídem |

> **Nota:** El ChatID de un grupo de WhatsApp tiene el formato `120363XXXXXXXXXX@g.us`.  
> Para obtenerlo: envía un mensaje desde la instancia Green API al grupo y lee el `chatId` en la respuesta.

## ⚡ Recomendadas

| Variable | Descripción | Valor de ejemplo |
|---|---|---|
| `ADMIN_API_KEY` | Clave secreta para endpoints admin (`/alert/whatsapp`, `/alert/daily`) | Cualquier string seguro (p.ej. `mi-clave-2024`) |
| `FIRMS_MAP_KEY` | Clave NASA FIRMS para datos satelitales reales | Regístrate gratis en [firms.modaps.eosdis.nasa.gov](https://firms.modaps.eosdis.nasa.gov/api/area/) |

## 🔍 Cómo verificar que están configuradas

Haz un GET a:
```
https://alerta-temprana-de-incendios-forestales.onrender.com/health
```
La respuesta incluye `"scheduler_activo": true`. Luego prueba `/alert/daily` (POST) para disparar una alerta manual.

## 📋 ChatID de grupo WhatsApp — Pasos detallados

1. En [app.green-api.com](https://app.green-api.com), ve a **API → getChats**
2. Envía la solicitud y busca el grupo en la lista (campo `name`)
3. Copia el campo `id` → ese es tu `ChatID` para el `.env` / Render

---
*Generado automáticamente para AlertaForestal Perú v2.3.0*
