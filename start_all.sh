#!/bin/bash
# Single command to start all AEO-Bench services with Cloudflare Tunnel
# Usage: ./start_all.sh [test_id] [test_id2] ...
# Examples:
#   ./start_all.sh        # Default: run test 0
#   ./start_all.sh 0 1 2  # Run tests 0, 1, and 2
#   ./start_all.sh all    # Run all tests
# Available test cases:
#   0: art_github
#   1: countdown_timer
#   2: dotenv_github
#   3: password_generator
#   4: pyfiglet_github
#   5: word_counter
# Press Ctrl+C to stop everything

set -e

# Parse test case arguments
TEST_IDS="${*:-0}"  # Default to "0" if no args provided
export TEST_IDS

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Fixed domain for named tunnel
DOMAIN="763324.uk"
TUNNEL_NAME="aeo-bench"

# Cleanup function
cleanup() {
    echo ""
    echo "Shutting down all services..."
    kill $(jobs -p) 2>/dev/null || true
    # Stop nginx
    nginx -s stop -c "$SCRIPT_DIR/nginx.conf" 2>/dev/null || true
    # Kill cloudflared tunnel
    pkill -f "cloudflared.*$TUNNEL_NAME" 2>/dev/null || true
    rm -f /tmp/nginx.pid /tmp/nginx_error.log /tmp/nginx_access.log
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

echo "=============================================="
echo "Starting AEO-Bench services..."
echo "=============================================="

# Kill any leftover processes from previous runs
echo "Cleaning up old processes..."
lsof -ti :8080 | xargs kill -9 2>/dev/null || true
lsof -ti :8010 | xargs kill -9 2>/dev/null || true
lsof -ti :8011 | xargs kill -9 2>/dev/null || true
pkill -f "cloudflared.*$TUNNEL_NAME" 2>/dev/null || true
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

# Start named cloudflared tunnel
echo "[2/4] Starting Cloudflare Tunnel ($TUNNEL_NAME)..."
cloudflared tunnel --url http://localhost:8080 run "$TUNNEL_NAME" 2>&1 | sed 's/^/[TUNNEL] /' &
CLOUDFLARED_PID=$!

# Give tunnel a moment to connect
sleep 3

echo ""
echo "=============================================="
echo "Tunnel: https://$DOMAIN"
echo "=============================================="
echo ""

# Start agents
echo "[3/4] Starting GREEN agent (Evaluation Manager)..."
echo "[GREEN] Test IDs: $TEST_IDS"
DOMAIN="$DOMAIN" TEST_IDS="$TEST_IDS" ./start_green.sh 2>&1 | sed 's/^/[GREEN] /' &
GREEN_PID=$!
sleep 2

echo "[4/4] Starting WHITE agent (Documentation Generator)..."
DOMAIN="$DOMAIN" ./start_white.sh 2>&1 | sed 's/^/[WHITE] /' &
WHITE_PID=$!
sleep 2

echo ""
echo "=============================================="
echo "AEO-Bench services running!"
echo "=============================================="
echo ""
echo "Green Agent (Evaluator): https://$DOMAIN/green"
echo "White Agent (Generator): https://$DOMAIN/white"
echo ""
echo "Press Ctrl+C to stop all services"
echo "=============================================="

# Wait for all background jobs
wait
