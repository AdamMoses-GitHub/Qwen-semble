@echo off
REM Qwen-semble GPU Installation Script for Windows
REM Requires: Python 3.12+, CUDA 12.1+, Visual Studio Build Tools

echo ========================================
echo Qwen-semble GPU Installation
echo ========================================
echo.

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.12 or higher.
    pause
    exit /b 1
)

echo Step 1: Installing PyTorch with CUDA 12.1 support...
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
if errorlevel 1 (
    echo ERROR: Failed to install PyTorch with CUDA support
    pause
    exit /b 1
)

echo.
echo Step 2: Installing application requirements...
pip install -r requirements-gpu.txt
if errorlevel 1 (
    echo ERROR: Failed to install requirements
    pause
    exit /b 1
)

echo.
echo Step 3: Installing Flash Attention (optional, may take several minutes)...
echo This requires MSVC compiler. Press Ctrl+C to skip if you encounter errors.
timeout /t 5
pip install flash-attn --no-build-isolation
if errorlevel 1 (
    echo WARNING: Flash Attention installation failed. This is optional.
    echo The application will work without it, but may be slower.
)

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo To verify CUDA is available, run:
echo   python -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}')"
echo.
echo To start the application, run:
echo   run.bat
echo.
pause
