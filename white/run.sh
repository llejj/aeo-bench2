#!/bin/bash
# White agent run script (called by agentbeats controller)
# Uses environment variables: HOST, AGENT_PORT, AGENT_URL set by controller

cd "$(dirname "$0")/.."
python -c "from src.white_agent import start_white_agent; start_white_agent(host='${HOST:-localhost}', port=${AGENT_PORT:-9002}, external_url='${AGENT_URL:-}')"
