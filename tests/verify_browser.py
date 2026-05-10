
import sys
import os
import asyncio
from unittest.mock import MagicMock, patch

# Setup paths
sys.path.append(os.path.join(os.getcwd()))

from agent_zero.hybrid.agent import HybridAgent, AgentConfig, OrchestratorConfig
from modules.headless_research.engine import HeadlessResearcher

# Mock imports that might fail or be heavy
sys.modules["litellm"] = MagicMock()

async def test_browser_tools():
    print("[-] Testing Browser Tool Integration...")
    
    # Setup dummy config
    config = AgentConfig(name="TestAgent", workspace_path=".")
    llm_config = OrchestratorConfig(primary_model="test")
    
    # Mock LLM and dependencies
    with patch("agent_zero.hybrid.agent.LLMFactory") as mock_factory, \
         patch("agent_zero.hybrid.agent.MessageBus"), \
         patch("agent_zero.hybrid.agent.CronService"), \
         patch("agent_zero.hybrid.agent.stealth_deep_research", new_callable=MagicMock) as mock_stealth, \
         patch("agent_zero.hybrid.agent.get_browser_scraper") as mock_get_scraper:
        
        # Setup mocks
        mock_factory.get_adapter.return_value = MagicMock()
        
        # Mock Stealth Result
        async def async_stealth(*args):
             return {"status": "success", "title": "Stealth Title", "content": "Stealth Content"}
        mock_stealth.side_effect = async_stealth
        
        # Mock Scraper Result
        mock_scraper_instance = MagicMock()
        async def async_scrape(*args):
             return {"success": True, "title": "General Title", "content": "General Content"}
        mock_scraper_instance.scrape_page.side_effect = async_scrape
        
        async def async_pdf(*args):
             return "path/to/detected.pdf"
        mock_scraper_instance.download_pdf.side_effect = async_pdf
        
        mock_get_scraper.return_value = mock_scraper_instance

        # Initialize Agent
        agent = HybridAgent(config, llm_config)
        print("[+] HybridAgent Initialized.")
        
        import json
        
        # 1. Test browse_stealth
        print("[1] Testing browse_stealth...")
        call = json.dumps({"tool": "browse_stealth", "params": {"url": "http://stealth.com"}})
        res = await agent._execute_tool(call)
        if "Stealth Title" in res:
            print("[+] browse_stealth passed.")
        else:
            print(f"[!] browse_stealth failed: {res}")
            
        # 2. Test browse_general
        print("[2] Testing browse_general...")
        call = json.dumps({"tool": "browse_general", "params": {"url": "http://general.com"}})
        res = await agent._execute_tool(call)
        if "General Title" in res:
             print("[+] browse_general passed.")
        else:
             print(f"[!] browse_general failed: {res}")

        # 3. Test browse_pdf
        print("[3] Testing browse_pdf...")
        call = json.dumps({"tool": "browse_pdf", "params": {"url": "http://pdf.com"}})
        res = await agent._execute_tool(call)
        if "path/to/detected.pdf" in res:
             print("[+] browse_pdf passed.")
        else:
             print(f"[!] browse_pdf failed: {res}")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(test_browser_tools())
