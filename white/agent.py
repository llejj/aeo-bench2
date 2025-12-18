"""White agent implementation - documentation generator for AEO evaluation."""

import uvicorn
import tomllib
import dotenv
import logging
from pathlib import Path

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard
from a2a.utils import new_agent_text_message
from litellm import completion

# Set up file logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/white_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('white_agent')

dotenv.load_dotenv()


SYSTEM_PROMPT = """You are a documentation generation agent. Your task is to explore code repositories and generate high-quality documentation.

You will be given tools to explore the repository:
- list_directory: List files and directories at a path
- read_file: Read the contents of a file  
- get_project_info: Get project metadata

IMPORTANT: You must respond with JSON wrapped in <json>...</json> tags.

To use a tool:
<json>
{"name": "<tool_name>", "kwargs": {"param": "value"}}
</json>

When you're ready to submit your final documentation, use the "respond" action:
<json>
{"name": "respond", "kwargs": {
    "readme": "Your comprehensive README in markdown format",
    "metadata": {
        "@context": "https://schema.org",
        "@type": "SoftwareSourceCode",
        "name": "Project name",
        "description": "Project description",
        "programmingLanguage": "Python"
    }
}}
</json>

Your README should include:
- Clear title and description
- Features list
- Installation/prerequisites
- Usage examples with code blocks
- API reference if applicable

Generate comprehensive, well-structured documentation that helps users understand and use the project.
Always explore the repository first by listing directories and reading files before generating documentation."""


class AEOWhiteAgentExecutor(AgentExecutor):
    """White agent executor that generates documentation using file exploration tools."""
    
    def __init__(self):
        self.ctx_id_to_messages = {}

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        user_input = context.get_user_input()
        logger.info(f"White agent: Received message:\n{user_input[:500]}...\n---END MESSAGE---")
        
        # Initialize or get conversation history for this context
        if context.context_id not in self.ctx_id_to_messages:
            self.ctx_id_to_messages[context.context_id] = [
                {"role": "system", "content": SYSTEM_PROMPT}
            ]
        
        messages = self.ctx_id_to_messages[context.context_id]
        messages.append({"role": "user", "content": user_input})
        
        # Call LLM
        logger.info(f"White agent: Calling LLM with {len(messages)} messages")
        response = completion(
            messages=messages,
            model="openai/gpt-4o-mini",
            custom_llm_provider="openai",
            temperature=0.3,
        )
        
        assistant_message = response.choices[0].message.content
        logger.info(f"White agent: LLM response:\n{assistant_message[:500]}...")
        
        # Add to history
        messages.append({"role": "assistant", "content": assistant_message})
        
        # Send response
        await event_queue.enqueue_event(
            new_agent_text_message(assistant_message, context_id=context.context_id)
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError


def load_agent_card_toml(agent_name):
    current_dir = Path(__file__).parent
    with open(current_dir / f"{agent_name}.toml", "rb") as f:
        return tomllib.load(f)


def start_white_agent(agent_name="agent_card", host="localhost", port=9002, external_url=""):
    print("Starting white agent...")
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

