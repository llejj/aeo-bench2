#!/bin/bash
# Start the GREEN agent (Assessment Manager) on port 8010
# Accessed via: https://domain/green/...

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/green"
source "$SCRIPT_DIR/.venv/bin/activate"

DOMAIN="${DOMAIN:-lisandra-aqueous-davin.ngrok-free.dev}"
export HTTPS_ENABLED=true
export CLOUDRUN_HOST="$DOMAIN/green"
export PORT=8010
export PYTHONUNBUFFERED=1

echo "=============================================="
echo "Starting GREEN agent (Assessment Manager)"
echo "=============================================="
echo "Controller port: $PORT"
echo "External URL: https://$CLOUDRUN_HOST"
echo "=============================================="
echo ""

agentbeats run_ctrl
