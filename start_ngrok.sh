#!/bin/bash
# Start ngrok pointing to the local proxy (port 8080)
# The proxy handles routing to green (8010) and white (8011)

DOMAIN="lisandra-aqueous-davin.ngrok-free.dev"

echo "=============================================="
echo "Starting ngrok tunnel"
echo "=============================================="
echo "https://$DOMAIN -> localhost:8080 (proxy)"
echo ""
echo "Agent URLs:"
echo "  Green: https://$DOMAIN/green/..."
echo "  White: https://$DOMAIN/white/..."
echo "=============================================="
echo ""

ngrok http 8080 --domain=$DOMAIN
