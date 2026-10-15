@echo off
chcp 65001 > nul
title AlertaForestal Peru - Servidor de Alertas 7:00 AM
cd /d "%~dp0"
echo =======================================================================
echo   Iniciando Servidor AlertaForestal Peru con Programador Diario
echo   El sistema enviara las alertas automaticamente cada dia a las 07:00 AM
echo =======================================================================
echo   API disponible en: http://localhost:5050
echo   Portal Web en:     http://localhost:5050/web/
echo.
echo Presiona Ctrl+C para detener el servidor.
echo =======================================================================
uvicorn app.main:app --port 5050 --host 0.0.0.0
pause
