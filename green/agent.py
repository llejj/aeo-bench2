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
    
    return TestCase(
        name=name,
        repo_path=repo_path,
        metadata=metadata,
        ground_truth_readme=ground_truth_readme
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
    },
    {
        "name": "get_project_info",
        "description": "Get project name and description from metadata",
        "parameters": {}
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
    
    elif tool_name == "get_project_info":
        return json.dumps({
            "name": test_case.metadata.get("name", test_case.name),
            "description": test_case.metadata.get("description", "No description available"),
            "language": test_case.metadata.get("language", "Unknown"),
            "domain": test_case.metadata.get("domain", "Unknown"),
            "files": test_case.metadata.get("files", [])
        }, indent=2)
    
    else:
        return f"Error: Unknown tool '{tool_name}'"


# =============================================================================
# Scoring
# =============================================================================

def score_documentation(response: str, ground_truth_readme: Optional[str] = None) -> dict:
    """
    Score the generated documentation.
    
    Scoring breakdown:
    - Structural (30 points):
      - Valid JSON: 10 points
      - README length > 50 chars: 10 points
      - Valid schema.org metadata: 10 points
    - Semantic (70 points) - via LLM judge:
      - Clarity: 25 points
      - Completeness: 25 points
      - Accuracy: 20 points
    """
    result = {
        "structural_score": 0,
        "semantic_score": 0,
        "total_score": 0,
        "max_score": 100,
        "details": {}
    }
    
    # Parse response
    parsed_data = None
    try:
        # Try to extract JSON from response
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
        result["details"]["valid_json"] = True
        result["structural_score"] += 10
    except json.JSONDecodeError:
        result["details"]["valid_json"] = False
        result["details"]["parse_error"] = "Could not parse response as JSON"
    
    if parsed_data:
        # Check README
        readme = parsed_data.get("readme", "")
        if readme and len(readme) > 50:
            result["details"]["has_readme"] = True
            result["structural_score"] += 10
        else:
            result["details"]["has_readme"] = False
        
        # Check metadata
        metadata = parsed_data.get("metadata", {})
        if metadata.get("@context") == "https://schema.org" and metadata.get("@type"):
            result["details"]["has_valid_metadata"] = True
            result["structural_score"] += 10
        else:
            result["details"]["has_valid_metadata"] = False
        
        # Semantic scoring via LLM
        if readme:
            try:
                semantic_result = score_with_llm(readme, metadata, ground_truth_readme)
                result["semantic_score"] = semantic_result["score"]
                result["details"]["semantic"] = semantic_result["feedback"]
            except Exception as e:
                logger.error(f"Error in LLM scoring: {e}")
                result["details"]["semantic_error"] = str(e)
    
    result["total_score"] = result["structural_score"] + result["semantic_score"]
    return result


def score_with_llm(readme: str, metadata: dict, ground_truth_readme: Optional[str] = None) -> dict:
    """Use LLM to score documentation quality."""
    
    prompt = f"""Evaluate this AI-generated documentation for a code repository.

GENERATED README:
{readme[:2000]}{"..." if len(readme) > 2000 else ""}

GENERATED METADATA:
{json.dumps(metadata, indent=2)}

{"GROUND TRUTH README (for reference):" + chr(10) + ground_truth_readme[:1500] if ground_truth_readme else ""}

Score on these criteria (respond with JSON only):
1. CLARITY (0-25 points): Is it easy to understand? Well-structured?
2. COMPLETENESS (0-25 points): Does it cover features, usage, examples?
3. ACCURACY (0-20 points): Does it seem accurate based on what's described?

Respond with JSON:
{{"clarity": <0-25>, "completeness": <0-25>, "accuracy": <0-20>, "feedback": "<brief feedback>"}}
"""

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
    
    total = min(25, max(0, scores.get("clarity", 0))) + \
            min(25, max(0, scores.get("completeness", 0))) + \
            min(20, max(0, scores.get("accuracy", 0)))
    
    return {
        "score": total,
        "feedback": {
            "clarity": scores.get("clarity", 0),
            "completeness": scores.get("completeness", 0),
            "accuracy": scores.get("accuracy", 0),
            "comment": scores.get("feedback", "")
        }
    }


# =============================================================================
# A2A Helpers (inlined from my_a2a)
# =============================================================================

def parse_tags(str_with_tags: str) -> dict:
    """Parse XML-like tags from a string."""
    tags = re.findall(r"<(.*?)>(.*?)</\1>", str_with_tags, re.DOTALL)
    return {tag: content.strip() for tag, content in tags}


async def get_agent_card(url: str) -> AgentCard | None:
    httpx_client = httpx.AsyncClient(timeout=60.0)
    resolver = A2ACardResolver(httpx_client=httpx_client, base_url=url)
    card = await resolver.get_agent_card()
    return card


async def send_message(url, message, task_id=None, context_id=None):
    card = await get_agent_card(url)
    httpx_client = httpx.AsyncClient(timeout=120.0)
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
    response = await client.send_message(request=req)
    return response


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
        
        # Send message to white agent
        response = await send_message(white_agent_url, next_message, context_id=context_id)
        
        res_root = response.root
        if not isinstance(res_root, SendMessageSuccessResponse):
            logger.error(f"Unexpected response type: {type(res_root)}")
            return {"error": "Unexpected response from white agent", "score": 0}
        
        res_result = res_root.result
        if not isinstance(res_result, Message):
            logger.error(f"Unexpected result type: {type(res_result)}")
            return {"error": "Unexpected result from white agent", "score": 0}
        
        # Track context for conversation continuity
        if context_id is None:
            context_id = res_result.context_id
        
        # Get text response
        text_parts = get_text_parts(res_result.parts)
        if not text_parts:
            logger.error("No text parts in response")
            return {"error": "Empty response from white agent", "score": 0}
        
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
                    return {"error": "Could not parse action from response", "score": 0}
            else:
                action_json = tags["json"]
            
            action_dict = json.loads(action_json)
            action_name = action_dict.get("name", "")
            action_kwargs = action_dict.get("kwargs", {})
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error parsing action: {e}")
            return {"error": f"Could not parse action: {e}", "score": 0}
        
        # Handle the action
        if action_name == RESPOND_ACTION_NAME:
            # Final response - score it
            logger.info("White agent submitted final documentation")
            
            # Build response JSON for scoring
            final_response = json.dumps({
                "readme": action_kwargs.get("readme", ""),
                "metadata": action_kwargs.get("metadata", {})
            })
            
            score_result = score_documentation(final_response, test_case.ground_truth_readme)
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
        "score": 0
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
            # Default: run first 2 test cases to stay within timeout
            # For full evaluation, pass test_config with test_ids: null
            test_config = {"test_ids": [0, 1]}
        
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

Individual Results:
"""
        for r in results:
            status = "✅" if r.get("total_score", 0) >= 60 else "❌"
            summary += f"  {status} {r.get('test_case', 'unknown')}: {r.get('total_score', 0)}/{r.get('max_score', 100)}"
            if "error" in r:
                summary += f" (Error: {r['error'][:50]}...)"
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

