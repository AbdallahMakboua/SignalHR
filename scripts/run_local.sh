#!/usr/bin/env bash
set -euo pipefail

# Local Simulator Startup Script
# Starts FastAPI server and prepares for demo

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

# Set PYTHONPATH to repo root so imports work (core, api, store packages)
export PYTHONPATH="${REPO_ROOT}:${PYTHONPATH:-}"

echo "=========================================="
echo "SignalHR Local Simulator Startup"
echo "=========================================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 not found"
    exit 1
fi

# Install dependencies if needed
echo "[1/4] Checking dependencies..."
python3 -m pip install -q fastapi uvicorn pydantic 2>/dev/null || true

# Clean up any previous state
echo "[2/4] Cleaning up previous state..."
rm -f /tmp/signalhr_aggregates.db
rm -rf artifacts/s3_raw/*
mkdir -p artifacts/s3_raw

# Stop any existing server
if [[ -f /tmp/signalhr_server.pid ]]; then
    OLD_PID=$(cat /tmp/signalhr_server.pid 2>/dev/null || echo "")
    if [[ -n "${OLD_PID}" ]] && kill -0 "${OLD_PID}" 2>/dev/null; then
        echo "  Stopping existing server PID: ${OLD_PID}"
        kill "${OLD_PID}" || true
        sleep 1
        if kill -0 "${OLD_PID}" 2>/dev/null; then
            echo "  Force killing PID: ${OLD_PID}"
            kill -9 "${OLD_PID}" || true
        fi
    fi
fi

# Ensure port 8000 is free (kill any stray process)
if command -v lsof &> /dev/null; then
    PORT_PIDS=$(lsof -ti tcp:8000 || true)
    if [[ -n "${PORT_PIDS}" ]]; then
        echo "  Stopping processes on port 8000: ${PORT_PIDS}"
        kill ${PORT_PIDS} 2>/dev/null || true
        sleep 1
        PORT_PIDS=$(lsof -ti tcp:8000 || true)
        if [[ -n "${PORT_PIDS}" ]]; then
            echo "  Force killing port 8000 PIDs: ${PORT_PIDS}"
            kill -9 ${PORT_PIDS} 2>/dev/null || true
        fi
    fi
fi

# Create artifacts directory for demo
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DEMO_DIR="artifacts/local_demo_${TIMESTAMP}"
mkdir -p "${DEMO_DIR}"
echo "  Demo directory: ${DEMO_DIR}"

# Hard verification: show which api/app.py is being used
echo "[3/4] Verifying API module path..."
python3 -c "import api.app; print(api.app.__file__)"

# Start FastAPI server in background
echo "[4/4] Starting FastAPI server..."
CMD="python3 api/app.py"
echo "  Command: ${CMD}"
${CMD} > "${DEMO_DIR}/server.log" 2>&1 &
SERVER_PID=$!
echo "  Server PID: ${SERVER_PID}"

# Wait for server to start
sleep 2

# Verify server process is still alive
if ! kill -0 "${SERVER_PID}" 2>/dev/null; then
    echo "ERROR: Server process exited"
    cat "${DEMO_DIR}/server.log"
    exit 1
fi

# Verify server is running
if ! curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
    echo "ERROR: Server failed to start"
    cat "${DEMO_DIR}/server.log"
    exit 1
fi

echo ""
echo "=========================================="
echo "✓ Local Simulator Ready"
echo "=========================================="
echo ""
echo "API Endpoint: http://127.0.0.1:8000"
echo "Demo directory: ${DEMO_DIR}"
echo "Server PID: ${SERVER_PID}"
echo ""
echo "Next step: bash scripts/demo.sh"
echo ""

# Save server info for demo script
echo "${SERVER_PID}" > /tmp/signalhr_server.pid
echo "${DEMO_DIR}" > /tmp/signalhr_demo_dir.txt
