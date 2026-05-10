
import sys
import os
import unittest
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nanobot.agent.planner import ResearchLifecycleManager, UserPersona, PhDPlanner

class TestResearchLifecycleManager(unittest.TestCase):
    def setUp(self):
        self.manager = ResearchLifecycleManager()

    def test_backward_compatibility(self):
        """Test that PhDPlanner alias works and detects student stages."""
        planner = PhDPlanner()
        metadata = {'milestones': {'literature_review_complete': True, 'experiments_started': True}}
        stage = planner.detect_phd_stage(metadata)
        self.assertEqual(stage, 'mid')
        
    def test_student_lifecycle(self):
        """Test explicit Student persona lifecycle."""
        # Must include all prior milestones due to sequential check
        # 'late' stage corresponds to: exp complete, but thesis NOT started yet.
        metadata = {
            'milestones': {
                'literature_review_complete': True,
                'experiments_started': True,
                'experiments_complete': True,
                'thesis_started': False
            }
        }
        stage = self.manager.detect_stage(UserPersona.STUDENT, metadata)
        self.assertEqual(stage, 'late')

    def test_faculty_lifecycle(self):
        """Test Faculty persona lifecycle."""
        # Default behavior
        stage = self.manager.detect_stage(UserPersona.FACULTY, {})
        self.assertEqual(stage, 'grant_writing')
        
        # Explicit stage
        metadata = {'faculty_stage': 'course_prep'}
        stage = self.manager.detect_stage(UserPersona.FACULTY, metadata)
        self.assertEqual(stage, 'course_prep')
        
        # Tools check - "syllabus" should return syllabus_architect
        tools = self.manager.recommend_tools("Create syllabus", 'course_prep', UserPersona.FACULTY)
        self.assertIn('syllabus_architect', tools)
        
        # Tools check - "notes" should return note_gatherer
        tools = self.manager.recommend_tools("Gather lecture notes", 'course_prep', UserPersona.FACULTY)
        self.assertIn('note_gatherer', tools)

        # PPT check (user request)
        tools = self.manager.recommend_tools("Make slides", 'course_prep', UserPersona.FACULTY)
        self.assertIn('slide_deck_builder', tools)

    def test_researcher_lifecycle(self):
        """Test Researcher persona lifecycle."""
        stage = self.manager.detect_stage(UserPersona.RESEARCHER, {})
        self.assertEqual(stage, 'exploration')
        
        metadata = {'researcher_stage': 'publication'}
        stage = self.manager.detect_stage(UserPersona.RESEARCHER, metadata)
        self.assertEqual(stage, 'publication')
        
        tools = self.manager.recommend_tools("Write paper", 'publication', UserPersona.RESEARCHER)
        self.assertIn('manuscript_architect', tools)

if __name__ == '__main__':
    unittest.main()
