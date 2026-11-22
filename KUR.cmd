@echo off
cd /d "%~dp0"
python -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3,14) else 1)"
if errorlevel 1 (
  echo Bu kilitli kurulum Python 3.14 gerektirir. Diger surumler icin README genel kurulumu kullanin.
  pause
  exit /b 1
)
python -m venv .venv-clean
if errorlevel 1 goto failed
".venv-clean\Scripts\python.exe" -m pip install -r requirements-windows-py314.lock.txt
if errorlevel 1 goto failed
".venv-clean\Scripts\python.exe" -m pip install --no-deps -e ".[dev]"
if errorlevel 1 goto failed
".venv-clean\Scripts\python.exe" -m pip check
if errorlevel 1 goto failed
echo Paket kurulumu tamamlandi. README'deki demo hazirlik adimini da calistirin.
echo RAG ve model hazirlik komutu: .venv-clean\Scripts\python.exe scripts\prepare_demo.py --download-sources --download-model
pause
exit /b 0
:failed
echo Kurulum basarisiz. Yukaridaki hata mesajini kontrol edin.
pause
exit /b 1
