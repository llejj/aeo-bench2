# AEO-Bench: Documentation Generation Benchmark

AEO-Bench (Agent Evaluation for Documentation) evaluates how effectively AI agents generate documentation for code repositories. Unlike SWE-Bench which tests coding ability, AEO-Bench tests *communication quality*: can agents transform raw code into well-documented, discoverable forms?

## Overview

This benchmark uses a **Green Agent / White Agent** architecture:
- **Green Agent**: The evaluator that orchestrates tests and scores documentation quality
- **White Agent**: The agent being tested that generates documentation

The Green Agent provides the White Agent with tools to explore a code repository, then evaluates the generated documentation using a 4-tier rubric.

## Project Structure

```
├── green/                    # Green Agent (evaluator)
│   ├── agent.py              # Main evaluation logic
│   └── agent_card.toml       # A2A agent configuration
├── white/                    # White Agent (documentation generator)
│   ├── agent.py              # White agent implementation
│   └── agent_card.toml       # A2A agent configuration
├── resources/
│   └── test_repos/           # Test cases for evaluation
│       ├── qrcode_generator/ # QR code generation project
│       ├── slugify_text/     # Text slugification utility
│       ├── progress_bar/     # Terminal progress bar
│       └── env_loader/       # Environment variable loader
├── main.py                   # Main entry point
└── start_all.sh              # Launch all agents
```

## Installation

### Prerequisites
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- OpenAI API key

### Setup

```bash
# Install dependencies
uv sync

# Configure environment
cp .env.example .env  # Create if doesn't exist
# Add your OpenAI API key to .env:
# OPENAI_API_KEY=sk-...
```

## Usage

### Quick Start

```bash
# Start all agents and run evaluation
./start_all.sh
```

### Running Specific Test Cases

By default, the evaluation runs 2 test cases. To run all or specific tests:

```python
# In your evaluation request, pass test_config:
<test_config>{"test_ids": null}</test_config>  # Run all tests
<test_config>{"test_ids": [0, 2]}</test_config>  # Run specific tests by index
```

## Evaluation Rubric

AEO-Bench uses a **4-tier scoring system** (100 points total):

### Tier 1: Structural Validity (15 points) - Automated
| Criterion | Points |
|-----------|--------|
| Valid JSON response | 5 |
| README present (>100 chars) | 5 |
| Schema.org metadata structure | 5 |

### Tier 2: Required Sections (25 points) - Keyword Detection
| Section | Points | Keywords Detected |
|---------|--------|-------------------|
| Installation/Setup | 8 | install, pip, requirements, setup |
| Usage/How to Run | 9 | usage, run, execute, command |
| Example/Demo | 8 | example, output, demo, ``` |

### Tier 3: Factual Accuracy (30 points) - LLM-Judged
| Criterion | Points |
|-----------|--------|
| Correct main purpose | 12 |
| Correct dependencies | 10 |
| Correct run command | 8 |

### Tier 4: Quality (30 points) - LLM-Judged
| Criterion | Points |
|-----------|--------|
| Clarity and readability | 12 |
| Completeness for new user | 10 |
| Professional formatting | 8 |

## Test Cases

The benchmark includes 4 diverse test cases from different domains:

| Test Case | Domain | Dependencies | Description |
|-----------|--------|--------------|-------------|
| `qrcode_generator` | Image/CLI | qrcode, pillow | Generate QR codes from text/URLs |
| `slugify_text` | Text Processing | None (stdlib) | Convert text to URL-friendly slugs |
| `progress_bar` | CLI Utility | None (stdlib) | Display progress bars for iterables |
| `env_loader` | Configuration | None (stdlib) | Load environment variables from .env files |

Each test case includes:
- Source code (`*.py`)
- `metadata.json` - Project metadata
- `ground_truth/README.md` - Gold-standard documentation
- `ground_truth/facts.json` - Key facts for accuracy verification

## Adding New Test Cases

1. Create a new directory under `resources/test_repos/`:
```
resources/test_repos/my_project/
├── main.py                    # Source code
├── metadata.json              # Project metadata
└── ground_truth/
    ├── README.md              # Gold-standard documentation
    └── facts.json             # Key facts for accuracy scoring
```

2. Create `metadata.json`:
```json
{
  "name": "my_project",
  "description": "Brief description of the project",
  "language": "Python",
  "domain": "utility",
  "files": ["main.py"]
}
```

3. Create `ground_truth/facts.json`:
```json
{
  "main_purpose": "What the project does",
  "dependencies": ["dep1", "dep2"],
  "run_command": "python main.py",
  "key_features": ["feature1", "feature2"],
  "must_mention": ["keyword1", "keyword2"],
  "main_file": "main.py"
}
```

## Environment Design

### Goal
Generate comprehensive documentation (README + schema.org metadata) for a code repository.

### State Space
- Repository files visible to the agent
- Conversation history
- Tool call results

### Available Actions
| Action | Description |
|--------|-------------|
| `list_directory(path)` | List files in a directory |
| `read_file(path)` | Read file contents |
| `get_project_info()` | Get project metadata |
| `respond(readme, metadata)` | Submit final documentation |

### Task Completion
The task ends when:
1. The agent calls the `respond` action with final documentation, OR
2. Maximum steps (15) are reached

## Example Output

```
Evaluation Complete ✅

Overall Score: 312/400 (78.0%)
Average Score: 78.0/100
Time: 45.2s
Test Cases: 4

Scoring Rubric:
  Tier 1 - Structural (15 pts): Valid JSON, README exists, metadata schema
  Tier 2 - Sections (25 pts): Installation, Usage, Examples present
  Tier 3 - Accuracy (30 pts): Correct purpose, dependencies, commands
  Tier 4 - Quality (30 pts): Clarity, completeness, formatting

Individual Results:
  ✅ qrcode_generator: 82/100 [T1:15/15 T2:25/25 T3:24/30 T4:18/30]
  ✅ slugify_text: 79/100 [T1:15/15 T2:25/25 T3:22/30 T4:17/30]
  ✅ progress_bar: 75/100 [T1:15/15 T2:17/25 T3:25/30 T4:18/30]
  ✅ env_loader: 76/100 [T1:15/15 T2:25/25 T3:20/30 T4:16/30]
```

## Reproducibility

To reproduce evaluation results:

```bash
# Run full evaluation
./start_all.sh

# Or run with specific configuration
uv run python main.py launch --test-ids 0,1,2,3
```

Logs are written to `/tmp/green_agent.log` for debugging.

## API Reference

### Green Agent Endpoints
- `POST /` - A2A message endpoint for receiving evaluation requests

### White Agent Endpoints  
- `POST /` - A2A message endpoint for receiving documentation tasks

## License

MIT License

## Authors

CS194 Course Project - Fall 2024
