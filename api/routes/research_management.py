"""
Integrated Research Management API
Provides endpoints for research persistence, wet lab coordination, and thesis tracking.
Follows international pharmaceutical research standards.
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
import uuid
import os
import sys

# Add project root dynamically for cross-platform compatibility
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from modules.research_persistence import (
    ResearchPersistenceManager,
    ResearchState
)
from modules.wetlab_coordinator import (
    WetLabCoordinator,
    ExperimentType,
    ExperimentStatus,
    WetLabExperiment,
    ExperimentSubmission
)
from modules.thesis_tracker import (
    ThesisMilestoneTracker,
    ThesisProject,
    ThesisMilestone,
    MilestoneType,
    MilestoneStatus
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/research/management", tags=["research_management"])

# Initialize managers
persistence_manager = ResearchPersistenceManager()


# ============= Research Persistence Endpoints =============

class SaveResearchStateRequest(BaseModel):
    research_id: str = Field(..., description="Unique research identifier")
    topic: str = Field(..., description="Research topic/title")
    research_type: str = Field(..., description="Type: phd, grand, review_article, general")
    current_stage: str = Field(..., description="Current research stage")
    progress: float = Field(..., description="Progress 0.0-1.0", ge=0.0, le=1.0)
    tasks: List[Dict[str, Any]] = Field(..., description="List of research tasks")


@router.post("/save", response_model=Dict[str, str])
async def save_research_state(request: SaveResearchStateRequest):
    """Save research state to persistent storage."""
    try:
        filepath = persistence_manager.save_research_state(
            research_id=request.research_id,
            topic=request.topic,
            research_type=request.research_type,
            current_stage=request.current_stage,
            progress=request.progress,
            tasks=request.tasks
        )
        return {
            "status": "success",
            "message": "Research state saved",
            "filepath": filepath,
            "research_id": request.research_id
        }
    except Exception as e:
        logger.error(f"Failed to save research state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/load/{research_id}", response_model=Dict[str, Any])
async def load_research_state(research_id: str):
    """Load research state from persistent storage."""
    state = persistence_manager.load_research_state(research_id)
    if not state:
        raise HTTPException(status_code=404, detail="Research not found")

    return {
        "status": "success",
        "research_id": state.research_id,
        "topic": state.topic,
        "research_type": state.research_type,
        "current_stage": state.current_stage,
        "progress": state.progress,
        "tasks": state.tasks,
        "created_at": state.created_at,
        "last_updated": state.last_updated
    }


@router.get("/list", response_model=List[Dict[str, Any]])
async def list_all_research():
    """List all saved research projects."""
    research_list = persistence_manager.list_all_research()
    return research_list


@router.get("/resume/{research_id}", response_model=Dict[str, Any])
async def get_resume_summary(research_id: str):
    """
    Get resume summary for research.
    Shows what was done, what's needed, where to continue.
    """
    summary = persistence_manager.get_resume_summary(research_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Research not found")
    return summary


@router.put("/task/{research_id}/{task_id}", response_model=Dict[str, str])
async def update_task_status(
    research_id: str,
    task_id: str,
    status: str,
    result: Optional[str] = None
):
    """Update task status in research."""
    success = persistence_manager.update_task_status(
        research_id=research_id,
        task_id=task_id,
        status=status,
        result=result
    )

    if not success:
        raise HTTPException(status_code=404, detail="Research or task not found")

    return {"status": "success", "message": "Task status updated"}


# ============= Wet Lab Coordination Endpoints =============

class CreateExperimentRequest(BaseModel):
    research_id: str = Field(..., description="Associated research ID")
    experiment_type: str = Field(..., description="Type of experiment")
    title: str = Field(..., description="Experiment title")
    description: str = Field(..., description="Detailed description")
    objective: str = Field(..., description="Research objective")
    hypothesis: str = Field(..., description="Research hypothesis")
    protocol: Dict[str, Any] = Field(..., description="Experimental protocol")
    required_materials: List[Dict[str, Any]] = Field(..., description="Materials needed")
    equipment: List[str] = Field(..., description="Equipment needed")
    safety_requirements: List[str] = Field(..., description="Safety requirements")
    estimated_duration: str = Field(..., description="Estimated time to complete")
    priority: int = Field(default=3, ge=1, le=5, description="Priority 1-5")
    dependencies: List[str] = Field(default_factory=list, description="Dependency IDs")
    deadline: Optional[str] = Field(None, description="Deadline ISO format")


class AssignExperimentRequest(BaseModel):
    experiment_id: str = Field(..., description="Experiment ID")
    assigned_to: str = Field(..., description="Person/Team assigned")
    notes: Optional[str] = Field(None, description="Assignment notes")


class SubmitResultsRequest(BaseModel):
    experiment_id: str = Field(..., description="Experiment ID")
    submitted_by: str = Field(..., description="Who submitted")
    results: Dict[str, Any] = Field(..., description="Experiment results")
    data_files: List[Dict[str, str]] = Field(default_factory=list, description="Attached data files")
    observations: str = Field(..., description="Key observations")
    conclusions: str = Field(..., description="Conclusions drawn")
    unexpected_outcomes: List[str] = Field(default_factory=list, description="Unexpected findings")
    next_steps: List[str] = Field(default_factory=list, description="Suggested next steps")
    quality_metrics: Dict[str, Any] = Field(default_factory=dict, description="Quality metrics")
    compliance_notes: List[str] = Field(default_factory=list, description="Compliance notes")


class ReviewSubmissionRequest(BaseModel):
    experiment_id: str = Field(..., description="Experiment ID")
    approved: bool = Field(..., description="Approve or reject")
    review_comments: List[str] = Field(default_factory=list, description="Review feedback")


@router.post("/wetlab/create", response_model=Dict[str, Any])
async def create_wetlab_experiment(request: CreateExperimentRequest):
    """Create new wet lab experiment."""
    try:
        coordinator = WetLabCoordinator(request.research_id)

        experiment = coordinator.create_experiment(
            experiment_type=ExperimentType(request.experiment_type),
            title=request.title,
            description=request.description,
            objective=request.objective,
            hypothesis=request.hypothesis,
            protocol=request.protocol,
            required_materials=request.required_materials,
            equipment=request.equipment,
            safety_requirements=request.safety_requirements,
            estimated_duration=request.estimated_duration,
            priority=request.priority,
            dependencies=request.dependencies,
            deadline=request.deadline
        )

        return {
            "status": "success",
            "message": "Experiment created",
            "experiment_id": experiment.experiment_id,
            "research_id": request.research_id
        }
    except Exception as e:
        logger.error(f"Failed to create experiment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/wetlab/assign", response_model=Dict[str, str])
async def assign_experiment(request: AssignExperimentRequest):
    """Assign experiment to lab personnel."""
    # Need research_id to get coordinator
    research_id = request.experiment_id.split("_")[0] if "_" in request.experiment_id else "default"

    coordinator = WetLabCoordinator(research_id)
    success = coordinator.assign_experiment(
        experiment_id=request.experiment_id,
        assigned_to=request.assigned_to,
        notes=request.notes
    )

    if not success:
        raise HTTPException(status_code=404, detail="Experiment not found")

    return {"status": "success", "message": "Experiment assigned"}


@router.post("/wetlab/start/{experiment_id}", response_model=Dict[str, str])
async def start_experiment(experiment_id: str, started_by: str):
    """Mark experiment as started."""
    research_id = experiment_id.split("_")[0] if "_" in experiment_id else "default"

    coordinator = WetLabCoordinator(research_id)
    success = coordinator.start_experiment(
        experiment_id=experiment_id,
        started_by=started_by
    )

    if not success:
        raise HTTPException(status_code=404, detail="Experiment not found")

    return {"status": "success", "message": "Experiment started"}


@router.post("/wetlab/submit", response_model=Dict[str, str])
async def submit_experiment_results(request: SubmitResultsRequest):
    """Submit experiment results."""
    submission = ExperimentSubmission(
        experiment_id=request.experiment_id,
        submitted_by=request.submitted_by,
        submitted_at=datetime.now().isoformat(),
        results=request.results,
        data_files=request.data_files,
        observations=request.observations,
        conclusions=request.conclusions,
        unexpected_outcomes=request.unexpected_outcomes,
        next_steps=request.next_steps,
        quality_metrics=request.quality_metrics,
        compliance_notes=request.compliance_notes
    )

    research_id = request.experiment_id.split("_")[0] if "_" in request.experiment_id else "default"
    coordinator = WetLabCoordinator(research_id)
    success = coordinator.submit_results(submission)

    if not success:
        raise HTTPException(status_code=404, detail="Experiment not found")

    return {"status": "success", "message": "Results submitted"}


@router.post("/wetlab/review", response_model=Dict[str, str])
async def review_submission(request: ReviewSubmissionRequest):
    """Review submitted experiment results."""
    research_id = request.experiment_id.split("_")[0] if "_" in request.experiment_id else "default"
    coordinator = WetLabCoordinator(research_id)
    success = coordinator.review_submission(
        experiment_id=request.experiment_id,
        approved=request.approved,
        review_comments=request.review_comments
    )

    if not success:
        raise HTTPException(status_code=404, detail="Experiment not found")

    return {"status": "success", "message": "Review completed"}


@router.get("/wetlab/pending/{research_id}", response_model=List[Dict[str, Any]])
async def get_pending_assignments(research_id: str):
    """Get experiments waiting for assignment."""
    coordinator = WetLabCoordinator(research_id)
    experiments = coordinator.get_pending_assignments()
    return [
        {
            "experiment_id": exp.experiment_id,
            "title": exp.title,
            "type": exp.experiment_type.value,
            "description": exp.description,
            "priority": exp.priority,
            "deadline": exp.deadline
        }
        for exp in experiments
    ]


@router.get("/wetlab/progress/{research_id}", response_model=List[Dict[str, Any]])
async def get_in_progress_experiments(research_id: str):
    """Get experiments currently in progress."""
    coordinator = WetLabCoordinator(research_id)
    experiments = coordinator.get_in_progress_experiments()
    return [
        {
            "experiment_id": exp.experiment_id,
            "title": exp.title,
            "type": exp.experiment_type.value,
            "assigned_to": exp.assigned_to,
            "started_at": exp.started_at,
            "status": exp.status.value
        }
        for exp in experiments
    ]


@router.get("/wetlab/summary/{research_id}", response_model=Dict[str, Any])
async def get_experiment_summary(research_id: str):
    """Get summary of all experiments."""
    coordinator = WetLabCoordinator(research_id)
    return coordinator.get_experiment_summary()


@router.get("/wetlab/request/{experiment_id}", response_model=Dict[str, Any])
async def generate_lab_request(experiment_id: str):
    """Generate lab request document."""
    research_id = experiment_id.split("_")[0] if "_" in experiment_id else "default"
    coordinator = WetLabCoordinator(research_id)
    request = coordinator.generate_lab_request(experiment_id)

    if not request:
        raise HTTPException(status_code=404, detail="Experiment not found")

    return request


# ============= Thesis Milestone Tracking Endpoints =============

class InitializeThesisRequest(BaseModel):
    research_id: str = Field(..., description="Associated research ID")
    title: str = Field(..., description="Thesis title")
    degree_type: str = Field(..., description="Degree: PhD, Masters, etc.")
    field: str = Field(..., description="Research field")
    start_date: str = Field(..., description="Start date ISO format")
    expected_completion: str = Field(..., description="Expected completion ISO format")
    advisor: Optional[str] = Field(None, description="Thesis advisor")
    committee_members: List[str] = Field(default_factory=list, description="Committee members")


class UpdateMilestoneRequest(BaseModel):
    research_id: str = Field(..., description="Research ID")
    milestone_id: str = Field(..., description="Milestone ID")
    status: str = Field(..., description="New status")
    progress: Optional[float] = Field(None, ge=0.0, le=1.0, description="Progress 0.0-1.0")
    notes: Optional[str] = Field(None, description="Update notes")


@router.post("/thesis/initialize", response_model=Dict[str, Any])
async def initialize_thesis(request: InitializeThesisRequest):
    """Initialize new thesis project with default milestones."""
    try:
        tracker = ThesisMilestoneTracker(request.research_id)
        thesis = tracker.initialize_thesis(
            title=request.title,
            degree_type=request.degree_type,
            field=request.field,
            start_date=request.start_date,
            expected_completion=request.expected_completion,
            advisor=request.advisor,
            committee_members=request.committee_members
        )

        return {
            "status": "success",
            "message": "Thesis initialized",
            "thesis_id": thesis.thesis_id,
            "research_id": request.research_id
        }
    except Exception as e:
        logger.error(f"Failed to initialize thesis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/thesis/milestone", response_model=Dict[str, str])
async def update_milestone_status(request: UpdateMilestoneRequest):
    """Update milestone status."""
    tracker = ThesisMilestoneTracker(request.research_id)
    success = tracker.update_milestone_status(
        milestone_id=request.milestone_id,
        status=MilestoneStatus(request.status),
        progress=request.progress,
        notes=request.notes
    )

    if not success:
        raise HTTPException(status_code=404, detail="Milestone not found")

    return {"status": "success", "message": "Milestone updated"}


@router.get("/thesis/deadlines/{research_id}", response_model=List[Dict[str, Any]])
async def get_upcoming_deadlines(
    research_id: str,
    days: int = 30
):
    """Get upcoming milestones within specified days."""
    tracker = ThesisMilestoneTracker(research_id)
    deadlines = tracker.get_upcoming_deadlines(days)
    return deadlines


@router.get("/thesis/progress/{research_id}", response_model=Dict[str, Any])
async def get_milestone_progress(research_id: str):
    """Get detailed progress of all milestones."""
    tracker = ThesisMilestoneTracker(research_id)
    progress = tracker.get_milestone_progress()

    if not progress:
        raise HTTPException(status_code=404, detail="Thesis not found")

    return progress


@router.get("/thesis/delayed/{research_id}", response_model=List[Dict[str, Any]])
async def get_delayed_milestones(research_id: str):
    """Get milestones that are past deadline."""
    tracker = ThesisMilestoneTracker(research_id)
    delayed = tracker.get_delayed_milestones()
    return delayed


@router.get("/thesis/report/{research_id}", response_model=Dict[str, Any])
async def generate_thesis_report(research_id: str):
    """Generate comprehensive thesis progress report."""
    tracker = ThesisMilestoneTracker(research_id)
    report = tracker.generate_thesis_report()

    if not report:
        raise HTTPException(status_code=404, detail="Thesis not found")

    return report


# ============= Comprehensive Research Dashboard Endpoints =============

@router.get("/dashboard/{research_id}", response_model=Dict[str, Any])
async def get_research_dashboard(research_id: str):
    """
    Get comprehensive research dashboard including:
    - Research state and progress
    - Wet lab experiment status
    - Thesis milestone progress
    - Resume summary if returning after absence
    """
    dashboard = {
        "research_id": research_id,
        "timestamp": datetime.now().isoformat()
    }

    # Research state
    state = persistence_manager.load_research_state(research_id)
    if state:
        dashboard["research"] = {
            "topic": state.topic,
            "research_type": state.research_type,
            "current_stage": state.current_stage,
            "progress": f"{state.progress * 100:.1f}%",
            "total_tasks": len(state.tasks),
            "completed_tasks": len(state.completed_tasks),
            "last_updated": state.last_updated
        }

    # Wet lab status
    wetlab_coordinator = WetLabCoordinator(research_id)
    wetlab_summary = wetlab_coordinator.get_experiment_summary()
    dashboard["wetlab"] = wetlab_summary

    # Thesis progress
    thesis_tracker = ThesisMilestoneTracker(research_id)
    if thesis_tracker.thesis:
        thesis_report = thesis_tracker.generate_thesis_report()
        dashboard["thesis"] = thesis_report

    # Resume summary
    resume_summary = persistence_manager.get_resume_summary(research_id)
    if resume_summary:
        dashboard["resume_summary"] = resume_summary

    return dashboard


@router.post("/comprehensive/initialize", response_model=Dict[str, Any])
async def initialize_comprehensive_research(
    research_id: str,
    topic: str,
    research_type: str,
    thesis_title: str,
    degree_type: str,
    field: str,
    start_date: str,
    expected_completion: str,
    advisor: Optional[str] = None
):
    """
    Initialize comprehensive research including:
    - Research state
    - Thesis project with milestones
    """
    results = {
        "research_id": research_id,
        "timestamp": datetime.now().isoformat()
    }

    # Initialize research state with initial planning
    initial_tasks = [
        {
            "id": "t_001",
            "title": "Research Planning",
            "stage": "planning",
            "status": "in_progress",
            "priority": 5,
            "description": "Create comprehensive research plan"
        },
        {
            "id": "t_002",
            "title": "Literature Review",
            "stage": "literature_review",
            "status": "pending",
            "priority": 4,
            "description": "Conduct systematic literature review"
        }
    ]

    persistence_manager.save_research_state(
        research_id=research_id,
        topic=topic,
        research_type=research_type,
        current_stage="planning",
        progress=0.05,
        tasks=initial_tasks
    )
    results["research_state"] = "initialized"

    # Initialize thesis
    thesis_tracker = ThesisMilestoneTracker(research_id)
    thesis_tracker.initialize_thesis(
        title=thesis_title,
        degree_type=degree_type,
        field=field,
        start_date=start_date,
        expected_completion=expected_completion,
        advisor=advisor
    )
    results["thesis"] = "initialized"

    return results


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "research_management_api",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "persistence": "operational",
            "wetlab_coordinator": "operational",
            "thesis_tracker": "operational"
        }
    }
