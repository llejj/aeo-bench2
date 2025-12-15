# Dual Agent Setup with Local Reverse Proxy (Free Tier)

Uses ONE ngrok static domain with a local Python proxy for path-based routing.

## Architecture

```
ngrok (port 8080) -> proxy.py -> /green/* -> agent (port 8010)
                              -> /white/* -> agent (port 8011)
```

## URLs

- **Green Agent**: `https://lisandra-aqueous-davin.ngrok-free.dev/green/...`
- **White Agent**: `https://lisandra-aqueous-davin.ngrok-free.dev/white/...`

## How to Run (4 terminals)

```bash
# Terminal 1: Start the local reverse proxy
./start_proxy.sh

# Terminal 2: Start ngrok (points to proxy on port 8080)
./start_ngrok.sh

# Terminal 3: Start green agent
./start_green.sh

# Terminal 4: Start white agent
./start_white.sh
```

## Files

| File | Purpose |
|------|---------|
| `proxy.py` | Local reverse proxy for path-based routing |
| `start_proxy.sh` | Starts the proxy on port 8080 |
| `start_ngrok.sh` | Starts ngrok tunnel to port 8080 |
| `start_green.sh` | Starts green agent on port 8010 |
| `start_white.sh` | Starts white agent on port 8011 |
| `green/` | Green agent working directory |
| `white/` | White agent working directory |
