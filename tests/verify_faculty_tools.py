
import unittest
import os
import asyncio
from nanobot.agent.tools.faculty import GrantForgeTool, SyllabusArchitectTool, NoteGathererTool, SlideDeckBuilderTool

class TestFacultyTools(unittest.TestCase):
    def setUp(self):
        self.grant_tool = GrantForgeTool()
        self.syllabus_tool = SyllabusArchitectTool()
        self.note_tool = NoteGathererTool()
        self.slide_tool = SlideDeckBuilderTool()

    def test_grant_forge(self):
        result = asyncio.run(self.grant_tool.execute("Cancer Research", "NIH"))
        self.assertIn("# Grant Proposal Draft: Cancer Research", result)
        self.assertIn("Agency: NIH", result)

    def test_syllabus_architect(self):
        result = asyncio.run(self.syllabus_tool.execute("Advanced Pharma", "PhD", 10))
        self.assertIn("# Syllabus: Advanced Pharma", result)
        self.assertIn("Week 10:", result)

    def test_note_gatherer(self):
        result = asyncio.run(self.note_tool.execute("CRISPR"))
        self.assertIn("# Lecture Notes: CRISPR", result)

    def test_slide_deck_builder(self):
        output_path = "test_slides.pptx"
        data = [
            {"title": "Slide 1", "points": ["Point A", "Point B"]},
            {"title": "Slide 2", "points": ["Point C"]}
        ]
        result = asyncio.run(self.slide_tool.execute("Test Presentation", data, output_path))
        
        self.assertTrue(os.path.exists(output_path))
        self.assertIn("Successfully generated", result)
        
        # Cleanup
        if os.path.exists(output_path):
            os.remove(output_path)

if __name__ == '__main__':
    unittest.main()
