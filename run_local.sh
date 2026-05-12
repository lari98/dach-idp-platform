#!/bin/bash
# ============================================================
#  DACH IDP Platform — Local Server (Mac / Linux)
#  Run: bash run_local.sh
#  Opens at: http://localhost:8000
#  API docs: http://localhost:8000/docs
# ============================================================

set -e

echo ""
echo " ===================================================="
echo "  DACH Intelligent Document Processing Platform"
echo "  v3.0.0 — Local Development Server"
echo " ===================================================="
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo " ERROR: python3 not found. Install from https://python.org"
    exit 1
fi

# Install dependencies
echo " Checking dependencies..."
pip3 install -r requirements.txt --quiet 2>/dev/null || \
  pip3 install -r requirements.txt --break-system-packages --quiet

# Environment
export APP_MODE=mock
export APP_ENV=development
export APP_HOST=0.0.0.0
export APP_PORT=8000
export LOG_LEVEL=INFO

echo ""
echo " Starting server in MOCK MODE (no Azure credentials needed)"
echo " API:  http://localhost:8000"
echo " Docs: http://localhost:8000/docs"
echo " ATS:  http://localhost:8000/api/v1/ats/jobs"
echo ""
echo " Press Ctrl+C to stop"
echo ""

python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
