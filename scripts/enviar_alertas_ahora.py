# -*- coding: utf-8 -*-
"""
Script de ejecución inmediata de alertas diarias de WhatsApp.
Ejecuta el análisis y envío de alertas a las zonas y grupos configurados.
"""
import sys
import os
import io
import asyncio
import logging

# Forzar UTF-8 en Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

from app.scheduler import run_daily_alerts

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  🚀 EJECUTANDO ENVÍO INMEDIATO DE ALERTAS DIARIAS")
    print("=" * 60 + "\n")
    asyncio.run(run_daily_alerts())
    print("\n" + "=" * 60)
    print("  🏁 PROCESO FINALIZADO")
    print("=" * 60 + "\n")
