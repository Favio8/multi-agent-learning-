@echo off
setlocal EnableExtensions

set "CONDA_CMD=%~1"
set "ENV_NAME=%~2"
set "ROOT_DIR=%~3"
set "DRY_RUN=%~4"

if "%CONDA_CMD%"=="" (
    echo [ERROR] Missing Conda executable path.
    exit /b 1
)

if "%ENV_NAME%"=="" (
    echo [ERROR] Missing Conda environment name.
    exit /b 1
)

if "%ROOT_DIR%"=="" (
    echo [ERROR] Missing project root path.
    exit /b 1
)

cd /d "%ROOT_DIR%"
if errorlevel 1 (
    echo [ERROR] Failed to enter project root: %ROOT_DIR%
    exit /b 1
)

echo [MAS-API] Project root: %ROOT_DIR%
echo [MAS-API] Using Conda env: %ENV_NAME%
echo [MAS-API] Command: "%CONDA_CMD%" run -n "%ENV_NAME%" python -m uvicorn api.app:app --host 127.0.0.1 --port 8000
if /I "%DRY_RUN%"=="--dry-run" (
    echo [MAS-API] Dry run finished.
    exit /b 0
)

echo [MAS-API] Starting FastAPI server...
call "%CONDA_CMD%" run -n "%ENV_NAME%" python -m uvicorn api.app:app --host 127.0.0.1 --port 8000
set "EXIT_CODE=%ERRORLEVEL%"
echo.
echo [MAS-API] Backend exited with code %EXIT_CODE%.
exit /b %EXIT_CODE%
