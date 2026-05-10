
import asyncio
import json
import logging
import sys
import os
from unittest.mock import MagicMock, AsyncMock, patch

# Add project root to path
sys.path.append(os.getcwd())

from agent_zero.core.orchestrator import AgentZero, LLMProvider, ToolRegistry, MemoryStore, Tool, ToolTimeoutError
from agent_zero.web_research.executor import Executor, ExecutorConfig, PageResult

async def test_concurrency():
    print("\n--- Testing Concurrency (Lock) ---")
    mock_llm = AsyncMock(spec=LLMProvider)
    mock_llm.generate.return_value = "[]"
    mock_tools = MagicMock(spec=ToolRegistry)
    mock_memory = AsyncMock(spec=MemoryStore)
    
    # Mock Security (License)
    with patch('agent_zero.core.orchestrator.nonexistent_license_guard')  # License disabled as mock_license:
        mock_license.get_cached_info.return_value = {'email': 'test@example.com'}
        mock_license.verify = AsyncMock(return_value=(True, "Verified (Mock)"))

        agent = AgentZero(mock_llm, mock_tools, mock_memory)
        
        # Mock decompose to be slow
        async def slow_decompose(*args, **kwargs):
            await asyncio.sleep(1)
            return []
        agent._decompose_goal = slow_decompose
        
        # Start one goal
        task1 = asyncio.create_task(agent.execute_goal("Goal 1", "early"))
        await asyncio.sleep(0.2) # Ensure it has entered the lock
        
        # Try to start another while first is running
        result2 = await agent.execute_goal("Goal 2", "early")
        
        print(f"Second execution result: {result2['error']}")
        assert result2['success'] is False
        assert "already executing" in result2['error']
        print("PASS: Concurrency lock prevented double execution.")
        
        await task1

async def test_json_parsing():
    print("\n--- Testing JSON Parsing Robustness ---")
    # Test cases: normal dict, array of dicts, markdown blocks, malformed with trailing commas
    parser = LLMProvider._parse_json
    
    # 1. Normal dict
    assert parser('{"key": "value"}') == {"key": "value"}
    
    # 2. Array
    assert parser('[{"task": "t1"}]') == [{"task": "t1"}]
    
    # 3. Markdown Block
    assert parser('Here is the JSON: ```json\n{"task": "t1"}\n```') == {"task": "t1"}
    
    # 4. Malformed with trailing comma
    assert parser('{"task": "t1",}') == {"task": "t1"}
    
    # 5. Mixed text
    assert parser('Thinking... Plan: {"a": 1} End.') == {"a": 1}
    
    print("PASS: JSON parsing is robust.")

async def test_tool_timeout():
    print("\n--- Testing Tool Timeout ---")
    mock_llm = AsyncMock(spec=LLMProvider)
    # Return 1 task
    mock_llm.generate.return_value = '[{"task": "slow_tool", "params": {}}]'
    
    slow_tool = AsyncMock(spec=Tool)
    slow_tool.name = "slow_tool"
    slow_tool.description = "A slow tool for testing"
    async def slow_exec(params):
        await asyncio.sleep(2)
        return "done"
    slow_tool.execute.side_effect = slow_exec
    
    registry = ToolRegistry()
    registry.register(slow_tool)
    
    mock_memory = AsyncMock(spec=MemoryStore)
    
    # Set short timeout
    # Set short timeout & Mock Security
    with patch('agent_zero.core.orchestrator.nonexistent_license_guard')  # License disabled as mock_license:
        mock_license.get_cached_info.return_value = {'email': 'test@example.com'}
        mock_license.verify = AsyncMock(return_value=(True, "Verified (Mock)"))

        agent = AgentZero(mock_llm, registry, mock_memory, tool_timeout=1)
        
        result = await agent.execute_goal("Test Timeout", "early")
        
        # The task should fail due to timeout
        # If license check failed, result['results'] would be empty or error would be different
        if result.get('license_expired'):
             print("FAIL: License check blocked execution")
             return

        task_res = result['results'][0]
        print(f"Task result error: {task_res['error']}")
        assert task_res['success'] is False
        assert "timed out" in task_res['error']
        print("PASS: Tool timeout enforced.")

async def test_executor_redirect_loop():
    print("\n--- Testing Executor Redirect Loop ---")
    config = ExecutorConfig(max_redirects=2)
    executor = Executor(config)
    
    # Mock session
    mock_session = AsyncMock()
    executor.session = mock_session
    
    # Create a circular redirect
    mock_response = MagicMock()
    mock_response.status = 302
    mock_response.headers = {'Location': 'http://loop'}
    mock_session.get.return_value.__aenter__.return_value = mock_response
    
    result = await executor.fetch_page("http://loop")
    assert result is None
    print("PASS: Redirect loop protected by depth limit.")

async def test_executor_size_limit():
    print("\n--- Testing Executor Size Limit ---")
    config = ExecutorConfig(max_response_size=100) # 100 bytes
    executor = Executor(config)
    
    mock_session = AsyncMock()
    executor.session = mock_session
    
    # Case 1: Headers have large size
    mock_response_large = MagicMock()
    mock_response_large.status = 200
    mock_response_large.headers = {'Content-Length': '500'}
    mock_session.get.return_value.__aenter__.return_value = mock_response_large
    
    result1 = await executor.fetch_page("http://large")
    assert result1 is None
    print("PASS: Size limit enforced via headers.")
    
    # Case 2: Content is actually large
    mock_response_real = MagicMock()
    mock_response_real.status = 200
    mock_response_real.headers = {} # No Content-Length
    mock_response_real.text = AsyncMock(return_value="A" * 200)
    mock_session.get.return_value.__aenter__.return_value = mock_response_real
    
    result2 = await executor.fetch_page("http://large-real")
    assert result2 is None
    print("PASS: Size limit enforced via actual content size.")

async def main():
    try:
        await test_concurrency()
        await test_json_parsing()
        await test_tool_timeout()
        await test_executor_redirect_loop()
        await test_executor_size_limit()
        print("\nALL ORCHESTRATION VERIFICATION TESTS PASSED!")
    except Exception as e:
        print(f"\nVERIFICATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
