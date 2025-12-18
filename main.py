"""CLI entry point for AEO-Bench."""

import typer
import asyncio
import httpx
import json
import uuid
import multiprocessing

from green import start_green_agent
from white import start_white_agent as start_white_agent_v1
from white2 import start_white_agent as start_white_agent_v2

app = typer.Typer(help="AEO-Bench - Answer Engine Optimization benchmark for documentation generation")


@app.command()
def green():
    """Start the green agent (evaluation manager)."""
    start_green_agent()


@app.command()
def white():
    """Start the white agent v1 (baseline - simple LLM wrapper)."""
    start_white_agent_v1()


@app.command()
def white2():
    """Start the white agent v2 (LangGraph with Planner/Explorer/Generator nodes)."""
    start_white_agent_v2()


@app.command()
def launch(version: str = typer.Option("v2", help="Agent version: v1 (baseline) or v2 (LangGraph)")):
    """Launch the complete evaluation workflow locally."""
    asyncio.run(launch_evaluation(version=version))


@app.command()
def validate():
    """Run rubric validation with hardcoded test cases.

    This validates that the 4-tier scoring rubric produces expected results
    on predefined documentation examples (perfect, partial, minimal).
    Used for Q8.5 validation in the submission.
    """
    from green.agent import validate_rubric
    results = validate_rubric(verbose=True)
    if results["failed"] > 0:
        print(f"\nValidation FAILED: {results['failed']} test case(s) did not pass")
        raise typer.Exit(code=1)
    print(f"\nValidation PASSED: All {results['passed']} test case(s) within expected ranges")


async def launch_evaluation(version: str = "v2"):
    """Launch both agents and run evaluation."""
    # Select white agent version
    if version == "v1":
        white_agent_fn = start_white_agent_v1
        white_agent_name = "white agent v1 (baseline)"
    else:
        white_agent_fn = start_white_agent_v2
        white_agent_name = "white agent v2 (LangGraph)"

    # Start green agent
    print("Launching green agent...")
    green_address = ("localhost", 9001)
    green_url = f"http://{green_address[0]}:{green_address[1]}"
    p_green = multiprocessing.Process(
        target=start_green_agent, args=("agent_card", *green_address)
    )
    p_green.start()

    # Wait for green agent to be ready
    await wait_agent_ready(green_url)
    print("Green agent is ready.")

    # Start white agent
    print(f"Launching {white_agent_name}...")
    white_address = ("localhost", 9002)
    white_url = f"http://{white_address[0]}:{white_address[1]}"
    p_white = multiprocessing.Process(
        target=white_agent_fn, args=("agent_card", *white_address)
    )
    p_white.start()
    
    await wait_agent_ready(white_url)
    print("White agent is ready.")

    # Send the task description to green agent
    print("Sending task to green agent...")
    test_config = {
        "test_ids": [0, 1, 2]  # Run first 3 test cases
    }
    task_text = f"""
Your task is to evaluate the agent located at:
<white_agent_url>
{white_url}
</white_agent_url>
You should use the following test configuration:
<test_config>
{json.dumps(test_config, indent=2)}
</test_config>
    """
    
    print("Task description:")
    print(task_text)
    print("Sending...")
    
    response = await send_message(green_url, task_text)
    print("Response from green agent:")
    print(response)

    print("Evaluation complete. Terminating agents...")
    p_green.terminate()
    p_green.join()
    p_white.terminate()
    p_white.join()
    print("Agents terminated.")


async def wait_agent_ready(url, timeout=30):
    """Wait until an A2A agent is ready."""
    for i in range(timeout):
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{url}/.well-known/agent.json")
                if response.status_code == 200:
                    return True
        except Exception as e:
            print(f"  Health check error: {type(e).__name__}: {e}")
        print(f"Waiting for agent at {url}... ({i+1}/{timeout})")
        await asyncio.sleep(1)
    
    raise TimeoutError(f"Agent at {url} not ready after {timeout}s")


async def send_message(url, message):
    """Send a message to an A2A agent."""
    from a2a.client import A2ACardResolver, A2AClient
    from a2a.types import Part, TextPart, MessageSendParams, Message, Role, SendMessageRequest

    async with httpx.AsyncClient(timeout=300.0) as httpx_client:
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=url)
        card = await resolver.get_agent_card()
        
        client = A2AClient(httpx_client=httpx_client, agent_card=card)
        
        params = MessageSendParams(
            message=Message(
                role=Role.user,
                parts=[Part(TextPart(text=message))],
                message_id=uuid.uuid4().hex,
            )
        )
        req = SendMessageRequest(id=uuid.uuid4().hex, params=params)
        response = await client.send_message(request=req)
        
        return response


if __name__ == "__main__":
    app()
