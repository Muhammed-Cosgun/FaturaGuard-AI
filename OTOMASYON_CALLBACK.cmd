@echo off
cd /d "%~dp0"
".venv-clean\Scripts\python.exe" scripts\run_automation_enabled.py callback
pause
