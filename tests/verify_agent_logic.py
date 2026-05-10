
import sys
import os
import unittest
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from orchestration.planner.orchestrator import ResearchOrchestrator, OrchestratorConfig

class TestAgentZeroLogic(unittest.TestCase):
    
    def setUp(self):
        # Mock Config
        self.config = OrchestratorConfig(use_cloud_api=False)
        # Inject Mock Persona
        self.config.user_persona = {
            "role": "PhD_Student",
            "primary_purpose": ["Thesis_Preparation"],
            "output_expectation": "Thesis_Ready",
            "strictness": "balanced",
            "research_horizon": "long_term"
        }
        
    def test_mode_enforcement_search(self):
        """Test that Search Mode is respected in the prompt/planning."""
        print("\nTesting SEARCH Mode Enforcement...")
        orchestrator = ResearchOrchestrator(self.config)
        
        # Mock the LLM generation to avoid actual API calls, 
        # but we really want to check the _build_prompt logic or the plan structure logic.
        # Since _build_prompt is internal, let's just inspect it directly or trust the planner if we can.
        # Actually, let's verify _build_prompt output contains the mode instruction.
        
        prompt = orchestrator._build_prompt("Test Topic", mode="search")
        self.assertIn("MODE: SEARCH", prompt)
        self.assertIn("Do not attempt synthesis", prompt)
        print("PASS: Search Mode instruction found in prompt.")

    def test_citation_lock_conservative(self):
        """Test that Conservative Strictness + Write Mode triggers Citation Lock."""
        print("\nTesting Citation Lock (Conservative + Write)...")
        
        # Set Strictness to Conservative
        self.config.user_persona["strictness"] = "conservative"
        orchestrator = ResearchOrchestrator(self.config)
        
        # Mock the generation to return a generic plan WITHOUT verification
        orchestrator._generate_plan_local = MagicMock(return_value={
            "objectives": ["Write Chapter 1"],
            "steps": [
                {
                    "step_id": 1,
                    "title": "Draft Introduction",
                    "description": "Write the intro.",
                    "category": "final_report", # Not literature_search
                    "dependencies": [],
                    "estimated_time_minutes": 60
                }
            ],
            "total_estimated_time": 60
        })
        
        plan = orchestrator.plan_research("Test Topic", mode="write")
        
        # Check if the FIRST step is now the injected verification step
        first_step = plan.steps[0]
        self.assertEqual(first_step.title, "Mandatory Evidence Verification")
        self.assertEqual(first_step.step_id, 0)
        self.assertIn("literature", first_step.category)
        print("PASS: Citation Lock injected verification step.")

    def test_citation_lock_balanced_bypass(self):
        """Test that Balanced Strictness behaves normally (no injection)."""
        print("\nTesting Citation Lock Bypass (Balanced)...")
        
        self.config.user_persona["strictness"] = "balanced"
        orchestrator = ResearchOrchestrator(self.config)
        
        orchestrator._generate_plan_local = MagicMock(return_value={
            "objectives": ["Write Chapter 1"],
            "steps": [
                {
                    "step_id": 1,
                    "title": "Draft Introduction",
                    "description": "Write the intro.",
                    "category": "final_report",
                    "dependencies": [],
                    "estimated_time_minutes": 60
                }
            ],
            "total_estimated_time": 60
        })
        
        plan = orchestrator.plan_research("Test Topic", mode="write")
        
        first_step = plan.steps[0]
        self.assertNotEqual(first_step.title, "Mandatory Evidence Verification")
        print("PASS: Citation Lock respected Balanced mode (no injection).")

if __name__ == '__main__':
    unittest.main()
