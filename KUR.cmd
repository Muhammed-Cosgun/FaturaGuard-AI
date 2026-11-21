@echo off
cd /d "%~dp0"
python -m venv .venv-clean
if errorlevel 1 goto failed
".venv-clean\Scripts\python.exe" -m pip install -r requirements-windows-py314.lock.txt
if errorlevel 1 goto failed
".venv-clean\Scripts\python.exe" -m pip install --no-deps -e ".[dev]"
if errorlevel 1 goto failed
".venv-clean\Scripts\python.exe" -m pip check
if errorlevel 1 goto failed
echo Kurulum tamamlandi. BASLAT.cmd ile uygulamayi acabilirsiniz.
pause
exit /b 0
:failed
echo Kurulum basarisiz. Yukaridaki hata mesajini kontrol edin.
pause
exit /b 1
