import sys
import os
import unittest
from pathlib import Path

# Add project root to sys.path
import importlib.util

# Import wrapper directly to avoid triggering agent_zero package init
wrapper_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'agent_zero', 'skills', 'scholar_copilot', 'wrapper.py'))
spec = importlib.util.spec_from_file_location("copilot_wrapper", wrapper_path)
cp_module = importlib.util.module_from_spec(spec)
sys.modules["copilot_wrapper"] = cp_module
spec.loader.exec_module(cp_module)

get_scholar_copilot = cp_module.get_scholar_copilot

class TestScholarCopilot(unittest.TestCase):
    
    def test_import(self):
        """Verify skill can be imported and initialized."""
        print("Testing ScholarCopilot Import...")
        skill = get_scholar_copilot()
        self.assertIsNotNone(skill)
        print("[SUCCESS] Import successful")

    def test_method_signatures(self):
        """Verify method signatures."""
        skill = get_scholar_copilot()
        self.assertTrue(hasattr(skill, 'load'))
        self.assertTrue(hasattr(skill, 'complete_text'))
        self.assertTrue(hasattr(skill, 'search_citations'))
        print("[SUCCESS] Method signatures verified")

if __name__ == "__main__":
    unittest.main()
