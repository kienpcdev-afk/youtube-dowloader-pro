@echo off
setlocal

cd /d "%~dp0"

REM -- Kich hoat moi truong ao neu co
if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
    echo [OK] Da kich hoat moi truong ao venv.
) else (
    echo [INFO] Khong tim thay venv, dung Python he thong.
)

REM -- Kiem tra streamlit
where streamlit >nul 2>&1
if errorlevel 1 (
    echo(
    echo [LOI] Khong tim thay lenh streamlit.
    echo       Vui long chay: pip install -r requirements.txt
    echo(
    pause
    exit /b 1
)

REM -- Kiem tra file huong dan
if not exist "KP_Guide.py" (
    echo(
    echo [LOI] Khong tim thay file KP_Guide.py trong thu muc: %~dp0
    echo(
    pause
    exit /b 1
)

set PORT=8502

echo(
echo =========================================================
echo   Huong dan cai dat -- YouTube Downloader Pro
echo   Dang khoi dong tai: http://localhost:%PORT%
echo   Nhan Ctrl+C de dung server.
echo =========================================================
echo(

streamlit run KP_Guide.py --server.port %PORT% --browser.gatherUsageStats false
set EXIT_CODE=%ERRORLEVEL%

if not %EXIT_CODE%==0 (
    echo(
    echo [LOI] Streamlit thoat voi ma loi: %EXIT_CODE%
    echo(
    pause
)

endlocal
exit /b %EXIT_CODE%
