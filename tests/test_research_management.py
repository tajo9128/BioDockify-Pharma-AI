
"""
Comprehensive tests for research persistence, wet lab coordination, and thesis tracking.
Verifies year-long thesis management with wet lab integration.
"""
import pytest
import sys
import os
import json
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, '/a0/usr/projects/biodockify_ai')

from modules.research_persistence import (
    ResearchPersistenceManager,
    ResearchState
)
from modules.wetlab_coordinator import (
    WetLabCoordinator,
    ExperimentType,
    ExperimentStatus,
    ExperimentSubmission
)
from modules.thesis_tracker import (
    ThesisMilestoneTracker,
    MilestoneType,
    MilestoneStatus
)


@pytest.fixture
def temp_storage():
    """Create temporary storage for tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_research_state():
    """Sample research state for testing."""
    return {
        "research_id": "test_research_001",
        "topic": "Alzheimer's Disease Drug Discovery",
        "research_type": "phd",
        "current_stage": "data_collection",
        "progress": 0.6,
        "tasks": [
            {
                "id": "t_001",
                "title": "Literature Review",
                "stage": "planning",
                "status": "completed",
                "priority": 5
            },
            {
                "id": "t_002",
                "title": "Cell Culture Experiments",
                "stage": "data_collection",
                "status": "in_progress",
                "priority": 5
            },
            {
                "id": "t_003",
                "title": "Animal Studies",
                "stage": "data_collection",
                "status": "pending",
                "priority": 4
            }
        ]
    }


# ============= Research Persistence Tests =============

class TestResearchPersistence:
    """Test suite for ResearchPersistenceManager."""

    def test_save_and_load_research_state(self, temp_storage, sample_research_state):
        """Test saving and loading research state."""
        manager = ResearchPersistenceManager(temp_storage)

        # Save state
        filepath = manager.save_research_state(
            research_id=sample_research_state["research_id"],
            topic=sample_research_state["topic"],
            research_type=sample_research_state["research_type"],
            current_stage=sample_research_state["current_stage"],
            progress=sample_research_state["progress"],
            tasks=sample_research_state["tasks"]
        )

        assert filepath is not None
        assert os.path.exists(filepath)

        # Load state
        state = manager.load_research_state(sample_research_state["research_id"])

        assert state is not None
        assert state.research_id == sample_research_state["research_id"]
        assert state.topic == sample_research_state["topic"]
        assert state.progress == 0.6
        assert len(state.tasks) == 3

    def test_list_all_research(self, temp_storage):
        """Test listing all research projects."""
        manager = ResearchPersistenceManager(temp_storage)

        # Create multiple research projects
        for i in range(3):
            manager.save_research_state(
                research_id=f"research_{i}",
                topic=f"Research Topic {i}",
                research_type="phd",
                current_stage="planning",
                progress=0.1 * i,
                tasks=[]
            )

        # List all research
        research_list = manager.list_all_research()

        assert len(research_list) == 3
        assert research_list[0]["research_id"] == "research_2"  # Most recent first

    def test_update_task_status(self, temp_storage, sample_research_state):
        """Test updating task status."""
        manager = ResearchPersistenceManager(temp_storage)

        # Save initial state
        manager.save_research_state(**sample_research_state)

        # Update task status
        success = manager.update_task_status(
            research_id=sample_research_state["research_id"],
            task_id="t_003",
            status="in_progress",
            result="Started animal studies"
        )

        assert success is True

        # Verify update
        state = manager.load_research_state(sample_research_state["research_id"])
        updated_task = next(t for t in state.tasks if t["id"] == "t_003")

        assert updated_task["status"] == "in_progress"
        assert updated_task["result"] == "Started animal studies"

    def test_get_resume_summary(self, temp_storage, sample_research_state):
        """Test getting resume summary for returning after absence."""
        manager = ResearchPersistenceManager(temp_storage)

        # Save state with tasks
        manager.save_research_state(**sample_research_state)

        # Get resume summary
        summary = manager.get_resume_summary(sample_research_state["research_id"])

        assert summary is not None
        assert "work_completed" in summary
        assert "what_needed_now" in summary
        assert "continue_from" in summary
        assert summary["work_completed"]["tasks_completed"] == 1
        assert "Cell Culture Experiments" in summary["continue_from"]


# ============= Wet Lab Coordination Tests =============

class TestWetLabCoordinator:
    """Test suite for WetLabCoordinator."""

    def test_create_experiment(self, temp_storage):
        """Test creating a wet lab experiment."""
        coordinator = WetLabCoordinator("test_research_001", temp_storage)

        experiment = coordinator.create_experiment(
            experiment_type=ExperimentType.ANIMAL_STUDY,
            title="Drug Efficacy in Mouse Model",
            description="Test drug efficacy in AD mouse model",
            objective="Evaluate drug effect on amyloid plaques",
            hypothesis="Drug reduces amyloid plaque formation",
            protocol={
                "steps": [
                    "Administer drug to mice",
                    "Wait 4 weeks",
                    "Sacrifice mice",
                    "Analyze brain tissue"
                ]
            },
            required_materials=[
                {"name": "AD mouse model", "quantity": 20},
                {"name": "Test compound", "quantity": "100mg"}
            ],
            equipment=["In vivo imaging system", "Microtome"],
            safety_requirements=["Biosafety level 2", "Animal handling training"],
            estimated_duration="4 weeks",
            priority=5,
            deadline=(datetime.now() + timedelta(days=30)).isoformat()
        )

        assert experiment is not None
        assert experiment.experiment_type == ExperimentType.ANIMAL_STUDY
        assert experiment.status == ExperimentStatus.PENDING
        assert len(experiment.required_materials) == 2

    def test_assign_experiment(self, temp_storage):
        """Test assigning experiment to personnel."""
        coordinator = WetLabCoordinator("test_research_001", temp_storage)

        # Create experiment first
        experiment = coordinator.create_experiment(
            experiment_type=ExperimentType.CELL_CULTURE,
            title="Cell Viability Assay",
            description="Test cell viability with drug treatment",
            objective="Determine IC50 value",
            hypothesis="Drug reduces cell viability",
            protocol={"steps": ["Treat cells", "Measure viability"]},
            required_materials=[],
            equipment=[],
            safety_requirements=[],
            estimated_duration="1 week"
        )

        # Assign experiment
        success = coordinator.assign_experiment(
            experiment_id=experiment.experiment_id,
            assigned_to="Dr. Smith",
            notes="Priority experiment"
        )

        assert success is True

        # Verify assignment
        loaded_exp = coordinator.experiments[experiment.experiment_id]
        assert loaded_exp.assigned_to == "Dr. Smith"
        assert loaded_exp.status == ExperimentStatus.ASSIGNED

    def test_submit_results(self, temp_storage):
        """Test submitting experiment results."""
        coordinator = WetLabCoordinator("test_research_001", temp_storage)

        # Create and assign experiment
        experiment = coordinator.create_experiment(
            experiment_type=ExperimentType.DRUG_SCREENING,
            title="Compound Library Screen",
            description="Screen 1000 compounds",
            objective="Identify hits",
            hypothesis="Some compounds will be active",
            protocol={"steps": ["Add compounds", "Measure activity"]},
            required_materials=[],
            equipment=[],
            safety_requirements=[],
            estimated_duration="2 weeks"
        )

        coordinator.assign_experiment(experiment.experiment_id, "Lab Technician")
        coordinator.start_experiment(experiment.experiment_id, "Lab Technician")

        # Submit results
        submission = ExperimentSubmission(
            experiment_id=experiment.experiment_id,
            submitted_by="Lab Technician",
            submitted_at=datetime.now().isoformat(),
            results={
                "total_compounds": 1000,
                "active_compounds": 45,
                "hit_rate": 4.5
            },
            data_files=[
                {"name": "results.csv", "path": "/data/results.csv"}
            ],
            observations="Found 45 active compounds",
            conclusions="Hit rate acceptable for lead optimization",
            unexpected_outcomes=[],
            next_steps=["Validate hits", "Perform dose-response"],
            quality_metrics={"z_prime": 0.7},
            compliance_notes=["GLP compliant"]
        )

        success = coordinator.submit_results(submission)

        assert success is True

        # Verify submission
        loaded_exp = coordinator.experiments[experiment.experiment_id]
        assert loaded_exp.submission is not None
        assert loaded_exp.status == ExperimentStatus.AWAITING_REVIEW

    def test_get_experiment_summary(self, temp_storage):
        """Test getting experiment summary."""
        coordinator = WetLabCoordinator("test_research_001", temp_storage)

        # Create multiple experiments
        for i in range(3):
            coordinator.create_experiment(
                experiment_type=ExperimentType.CELL_CULTURE,
                title=f"Experiment {i}",
                description=f"Description {i}",
                objective=f"Objective {i}",
                hypothesis=f"Hypothesis {i}",
                protocol={},
                required_materials=[],
                equipment=[],
                safety_requirements=[],
                estimated_duration="1 week"
            )

        # Get summary
        summary = coordinator.get_experiment_summary()

        assert summary["total_experiments"] == 3
        assert summary["pending_assignments"] == 3


# ============= Thesis Milestone Tracker Tests =============

class TestThesisMilestoneTracker:
    """Test suite for ThesisMilestoneTracker."""

    def test_initialize_thesis(self, temp_storage):
        """Test initializing a new thesis project."""
        tracker = ThesisMilestoneTracker("test_research_001", temp_storage)

        start_date = datetime.now()
        end_date = start_date + timedelta(days=365)

        thesis = tracker.initialize_thesis(
            title="Novel Therapeutic Approaches for Alzheimer's Disease",
            degree_type="PhD",
            field="Pharmacology",
            start_date=start_date.isoformat(),
            expected_completion=end_date.isoformat(),
            advisor="Dr. Johnson",
            committee_members=["Dr. Smith", "Dr. Williams"]
        )

        assert thesis is not None
        assert thesis.degree_type == "PhD"
        assert len(thesis.milestones) == 10  # Default milestones
        assert thesis.advisor == "Dr. Johnson"

    def test_update_milestone_status(self, temp_storage):
        """Test updating milestone status."""
        tracker = ThesisMilestoneTracker("test_research_001", temp_storage)

        # Initialize thesis
        start_date = datetime.now()
        end_date = start_date + timedelta(days=365)
        tracker.initialize_thesis(
            title="Test Thesis",
            degree_type="PhD",
            field="Pharmacology",
            start_date=start_date.isoformat(),
            expected_completion=end_date.isoformat()
        )

        # Update first milestone
        success = tracker.update_milestone_status(
            milestone_id="m_1",
            status=MilestoneStatus.IN_PROGRESS,
            progress=0.3,
            notes="Making good progress on planning"
        )

        assert success is True

        # Verify update
        milestone = tracker.thesis.milestones["m_1"]
        assert milestone.status == MilestoneStatus.IN_PROGRESS
        assert milestone.progress == 0.3
        assert "Making good progress" in milestone.notes[0]

    def test_get_upcoming_deadlines(self, temp_storage):
        """Test getting upcoming deadlines."""
        tracker = ThesisMilestoneTracker("test_research_001", temp_storage)

        # Initialize thesis
        start_date = datetime.now()
        end_date = start_date + timedelta(days=365)
        tracker.initialize_thesis(
            title="Test Thesis",
            degree_type="PhD",
            field="Pharmacology",
            start_date=start_date.isoformat(),
            expected_completion=end_date.isoformat()
        )

        # Get upcoming deadlines (within 30 days)
        deadlines = tracker.get_upcoming_deadlines(days=60)

        # First milestone should be upcoming
        assert len(deadlines) > 0
        assert all(d["days_until"] <= 60 for d in deadlines)

    def test_generate_thesis_report(self, temp_storage):
        """Test generating comprehensive thesis report."""
        tracker = ThesisMilestoneTracker("test_research_001", temp_storage)

        # Initialize thesis
        start_date = datetime.now()
        end_date = start_date + timedelta(days=365)
        tracker.initialize_thesis(
            title="Novel Therapeutic Approaches for Alzheimer's Disease",
            degree_type="PhD",
            field="Pharmacology",
            start_date=start_date.isoformat(),
            expected_completion=end_date.isoformat(),
            advisor="Dr. Johnson"
        )

        # Update some progress
        tracker.update_milestone_status(
            milestone_id="m_1",
            status=MilestoneStatus.IN_PROGRESS,
            progress=0.5
        )

        # Generate report
        report = tracker.generate_thesis_report()

        assert "thesis_info" in report
        assert "timeline" in report
        assert "progress" in report
        assert "recommendations" in report
        assert report["thesis_info"]["degree_type"] == "PhD"
        assert "overall_status" in report
        assert len(report["recommendations"]) > 0


# ============= Integration Tests =============

class TestResearchManagementIntegration:
    """Test suite for integrated research management."""

    def test_full_research_lifecycle(self, temp_storage):
        """Test complete research lifecycle with wet lab and thesis tracking."""
        # Initialize research
        persistence = ResearchPersistenceManager(temp_storage)
        persistence.save_research_state(
            research_id="integration_test",
            topic="Alzheimer's Disease Drug Discovery",
            research_type="phd",
            current_stage="planning",
            progress=0.1,
            tasks=[
                {
                    "id": "t_001",
                    "title": "Literature Review",
                    "stage": "planning",
                    "status": "completed",
                    "priority": 5
                }
            ]
        )

        # Initialize thesis
        thesis_tracker = ThesisMilestoneTracker("integration_test", temp_storage)
        start_date = datetime.now()
        end_date = start_date + timedelta(days=365)
        thesis_tracker.initialize_thesis(
            title="Novel Alzheimer's Therapeutics",
            degree_type="PhD",
            field="Pharmacology",
            start_date=start_date.isoformat(),
            expected_completion=end_date.isoformat()
        )

        # Create wet lab experiment
        wetlab = WetLabCoordinator("integration_test", temp_storage)
        experiment = wetlab.create_experiment(
            experiment_type=ExperimentType.ANIMAL_STUDY,
            title="Drug Efficacy Study",
            description="Test drug in mouse model",
            objective="Evaluate efficacy",
            hypothesis="Drug reduces plaques",
            protocol={},
            required_materials=[],
            equipment=[],
            safety_requirements=[],
            estimated_duration="4 weeks",
            priority=5
        )

        # Verify all components initialized
        research_state = persistence.load_research_state("integration_test")
        assert research_state is not None
        assert thesis_tracker.thesis is not None
        assert len(wetlab.experiments) == 1

        # Test resume summary
        resume_summary = persistence.get_resume_summary("integration_test")
        assert "work_completed" in resume_summary
        assert resume_summary["research_id"] == "integration_test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
