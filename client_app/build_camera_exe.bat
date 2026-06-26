@echo off
color 0A
title Dong goi phan mem AI Camera
echo =========================================================
echo   HE THONG DONG GOI USB CAMERA - NGHIEN CUU KHOA HOC
echo =========================================================
echo.

set "PYTHON_EXE="

:: Kiem tra venv o thu muc cha (do da di chuyen vao client_app)
if exist "%~dp0..\venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0..\venv\Scripts\python.exe"
    echo [OK] Da tim thay Python trong venv tai: ..\venv
) else if exist "%~dp0venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"
    echo [OK] Da tim thay Python trong venv tai: .\venv
) else (
    :: Thu dung python he thong
    where python >nul 2>&1
    if %errorlevel% equ 0 (
        set "PYTHON_EXE=python"
        echo [Canh bao] Khong tim thay venv. Su dung Python he thong.
    ) else (
        echo [Loi] Khong tim thay Python. Vui long cai dat Python hoac tao venv.
        pause
        exit /b 1
    )
)

echo.
echo [1/3] Dang cai dat cong cu PyInstaller...
"%PYTHON_EXE%" -m pip install pyinstaller >nul 2>&1
echo OK!

echo.
echo [2/3] Dang bien dich usb_camera_scanner.py thanh file .exe...
echo Quatrinh nay co the mat tu 1-3 phut, vui long cho...
cd /d "%~dp0"
"%PYTHON_EXE%" -m PyInstaller --onefile --windowed --name "HeThongCamera_AI" usb_camera_scanner.py

echo.
echo [3/3] Don dep cac file rac sinh ra trong qua trinh build...
rmdir /s /q "%~dp0build"
del /q "%~dp0HeThongCamera_AI.spec"

echo.
echo =========================================================
echo   HOAN TAT! XIN CHUC MUNG!
echo =========================================================
echo File chay truc tiep (HeThongCamera_AI.exe) da duoc luu tai thu muc:
echo %~dp0dist\
echo.
pause
