@echo off
REM Qwen-semble CPU-Only Installation Script for Windows

echo ========================================
echo Qwen-semble CPU Installation
echo ========================================
echo.

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.12 or higher.
    pause
    exit /b 1
)

echo Installing requirements (CPU-only version)...
pip install -r requirements-cpu.txt
if errorlevel 1 (
    echo ERROR: Failed to install requirements
    pause
    exit /b 1
)

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo To start the application, run:
echo   run.bat
echo.
echo Note: This is the CPU-only version. For better performance,
echo consider installing the GPU version if you have CUDA-capable GPU.
echo.
pause
