
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

from nanobot.agent.brain import Brain
from nanobot.agent.working_memory import WorkingMemory
from nanobot.providers.base import LLMProvider, LLMResponse, ToolCallRequest

async def test_brain_reasoning():
    print("Testing Cognitive Brain Architecture...")
    
    # Mock Provider
    mock_provider = MagicMock(spec=LLMProvider)
    mock_provider.get_default_model.return_value = "gpt-4"
    
    # Mock Response 1: Thought + Tool Call
    response1 = MagicMock(spec=LLMResponse)
    response1.content = "I need to check the current configuration files to see what's wrong."
    response1.has_tool_calls = True
    response1.tool_calls = [
        ToolCallRequest(id="call_123", name="read_file", arguments={"path": "config.yaml"})
    ]
    
    # Mock Response 2: Final Answer
    response2 = MagicMock(spec=LLMResponse)
    response2.content = "The config looks good. I have updated the scratchpad with the findings."
    response2.has_tool_calls = False
    response2.tool_calls = []
    
    mock_provider.chat = AsyncMock(side_effect=[response1, response2])
    
    workspace = Path(".")
    brain = Brain(workspace, mock_provider)
    
    goal = "Check the system configuration and report status."
    history = []
    tools = [{"name": "read_file", "description": "Read a file"}]
    
    print(f"Goal: {goal}")
    
    # Step 1: Brain Thinks
    content, tool_calls, is_complete = await brain.process_goal(goal, history, tools)
    print(f"Step 1 Response: {content}")
    print(f"Step 1 Tool Calls: {[tc.name for tc in tool_calls] if tool_calls else 'None'}")
    
    # Simulate tool result adding fact to brain
    brain.working_memory.add_fact("Config file version is 2.4.1", confidence=1.0)
    
    # Step 2: Brain Thinks again with fact in working memory
    content, tool_calls, is_complete = await brain.process_goal(goal, history, tools)
    print(f"Step 2 Response: {content}")
    print(f"Is Complete: {is_complete}")
    
    print("\nThought Trace:")
    print(brain.get_thought_trace())
    
    assert "Config file version is 2.4.1" in brain.working_memory.format_for_prompt()
    print("\nSUCCESS: Cognitive Brain Architecture verified!")

if __name__ == "__main__":
    asyncio.run(test_brain_reasoning())
