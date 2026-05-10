
"""
Auto-Research Integration with Research Management System
Integrates persistence, wet lab, and thesis tracking with auto-research workflow.
"""
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import uuid

# Add project root dynamically for cross-platform compatibility
_project_root = Path(__file__).parent.parent.absolute()
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from modules.research_persistence import ResearchPersistenceManager
from modules.wetlab_coordinator import WetLabCoordinator, ExperimentType
from modules.thesis_tracker import ThesisMilestoneTracker
from modules.auto_research_orchestrator import (
    ResearchTopicDetector,
    AutoResearchOrchestrator,
    TodoListManager,
    AgentCommunicationBridge
)

logger = logging.getLogger(__name__)


class IntegratedResearchManager:
    """
    Integrated research manager combining auto-research with persistence,
    wet lab coordination, and thesis tracking.
    """

    def __init__(self):
        self.persistence = ResearchPersistenceManager()
        self.detector = ResearchTopicDetector()
        self.orchestrator = AutoResearchOrchestrator()
        self.todo_manager = TodoListManager()
        self.communication_bridge = AgentCommunicationBridge()

    def start_comprehensive_research(
        self,
        topic: str,
        user_message: str,
        context_id: str = None
    ) -> Dict[str, Any]:
        """
        Start comprehensive research with full integration.
        Returns research ID and initial state.
        """
        # Detect research type
        detection_result = self.detector.detect_research_topic(user_message)
        research_type = detection_result.get("research_type", "general")

        # Generate research ID
        research_id = f"{research_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Create research plan
        plan = self.orchestrator.planner.create_research_plan(
            topic=topic,
            research_type=research_type,
            context_id=context_id
        )

        # Initialize todo list from plan
        self.todo_manager.create_todo_list(
            research_id=research_id,
            tasks=plan.tasks,
            dependencies=plan.dependencies
        )

        # Save initial research state to persistence
        self.persistence.save_research_state(
            research_id=research_id,
            topic=topic,
            research_type=research_type,
            current_stage="planning",
            progress=0.05,
            tasks=[{
                "id": task["id"],
                "title": task["title"],
                "stage": task.get("stage", "unknown"),
                "status": task.get("status", "pending"),
                "priority": task.get("priority", 3),
                "description": task.get("description", "")
            } for task in plan.tasks]
        )

        # Initialize thesis for PhD or long-term research
        thesis_initialized = False
        if research_type in ["phd", "grand"]:
            thesis_tracker = ThesisMilestoneTracker(research_id)
            start_date = datetime.now()
            end_date = start_date + timedelta(days=730 if research_type == "grand" else 365)

            thesis_tracker.initialize_thesis(
                title=topic,
                degree_type="PhD" if research_type == "phd" else "Postdoc",
                field=self._infer_field(topic),
                start_date=start_date.isoformat(),
                expected_completion=end_date.isoformat()
            )
            thesis_initialized = True

        # Generate wet lab tasks if needed
        wetlab_tasks_generated = self._generate_wetlab_tasks(
            research_id=research_id,
            research_type=research_type,
            topic=topic
        )

        return {
            "research_id": research_id,
            "topic": topic,
            "research_type": research_type,
            "detection_confidence": detection_result.get("confidence", 0.0),
            "total_tasks": len(plan.tasks),
            "thesis_initialized": thesis_initialized,
            "wetlab_tasks_generated": wetlab_tasks_generated,
            "current_stage": "planning",
            "overall_progress": "5.0%",
            "next_steps": [
                "Review generated research plan",
                "Confirm thesis milestones (if applicable)",
                "Check wet lab experiment requirements (if applicable)",
                "Begin research execution"
            ]
        }

    def _infer_field(self, topic: str) -> str:
        """Infer research field from topic."""
        topic_lower = topic.lower()

        field_keywords = {
            "Pharmacology": ["drug", "pharmacology", "medication", "compound", "therapy"],
            "Neuroscience": ["alzheimer", "neuro", "brain", "cognitive", "dementia"],
            "Biochemistry": ["protein", "enzyme", "metabolism", "molecular"],
            "Immunology": ["immune", "antibody", "vaccine", "inflammation"],
            "Oncology": ["cancer", "tumor", "oncology", "chemotherapy"]
        }

        for field, keywords in field_keywords.items():
            if any(keyword in topic_lower for keyword in keywords):
                return field

        return "Pharmaceutical Sciences"

    def _generate_wetlab_tasks(
        self,
        research_id: str,
        research_type: str,
        topic: str
    ) -> int:
        """Generate wet lab tasks based on research type."""
        coordinator = WetLabCoordinator(research_id)

        generated = 0

        if research_type in ["phd", "grand", "review_article"]:
            # Generate initial wet lab experiment for validation
            experiment = coordinator.create_experiment(
                experiment_type=ExperimentType.CELL_CULTURE,
                title=f"Initial Validation for {topic[:50]}...",
                description=f"Preliminary cell culture experiments to validate approach for {topic}",
                objective="Establish proof-of-concept for research methodology",
                hypothesis=f"Proposed methodology will yield measurable results for {topic}",
                protocol={
                    "steps": [
                        "Culture relevant cell lines",
                        "Apply experimental conditions",
                        "Measure outcomes",
                        "Analyze data"
                    ]
                },
                required_materials=[
                    {"name": "Cell culture media", "quantity": "5L"},
                    {"name": "Cell lines", "quantity": "As specified"}
                ],
                equipment=["Cell culture incubator", "Microscope", "Plate reader"],
                safety_requirements=["Biosafety level 2"],
                estimated_duration="2 weeks",
                priority=4,
                deadline=(datetime.now() + timedelta(days=14)).isoformat()
            )

            generated += 1

            # Generate animal study task if PhD
            if research_type == "phd":
                experiment = coordinator.create_experiment(
                    experiment_type=ExperimentType.ANIMAL_STUDY,
                    title=f"In Vivo Study for {topic[:50]}...",
                    description=f"Animal model experiments for {topic}",
                    objective="Validate findings in animal model",
                    hypothesis=f"Results will translate to animal model for {topic}",
                    protocol={
                        "steps": [
                            "Select appropriate animal model",
                            "Administer experimental conditions",
                            "Monitor outcomes",
                            "Collect and analyze samples"
                        ]
                    },
                    required_materials=[
                        {"name": "Animal model", "quantity": "As specified"},
                        {"name": "Experimental compound", "quantity": "As specified"}
                    ],
                    equipment=["Animal housing", "Monitoring systems"],
                    safety_requirements=["IACUC approval required"],
                    estimated_duration="4 weeks",
                    priority=5,
                    deadline=(datetime.now() + timedelta(days=30)).isoformat()
                )

                generated += 1

        return generated

    async def execute_research_stage(
        self,
        research_id: str,
        stage_name: str,
        context_id: str = None
    ) -> Dict[str, Any]:
        """
        Execute a research stage and update persistence.
        """
        # Execute stage through orchestrator
        result = await self.orchestrator.execute_stage(
            stage_name=stage_name,
            research_id=research_id,
            context_id=context_id
        )

        # Update task status in persistence
        if "task_id" in result:
            self.persistence.update_task_status(
                research_id=research_id,
                task_id=result["task_id"],
                status="completed",
                result=result.get("output", "")
            )

        # Update overall progress
        self._update_progress(research_id)

        return result

    def _update_progress(self, research_id: str):
        """Update overall progress based on completed tasks."""
        state = self.persistence.load_research_state(research_id)
        if not state:
            return

        completed = sum(1 for t in state.tasks if t.get("status") == "completed")
        progress = completed / len(state.tasks) if state.tasks else 0.0

        # Save updated state
        self.persistence.save_research_state(
            research_id=research_id,
            topic=state.topic,
            research_type=state.research_type,
            current_stage=self._determine_current_stage(state),
            progress=progress,
            tasks=state.tasks
        )

    def _determine_current_stage(self, state) -> str:
        """Determine current stage based on completed tasks."""
        stages = ["planning", "literature_review", "methodology", "data_collection", "analysis"]

        for stage in stages:
            stage_tasks = [t for t in state.tasks if t.get("stage") == stage]
            if stage_tasks and any(t.get("status") != "completed" for t in stage_tasks):
                return stage

        return "completed"

    def resume_research(
        self,
        research_id: str,
        context_id: str = None
    ) -> Dict[str, Any]:
        """
        Resume research after absence.
        Provides comprehensive summary of what was done and what's needed.
        """
        # Get resume summary from persistence
        summary = self.persistence.get_resume_summary(research_id)

        if not summary:
            return {"error": "Research not found"}

        # Get wet lab status
        wetlab_coordinator = WetLabCoordinator(research_id)
        wetlab_summary = wetlab_coordinator.get_experiment_summary()
        summary["wetlab_status"] = wetlab_summary

        # Get thesis progress if applicable
        thesis_tracker = ThesisMilestoneTracker(research_id)
        if thesis_tracker.thesis:
            thesis_report = thesis_tracker.generate_thesis_report()
            summary["thesis_progress"] = thesis_report

        # Get todo list status
        todo_list = self.todo_manager.get_todo_list(research_id)
        summary["todo_list"] = todo_list

        return summary

    def submit_wetlab_results(
        self,
        research_id: str,
        experiment_id: str,
        submission_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Submit wet lab experiment results.
        """
        from modules.wetlab_coordinator import ExperimentSubmission

        submission = ExperimentSubmission(
            experiment_id=experiment_id,
            submitted_by="User",
            submitted_at=datetime.now().isoformat(),
            results=submission_data.get("results", {}),
            data_files=submission_data.get("data_files", []),
            observations=submission_data.get("observations", ""),
            conclusions=submission_data.get("conclusions", ""),
            unexpected_outcomes=submission_data.get("unexpected_outcomes", []),
            next_steps=submission_data.get("next_steps", []),
            quality_metrics=submission_data.get("quality_metrics", {}),
            compliance_notes=submission_data.get("compliance_notes", [])
        )

        coordinator = WetLabCoordinator(research_id)
        success = coordinator.submit_results(submission)

        if success:
            # Update research state with new results
            self._update_progress(research_id)

            return {
                "status": "success",
                "message": "Wet lab results submitted successfully",
                "experiment_id": experiment_id
            }
        else:
            return {
                "status": "error",
                "message": "Failed to submit results"
            }

    def get_comprehensive_dashboard(
        self,
        research_id: str
    ) -> Dict[str, Any]:
        """
        Get comprehensive dashboard with all research information.
        """
        dashboard = {
            "research_id": research_id,
            "timestamp": datetime.now().isoformat()
        }

        # Research state
        state = self.persistence.load_research_state(research_id)
        if state:
            dashboard["research"] = {
                "topic": state.topic,
                "research_type": state.research_type,
                "current_stage": state.current_stage,
                "progress": f"{state.progress * 100:.1f}%",
                "total_tasks": len(state.tasks),
                "completed_tasks": len(state.completed_tasks)
            }

        # Wet lab status
        wetlab_coordinator = WetLabCoordinator(research_id)
        dashboard["wetlab"] = wetlab_coordinator.get_experiment_summary()

        # Thesis progress
        thesis_tracker = ThesisMilestoneTracker(research_id)
        if thesis_tracker.thesis:
            dashboard["thesis"] = thesis_tracker.generate_thesis_report()

        # Todo list
        dashboard["todo_list"] = self.todo_manager.get_todo_list(research_id)

        return dashboard
