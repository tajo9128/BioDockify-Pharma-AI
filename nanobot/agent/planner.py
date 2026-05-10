"""
Research Lifecycle Manager - Persona-aware Research Progression and Tool Selection
Refactored from PhDPlanner to support Students, Faculty, and Researchers.
"""

import re
import logging
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class UserPersona(Enum):
    STUDENT = "student"
    FACULTY = "faculty"
    RESEARCHER = "researcher"
    RECEPTIONIST = "receptionist"

class ResearchLifecycleManager:
    """
    Manager for research lifecycles across different user personas.
    Determines current stage and recommends appropriate tools for Students, Faculty, and Researchers.
    """

    # Tools commonly used at each stage per persona
    PERSONA_TOOLS = {
        UserPersona.STUDENT: {
            'proposal': [
                'literature_landscape', 'gap_detection', 'novelty_scoring',
                'reference_management', 'topic_exploration'
            ],
            'early': [
                'literature_review', 'hypothesis_generation', 'methodology_design',
                'experimental_planning', 'feasibility_analysis'
            ],
            'mid': [
                'docking_execution', 'md_simulation', 'result_analysis',
                'data_visualization', 'experiment_tracking'
            ],
            'late': [
                'data_synthesis', 'discussion_writing', 'limitation_analysis',
                'figure_generation', 'result_validation'
            ],
            'submission': [
                'chapter_assembly', 'citation_formatting', 'viva_preparation',
                'manuscript_preparation', 'peer_review_simulation'
            ]
        },
        UserPersona.FACULTY: {
            'grant_writing': [
                'grant_forge', 'literature_landscape', 'collaboration_finder',
                'funding_tracker', 'budget_manager'
            ],
            'course_prep': [
                'syllabus_architect', 'note_gatherer', 'slide_deck_builder',
                'quiz_generator', 'resource_curator'
            ],
            'supervision': [
                'student_tracker', 'thesis_reviewer', 'meeting_scheduler',
                'progress_reporter'
            ],
            'admin': [
                'compliance_checker', 'department_report_generator',
                'lab_inventory_manager'
            ]

        },
        UserPersona.RESEARCHER: {
            'exploration': [
                'deep_drive', 'patent_search', 'grant_forge',
                'competitor_analysis'
            ],
            'execution': [
                'experiment_tracker', 'high_throughput_screener', 'data_analyst',
                'sim_runner', 'sample_manager'
            ],
            'analysis': [
                'statistical_suite', 'result_visualizer', 'mechanism_elucidator',
                'structure_activity_analyzer'
            ],
            'publication': [
                'manuscript_architect', 'journal_selector', 'citation_manager',
                'figure_polisher'
            ]
        }
    }

    # Detailed descriptions of each stage per persona
    PERSONA_STAGE_DESCRIPTIONS = {
        UserPersona.STUDENT: {
            'proposal': "Defining research topic, literature review, and hypothesis.",
            'early': "Finalizing methodology and starting initial experiments.",
            'mid': "Core research phase with active experimentation and analysis.",
            'late': "Synthesizing findings and writing the thesis.",
            'submission': "Final preparation, formatting, and defense."
        },
        UserPersona.FACULTY: {
            'grant_writing': "Preparing and submitting grant proposals for funding.",
            'course_prep': "Designing curriculum, syllabi, and lecture materials.",
            'supervision': "Mentoring students and reviewing their progress.",
            'admin': "Managing lab resources, compliance, and departmental duties."
        },
        UserPersona.RESEARCHER: {
            'exploration': "Identifying new research avenues and conducting feasibility studies.",
            'execution': "Running experiments, simulations, and data collection.",
            'analysis': "Interpreting data and deriving insights.",
            'publication': "Writing and submitting manuscripts to journals."
        }
    }

    def __init__(self):
        """Initialize the Research Lifecycle Manager."""
        pass

    def detect_stage(self, persona: UserPersona, project_metadata: Optional[Dict] = None) -> str:
        """
        Automatically detect lifecycle stage based on persona and project state.
        
        Args:
            persona: The user persona (Student, Faculty, Researcher).
            project_metadata: Dictionary containing project status and milestones.
            
        Returns:
            str: The detected stage key.
        """
        if not project_metadata:
            return self._get_default_stage(persona)

        # Check explicit stage indicator
        explicit_stage = project_metadata.get(f'{persona.value}_stage', '').lower()
        if explicit_stage and explicit_stage in self.PERSONA_TOOLS.get(persona, {}):
            return explicit_stage

        # Helper method for specific detection logic
        if persona == UserPersona.STUDENT:
            return self._detect_student_stage(project_metadata)
        elif persona == UserPersona.FACULTY:
            # Default to grant writing if ambiguous for now, logic can be expanded
            return 'grant_writing' 
        elif persona == UserPersona.RESEARCHER:
            return 'exploration'
            
        return self._get_default_stage(persona)

    def _get_default_stage(self, persona: UserPersona) -> str:
        defaults = {
            UserPersona.STUDENT: 'proposal',
            UserPersona.FACULTY: 'grant_writing',
            UserPersona.RESEARCHER: 'exploration'
        }
        return defaults.get(persona, 'proposal')

    def _detect_student_stage(self, metadata: Dict) -> str:
        """Legacy logic for PhD stage detection."""
        milestones = metadata.get('milestones', {})
        if not milestones.get('literature_review_complete', False):
            return 'proposal'
        if not milestones.get('experiments_started', False):
            return 'early'
        if not milestones.get('experiments_complete', False):
            return 'mid'
        if not milestones.get('thesis_started', False):
            return 'late'
        return 'submission'

    # Backward compatibility for PhDPlanner
    def detect_phd_stage(self, project_metadata: Optional[Dict] = None) -> str:
        """Alias for detect_stage using STUDENT persona."""
        return self.detect_stage(UserPersona.STUDENT, project_metadata)

    def detect_phd_stage_from_timeline(self, start_date: Optional[str] = None, total_duration_years: int = 4) -> str:
        """
        Detect PhD stage based on timeline.
        Kept for backward compatibility.
        """
        if not start_date:
            return 'proposal'

        try:
            start = datetime.fromisoformat(start_date)
            elapsed = (datetime.now() - start).total_seconds() / (365.25 * 24 * 3600)

            if elapsed < 0.2 * total_duration_years:
                return 'proposal'
            elif elapsed < 0.4 * total_duration_years:
                return 'early'
            elif elapsed < 0.75 * total_duration_years:
                return 'mid'
            elif elapsed < 0.95 * total_duration_years:
                return 'late'
            else:
                return 'submission'
        except (ValueError, TypeError):
            return 'proposal'

    def detect_stages(self, personas: List[UserPersona], project_metadata: Optional[Dict] = None) -> Dict[UserPersona, str]:
        """
        Detect stages for multiple active personas.
        
        Args:
            personas: List of active user personas.
            project_metadata: Project metadata.
            
        Returns:
            Dictionary mapping UserPersona to detected stage string.
        """
        return {p: self.detect_stage(p, project_metadata) for p in personas}

    def recommend_tools(self, goal: str, stage: str, persona: UserPersona = UserPersona.STUDENT, available_tools: Optional[List[str]] = None) -> List[str]:
        """
        Recommend tools based on persona, stage, and goal keywords.
        Single persona version (backward compatible).
        """
        return self.recommend_tools_multi(goal, {persona: stage}, available_tools)

    def recommend_tools_multi(self, goal: str, active_stages: Dict[UserPersona, str], available_tools: Optional[List[str]] = None) -> List[str]:
        """
        Recommend tools aggregating capabilities from multiple active personas.
        
        Args:
            goal: The user's current goal/task.
            active_stages: Dictionary mapping active personas to their current stages.
            available_tools: List of tool names available in the registry.
            
        Returns:
            List of recommended tool names sorted by relevance.
        """
        candidate_tools = set()
        
        # Aggregate tools from all active personas and their respective stages
        for persona, stage in active_stages.items():
            stage_tools_map = self.PERSONA_TOOLS.get(persona, {})
            # Get tools for this specific stage
            tools = stage_tools_map.get(stage, [])
            candidate_tools.update(tools)
            
            # Fallback: if stage looks like it belongs to another persona (cross-contamination safety)
            if not tools:
                for p_check in self.PERSONA_TOOLS:
                    if stage in self.PERSONA_TOOLS[p_check]:
                        candidate_tools.update(self.PERSONA_TOOLS[p_check][stage])

        # Filter by availability
        candidates_list = list(candidate_tools)
        if available_tools:
            candidates_list = [t for t in candidates_list if t in available_tools]

        # Scoring based on keyword matching
        goal_lower = goal.lower()
        keywords = re.findall(r'\b\w+\b', goal_lower)
        
        scored_tools = []
        for tool in candidates_list:
            score = sum(1 for kw in keywords if kw in tool.lower())
            scored_tools.append((tool, score))
            
        scored_tools.sort(key=lambda x: x[1], reverse=True)
        # Return tools with score > 0, or top 5 diversity if no direct match
        return [t for t, s in scored_tools if s > 0] or candidates_list[:5]

    def get_stage_description(self, stage: str, persona: UserPersona = UserPersona.STUDENT) -> str:
        descriptions = self.PERSONA_STAGE_DESCRIPTIONS.get(persona, {})
        return descriptions.get(stage, 'Unknown stage')

    def get_all_stages(self, persona: UserPersona = UserPersona.STUDENT) -> List[str]:
        return list(self.PERSONA_TOOLS.get(persona, {}).keys())

# Alias for backward compatibility
PhDPlanner = ResearchLifecycleManager
