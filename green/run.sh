#!/bin/bash
# Green agent run script (called by agentbeats controller)
# Uses environment variables: HOST, AGENT_PORT, AGENT_URL set by controller

HOST=${HOST:-localhost}
AGENT_PORT=${AGENT_PORT:-9001}
# AGENT_URL is passed by the controller with the full external URL including /to_agent/<id>
EXTERNAL_URL=${AGENT_URL:-}

cd "$(dirname "$0")"
python -c "from src.green_agent import start_green_agent; start_green_agent(host='$HOST', port=$AGENT_PORT, external_url='$EXTERNAL_URL')"

