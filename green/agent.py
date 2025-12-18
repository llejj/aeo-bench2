"""Green agent implementation - manages AEO evaluation and scoring."""

import uvicorn
import tomllib
import dotenv
import json
import time
import logging
import os
import re
import httpx
import uuid
import asyncio
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard, SendMessageSuccessResponse, Message
from a2a.utils import new_agent_text_message, get_text_parts
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import Part, TextPart, MessageSendParams, Role, SendMessageRequest
from litellm import completion

# Set up file logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/green_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('green_agent')

dotenv.load_dotenv()

# Response action name - indicates white agent wants to submit final answer
RESPOND_ACTION_NAME = "respond"


# =============================================================================
# Test Case Loading
# =============================================================================

@dataclass
class TestCase:
    """Represents a test case for AEO evaluation."""
    name: str
    repo_path: Path
    metadata: dict
    ground_truth_readme: Optional[str] = None
    facts: Optional[dict] = None  # Key facts for accuracy scoring


def get_test_repos_path() -> Path:
    """Get the path to test repos directory."""
    # Navigate from green/agent.py to resources/test_repos/
    current_dir = Path(__file__).parent
    return current_dir.parent / "resources" / "test_repos"


def discover_test_cases() -> list[str]:
    """Discover all test case directories."""
    test_repos_path = get_test_repos_path()
    if not test_repos_path.exists():
        return []
    return sorted([
        item.name for item in test_repos_path.iterdir()
        if item.is_dir() and not item.name.startswith('.')
    ])


def load_test_case(name: str) -> TestCase:
    """Load a specific test case by name."""
    repo_path = get_test_repos_path() / name
    
    if not repo_path.exists():
        raise ValueError(f"Test case not found: {name}")
    
    # Load metadata.json
    metadata_path = repo_path / "metadata.json"
    if not metadata_path.exists():
        raise ValueError(f"metadata.json not found for test case: {name}")
    
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    # Load ground truth README if available
    ground_truth_readme = None
    ground_truth_path = repo_path / "ground_truth" / "README.md"
    if ground_truth_path.exists():
        with open(ground_truth_path, 'r') as f:
            ground_truth_readme = f.read()
    
    # Load facts.json for accuracy scoring if available
    facts = None
    facts_path = repo_path / "ground_truth" / "facts.json"
    if facts_path.exists():
        with open(facts_path, 'r') as f:
            facts = json.load(f)
    
    return TestCase(
        name=name,
        repo_path=repo_path,
        metadata=metadata,
        ground_truth_readme=ground_truth_readme,
        facts=facts
    )


# =============================================================================
# File Exploration Tools
# =============================================================================

TOOLS_INFO = [
    {
        "name": "list_directory",
        "description": "List files and directories at the given path within the repository",
        "parameters": {"path": "string - relative path within repo (default: root, use '.')"}
    },
    {
        "name": "read_file",
        "description": "Read the contents of a file within the repository",
        "parameters": {"path": "string - relative path to file within repo"}
    }
]


def execute_tool(tool_name: str, args: dict, test_case: TestCase) -> str:
    """Execute a tool and return the result."""
    if tool_name == "list_directory":
        path = args.get("path", ".")
        target_path = test_case.repo_path / path
        
        # Security check - ensure we stay within repo
        try:
            target_path = target_path.resolve()
            if not str(target_path).startswith(str(test_case.repo_path.resolve())):
                return "Error: Cannot access paths outside the repository"
        except Exception:
            return "Error: Invalid path"
        
        if not target_path.exists():
            return f"Error: Path does not exist: {path}"
        
        if not target_path.is_dir():
            return f"Error: Path is not a directory: {path}"
        
        items = []
        for item in sorted(target_path.iterdir()):
            if item.name.startswith('.'):
                continue
            if item.name == 'ground_truth':  # Hide ground truth from agent
                continue
            suffix = "/" if item.is_dir() else ""
            items.append(f"{item.name}{suffix}")
        
        return json.dumps(items, indent=2)
    
    elif tool_name == "read_file":
        path = args.get("path", "")
        if not path:
            return "Error: 'path' parameter is required"
        
        target_path = test_case.repo_path / path
        
        # Security check - ensure we stay within repo and don't read ground truth
        try:
            target_path = target_path.resolve()
            if not str(target_path).startswith(str(test_case.repo_path.resolve())):
                return "Error: Cannot access paths outside the repository"
            if "ground_truth" in str(target_path):
                return "Error: Cannot access ground truth files"
        except Exception:
            return "Error: Invalid path"
        
        if not target_path.exists():
            return f"Error: File does not exist: {path}"
        
        if not target_path.is_file():
            return f"Error: Path is not a file: {path}"
        
        try:
            with open(target_path, 'r') as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {e}"
    
    else:
        return f"Error: Unknown tool '{tool_name}'"


# =============================================================================
# Scoring - 4-Tier Rubric (100 points total)
# =============================================================================

# Keywords for section detection (Tier 2)
SECTION_KEYWORDS = {
    "installation": ["install", "pip", "requirements", "setup", "prerequisite", "dependencies"],
    "usage": ["usage", "how to run", "run", "execute", "command", "python", "cli"],
    "example": ["example", "output", "demo", "sample", "```"],
}


def detect_sections(readme: str) -> dict:
    """Detect presence of required documentation sections."""
    readme_lower = readme.lower()
    return {
        section: any(kw in readme_lower for kw in keywords)
        for section, keywords in SECTION_KEYWORDS.items()
    }


def score_tier1_structural(parsed_data: Optional[dict]) -> tuple[int, dict]:
    """
    Tier 1: Structural Validity (15 points)
    - Valid JSON response: 5 points
    - README present and non-trivial (>100 chars): 5 points
    - Schema.org metadata structure: 5 points
    """
    score = 0
    details = {}
    
    if parsed_data is None:
        details["valid_json"] = False
        return score, details
    
    # Valid JSON (already parsed)
    details["valid_json"] = True
    score += 5
    
    # README present and non-trivial
    readme = parsed_data.get("readme", "")
    if readme and len(readme) > 100:
        details["has_readme"] = True
        details["readme_length"] = len(readme)
        score += 5
    else:
        details["has_readme"] = False
        details["readme_length"] = len(readme) if readme else 0

    # Schema.org metadata structure
    metadata = parsed_data.get("metadata", {})
    has_context = metadata.get("@context") == "https://schema.org"
    has_type = bool(metadata.get("@type"))
    has_name = bool(metadata.get("name"))

    if has_context and has_type and has_name:
        details["valid_metadata"] = True
        score += 5
    else:
        details["valid_metadata"] = False
        details["metadata_issues"] = {
            "has_context": has_context,
            "has_type": has_type,
            "has_name": has_name
        }
    
    return score, details


def score_tier2_sections(readme: str) -> tuple[int, dict]:
    """
    Tier 2: Required Sections (25 points)
    - Installation/Setup: 8 points
    - Usage/How to Run: 9 points
    - Example/Demo: 8 points
    """
    sections = detect_sections(readme)
    score = 0
    details = {"sections_found": sections}
    
    if sections.get("installation"):
        score += 8
    if sections.get("usage"):
        score += 9
    if sections.get("example"):
        score += 8
    
    details["sections_score"] = score
    return score, details


def score_tier3_accuracy(readme: str, metadata: dict, facts: Optional[dict]) -> tuple[int, dict]:
    """
    Tier 3: Factual Accuracy (30 points) - LLM-judged against facts.json
    - Correct main purpose: 12 points
    - Correct dependencies: 10 points
    - Correct run command: 8 points
    """
    if not facts:
        # No facts available, give partial credit based on general accuracy
        return 15, {"note": "No facts.json available, partial credit given"}
    
    prompt = f"""Evaluate if this documentation accurately describes the code.

GENERATED README:
{readme[:2000]}

GENERATED METADATA:
{json.dumps(metadata, indent=2)}

GROUND TRUTH FACTS:
- Main Purpose: {facts.get('main_purpose', 'N/A')}
- Dependencies: {facts.get('dependencies', [])}
- Run Command: {facts.get('run_command', 'N/A')}
- Must Mention: {facts.get('must_mention', [])}

Score accuracy on these criteria (respond with JSON only):
1. PURPOSE (0-12): Does the README correctly describe the main purpose?
2. DEPENDENCIES (0-10): Are the correct dependencies listed?
3. RUN_COMMAND (0-8): Is there a correct or similar run command?

Respond with JSON:
{{"purpose": <0-12>, "dependencies": <0-10>, "run_command": <0-8>, "reasoning": "<brief explanation>"}}
"""

    try:
        response = completion(
            messages=[
                {"role": "system", "content": "You are an accuracy evaluator. Compare generated docs to ground truth facts. Respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            model="openai/gpt-4o-mini",
            custom_llm_provider="openai",
            temperature=0.3,
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Parse JSON from response
        if "```json" in result_text:
            start = result_text.find("```json") + 7
            end = result_text.find("```", start)
            result_text = result_text[start:end].strip()
        elif result_text.startswith("```"):
            result_text = result_text[3:result_text.rfind("```")].strip()
        
        scores = json.loads(result_text)
        
        purpose_score = min(12, max(0, scores.get("purpose", 0)))
        deps_score = min(10, max(0, scores.get("dependencies", 0)))
        cmd_score = min(8, max(0, scores.get("run_command", 0)))
        
        total = purpose_score + deps_score + cmd_score
        
        return total, {
            "purpose": purpose_score,
            "dependencies": deps_score,
            "run_command": cmd_score,
            "reasoning": scores.get("reasoning", "")
        }
    except Exception as e:
        logger.error(f"Error in Tier 3 accuracy scoring: {e}")
        return 0, {"error": str(e)}


def score_tier4_quality(readme: str, metadata: dict, ground_truth_readme: Optional[str]) -> tuple[int, dict]:
    """
    Tier 4: Quality (30 points) - LLM-judged
    - Clarity and readability: 12 points
    - Completeness for a new user: 10 points
    - Professional formatting: 8 points
    """
    prompt = f"""Evaluate the quality of this AI-generated documentation.

GENERATED README:
{readme[:2500]}

{"REFERENCE README (for comparison):" + chr(10) + ground_truth_readme[:1500] if ground_truth_readme else ""}

Score quality on these criteria (respond with JSON only):
1. CLARITY (0-12): Is it easy to understand? Well-organized with clear explanations?
2. COMPLETENESS (0-10): Could a new user get started from this documentation alone?
3. FORMATTING (0-8): Is markdown properly used? Headers, code blocks, lists formatted well?

Respond with JSON:
{{"clarity": <0-12>, "completeness": <0-10>, "formatting": <0-8>, "feedback": "<brief feedback>"}}
"""

    try:
        response = completion(
            messages=[
                {"role": "system", "content": "You are a documentation quality evaluator. Respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            model="openai/gpt-4o-mini",
            custom_llm_provider="openai",
            temperature=0.3,
        )

        result_text = response.choices[0].message.content.strip()

        # Parse JSON from response
        if "```json" in result_text:
            start = result_text.find("```json") + 7
            end = result_text.find("```", start)
            result_text = result_text[start:end].strip()
        elif result_text.startswith("```"):
            result_text = result_text[3:result_text.rfind("```")].strip()

        scores = json.loads(result_text)

        clarity = min(12, max(0, scores.get("clarity", 0)))
        completeness = min(10, max(0, scores.get("completeness", 0)))
        formatting = min(8, max(0, scores.get("formatting", 0)))

        total = clarity + completeness + formatting

        return total, {
            "clarity": clarity,
            "completeness": completeness,
            "formatting": formatting,
            "feedback": scores.get("feedback", "")
        }
    except Exception as e:
        logger.error(f"Error in Tier 4 quality scoring: {e}")
        return 0, {"error": str(e)}


def score_documentation(response: str, test_case: Optional['TestCase'] = None) -> dict:
    """
    Score the generated documentation using 4-tier rubric.
    
    Tier 1: Structural Validity (15 points) - Automated
    Tier 2: Required Sections (25 points) - Keyword detection
    Tier 3: Factual Accuracy (30 points) - LLM + facts.json
    Tier 4: Quality (30 points) - LLM-judged
    
    Total: 100 points
    """
    result = {
        "tier1_structural": 0,
        "tier2_sections": 0,
        "tier3_accuracy": 0,
        "tier4_quality": 0,
        "total_score": 0,
        "max_score": 100,
        "details": {}
    }
    
    # Parse response
    parsed_data = None
    try:
        text = response.strip()
        
        # Handle markdown code blocks
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            text = text[start:end].strip()
        elif text.startswith("```"):
            start = text.find("```") + 3
            end = text.find("```", start)
            text = text[start:end].strip()
        
        parsed_data = json.loads(text)
    except json.JSONDecodeError as e:
        result["details"]["parse_error"] = str(e)
    
    # Tier 1: Structural
    tier1_score, tier1_details = score_tier1_structural(parsed_data)
    result["tier1_structural"] = tier1_score
    result["details"]["tier1"] = tier1_details
    
    if parsed_data:
        readme = parsed_data.get("readme", "")
        metadata = parsed_data.get("metadata", {})
        
        # Tier 2: Sections
        if readme:
            tier2_score, tier2_details = score_tier2_sections(readme)
            result["tier2_sections"] = tier2_score
            result["details"]["tier2"] = tier2_details
        
        # Tier 3: Accuracy (needs facts from test_case)
        facts = test_case.facts if test_case else None
        if readme:
            tier3_score, tier3_details = score_tier3_accuracy(readme, metadata, facts)
            result["tier3_accuracy"] = tier3_score
            result["details"]["tier3"] = tier3_details
        
        # Tier 4: Quality
        ground_truth = test_case.ground_truth_readme if test_case else None
        if readme:
            tier4_score, tier4_details = score_tier4_quality(readme, metadata, ground_truth)
            result["tier4_quality"] = tier4_score
            result["details"]["tier4"] = tier4_details
    
    # Calculate total
    result["total_score"] = (
        result["tier1_structural"] +
        result["tier2_sections"] +
        result["tier3_accuracy"] +
        result["tier4_quality"]
    )
    
    return result


# =============================================================================
# Rubric Validation (Q8.5)
# =============================================================================

# Hardcoded validation test cases with expected score ranges
VALIDATION_CASES = [
    {
        "name": "perfect_documentation",
        "description": "Complete, well-structured documentation with all required sections",
        "doc": {
            "readme": """# QR Code Generator

A Python tool for generating QR codes from text or URLs.

## Installation

Install using pip:

```bash
pip install qrcode pillow
```

## Usage

Generate a QR code:

```bash
python qr_generator.py "Hello World"
```

### Options

| Option | Description |
|--------|-------------|
| `-o` | Output file path |
| `-s` | QR code size |

## Examples

```python
from qr_generator import generate_qr
generate_qr("https://example.com", "output.png")
```

## Dependencies

- qrcode
- pillow

## License

MIT
""",
            "metadata": {
                "@context": "https://schema.org",
                "@type": "SoftwareSourceCode",
                "name": "QR Code Generator",
                "description": "Generate QR codes from text or URLs",
                "programmingLanguage": "Python"
            }
        },
        "facts": {
            "main_purpose": "Generate QR codes from text or URLs",
            "dependencies": ["qrcode", "pillow"],
            "run_command": "python qr_generator.py",
            "key_features": ["Generate QR codes", "Custom output path", "Custom size"],
            "must_mention": ["qrcode", "pillow", "QR"],
            "main_file": "qr_generator.py"
        },
        "expected_ranges": {
            "tier1_structural": (14, 15),
            "tier2_sections": (23, 25),
            "tier3_accuracy": (24, 30),  # Should score high with matching facts
            "tier4_quality": (22, 30),
            "total": (83, 100)
        }
    },
    {
        "name": "partial_documentation",
        "description": "Incomplete documentation missing some sections",
        "doc": {
            "readme": """# Project

This is a Python project that does something useful.

## How to Run

Run with: python main.py

The output will be printed to console.
""",
            "metadata": {
                "@context": "https://schema.org",
                "@type": "SoftwareSourceCode"
            }
        },
        "facts": {
            "main_purpose": "A data processing utility for CSV files",
            "dependencies": ["pandas", "numpy"],
            "run_command": "python main.py input.csv",
            "key_features": ["CSV parsing", "Data transformation", "Export to JSON"],
            "must_mention": ["pandas", "CSV", "data"],
            "main_file": "main.py"
        },
        "expected_ranges": {
            "tier1_structural": (8, 10),  # Missing name in metadata
            "tier2_sections": (8, 17),    # Has usage but missing install/examples
            "tier3_accuracy": (0, 12),    # Should score low - docs don't match facts
            "tier4_quality": (10, 20),
            "total": (28, 59)
        }
    },
    {
        "name": "minimal_documentation",
        "description": "Minimal documentation that barely meets requirements",
        "doc": {
            "readme": "# Project\n\nA project readme.",
            "metadata": {}
        },
        "facts": {
            "main_purpose": "A web scraping tool for extracting product data",
            "dependencies": ["requests", "beautifulsoup4"],
            "run_command": "python scraper.py --url https://example.com",
            "key_features": ["Web scraping", "HTML parsing", "JSON export"],
            "must_mention": ["requests", "BeautifulSoup", "scrape"],
            "main_file": "scraper.py"
        },
        "expected_ranges": {
            "tier1_structural": (5, 5),   # Valid JSON but no README >100 chars, no metadata
            "tier2_sections": (0, 0),     # No sections detected
            "tier3_accuracy": (0, 10),    # Should score very low - docs don't match facts at all
            "tier4_quality": (5, 15),
            "total": (10, 30)
        }
    }
]


def validate_rubric(verbose: bool = True) -> dict:
    """
    Validate the scoring rubric using hardcoded test cases.
    
    This function runs predefined documentation examples through the scoring
    system and verifies that scores fall within expected ranges.
    
    Returns:
        dict with validation results for each test case
    """
    results = {
        "passed": 0,
        "failed": 0,
        "cases": []
    }
    
    for case in VALIDATION_CASES:
        if verbose:
            print(f"\n{'='*60}")
            print(f"Validating: {case['name']}")
            print(f"Description: {case['description']}")

        # Create a mock TestCase with facts for accuracy scoring
        mock_test_case = TestCase(
            name=case["name"],
            repo_path=Path("/tmp/validation"),  # Dummy path
            metadata={},
            ground_truth_readme=None,
            facts=case.get("facts")  # Use facts from validation case
        )

        # Score the documentation with the mock test case
        doc_json = json.dumps(case["doc"])
        score_result = score_documentation(doc_json, test_case=mock_test_case)
        
        # Check if scores are within expected ranges
        case_passed = True
        tier_results = {}
        
        for tier, (min_expected, max_expected) in case["expected_ranges"].items():
            if tier == "total":
                actual = score_result["total_score"]
            else:
                actual = score_result.get(tier, 0)
            
            in_range = min_expected <= actual <= max_expected
            tier_results[tier] = {
                "actual": actual,
                "expected_range": (min_expected, max_expected),
                "passed": in_range
            }
            
            if not in_range:
                case_passed = False
            
            if verbose:
                status = "✅" if in_range else "❌"
                print(f"  {status} {tier}: {actual} (expected {min_expected}-{max_expected})")
        
        if case_passed:
            results["passed"] += 1
            if verbose:
                print(f"  Result: PASSED ✅")
        else:
            results["failed"] += 1
            if verbose:
                print(f"  Result: FAILED ❌")
        
        results["cases"].append({
            "name": case["name"],
            "passed": case_passed,
            "tiers": tier_results,
            "total_score": score_result["total_score"]
        })
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"Validation Summary: {results['passed']}/{len(VALIDATION_CASES)} passed")
    
    return results


# =============================================================================
# A2A Helpers (inlined from my_a2a)
# =============================================================================

def parse_tags(str_with_tags: str) -> dict:
    """Parse XML-like tags from a string."""
    tags = re.findall(r"<(.*?)>(.*?)</\1>", str_with_tags, re.DOTALL)
    return {tag: content.strip() for tag, content in tags}


async def get_agent_card(url: str, timeout: float = 60.0) -> AgentCard | None:
    """Get agent card with timeout handling."""
    try:
        httpx_client = httpx.AsyncClient(timeout=timeout)
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=url)
        card = await resolver.get_agent_card()
        return card
    except httpx.TimeoutException:
        logger.error(f"Timeout getting agent card from {url}")
        raise
    except Exception as e:
        logger.error(f"Error getting agent card from {url}: {e}")
        raise


async def send_message(url, message, task_id=None, context_id=None, timeout: float = 180.0):
    """Send message to agent with timeout and error handling."""
    try:
        card = await get_agent_card(url)
        httpx_client = httpx.AsyncClient(timeout=timeout)
        client = A2AClient(httpx_client=httpx_client, agent_card=card)

        message_id = uuid.uuid4().hex
        params = MessageSendParams(
            message=Message(
                role=Role.user,
                parts=[Part(TextPart(text=message))],
                message_id=message_id,
                task_id=task_id,
                context_id=context_id,
            )
        )
        request_id = uuid.uuid4().hex
        req = SendMessageRequest(id=request_id, params=params)

        # Use asyncio timeout as additional safeguard
        async with asyncio.timeout(timeout + 30):
            response = await client.send_message(request=req)
        return response
    except asyncio.TimeoutError:
        logger.error(f"Asyncio timeout sending message to {url}")
        raise
    except httpx.TimeoutException:
        logger.error(f"HTTP timeout sending message to {url}")
        raise
    except Exception as e:
        logger.error(f"Error sending message to {url}: {e}")
        raise


# =============================================================================
# Evaluation Loop
# =============================================================================

async def evaluate_test_case(white_agent_url: str, test_case: TestCase, max_steps: int = 15) -> dict:
    """
    Evaluate a single test case by interacting with the white agent.
    
    Similar to tau-bench pattern:
    1. Send task + tools description
    2. Loop: receive tool calls, execute them, send results back
    3. When agent responds with final documentation, score it
    """
    
    # Build initial task message
    task_description = f"""You are tasked with generating documentation for a code repository.

PROJECT: {test_case.metadata.get('name', test_case.name)}
DESCRIPTION: {test_case.metadata.get('description', 'N/A')}

You have access to the following tools to explore the repository:
{json.dumps(TOOLS_INFO, indent=2)}

To use a tool, respond with JSON wrapped in <json>...</json> tags:
<json>
{{"name": "<tool_name>", "kwargs": {{"param": "value"}}}}
</json>

When you're ready to submit your final documentation, use the "{RESPOND_ACTION_NAME}" action:
<json>
{{"name": "{RESPOND_ACTION_NAME}", "kwargs": {{
    "readme": "Your generated README in markdown format",
    "metadata": {{
        "@context": "https://schema.org",
        "@type": "SoftwareSourceCode",
        "name": "...",
        "description": "...",
        "programmingLanguage": "..."
    }}
}}}}
</json>

Start by exploring the repository structure, then read relevant files to understand the code.
Generate comprehensive documentation that would help users understand and use this project.

Begin by listing the directory contents.
"""

    context_id = None
    next_message = task_description
    
    for step in range(max_steps):
        logger.info(f"Step {step + 1}/{max_steps}: Sending message to white agent")
        print(f"@@@ Green agent: Sending message to white agent{'ctx_id=' + str(context_id) if context_id else ''}... -->\n{next_message}")
        
        # Send message to white agent with error handling
        try:
            response = await send_message(white_agent_url, next_message, context_id=context_id)
        except asyncio.TimeoutError:
            logger.error(f"Timeout on step {step + 1}")
            return {
                "test_case": test_case.name,
                "error": f"Timeout on step {step + 1}",
                "steps_taken": step + 1,
                "total_score": 0,
                "max_score": 100
            }
        except Exception as e:
            logger.error(f"Error on step {step + 1}: {e}")
            return {
                "test_case": test_case.name,
                "error": f"Communication error: {str(e)[:100]}",
                "steps_taken": step + 1,
                "total_score": 0,
                "max_score": 100
            }
        
        res_root = response.root
        if not isinstance(res_root, SendMessageSuccessResponse):
            logger.error(f"Unexpected response type: {type(res_root)}")
            return {
                "test_case": test_case.name,
                "error": "Unexpected response from white agent",
                "total_score": 0,
                "max_score": 100
            }
        
        res_result = res_root.result
        if not isinstance(res_result, Message):
            logger.error(f"Unexpected result type: {type(res_result)}")
            return {
                "test_case": test_case.name,
                "error": "Unexpected result from white agent",
                "total_score": 0,
                "max_score": 100
            }
        
        # Track context for conversation continuity
        if context_id is None:
            context_id = res_result.context_id
        
        # Get text response
        text_parts = get_text_parts(res_result.parts)
        if not text_parts:
            logger.error("No text parts in response")
            return {
                "test_case": test_case.name,
                "error": "Empty response from white agent",
                "total_score": 0,
                "max_score": 100
            }
        
        white_text = text_parts[0]
        print(f"@@@ White agent response:\n{white_text}")
        logger.info(f"White agent response:\n{white_text[:500]}...")
        
        # Parse the action from response
        try:
            tags = parse_tags(white_text)
            if "json" not in tags:
                logger.warning("No <json> tag found in response")
                # Try to extract JSON directly
                if "{" in white_text:
                    json_start = white_text.find("{")
                    json_end = white_text.rfind("}") + 1
                    action_json = white_text[json_start:json_end]
                else:
                    return {
                        "test_case": test_case.name,
                        "error": "Could not parse action from response",
                        "total_score": 0,
                        "max_score": 100
                    }
            else:
                action_json = tags["json"]
            
            action_dict = json.loads(action_json)
            action_name = action_dict.get("name", "")
            action_kwargs = action_dict.get("kwargs", {})
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error parsing action: {e}")
            return {
                "test_case": test_case.name,
                "error": f"Could not parse action: {e}",
                "total_score": 0,
                "max_score": 100
            }
        
        # Handle the action
        if action_name == RESPOND_ACTION_NAME:
            # Final response - score it
            logger.info("White agent submitted final documentation")
            
            # Build response JSON for scoring
            final_response = json.dumps({
                "readme": action_kwargs.get("readme", ""),
                "metadata": action_kwargs.get("metadata", {})
            })
            
            score_result = score_documentation(final_response, test_case)
            return {
                "test_case": test_case.name,
                "steps_taken": step + 1,
                **score_result
            }
        
        else:
            # Tool call - execute and send result back
            tool_result = execute_tool(action_name, action_kwargs, test_case)
            print(f"@@@ Tool '{action_name}' called with args: {action_kwargs}")
            print(f"@@@ Tool result:\n{tool_result}")
            logger.info(f"Tool '{action_name}' result: {tool_result[:200]}...")
            
            next_message = f"""Tool call result for '{action_name}':
{tool_result}

Continue exploring or submit your final documentation when ready."""
    
    # Hit max steps without final response
    logger.warning(f"Hit max steps ({max_steps}) without final documentation")
    return {
        "test_case": test_case.name,
        "error": "Max steps reached without final documentation",
        "steps_taken": max_steps,
        "total_score": 0,
        "max_score": 100
    }


# =============================================================================
# Agent Executor
# =============================================================================

class AEOGreenAgentExecutor(AgentExecutor):
    def __init__(self):
        pass

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        logger.info("Green agent: Received a task, parsing...")
        user_input = context.get_user_input()
        logger.info(f"Green agent: Received message:\n{user_input}\n---END MESSAGE---")
        
        # Parse the task configuration
        tags = parse_tags(user_input)
        logger.info(f"Green agent: Parsed tags: {list(tags.keys())}")
        
        white_agent_url = tags.get("white_agent_url", "http://localhost:9002")
        
        # Get test configuration
        if "test_config" in tags:
            test_config = json.loads(tags["test_config"])
        else:
            # Read from TEST_IDS env var, defaulting to [0]
            env_test_ids = os.environ.get("TEST_IDS", "0")
            if env_test_ids.lower() == "all":
                test_config = {"test_ids": None}  # None means all tests
            else:
                test_config = {"test_ids": [int(x) for x in env_test_ids.split()]}
        
        # Discover and load test cases
        all_test_cases = discover_test_cases()
        logger.info(f"Green agent: Found {len(all_test_cases)} test cases: {all_test_cases}")
        
        test_ids = test_config.get("test_ids")
        if test_ids is not None:
            # Run specific tests by index
            selected_cases = [all_test_cases[i] for i in test_ids if i < len(all_test_cases)]
        else:
            selected_cases = all_test_cases
        
        if not selected_cases:
            await event_queue.enqueue_event(
                new_agent_text_message("Error: No test cases found or selected.")
            )
            return
        
        # Run evaluation
        logger.info(f"Green agent: Running evaluation on {len(selected_cases)} test cases")
        results = []
        total_score = 0
        max_possible = 0
        
        timestamp_started = time.time()
        
        for case_name in selected_cases:
            logger.info(f"Green agent: Evaluating test case: {case_name}")
            
            try:
                test_case = load_test_case(case_name)
                result = await evaluate_test_case(white_agent_url, test_case)
                results.append(result)
                
                total_score += result.get("total_score", 0)
                max_possible += result.get("max_score", 100)
                
                logger.info(f"Test case '{case_name}': {result.get('total_score', 0)}/{result.get('max_score', 100)}")
                
            except Exception as e:
                logger.error(f"Error evaluating test case '{case_name}': {e}")
                results.append({
                    "test_case": case_name,
                    "error": str(e),
                    "total_score": 0,
                    "max_score": 100
                })
                max_possible += 100
        
        time_used = time.time() - timestamp_started
        
        # Calculate overall metrics
        avg_score = total_score / len(results) if results else 0
        score_percentage = (total_score / max_possible * 100) if max_possible > 0 else 0
        
        # Determine success
        success = score_percentage >= 60
        result_emoji = "✅" if success else "❌"
        
        # Build summary
        summary = f"""Evaluation Complete {result_emoji}

Overall Score: {total_score}/{max_possible} ({score_percentage:.1f}%)
Average Score: {avg_score:.1f}/100
Time: {time_used:.1f}s
Test Cases: {len(results)}

Scoring Rubric:
  Tier 1 - Structural (15 pts): Valid JSON, README exists, metadata schema
  Tier 2 - Sections (25 pts): Installation, Usage, Examples present
  Tier 3 - Accuracy (30 pts): Correct purpose, dependencies, commands
  Tier 4 - Quality (30 pts): Clarity, completeness, formatting

Individual Results:
"""
        for r in results:
            status = "✅" if r.get("total_score", 0) >= 60 else "❌"
            summary += f"  {status} {r.get('test_case', 'unknown')}: {r.get('total_score', 0)}/{r.get('max_score', 100)}"
            if "error" in r:
                summary += f" (Error: {r['error'][:50]}...)"
            else:
                # Show tier breakdown
                t1 = r.get('tier1_structural', 0)
                t2 = r.get('tier2_sections', 0)
                t3 = r.get('tier3_accuracy', 0)
                t4 = r.get('tier4_quality', 0)
                summary += f" [T1:{t1}/15 T2:{t2}/25 T3:{t3}/30 T4:{t4}/30]"
            summary += "\n"
        
        logger.info(summary)
        await event_queue.enqueue_event(new_agent_text_message(summary))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError


# =============================================================================
# Server Setup
# =============================================================================

def load_agent_card_toml(agent_name):
    current_dir = Path(__file__).parent
    with open(current_dir / f"{agent_name}.toml", "rb") as f:
        return tomllib.load(f)


def start_green_agent(agent_name="agent_card", host="localhost", port=9001, external_url=""):
    print("Starting green agent...")
    agent_card_dict = load_agent_card_toml(agent_name)
    
    # Use external URL if provided (for tunnel access), otherwise use local URL
    if external_url:
        url = external_url if external_url.startswith("http") else f"https://{external_url}"
        print(f"Using external URL: {url}")
    else:
        url = f"http://{host}:{port}"
        print(f"Using local URL: {url}")
    agent_card_dict["url"] = url

    request_handler = DefaultRequestHandler(
        agent_executor=AEOGreenAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )

    app = A2AStarletteApplication(
        agent_card=AgentCard(**agent_card_dict),
        http_handler=request_handler,
    )

    uvicorn.run(app.build(), host=host, port=port)

