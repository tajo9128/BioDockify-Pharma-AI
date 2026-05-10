"""Faculty Materials Generator."""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import json
import re
from enum import Enum

logger = logging.getLogger(__name__)


class MaterialType(Enum):
    LECTURE_NOTES = "lecture_notes"
    PPT_SLIDES = "ppt_slides"
    STUDY_GUIDE = "study_guide"


class SyllabusParser:
    """Parse and extract information from course syllabus."""
    
    def __init__(self):
        self.supported_formats = [".pdf", ".docx", ".txt", ".md"]
    
    def parse_syllabus(self, file_path: str) -> Dict[str, Any]:
        """Parse syllabus file and extract structured information."""
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == ".pdf":
            return self._parse_pdf(file_path)
        elif file_ext == ".docx":
            return self._parse_docx(file_path)
        elif file_ext in [".txt", ".md"]:
            return self._parse_text(file_path)
        else:
            raise ValueError(f"Unsupported format: {file_ext}")
    
    def _parse_pdf(self, file_path: str) -> Dict[str, Any]:
        try:
            import pypdf
            with open(file_path, "rb") as f:
                reader = pypdf.PdfReader(f)
                text = "\n".join([page.extract_text() for page in reader.pages])
            return self._extract_syllabus_info(text)
        except Exception as e:
            logger.error(f"Error parsing PDF: {e}")
            return self._create_fallback_syllabus()
    
    def _parse_docx(self, file_path: str) -> Dict[str, Any]:
        try:
            from docx import Document
            doc = Document(file_path)
            text = "\n".join([para.text for para in doc.paragraphs])
            return self._extract_syllabus_info(text)
        except Exception as e:
            logger.error(f"Error parsing DOCX: {e}")
            return self._create_fallback_syllabus()
    
    def _parse_text(self, file_path: str) -> Dict[str, Any]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
            return self._extract_syllabus_info(text)
        except Exception as e:
            logger.error(f"Error parsing text file: {e}")
            return self._create_fallback_syllabus()
    
    def _extract_syllabus_info(self, text: str) -> Dict[str, Any]:
        syllabus = {
            "course_info": {},
            "weeks": [],
            "readings": [],
            "assignments": [],
            "exams": [],
            "policies": {}
        }
        
        title_match = re.search(r"(?:Course|Title|Subject|Name)\s*[:\-]\s*(.+?)(?:\n|$)", text, re.IGNORECASE)
        if title_match:
            syllabus["course_info"]["title"] = title_match.group(1).strip()
        
        instructor_match = re.search(r"(?:Instructor|Professor|Faculty)\s*[:\-]\s*(.+?)(?:\n|$)", text, re.IGNORECASE)
        if instructor_match:
            syllabus["course_info"]["instructor"] = instructor_match.group(1).strip()
        
        week_pattern = r"(?:Week|Session|Module|Unit)\s*(\d+)\s*[:\-\.]\s*(.+?)(?:\n(?=Week|Session|Module|Unit|$))"
        week_matches = re.finditer(week_pattern, text, re.IGNORECASE | re.DOTALL)
        
        for match in week_matches:
            week_num = int(match.group(1))
            week_content = match.group(2).strip()
            topic = self._extract_topic(week_content)
            readings = self._extract_readings(week_content)
            syllabus["weeks"].append({"week": week_num, "topic": topic, "content": week_content, "readings": readings})
        
        return syllabus
    
    def _extract_topic(self, content: str) -> str:
        lines = [line.strip() for line in content.split("\n") if line.strip()]
        if lines:
            return lines[0][:100]
        return "Topic TBD"
    
    def _extract_readings(self, content: str) -> List[str]:
        readings = []
        patterns = [r"Readings?\s*[:\-\.]\s*(.+?)(?:\n|$)", r"References?\s*[:\-\.]\s*(.+?)(?:\n|$)"]
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                readings.append(match.group(1).strip())
        return readings[:5]
    
    def _create_fallback_syllabus(self) -> Dict[str, Any]:
        return {"course_info": {"title": "Course", "instructor": "Instructor"}, "weeks": [], "readings": [], "assignments": [], "exams": [], "policies": {}}


class BookResourceGatherer:
    """Gather books and resources for course topics."""
    
    def gather_resources_for_topic(self, topic: str, resource_type: str = "all") -> Dict[str, Any]:
        resources = {"topic": topic, "books": [], "articles": [], "videos": []}
        
        if resource_type in ["all", "books"]:
            resources["books"] = self._recommend_books(topic)
        if resource_type in ["all", "articles"]:
            resources["articles"] = self._recommend_articles(topic)
        if resource_type in ["all", "videos"]:
            resources["videos"] = self._recommend_videos(topic)
        
        return resources
    
    def _recommend_books(self, topic: str) -> List[Dict[str, Any]]:
        return [
            {"title": f"{topic}: Principles and Practice", "authors": "Leading Experts", "year": 2023, "publisher": "Academic Press", "type": "textbook"},
            {"title": f"Handbook of {topic}", "authors": "Field Specialists", "year": 2022, "publisher": "Springer", "type": "reference"}
        ]
    
    def _recommend_articles(self, topic: str) -> List[Dict[str, Any]]:
        return [
            {"title": f"Recent Advances in {topic}", "authors": "Recent Researchers", "journal": "Nature Reviews", "year": 2024, "type": "review"}
        ]
    
    def _recommend_videos(self, topic: str) -> List[Dict[str, Any]]:
        return [
            {"title": f"Introduction to {topic}", "source": "MIT OpenCourseWare", "duration": "1 hour"}
        ]


class ClassMaterialsGenerator:
    """Generate class materials including notes, PPTs, handouts."""
    
    def __init__(self):
        # Dynamic path resolution for cross-platform compatibility
        project_root = Path(__file__).parent.parent.absolute()
        self.output_dir = project_root / "data" / "class_materials"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_lecture_notes(self, topic: str, week_info: Dict[str, Any], resources: Dict[str, Any] = None) -> Dict[str, Any]:
        notes = {
            "topic": topic,
            "week": week_info.get("week", 0),
            "content": {
                "introduction": self._generate_introduction(topic),
                "learning_objectives": self._generate_learning_objectives(topic),
                "key_concepts": self._generate_key_concepts(topic),
                "detailed_content": self._generate_detailed_content(topic, week_info),
                "examples": self._generate_examples(topic),
                "references": self._generate_references(resources),
                "discussion_questions": self._generate_discussion_questions(topic),
                "homework": self._generate_homework(topic)
            },
            "created_at": datetime.now().isoformat()
        }
        self._save_notes(notes)
        return notes
    
    def _generate_introduction(self, topic: str) -> str:
        return f"Introduction to {topic}\n\nThis lecture provides an overview of {topic}, covering fundamental concepts, theoretical frameworks, and practical applications."
    
    def _generate_learning_objectives(self, topic: str) -> List[str]:
        return [
            f"Understand the fundamental principles of {topic}",
            f"Analyze key theoretical frameworks in {topic}",
            f"Apply {topic} concepts to practical scenarios"
        ]
    
    def _generate_key_concepts(self, topic: str) -> List[Dict[str, str]]:
        return [
            {"concept": f"Core Concept 1: Foundation of {topic}", "definition": f"Fundamental principles that form the basis of {topic}", "importance": "Critical"},
            {"concept": f"Core Concept 2: Applications of {topic}", "definition": f"Practical applications in real-world scenarios", "importance": "Connects theory to practice"}
        ]
    
    def _generate_detailed_content(self, topic: str, week_info: Dict) -> str:
        content = week_info.get("content", "")
        return f"Detailed Content\n\n{content}\n\nKey Sections:\n1. Theoretical Background\n2. Practical Applications\n3. Current Research\n4. Critical Analysis"
    
    def _generate_examples(self, topic: str) -> List[Dict[str, str]]:
        return [
            {"title": f"Example 1: Basic {topic} Application", "description": f"Fundamental example demonstrating core {topic} concepts"}
        ]
    
    def _generate_references(self, resources: Dict) -> List[str]:
        if not resources:
            return ["Please provide specific references for this topic"]
        refs = []
        for book in resources.get("books", [])[:3]:
            refs.append(f"{book.get('authors', 'N/A')}. {book.get('title', 'N/A')}. {book.get('publisher', 'N/A')}, {book.get('year', 'N/A')}.")
        return refs
    
    def _generate_discussion_questions(self, topic: str) -> List[str]:
        return [
            f"How does {topic} relate to other concepts in this field?",
            f"What are the main challenges in implementing {topic} in practice?",
            f"How has {topic} evolved over time?"
        ]
    
    def _generate_homework(self, topic: str) -> Dict[str, Any]:
        return {
            "title": f"Homework Assignment: {topic}",
            "description": f"Complete the following exercises to reinforce your understanding of {topic}",
            "exercises": [
                {"question": f"Explain the fundamental principles of {topic}", "type": "short_answer", "points": 10},
                {"question": f"Apply {topic} concepts to solve a problem", "type": "problem_solving", "points": 20}
            ],
            "due_date": (datetime.now() + timedelta(days=7)).isoformat(),
            "total_points": 30
        }
    
    def _save_notes(self, notes: Dict):
        topic_slug = notes["topic"].lower().replace(" ", "_")[:50]
        week = notes["week"]
        filename = f"week_{week}_{topic_slug}.json"
        filepath = self.output_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(notes, f, indent=2, ensure_ascii=False)
        logger.info(f"Lecture notes saved to {filepath}")
    
    def generate_ppt_slides(self, topic: str, notes: Dict[str, Any]) -> Dict[str, Any]:
        slides = {
            "presentation": {
                "title": topic,
                "subtitle": f"Week {notes['week']}",
                "slides": self._generate_slides_content(topic, notes)
            },
            "created_at": datetime.now().isoformat()
        }
        self._save_ppt(slides)
        return slides
    
    def _generate_slides_content(self, topic: str, notes: Dict) -> List[Dict]:
        return [
            {"slide_number": 1, "title": topic, "content": [f"Week {notes['week']}", notes["content"]["learning_objectives"][0]], "notes": f"Introduction to {topic}"},
            {"slide_number": 2, "title": "Learning Objectives", "content": notes["content"]["learning_objectives"], "notes": "Objectives for today's lecture"},
            {"slide_number": 3, "title": "Key Concepts", "content": [notes["content"]["key_concepts"][0]["concept"], notes["content"]["key_concepts"][1]["concept"]], "notes": "Core concepts to understand"},
            {"slide_number": 4, "title": "References", "content": notes["content"]["references"][:3], "notes": "Key references"}
        ]
    
    def _save_ppt(self, slides: Dict):
        topic_slug = slides["presentation"]["title"].lower().replace(" ", "_")[:50]
        filename = f"ppt_{topic_slug}.json"
        filepath = self.output_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(slides, f, indent=2, ensure_ascii=False)
        logger.info(f"PPT slides saved to {filepath}")
