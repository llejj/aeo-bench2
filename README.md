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
│       ├── password_generator/ # Synthetic: Password generation
│       ├── countdown_timer/    # Synthetic: Terminal countdown timer
│       ├── word_counter/       # Synthetic: Word/line/char counting
│       ├── art_github/         # Real: ASCII art library
│       ├── dotenv_github/      # Real: python-dotenv
│       └── pyfiglet_github/    # Real: ASCII text banners
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

The benchmark includes **6 diverse test cases** - a mix of synthetic (hand-crafted) and real GitHub repositories:

### Synthetic Test Cases (3)
Hand-crafted projects with clean, uncontaminated code:

| Test Case | Domain | Dependencies | Description |
|-----------|--------|--------------|-------------|
| `password_generator` | Security | None (stdlib) | Generate secure random passwords with options |
| `countdown_timer` | CLI Utility | None (stdlib) | Terminal countdown timer with stopwatch mode |
| `word_counter` | Text Processing | None (stdlib) | Count words, lines, and characters (like `wc`) |

### Real GitHub Repositories (3)
Cloned from actual open-source projects using `git clone --depth 1`:

| Test Case | Source | Stars | Description |
|-----------|--------|-------|-------------|
| `art_github` | [sepandhaghighi/art](https://github.com/sepandhaghighi/art) | 2k+ | ASCII art library with 677 fonts |
| `dotenv_github` | [theskumar/python-dotenv](https://github.com/theskumar/python-dotenv) | 7k+ | Load .env files as environment variables |
| `pyfiglet_github` | [pwaller/pyfiglet](https://github.com/pwaller/pyfiglet) | 1.4k+ | Pure Python FIGlet ASCII text banners |

The real repositories were cloned with `git clone --depth 1`, then cleaned up by removing `.git/`, test directories, CI configs, and other non-essential files. The original README serves as the ground truth documentation.

### Test Case Structure
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
| `respond(readme, metadata)` | Submit final documentation |

### Task Completion
The task ends when:
1. The agent calls the `respond` action with final documentation, OR
2. Maximum steps (15) are reached

## Example Output

```
Evaluation Complete ✅

Overall Score: 468/600 (78.0%)
Average Score: 78.0/100
Time: 67.3s
Test Cases: 6

Scoring Rubric:
  Tier 1 - Structural (15 pts): Valid JSON, README exists, metadata schema
  Tier 2 - Sections (25 pts): Installation, Usage, Examples present
  Tier 3 - Accuracy (30 pts): Correct purpose, dependencies, commands
  Tier 4 - Quality (30 pts): Clarity, completeness, formatting

Individual Results:
  ✅ password_generator: 82/100 [T1:15/15 T2:25/25 T3:24/30 T4:18/30]
  ✅ countdown_timer: 79/100 [T1:15/15 T2:25/25 T3:22/30 T4:17/30]
  ✅ word_counter: 75/100 [T1:15/15 T2:17/25 T3:25/30 T4:18/30]
  ✅ art_github: 80/100 [T1:15/15 T2:25/25 T3:22/30 T4:18/30]
  ✅ dotenv_github: 76/100 [T1:15/15 T2:25/25 T3:20/30 T4:16/30]
  ✅ pyfiglet_github: 76/100 [T1:15/15 T2:25/25 T3:20/30 T4:16/30]
```

## CLI Commands

Available commands for running and testing:

```bash
# Start all agents with Cloudflare tunnel (for AgentBeats platform)
./start_all.sh

# Start green agent only (evaluation manager)
uv run python main.py green

# Start white agent only (documentation generator)
uv run python main.py white

# Run local evaluation with both agents
uv run python main.py launch

# Validate scoring rubric with test cases (Q8.5)
uv run python main.py validate
```

## Reproducibility

To reproduce evaluation results:

```bash
# Run full evaluation with all 6 test cases
./start_all.sh
# Then trigger evaluation via AgentBeats platform

# Or run locally with specific test cases
uv run python main.py launch  # Runs first 3 test cases by default
```

Logs are written to `/tmp/green_agent.log` for debugging.

## Rubric Validation

The scoring system includes built-in validation to ensure consistent and accurate evaluation.

### CLI Command

```bash
# Validate the scoring rubric with hardcoded test cases
uv run python main.py validate
```

This runs 3 predefined documentation examples through the scorer and verifies scores fall within expected ranges.

### Python API

```python
from green.agent import validate_rubric

# Run validation
results = validate_rubric(verbose=True)
# Output: Validation Summary: 3/3 passed
```

### Validation Test Cases

| Case | Description | Expected Score |
|------|-------------|----------------|
| `perfect_documentation` | Complete docs with all sections | 75-100 |
| `partial_documentation` | Missing some sections | 35-65 |
| `minimal_documentation` | Bare minimum content | 15-35 |

Each validation case checks that scores fall within expected ranges across all 4 tiers.

## Bias and Contamination

AEO-Bench addresses potential evaluation biases:

### Contamination Prevention
- **Synthetic test cases**: Hand-crafted, not present in any LLM training data
- **Real repos**: Selected for being less famous to reduce contamination risk
- **Ground truth isolation**: White agent cannot access `ground_truth/` directories

### Evaluation Consistency
- LLM judge uses low temperature (0.3) for reproducible scoring
- Keyword-based section detection provides objective measurements
- Multi-tier scoring prevents over-reliance on any single metric

### Why Synthetic + Real Mix?
- **Synthetic**: Guaranteed uncontaminated, controlled complexity
- **Real**: Validates performance on actual open-source patterns
- **Together**: Comprehensive coverage of documentation scenarios

## API Reference

### Green Agent Endpoints
- `POST /` - A2A message endpoint for receiving evaluation requests

### White Agent Endpoints  
- `POST /` - A2A message endpoint for receiving documentation tasks

## License

MIT License

## Authors

CS194 Course Project - Fall 2024
