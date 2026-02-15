@echo off
REM Qwen-semble TTS Voice Studio Launcher
echo Starting Qwen-semble TTS Voice Studio...
echo.

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Run the application
python src\main.py

REM Keep window open if there's an error
if errorlevel 1 (
    echo.
    echo Application exited with an error. Check output\logs\app.log for details.
    pause
)
