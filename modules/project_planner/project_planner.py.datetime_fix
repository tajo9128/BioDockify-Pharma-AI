"""
Project Planner - Breaks down project titles into comprehensive task lists
Integrates with Agent Zero for intelligent planning
"""
import uuid
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ProjectType(str, Enum):
    """Types of projects supported"""
    RESEARCH = "research"
    DEVELOPMENT = "development"
    WRITING = "writing"
    REVIEW = "review"
    GRANT_APPLICATION = "grant_application"
    PUBLICATION = "publication"
    CLINICAL_TRIAL = "clinical_trial"
    THESIS = "thesis"
    LAB_EXPERIMENT = "lab_experiment"


class ProjectPhase(str, Enum):
    """Standard project phases"""
    PLANNING = "planning"
    PREPARATION = "preparation"
    EXECUTION = "execution"
    ANALYSIS = "analysis"
    REVIEW = "review"
    FINALIZATION = "finalization"


@dataclass
class ProjectTask:
    """Task within a project"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    phase: ProjectPhase = ProjectPhase.PLANNING
    priority: int = 0  # 0 = highest
    depends_on: List[str] = field(default_factory=list)
    estimated_hours: float = 0.0
    status: str = "pending"
    assigned_to: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


@dataclass
class Project:
    """Complete project plan"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    project_type: ProjectType = ProjectType.RESEARCH
    created_at: datetime = field(default_factory=datetime.utcnow)
    estimated_completion: Optional[datetime] = None
    status: str = "planning"
    tasks: List[ProjectTask] = field(default_factory=list)
    device_sessions: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ProjectPlanner:
    """
    Project Planner - Uses Agent Zero to create comprehensive project plans
    
    Features:
    - Project title → Full task breakdown
    - Agent Zero planning integration
    - Persistent memory recall
    - Timeline estimation
    - Resource allocation
    """

    def __init__(self, hybrid_agent=None, memory_system=None):
        self.hybrid_agent = hybrid_agent
        self.memory_system = memory_system
        self.projects: Dict[str, Project] = {}
        self._setup_logging()

    def _setup_logging(self):
        logger.info("Project Planner initialized")

    async def create_project_from_title(
        self,
        project_title: str,
        project_type: ProjectType = ProjectType.RESEARCH,
        additional_context: Optional[str] = None
    ) -> Project:
        """
        Create a complete project plan from a simple title
        
        Args:
            project_title: The project title
            project_type: Type of project
            additional_context: Any additional details
        
        Returns:
            Complete Project with task list
        """
        logger.info(f"Creating project plan for: {project_title}")

        # Step 1: Recall relevant projects from memory
        similar_projects = await self._recall_similar_projects(project_title)

        # Step 2: Use Agent Zero to plan the project
        project_plan = await self._agent_zero_plan_project(
            project_title,
            project_type,
            additional_context,
            similar_projects
        )

        # Process tasks from plan
        tasks = []
        for task_dict in project_plan.get('tasks', []):
            tasks.append(ProjectTask(
                title=task_dict.get('title', ''),
                description=task_dict.get('description', ''),
                phase=ProjectPhase(task_dict.get('phase', 'planning')),
                priority=task_dict.get('priority', 2),
                estimated_hours=task_dict.get('estimated_hours', 1.0),
                depends_on=task_dict.get('depends_on', [])
            ))

        # Step 3: Create Project object
        project = Project(
            title=project_title,
            description=project_plan.get('description', ''),
            project_type=project_type,
            estimated_completion=datetime.utcnow() + timedelta(days=project_plan.get('estimated_days', 30)),
            tasks=tasks,
            metadata=project_plan.get('metadata', {})
        )

        self.projects[project.id] = project

        # Step 4: Store project in persistent memory
        await self._store_project_in_memory(project)

        logger.info(f"Created project plan with {len(project.tasks)} tasks")
        return project

    async def _recall_similar_projects(
        self,
        project_title: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Recall similar projects from memory for context"""
        if not self.memory_system:
            return []

        try:
            # Search for similar projects
            results = await self.memory_system.search(
                query=f"project {project_title} research tasks plan",
                limit=limit
            )

            logger.info(f"Recalled {len(results)} similar project memories")
            return results
        except Exception as e:
            logger.error(f"Error recalling similar projects: {e}")
            return []

    async def _agent_zero_plan_project(
        self,
        project_title: str,
        project_type: ProjectType,
        additional_context: Optional[str],
        similar_projects: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Use Agent Zero to create detailed project plan
        """
        # Build planning prompt
        similar_context = ""
        if similar_projects:
            similar_context = "\n\nSimilar Projects for Reference:\n"
            for i, proj in enumerate(similar_projects[:3]):
                similar_context += f"\n{i+1}. {proj.get('content', '')[:200]}...\n"

        planning_prompt = f"""
You are a Project Planning Expert for pharmaceutical research.

Create a detailed task breakdown for the following project:

PROJECT TITLE: {project_title}
PROJECT TYPE: {project_type.value}
ADDITIONAL CONTEXT: {additional_context or 'None'}

{similar_context}

REQUIREMENTS:
1. Break down the project into logical tasks
2. Each task should have:
   - Clear title
   - Detailed description
   - Phase (planning, preparation, execution, analysis, review, finalization)
   - Priority (0-5, where 0 is highest)
   - Estimated hours
   - Dependencies (list task IDs this depends on)

3. Create tasks in order of execution
4. Consider dependencies between tasks
5. Estimate total project duration

Respond in JSON format:
{{
  "description": "Brief project description",
  "estimated_days": <total days>,
  "tasks": [
    {{
      "title": "Task title",
      "description": "Detailed task description",
      "phase": "planning|preparation|execution|analysis|review|finalization",
      "priority": 0-5,
      "estimated_hours": <hours>,
      "depends_on": [<task_ids>],
      "metadata": {{<any additional info>}}
    }}
  ],
  "metadata": {{
    "total_tasks": <count>,
    "phases": <list of phases>,
    "estimated_effort_hours": <total hours>,
    "key_deliverables": <list of deliverables>
  }}
}}
"""

        try:
            # Execute through Agent Zero
            if self.hybrid_agent:
                # We use the execute method we added earlier if available
                if hasattr(self.hybrid_agent, 'execute'):
                    response_json = await self.hybrid_agent.execute(planning_prompt)
                    import json
                    try:
                        # Extract JSON from response if it has text around it
                        if "```json" in response_json:
                            json_str = response_json.split("```json")[1].split("```")[0].strip()
                        elif "```" in response_json:
                            json_str = response_json.split("```")[1].split("```")[0].strip()
                        else:
                            json_str = response_json
                        
                        return json.loads(json_str)
                    except:
                        logger.warning("Failed to parse Agent Zero planning response as JSON, using template.")

            return self._create_default_plan(project_title, project_type)

        except Exception as e:
            logger.error(f"Error in Agent Zero planning: {e}")
            return self._create_default_plan(project_title, project_type)

    def _create_default_plan(
        self,
        project_title: str,
        project_type: ProjectType
    ) -> Dict[str, Any]:
        """Create default project plan template"""
        templates = {
            ProjectType.RESEARCH: self._research_template(project_title),
            ProjectType.DEVELOPMENT: self._development_template(project_title),
            ProjectType.WRITING: self._writing_template(project_title),
            ProjectType.REVIEW: self._review_template(project_title),
            ProjectType.GRANT_APPLICATION: self._grant_template(project_title),
            ProjectType.PUBLICATION: self._publication_template(project_title),
            ProjectType.CLINICAL_TRIAL: self._clinical_trial_template(project_title),
            ProjectType.THESIS: self._thesis_template(project_title),
            ProjectType.LAB_EXPERIMENT: self._experiment_template(project_title),
        }

        return templates.get(project_type, self._generic_template(project_title))

    def _research_template(self, title: str) -> Dict[str, Any]:
        """Template for research projects"""
        return {
            "description": f"Research project on {title}",
            "estimated_days": 30,
            "tasks": [
                {"title": "Literature Review", "description": f"Conduct comprehensive literature review on {title}", "phase": "planning", "priority": 0, "estimated_hours": 40, "depends_on": []},
                {"title": "Hypothesis Development", "description": "Formulate testable hypotheses based on literature review", "phase": "planning", "priority": 0, "estimated_hours": 8, "depends_on": []},
                {"title": "Study Protocol Design", "description": "Design detailed study protocol including methods and materials", "phase": "preparation", "priority": 1, "estimated_hours": 16, "depends_on": []},
                {"title": "IRB/Ethics Approval", "description": "Prepare and submit IRB/ethics committee application", "phase": "preparation", "priority": 0, "estimated_hours": 20, "depends_on": []},
                {"title": "Data Collection", "description": "Execute data collection according to protocol", "phase": "execution", "priority": 1, "estimated_hours": 60, "depends_on": ["Study Protocol Design", "IRB/Ethics Approval"]},
                {"title": "Data Analysis", "description": "Analyze collected data using appropriate statistical methods", "phase": "analysis", "priority": 2, "estimated_hours": 40, "depends_on": ["Data Collection"]},
                {"title": "Results Interpretation", "description": "Interpret results and draw conclusions", "phase": "analysis", "priority": 2, "estimated_hours": 24, "depends_on": ["Data Analysis"]},
                {"title": "Manuscript Drafting", "description": "Draft manuscript including introduction, methods, results, discussion", "phase": "review", "priority": 3, "estimated_hours": 40, "depends_on": ["Results Interpretation"]},
                {"title": "Peer Review Response", "description": "Address reviewer comments and revise manuscript", "phase": "review", "priority": 3, "estimated_hours": 24, "depends_on": ["Manuscript Drafting"]},
                {"title": "Final Submission", "description": "Submit final manuscript to target journal", "phase": "finalization", "priority": 4, "estimated_hours": 8, "depends_on": ["Peer Review Response"]}
            ],
            "metadata": {
                "total_tasks": 10,
                "phases": ["planning", "preparation", "execution", "analysis", "review", "finalization"],
                "estimated_effort_hours": 280,
                "key_deliverables": ["Literature Review", "Study Protocol", "Dataset", "Manuscript", "Publication"]
            }
        }

    def _development_template(self, title: str) -> Dict[str, Any]:
        """Template for development projects"""
        return {
            "description": f"Development project for {title}",
            "estimated_days": 60,
            "tasks": [
                {"title": "Requirements Analysis", "description": "Gather and analyze requirements for the project", "phase": "planning", "priority": 0, "estimated_hours": 16, "depends_on": []},
                {"title": "Architecture Design", "description": "Design system architecture and technical specifications", "phase": "planning", "priority": 0, "estimated_hours": 24, "depends_on": ["Requirements Analysis"]},
                {"title": "Backend Development", "description": "Develop backend APIs and business logic", "phase": "execution", "priority": 0, "estimated_hours": 80, "depends_on": ["Architecture Design"]},
                {"title": "Frontend Development", "description": "Implement frontend components and interactions", "phase": "execution", "priority": 0, "estimated_hours": 80, "depends_on": ["Architecture Design"]},
                {"title": "Integration & Testing", "description": "Integrate components and conduct testing", "phase": "execution", "priority": 1, "estimated_hours": 48, "depends_on": ["Backend Development", "Frontend Development"]},
                {"title": "Deployment", "description": "Deploy application to production environment", "phase": "finalization", "priority": 1, "estimated_hours": 16, "depends_on": ["Integration & Testing"]}
            ],
            "metadata": {"total_tasks": 6, "estimated_effort_hours": 264}
        }

    def _writing_template(self, title: str) -> Dict[str, Any]:
        return {
            "description": f"Writing project: {title}",
            "estimated_days": 14,
            "tasks": [
                {"title": "Outline", "description": "Create detailed outline", "phase": "planning", "priority": 0, "estimated_hours": 4, "depends_on": []},
                {"title": "First Draft", "description": "Write first draft", "phase": "execution", "priority": 1, "estimated_hours": 24, "depends_on": ["Outline"]},
                {"title": "Review & Edit", "description": "Review and edit manuscript", "phase": "review", "priority": 2, "estimated_hours": 8, "depends_on": ["First Draft"]},
                {"title": "Final Version", "description": "Produce final version", "phase": "finalization", "priority": 3, "estimated_hours": 4, "depends_on": ["Review & Edit"]}
            ],
            "metadata": {"total_tasks": 4}
        }

    def _review_template(self, title: str) -> Dict[str, Any]:
        return {
            "description": f"Review of {title}",
            "estimated_days": 7,
            "tasks": [
                {"title": "Initial Read", "description": "Initial thorough reading", "phase": "planning", "priority": 0, "estimated_hours": 4, "depends_on": []},
                {"title": "Detailed Analysis", "description": "Detailed point-by-point analysis", "phase": "analysis", "priority": 1, "estimated_hours": 8, "depends_on": ["Initial Read"]},
                {"title": "Review Report", "description": "Write review report", "phase": "review", "priority": 1, "estimated_hours": 4, "depends_on": ["Detailed Analysis"]}
            ],
            "metadata": {"total_tasks": 3}
        }

    def _grant_template(self, title: str) -> Dict[str, Any]:
        return {
            "description": f"Grant application for {title}",
            "estimated_days": 45,
            "tasks": [
                {"title": "Concept Note", "description": "Develop concept note", "phase": "planning", "priority": 0, "estimated_hours": 8, "depends_on": []},
                {"title": "Budget Preparation", "description": "Prepare detailed budget", "phase": "preparation", "priority": 1, "estimated_hours": 16, "depends_on": ["Concept Note"]},
                {"title": "Full Proposal Writing", "description": "Write full grant proposal", "phase": "execution", "priority": 0, "estimated_hours": 40, "depends_on": ["Concept Note"]},
                {"title": "Internal Review", "description": "Submit for internal review", "phase": "review", "priority": 1, "estimated_hours": 8, "depends_on": ["Full Proposal Writing"]},
                {"title": "Final Submission", "description": "Finalize and submit grant", "phase": "finalization", "priority": 0, "estimated_hours": 4, "depends_on": ["Internal Review"]}
            ],
            "metadata": {"total_tasks": 5}
        }

    def _publication_template(self, title: str) -> Dict[str, Any]:
        return {
            "description": f"Publication project for {title}",
            "estimated_days": 21,
            "tasks": [
                {"title": "Journal Selection", "description": "Select target journal", "phase": "planning", "priority": 0, "estimated_hours": 4, "depends_on": []},
                {"title": "Formatting", "description": "Format according to journal guidelines", "phase": "preparation", "priority": 1, "estimated_hours": 8, "depends_on": ["Journal Selection"]},
                {"title": "Cover Letter", "description": "Write cover letter", "phase": "preparation", "priority": 2, "estimated_hours": 2, "depends_on": ["Journal Selection"]},
                {"title": "Online Submission", "description": "Complete online submission process", "phase": "finalization", "priority": 0, "estimated_hours": 4, "depends_on": ["Formatting", "Cover Letter"]}
            ],
            "metadata": {"total_tasks": 4}
        }

    def _clinical_trial_template(self, title: str) -> Dict[str, Any]:
        return {
            "description": f"Clinical trial protocol for {title}",
            "estimated_days": 120,
            "tasks": [
                {"title": "Protocol Draft", "description": "Draft study protocol", "phase": "planning", "priority": 0, "estimated_hours": 40, "depends_on": []},
                {"title": "Regulatory Filing", "description": "Submit to regulatory bodies", "phase": "preparation", "priority": 0, "estimated_hours": 80, "depends_on": ["Protocol Draft"]},
                {"title": "Site Selection", "description": "Identify and select clinical sites", "phase": "preparation", "priority": 1, "estimated_hours": 40, "depends_on": ["Protocol Draft"]},
                {"title": "Patient Recruitment", "description": "Recruit and enroll participants", "phase": "execution", "priority": 1, "estimated_hours": 160, "depends_on": ["Regulatory Filing", "Site Selection"]},
                {"title": "Data Monitoring", "description": "Ongoing data monitoring", "phase": "execution", "priority": 2, "estimated_hours": 80, "depends_on": ["Patient Recruitment"]}
            ],
            "metadata": {"total_tasks": 5}
        }

    def _thesis_template(self, title: str) -> Dict[str, Any]:
        return {
            "description": f"Thesis project: {title}",
            "estimated_days": 180,
            "tasks": [
                {"title": "Proposal", "description": "Write and defend proposal", "phase": "planning", "priority": 0, "estimated_hours": 40, "depends_on": []},
                {"title": "Literature Review Chapter", "description": "Complete literature review", "phase": "execution", "priority": 1, "estimated_hours": 80, "depends_on": ["Proposal"]},
                {"title": "Research/Experiments", "description": "Conduct core research", "phase": "execution", "priority": 0, "estimated_hours": 160, "depends_on": ["Proposal"]},
                {"title": "Data Analysis Chapter", "description": "Write analysis chapter", "phase": "analysis", "priority": 1, "estimated_hours": 40, "depends_on": ["Research/Experiments"]},
                {"title": "Conclusion & Filing", "description": "Finalize thesis and file", "phase": "finalization", "priority": 2, "estimated_hours": 20, "depends_on": ["Data Analysis Chapter"]}
            ],
            "metadata": {"total_tasks": 5}
        }

    def _experiment_template(self, title: str) -> Dict[str, Any]:
        return {
            "description": f"Lab experiment: {title}",
            "estimated_days": 14,
            "tasks": [
                {"title": "Reagent Prep", "description": "Prepare all reagents and materials", "phase": "preparation", "priority": 0, "estimated_hours": 4, "depends_on": []},
                {"title": "Execution", "description": "Run the laboratory protocol", "phase": "execution", "priority": 0, "estimated_hours": 16, "depends_on": ["Reagent Prep"]},
                {"title": "Sample Analysis", "description": "Analyze resulting samples", "phase": "analysis", "priority": 1, "estimated_hours": 8, "depends_on": ["Execution"]},
                {"title": "Lab Report", "description": "Document results in lab notebook", "phase": "finalization", "priority": 2, "estimated_hours": 4, "depends_on": ["Sample Analysis"]}
            ],
            "metadata": {"total_tasks": 4}
        }

    def _generic_template(self, title: str) -> Dict[str, Any]:
        """Generic project template"""
        return {
            "description": f"Project: {title}",
            "estimated_days": 30,
            "tasks": [
                {"title": "Planning", "description": f"Create detailed plan for {title}", "phase": "planning", "priority": 0, "estimated_hours": 8, "depends_on": []},
                {"title": "Preparation", "description": "Gather resources and prepare for execution", "phase": "preparation", "priority": 1, "estimated_hours": 16, "depends_on": ["Planning"]},
                {"title": "Execution Phase 1", "description": f"Execute initial phase of {title}", "phase": "execution", "priority": 1, "estimated_hours": 40, "depends_on": ["Preparation"]},
                {"title": "Execution Phase 2", "description": f"Execute main phase of {title}", "phase": "execution", "priority": 1, "estimated_hours": 40, "depends_on": ["Execution Phase 1"]},
                {"title": "Analysis", "description": "Analyze results and findings", "phase": "analysis", "priority": 2, "estimated_hours": 24, "depends_on": ["Execution Phase 2"]},
                {"title": "Review", "description": "Review and refine work", "phase": "review", "priority": 3, "estimated_hours": 16, "depends_on": ["Analysis"]},
                {"title": "Finalization", "description": "Complete and deliver final output", "phase": "finalization", "priority": 4, "estimated_hours": 16, "depends_on": ["Review"]}
            ],
            "metadata": {
                "total_tasks": 7,
                "phases": ["planning", "preparation", "execution", "analysis", "review", "finalization"],
                "estimated_effort_hours": 160,
                "key_deliverables": ["Plan", "Output", "Report"]
            }
        }

    async def _store_project_in_memory(self, project: Project):
        """Store project plan in persistent memory"""
        if not self.memory_system:
            return

        try:
            # Import here to avoid circular dependencies
            from modules.memory.advanced_memory import MemoryType, MemoryImportance

            project_content = f"""
Project: {project.title}
Description: {project.description}
Type: {project.project_type.value}
Total Tasks: {len(project.tasks)}
Estimated Completion: {project.estimated_completion}

Task List:
{chr(10).join([f"{i+1}. {task.title} ({task.phase.value}) - {task.estimated_hours}h" for i, task in enumerate(project.tasks)])}
            """.strip()

            await self.memory_system.add_memory(
                content=project_content,
                memory_type=MemoryType.SEMANTIC,
                importance=MemoryImportance.HIGH,
                source=f"project:{project.id}",
                tags=['project', 'task_list', 'plan', project.project_type.value],
                metadata={
                    'project_id': project.id,
                    'project_title': project.title,
                    'project_type': project.project_type.value,
                    'task_count': len(project.tasks),
                    'total_hours': sum(task.estimated_hours for task in project.tasks)
                }
            )

            logger.info(f"Stored project plan in memory: {project.id}")

        except Exception as e:
            logger.error(f"Error storing project in memory: {e}")

    async def get_project(self, project_id: str) -> Optional[Project]:
        """Get project by ID"""
        return self.projects.get(project_id)

    async def list_projects(self, project_type: Optional[ProjectType] = None) -> List[Project]:
        """List all projects, optionally filtered by type"""
        if project_type:
            return [p for p in self.projects.values() if p.project_type == project_type]
        return list(self.projects.values())

    async def get_project_tasks(
        self,
        project_id: str,
        status_filter: Optional[str] = None
    ) -> List[ProjectTask]:
        """Get tasks for a project, optionally filtered"""
        project = await self.get_project(project_id)
        if not project:
            return []

        tasks = project.tasks
        if status_filter:
            tasks = [t for t in tasks if t.status == status_filter]

        return tasks

    async def update_task_status(
        self,
        project_id: str,
        task_id: str,
        status: str,
        progress_data: Optional[Dict[str, Any]] = None
    ):
        """Update task status and progress"""
        project = await self.get_project(project_id)
        if not project:
            return

        for task in project.tasks:
            if task.id == task_id:
                task.status = status
                if status == "completed":
                    task.completed_at = datetime.utcnow()

                # Store task completion in memory
                if self.memory_system:
                    await self._store_task_completion(project, task, progress_data)

                break

        logger.info(f"Updated task {task_id} to status: {status}")

    async def _store_task_completion(
        self,
        project: Project,
        task: ProjectTask,
        progress_data: Optional[Dict[str, Any]]
    ):
        """Store task completion in memory for learning"""
        try:
            from modules.memory.advanced_memory import MemoryType, MemoryImportance

            completion_content = f"""
Completed Task: {task.title}
Project: {project.title}
Phase: {task.phase.value}
Duration: {task.estimated_hours}h (estimated)
Completed At: {task.completed_at}

Results:
{str(progress_data or 'No additional data')}
            """.strip()

            await self.memory_system.add_memory(
                content=completion_content,
                memory_type=MemoryType.PROCEDURAL,
                importance=MemoryImportance.MEDIUM,
                source=f"project:{project.id}:task:{task.id}",
                tags=['task_completion', 'project', project.project_type.value, task.phase.value],
                metadata={
                    'project_id': project.id,
                    'project_title': project.title,
                    'task_id': task.id,
                    'task_title': task.title,
                    'task_phase': task.phase.value,
                    'completed_at': task.completed_at.isoformat() if task.completed_at else None
                }
            )

        except Exception as e:
            logger.error(f"Error storing task completion: {e}")

    async def calculate_project_progress(self, project_id: str) -> Dict[str, Any]:
        """Calculate overall project progress"""
        project = await self.get_project(project_id)
        if not project:
            return {"progress": 0, "completed_tasks": 0, "total_tasks": 0}

        completed_tasks = [t for t in project.tasks if t.status == "completed"]
        total_tasks = len(project.tasks)
        progress = (len(completed_tasks) / total_tasks * 100) if total_tasks > 0 else 0

        total_hours = sum(task.estimated_hours for task in project.tasks)
        completed_hours = sum(task.estimated_hours for task in completed_tasks)
        hours_progress = (completed_hours / total_hours * 100) if total_hours > 0 else 0

        return {
            "progress": progress,
            "completed_tasks": len(completed_tasks),
            "total_tasks": total_tasks,
            "completed_hours": completed_hours,
            "total_hours": total_hours,
            "by_phase": self._calculate_phase_progress(project.tasks)
        }

    def _calculate_phase_progress(self, tasks: List[ProjectTask]) -> Dict[str, float]:
        """Calculate progress by phase"""
        phase_progress = {}
        phases = {}

        for task in tasks:
            phase = task.phase.value
            if phase not in phases:
                phases[phase] = {"total": 0, "completed": 0}
            phases[phase]["total"] += 1
            if task.status == "completed":
                phases[phase]["completed"] += 1

        for phase, counts in phases.items():
            phase_progress[phase] = (counts["completed"] / counts["total"] * 100) if counts["total"] > 0 else 0

        return phase_progress


# Global instance
_project_planner: Optional[ProjectPlanner] = None


def get_project_planner(hybrid_agent=None, memory_system=None) -> ProjectPlanner:
    """Get or create global project planner instance"""
    global _project_planner
    if _project_planner is None:
        _project_planner = ProjectPlanner(hybrid_agent=hybrid_agent, memory_system=memory_system)
    return _project_planner
