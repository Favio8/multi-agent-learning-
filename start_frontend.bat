@echo off
setlocal EnableExtensions

set "ROOT_DIR=%~1"
set "DRY_RUN=%~2"

if "%ROOT_DIR%"=="" (
    echo [ERROR] Missing project root path.
    exit /b 1
)

cd /d "%ROOT_DIR%\frontend"
if errorlevel 1 (
    echo [ERROR] Failed to enter frontend directory: %ROOT_DIR%\frontend
    exit /b 1
)

echo [MAS-FRONTEND] Project root: %ROOT_DIR%
echo [MAS-FRONTEND] Command: npm run dev -- --host 127.0.0.1 --port 5173
if /I "%DRY_RUN%"=="--dry-run" (
    echo [MAS-FRONTEND] Dry run finished.
    exit /b 0
)

echo [MAS-FRONTEND] Starting Vite dev server...
call npm run dev -- --host 127.0.0.1 --port 5173
set "EXIT_CODE=%ERRORLEVEL%"
echo.
echo [MAS-FRONTEND] Frontend exited with code %EXIT_CODE%.
exit /b %EXIT_CODE%
