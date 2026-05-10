# CONFTEST - Minimal version for testing
# This is a workaround for torch import issues on Windows
# Full imports are done inside tests that need them

import pytest
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

print(f"[DEBUG] Loading conftest.py...")

# Try importing ChromaVectorStore separately - this may fail due to torch
# If it fails, tests that need it will be skipped
CHROMA_AVAILABLE = False
try:
    from modules.vector.chroma_integration import ChromaVectorStore
    CHROMA_AVAILABLE = True
    print("[DEBUG] ChromaVectorStore imported successfully")
except Exception as e:
    print(f"[DEBUG] ChromaVectorStore import failed: {type(e).__name__}: {e}")
    ChromaVectorStore = None

# Try importing AgentZero - these are likely to fail too
AGENT_AVAILABLE = False
try:
    from agent_zero.core.agent_with_monitoring import MonitoredAgentZero
    from agent_zero.nanobot.monitored_nanobot import MonitoredNanoBotCoordinator
    AGENT_AVAILABLE = True
    print("[DEBUG] AgentZero modules imported successfully")
except Exception as e:
    print(f"[DEBUG] AgentZero import failed: {type(e).__name__}: {e}")
    MonitoredAgentZero = None
    MonitoredNanoBotCoordinator = None

print(f"[DEBUG] AGENT_AVAILABLE: {AGENT_AVAILABLE}, CHROMA_AVAILABLE: {CHROMA_AVAILABLE}")

@pytest.fixture
def test_config():
    """Test configuration dictionaries."""
    return {
        "api_key": "test_key",
        "model": "gpt-4o",
        "enable_self_repair": True,
        "enable_diagnosis": True,
        "persist_dir": "./data/test_chroma_pytest",
        "workspace_path": "./data/workspace_test"
    }

@pytest.fixture
async def monitored_agent(test_config):
    """Create a monitored agent instance for testing."""
    if not AGENT_AVAILABLE:
        pytest.skip("Agent dependencies not available")
    
    from agent_zero.hybrid.context import AgentConfig
    from orchestration.planner.orchestrator import OrchestratorConfig
    
    agent_cfg = AgentConfig(name="TestAgent", workspace_path=test_config["workspace_path"])
    llm_cfg = OrchestratorConfig(primary_model="openai")
    
    agent = MonitoredAgentZero(agent_cfg, llm_cfg)
    yield agent
    # Cleanup
    if hasattr(agent, "stop"):
        await agent.stop()

@pytest.fixture
async def chroma_store(test_config):
    """Create a local ChromaDB store for testing."""
    if not CHROMA_AVAILABLE:
        pytest.skip("Chroma dependencies not available")
    
    store = ChromaVectorStore(persist_dir=test_config["persist_dir"])
    yield store
    # Cleanup: remove test data
    import shutil
    if os.path.exists(test_config["persist_dir"]):
        shutil.rmtree(test_config["persist_dir"])

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    if sys.platform == "win32":
        loop = asyncio.WindowsSelectorEventLoopPolicy().new_event_loop()
    else:
        loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def task_store():
    """Create a TaskStore with a temporary database."""
    import tempfile
    from pathlib import Path
    from runtime.task_store import TaskStore
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "tasks.db"
        store = TaskStore(str(db_path))
        await store.init()
        yield store
