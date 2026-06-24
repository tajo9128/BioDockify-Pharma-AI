"""
Pharma Thesis Engine (Master Framework)
Orchestrates the writing process, enforcing branch-specific focus and strict validation.
BioDockify AI handles all AI content generation - this module manages structure and contextual mapping.
"""
import logging
import asyncio
from typing import Dict, Any, Optional, Callable, List

from modules.thesis.structure import (
    get_template, THESIS_STRUCTURE, ChapterId, ChapterTemplate, 
    SectionRequirement, PharmaBranch, DegreeType, get_branch_profile
)
from modules.thesis.validator import thesis_validator
from modules.agent.prompts import PHD_THESIS_WRITER_PROMPT
from modules.rag.vector_store import get_vector_store

logger = logging.getLogger("thesis.engine")

class ThesisEngine:
    """
    Master Pharma Thesis generation engine.
    """
    
    def __init__(self):
        self.vector_store = get_vector_store()
        self._agent_callback: Optional[Callable] = None
        self._current_thesis_context: Dict[str, Any] = {}
    
    def set_agent_callback(self, callback: Callable[[str], str]):
        self._agent_callback = callback
    
    def set_thesis_context(self, context: Dict[str, Any]):
        self._current_thesis_context = context

    async def generate_chapter(
        self, 
        chapter_id: str, 
        topic: str,
        branch: PharmaBranch = PharmaBranch.GENERAL,
        degree: DegreeType = DegreeType.PHD,
        agent_generate: Optional[Callable[[str, str, Dict], str]] = None
    ) -> Dict[str, Any]:
        """
        Generate a thesis chapter with branch-specific focus.
        """
        # 0. Input Validation (Bug #8)
        if not topic or not topic.strip():
            return {"status": "error", "message": "Research topic is required."}
        
        if not isinstance(branch, PharmaBranch):
            return {"status": "error", "message": f"Invalid pharma branch: {branch}"}
            
        if not isinstance(degree, DegreeType):
            return {"status": "error", "message": f"Invalid degree type: {degree}"}

        logger.info(f"Generating {chapter_id} for topic: {topic} | Branch: {branch} | Degree: {degree}")
        
        # 1. Structure Selection (Bug #15)
        try:
            template = get_template(chapter_id, degree)
            if not template:
                return {"status": "error", "message": f"Invalid or missing chapter template for: {chapter_id}"}
        except Exception as e:
            logger.error(f"Template system error: {e}")
            return {"status": "error", "message": f"Thesis structure system unavailable: {str(e)}"}
        
        profile = get_branch_profile(branch)
        
        # 2. Proof Validation
        validation = thesis_validator.validate_chapter_readiness(chapter_id, branch, degree)
        if validation["status"] == "blocked":
            return {
                "status": "blocked",
                "reason": "Missing Mandatory Proofs",
                "details": validation
            }
        
        # 3. Context Preparation
        chapter_context = await self._get_chapter_context(template, topic, branch, profile)
        
        # 4. Generate Content
        if agent_generate:
            draft = await self._generate_with_agent(template, topic, branch, degree, profile, chapter_context, agent_generate)
        elif self._agent_callback:
            draft = await self._generate_with_callback(template, topic, branch, degree, profile, chapter_context)
        else:
            draft = self._generate_template(template, topic, branch, degree, profile, chapter_context)
        
        # 5. Strict Rule Post-Validation
        violations = thesis_validator.validate_content_strict(chapter_id, draft, branch, degree)
        
        return {
            "status": "success" if not violations else "warning",
            "chapter_id": chapter_id,
            "title": template.title,
            "content": draft,
            "violations": violations,
            "validation_log": validation,
            "branch_applied": branch.value,
            "degree_applied": degree.value
        }
    
    async def _get_chapter_context(self, template: ChapterTemplate, topic: str, branch: PharmaBranch, profile: Dict) -> Dict[str, Any]:
        context = {
            "topic": topic,
            "branch": branch.value,
            "branch_focus": profile.get("intro_focus", ""),
            "thesis_context": self._current_thesis_context,
            "excerpts": [],
            "section_contexts": {}
        }
        
        try:
            query = f"{topic} {template.title} {branch.value}"
            results = await self.vector_store.search(query, k=5)
            context["excerpts"] = [r.get("text", "")[:500] for r in results]
            
            for section in template.sections:
                section_query = f"{topic} {section.title} {branch.value} {section.description}"
                section_results = await self.vector_store.search(section_query, k=3)
                context["section_contexts"][section.title] = [
                    r.get("text", "")[:400] for r in section_results
                ]
        except Exception as e:
            logger.warning(f"Context retrieval failed: {e}")
        
        return context

    async def _generate_with_agent(
        self,
        template: ChapterTemplate,
        topic: str,
        branch: PharmaBranch,
        degree: DegreeType,
        profile: Dict,
        context: Dict[str, Any],
        agent_generate: Callable[[str, str, Dict], str]
    ) -> str:
        """
        Internal generation logic using a provided BioDockify AI callback.
        """
        content = [f"# {template.title}\n"]
        if branch != PharmaBranch.GENERAL:
            content.append(f"> **Specialization**: {branch.value} ({degree.value})\n")
        
        for section in template.sections:
            # Prepare section specific context for BioDockify AI
            section_context = {
                "topic": topic,
                "section_title": section.title,
                "section_description": section.description,
                "branch": branch.value,
                "degree": degree.value,
                "global_rules": template.global_rules,
                "context_excerpts": context.get("section_contexts", {}).get(section.title, []),
                "word_limit": section.word_limit
            }
            
            # BioDockify AI generates content
            try:
                # Check if callback is a coroutine
                if asyncio.iscoroutinefunction(agent_generate):
                    section_content = await agent_generate(topic, section.title, section_context)
                else:
                    section_content = agent_generate(topic, section.title, section_context)
            except Exception as e:
                logger.error(f"Agent generation failed for section {section.title}: {e}")
                section_content = f"*[Generation Failed: {e}]*"
            
            content.append(f"## {section.title}")
            content.append(section_content if section_content else f"*{section.description}*")
            content.append("")
        
        return "\n".join(content)

    async def _generate_with_callback(
        self,
        template: ChapterTemplate,
        topic: str,
        branch: PharmaBranch,
        degree: DegreeType,
        profile: Dict,
        context: Dict[str, Any]
    ) -> str:
        # Build degree-aware structural requirements
        degree_requirements = {
            DegreeType.PHD: {"word_scale": 1.0, "citation_min": 30, "depth": "original contribution, extensive critical analysis"},
            DegreeType.M_PHARM: {"word_scale": 0.7, "citation_min": 20, "depth": "thorough review with experimental validation"},
            DegreeType.B_PHARM: {"word_scale": 0.5, "citation_min": 10, "depth": "literature-based acceptable, clear explanation"},
            DegreeType.PHARM_D: {"word_scale": 0.8, "citation_min": 15, "depth": "clinical focus, patient outcomes, evidence-based practice"},
        }
        dreq = degree_requirements.get(degree, degree_requirements[DegreeType.PHD])

        content = [f"# {template.title}\n"]
        if branch != PharmaBranch.GENERAL:
            content.append(f"> **Specialization**: {branch.value} ({degree.value})\n")

        for section in template.sections:
            section_context = context.get("section_contexts", {}).get(section.title, [])
            context_text = "\n".join(section_context) if section_context else "No specific context."
            rules_text = "\n".join([f"- {r}" for r in template.global_rules])
            word_limit = int((section.word_limit or 500) * dreq["word_scale"])

            # Branch-specific field injection
            branch_instructions = ""
            if template.id == ChapterId.INTRODUCTION:
                branch_instructions = f"BRANCH FOCUS: {profile.get('intro_focus', 'General pharmaceutical research')}"
            elif template.id == ChapterId.MATERIALS_METHODS:
                branch_instructions = f"MANDATORY METHODS: {profile.get('methods_mandatory', 'Standard protocols')}"
            elif template.id == ChapterId.RESULTS:
                branch_instructions = f"EXPECTED DATA TYPES: {profile.get('results_data', 'Quantitative and qualitative')}"
            elif template.id == ChapterId.DISCUSSION:
                branch_instructions = f"DISCUSSION FOCUS: {profile.get('discussion_mechanism', 'Compare with prior literature')}"

            # PHARM.D specific rules
            pharm_d_rules = ""
            if degree == DegreeType.PHARM_D:
                pharm_d_rules = (
                    "- Focus strictly on patient outcomes and clinical data.\n"
                    "- No mechanistic, molecular, or synthetic chemistry claims allowed.\n"
                )

            # Degree-level depth instruction
            depth_note = f"DEGREE LEVEL: {degree.value}. Expected depth: {dreq['depth']}. Minimum citations for chapter: {dreq['citation_min']}."

            prompt = f"""{PHD_THESIS_WRITER_PROMPT}

Write the "{section.title}" section for a {degree.value} thesis chapter on "{template.title}".

BRANCH: {branch.value}
TOPIC: {topic}
SECTION FOCUS: {section.description}
{branch_instructions}
{depth_note}

STRICT RULES:
{rules_text}
{pharm_d_rules}
CONTEXT:
{context_text}

INSTRUCTIONS:
- Write in formal, past-tense academic pharma English.
- Use branch-specific terminology for {branch.value}.
- Mention expected data types: {profile.get('results_data', 'standard metrics')}.
- Word limit: {word_limit} words.

Write the section:"""

            section_content = self._agent_callback(prompt)
            content.append(f"## {section.title}")
            content.append(section_content if section_content else f"*{section.description}*")
            content.append("")

        return "\n".join(content)

    def _generate_template(self, template: ChapterTemplate, topic: str, branch: PharmaBranch, degree: DegreeType, profile: Dict, context: Dict[str, Any]) -> str:
        content = [f"# {template.title} (Draft Template)\n"]
        content.append(f"Branch: {branch.value} | Degree: {degree.value}\n")
        
        for section in template.sections:
            content.append(f"## {section.title}")
            content.append(f"*{section.description}*\n")
            if section.word_limit:
                content.append(f"*Limit: {section.word_limit} words*")
            content.append("\n[Content pending AI generation...]\n")
        
        return "\n".join(content)

    def get_all_chapters(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": cid.value,
                "title": THESIS_STRUCTURE[cid].title,
                "section_count": len(THESIS_STRUCTURE[cid].sections)
            }
            for cid in THESIS_STRUCTURE if cid not in [ChapterId.REFERENCES, ChapterId.APPENDICES]
        ]

thesis_engine = ThesisEngine()

def get_thesis_engine() -> ThesisEngine:
    return thesis_engine
