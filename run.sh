#!/bin/bash
# AgentBeats controller launch script
# Uses environment variables: HOST, AGENT_PORT, ROLE

HOST=${HOST:-localhost}
AGENT_PORT=${AGENT_PORT:-9001}
ROLE=${ROLE:-green}

if [ "$ROLE" = "green" ]; then
    python -c "from src.green_agent import start_green_agent; start_green_agent(host='$HOST', port=$AGENT_PORT)"
elif [ "$ROLE" = "white" ]; then
    python -c "from src.white_agent import start_white_agent; start_white_agent(host='$HOST', port=$AGENT_PORT)"
else
    echo "Unknown ROLE: $ROLE. Use 'green' or 'white'."
    exit 1
fi

