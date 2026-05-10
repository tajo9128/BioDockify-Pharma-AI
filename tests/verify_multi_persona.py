
import unittest
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nanobot.agent.planner import ResearchLifecycleManager, UserPersona

class TestMultiPersona(unittest.TestCase):
    def setUp(self):
        self.manager = ResearchLifecycleManager()

    def test_multi_stage_detection(self):
        """Test detecting stages for multiple personas simultaneously."""
        personas = [UserPersona.FACULTY, UserPersona.STUDENT]
        
        # Faculty default (grant_writing), Student late (thesis_started)
        metadata = {
            'milestones': {
                'literature_review_complete': True,
                'experiments_started': True,
                'experiments_complete': True,
                'thesis_started': True # Late student stage
            }
        }
        
        stages = self.manager.detect_stages(personas, metadata)
        
        self.assertEqual(stages[UserPersona.FACULTY], 'grant_writing')
        self.assertEqual(stages[UserPersona.STUDENT], 'submission')

    def test_multi_tool_recommendation(self):
        """Test tool recommendations aggregating from multiple personas."""
        active_stages = {
            UserPersona.FACULTY: 'course_prep',
            UserPersona.STUDENT: 'submission'
        }
        
        # User wants to work on their thesis and prepare a syllabus
        # Goal 1: "Write thesis chapter" -> Should trigger Student tool ('chapter_assembly' is in submission)
        tools = self.manager.recommend_tools_multi("Write thesis chapter", active_stages)
        self.assertIn('chapter_assembly', tools)
        
        # Goal 2: "Design syllabus" -> Should trigger Faculty tool
        tools = self.manager.recommend_tools_multi("Design syllabus", active_stages)
        self.assertIn('syllabus_architect', tools)
        
        # Goal 3: Mixed/Ambiguous -> Should handle gracefully
        # "Generate slides for thesis defense" 
        # Faculty has 'slide_deck_builder', Student has 'figure_generation' or 'viva_preparation'
        tools = self.manager.recommend_tools_multi("Create presentation slides", active_stages)
        # slide_deck_builder is in Faculty[course_prep]
        self.assertIn('slide_deck_builder', tools)

if __name__ == '__main__':
    unittest.main()
