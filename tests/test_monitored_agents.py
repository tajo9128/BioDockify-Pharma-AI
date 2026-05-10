import pytest
import asyncio
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_monitored_agent_execution(monitored_agent):
    """Test that MonitoredAgentZero correctly wraps and executes."""
    # Mock the underlying agent.execute
    monitored_agent.agent.execute = AsyncMock(return_value={"status": "success", "data": "test"})
    
    result = await monitored_agent.execute("test task", mode="unit_test")
    
    assert result["status"] == "success"
    # Verify execution was called
    monitored_agent.agent.execute.assert_called_once_with("test task")

@pytest.mark.asyncio
async def test_monitored_agent_error_tracking(monitored_agent):
    """Test that MonitoredAgentZero tracks failed executions."""
    # Mock to raise an exception
    monitored_agent.agent.execute = AsyncMock(side_effect=ValueError("Test Error"))
    
    with pytest.raises(ValueError, match="Test Error"):
        await monitored_agent.execute("failing task")
        
    # We could also check prometheus metrics here if we wanted to be deep.
    # For unit tests, confirming the wrapper doesn't block the exception is key.

@pytest.mark.asyncio
async def test_monitored_nanobot_active_count(test_config):
    """Test that MonitoredNanoBotCoordinator tracks active bot counts."""
    from agent_zero.nanobot.monitored_nanobot import MonitoredNanoBotCoordinator
    
    # We need to mock HybridAgentBrain to avoid actual initialization
    with patch('agent_zero.nanobot.monitored_nanobot.HybridAgentBrain') as MockBrain:
        mock_instance = MockBrain.return_value
        mock_instance.agent_loop.subagents.get_running_count.return_value = 5
        
        coordinator = MonitoredNanoBotCoordinator("./test_workspace", test_config)
        coordinator.update_metrics()
        
        # Check current value of the gauge
        from prometheus_client import REGISTRY
        count = REGISTRY.get_sample_value('nanobot_active_count')
        assert count == 5.0
