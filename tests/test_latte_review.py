import sys
import os
import unittest
from pathlib import Path

# Add project root to sys.path
import importlib.util

# Add LatteReview to path
LATTE_DIR = Path(os.path.abspath(__file__)).parent.parent / "_external" / "LatteReview"
if str(LATTE_DIR) not in sys.path:
    sys.path.insert(0, str(LATTE_DIR))

# Import wrapper directly to avoid triggering agent_zero package init and its deep dependencies
wrapper_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'agent_zero', 'skills', 'latte_review', 'wrapper.py'))
spec = importlib.util.spec_from_file_location("latte_wrapper", wrapper_path)
latte_module = importlib.util.module_from_spec(spec)
sys.modules["latte_wrapper"] = latte_module
spec.loader.exec_module(latte_module)

get_latte_review = latte_module.get_latte_review

class TestLatteReview(unittest.TestCase):
    
    def test_import(self):
        """Verify skill can be imported and initialized."""
        print("Testing Import...")
        skill = get_latte_review()
        self.assertIsNotNone(skill)
        print("[SUCCESS] Import successful")

    def test_dependencies(self):
        """Verify internal dependencies."""
        print("Testing Dependencies...")
        try:
            import lattereview
            print("[SUCCESS] LatteReview module found")
        except ImportError:
            self.fail("LatteReview module could not be imported")

    def test_method_signatures(self):
        """Verify new method signatures exist."""
        skill = get_latte_review()
        self.assertTrue(hasattr(skill, 'screen_papers'))
        self.assertTrue(hasattr(skill, 'score_papers'))
        self.assertTrue(hasattr(skill, 'abstract_papers'))
        print("[SUCCESS] Method signatures verified")

if __name__ == "__main__":
    unittest.main()


