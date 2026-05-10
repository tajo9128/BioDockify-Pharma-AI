
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio

# Adjust python path if needed, but pytest usually handles it if run from root
from orchestration.executor import ResearchExecutor
from orchestration.planner.orchestrator import ResearchPlan, ResearchStep

@pytest.mark.asyncio
async def test_executor_async_flow():
    """
    Verify ResearchExecutor executes steps asynchronously and updates TaskStore.
    """
    # Mock TaskStore globally for this test
    mock_store = AsyncMock()
    
    with patch("runtime.task_store.get_task_store", return_value=mock_store):
        # 1. Create a dummy plan
        step1 = ResearchStep(
            step_id=1, 
            title="Literature Search Test", 
            description="Testing async execution", 
            category="literature_search",
            dependencies=[],
            estimated_time_minutes=5
        )
        
        plan = ResearchPlan(
            research_title="Async Test Protocol",
            objectives=["Verify Async"],
            steps=[step1],
            total_estimated_time_minutes=5
        )
        
        # 2. Initialize Executor
        executor = ResearchExecutor(task_id="task_test_async_001")
        
        # 3. Mock the actual work handler to avoid real side effects (file system, network)
        # We want to test the flow control and TaskStore interaction
        executor._handle_literature_search = AsyncMock()
        
        # 4. Execute Plan
        context = await executor.execute_plan(plan)
        
        # 5. Verifications
        
        # Start log
        mock_store.append_log.assert_any_call("task_test_async_001", "[INFO] Starting research on: Async Test Protocol")
        
        # Handler called?
        assert executor._handle_literature_search.called
        
        # Checkpointing?
        # Expect update_task call with progress
        assert mock_store.update_task.called
        
        # Check final update
        args, kwargs = mock_store.update_task.call_args_list[-1]
        # Depending on implementation, it might be update_task(task_id, result=...) or similar
        # We just check it was called for now
        assert args[0] == "task_test_async_001"
        
        print("\n[Passed] Async Executor Flow Verified")
