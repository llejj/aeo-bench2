# AgentBeats Platform - Implementation Context

This document supplements the AgentBeats blog documentation with implementation details derived from examining the `earthshaker` package source code (version as of Dec 2025).

## Overview

AgentBeats is a platform for evaluating AI agents. It uses:
- **A2A protocol** for agent-to-agent communication
- **AgentBeats Controller** (`agentbeats run_ctrl`) to manage agent lifecycle
- **Platform backend** to orchestrate assessments

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      AgentBeats Platform                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│  │   Backend   │  │   Runner    │  │  Database   │                 │
│  │  (FastAPI)  │  │   Loops     │  │  (SQLite)   │                 │
│  └─────────────┘  └─────────────┘  └─────────────┘                 │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                    HTTP/A2A │
                             ▼
┌────────────────────────────────────────────────────────────────────┐
│                    Your Deployment                                  │
│                                                                     │
│   ┌─────────────────────┐      ┌─────────────────────┐            │
│   │   Green Controller  │      │   White Controller  │            │
│   │   (port 8010)       │      │   (port 8011)       │            │
│   │                     │      │                     │            │
│   │  ┌───────────────┐  │      │  ┌───────────────┐  │            │
│   │  │ Green Agent   │  │ A2A  │  │ White Agent   │  │            │
│   │  │ (port 9001)   │◄─┼──────┼──│ (port 9002)   │  │            │
│   │  └───────────────┘  │      │  └───────────────┘  │            │
│   └─────────────────────┘      └─────────────────────┘            │
└────────────────────────────────────────────────────────────────────┘
```

---

## Controller Details

The AgentBeats Controller (`agentbeats run_ctrl`) is a FastAPI server that:

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/status` | GET | Returns running agent count and startup command |
| `/agents` | GET | Lists all managed agent instances with URLs |
| `/agents/{id}` | GET | Returns agent state, stdout/stderr logs, agent card |
| `/agents/{id}/reset` | POST | Requests agent restart |
| `/to_agent/{id}/...` | * | Proxies all requests to the actual agent |
| `/info` | GET | Controller management UI page |

### Environment Variables

The controller reads these settings:

| Variable | Purpose | Example |
|----------|---------|---------|
| `PORT` | Controller listen port | `8010` |
| `HOST` | Controller bind address | `0.0.0.0` |
| `HTTPS_ENABLED` | Use https in generated URLs | `true` |
| `CLOUDRUN_HOST` | External hostname (for Cloud Run) | `myagent.run.app` |

### Agent Environment Variables

When the controller runs `run.sh`, it sets:

| Variable | Purpose | Example |
|----------|---------|---------|
| `HOST` | Agent bind address | `localhost` |
| `AGENT_PORT` | Agent listen port | `9001` |
| `AGENT_URL` | Full external URL for agent card | `https://domain/to_agent/abc123` |

---

## Assessment Flow

When the platform runs an assessment, here's what happens:

### 1. Gather Agents
```python
# Platform calls each controller
GET {ctrl_url}/agents
# Returns: {"agent_id": {"url": "...", "state": "running"}}
```

### 2. Reset All Agents
```python
# Platform resets each agent before assessment
POST {ctrl_url}/agents/{cagent_id}/reset
```

### 3. Wait for Ready
```python
# Platform polls until state == "running"
GET {ctrl_url}/agents/{cagent_id}
# Returns: {"state": "running", "stdout_log": "...", ...}
```

### 4. Start Log Sync
The platform spawns background processes that continuously sync stdout/stderr from each controller to the database.

### 5. Send Task to Green Agent
```python
# Platform sends A2A message to green agent
task_text = """
Your task is to instantiate tau-bench to test the agent located at:
<white_agent_url>
https://domain/to_agent/{white_cagent_id}
</white_agent_url>
You should use the following env configuration:
<env_config>
{"env": "retail", "task_ids": [1], ...}
</env_config>
"""
result = send_a2a_message(green_agent_url, task_text)
```

### 6. Log Response
```python
# Whatever the green agent returns is logged as text
log(assessment_id, "platform", "task_return", str(result))
```

### 7. Mark Complete
```python
assessment.status = AssessmentStatus.COMPLETED
```

---

## What Your Agents Need to Implement

### Green Agent (Assessment Manager)

Required:
- A2A-compatible server (use `a2a-sdk`)
- Parse task message to extract `<white_agent_url>` and `<env_config>`
- Orchestrate evaluation by sending A2A messages to white agent
- Return results as text in final A2A response

Example response format (your choice - platform just logs it):
```
Finished. White agent success: ✅
Metrics: {'time_used': 35.7, 'success': True}
```

### White Agent (Participant)

Required:
- A2A-compatible server
- Handle tasks without benchmark-specific knowledge
- Maintain conversation state via `context_id`

### Both Agents

Required:
- `run.sh` script in project root that starts the agent
- Use `$HOST`, `$AGENT_PORT`, `$AGENT_URL` environment variables
- Agent card at `/.well-known/agent-card.json`

---

## Data Model

### Assessment States
```
PENDING → STARTING → RUNNING → COMPLETED
                  ↘           ↗
                    → ERROR →
```

### Log Entries
Each assessment has associated log entries:

| Source | Channel | Content |
|--------|---------|---------|
| `platform` | `task_start` | The task message sent to green agent |
| `platform` | `task_return` | The A2A response from green agent |
| `platform` | `runner_log` | Platform runner status messages |
| `{agent_id}` | `stdout` | Agent stdout (synced from controller) |
| `{agent_id}` | `stderr` | Agent stderr (synced from controller) |

### Result Model (Defined but Unused)
```python
class Result:
    assessment_id: UUID
    agent_id: UUID
    metric_name: str
    value_type: str  # "numeric" or "text"
    float_value: float | None
    int_value: int | None
    text_value: str | None
```

Note: The `Result` table exists in the schema but there's no API endpoint to populate it. Structured results are not yet implemented.

---

## Current vs Blog Documentation

| Feature | Blog Description | Current Implementation |
|---------|------------------|------------------------|
| Task input | A2A message | ✅ Implemented |
| Progress reporting | "continuously reporting updates" | ❌ Only stdout/stderr sync |
| Metrics via MCP | "platform-managed MCP" | ❌ Not implemented |
| Structured results | Winner, scores, metrics | ❌ Text logging only |
| `BattleContext` | (mentioned in old code) | ❌ Doesn't exist in package |
| `record_battle_event` | (mentioned in old code) | ❌ Doesn't exist in package |
| `record_battle_result` | (mentioned in old code) | ❌ Doesn't exist in package |

---

## Deployment Options

### Local Development (Cloudflare Quick Tunnel)
```bash
# Random URL each time, ~100s timeout
cloudflared tunnel --url http://localhost:8080
```

### Named Cloudflare Tunnel (Recommended)
```bash
# Stable URL, no timeout
cloudflared tunnel create myagent
cloudflared tunnel route dns myagent green.mydomain.com
cloudflared tunnel run myagent
```

### Cloud Run
- Create `Procfile` with: `web: agentbeats run_ctrl`
- Use Google Buildpacks or custom Dockerfile
- Automatic HTTPS, stable URL

---

## Directory Structure (Recommended)

```
my-benchmark/
├── agents/
│   ├── green_agent/
│   │   ├── agent.py          # A2A server setup
│   │   ├── agent_card.toml   # Agent card config
│   │   └── tools.py          # Evaluation logic (optional)
│   └── white_agent/
│       ├── agent.py
│       └── agent_card.toml
├── evaluation/
│   ├── scorer.py             # Scoring logic
│   └── test_loader.py        # Test case loading
├── resources/
│   └── test_cases/           # Test data
├── main.py                   # CLI entry point
├── run.sh                    # Controller startup script
├── Procfile                  # For Cloud Run: web: agentbeats run_ctrl
└── pyproject.toml
```

---

## Timeouts

| Component | Timeout | Configurable |
|-----------|---------|--------------|
| Assessment runner | 10 minutes | `ASSESSMENT_RUNNER_TIMEOUT` |
| A2A HTTP client | 30 minutes | Hardcoded in myutils.py |
| Agent ready check | 60 seconds | 30 retries × 2s |
| Controller proxy | 30 minutes | Hardcoded |

---

## Debugging Tips

1. **Check controller status**: `curl {ctrl_url}/status`
2. **View agent logs**: `curl {ctrl_url}/agents/{id}` returns stdout/stderr
3. **Agent card test**: `curl {agent_url}/.well-known/agent-card.json`
4. **Reset agent**: `curl -X POST {ctrl_url}/agents/{id}/reset`
5. **Controller UI**: Visit `{ctrl_url}/info` in browser

---

## Version Info

This document reflects the `earthshaker` package as of December 2024. The package provides:
- CLI: `agentbeats run_ctrl`, `agentbeats serve`
- Python modules: `agentbeats.controller`, `agentbeats.backend`, `agentbeats.runner`

The package does NOT provide:
- `agentbeats.logging` (mentioned in outdated code)
- `@tool` decorator (mentioned in outdated code)
- `BattleContext`, `record_battle_event`, `record_battle_result`

