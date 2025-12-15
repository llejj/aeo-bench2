#!/bin/bash
# White agent run script (called by agentbeats controller)
# Uses environment variables: HOST, AGENT_PORT, CLOUDRUN_HOST set by controller

HOST=${HOST:-localhost}
AGENT_PORT=${AGENT_PORT:-9002}
EXTERNAL_URL=${CLOUDRUN_HOST:-}

cd "$(dirname "$0")"
python -c "from src.white_agent import start_white_agent; start_white_agent(host='$HOST', port=$AGENT_PORT, external_url='$EXTERNAL_URL')"

