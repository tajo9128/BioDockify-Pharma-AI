
"""
Role Detector and API Integration for Proactive Guidance
Detects user role (researcher/faculty) and integrates proactive guidance into chat.
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json
from enum import Enum

from modules.proactive_guidance import (
    UserRole, GuidanceType, ProactiveGuidance,
    ResearchGuidanceEngine, FacultyGuidanceEngine
)
from modules.faculty_materials import (
    SyllabusParser, BookResourceGatherer, ClassMaterialsGenerator
)

logger = logging.getLogger(__name__)


class RoleDetector:
    """Detect user role based on conversation context and user profile."""

    def __init__(self):
        self.research_keywords = [
            "research", "phd", "thesis", "dissertation", "paper", "journal",
            "publication", "experiment", "data analysis", "literature review",
            "methodology", "hypothesis", "grant", "funding", "clinical trial",
            "drug discovery", "pharmaceutical", "biotech", "wet lab"
        ]

        self.faculty_keywords = [
            "teach", "lecture", "class", "course", "syllabus", "student",
            "assignment", "exam", "grade", "curriculum", "semester",
            "instruction", "education", "pedagogy", "university"
        ]

        self.research_intents = [
            "plan research", "analyze data", "write paper", "design experiment",
            "literature review", "statistical analysis", "publish findings"
        ]

        self.faculty_intents = [
            "prepare class", "create syllabus", "design assignment",
            "grade students", "lecture notes", "presentation slides"
        ]

    def detect_role(
        self,
        message: str,
        user_profile: Dict[str, Any] = None,
        conversation_history: List[Dict] = None
    ) -> Tuple[UserRole, float]:
        """Detect user role with confidence score."""
        message_lower = message.lower()

        # Check user profile for explicit role
        if user_profile:
            explicit_role = user_profile.get("role", "")
            if explicit_role:
                return self._parse_role(explicit_role), 1.0

        # Score based on keywords
        research_score = self._score_keywords(message_lower, self.research_keywords)
        faculty_score = self._score_keywords(message_lower, self.faculty_keywords)

        # Score based on intents
        research_intents_score = self._score_keywords(message_lower, self.research_intents)
        faculty_intents_score = self._score_keywords(message_lower, self.faculty_intents)

        # Combine scores
        total_research_score = research_score + (research_intents_score * 1.5)
        total_faculty_score = faculty_score + (faculty_intents_score * 1.5)

        # Analyze conversation history if available
        if conversation_history:
            history_research_score = self._score_conversation_history(
                conversation_history, self.research_keywords + self.research_intents
            )
            history_faculty_score = self._score_conversation_history(
                conversation_history, self.faculty_keywords + self.faculty_intents
            )

            total_research_score += history_research_score * 0.5
            total_faculty_score += history_faculty_score * 0.5

        # Determine role
        if total_research_score > total_faculty_score:
            confidence = min(total_research_score / (total_research_score + total_faculty_score), 1.0)
            return UserRole.RESEARCHER, max(confidence, 0.5)
        elif total_faculty_score > total_research_score:
            confidence = min(total_faculty_score / (total_research_score + total_faculty_score), 1.0)
            return UserRole.FACULTY, max(confidence, 0.5)
        else:
            # Equal scores - default to unknown
            return UserRole.UNKNOWN, 0.0

    def _score_keywords(self, text: str, keywords: List[str]) -> float:
        """Score text based on keyword matches."""
        score = 0.0
        for keyword in keywords:
            if keyword in text:
                score += 1.0
        return score

    def _score_conversation_history(
        self,
        history: List[Dict],
        keywords: List[str]
    ) -> float:
        """Score conversation history based on keywords."""
        score = 0.0
        for msg in history[-10:]:  # Last 10 messages
            text = msg.get("content", "").lower()
            score += self._score_keywords(text, keywords)
        return score

    def _parse_role(self, role_str: str) -> UserRole:
        """Parse role string to UserRole enum."""
        role_str = role_str.lower()
        if "researcher" in role_str or "phd" in role_str or "student" in role_str:
            return UserRole.RESEARCHER
        elif "faculty" in role_str or "professor" in role_str or "teacher" in role_str:
            return UserRole.FACULTY
        else:
            return UserRole.UNKNOWN


class ProactiveGuidanceManager:
    """Manages proactive guidance for all user roles."""

    def __init__(self, config):
        self.config = config
        self.role_detector = RoleDetector()
        self.syllabus_parser = SyllabusParser()
        self.book_gatherer = BookResourceGatherer()
        self.materials_generator = ClassMaterialsGenerator()

        # Store user contexts
        self.user_contexts: Dict[str, Dict[str, Any]] = {}

    def get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Get or create user context."""
        if user_id not in self.user_contexts:
            self.user_contexts[user_id] = {
                "role": UserRole.UNKNOWN,
                "confidence": 0.0,
                "research_state": None,
                "faculty_data": {},
                "conversation_history": [],
                "guidance_history": []
            }
        return self.user_contexts[user_id]

    def process_message(
        self,
        user_id: str,
        message: str,
        research_state: Dict = None,
        conversation_history: List = None
    ) -> Dict[str, Any]:
        """Process message and generate proactive guidance."""
        context = self.get_user_context(user_id)

        # Update conversation history
        if conversation_history:
            context["conversation_history"] = conversation_history

        # Detect role
        role, confidence = self.role_detector.detect_role(
            message,
            context.get("user_profile"),
            context.get("conversation_history")
        )

        # Update role if confidence is higher
        if confidence > context.get("confidence", 0.0):
            context["role"] = role
            context["confidence"] = confidence

        # Generate role-specific guidance
        guidance = []

        if role == UserRole.RESEARCHER:
            context["research_state"] = research_state or context.get("research_state")
            guidance = self._generate_research_guidance(context)
        elif role == UserRole.FACULTY:
            guidance = self._generate_faculty_guidance(context, message)
        else:
            # Generate both types of guidance for unknown role
            if research_state:
                context["research_state"] = research_state
            guidance = self._generate_mixed_guidance(context)

        # Store guidance in history
        context["guidance_history"].extend([g.to_dict() for g in guidance])

        return {
            "role": role.value,
            "confidence": confidence,
            "guidance": [g.to_dict() for g in guidance],
            "actions": self._extract_actions(guidance)
        }

    def _generate_research_guidance(self, context: Dict) -> List[ProactiveGuidance]:
        """Generate guidance for researcher."""
        engine = ResearchGuidanceEngine(context.get("research_state"))
        return engine.generate_proactive_suggestions()

    def _generate_faculty_guidance(
        self,
        context: Dict,
        message: str
    ) -> List[ProactiveGuidance]:
        """Generate guidance for faculty."""
        # Check if user is uploading syllabus
        if "syllabus" in message.lower() or "upload" in message.lower():
            return [FacultyGuidanceEngine(context.get("faculty_data"))._suggest_syllabus_upload()]

        # Generate faculty guidance
        faculty_data = context.get("faculty_data", {})
        engine = FacultyGuidanceEngine(faculty_data)

        # Check if we need to generate materials for next class
        if faculty_data.get("syllabus"):
            next_week_guidance = self._generate_next_class_materials(faculty_data)
            if next_week_guidance:
                return [next_week_guidance]

        return engine.generate_proactive_suggestions()

    def _generate_next_class_materials(self, faculty_data: Dict) -> ProactiveGuidance:
        """Generate guidance for next class materials."""
        syllabus = faculty_data.get("syllabus", {})
        current_week = syllabus.get("current_week", 1)
        next_week = current_week + 1

        if next_week <= len(syllabus.get("weeks", [])):
            week_info = syllabus["weeks"][next_week - 1]

            return ProactiveGuidance(
                guidance_id=f"next_class_{next_week}",
                guidance_type=GuidanceType.CLASS_PREPARATION,
                title=f"Next Class: Week {next_week} Materials",
                description=f"Your next class covers: {week_info.get('topic', 'Topic')}. I can help prepare materials.",
                action_items=[
                    f"Topic: {week_info.get('topic', 'Topic')}",
                    "Generate lecture notes",
                    "Create presentation slides",
                    "Gather reading materials",
                    "Prepare discussion questions"
                ],
                priority="high",
                estimated_effort="2-3 hours",
                context={"week": next_week, "topic": week_info.get("topic", "")}
            )

        return None

    def _generate_mixed_guidance(self, context: Dict) -> List[ProactiveGuidance]:
        """Generate mixed guidance when role is unknown."""
        guidance = []

        # Check if we have research state
        if context.get("research_state"):
            research_guidance = self._generate_research_guidance(context)
            guidance.extend(research_guidance[:2])  # Top 2

        # Check if we have faculty data
        if context.get("faculty_data", {}).get("syllabus"):
            faculty_guidance = self._generate_next_class_materials(context.get("faculty_data"))
            if faculty_guidance:
                guidance.append(faculty_guidance)

        # If still no guidance, provide general suggestions
        if not guidance:
            guidance.append(ProactiveGuidance(
                guidance_id="general_welcome",
                guidance_type=GuidanceType.NEXT_STEP,
                title="How Can I Help You?",
                description="I can assist you with research projects or faculty teaching tasks. What would you like to work on today?",
                action_items=[
                    "Start a new research project",
                    "Get help with course preparation",
                    "Upload a syllabus for class materials",
                    "Review current research progress"
                ],
                priority="medium",
                context={"welcome": True}
            ))

        return guidance

    def _extract_actions(self, guidance: List[ProactiveGuidance]) -> List[Dict]:
        """Extract actionable items from guidance."""
        actions = []

        for g in guidance:
            for i, action_item in enumerate(g.action_items):
                actions.append({
                    "action_id": f"{g.guidance_id}_action_{i}",
                    "guidance_id": g.guidance_id,
                    "description": action_item,
                    "priority": g.priority,
                    "type": g.guidance_type.value,
                    "estimated_effort": g.estimated_effort
                })

        return actions

    def upload_syllabus(
        self,
        user_id: str,
        syllabus_path: str
    ) -> Dict[str, Any]:
        """Process uploaded syllabus."""
        context = self.get_user_context(user_id)

        try:
            syllabus_data = self.syllabus_parser.parse_syllabus(syllabus_path)
            context["faculty_data"]["syllabus"] = syllabus_data
            context["faculty_data"]["syllabus_path"] = syllabus_path

            # Generate guidance based on syllabus
            guidance = self._generate_faculty_guidance(context, "")

            return {
                "success": True,
                "message": "Syllabus uploaded successfully",
                "syllabus": syllabus_data,
                "guidance": [g.to_dict() for g in guidance]
            }
        except Exception as e:
            logger.error(f"Error uploading syllabus: {e}")
            return {
                "success": False,
                "message": f"Error processing syllabus: {str(e)}",
                "guidance": []
            }

    def generate_class_materials(
        self,
        user_id: str,
        week: int = None,
        topic: str = None
    ) -> Dict[str, Any]:
        """Generate class materials for a specific week."""
        context = self.get_user_context(user_id)
        syllabus = context.get("faculty_data", {}).get("syllabus")

        if not syllabus:
            return {
                "success": False,
                "message": "No syllabus found. Please upload a syllabus first."
            }

        # Determine week and topic
        if week is None:
            week = syllabus.get("current_week", 1) + 1

        weeks = syllabus.get("weeks", [])
        if not weeks or week > len(weeks):
            return {
                "success": False,
                "message": f"Week {week} not found in syllabus."
            }

        week_info = weeks[week - 1]

        if topic is None:
            topic = week_info.get("topic", "Topic")

        # Gather resources
        resources = self.book_gatherer.gather_resources_for_topic(topic)

        # Generate lecture notes
        notes = self.materials_generator.generate_lecture_notes(
            topic, week_info, resources
        )

        # Generate PPT slides
        slides = self.materials_generator.generate_ppt_slides(topic, notes)

        return {
            "success": True,
            "week": week,
            "topic": topic,
            "notes": notes,
            "slides": slides,
            "resources": resources
        }


def create_proactive_guidance_routes(config, app):
    """Create API routes for proactive guidance."""

    manager = ProactiveGuidanceManager(config)

    @app.post("/api/proactive/process")
    async def process_proactive_guidance(request):
        """Process message and generate proactive guidance."""
        data = await request.json()

        user_id = data.get("user_id", "default")
        message = data.get("message", "")
        research_state = data.get("research_state")
        conversation_history = data.get("conversation_history", [])

        result = manager.process_message(
            user_id, message, research_state, conversation_history
        )

        return {"status": "success", "data": result}

    @app.post("/api/proactive/upload_syllabus")
    async def upload_syllabus(request):
        """Upload and parse syllabus."""
        data = await request.json()

        user_id = data.get("user_id", "default")
        syllabus_path = data.get("syllabus_path")

        result = manager.upload_syllabus(user_id, syllabus_path)

        return {"status": "success" if result["success"] else "error", "data": result}

    @app.post("/api/proactive/generate_materials")
    async def generate_materials(request):
        """Generate class materials."""
        data = await request.json()

        user_id = data.get("user_id", "default")
        week = data.get("week")
        topic = data.get("topic")

        result = manager.generate_class_materials(user_id, week, topic)

        return {"status": "success" if result["success"] else "error", "data": result}

    @app.get("/api/proactive/guidance/{user_id}")
    async def get_guidance(user_id):
        """Get proactive guidance history for user."""
        context = manager.get_user_context(user_id)

        return {
            "status": "success",
            "data": {
                "role": context["role"].value if isinstance(context["role"], Enum) else context["role"],
                "confidence": context["confidence"],
                "guidance_history": context["guidance_history"]
            }
        }

    @app.get("/api/proactive/context/{user_id}")
    async def get_context(user_id):
        """Get full user context."""
        context = manager.get_user_context(user_id)

        return {
            "status": "success",
            "data": context
        }

    return manager
