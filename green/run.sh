#!/bin/bash
# Green agent run script (called by agentbeats controller)
# Uses environment variables: HOST, AGENT_PORT, AGENT_URL set by controller

cd "$(dirname "$0")/.."
python -c "from src.green_agent import start_green_agent; start_green_agent(host='${HOST:-localhost}', port=${AGENT_PORT:-9001}, external_url='${AGENT_URL:-}')"
