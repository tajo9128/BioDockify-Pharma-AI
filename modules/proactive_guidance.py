
"""
Proactive Guidance Engine for Agent Zero (BioDockify AI)
Provides proactive suggestions and guidance for researchers and faculty.
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import json
import uuid

logger = logging.getLogger(__name__)


class UserRole(Enum):
    """User role types."""
    RESEARCHER = "researcher"
    FACULTY = "faculty"
    STUDENT = "student"
    ADMIN = "admin"
    UNKNOWN = "unknown"


class GuidanceType(Enum):
    """Types of proactive guidance."""
    NEXT_STEP = "next_step"
    PLANNING = "planning"
    RESOURCE_RECOMMENDATION = "resource_recommendation"
    DEADLINE_ALERT = "deadline_alert"
    OPTIMIZATION = "optimization"
    COLLABORATION = "collaboration"
    PUBLICATION = "publication"
    CLASS_PREPARATION = "class_preparation"
    SYLLABUS_TRACKING = "syllabus_tracking"
    STUDENT_ASSESSMENT = "student_assessment"


class ProactiveGuidance:
    """Proactive guidance item."""

    def __init__(
        self,
        guidance_id: str,
        guidance_type: GuidanceType,
        title: str,
        description: str,
        action_items: List[str],
        priority: str,  # "critical", "high", "medium", "low"
        context: Dict[str, Any] = None,
        estimated_effort: str = None,
        dependencies: List[str] = None,
        deadline: str = None
    ):
        self.guidance_id = guidance_id
        self.guidance_type = guidance_type
        self.title = title
        self.description = description
        self.action_items = action_items
        self.priority = priority
        self.context = context or {}
        self.estimated_effort = estimated_effort
        self.dependencies = dependencies or []
        self.deadline = deadline
        self.created_at = datetime.now().isoformat()
        self.status = "pending"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "guidance_id": self.guidance_id,
            "guidance_type": self.guidance_type.value,
            "title": self.title,
            "description": self.description,
            "action_items": self.action_items,
            "priority": self.priority,
            "context": self.context,
            "estimated_effort": self.estimated_effort,
            "dependencies": self.dependencies,
            "deadline": self.deadline,
            "created_at": self.created_at,
            "status": self.status
        }


class ResearchGuidanceEngine:
    """Proactive guidance engine for researchers."""

    def __init__(self, research_state):
        self.research_state = research_state
        self.current_guidance: List[ProactiveGuidance] = []

    def generate_proactive_suggestions(self) -> List[ProactiveGuidance]:
        """Generate proactive suggestions based on current research state."""
        suggestions = []

        # Analyze current stage and generate relevant suggestions
        if not self.research_state:
            return suggestions

        current_stage = self.research_state.get("current_stage", "")
        progress = self.research_state.get("progress", 0.0)
        tasks = self.research_state.get("tasks", [])

        # Suggestions based on research stage
        if current_stage == "planning":
            suggestions.extend(self._planning_stage_guidance())
        elif current_stage == "literature_review":
            suggestions.extend(self._literature_review_guidance())
        elif current_stage == "methodology_design":
            suggestions.extend(self._methodology_design_guidance())
        elif current_stage == "data_collection":
            suggestions.extend(self._data_collection_guidance())
        elif current_stage == "data_analysis":
            suggestions.extend(self._data_analysis_guidance())
        elif current_stage == "results_interpretation":
            suggestions.extend(self._results_interpretation_guidance())
        elif current_stage == "writing_draft":
            suggestions.extend(self._writing_guidance())

        # Priority-based suggestions
        suggestions.extend(self._priority_based_guidance(tasks))

        # Deadline-based alerts
        suggestions.extend(self._deadline_alerts())

        # Resource recommendations
        suggestions.extend(self._resource_recommendations())

        return suggestions

    def _planning_stage_guidance(self) -> List[ProactiveGuidance]:
        """Guidance for planning stage."""
        suggestions = []

        # Check if research questions are defined
        suggestions.append(ProactiveGuidance(
            guidance_id=str(uuid.uuid4()),
            guidance_type=GuidanceType.PLANNING,
            title="Define Research Questions",
            description="Your research needs clear, focused questions. Based on your topic, consider defining specific, measurable research questions.",
            action_items=[
                "Identify the main research question",
                "Formulate 3-5 specific sub-questions",
                "Ensure questions are answerable with available methods",
                "Check if questions contribute to existing knowledge"
            ],
            priority="critical",
            estimated_effort="1-2 hours",
            context={"stage": "planning"}
        ))

        # Ethical approval guidance
        suggestions.append(ProactiveGuidance(
            guidance_id=str(uuid.uuid4()),
            guidance_type=GuidanceType.NEXT_STEP,
            title="Submit IRB/Ethics Application",
            description="If your research involves human or animal subjects, you need ethics approval before starting data collection.",
            action_items=[
                "Determine if ethics approval is required",
                "Prepare IRB/ethics committee application",
                "Gather required documents (protocol, consent forms)",
                "Submit to appropriate ethics committee",
                "Follow up on application status"
            ],
            priority="high",
            estimated_effort="2-3 days",
            deadline=(datetime.now() + timedelta(days=14)).isoformat(),
            context={"stage": "planning"}
        ))

        return suggestions

    def _literature_review_guidance(self) -> List[ProactiveGuidance]:
        """Guidance for literature review stage."""
        suggestions = []

        suggestions.append(ProactiveGuidance(
            guidance_id=str(uuid.uuid4()),
            guidance_type=GuidanceType.NEXT_STEP,
            title="Expand Literature Search",
            description="Your literature review should be comprehensive. Consider expanding your search to include recent publications and systematic reviews.",
            action_items=[
                "Search PubMed/Medline for recent publications (last 5 years)",
                "Include preprint servers (bioRxiv, medRxiv) for latest findings",
                "Look for systematic reviews and meta-analyses",
                "Use citation chaining to find related papers",
                "Create database for managing references (Zotero, EndNote)"
            ],
            priority="high",
            estimated_effort="1-2 weeks",
            context={"stage": "literature_review"}
        ))

        suggestions.append(ProactiveGuidance(
            guidance_id=str(uuid.uuid4()),
            guidance_type=GuidanceType.RESOURCE_RECOMMENDATION,
            title="Use Specialized Databases",
            description="For pharmaceutical research, use specialized databases beyond PubMed for comprehensive coverage.",
            action_items=[
                "Search Embase for drug information and pharmacology",
                "Check ClinicalTrials.gov for ongoing trials",
                "Use Scopus for broader coverage and citation metrics",
                "Search Web of Science for citation tracking",
                "Check drug approval databases (FDA, EMA)"
            ],
            priority="medium",
            estimated_effort="2-3 days",
            context={"stage": "literature_review"}
        ))

        return suggestions

    def _methodology_design_guidance(self) -> List[ProactiveGuidance]:
        """Guidance for methodology design stage."""
        suggestions = []

        suggestions.append(ProactiveGuidance(
            guidance_id=str(uuid.uuid4()),
            guidance_type=GuidanceType.NEXT_STEP,
            title="Finalize Experimental Design",
            description="Based on your research questions, finalize your experimental design including sample size, controls, and statistical methods.",
            action_items=[
                "Perform power analysis for sample size calculation",
                "Define inclusion/exclusion criteria",
                "Select appropriate controls and blinding methods",
                "Choose statistical analysis methods",
                "Plan for data quality control and reproducibility"
            ],
            priority="critical",
            estimated_effort="3-5 days",
            context={"stage": "methodology_design"}
        ))

        suggestions.append(ProactiveGuidance(
            guidance_id=str(uuid.uuid4()),
            guidance_type=GuidanceType.RESOURCE_RECOMMENDATION,
            title="Set Up Laboratory Environment",
            description="Prepare your laboratory space and ensure all required equipment and materials are available.",
            action_items=[
                "Verify equipment availability and calibration",
                "Order necessary reagents and materials",
                "Set up data collection systems",
                "Prepare standard operating procedures (SOPs)",
                "Arrange for lab safety training"
            ],
            priority="high",
            estimated_effort="1-2 weeks",
            context={"stage": "methodology_design"}
        ))

        return suggestions

    def _data_collection_guidance(self) -> List[ProactiveGuidance]:
        """Guidance for data collection stage."""
        suggestions = []

        suggestions.append(ProactiveGuidance(
            guidance_id=str(uuid.uuid4()),
            guidance_type=GuidanceType.NEXT_STEP,
            title="Monitor Data Quality",
            description="Regular monitoring of data quality is essential during collection. Implement quality control procedures.",
            action_items=[
                "Perform daily data quality checks",
                "Document any deviations from protocol",
                "Maintain detailed lab notebooks",
                "Back up data regularly (multiple locations)",
                "Conduct interim analyses to detect issues early"
            ],
            priority="critical",
            estimated_effort="Ongoing",
            context={"stage": "data_collection"}
        ))

        suggestions.append(ProactiveGuidance(
            guidance_id=str(uuid.uuid4()),
            guidance_type=GuidanceType.OPTIMIZATION,
            title="Optimize Experimental Conditions",
            description="Based on initial results, you may need to optimize experimental conditions for better outcomes.",
            action_items=[
                "Review preliminary results for trends",
                "Identify variables that may affect outcomes",
                "Consider dose-response optimization",
                "Test different incubation times/conditions",
                "Document all optimization experiments"
            ],
            priority="high",
            estimated_effort="1-2 weeks",
            context={"stage": "data_collection"}
        ))

        return suggestions

    def _data_analysis_guidance(self) -> List[ProactiveGuidance]:
        """Guidance for data analysis stage."""
        suggestions = []

        suggestions.append(ProactiveGuidance(
            guidance_id=str(uuid.uuid4()),
            guidance_type=GuidanceType.NEXT_STEP,
            title="Perform Statistical Analysis",
            description="Now that data collection is complete, perform statistical analysis to test your hypotheses.",
            action_items=[
                "Clean and validate collected data",
                "Perform exploratory data analysis",
                "Apply appropriate statistical tests",
                "Check assumptions of statistical methods",
                "Create visualizations (graphs, charts, plots)",
                "Document analysis methods and scripts"
            ],
            priority="critical",
            estimated_effort="2-3 weeks",
            context={"stage": "data_analysis"}
        ))

        suggestions.append(ProactiveGuidance(
            guidance_id=str(uuid.uuid4()),
            guidance_type=GuidanceType.PUBLICATION,
            title="Plan for Publication",
            description="Start planning your publication early. Identify target journals and prepare manuscript elements.",
            action_items=[
                "Identify 3-5 potential target journals",
                "Review journal guidelines and requirements",
                "Prepare figures and tables for manuscript",
                "Start writing methods section first",
                "Check if supplementary materials are needed"
            ],
            priority="high",
            estimated_effort="2-3 weeks",
            context={"stage": "data_analysis"}
        ))

        return suggestions

    def _results_interpretation_guidance(self) -> List[ProactiveGuidance]:
        """Guidance for results interpretation stage."""
        suggestions = []

        suggestions.append(ProactiveGuidance(
            guidance_id=str(uuid.uuid4()),
            guidance_type=GuidanceType.NEXT_STEP,
            title="Interpret Results in Context",
            description="Interpret your results in the context of existing literature. Discuss how your findings advance the field.",
            action_items=[
                "Compare results with literature review findings",
                "Identify strengths and limitations of your study",
                "Discuss implications for future research",
                "Consider clinical or practical applications",
                "Acknowledge alternative explanations"
            ],
            priority="critical",
            estimated_effort="1-2 weeks",
            context={"stage": "results_interpretation"}
        ))

        return suggestions

    def _writing_guidance(self) -> List[ProactiveGuidance]:
        """Guidance for writing stage."""
        suggestions = []

        suggestions.append(ProactiveGuidance(
            guidance_id=str(uuid.uuid4()),
            guidance_type=GuidanceType.NEXT_STEP,
            title="Complete Manuscript Writing",
            description="Finalize your manuscript following journal guidelines. Ensure clarity, conciseness, and completeness.",
            action_items=[
                "Complete Introduction (background, rationale, hypotheses)",
                "Finalize Methods (detailed, reproducible)",
                "Write Results (clear, logical flow)",
                "Write Discussion (interpretation, implications, limitations)",
                "Write Abstract (concise summary)",
                "Create acknowledgments and declarations"
            ],
            priority="critical",
            estimated_effort="2-3 weeks",
            context={"stage": "writing_draft"}
        ))

        return suggestions

    def _priority_based_guidance(self, tasks: List[Dict]) -> List[ProactiveGuidance]:
        """Priority-based guidance based on task status."""
        suggestions = []

        pending_high_priority = [t for t in tasks if t.get("status") == "pending" and t.get("priority", 0) >= 4]

        if pending_high_priority:
            suggestions.append(ProactiveGuidance(
                guidance_id=str(uuid.uuid4()),
                guidance_type=GuidanceType.NEXT_STEP,
                title=f"Focus on High-Priority Tasks",
                description=f"You have {len(pending_high_priority)} high-priority tasks pending. Focus on completing these first.",
                action_items=[
                    f"Complete: {', '.join([t.get('title', 'Task') for t in pending_high_priority[:3]])}",
                    "Block time for high-priority work",
                    "Minimize interruptions during focused work",
                    "Consider delegating lower-priority tasks"
                ],
                priority="high",
                context={"pending_tasks": len(pending_high_priority)}
            ))

        return suggestions

    def _deadline_alerts(self) -> List[ProactiveGuidance]:
        """Generate deadline-based alerts."""
        suggestions = []

        # This would integrate with thesis tracker to check upcoming deadlines
        suggestions.append(ProactiveGuidance(
            guidance_id=str(uuid.uuid4()),
            guidance_type=GuidanceType.DEADLINE_ALERT,
            title="Review Upcoming Deadlines",
            description="Check your milestone deadlines and plan accordingly to stay on track.",
            action_items=[
                "Review thesis milestone deadlines",
                "Check wet lab experiment due dates",
                "Plan buffer time for unexpected delays",
                "Set reminders for critical deadlines"
            ],
            priority="medium",
            context={"deadline_check": True}
        ))

        return suggestions

    def _resource_recommendations(self) -> List[ProactiveGuidance]:
        """Generate resource recommendations."""
        suggestions = []

        suggestions.append(ProactiveGuidance(
            guidance_id=str(uuid.uuid4()),
            guidance_type=GuidanceType.RESOURCE_RECOMMENDATION,
            title="Expand Your Toolkit",
            description="Consider using additional tools and resources to enhance your research efficiency.",
            action_items=[
                "Try data visualization tools (Plotly, Seaborn, Matplotlib)",
                "Use reference management software (Zotero, Mendeley)",
                "Explore statistical software (R, Python scipy, SPSS)",
                "Check for specialized analysis tools for your field",
                "Consider cloud storage for data backup and collaboration"
            ],
            priority="low",
            context={"tools": True}
        ))

        return suggestions


class FacultyGuidanceEngine:
    """Proactive guidance engine for faculty members."""

    def __init__(self, faculty_data):
        self.faculty_data = faculty_data or {}
        self.current_guidance: List[ProactiveGuidance] = []

    def generate_proactive_suggestions(self) -> List[ProactiveGuidance]:
        """Generate proactive suggestions for faculty."""
        suggestions = []

        # Check if syllabus exists
        if not self.faculty_data.get("syllabus"):
            suggestions.append(self._suggest_syllabus_upload())
        else:
            suggestions.extend(self._syllabus_based_guidance())

        # Class preparation suggestions
        suggestions.extend(self._class_preparation_guidance())

        # Student assessment suggestions
        suggestions.extend(self._student_assessment_guidance())

        # Resource gathering suggestions
        suggestions.extend(self._resource_gathering_guidance())

        return suggestions

    def _suggest_syllabus_upload(self) -> ProactiveGuidance:
        """Suggest uploading syllabus."""
        return ProactiveGuidance(
            guidance_id=str(uuid.uuid4()),
            guidance_type=GuidanceType.SYLLABUS_TRACKING,
            title="Upload Your Course Syllabus",
            description="To provide personalized assistance with class preparation, please upload your course syllabus. This will help me track topics, schedule, and generate relevant materials.",
            action_items=[
                "Upload syllabus document (PDF, DOCX)",
                "Ensure syllabus includes: course title, weekly topics, readings, assignments, exams",
                "Specify academic term and dates",
                "Add any special instructions or preferences"
            ],
            priority="high",
            estimated_effort="5-10 minutes",
            context={"syllabus_needed": True}
        )

    def _syllabus_based_guidance(self) -> List[ProactiveGuidance]:
        """Generate suggestions based on syllabus."""
        suggestions = []

        syllabus = self.faculty_data.get("syllabus", {})
        current_week = self._get_current_week(syllabus)
        next_week = current_week + 1

        # Next class preparation
        if next_week <= len(syllabus.get("weeks", [])):
            week_info = syllabus["weeks"][next_week - 1] if next_week > 0 and next_week <= len(syllabus.get("weeks", [])) else {}

            if week_info:
                suggestions.append(ProactiveGuidance(
                    guidance_id=str(uuid.uuid4()),
                    guidance_type=GuidanceType.CLASS_PREPARATION,
                    title=f"Prepare for Week {next_week}: {week_info.get('topic', 'Upcoming Topic')}",
                    description=f"Your next class covers: {week_info.get('topic', 'Topic')}. Start preparing materials and reviewing content.",
                    action_items=[
                        f"Review topic: {week_info.get('topic', 'Topic')}",
                        f"Gather readings: {', '.join(week_info.get('readings', ['To be specified']))}",
                        "Prepare lecture notes",
                        "Create or update presentation slides",
                        "Prepare discussion questions",
                        "Check for recent developments in the topic"
                    ],
                    priority="high",
                    estimated_effort="2-3 hours",
                    context={"week": next_week, "topic": week_info.get("topic", "")}
                ))

        return suggestions

    def _class_preparation_guidance(self) -> List[ProactiveGuidance]:
        """Class preparation suggestions."""
        suggestions = []

        suggestions.append(ProactiveGuidance(
            guidance_id=str(uuid.uuid4()),
            guidance_type=GuidanceType.CLASS_PREPARATION,
            title="Enhance Lecture Materials",
            description="Consider enhancing your lecture materials with additional resources and interactive elements.",
            action_items=[
                "Add recent research papers to reading list",
                "Include case studies or real-world examples",
                "Prepare interactive activities or discussions",
                "Update slides with current data or findings",
                "Create supplementary materials (handouts, study guides)"
            ],
            priority="medium",
            estimated_effort="1-2 hours",
            context={"enhancement": True}
        ))

        return suggestions

    def _student_assessment_guidance(self) -> List[ProactiveGuidance]:
        """Student assessment suggestions."""
        suggestions = []

        suggestions.append(ProactiveGuidance(
            guidance_id=str(uuid.uuid4()),
            guidance_type=GuidanceType.STUDENT_ASSESSMENT,
            title="Prepare Student Assessments",
            description="Plan assessments and grading materials for upcoming evaluations.",
            action_items=[
                "Review assessment schedule in syllabus",
                "Prepare exam questions based on covered topics",
                "Create rubrics for grading assignments",
                "Plan for make-up exams or alternative assessments",
                "Set up grade tracking system"
            ],
            priority="medium",
            estimated_effort="2-3 hours",
            context={"assessment": True}
        ))

        return suggestions

    def _resource_gathering_guidance(self) -> List[ProactiveGuidance]:
        """Resource gathering suggestions."""
        suggestions = []

        suggestions.append(ProactiveGuidance(
            guidance_id=str(uuid.uuid4()),
            guidance_type=GuidanceType.RESOURCE_RECOMMENDATION,
            title="Gather Additional Resources",
            description="Expand your teaching materials with additional books, articles, and multimedia resources.",
            action_items=[
                "Search for recent textbooks in your field",
                "Find open-access resources and journals",
                "Locate educational videos or podcasts",
                "Identify online simulations or interactive tools",
                "Compile list of recommended readings for students"
            ],
            priority="low",
            estimated_effort="1-2 hours",
            context={"resources": True}
        ))

        return suggestions

    def _get_current_week(self, syllabus: Dict) -> int:
        """Determine current week based on syllabus."""
        # This would calculate based on current date and syllabus dates
        # For now, return a placeholder
        return syllabus.get("current_week", 1)
