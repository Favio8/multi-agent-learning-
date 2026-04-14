@echo off
setlocal EnableExtensions EnableDelayedExpansion

for %%I in ("%~dp0.") do set "ROOT_DIR=%%~fI"
cd /d "%ROOT_DIR%"

set "ENV_NAME=MAS"
set "DRY_RUN=0"

:parse_args
if "%~1"=="" goto args_done
if /I "%~1"=="--dry-run" (
    set "DRY_RUN=1"
) else (
    set "ENV_NAME=%~1"
)
shift
goto parse_args

:args_done
echo ========================================
echo   Multi-Agent Learning Startup
echo ========================================
echo.
echo [INFO] Project root: %ROOT_DIR%
echo [INFO] Conda env: %ENV_NAME%
echo.

set "CONDA_CMD="
if defined CONDA_EXE (
    set "CONDA_CMD=%CONDA_EXE%"
)

if not defined CONDA_CMD (
    for /f "delims=" %%I in ('where conda.exe 2^>nul') do (
        set "CONDA_CMD=%%I"
        goto conda_found
    )
)

if not defined CONDA_CMD (
    for /f "delims=" %%I in ('where conda 2^>nul') do (
        set "CONDA_CMD=%%I"
        goto conda_found
    )
)

:conda_found
if not defined CONDA_CMD (
    echo [ERROR] Conda was not found. Please open this project from a terminal where Conda is available.
    pause
    exit /b 1
)

node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js 18+ is required.
    pause
    exit /b 1
)

call "%CONDA_CMD%" run -n "%ENV_NAME%" python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Conda environment "%ENV_NAME%" is not available.
    echo         You can run: conda env list
    pause
    exit /b 1
)

echo [INFO] Verifying backend dependencies...
call "%CONDA_CMD%" run -n "%ENV_NAME%" python -c "import fastapi, uvicorn, dotenv, requests" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing Python dependencies into "%ENV_NAME%"...
    call "%CONDA_CMD%" run -n "%ENV_NAME%" python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install Python dependencies.
        pause
        exit /b 1
    )
) else (
    echo [INFO] Backend dependencies look ready.
)

if not exist "frontend\node_modules" (
    echo [INFO] Installing frontend dependencies...
    pushd frontend
    call npm install
    if errorlevel 1 (
        popd
        echo [ERROR] Failed to install frontend dependencies.
        pause
        exit /b 1
    )
    popd
) else (
    echo [INFO] Frontend dependencies look ready.
)

if not exist "data" mkdir data
if not exist "data\uploads" mkdir data\uploads
if not exist "logs" mkdir logs

echo.
echo [INFO] Backend runner:
echo        %ROOT_DIR%\start_backend.bat
echo [INFO] Frontend runner:
echo        %ROOT_DIR%\start_frontend.bat

if "%DRY_RUN%"=="1" (
    echo.
    echo [INFO] Dry run finished. No windows were launched.
    exit /b 0
)

echo.
echo [INFO] Starting backend window...
start "MAS-API" cmd /k call "%ROOT_DIR%\start_backend.bat" "%CONDA_CMD%" "%ENV_NAME%" "%ROOT_DIR%"

timeout /t 3 /nobreak >nul

echo [INFO] Starting frontend window...
start "MAS-FRONTEND" cmd /k call "%ROOT_DIR%\start_frontend.bat" "%ROOT_DIR%"

echo.
echo ========================================
echo   Startup triggered successfully
echo ========================================
echo.
echo   Backend:  http://127.0.0.1:8000
echo   API Docs: http://127.0.0.1:8000/docs
echo   Frontend: check the MAS-FRONTEND window for the final Vite URL
echo.
echo   Tip: if you want another Conda env, run:
echo        start_app.bat YourEnvName
echo.
pause
