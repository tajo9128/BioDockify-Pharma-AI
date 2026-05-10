"""
Mocked Final Validation Script
Verifies LM Studio integration by mocking out broken ML dependencies.
"""
import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# MOCK BROKEN MODULES BEFORE IMPORTING ORCHESTRATOR
sys.modules["modules.compliance.academic_compliance"] = MagicMock()
sys.modules["modules.compliance.plagiarism"] = MagicMock()
sys.modules["modules.literature"] = MagicMock()
sys.modules["modules.literature.discovery"] = MagicMock()
sys.modules["modules.literature.semantic_scholar"] = MagicMock()
sys.modules["semanticscholar"] = MagicMock()
sys.modules["Bio"] = MagicMock()

# Now import the modules using these mocks
from modules.llm.adapters import LMStudioAdapter
from modules.llm.factory import LLMFactory
from orchestration.planner.orchestrator import ResearchOrchestrator, OrchestratorConfig

class TestFinalValidationMocked(unittest.TestCase):

    def test_01_lmstudio_connection(self):
        """Verify LM Studio Adapter connection and auto-detection."""
        print("\n[Test 1] LM Studio Connection & Auto-Detection")
        
        adapter = LMStudioAdapter(model="auto")
        
        # Mock the underlying requests
        with patch('modules.llm.adapters.requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": [{"id": "biomed-llama3-8b"}]
            }
            mock_get.return_value = mock_response
            
            detected = adapter._auto_select_model()
            print(f"   [OK] Detected Model: {detected}")
            self.assertEqual(detected, "biomed-llama3-8b")
            
    def test_02_llm_factory_lmstudio(self):
        """Verify LLM Factory produces LMStudioAdapter correctly."""
        print("\n[Test 2] LLM Factory Configuration")
        
        class MockConfig:
            lm_studio_url = "http://localhost:1234/v1"
            lm_studio_model = "auto"
            
        adapter = LLMFactory.get_adapter("lm_studio", MockConfig())
        self.assertIsInstance(adapter, LMStudioAdapter)
        self.assertEqual(adapter.config_model, "auto")
        print("   [OK] Factory returned LMStudioAdapter with auto mode")

    def test_03_orchestrator_e2e_mocked(self):
        """Simulate a full research task via Orchestrator (with mocked ML components)."""
        print("\n[Test 3] End-to-End Orchestrator (Fully Mocked)")
        
        # config
        # Fix: user_persona must be a dict matching the schema
        persona_data = {
            "role": "PhD_Student",
            "primary_purpose": ["Thesis_Preparation"],
            "output_expectation": "Thesis_Ready",
            "strictness": "balanced",
            "research_horizon": "long_term"
        }
        config = OrchestratorConfig(
            user_persona=persona_data,
            use_cloud_api=True,      # Forces "Hybrid Mode" in constructor logic
            primary_model="lm_studio"
        )
        
        
        # Instantiate Orchestrator
        orchestrator = ResearchOrchestrator(config)
        
        # Mock LLM generation
        mock_plan_json = json.dumps({
            "objectives": ["Identify mechanisms of action"],
            "steps": [
                {
                    "step_id": 1,
                    "title": "Literature Landscape",
                    "description": "Search for recent papers.",
                    "category": "literature_search",
                    "dependencies": [],
                    "estimated_time_minutes": 10
                }
            ],
            "total_estimated_time": 10
        })
        
        # Patch the Factory to return our Mock Adapter
        with patch('modules.llm.factory.LLMFactory.get_adapter') as mock_factory:
            mock_adapter = MagicMock()
            mock_adapter.generate.return_value = mock_plan_json
            mock_factory.return_value = mock_adapter
            
            # Run planning
            plan = orchestrator.plan_research("How does Aspirin work?", mode="search")
            
            print(f"   [OK] Plan Generated: {len(plan.steps)} steps")
            self.assertEqual(plan.steps[0].title, "Literature Landscape")
            
            # Verify the prompt contained the mode instruction
            call_args = mock_adapter.generate.call_args
            if call_args:
                prompt_sent = call_args[0][0]
                self.assertIn("SEARCH", prompt_sent)
                print("   [OK] Orchestrator successfully used adapter (mocked) with SEARCH mode")
            else:
                self.fail("Adapter generate method was not called!")

if __name__ == '__main__':
    unittest.main()
