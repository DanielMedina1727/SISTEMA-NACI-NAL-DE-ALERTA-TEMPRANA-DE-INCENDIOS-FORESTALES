"""
Dashboard Operacional del Sistema de Alerta Temprana de Incendios Forestales.
Incluye visualización de zonas semáforo (Verde, Amarillo, Rojo), mapa de calor (Heatmap) continua y control de capas.

Correr con: streamlit run dashboard/app.py
"""
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import folium
from folium.plugins import HeatMap
import pandas as pd
import plotly.express as px
import requests
import streamlit as st
import streamlit.components.v1 as components

try:
    from streamlit_folium import st_folium
except ImportError:
    st_folium = None

API_URL = "http://127.0.0.1:5050"
COLOR_MAP = {"Verde": "#2ecc71", "Amarillo": "#f1c40f", "Rojo": "#e74c3c"}


def _admin_headers() -> dict:
    """Cabecera X-API-Key si ADMIN_API_KEY está configurada (endpoints de alerta)."""
    key = os.getenv("ADMIN_API_KEY", "").strip()
    return {"X-API-Key": key} if key else {}

# Fuente única de verdad del semáforo y de las features (app/model.py)
from app.model import RiskModel, FEATURE_ORDER, classify, THRESHOLDS

st.set_page_config(
    page_title="Centro de Control | Alerta de Incendios",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo visual Glassmorphism Dark Mode Operacional
st.markdown("""
    <style>
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
    }
    .metric-card {
        background: linear-gradient(135deg, #161b22 0%, #21262d 100%);
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 16px;
    }
    </style>
""", unsafe_allow_html=True)

# Título Operacional
st.title("🔥 Centro de Control - Predicción de Riesgo de Incendios Forestales")
st.caption("Índice diario de susceptibilidad georreferenciado, zonas semáforo (Verde/Amarillo/Rojo) y mapa de calor de ignición")

# Sidebar Operacional
with st.sidebar:
    st.image("https://img.icons8.com/color/96/fire-element.png", width=65)
    st.header("⚙️ Panel de Operación")

    # Comprobar salud de la API
    api_online = False
    try:
        r_health = requests.get(f"{API_URL}/health", timeout=2)
        if r_health.status_code == 200:
            api_online = True
            st.success("🟢 Servidor API en Línea")
        else:
            st.error("🔴 Servidor API Offline")
    except Exception:
        st.warning("⚠️ Modo Simulación (API no detectada)")

    st.markdown("---")
    st.caption("📍 Cobertura: región Cajamarca (Perú)")
    st.caption("📅 Índice diario de susceptibilidad (NO es un pronóstico a 24/48 h)")
    min_prob_slider = st.slider("🔍 Umbral de Sensibilidad", 0.0, 1.0, 0.0, 0.05)
    
    st.markdown("---")
    st.subheader("🎨 Opciones del Mapa")
    show_heatmap = st.checkbox("🔥 Capa de Mapa de Calor (HeatMap)", value=True)
    show_polygons = st.checkbox("🟩 Zonas Semáforo (Celdas 1km²)", value=True)

    st.markdown("---")
    st.subheader("📄 Ficha de Emergencia")
    if api_online:
        st.download_button(
            label="Descargar Reporte Ejecutivo PDF",
            data=requests.get(f"{API_URL}/report/pdf").content,
            file_name="Reporte_Ejecutivo_Incendios_Cajamarca.pdf",
            mime="application/pdf"
        )
    else:
        st.info("Conecta la API para descargar el PDF oficial.")

# Cargar GeoJSON de la API o dataset local
features = []
if api_online:
    try:
        resp = requests.get(f"{API_URL}/risk/today?limit=1200", timeout=5)
        if resp.status_code == 200 and resp.text.strip():
            geojson_data = resp.json()
            features = geojson_data.get("features", [])
        else:
            st.sidebar.warning(f"HTTP {resp.status_code} en /risk/today. Usando dataset local.")
    except Exception:
        st.sidebar.warning("Cargando desde dataset local de Cajamarca.")

if not features:
    grid_path = Path(__file__).parent.parent / "data" / "dataset.csv"

    if grid_path.exists():
        df_full = pd.read_csv(grid_path)
        # Filtrar espacialmente la zona 2D de Cajamarca
        caj_df = df_full[
            (df_full["latitude"] >= -7.7592) & (df_full["latitude"] <= -4.5519) &
            (df_full["longitude"] >= -79.4517) & (df_full["longitude"] <= -77.7389)
        ]
        df_sample = caj_df.head(600) if not caj_df.empty else df_full.head(600)
        # Inferencia REAL con el modelo (mismos umbrales y features que la API).
        try:
            _model = RiskModel()
            for col in FEATURE_ORDER:
                if col not in df_sample.columns:
                    df_sample[col] = 0.0
            _probas = _model.model.predict_proba(df_sample[FEATURE_ORDER])[:, 1]
        except Exception as exc:
            st.sidebar.warning(f"Modelo no disponible ({exc}). Fallback a etiqueta FIRMS.")
            _probas = df_sample.get("target", pd.Series(0.0, index=df_sample.index)).astype(float).values

        cell_size = 0.009
        for i, (idx, row) in enumerate(df_sample.iterrows()):
            lon, lat = float(row["longitude"]), float(row["latitude"])
            prob = float(_probas[i])
            nivel = classify(prob)
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [lon - cell_size/2, lat - cell_size/2],
                        [lon + cell_size/2, lat - cell_size/2],
                        [lon + cell_size/2, lat + cell_size/2],
                        [lon - cell_size/2, lat + cell_size/2],
                        [lon - cell_size/2, lat - cell_size/2]
                    ]]
                },
                "properties": {
                    "grid_id": str(row["grid_id"]),
                    "probabilidad": round(prob, 4),
                    "nivel": nivel,
                    "temp_2m": float(row.get("temp_2m", 26.0)),
                    "humedad_relativa": float(row.get("humedad_relativa", 35.0)),
                    "viento_velocidad": float(row.get("viento_velocidad", 20.0)),
                    "viento_direccion": float(row.get("viento_direccion", 45.0)),
                    "pendiente_pct": float(row.get("pendiente_pct", 15.0)),
                    "ndvi": float(row.get("ndvi", 0.45)),
                }
            })


# Filtro por umbral
filtered_features = [f for f in features if f["properties"].get("probabilidad", 0) >= min_prob_slider]

# Métricas Operacionales
total_cnt = len(filtered_features)
rojas_cnt = sum(1 for f in filtered_features if f["properties"]["nivel"] == "Rojo")
amarillas_cnt = sum(1 for f in filtered_features if f["properties"]["nivel"] == "Amarillo")
verdes_cnt = sum(1 for f in filtered_features if f["properties"]["nivel"] == "Verde")

m1, m2, m3, m4 = st.columns(4)
m1.metric("📊 Total Grillas Monitoreadas", f"{total_cnt} celdas")
m2.metric("🔴 Alerta Roja (Despacho)", f"{rojas_cnt}", delta="Atención Brigadas", delta_color="inverse")
m3.metric("🟡 Vigilancia (Patrullaje)", f"{amarillas_cnt}")
m4.metric("🟢 Zonas Seguras", f"{verdes_cnt}")

st.markdown("---")

# Pestañas Exclusivamente Operacionales
tab1, tab2, tab3 = st.tabs([
    "🗺️ Mapa de Riesgo en Tiempo Real",
    "💨 Simulador de Propagación por Viento",
    "🚨 Despacho de Alertas & Notificaciones"
])

# ----------------------------------------------------
# PESTAÑA 1: MAPA OPERACIONAL Y MAPA DE CALOR
# ----------------------------------------------------
with tab1:
    st.subheader("🗺️ Cobertura de Riesgo Georreferenciado & Mapa de Calor")
    
    m = folium.Map(location=[-7.16, -78.5], zoom_start=9, tiles="OpenStreetMap")

    # 1. Capa de Mapa de Calor (HeatMap Continua)
    if show_heatmap:
        heat_data = []
        for f in filtered_features:
            props = f["properties"]
            prob = props.get("probabilidad", 0)
            coords = f["geometry"]["coordinates"][0]
            # Usar centro de la grilla
            lons = [pt[0] for pt in coords]
            lats = [pt[1] for pt in coords]
            c_lat, c_lon = sum(lats)/len(lats), sum(lons)/len(lons)
            heat_data.append([c_lat, c_lon, prob])

        if heat_data:
            HeatMap(
                heat_data,
                min_opacity=0.3,
                max_val=1.0,
                radius=18,
                blur=15,
                gradient={0.2: '#2ecc71', 0.5: '#f1c40f', 0.8: '#e74c3c', 1.0: '#900c3f'}
            ).add_to(m)

    # 2. Capa de Polígonos Semáforo (Verde, Amarillo, Rojo)
    if show_polygons:
        for f in filtered_features:
            props = f["properties"]
            nivel = props.get("nivel", "Verde")
            color = COLOR_MAP.get(nivel, "#2ecc71")

            coords = f["geometry"]["coordinates"][0]
            folium_coords = [[pt[1], pt[0]] for pt in coords]

            popup_html = f"""
            <div style="font-family:sans-serif; font-size:12px; width:210px;">
                <b style="font-size:14px;">Grilla: {props.get('grid_id')}</b><br/><hr style="margin:4px 0;"/>
                <b>Estado:</b> <span style="color:{color}; font-weight:bold;">{nivel}</span><br/>
                <b>Probabilidad:</b> {props.get('probabilidad', 0):.1%}<br/>
                <b>Temperatura:</b> {props.get('temp_2m', 0)} °C<br/>
                <b>Humedad:</b> {props.get('humedad_relativa', 0)} %<br/>
                <b>Viento:</b> {props.get('viento_velocidad', 0)} km/h ({props.get('viento_direccion', 0)}°)<br/>
                <b>Pendiente:</b> {props.get('pendiente_pct', 0)} %
            </div>
            """

            folium.Polygon(
                locations=folium_coords,
                color="black",
                weight=0.6,
                fill_color=color,
                fill_opacity=0.60,
                popup=folium.Popup(popup_html, max_width=250),
            ).add_to(m)

    # 3. Leyenda Flotante del Semáforo
    legend_html = f"""
     <div style="
     position: fixed; 
     bottom: 30px; right: 30px; width: 190px; height: 125px; 
     background-color: rgba(13, 17, 23, 0.85);
     border:2px solid #30363d; z-index:9999; font-size:12px;
     border-radius:10px; padding: 10px; color: #c9d1d9;
     box-shadow: 0 4px 15px rgba(0,0,0,0.5);
     ">
     <b>Leyenda de Riesgo</b><br/>
     <i style="background:#e74c3c; width:12px; height:12px; display:inline-block; border-radius:50%; margin-right:5px;"></i> <b>Rojo:</b> Top 1% (≥ {THRESHOLDS['rojo']:.1%})<br/>
     <i style="background:#f1c40f; width:12px; height:12px; display:inline-block; border-radius:50%; margin-right:5px;"></i> <b>Amarillo:</b> Top 5% (≥ {THRESHOLDS['amarillo']:.1%})<br/>
     <i style="background:#2ecc71; width:12px; height:12px; display:inline-block; border-radius:50%; margin-right:5px;"></i> <b>Verde:</b> Resto del territorio<br/>
     </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    if st_folium is not None:
        st_folium(m, width="100%", height=560)
    else:
        components.html(m._repr_html_(), height=560)

# ----------------------------------------------------
# PESTAÑA 2: PROPAGACIÓN POR VIENTO
# ----------------------------------------------------
with tab2:
    st.subheader("💨 Proyección de Expansión del Fuego")
    st.markdown("Calcula la trayectoria proyectada de fuego/humo hacia celdas vecinas impulsadas por vectores de viento.")

    col_sim1, col_sim2 = st.columns([1, 1.5])

    with col_sim1:
        st.markdown("### Parámetros del Vector de Viento")
        red_grid_options = [f["properties"]["grid_id"] for f in filtered_features if f["properties"]["nivel"] == "Rojo"]
        if not red_grid_options:
            red_grid_options = ["-78.5000_-7.1600", "-78.5500_-7.2000"]

        selected_grid_prop = st.selectbox("Grilla en Alerta Roja:", red_grid_options)
        v_dir_input = st.slider("Dirección del Viento (grados)", 0, 360, 45, 15)
        v_vel_input = st.slider("Velocidad del Viento (km/h)", 5, 80, 30)

        if st.button("🚀 Calcular Alcance de Propagación"):
            try:
                if api_online:
                    r_prop = requests.post(f"{API_URL}/propagate?grid_id={selected_grid_prop}&viento_direccion={v_dir_input}&viento_velocidad={v_vel_input}").json()
                else:
                    r_prop = {
                        "origen": selected_grid_prop,
                        "direccion_viento": "NE",
                        "velocidad_viento": v_vel_input,
                        "grillas_afectadas": [
                            {"grid_id": "-78.4910_-7.1510", "nivel": "Amarillo", "probabilidad_recibir_fuego": 0.36},
                            {"grid_id": "-78.4820_-7.1420", "nivel": "Amarillo", "probabilidad_recibir_fuego": 0.22},
                            {"grid_id": "-78.4730_-7.1330", "nivel": "Amarillo", "probabilidad_recibir_fuego": 0.13},
                        ]
                    }

                st.session_state["prop_result"] = r_prop
            except Exception as ex:
                st.error(f"Error en cálculo: {ex}")

    with col_sim2:
        st.markdown("### Grillas Adyacentes en Riesgo por Viento")
        if "prop_result" in st.session_state:
            res = st.session_state["prop_result"]
            st.success(f"📍 Origen: **{res.get('origen')}** | Rumbo del Viento: **{res.get('direccion_viento')}** ({res.get('velocidad_viento')} km/h)")
            
            affected_items = res.get("grillas_afectadas", [])
            if affected_items:
                df_aff = pd.DataFrame(affected_items)
                st.dataframe(df_aff, use_container_width=True)

                fig_prop = px.bar(
                    df_aff,
                    x="grid_id",
                    y="probabilidad_recibir_fuego",
                    color="probabilidad_recibir_fuego",
                    color_continuous_scale="Reds",
                    title="Probabilidad de Impacto en Celdas Vecinas",
                    labels={"probabilidad_recibir_fuego": "Probabilidad", "grid_id": "Grilla Vecina"}
                )
                st.plotly_chart(fig_prop, use_container_width=True)
        else:
            st.info("Selecciona una grilla y presiona 'Calcular Alcance' para ver el área proyectada.")

# ----------------------------------------------------
# PESTAÑA 3: DESPACHO DE ALERTAS
# ----------------------------------------------------
with tab3:
    st.subheader("🚨 Gestión y Despacho de Alertas a Brigadas")
    st.markdown("Envío automático de notificaciones de emergencia con coordenadas GPS directas a los equipos en campo.")

    col_alt1, col_alt2 = st.columns([1.2, 1])

    with col_alt1:
        st.markdown("### Enviar Alerta Crítica por WhatsApp")
        grid_target_alert = st.selectbox("Grilla Objetiva para Despacho:", red_grid_options, key="alert_target")
        
        try:
            lon_a, lat_a = float(grid_target_alert.split("_")[0]), float(grid_target_alert.split("_")[1])
        except Exception:
            lon_a, lat_a = -78.50, -7.16

        st.write(f"**Coordenadas GPS:** `{lat_a:.4f}, {lon_a:.4f}`")
        st.write(f"**Enlace a Mapa:** [Abrir Google Maps](https://www.google.com/maps?q={lat_a},{lon_a})")

        if st.button("🔴 Notificar Inmediatamente a Bomberos y Rondas"):
            if not api_online:
                st.warning(
                    "El envío de alertas requiere la API en línea. "
                    "Inicia el servidor (INICIAR_SERVIDOR_7AM.bat o "
                    "`python -m uvicorn app.main:app --port 5050`)."
                )
            else:
                try:
                    r_alert = requests.post(f"{API_URL}/alert/whatsapp", json={
                        "grid_id": grid_target_alert,
                        "lat": lat_a,
                        "lon": lon_a,
                        "confianza": 0.95
                    }, headers=_admin_headers(), timeout=20)
                    if r_alert.status_code == 200:
                        st.success("📩 Alerta enviada por WhatsApp a las brigadas.")
                    elif r_alert.status_code == 401:
                        st.error("🔒 La API exige X-API-Key (define ADMIN_API_KEY en .env).")
                    else:
                        st.error(f"Error de la API ({r_alert.status_code}): {r_alert.text[:200]}")
                except Exception as e:
                    st.error(f"Error transmitiendo alerta: {e}")

    with col_alt2:
        st.markdown("### Reportes Ciudadanos Recientes")
        reports = []
        if api_online:
            try:
                rr = requests.get(f"{API_URL}/report/recent?limit=8", timeout=5).json()
                reports = rr.get("reports", [])
            except Exception:
                reports = []
        if reports:
            df_log = pd.DataFrame([
                {
                    "Fecha/Hora (UTC)": str(r.get("timestamp", ""))[:19].replace("T", " "),
                    "Tipo": r.get("incident_label", r.get("incident_type", "")),
                    "Lat": r.get("lat"),
                    "Lon": r.get("lon"),
                    "Zona": r.get("reporter_zone") or "-",
                }
                for r in reports
            ])
            st.dataframe(df_log, use_container_width=True)
        elif api_online:
            st.info("Aún no hay reportes ciudadanos registrados.")
        else:
            st.info("Conecta la API para ver los reportes ciudadanos.")
