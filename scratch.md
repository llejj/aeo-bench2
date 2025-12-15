# Dual Agent Setup with Cloudflare Tunnel (Free Tier)

Uses Cloudflare Tunnel (cloudflared) with a local Python proxy for path-based routing.

## Architecture

```
cloudflared (port 8080) -> proxy.py -> /green/* -> agent (port 8010)
                                    -> /white/* -> agent (port 8011)
```

## Prerequisites

Install cloudflared:
```bash
brew install cloudflared
```

## Quick Start (Recommended)

Single command to start everything:
```bash
./start_all.sh
```

This will:
1. Start the proxy
2. Start cloudflared and auto-capture the tunnel URL
3. Start both agents with the correct URL
4. Clean up all processes when you press Ctrl+C

## Manual Start (4 terminals)

If you prefer manual control:

```bash
# Terminal 1: Start the local reverse proxy
./start_proxy.sh

# Terminal 2: Start cloudflared tunnel (note the URL it outputs)
cloudflared tunnel --url http://localhost:8080
# Example output: https://random-words.trycloudflare.com

# Terminal 3: Start green agent (use the cloudflared URL)
DOMAIN="random-words.trycloudflare.com" ./start_green.sh

# Terminal 4: Start white agent (use the same cloudflared URL)
DOMAIN="random-words.trycloudflare.com" ./start_white.sh
```

## URLs

After starting, your agents will be accessible at:
- **Green Agent**: `https://<your-cloudflared-url>/green/...`
- **White Agent**: `https://<your-cloudflared-url>/white/...`

## Files

| File | Purpose |
|------|---------|
| `start_all.sh` | **Single command to start everything** |
| `proxy.py` | Local reverse proxy for path-based routing |
| `start_proxy.sh` | Starts the proxy on port 8080 |
| `start_green.sh` | Starts green agent on port 8010 |
| `start_white.sh` | Starts white agent on port 8011 |
| `green/` | Green agent working directory |
| `white/` | White agent working directory |

## Notes

- The cloudflared quick tunnel URL changes each time you restart it
- For a stable URL, create a Cloudflare account and set up a named tunnel
- The agents automatically use the external URL from the DOMAIN environment variable
