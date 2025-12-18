"""White agent v2 - LangGraph-based documentation generator with Planner/Explorer/Generator nodes."""

import json
import uvicorn
import tomllib
import dotenv
import logging
from pathlib import Path
from typing import TypedDict, Literal, Optional

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard
from a2a.utils import new_agent_text_message
from litellm import completion

from langgraph.graph import StateGraph, END

# Set up file logging (same as baseline)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/white2_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('white2_agent')

dotenv.load_dotenv()


# ============================================================================
# State Definition
# ============================================================================

class AgentState(TypedDict):
    """State maintained across the agent's execution."""
    phase: Literal["planning", "exploring", "generating"]
    project_name: str
    project_description: str
    files_discovered: list[str]  # All files found (with full paths)
    directories_discovered: list[str]  # All directories found
    directories_explored: list[str]  # Directories we've listed
    files_read: dict[str, str]
    exploration_plan: list[str]
    messages: list[dict]
    next_action: Optional[dict]  # The action to return to green agent


# ============================================================================
# Node Prompts
# ============================================================================

PLANNER_PROMPT = """You are a documentation planning agent. Your task is to THOROUGHLY explore a code repository's structure before creating an exploration plan.

PROJECT: {project_name}
DESCRIPTION: {project_description}

DIRECTORIES ALREADY EXPLORED:
{explored_dirs}

FILES DISCOVERED SO FAR:
{files_list}

DIRECTORIES NOT YET EXPLORED:
{unexplored_dirs}

CRITICAL RULES:
1. You MUST explore ALL unexplored directories before creating a plan
2. If there are ANY directories in "DIRECTORIES NOT YET EXPLORED", you MUST explore them first
3. Only create a plan when ALL directories have been explored

If there are ANY unexplored directories (even if you think they might not be important), respond with:
<json>
{{
    "action": "explore_directory",
    "directory": "path/to/dir",
    "reasoning": "Why I need to explore this directory"
}}
</json>

ONLY when there are ZERO unexplored directories remaining, create the final plan:
<json>
{{
    "action": "create_plan",
    "reasoning": "Your step-by-step reasoning about what files to read",
    "plan": ["path/to/file1.py", "path/to/file2.py", ...]
}}
</json>

Your plan MUST include:
- The main source code files (not just setup.py)
- At least 3-5 files for comprehensive documentation
- Prioritize .py files in the main package directory"""


EXPLORER_PROMPT = """You are a code exploration agent. Your task is to read ALL files in your exploration plan before generating documentation.

PROJECT: {project_name}
DESCRIPTION: {project_description}

EXPLORATION PLAN: {exploration_plan}

FILES ALREADY READ:
{files_read_summary}

FILES DISCOVERED:
{files_discovered}

CRITICAL RULES:
1. You MUST read ALL files in your exploration plan before saying "ready"
2. You should read at least 2-3 files minimum for good documentation
3. Only say "ready" when you have read ALL planned files AND have enough information

Count the files you've read vs the plan:
- If there are files in the plan you haven't read yet, read the next one
- Only say "ready" when the plan is complete

Respond with a JSON object:
<json>
{{
    "reasoning": "Which files remain unread from the plan",
    "action": "read_file" or "ready",
    "file_path": "path/to/file.py"  // only if action is "read_file"
}}
</json>"""


GENERATOR_PROMPT = """You are a documentation generation agent. Based on the code you've explored, generate comprehensive documentation.

PROJECT: {project_name}
DESCRIPTION: {project_description}

FILES READ:
{files_content}

Generate a comprehensive README following this EXACT structure:

# [Project Name]

[One paragraph description of what the project does and why it's useful]

## Features

- [Feature 1]
- [Feature 2]
- [Feature 3]

## Installation

```bash
pip install [project_name]
```

Or install from source:
```bash
git clone [repo_url]
cd [project_name]
pip install -e .
```

## Usage

[Explain how to use the main functionality]

```python
# Example code showing basic usage
```

## Examples

### Example 1: [Description]
```python
# Complete runnable example
```

### Example 2: [Description]
```python
# Another complete example
```

## API Reference

[Document main functions/classes with their parameters and return values]

---

CRITICAL REQUIREMENTS:
- You MUST include ALL sections: Features, Installation, Usage, Examples, API Reference
- You MUST use these exact markdown headers: ## Features, ## Installation, ## Usage, ## Examples
- You MUST include working code examples
- Be specific and detailed based on the actual code you read, not generic placeholders
- The README should be at least 50 lines long

IMPORTANT: Respond with JSON wrapped in <json>...</json> tags (NOT ```json code blocks).
Use \\n for newlines in the readme string. Escape any quotes with \\.

<json>
{{
    "readme": "# {project_name}\\n\\n[Description]\\n\\n## Features\\n\\n- Feature 1\\n- Feature 2\\n\\n## Installation\\n\\n[Installation instructions]\\n\\n## Usage\\n\\n[Usage instructions]\\n\\n## Examples\\n\\n[Examples]\\n\\n## API Reference\\n\\n[API docs]",
    "metadata": {{
        "@context": "https://schema.org",
        "@type": "SoftwareSourceCode",
        "name": "{project_name}",
        "description": "[Actual description based on code]",
        "programmingLanguage": "Python"
    }}
}}
</json>"""


# ============================================================================
# LLM Helper
# ============================================================================

def call_llm(messages: list[dict], temperature: float = 0.3) -> str:
    """Call the LLM and return the response text."""
    response = completion(
        messages=messages,
        model="openai/gpt-4o",
        custom_llm_provider="openai",
        temperature=temperature,
    )
    return response.choices[0].message.content


def extract_json(text: str) -> dict:
    """Extract JSON from <json>...</json> tags, ```json blocks, or raw JSON."""
    import re

    logger.debug(f"extract_json input (first 200 chars): {repr(text[:200])}")

    # Try to find JSON in <json> tags (preferred - unambiguous)
    match = re.search(r'<json>\s*(.*?)\s*</json>', text, re.DOTALL)
    if match:
        logger.debug("Found <json> tags")
        return json.loads(match.group(1))

    # For ```json blocks, we need to handle nested ``` code blocks in the content
    # Strategy: Find ```json, then find matching closing ``` by looking for JSON structure
    if '```json' in text:
        start_idx = text.find('```json')
        if start_idx != -1:
            json_start = start_idx + 7  # After ```json
            # Find where the JSON object starts (first {)
            brace_idx = text.find('{', json_start)
            if brace_idx != -1:
                # Count braces to find the end of JSON object
                depth = 0
                in_string = False
                escape = False
                for i, char in enumerate(text[brace_idx:], brace_idx):
                    if escape:
                        escape = False
                        continue
                    if char == '\\':
                        escape = True
                        continue
                    if char == '"' and not escape:
                        in_string = not in_string
                        continue
                    if in_string:
                        continue
                    if char == '{':
                        depth += 1
                    elif char == '}':
                        depth -= 1
                        if depth == 0:
                            json_str = text[brace_idx:i+1]
                            logger.debug(f"Found JSON by brace matching: {repr(json_str[:100])}")
                            return json.loads(json_str)

    # Fallback: Try greedy match for ```json...``` (gets last ```)
    match = re.search(r'```json\s*(.*)\s*```', text, re.DOTALL)
    if match:
        content = match.group(1).strip()
        # Find the actual JSON object in the content
        if '{' in content:
            brace_start = content.find('{')
            brace_end = content.rfind('}')
            if brace_start != -1 and brace_end != -1:
                json_str = content[brace_start:brace_end+1]
                logger.debug(f"Found ```json block (greedy): {repr(json_str[:100])}")
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass

    # Try to find JSON in ``` code blocks (no language specifier)
    match = re.search(r'```\s*(.*?)\s*```', text, re.DOTALL)
    if match:
        logger.debug(f"Found ``` block: {repr(match.group(1)[:100])}")
        return json.loads(match.group(1))

    logger.debug("No code block found, trying raw JSON parse")
    # Try to parse as raw JSON
    return json.loads(text)


# ============================================================================
# Node Functions
# ============================================================================

def planner_node(state: AgentState) -> AgentState:
    """Explore directory structure and create an exploration plan."""
    logger.info("PLANNER NODE: Analyzing directory structure")

    # Identify unexplored directories
    unexplored = [d for d in state["directories_discovered"]
                  if d not in state["directories_explored"]]

    print(f"\n>>> PLANNER: {len(state['directories_explored'])} dirs explored, {len(unexplored)} remaining, {len(state['files_discovered'])} files found")

    # Format the prompt
    prompt = PLANNER_PROMPT.format(
        project_name=state["project_name"],
        project_description=state["project_description"],
        explored_dirs="\n".join(f"- {d}" for d in state["directories_explored"]) or "- . (root)",
        files_list="\n".join(f"- {f}" for f in state["files_discovered"]) or "None yet",
        unexplored_dirs="\n".join(f"- {d}" for d in unexplored) or "None"
    )

    messages = [{"role": "user", "content": prompt}]
    response = call_llm(messages)
    logger.info(f"PLANNER response: {response[:500]}...")

    try:
        result = extract_json(response)
        action = result.get("action", "create_plan")

        if action == "explore_directory" and result.get("directory"):
            # Need to explore more directories
            directory = result["directory"]
            state["next_action"] = {
                "name": "list_directory",
                "kwargs": {"path": directory}
            }
            logger.info(f"PLANNER: Will explore directory {directory}")
            print(f">>> PLANNER: Decision = explore directory '{directory}'")
            # Stay in planning phase
        else:
            # Ready to create the plan
            state["exploration_plan"] = result.get("plan", [])
            logger.info(f"PLANNER: Created plan with {len(state['exploration_plan'])} files: {state['exploration_plan']}")
            print(f">>> PLANNER: Decision = create plan with {len(state['exploration_plan'])} files")
            print(f">>> PLANNER: Files to read: {state['exploration_plan']}")

            # Transition to exploring phase
            state["phase"] = "exploring"

            # Set next action to read first file in plan
            if state["exploration_plan"]:
                first_file = state["exploration_plan"][0]
                state["next_action"] = {
                    "name": "read_file",
                    "kwargs": {"path": first_file}
                }
            else:
                # No files to read, go straight to generating
                state["phase"] = "generating"
                state["next_action"] = None

    except Exception as e:
        logger.error(f"PLANNER: Failed to parse response: {e}")
        # Default plan: read all .py files discovered
        state["exploration_plan"] = [f for f in state["files_discovered"] if f.endswith('.py')][:5]
        state["phase"] = "exploring"
        if state["exploration_plan"]:
            state["next_action"] = {
                "name": "read_file",
                "kwargs": {"path": state["exploration_plan"][0]}
            }

    return state


def explorer_node(state: AgentState) -> AgentState:
    """Read files from the plan. No LLM needed - just iterate through the plan."""
    logger.info("EXPLORER NODE: Reading next file from plan")

    # Find unread files from the plan
    unread = [f for f in state["exploration_plan"] if f not in state["files_read"]]
    total = len(state["exploration_plan"])
    read_count = total - len(unread)

    if unread:
        # Read the next file in the plan
        next_file = unread[0]
        state["next_action"] = {
            "name": "read_file",
            "kwargs": {"path": next_file}
        }
        logger.info(f"EXPLORER: Will read {next_file} ({len(unread)} files remaining)")
        print(f">>> EXPLORER: Reading file {read_count + 1}/{total}: {next_file}")
    else:
        # All files read, move to generating
        state["phase"] = "generating"
        state["next_action"] = None
        logger.info(f"EXPLORER: All {len(state['exploration_plan'])} files read, ready to generate")
        print(f">>> EXPLORER: Done! Read all {total} files, transitioning to GENERATOR")

    return state


def generator_node(state: AgentState) -> AgentState:
    """Generate the final documentation."""
    logger.info("GENERATOR NODE: Generating documentation")

    print(f"\n>>> GENERATOR: Creating docs from {len(state['files_read'])} files")
    print(f">>> GENERATOR: Files: {list(state['files_read'].keys())}")

    # Format files content
    files_content = "\n\n".join(
        f"=== {path} ===\n{content}"
        for path, content in state["files_read"].items()
    )

    prompt = GENERATOR_PROMPT.format(
        project_name=state["project_name"],
        project_description=state["project_description"],
        files_content=files_content or "No files were read."
    )

    messages = [{"role": "user", "content": prompt}]
    response = call_llm(messages)
    logger.info(f"GENERATOR response: {response[:500]}...")

    try:
        result = extract_json(response)
        state["next_action"] = {
            "name": "respond",
            "kwargs": {
                "readme": result.get("readme", "# Documentation\n\nNo documentation generated."),
                "metadata": result.get("metadata", {
                    "@context": "https://schema.org",
                    "@type": "SoftwareSourceCode",
                    "name": state["project_name"],
                    "description": state["project_description"],
                    "programmingLanguage": "Python"
                })
            }
        }
        logger.info("GENERATOR: Created final documentation")
    except Exception as e:
        logger.error(f"GENERATOR: Failed to parse response: {e}")
        # Return minimal documentation
        state["next_action"] = {
            "name": "respond",
            "kwargs": {
                "readme": f"# {state['project_name']}\n\n{state['project_description']}",
                "metadata": {
                    "@context": "https://schema.org",
                    "@type": "SoftwareSourceCode",
                    "name": state["project_name"],
                    "description": state["project_description"],
                    "programmingLanguage": "Python"
                }
            }
        }

    state["phase"] = "done"
    return state


# ============================================================================
# Graph Builder
# ============================================================================

def build_graph():
    """Build the LangGraph state machine."""
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("planner", planner_node)
    graph.add_node("explorer", explorer_node)
    graph.add_node("generator", generator_node)

    # Add edges based on phase
    def route_by_phase(state: AgentState) -> str:
        phase = state.get("phase", "planning")
        if phase == "planning":
            return "planner"
        elif phase == "exploring":
            return "explorer"
        elif phase == "generating":
            return "generator"
        else:
            return END

    graph.set_conditional_entry_point(route_by_phase)

    # After each node, we exit to return action to green agent
    graph.add_edge("planner", END)
    graph.add_edge("explorer", END)
    graph.add_edge("generator", END)

    return graph.compile()


# ============================================================================
# A2A Executor
# ============================================================================

class AEOWhiteAgentExecutor(AgentExecutor):
    """White agent executor using LangGraph for structured decision making."""

    def __init__(self):
        self.ctx_id_to_state: dict[str, AgentState] = {}
        self.graph = build_graph()

    def _parse_initial_message(self, message: str) -> tuple[str, str]:
        """Extract project name and description from initial task message."""
        # Look for PROJECT: and DESCRIPTION: markers
        import re

        project_match = re.search(r'PROJECT:\s*(.+?)(?:\n|DESCRIPTION:)', message, re.IGNORECASE)
        project_name = project_match.group(1).strip() if project_match else "Unknown Project"

        desc_match = re.search(r'DESCRIPTION:\s*(.+?)(?:\n\n|You have access)', message, re.IGNORECASE | re.DOTALL)
        description = desc_match.group(1).strip() if desc_match else ""

        return project_name, description

    def _parse_tool_result(self, message: str) -> tuple[str, str, str]:
        """Parse tool result message from green agent."""
        import re

        # Extract tool name
        tool_match = re.search(r"Tool call result for '(\w+)':", message)
        tool_name = tool_match.group(1) if tool_match else "unknown"

        # Extract the result (everything between the tool header and the "Continue exploring" footer)
        result_match = re.search(r"Tool call result for '\w+':\s*(.+?)(?:\n\nContinue exploring|$)", message, re.DOTALL)
        result = result_match.group(1).strip() if result_match else message

        # For read_file, try to get the path from the result or previous action
        path = ""
        if tool_name == "read_file":
            # The path might be mentioned in the result or we track it separately
            path_match = re.search(r"Contents of (.+?):", result)
            path = path_match.group(1) if path_match else ""

        return tool_name, path, result

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        user_input = context.get_user_input()
        logger.info(f"White2 agent: Received message:\n{user_input[:500]}...")

        ctx_id = context.context_id

        # Initialize or get state
        if ctx_id not in self.ctx_id_to_state:
            # First message - initialize state
            project_name, project_description = self._parse_initial_message(user_input)

            self.ctx_id_to_state[ctx_id] = AgentState(
                phase="planning",
                project_name=project_name,
                project_description=project_description,
                files_discovered=[],
                directories_discovered=[],
                directories_explored=[],
                files_read={},
                exploration_plan=[],
                messages=[],
                next_action=None
            )

            # First action is always list_directory to see what files exist
            action = {"name": "list_directory", "kwargs": {"path": "."}}
            response_text = f"<json>{json.dumps(action)}</json>"

            logger.info(f"White2 agent: Initial action - list_directory")
            await event_queue.enqueue_event(
                new_agent_text_message(response_text, context_id=ctx_id)
            )
            return

        state = self.ctx_id_to_state[ctx_id]
        state["messages"].append({"role": "user", "content": user_input})

        # Parse the tool result and update state
        tool_name, path, result = self._parse_tool_result(user_input)

        if tool_name == "list_directory":
            # Parse directory listing and separate files from directories
            # Get the directory path that was listed
            listed_dir = "."
            if state.get("next_action") and state["next_action"].get("name") == "list_directory":
                listed_dir = state["next_action"]["kwargs"].get("path", ".")

            # Mark this directory as explored
            if listed_dir not in state["directories_explored"]:
                state["directories_explored"].append(listed_dir)

            # Check if result is an error (not a directory listing)
            if result.startswith("Error:") or "is not a directory" in result:
                logger.info(f"White2 agent: Directory listing error for {listed_dir}: {result[:100]}")
                # Remove this path from directories_discovered if it was mistakenly added
                if listed_dir in state["directories_discovered"]:
                    state["directories_discovered"].remove(listed_dir)
                # Add it to files_discovered instead
                if listed_dir not in state["files_discovered"] and listed_dir != ".":
                    state["files_discovered"].append(listed_dir)
            else:
                try:
                    items = json.loads(result)
                except:
                    items = [f.strip() for f in result.split('\n') if f.strip()]

                # Separate files and directories, build full paths
                for item in items:
                    # Build full path
                    if listed_dir == ".":
                        full_path = item
                    else:
                        full_path = f"{listed_dir}/{item}"

                    # Directories typically end with / or don't have extensions
                    if item.endswith('/'):
                        dir_path = full_path.rstrip('/')
                        if dir_path not in state["directories_discovered"]:
                            state["directories_discovered"].append(dir_path)
                    elif '.' not in item and not item.startswith('_'):
                        # Likely a directory (heuristic)
                        if full_path not in state["directories_discovered"]:
                            state["directories_discovered"].append(full_path)
                    else:
                        # It's a file
                        if full_path not in state["files_discovered"]:
                            state["files_discovered"].append(full_path)

                logger.info(f"White2 agent: Explored {listed_dir}, found {len(state['files_discovered'])} files, {len(state['directories_discovered'])} dirs")

        elif tool_name == "read_file":
            # Store the file content
            # Try to extract path from the last action we took
            if state.get("next_action") and state["next_action"].get("name") == "read_file":
                path = state["next_action"]["kwargs"].get("path", path)
            if path:
                state["files_read"][path] = result
                logger.info(f"White2 agent: Read file {path} ({len(result)} chars)")

        # Run the graph to get next action
        old_phase = state['phase']
        logger.info(f"White2 agent: Running graph in phase '{state['phase']}'")
        result_state = self.graph.invoke(state)

        # Print phase transition if changed
        if result_state.get("phase") != old_phase:
            print(f">>> Phase transition: {old_phase} -> {result_state.get('phase')}")

        # If phase changed to "generating" but no action yet, run graph again for generator
        if result_state.get("phase") == "generating" and result_state.get("next_action") is None:
            logger.info("White2 agent: EXPLORER finished, running GENERATOR")
            result_state = self.graph.invoke(result_state)

        # Update our stored state
        self.ctx_id_to_state[ctx_id] = result_state

        # Get the action to return
        action = result_state.get("next_action")
        if action:
            response_text = f"<json>{json.dumps(action)}</json>"
            logger.info(f"White2 agent: Returning action {action['name']}")

            # Print tool call or final response
            if action['name'] == 'respond':
                print(f"\n{'='*60}")
                print(f">>> FINAL DOCUMENTATION:")
                print(json.dumps(action, indent=2))
                print(f"{'='*60}\n")
            else:
                print(f">>> Tool call: {action['name']}({action.get('kwargs', {})})")
        else:
            # Fallback - shouldn't happen now that we run GENERATOR properly
            logger.error("White2 agent: No action determined, generating fallback documentation")
            action = {
                "name": "respond",
                "kwargs": {
                    "readme": f"# {state['project_name']}\n\n{state['project_description']}",
                    "metadata": {
                        "@context": "https://schema.org",
                        "@type": "SoftwareSourceCode",
                        "name": state["project_name"],
                        "description": state["project_description"],
                        "programmingLanguage": "Python"
                    }
                }
            }
            response_text = f"<json>{json.dumps(action)}</json>"

        state["messages"].append({"role": "assistant", "content": response_text})

        await event_queue.enqueue_event(
            new_agent_text_message(response_text, context_id=ctx_id)
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError


# ============================================================================
# Server Setup
# ============================================================================

def load_agent_card_toml(agent_name):
    current_dir = Path(__file__).parent
    with open(current_dir / f"{agent_name}.toml", "rb") as f:
        return tomllib.load(f)


def start_white_agent(agent_name="agent_card", host="localhost", port=9003, external_url=""):
    """Start the white2 agent server."""
    print("Starting white2 agent (LangGraph version)...")
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
        agent_executor=AEOWhiteAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )

    app = A2AStarletteApplication(
        agent_card=AgentCard(**agent_card_dict),
        http_handler=request_handler,
    )

    uvicorn.run(app.build(), host=host, port=port)
