@echo off
setlocal

cd /d "%~dp0"
echo [INFO] Creating Virtual Environment...
if not exist ".venv" (
    python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip

echo [INFO] Installing dependencies for EDUX-TEST-SOLVER...
cd /d "%~dp0EDUX-TEST-SOLVER"
python -m pip install -r requirements.txt
python -m playwright install chromium

echo [INFO] Installing dependencies for EDUX-SLIDE-BRUTEFORCE...
cd /d "%~dp0EDUX-SLIDE-BRUTEFORCE"
python -m pip install -r requirements.txt
python -m playwright install chromium

echo [INFO] Installing dependencies for EDUX-SLIDE-AI...
cd /d "%~dp0EDUX-SLIDE-AI"
python -m pip install -r requirements.txt

echo [INFO] All dependencies installed successfully!
pause
endlocal
