#!/bin/bash
# Start the local reverse proxy for path-based routing
# Routes /green/* -> 8010, /white/* -> 8011

cd "$(dirname "$0")"
source .venv/bin/activate

echo "=============================================="
echo "Starting reverse proxy on port 8080"
echo "=============================================="
echo "  /green/* -> localhost:8010 (green agent)"
echo "  /white/* -> localhost:8011 (white agent)"
echo "=============================================="
echo ""

python proxy.py

