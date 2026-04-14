#!/bin/bash
# Linux/Mac startup script for the FastAPI + React workspace

echo "========================================"
echo "  知卡学伴"
echo "  FastAPI + React Workspace"
echo "========================================"
echo ""

if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3.10+ is required."
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo "[ERROR] Node.js 18+ is required."
    exit 1
fi

if [ ! -d "venv" ]; then
    echo "[INFO] Creating Python virtual environment..."
    python3 -m venv venv
fi

echo "[INFO] Activating Python virtual environment..."
source venv/bin/activate

echo "[INFO] Installing Python dependencies..."
pip install -r requirements.txt --quiet

echo "[INFO] Installing frontend dependencies..."
(
    cd frontend
    npm install --silent
)

mkdir -p data/uploads
mkdir -p logs

echo ""
echo "[INFO] Starting FastAPI backend..."
python api/app.py &
API_PID=$!

sleep 3

echo "[INFO] Starting React frontend..."
(
    cd frontend
    npm run dev
) &
UI_PID=$!

echo ""
echo "========================================"
echo "  Workspace Ready"
echo "========================================"
echo ""
echo "  Frontend: http://localhost:5173"
echo "  API Docs: http://localhost:8000/docs"
echo ""
echo "  Press Ctrl+C to stop both services."
echo "========================================"

trap "echo ''; echo '[INFO] Stopping services...'; kill $API_PID $UI_PID; exit" INT
wait
