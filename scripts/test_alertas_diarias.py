# -*- coding: utf-8 -*-
"""
Script de prueba de alertas automaticas.
Ejecuta el mismo flujo que el scheduler diario pero directamente,
sin necesidad de tener la API FastAPI corriendo.
"""
import sys
import os
import io
import logging

# Forzar UTF-8 en la consola de Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Asegurar que el path del proyecto este en PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

from app.scheduler import ZONAS, _classify_zone, _build_message, _get_zone_group_id
from app.whatsapp_alerts import get_accounts, send_message_to_chat

# ─── Datos de riesgo de prueba (simulando respuesta del modelo) ───
# Generamos grillas sintéticas dentro de cada zona con niveles variados
DEMO_FEATURES = [
    # San Marcos — ROJO
    {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[
        [-78.10, -7.50], [-78.09, -7.50], [-78.09, -7.49], [-78.10, -7.49], [-78.10, -7.50]
    ]]}, "properties": {"grid_id": "SM_001", "probabilidad": 0.82, "nivel": "Rojo"}},
    {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[
        [-78.08, -7.45], [-78.07, -7.45], [-78.07, -7.44], [-78.08, -7.44], [-78.08, -7.45]
    ]]}, "properties": {"grid_id": "SM_002", "probabilidad": 0.76, "nivel": "Rojo"}},
    {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[
        [-78.12, -7.40], [-78.11, -7.40], [-78.11, -7.39], [-78.12, -7.39], [-78.12, -7.40]
    ]]}, "properties": {"grid_id": "SM_003", "probabilidad": 0.51, "nivel": "Amarillo"}},

    # San Pablo — AMARILLO
    {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[
        [-78.92, -7.10], [-78.91, -7.10], [-78.91, -7.09], [-78.92, -7.09], [-78.92, -7.10]
    ]]}, "properties": {"grid_id": "SP_001", "probabilidad": 0.48, "nivel": "Amarillo"}},
    {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[
        [-78.90, -7.05], [-78.89, -7.05], [-78.89, -7.04], [-78.90, -7.04], [-78.90, -7.05]
    ]]}, "properties": {"grid_id": "SP_002", "probabilidad": 0.39, "nivel": "Amarillo"}},

    # Bambamarca — VERDE
    {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[
        [-78.50, -6.70], [-78.49, -6.70], [-78.49, -6.69], [-78.50, -6.69], [-78.50, -6.70]
    ]]}, "properties": {"grid_id": "BB_001", "probabilidad": 0.18, "nivel": "Verde"}},

    # Celendín — AMARILLO
    {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[
        [-78.10, -6.80], [-78.09, -6.80], [-78.09, -6.79], [-78.10, -6.79], [-78.10, -6.80]
    ]]}, "properties": {"grid_id": "CE_001", "probabilidad": 0.44, "nivel": "Amarillo"}},

    # Chota — VERDE
    {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[
        [-78.70, -6.50], [-78.69, -6.50], [-78.69, -6.49], [-78.70, -6.49], [-78.70, -6.50]
    ]]}, "properties": {"grid_id": "CH_001", "probabilidad": 0.12, "nivel": "Verde"}},

    # Cajamarca — ROJO
    {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[
        [-78.50, -7.10], [-78.49, -7.10], [-78.49, -7.09], [-78.50, -7.09], [-78.50, -7.10]
    ]]}, "properties": {"grid_id": "CAJ_001", "probabilidad": 0.88, "nivel": "Rojo"}},
    {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[
        [-78.52, -7.05], [-78.51, -7.05], [-78.51, -7.04], [-78.52, -7.04], [-78.52, -7.05]
    ]]}, "properties": {"grid_id": "CAJ_002", "probabilidad": 0.61, "nivel": "Amarillo"}},
]


def run_test_alerts():
    print("\n" + "="*60)
    print("  🔥 PRUEBA DE ALERTAS AUTOMÁTICAS — AlertaForestal Perú")
    print("="*60)

    # Verificar credenciales y cuentas
    try:
        accounts = get_accounts()
        print(f"\n✅ Cuentas Green API verificadas: {len(accounts)}")
        for account in accounts:
            print(f"   - {account.label}: {len(account.group_ids)} grupo(s)")
    except RuntimeError as e:
        print(f"\n❌ Error de credenciales: {e}")
        return

    print(f"\n📊 Datos de prueba: {len(DEMO_FEATURES)} grillas sintéticas en 6 zonas")
    print(f"   (En producción estos datos vienen del modelo LightGBM)\n")
    print("-"*60)

    resultados = []
    for zona in ZONAS:
        chat_id = _get_zone_group_id(zona)
        if not chat_id:
            print(f"⚠️  Sin ChatID para {zona['nombre']} — saltando")
            continue

        # Calcular riesgo de la zona
        zona_info = _classify_zone(DEMO_FEATURES, zona)
        nivel = zona_info["nivel"]
        emoji = {"Rojo": "🔴", "Amarillo": "🟡", "Verde": "🟢"}.get(nivel, "⚪")

        print(f"\n📍 Zona: {zona['nombre']}")
        print(f"   Nivel detectado: {emoji} {nivel}")
        print(f"   Grillas analizadas: {zona_info['n_total']} "
              f"(rojas: {zona_info['n_rojas']}, amarillas: {zona_info['n_amarillas']})")

        if zona_info['top_grid']:
            print(f"   Punto crítico: lat={zona_info['top_grid']['lat']}, "
                  f"lon={zona_info['top_grid']['lon']}, "
                  f"proba={zona_info['top_grid']['probabilidad']:.0%}")

        # Construir mensaje
        mensaje = _build_message(zona_info)

        # Enviar por la cuenta que tiene asignado este grupo
        print(f"   📤 Enviando al grupo WhatsApp ({chat_id[:20]}...)...")
        try:
            result = send_message_to_chat(chat_id, mensaje, accounts=accounts)
            print(f"   ✅ Enviado vía {result['account']} → {result['response']}")
            resultados.append({
                "zona": zona["nombre"],
                "nivel": nivel,
                "chat_id": chat_id,
                "account": result["account"],
                "status": "ok",
            })
        except Exception as exc:
            print(f"   ❌ Error al enviar: {exc}")
            resultados.append({
                "zona": zona["nombre"],
                "nivel": nivel,
                "chat_id": chat_id,
                "status": "error",
                "error": str(exc),
            })

    print("\n" + "="*60)
    print("  RESUMEN DE ALERTAS ENVIADAS")
    print("="*60)
    ok    = [r for r in resultados if r["status"] == "ok"]
    err   = [r for r in resultados if r["status"] == "error"]
    print(f"  ✅ Exitosas: {len(ok)}/{len(resultados)}")
    print(f"  ❌ Fallidas: {len(err)}/{len(resultados)}")
    if err:
        for r in err:
            print(f"    → {r['zona']}: {r.get('error', 'desconocido')}")
    print("="*60 + "\n")


if __name__ == "__main__":
    run_test_alerts()
