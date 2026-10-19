@echo off
setlocal
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
  echo No se encontro venv. Consulta docs\GUIA_EXPOSICION_LUNES.md.
  pause
  exit /b 1
)
set PYTHONUTF8=1
"venv\Scripts\python.exe" "scripts\expo_local.py"
if errorlevel 1 (
  echo No se pudo iniciar la exposicion. Revisa los logs en tmp\expo.
  pause
  exit /b 1
)
echo AeroGuard esta listo. Los servidores siguen ejecutandose en segundo plano.
pause
