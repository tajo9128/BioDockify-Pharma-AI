"""
Wet Lab Integration System
Manages wet lab and animal study tasks for pharmaceutical research.
Coordinates between BioDockify AI and physical lab work.
"""
import logging
import os
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
import json

logger = logging.getLogger(__name__)

class ExperimentType(Enum):
    """Types of wet lab experiments."""
    CELL_CULTURE = "cell_culture"
    ANIMAL_STUDY = "animal_study"
    DRUG_SCREENING = "drug_screening"
    MOLECULAR_BIOLOGY = "molecular_biology"
    BIOCHEMISTRY = "biochemistry"
    IMMUNOLOGY = "immunology"
    MICROBIOLOGY = "microbiology"
    PHARMACOLOGY = "pharmacology"


class ExperimentStatus(Enum):
    """Status of experiment execution."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    AWAITING_REVIEW = "awaiting_review"


@dataclass
class WetLabExperiment:
    """Wet lab experiment definition."""
    experiment_id: str
    experiment_type: ExperimentType
    title: str
    description: str
    objective: str
    hypothesis: str
    protocol: Dict[str, Any]
    required_materials: List[Dict[str, Any]]
    equipment: List[str]
    safety_requirements: List[str]
    estimated_duration: str
    assigned_to: Optional[str] = None
    status: ExperimentStatus = ExperimentStatus.PENDING
    priority: int = 3  # 1-5, 5 = critical
    dependencies: List[str] = field(default_factory=list)
    deadline: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    assigned_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    submission: Optional[Dict[str, Any]] = None
    review_comments: List[str] = field(default_factory=list)


@dataclass
class ExperimentSubmission:
    """Submission data from wet lab work."""
    experiment_id: str
    submitted_by: str
    submitted_at: str
    results: Dict[str, Any]
    data_files: List[Dict[str, str]]
    observations: str
    conclusions: str
    unexpected_outcomes: List[str]
    next_steps: List[str]
    quality_metrics: Dict[str, Any]
    compliance_notes: List[str]


class WetLabCoordinator:
    """
    Coordinates wet lab experiments and animal studies.
    Manages experiment assignment, progress tracking, and result submission.
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

        self.storage_path = os.path.join(storage_path, f"{research_id}_wetlab.json")
        self.experiments: Dict[str, WetLabExperiment] = {}
        self.load_experiments()

    def load_experiments(self):
        """Load experiments from storage."""
        if os.path.exists(self.storage_path):
            with open(self.storage_path, 'r') as f:
                data = json.load(f)

            for exp_id, exp_data in data.items():
                # Convert enums back
                exp_data["experiment_type"] = ExperimentType(exp_data["experiment_type"])
                exp_data["status"] = ExperimentStatus(exp_data["status"])
                self.experiments[exp_id] = WetLabExperiment(**exp_data)

    def save_experiments(self):
        """Save experiments to storage."""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)

        data = {}
        for exp_id, exp in self.experiments.items():
            data[exp_id] = asdict(exp)
            # Convert enums to strings
            data[exp_id]["experiment_type"] = exp.experiment_type.value
            data[exp_id]["status"] = exp.status.value

        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=2)

    def create_experiment(
        self,
        experiment_type: ExperimentType,
        title: str,
        description: str,
        objective: str,
        hypothesis: str,
        protocol: Dict[str, Any],
        required_materials: List[Dict[str, Any]],
        equipment: List[str],
        safety_requirements: List[str],
        estimated_duration: str,
        priority: int = 3,
        dependencies: List[str] = None,
        deadline: str = None
    ) -> WetLabExperiment:
        """Create a new wet lab experiment."""
        experiment_id = f"wetlab_{len(self.experiments) + 1}_{datetime.now().strftime('%Y%m%d')}"

        experiment = WetLabExperiment(
            experiment_id=experiment_id,
            experiment_type=experiment_type,
            title=title,
            description=description,
            objective=objective,
            hypothesis=hypothesis,
            protocol=protocol,
            required_materials=required_materials,
            equipment=equipment,
            safety_requirements=safety_requirements,
            estimated_duration=estimated_duration,
            priority=priority,
            dependencies=dependencies or [],
            deadline=deadline
        )

        self.experiments[experiment_id] = experiment
        self.save_experiments()

        logger.info(f"Created wet lab experiment: {experiment_id} - {title}")
        return experiment

    def assign_experiment(
        self,
        experiment_id: str,
        assigned_to: str,
        notes: str = None
    ) -> bool:
        """Assign experiment to lab personnel."""
        if experiment_id not in self.experiments:
            return False

        self.experiments[experiment_id].assigned_to = assigned_to
        self.experiments[experiment_id].assigned_at = datetime.now().isoformat()
        self.experiments[experiment_id].status = ExperimentStatus.ASSIGNED

        if notes:
            self.experiments[experiment_id].review_comments.append(notes)

        self.save_experiments()
        return True

    def start_experiment(
        self,
        experiment_id: str,
        started_by: str
    ) -> bool:
        """Mark experiment as started."""
        if experiment_id not in self.experiments:
            return False

        self.experiments[experiment_id].status = ExperimentStatus.IN_PROGRESS
        self.experiments[experiment_id].started_at = datetime.now().isoformat()

        self.save_experiments()
        return True

    def submit_results(
        self,
        submission: ExperimentSubmission
    ) -> bool:
        """Submit experiment results."""
        if submission.experiment_id not in self.experiments:
            return False

        experiment = self.experiments[submission.experiment_id]
        experiment.submission = asdict(submission)
        experiment.status = ExperimentStatus.AWAITING_REVIEW
        experiment.completed_at = submission.submitted_at

        self.save_experiments()
        logger.info(f"Results submitted for experiment: {submission.experiment_id}")
        return True

    def review_submission(
        self,
        experiment_id: str,
        approved: bool,
        review_comments: List[str] = None
    ) -> bool:
        """Review submitted experiment results."""
        if experiment_id not in self.experiments:
            return False

        experiment = self.experiments[experiment_id]

        if approved:
            experiment.status = ExperimentStatus.COMPLETED
        else:
            experiment.status = ExperimentStatus.FAILED

        if review_comments:
            experiment.review_comments.extend(review_comments)

        self.save_experiments()
        return True

    def get_pending_assignments(self) -> List[WetLabExperiment]:
        """Get experiments waiting for assignment."""
        return [
            exp for exp in self.experiments.values()
            if exp.status == ExperimentStatus.PENDING
        ]

    def get_in_progress_experiments(self) -> List[WetLabExperiment]:
        """Get experiments currently in progress."""
        return [
            exp for exp in self.experiments.values()
            if exp.status == ExperimentStatus.IN_PROGRESS
        ]

    def get_awaiting_review(self) -> List[WetLabExperiment]:
        """Get experiments awaiting review."""
        return [
            exp for exp in self.experiments.values()
            if exp.status == ExperimentStatus.AWAITING_REVIEW
        ]

    def get_experiment_summary(self) -> Dict[str, Any]:
        """Get summary of all experiments."""
        status_counts = {}
        for exp in self.experiments.values():
            status = exp.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        pending_assignments = self.get_pending_assignments()
        in_progress = self.get_in_progress_experiments()
        awaiting_review = self.get_awaiting_review()

        return {
            "total_experiments": len(self.experiments),
            "status_counts": status_counts,
            "pending_assignments": len(pending_assignments),
            "in_progress": len(in_progress),
            "awaiting_review": len(awaiting_review),
            "experiments_by_type": self._get_experiments_by_type()
        }

    def _get_experiments_by_type(self) -> Dict[str, int]:
        """Get experiment count by type."""
        type_counts = {}
        for exp in self.experiments.values():
            exp_type = exp.experiment_type.value
            type_counts[exp_type] = type_counts.get(exp_type, 0) + 1
        return type_counts

    def generate_lab_request(
        self,
        experiment_id: str
    ) -> Optional[Dict[str, Any]]:
        """Generate lab request document for experiment."""
        if experiment_id not in self.experiments:
            return None

        exp = self.experiments[experiment_id]

        return {
            "request_id": exp.experiment_id,
            "title": exp.title,
            "description": exp.description,
            "objective": exp.objective,
            "hypothesis": exp.hypothesis,
            "experiment_type": exp.experiment_type.value,
            "protocol": exp.protocol,
            "required_materials": exp.required_materials,
            "equipment": exp.equipment,
            "safety_requirements": exp.safety_requirements,
            "estimated_duration": exp.estimated_duration,
            "priority": exp.priority,
            "deadline": exp.deadline,
            "generated_at": datetime.now().isoformat()
        }
