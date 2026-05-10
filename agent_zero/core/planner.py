"""
Multi-step reasoning and PhD stage detection

This module provides:
- Automatic PhD stage detection from project metadata
- Tool recommendation based on stage and goals
- Multi-step planning capabilities
"""

from typing import Dict, List, Optional, Any
import re
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class LLMProvider:
    """Abstract base class for LLM providers"""

    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from prompt"""
        raise NotImplementedError


class PhDPlanner:
    """
    Planner for PhD research progression and tool selection

    This class helps determine:
    1. Current stage of the PhD journey
    2. Which tools are most appropriate for a given goal and stage
    3. Execution order and dependencies

    Attributes:
        llm: LLM provider for intelligent recommendations
        stage_tools: Mapping of PhD stages to recommended tools
        stage_descriptions: Descriptions of each PhD stage
    """

    # Tools commonly used at each PhD stage
    STAGE_TOOLS = {
        'proposal': [
            'literature_landscape',
            'gap_detection',
            'novelty_scoring',
            'reference_management',
            'topic_exploration'
        ],
        'early': [
            'literature_review',
            'hypothesis_generation',
            'methodology_design',
            'experimental_planning',
            'feasibility_analysis'
        ],
        'mid': [
            'docking_execution',
            'md_simulation',
            'result_analysis',
            'data_visualization',
            'experiment_tracking'
        ],
        'late': [
            'data_synthesis',
            'discussion_writing',
            'limitation_analysis',
            'figure_generation',
            'result_validation'
        ],
        'submission': [
            'chapter_assembly',
            'citation_formatting',
            'viva_preparation',
            'manuscript_preparation',
            'peer_review_simulation'
        ]
    }

    # Detailed descriptions of each stage
    STAGE_DESCRIPTIONS = {
        'proposal': """
The initial stage where the research topic is defined.
Focus areas:
- Conducting preliminary literature review
- Identifying research gaps
- Formulating research questions and hypotheses
- Defining scope and novelty of the project
- Preparing research proposal
        """,
        'early': """
The beginning phase of active research.
Focus areas:
- Comprehensive literature review
- Finalizing methodology
- Setting up experiments or simulations
- Initial data collection
- Refining hypotheses based on early findings
        """,
        'mid': """
The core research phase with active experimentation.
Focus areas:
- Executing main experiments or simulations
- Analyzing results
- Iterating based on findings
- Data management and organization
- Regular progress reporting
        """,
        'late': """
The synthesis and writing phase.
Focus areas:
- Synthesizing all research findings
- Writing dissertation chapters
- Creating figures and visualizations
- Analyzing limitations and future work
- Preparing supplementary materials
        """,
        'submission': """
Final preparation before thesis defense.
Focus areas:
- Assembling complete thesis
- Formatting and citations
- Preparing for viva voce
- Manuscript preparation for publication
- Final review and revisions
        """
    }

    def __init__(self, llm: LLMProvider):
        """
        Initialize the PhD Planner

        Args:
            llm: LLM provider for intelligent recommendations
        """
        self.llm = llm

    def detect_phd_stage(
        self,
        project_metadata: Optional[Dict] = None
    ) -> str:
        """
        Automatically detect PhD stage from project state

        The detection considers multiple factors:
        - Time since project start
        - Completion of key milestones
        - Available data and artifacts
        - Project progression indicators

        Args:
            project_metadata: Dictionary containing project information

        Returns:
            One of: 'proposal', 'early', 'mid', 'late', 'submission'
        """
        if not project_metadata:
            project_metadata = {}

        # Check explicit stage indicator
        if 'phd_stage' in project_metadata:
            explicit_stage = project_metadata['phd_stage'].lower()
            if explicit_stage in self.STAGE_TOOLS:
                return explicit_stage

        # Detection based on project milestones
        milestones = project_metadata.get('milestones', {})

        # Check if literature review is complete
        if not milestones.get('literature_review_complete', False):
            return 'proposal'

        # Check if experiments have started
        if not milestones.get('experiments_started', False):
            return 'early'

        # Check if experiments are complete
        if not milestones.get('experiments_complete', False):
            return 'mid'

        # Check if thesis writing has started
        if not milestones.get('thesis_started', False):
            return 'late'

        # All major milestones complete
        return 'submission'

    def detect_phd_stage_from_timeline(
        self,
        start_date: Optional[str] = None,
        total_duration_years: int = 4
    ) -> str:
        """
        Detect PhD stage based on timeline

        Args:
            start_date: ISO format date string when PhD started
            total_duration_years: Expected total PhD duration

        Returns:
            Detected PhD stage
        """
        if not start_date:
            return 'proposal'

        try:
            start = datetime.fromisoformat(start_date)
            elapsed = (datetime.now() - start).total_seconds() / (365.25 * 24 * 3600)  # Years

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

        except (ValueError, TypeError) as e:
            logger.warning(f"Error parsing start_date: {e}")
            return 'proposal'

    async def recommend_tools(
        self,
        goal: str,
        stage: str,
        available_tools: Optional[List[str]] = None,
        max_recommendations: int = 5
    ) -> List[str]:
        """
        Recommend tools based on goal and PhD stage

        This method:
        1. Gets stage-specific tools
        2. Filters by available tools if provided
        3. Uses LLM to rank and select most relevant tools

        Args:
            goal: Research goal or objective
            stage: Current PhD stage
            available_tools: List of available tool names (optional)
            max_recommendations: Maximum number of tools to recommend

        Returns:
            List of recommended tool names
        """
        # Get stage-specific tools
        stage_specific = self.STAGE_TOOLS.get(stage, [])

        # Filter by available tools
        if available_tools:
            stage_specific = [
                tool for tool in stage_specific
                if tool in available_tools
            ]

        if not stage_specific:
            logger.warning(f"No stage-specific tools found for stage: {stage}")
            return []

        # Use LLM to select and rank most relevant tools
        prompt = f"""
You are a PhD research advisor helping select the best tools for a research goal.

Research Goal: {goal}
PhD Stage: {stage}

Stage Description:
{self.STAGE_DESCRIPTIONS.get(stage, 'No description available')}

Available tools for this stage:
{self._format_tool_list(stage_specific)}

Select the {max_recommendations} most relevant tools for this goal and stage.

Consider:
1. Which tools directly address the goal?
2. What's the optimal order of tool usage?
3. Which tools are essential vs. optional?

Format your response as a Python list:
['tool1', 'tool2', 'tool3', ...]

Respond ONLY with the list, no explanation.
"""

        try:
            response = await self.llm.generate(prompt, max_tokens=500)
            recommended = self._extract_tool_names(response)

            # Ensure we don't exceed max recommendations
            recommended = recommended[:max_recommendations]

            logger.info(f"Recommended {len(recommended)} tools for stage {stage}")
            return recommended

        except Exception as e:
            logger.error(f"Error recommending tools: {str(e)}")
            # Fallback: return first N stage-specific tools
            return stage_specific[:max_recommendations]

    def recommend_tools_simple(
        self,
        goal: str,
        stage: str,
        available_tools: Optional[List[str]] = None
    ) -> List[str]:
        """
        Simple tool recommendation without LLM

        Uses keyword matching to find relevant tools

        Args:
            goal: Research goal
            stage: PhD stage
            available_tools: List of available tools

        Returns:
            List of recommended tool names
        """
        stage_specific = self.STAGE_TOOLS.get(stage, [])

        if available_tools:
            stage_specific = [
                tool for tool in stage_specific
                if tool in available_tools
            ]

        # Extract keywords from goal
        goal_lower = goal.lower()
        keywords = re.findall(r'\b\w+\b', goal_lower)

        # Score tools based on keyword matches
        scored_tools = []
        for tool in stage_specific:
            tool_lower = tool.lower()
            score = sum(1 for kw in keywords if kw in tool_lower)
            scored_tools.append((tool, score))

        # Sort by score and return
        scored_tools.sort(key=lambda x: x[1], reverse=True)

        return [tool for tool, score in scored_tools if score > 0]

    async def create_execution_plan(
        self,
        goal: str,
        stage: str,
        available_tools: List[str],
        context: Optional[Dict] = None
    ) -> Dict:
        """
        Create a detailed execution plan for a research goal

        Args:
            goal: High-level research goal
            stage: Current PhD stage
            available_tools: List of available tools
            context: Additional context for planning

        Returns:
            Execution plan with steps and dependencies
        """
        # Get recommended tools
        recommended_tools = await self.recommend_tools(
            goal, stage, available_tools, max_recommendations=5
        )

        prompt = f"""
Create a detailed execution plan for this research goal.

Research Goal: {goal}
PhD Stage: {stage}

Recommended Tools: {', '.join(recommended_tools)}
All Available Tools: {', '.join(available_tools)}

{"Additional Context: " + str(context) if context else ""}

Create a step-by-step execution plan in JSON format:
{{
  "steps": [
    {{
      "step": 1,
      "tool": "tool_name",
      "description": "What this step accomplishes",
      "params": {{"key": "value"}},
      "estimated_time": "hours",
      "dependencies": []
    }}
  ],
  "overview": "Brief overview of the plan",
  "estimated_total_time": "hours",
  "risks": ["potential risk 1", "potential risk 2"],
  "success_criteria": ["criterion 1", "criterion 2"]
}}

Requirements:
1. Use only available tools
2. Specify dependencies between steps (by step number)
3. Provide realistic time estimates
4. Identify potential risks and success criteria
5. Return ONLY the JSON, no explanation
"""

        try:
            response = await self.llm.generate(prompt, max_tokens=2000)
            plan = self._parse_json(response)

            if not plan:
                # Fallback to simple plan
                plan = {
                    'steps': [
                        {
                            'step': i + 1,
                            'tool': tool,
                            'description': f'Execute {tool}',
                            'params': {},
                            'estimated_time': '1',
                            'dependencies': []
                        }
                        for i, tool in enumerate(recommended_tools)
                    ],
                    'overview': f'Execute {len(recommended_tools)} steps for {goal}',
                    'estimated_total_time': str(len(recommended_tools)),
                    'risks': [],
                    'success_criteria': []
                }

            logger.info(f"Created execution plan with {len(plan.get('steps', []))} steps")
            return plan

        except Exception as e:
            logger.error(f"Error creating execution plan: {str(e)}")
            return {'error': str(e)}

    def get_stage_description(self, stage: str) -> str:
        """Get description of a PhD stage"""
        return self.STAGE_DESCRIPTIONS.get(stage, 'Unknown stage')

    def get_stage_tools(self, stage: str) -> List[str]:
        """Get tools associated with a stage"""
        return self.STAGE_TOOLS.get(stage, []).copy()

    def get_all_stages(self) -> List[str]:
        """Get list of all PhD stages"""
        return list(self.STAGE_TOOLS.keys())

    def _format_tool_list(self, tools: List[str]) -> str:
        """Format tool list for display"""
        return '\n'.join([f"- {tool}" for tool in tools])

    def _extract_tool_names(self, text: str) -> List[str]:
        """
        Extract tool names from LLM response

        Args:
            text: LLM response text

        Returns:
            List of tool names
        """
        # Try to parse as Python list
        import json

        # Clean up the text
        text = text.strip()

        # Try JSON parsing first
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

        # Extract from list notation: ['tool1', 'tool2']
        list_match = re.search(r'\[([^\]]+)\]', text)
        if list_match:
            items = list_match.group(1)
            # Extract quoted strings
            tools = re.findall(r'["\']([^"\']+)["\']', items)
            if tools:
                return tools

        # Extract tool-like words (alphanumeric with underscores)
        tools = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', text)

        # Filter common words
        stop_words = {'the', 'and', 'for', 'use', 'using', 'select', 'recommend', 'tools', 'tool', 'list', 'are', 'is', 'best'}
        tools = [t for t in tools if t.lower() not in stop_words and len(t) > 2]

        return tools

    def _parse_json(self, text: str) -> Dict:
        """
        Parse JSON from text

        Args:
            text: Text containing JSON

        Returns:
            Parsed dictionary or empty dict
        """
        import json

        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass

        # Try to find JSON in text
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        return {}

    def get_next_stage(self, current_stage: str) -> Optional[str]:
        """Get the next stage in the PhD progression"""
        stages = self.get_all_stages()
        try:
            idx = stages.index(current_stage)
            if idx < len(stages) - 1:
                return stages[idx + 1]
        except ValueError:
            pass
        return None

    def get_stage_progression(self) -> Dict[str, int]:
        """Get stage progression mapping"""
        return {stage: idx for idx, stage in enumerate(self.get_all_stages())}
