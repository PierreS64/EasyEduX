@echo off
chcp 65001 >nul
setlocal

:menu
echo.
echo ===========================================
echo CHON PHUONG THUC DANG NHAP EDUX
echo ===========================================
echo 1. Dang nhap bang tai khoan va mat khau EDUX
echo 2. Dang nhap bang tai khoan Microsoft
echo ===========================================
set /p choice="Chon phuong thuc (1 hoac 2): "

if "%choice%"=="1" (
    set USE_MICROSOFT_LOGIN=0
) else if "%choice%"=="2" (
    set USE_MICROSOFT_LOGIN=1
) else (
    echo [Loi] Lua chon khong hop le. Vui long chon lai.
    goto menu
)

cd /d "%~dp0"
if not exist ".venv" (
    echo [ERROR] Virtual environment not found. Please run install_deps.bat first.
    pause
    exit /b 1
)
call .venv\Scripts\activate.bat

cd EDUX-TEST-SOLVER
pytest -s --headed --browser chromium
endlocal
