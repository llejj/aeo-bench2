#!/bin/bash
# White agent v2 run script (LangGraph version)
# Uses environment variables: HOST, AGENT_PORT, AGENT_URL set by controller

cd "$(dirname "$0")/.."
python -c "from white2 import start_white_agent; start_white_agent(host='${HOST:-localhost}', port=${AGENT_PORT:-9003}, external_url='${AGENT_URL:-}')"
