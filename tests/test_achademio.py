import sys
import os
import unittest
from pathlib import Path

# Add project root to sys.path
import importlib.util

# Import wrapper directly to avoid triggering agent_zero package init
wrapper_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'agent_zero', 'skills', 'achademio', 'wrapper.py'))
spec = importlib.util.spec_from_file_location("achademio_wrapper", wrapper_path)
ach_module = importlib.util.module_from_spec(spec)
sys.modules["achademio_wrapper"] = ach_module
spec.loader.exec_module(ach_module)

get_achademio = ach_module.get_achademio

class TestAchademio(unittest.TestCase):
    
    def test_import(self):
        """Verify skill can be imported and initialized."""
        print("Testing Achademio Import...")
        skill = get_achademio()
        self.assertIsNotNone(skill)
        print("[SUCCESS] Import successful")

    def test_logic_paths(self):
        """Verify the skill has the required methods."""
        skill = get_achademio()
        self.assertTrue(hasattr(skill, 'rewrite_academic'))
        self.assertTrue(hasattr(skill, 'bullets_to_paragraph'))
        self.assertTrue(hasattr(skill, 'text_to_slides'))
        self.assertTrue(hasattr(skill, 'proofread'))
        print("[SUCCESS] Method signatures verified")

if __name__ == "__main__":
    unittest.main()
