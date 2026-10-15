@echo off
chcp 65001 > nul
title AlertaForestal Peru - Envio Inmediato de Alertas 7:00 AM
cd /d "%~dp0"
echo ========================================================
echo   Enviando Alertas Diarias a los Grupos de WhatsApp...
echo ========================================================
python scripts/enviar_alertas_ahora.py
echo.
pause
