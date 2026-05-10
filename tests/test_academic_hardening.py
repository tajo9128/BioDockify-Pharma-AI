import unittest
import os
import threading
from unittest.mock import MagicMock, patch
from modules.scientific_method.hypothesis_engine import get_hypothesis_engine
from modules.literature.synthesis import get_synthesizer
from modules.compliance.academic_compliance import get_compliance_engine, ComplianceReport
from modules.thesis.engine import get_thesis_engine
from modules.thesis.structure import PharmaBranch, DegreeType
from export.docx_academic import AcademicDOCXExporter

class TestAcademicHardening(unittest.TestCase):
    
    def test_hypothesis_singleton_thread_safety(self):
        """Verify HypothesisEngine singleton is thread-safe."""
        engines = []
        def get_engine():
            engines.append(get_hypothesis_engine())
            
        threads = [threading.Thread(target=get_engine) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()
        
        self.assertTrue(all(e is engines[0] for e in engines))
        self.assertIsNotNone(engines[0])

    def test_synthesizer_singleton_thread_safety(self):
        """Verify ReviewSynthesizer singleton is thread-safe."""
        engines = []
        def get_engine():
            engines.append(get_synthesizer())
            
        threads = [threading.Thread(target=get_engine) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()
        
        self.assertTrue(all(e is engines[0] for e in engines))

    def test_compliance_regex_fix(self):
        """Verify compliance engine correctly identifies fixed regex patterns (Bug #2)."""
        engine = get_compliance_engine()
        text = "In conclusion, this result is a game-changer."
        report = engine.analyze_text(text)
        
        # Should have found two issues: "In conclusion," and "game-changer"
        issue_found = any("Collectively, these findings suggest" in str(issue) for issue in report.issues)
        self.assertTrue(issue_found, "Failed to suggest replacement for 'In conclusion,'")
        
        game_changer_found = any("significant advancement" in str(issue) for issue in report.issues)
        self.assertTrue(game_changer_found, "Failed to suggest replacement for 'game-changer'")

    def test_compliance_return_type(self):
        """Verify compliance engine returns the correct standardized type (Bug #10)."""
        engine = get_compliance_engine()
        report = engine.analyze_text("Some text.")
        self.assertIsInstance(report, ComplianceReport)
        self.assertIsInstance(report.issues, list)

    def test_thesis_input_validation(self):
        """Verify thesis engine validates inputs (Bug #8)."""
        engine = get_thesis_engine()
        
        # Test empty topic
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(engine.generate_chapter("INTRO", ""))
        self.assertEqual(result["status"], "error")
        self.assertIn("topic is required", result["message"])
        
        # Test invalid branch types
        result = loop.run_until_complete(engine.generate_chapter("INTRO", "Topic", branch="INVALID"))
        self.assertEqual(result["status"], "error")
        self.assertIn("Invalid pharma branch", result["message"])

    def test_docx_atomic_save(self):
        """Verify DOCX exporter uses atomic save via temp file (Bug #16)."""
        try:
            exporter = AcademicDOCXExporter(template='ieee')
            output_path = "test_atomic_save.docx"
            
            # Mocking rename to ensure it's called
            with patch('os.rename') as mock_rename:
                with patch('os.remove'): # Mock remove in case file exists
                    exporter.export(output_path)
                    self.assertTrue(mock_rename.called)
                    # Verify it renamed a .docx temp file to the target path
                    tmp_arg = mock_rename.call_args[0][0]
                    target_arg = mock_rename.call_args[0][1]
                    self.assertTrue(tmp_arg.endswith('.docx'))
                    self.assertEqual(target_arg, output_path)
            
            # Cleanup
            if os.path.exists(output_path):
                os.remove(output_path)
        except ImportError:
            self.skipTest("python-docx not installed, skipping atomic save test.")

if __name__ == "__main__":
    unittest.main()
