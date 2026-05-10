"""
Thesis Milestone Tracker
Manages year-long thesis projects with milestones, deadlines, and progress tracking.
Follows pharmaceutical research standards for PhD and research projects.
"""
import logging
import os
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
import json

logger = logging.getLogger(__name__)

class MilestoneType(Enum):
    """Types of thesis milestones."""
    PLANNING = "planning"
    LITERATURE_REVIEW = "literature_review"
    METHODOLOGY_DESIGN = "methodology_design"
    DATA_COLLECTION = "data_collection"
    DATA_ANALYSIS = "data_analysis"
    RESULTS_INTERPRETATION = "results_interpretation"
    WRITING_DRAFT = "writing_draft"
    REVIEW_REVISION = "review_revision"
    FINAL_SUBMISSION = "final_submission"
    DEFENSE_PREPARATION = "defense_preparation"


class MilestoneStatus(Enum):
    """Status of milestone completion."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DELAYED = "delayed"
    ON_HOLD = "on_hold"
    CANCELLED = "cancelled"


@dataclass
class ThesisMilestone:
    """Thesis milestone definition."""
    milestone_id: str
    milestone_type: MilestoneType
    title: str
    description: str
    objectives: List[str]
    deliverables: List[str]
    start_date: str
    deadline: str
    status: MilestoneStatus = MilestoneStatus.NOT_STARTED
    progress: float = 0.0
    required_tasks: List[str] = field(default_factory=list)
    completed_tasks: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    assigned_to: Optional[str] = None
    notes: List[str] = field(default_factory=list)
    review_comments: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ThesisProject:
    """Complete thesis project."""
    thesis_id: str
    research_id: str
    title: str
    degree_type: str  # PhD, Master's, etc.
    field: str  # e.g., Pharmacology, Neuroscience
    start_date: str
    expected_completion: str
    advisor: Optional[str] = None
    committee_members: List[str] = field(default_factory=list)
    milestones: Dict[str, ThesisMilestone] = field(default_factory=dict)
    overall_progress: float = 0.0
    current_milestone: Optional[str] = None
    thesis_document_path: Optional[str] = None
    status: str = "active"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class ThesisMilestoneTracker:
    """
    Tracks thesis milestones for year-long research projects.
    Manages deadlines, dependencies, and progress tracking.
    """

    def __init__(self, research_id: str, storage_path: str = None):
        self.research_id = research_id
        if storage_path is None:
            # Use environment variable or default to a platform-independent path
            base_path = os.environ.get('BIODOCKIFY_DATA_DIR')
            if base_path is None:
                # Default to a data subdirectory in the project root
                base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'research_state')
            storage_path = base_path

        self.storage_path = os.path.join(storage_path, f"{research_id}_thesis.json")
        self.thesis: Optional[ThesisProject] = None
        self.load_thesis()

    def load_thesis(self):
        """Load thesis from storage."""
        if os.path.exists(self.storage_path):
            with open(self.storage_path, 'r') as f:
                data = json.load(f)

            # Convert milestone data
            milestones = {}
            for mid, mdata in data["milestones"].items():
                mdata["milestone_type"] = MilestoneType(mdata["milestone_type"])
                mdata["status"] = MilestoneStatus(mdata["status"])
                milestones[mid] = ThesisMilestone(**mdata)

            data["milestones"] = milestones
            self.thesis = ThesisProject(**data)

    def save_thesis(self):
        """Save thesis to storage."""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)

        data = asdict(self.thesis)

        # Convert milestone enums to strings
        for mid, mdata in data["milestones"].items():
            mdata["milestone_type"] = self.thesis.milestones[mid].milestone_type.value
            mdata["status"] = self.thesis.milestones[mid].status.value

        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=2)

    def initialize_thesis(
        self,
        title: str,
        degree_type: str,
        field: str,
        start_date: str,
        expected_completion: str,
        advisor: str = None,
        committee_members: List[str] = None
    ) -> ThesisProject:
        """Initialize new thesis project with default milestones."""
        thesis_id = f"thesis_{self.research_id}"

        self.thesis = ThesisProject(
            thesis_id=thesis_id,
            research_id=self.research_id,
            title=title,
            degree_type=degree_type,
            field=field,
            start_date=start_date,
            expected_completion=expected_completion,
            advisor=advisor,
            committee_members=committee_members or []
        )

        # Create default milestones for year-long project
        self._create_default_milestones()

        self.save_thesis()
        logger.info(f"Initialized thesis project: {thesis_id}")
        return self.thesis

    def _create_default_milestones(self):
        """Create default milestones for year-long thesis."""
        # Calculate milestone dates (spread over 12 months)
        start = datetime.fromisoformat(self.thesis.start_date)
        end = datetime.fromisoformat(self.thesis.expected_completion)
        total_days = (end - start).days

        milestones_config = [
            (MilestoneType.PLANNING, "Research Planning", 0.0, 0.1, [
                "Define research questions",
                "Develop hypothesis",
                "Create study design",
                "Submit ethics approval"
            ]),
            (MilestoneType.LITERATURE_REVIEW, "Literature Review", 0.1, 0.25, [
                "Conduct systematic search",
                "Screen and select studies",
                "Extract and analyze data",
                "Write literature review chapter"
            ]),
            (MilestoneType.METHODOLOGY_DESIGN, "Methodology Design", 0.25, 0.4, [
                "Design experimental protocols",
                "Select animal models",
                "Prepare reagents and materials",
                "Establish quality control procedures"
            ]),
            (MilestoneType.DATA_COLLECTION, "Data Collection", 0.4, 0.65, [
                "Execute wet lab experiments",
                "Collect animal study data",
                "Perform drug screening",
                "Document all procedures"
            ]),
            (MilestoneType.DATA_ANALYSIS, "Data Analysis", 0.65, 0.8, [
                "Statistical analysis",
                "Meta-analysis if applicable",
                "Data visualization",
                "Interpret results"
            ]),
            (MilestoneType.RESULTS_INTERPRETATION, "Results Interpretation", 0.8, 0.9, [
                "Write results chapter",
                "Interpret findings",
                "Compare with literature",
                "Identify implications"
            ]),
            (MilestoneType.WRITING_DRAFT, "Draft Writing", 0.9, 0.95, [
                "Write introduction",
                "Write methods section",
                "Write discussion",
                "Create figures and tables"
            ]),
            (MilestoneType.REVIEW_REVISION, "Review and Revision", 0.95, 0.98, [
                "Advisor review",
                "Committee feedback",
                "Incorporate revisions",
                "Finalize thesis document"
            ]),
            (MilestoneType.FINAL_SUBMISSION, "Final Submission", 0.98, 1.0, [
                "Submit thesis to committee",
                "Prepare presentation",
                "Submit to university"
            ]),
            (MilestoneType.DEFENSE_PREPARATION, "Defense Preparation", 0.98, 1.0, [
                "Prepare defense slides",
                "Practice presentation",
                "Prepare for questions",
                "Final defense"
            ])
        ]

        for i, (mtype, mtitle, start_pct, end_pct, objectives) in enumerate(milestones_config):
            start_days = int(total_days * start_pct)
            end_days = int(total_days * end_pct)

            milestone = ThesisMilestone(
                milestone_id=f"m_{i+1}",
                milestone_type=mtype,
                title=mtitle,
                description=f"{mtitle} for {self.thesis.title}",
                objectives=objectives,
                deliverables=[
                    f"{obj} report" for obj in objectives
                ],
                start_date=(start + timedelta(days=start_days)).isoformat(),
                deadline=(start + timedelta(days=end_days)).isoformat()
            )

            self.thesis.milestones[milestone.milestone_id] = milestone

    def update_milestone_status(
        self,
        milestone_id: str,
        status: MilestoneStatus,
        progress: float = None,
        notes: str = None
    ) -> bool:
        """Update milestone status."""
        if not self.thesis or milestone_id not in self.thesis.milestones:
            return False

        milestone = self.thesis.milestones[milestone_id]
        milestone.status = status
        milestone.updated_at = datetime.now().isoformat()

        if progress is not None:
            milestone.progress = progress

        if notes:
            milestone.notes.append(notes)

        # Recalculate overall progress
        self._calculate_overall_progress()

        # Update current milestone
        self._update_current_milestone()

        self.save_thesis()
        return True

    def _calculate_overall_progress(self):
        """Calculate overall thesis progress."""
        if not self.thesis:
            return

        total_progress = sum(
            m.progress for m in self.thesis.milestones.values()
        )

        if self.thesis.milestones:
            self.thesis.overall_progress = total_progress / len(self.thesis.milestones)

    def _update_current_milestone(self):
        """Update current milestone based on status."""
        if not self.thesis:
            return

        for mid, milestone in sorted(self.thesis.milestones.items()):
            if milestone.status in [MilestoneStatus.NOT_STARTED, MilestoneStatus.IN_PROGRESS]:
                self.thesis.current_milestone = mid
                return

        self.thesis.current_milestone = None

    def get_upcoming_deadlines(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get upcoming milestones within specified days."""
        if not self.thesis:
            return []

        today = datetime.now()
        cutoff = today + timedelta(days=days)

        upcoming = []
        for mid, milestone in self.thesis.milestones.items():
            deadline = datetime.fromisoformat(milestone.deadline)

            if today <= deadline <= cutoff:
                days_until = (deadline - today).days
                upcoming.append({
                    "milestone_id": mid,
                    "title": milestone.title,
                    "deadline": milestone.deadline,
                    "days_until": days_until,
                    "status": milestone.status.value,
                    "progress": milestone.progress
                })

        return sorted(upcoming, key=lambda x: x["days_until"])

    def get_milestone_progress(self) -> Dict[str, Any]:
        """Get detailed progress of all milestones."""
        if not self.thesis:
            return {}

        progress_data = {
            "thesis_title": self.thesis.title,
            "overall_progress": f"{self.thesis.overall_progress * 100:.1f}%",
            "current_milestone": self.thesis.current_milestone,
            "total_milestones": len(self.thesis.milestones),
            "completed_milestones": sum(
                1 for m in self.thesis.milestones.values()
                if m.status == MilestoneStatus.COMPLETED
            ),
            "milestones": []
        }

        for mid, milestone in self.thesis.milestones.items():
            deadline = datetime.fromisoformat(milestone.deadline)
            today = datetime.now()
            days_until = (deadline - today).days
            is_overdue = days_until < 0 and milestone.status != MilestoneStatus.COMPLETED

            progress_data["milestones"].append({
                "id": mid,
                "title": milestone.title,
                "type": milestone.milestone_type.value,
                "description": milestone.description,
                "status": milestone.status.value,
                "progress": f"{milestone.progress * 100:.1f}%",
                "start_date": milestone.start_date,
                "deadline": milestone.deadline,
                "days_until": days_until,
                "is_overdue": is_overdue,
                "objectives_completed": len(milestone.completed_tasks),
                "objectives_total": len(milestone.required_tasks)
            })

        return progress_data

    def get_delayed_milestones(self) -> List[Dict[str, Any]]:
        """Get milestones that are past deadline and not completed."""
        if not self.thesis:
            return []

        today = datetime.now()
        delayed = []

        for mid, milestone in self.thesis.milestones.items():
            deadline = datetime.fromisoformat(milestone.deadline)
            days_overdue = (today - deadline).days

            if days_overdue > 0 and milestone.status != MilestoneStatus.COMPLETED:
                delayed.append({
                    "milestone_id": mid,
                    "title": milestone.title,
                    "deadline": milestone.deadline,
                    "days_overdue": days_overdue,
                    "status": milestone.status.value,
                    "progress": milestone.progress
                })

        return sorted(delayed, key=lambda x: x["days_overdue"], reverse=True)

    def generate_thesis_report(self) -> Dict[str, Any]:
        """Generate comprehensive thesis progress report."""
        if not self.thesis:
            return {}

        upcoming = self.get_upcoming_deadlines(30)
        delayed = self.get_delayed_milestones()
        progress = self.get_milestone_progress()

        today = datetime.now()
        start = datetime.fromisoformat(self.thesis.start_date)
        end = datetime.fromisoformat(self.thesis.expected_completion)

        days_elapsed = (today - start).days
        days_remaining = (end - today).days
        total_days = (end - start).days

        time_progress = min(days_elapsed / total_days, 1.0)
        work_progress = self.thesis.overall_progress

        # Check if on track
        on_track = abs(time_progress - work_progress) < 0.1

        return {
            "thesis_info": {
                "title": self.thesis.title,
                "degree_type": self.thesis.degree_type,
                "field": self.thesis.field,
                "advisor": self.thesis.advisor,
                "committee_members": self.thesis.committee_members
            },
            "timeline": {
                "start_date": self.thesis.start_date,
                "expected_completion": self.thesis.expected_completion,
                "days_elapsed": days_elapsed,
                "days_remaining": days_remaining,
                "total_duration_days": total_days,
                "time_progress": f"{time_progress * 100:.1f}%",
                "work_progress": f"{work_progress * 100:.1f}%",
                "on_track": on_track
            },
            "progress": progress,
            "upcoming_deadlines": upcoming,
            "delayed_milestones": delayed,
            "overall_status": self._get_overall_status(),
            "recommendations": self._generate_recommendations()
        }

    def _get_overall_status(self) -> str:
        """Get overall thesis status."""
        if not self.thesis:
            return "unknown"

        delayed = self.get_delayed_milestones()

        if len(delayed) > 2:
            return "critical"
        elif len(delayed) > 0:
            return "at_risk"
        elif self.thesis.overall_progress >= 0.9:
            return "final_stages"
        elif self.thesis.overall_progress >= 0.5:
            return "on_track"
        else:
            return "early_stages"

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on current status."""
        recommendations = []

        if not self.thesis:
            return recommendations

        delayed = self.get_delayed_milestones()
        upcoming = self.get_upcoming_deadlines(30)

        # Check for delayed milestones
        if delayed:
            recommendations.append(f"URGENT: {len(delayed)} milestone(s) are overdue")
            recommendations.append("Review timeline and consider adjusting deadlines")

        # Check for upcoming deadlines
        if upcoming:
            recommendations.append(f"{len(upcoming)} milestone(s) due within 30 days")

        # Check progress alignment
        today = datetime.now()
        start = datetime.fromisoformat(self.thesis.start_date)
        end = datetime.fromisoformat(self.thesis.expected_completion)
        days_elapsed = (today - start).days
        total_days = (end - start).days
        time_progress = min(days_elapsed / total_days, 1.0)

        if self.thesis.overall_progress < time_progress - 0.15:
            recommendations.append("Work is behind schedule - consider increasing effort")
        elif self.thesis.overall_progress > time_progress + 0.15:
            recommendations.append("Work is ahead of schedule - maintain current pace")
        else:
            recommendations.append("Work is on track - continue current approach")

        # Specific recommendations based on stage
        if self.thesis.overall_progress < 0.25:
            recommendations.append("Focus on completing planning and literature review")
        elif self.thesis.overall_progress < 0.5:
            recommendations.append("Emphasize methodology design and preparation")
        elif self.thesis.overall_progress < 0.75:
            recommendations.append("Prioritize data collection and experiments")
        elif self.thesis.overall_progress < 0.9:
            recommendations.append("Focus on analysis and interpretation")
        else:
            recommendations.append("Concentrate on writing and final preparations")

        return recommendations
