@echo off
cd /d "%~dp0"
set PYTHONDONTWRITEBYTECODE=1
".venv-clean\Scripts\python.exe" -m uvicorn faturaguard.main:app --host 127.0.0.1 --port 8011
pause
