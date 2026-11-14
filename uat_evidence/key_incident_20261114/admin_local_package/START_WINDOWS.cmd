@echo off
setlocal
cd /d "%~dp0"
py -3 --version >nul 2>&1
if errorlevel 1 goto python_missing
if not exist ".venv\Scripts\python.exe" py -3 -m venv .venv
if not exist ".venv\Scripts\python.exe" goto failed
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check cryptography
if errorlevel 1 goto failed
if exist "juog-isolated-rotation.enc.json" goto transfer
".venv\Scripts\python.exe" generate_encrypted_bundle.py
if errorlevel 1 goto failed
:transfer
".venv\Scripts\python.exe" local_admin_transfer.py
if errorlevel 1 goto failed
echo Local helper closed. This does NOT confirm remote key replacement.
pause
exit /b 0
:python_missing
echo Python 3 with tkinter is required. Obtain it from python.org. No key was generated.
pause
exit /b 1
:failed
echo STOP. Keep authentication disabled. Do not restore old keys. Do not send secrets or screenshots.
pause
exit /b 1
