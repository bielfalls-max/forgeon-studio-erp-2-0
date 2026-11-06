@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Ambiente nao encontrado. Consulte README.md para instalar.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m forgeon
if errorlevel 1 pause
