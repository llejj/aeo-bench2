# White Agent Report: Documentation Generation on AEO-Bench

## Abstract

This report describes a documentation generation agent evaluated on AEO-Bench, a benchmark that tests AI agents' ability to transform raw code into well-documented, discoverable forms. The white agent uses GPT-4o with tool-augmented reasoning to iteratively explore code repositories before generating comprehensive README documentation and schema.org metadata. Evaluated across 6 test cases spanning 4 domains (security utilities, text processing, CLI tools, and ASCII art libraries), the agent achieves an average score of 75-80% on a 100-point rubric measuring structural validity, section coverage, factual accuracy, and documentation quality. Key findings include: (1) iterative exploration significantly improves accuracy over single-shot generation, (2) the agent generalizes across synthetic and real-world repositories without domain-specific tuning, and (3) performance is primarily limited by exploration depth rather than reasoning quality.

## Benchmark: AEO-Bench

### Related Work

Existing benchmarks evaluate AI agents on various capabilities:
- **SWE-Bench** tests coding ability by having agents fix GitHub issues, but does not assess documentation quality
- **DocPrompting** focuses on function-level docstring generation, lacking project-level documentation
- **HumanEval** and **MBPP** test code generation from specifications, not documentation generation

AEO-Bench fills a gap by evaluating project-level documentation generation, including README files and schema.org metadata for AI discoverability.

### Benchmark Overview

AEO-Bench evaluates agents on generating documentation for 6 test repositories:

| Category | Test Cases | Domain |
|----------|------------|--------|
| Synthetic | password_generator, countdown_timer, word_counter | Security, CLI, Text Processing |
| Real (GitHub) | art_github (2k+ stars), dotenv_github (7k+ stars), pyfiglet_github (1.4k+ stars) | ASCII Art, Configuration |

**Inputs**: The agent receives a task description and access to two tools:
- `list_directory(path)`: List files and subdirectories
- `read_file(path)`: Read file contents

**Outputs**: JSON response containing:
- `readme`: Markdown documentation with title, description, installation, usage, examples
- `metadata`: schema.org JSON-LD with @context, @type, name, description, programmingLanguage

**Evaluation**: 4-tier rubric (100 points total):
1. **Tier 1 - Structural (15 pts)**: Valid JSON, README >100 chars, valid schema.org structure
2. **Tier 2 - Sections (25 pts)**: Installation (8), Usage (9), Examples (8) via keyword detection
3. **Tier 3 - Accuracy (30 pts)**: Purpose (12), Dependencies (10), Run command (8) via LLM judge
4. **Tier 4 - Quality (30 pts)**: Clarity (12), Completeness (10), Formatting (8) via LLM judge

## White Agent Framework

### Architecture

The white agent implements a tool-augmented reasoning architecture:

```
┌─────────────────────────────────────────────────────────┐
│                    White Agent                          │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌──────────────────────────┐   │
│  │ System Prompt   │    │ Conversation History     │   │
│  │ - Instructions  │    │ - context_id -> messages │   │
│  │ - Output format │    │ - Multi-turn support     │   │
│  └────────┬────────┘    └────────────┬─────────────┘   │
│           │                          │                  │
│           v                          v                  │
│  ┌─────────────────────────────────────────────────┐   │
│  │               GPT-4o (temp=0.3)                 │   │
│  └─────────────────────────────────────────────────┘   │
│                          │                              │
│                          v                              │
│  ┌─────────────────────────────────────────────────┐   │
│  │  JSON Response: tool call OR final docs         │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Decision Pipeline

1. **Receive message**: Task description or tool result from green agent
2. **Update history**: Append to conversation for context_id
3. **Call LLM**: GPT-4o generates next action based on accumulated context
4. **Parse response**: Extract JSON from `<json>...</json>` tags
5. **Return action**: Either tool call (continue) or respond (terminate)

### Key Design Choices

- **Tool-augmented reasoning**: Exploration before generation improves accuracy
- **Conversation history**: Enables coherent multi-step interactions
- **Low temperature (0.3)**: Balances consistency with reasonable variation
- **Structured output**: JSON format ensures parseable responses

## Experiments

### Quantitative Results

| Test Case | Total | T1 | T2 | T3 | T4 | Steps |
|-----------|-------|----|----|----|----|-------|
| password_generator | 82/100 | 15/15 | 25/25 | 24/30 | 18/30 | 3 |
| countdown_timer | 79/100 | 15/15 | 25/25 | 22/30 | 17/30 | 4 |
| word_counter | 75/100 | 15/15 | 17/25 | 25/30 | 18/30 | 3 |
| art_github | 80/100 | 15/15 | 25/25 | 22/30 | 18/30 | 5 |
| dotenv_github | 76/100 | 15/15 | 25/25 | 20/30 | 16/30 | 4 |
| pyfiglet_github | 76/100 | 15/15 | 25/25 | 20/30 | 16/30 | 4 |
| **Average** | **78/100** | 15/15 | 23.7/25 | 22.2/30 | 17.2/30 | 3.8 |

### Analysis

1. **Structural Consistency**: Perfect scores on Tier 1 across all tests demonstrate reliable JSON formatting and schema.org compliance.

2. **Section Coverage**: High Tier 2 scores (94.8%) indicate the system prompt effectively guides section generation. The word_counter dip (17/25) stems from minimal example output in that repository.

3. **Accuracy Variation**: Tier 3 scores vary based on exploration depth. Repositories with clear main files (password_generator, word_counter) score higher than complex multi-file projects.

4. **Quality Ceiling**: Tier 4 scores plateau around 17-18/30, suggesting room for improvement in documentation polish and user-friendliness.

### Baseline Comparison

| Approach | Avg Score | Notes |
|----------|-----------|-------|
| No exploration (direct generation) | ~45/100 | Fails Tier 3 accuracy checks |
| Single-file reading | ~60/100 | Misses dependencies and context |
| **Our approach (iterative)** | **78/100** | Full exploration before generation |

### Generalization

The agent performs consistently across:
- **Repository complexity**: Synthetic (1 file) vs. real (multi-file) projects
- **Domains**: Security, text processing, CLI, libraries
- **Code patterns**: CLI tools, importable libraries, configuration utilities

No domain-specific tuning was required, demonstrating the generality of the exploration-first approach.

### Limitations

1. **Exploration depth**: Agent sometimes misses subdirectories, reducing accuracy
2. **Quality ceiling**: Generated documentation is functional but not polished
3. **Token efficiency**: Complex repositories require more exploration tokens

### Future Work

- Add explicit planning step before exploration
- Implement iterative refinement of generated documentation
- Fine-tune on high-quality documentation examples
