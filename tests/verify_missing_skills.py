
import sys
import os
import asyncio
import json
from unittest.mock import MagicMock, patch

# Setup paths
sys.path.append(os.path.join(os.getcwd()))

from agent_zero.hybrid.agent import HybridAgent, AgentConfig, OrchestratorConfig

# Mock imports
sys.modules["litellm"] = MagicMock()

async def test_missing_skills():
    print("[-] Testing Missing Skills Integration...")
    
    # Setup dummy config
    config = AgentConfig(name="TestAgent", workspace_path=".")
    llm_config = OrchestratorConfig(primary_model="test")
    
    # Mock LLM and dependencies
    with patch("agent_zero.hybrid.agent.LLMFactory") as mock_factory, \
         patch("agent_zero.hybrid.agent.MessageBus"), \
         patch("agent_zero.hybrid.agent.CronService"), \
         patch("agent_zero.skills.deep_drive.wrapper.DeepDriveSkill") as mock_deep, \
         patch("agent_zero.skills.scholar_copilot.wrapper.ScholarCopilotSkill") as mock_scholar, \
         patch("agent_zero.hybrid.agent.get_browser_scraper"):
        
        # Setup mocks
        mock_factory.get_adapter.return_value.generate = AsyncMock(return_value="Summary content")
        
        # Mock Deep Drive
        mock_deep_inst = mock_deep.return_value
        mock_deep_inst.analyze_authorship.return_value = {"status": "Analysis Complete"}
        
        # Mock Scholar
        mock_scholar_inst = mock_scholar.return_value
        mock_scholar_inst.complete_text.return_value = "Completed text"

        # Initialize Agent
        agent = HybridAgent(config, llm_config)
        agent.llm_adapter.generate = AsyncMock(return_value="Summary content")
        
        print("[+] HybridAgent Initialized.")
        
        # 1. Test deep_drive_analyze
        print("[1] Testing deep_drive_analyze...")
        call = json.dumps({"tool": "deep_drive_analyze", "params": {"text": "test text"}})
        res = await agent._execute_tool(call)
        if "Analysis Complete" in str(res):
            print("[+] deep_drive_analyze passed.")
        else:
            print(f"[!] deep_drive_analyze failed: {res}")
            
        # 2. Test scholar_complete
        print("[2] Testing scholar_complete...")
        call = json.dumps({"tool": "scholar_complete", "params": {"text": "Start sentence"}})
        res = await agent._execute_tool(call)
        if "Completed text" in str(res):
             print("[+] scholar_complete passed.")
        else:
             print(f"[!] scholar_complete failed: {res}")

        # 3. Test summarize_content
        print("[3] Testing summarize_content...")
        call = json.dumps({"tool": "summarize_content", "params": {"text": "Long text..."}})
        res = await agent._execute_tool(call)
        if "Summary content" in str(res):
             print("[+] summarize_content passed.")
        else:
             print(f"[!] summarize_content failed: {res}")

class AsyncMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(test_missing_skills())
