@echo off
title FinanCuota - Local
cd /d "%~dp0"
echo.
echo  FinanCuota - Simulador de credito vehicular
echo  ============================================
echo.
python --version >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python no esta instalado. Instala Python 3.10+ desde python.org
  pause
  exit /b 1
)
echo Instalando dependencias si faltan...
python -m pip install -r requirements.txt -q
echo.
echo  URL:    http://127.0.0.1:5000
echo  Admin:  usuario admin  /  contrasena adminupc
echo.
echo  La base de datos se guarda en: financuota.db (en esta carpeta)
echo  Presiona Ctrl+C para detener el servidor.
echo.
python app.py
pause
