"""
Verification script for Full Agent Zero Port.
Tests PhDStage detection, Persistent Memory, and enhanced Reasoning.
"""

import asyncio
import json
from pathlib import Path
from unittest.mock import MagicMock
from nanobot.agent.brain import Brain
from nanobot.agent.planner import PhDPlanner
from nanobot.providers.base import LLMProvider, LLMResponse, ToolCallRequest

async def test_full_port():
    print("Testing Full Agent Zero Port...")
    workspace = Path("./test_workspace_full")
    workspace.mkdir(exist_ok=True)
    
    # Mock Provider
    provider = MagicMock(spec=LLMProvider)
    provider.get_default_model.return_value = "gpt-4"
    
    # 1. Test PhD Planner Detection
    planner = PhDPlanner()
    metadata = {"milestones": {"literature_review_complete": True, "experiments_started": True}}
    stage = planner.detect_phd_stage(metadata)
    print(f"Detected Stage: {stage} (Expected: mid)")
    assert stage == "mid"
    
    # 2. Test Persistent Memory
    brain = Brain(workspace, provider)
    await brain.store_result(
        task={"task": "search", "params": {"q": "Alzheimer target"}},
        result="BACE1 is a key target.",
        goal="Find Alzheimer targets"
    )
    
    # Wait for write
    memories = brain.memory.long_term
    print(f"Stored Memories: {len(memories)}")
    assert len(memories) > 0
    assert memories[0]["goal"] == "Find Alzheimer targets"
    
    # 3. Test Reasoning with Stage Context
    # Mock response with manual tool call to test robust parsing
    mock_resp = LLMResponse(
        content="I should search for ligand info.\n```json\n{\"tool\": \"web_search\", \"params\": {\"query\": \"BACE1 ligands\"}}\n```",
        tool_calls=[] # Purposefully empty to trigger manual parsing
    )
    # Correcting the mock to return a coroutine
    async def mock_chat(*args, **kwargs):
        return mock_resp
    provider.chat = mock_chat
    
    content, tool_calls, is_complete = await brain.process_goal(
        goal="Deep dive into BACE1",
        history=[],
        tools=[{"name": "web_search", "description": "search web"}],
        project_metadata=metadata
    )
    
    print(f"Reasoning Content: {content[:50]}...")
    print(f"Detected Tool Calls: {[t.name for t in tool_calls]}")
    assert len(tool_calls) > 0
    assert tool_calls[0].name == "web_search"
    
    print("\nSUCCESS: Full Agent Zero Port verified!")

if __name__ == "__main__":
    asyncio.run(test_full_port())
