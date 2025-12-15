#!/bin/bash
# Start the WHITE agent (Target Being Tested) on port 8011
# Accessed via: https://domain/white/...

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/white"
source .venv/bin/activate

DOMAIN="${DOMAIN:-lisandra-aqueous-davin.ngrok-free.dev}"
export HTTPS_ENABLED=true
export CLOUDRUN_HOST="$DOMAIN/white"
export PORT=8011
export PYTHONUNBUFFERED=1

echo "=============================================="
echo "Starting WHITE agent (Target Being Tested)"
echo "=============================================="
echo "Controller port: $PORT"
echo "External URL: https://$CLOUDRUN_HOST"
echo "=============================================="
echo ""

agentbeats run_ctrl
