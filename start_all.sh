#!/bin/bash
# Single command to start all services with Cloudflare Tunnel
# Usage: ./start_all.sh
# Press Ctrl+C to stop everything

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Cleanup function
cleanup() {
    echo ""
    echo "Shutting down all services..."
    kill $(jobs -p) 2>/dev/null
    # Stop nginx
    nginx -s stop -c "$SCRIPT_DIR/nginx.conf" 2>/dev/null || true
    rm -f /tmp/cloudflared-$$.log /tmp/nginx.pid /tmp/nginx_error.log /tmp/nginx_access.log
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

echo "=============================================="
echo "Starting all services..."
echo "=============================================="

# Kill any leftover processes from previous runs
echo "Cleaning up old processes..."
lsof -ti :8080 | xargs kill -9 2>/dev/null || true
lsof -ti :8010 | xargs kill -9 2>/dev/null || true
lsof -ti :8011 | xargs kill -9 2>/dev/null || true
pkill -f cloudflared 2>/dev/null || true
nginx -s stop -c "$SCRIPT_DIR/nginx.conf" 2>/dev/null || true

# Clean up stale agent state directories and nginx files
rm -rf "$SCRIPT_DIR/green/.ab" 2>/dev/null || true
rm -rf "$SCRIPT_DIR/white/.ab" 2>/dev/null || true
rm -f /tmp/nginx.pid /tmp/nginx_error.log /tmp/nginx_access.log 2>/dev/null || true
sleep 1

# Start nginx proxy
echo "[1/4] Starting nginx proxy..."
nginx -c "$SCRIPT_DIR/nginx.conf"
echo "[PROXY] nginx started on port 8080"
echo "[PROXY]   /green/* -> localhost:8010"
echo "[PROXY]   /white/* -> localhost:8011"
sleep 1

# Start cloudflared and capture URL
echo "[2/4] Starting Cloudflare Tunnel..."
cloudflared tunnel --url http://localhost:8080 2>&1 | tee /tmp/cloudflared-$$.log | sed 's/^/[TUNNEL] /' &
CLOUDFLARED_PID=$!

# Wait for cloudflared to output the URL
echo "Waiting for tunnel URL..."
for i in {1..30}; do
    DOMAIN=$(grep -o 'https://[^[:space:]]*\.trycloudflare\.com' /tmp/cloudflared-$$.log 2>/dev/null | head -1 | sed 's|https://||')
    if [ -n "$DOMAIN" ]; then
        break
    fi
    sleep 1
done

if [ -z "$DOMAIN" ]; then
    echo "ERROR: Could not get cloudflared tunnel URL"
    exit 1
fi

echo ""
echo "=============================================="
echo "Tunnel URL: https://$DOMAIN"
echo "=============================================="
echo ""

# Start agents
echo "[3/4] Starting GREEN agent..."
DOMAIN="$DOMAIN" ./start_green.sh 2>&1 | sed 's/^/[GREEN] /' &
GREEN_PID=$!
sleep 2

echo "[4/4] Starting WHITE agent..."
DOMAIN="$DOMAIN" ./start_white.sh 2>&1 | sed 's/^/[WHITE] /' &
WHITE_PID=$!
sleep 2

echo ""
echo "=============================================="
echo "All services running!"
echo "=============================================="
echo ""
echo "Green Agent: https://$DOMAIN/green"
echo "White Agent: https://$DOMAIN/white"
echo ""
echo "Press Ctrl+C to stop all services"
echo "=============================================="

# Wait for all background jobs
wait

