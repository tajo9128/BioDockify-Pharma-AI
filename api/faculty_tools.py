"""Faculty Tools API - Syllabus parsing, assignment generation, question bank, plagiarism check."""
from helpers.api import ApiHandler, Request
import json
import logging

logger = logging.getLogger("faculty_tools")


class FacultyTools(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        action = (input.get("action", "") or "").strip()

        if action == "syllabus":
            return self._parse_syllabus(input)
        elif action == "assignment":
            return self._gen_assignment(input)
        elif action == "questions":
            return self._gen_questions(input)
        elif action == "plagiarism":
            return await self._check_plagiarism(input)
        elif action == "lecture":
            return self._gen_lecture(input)
        else:
            return {
                "actions": ["syllabus", "assignment", "questions", "plagiarism", "lecture"],
                "hint": "Send action with topic/text"
            }

    def _parse_syllabus(self, input: dict) -> dict:
        text = (input.get("text", "") or "").strip()
        if not text:
            return {"error": "Please paste syllabus text"}

        # Extract course info using heuristics
        lines = text.split("\n")
        course_name = ""
        course_code = ""
        topics = []
        duration = ""
        assessment = ""

        for line in lines:
            line = line.strip()
            if not line: continue
            low = line.lower()
            if "course" in low and ":" in line and not course_name:
                course_name = line.split(":", 1)[-1].strip()
            elif "code" in low and ":" in line:
                course_code = line.split(":", 1)[-1].strip()
            elif "week" in low or "topic" in low:
                topics.append(line)
            elif "duration" in low or "hours" in low or "credit" in low:
                duration = line
            elif "exam" in low or "assessment" in low or "grade" in low:
                assessment = line

        # If no structured data found, try faculty_materials parser
        if not course_name:
            try:
                from modules.faculty_materials import SyllabusParser
                parser = SyllabusParser()
                # Try parsing as text
                result = parser._extract_syllabus_info(text)
                course_name = result.get("course_name", "")
                topics = result.get("topics", []) or result.get("weekly_topics", [])
                duration = str(result.get("duration", ""))
            except:
                course_name = "Course (auto-detected)"
                topics = [l for l in lines[:20] if len(l) > 20]

        return {
            "course_name": course_name or "Untitled Course",
            "course_code": course_code,
            "topics": topics[:20],
            "topic_count": len(topics),
            "duration": duration,
            "assessment": assessment,
            "estimated_weeks": max(1, len(topics) // 2),
            "estimated_lectures": len(topics),
        }

    def _gen_assignment(self, input: dict) -> dict:
        topic = (input.get("topic", "") or "").strip()
        atype = input.get("type", "essay").strip()
        level = input.get("level", "undergraduate").strip()
        word_count = input.get("word_count", "2000").strip()

        if not topic:
            return {"error": "Topic required"}

        # Generate assignment prompt
        prompts = {
            "essay": f"Write a {word_count}-word essay on '{topic}'. Include: 1) Introduction with background, 2) Critical analysis of key concepts, 3) Recent research findings (cite at least 5 papers), 4) Your critical evaluation, 5) Conclusion with future directions. Use APA 7th edition formatting.",
            "report": f"Prepare a laboratory report on '{topic}'. Include: Objective, Materials & Methods, Results (with data tables), Discussion, Conclusion. Length: {word_count} words.",
            "presentation": f"Create a 15-minute presentation on '{topic}'. Include: Title slide, Learning Objectives (3), Background (2 slides), Key Concepts (4 slides), Case Study (2 slides), Summary (1 slide), References. Submit slides + speaker notes.",
            "case_study": f"Analyze the following case study on '{topic}'. 1) Summarize the case (200 words), 2) Identify key pharmaceutical issues, 3) Propose evidence-based solutions, 4) Discuss implications for clinical practice, 5) Provide 5+ references.",
            "review": f"Write a literature review on '{topic}'. Search PubMed for recent papers (last 5 years). Structure: Abstract, Introduction, Methodology of search, Thematic analysis, Critical discussion, Conclusion. Include at least 15 references.",
        }

        prompt = prompts.get(atype, prompts["essay"])

        rubric = [
            {"criterion": "Content & Understanding", "weight": 30, "levels": ["Excellent (27-30)", "Good (21-26)", "Adequate (15-20)", "Poor (<15)"]},
            {"criterion": "Critical Analysis", "weight": 25, "levels": ["Excellent (22-25)", "Good (17-21)", "Adequate (12-16)", "Poor (<12)"]},
            {"criterion": "Research & Citations", "weight": 20, "levels": ["Excellent (18-20)", "Good (14-17)", "Adequate (10-13)", "Poor (<10)"]},
            {"criterion": "Structure & Organization", "weight": 15, "levels": ["Excellent (13-15)", "Good (10-12)", "Adequate (7-9)", "Poor (<7)"]},
            {"criterion": "Writing Quality", "weight": 10, "levels": ["Excellent (9-10)", "Good (7-8)", "Adequate (5-6)", "Poor (<5)"]},
        ]

        return {
            "topic": topic,
            "type": atype,
            "level": level,
            "word_count": word_count,
            "prompt": prompt,
            "rubric": rubric,
            "total_marks": 100,
            "suggested_deadline": "2 weeks from assignment date",
            "submission_format": "PDF or DOCX via LMS",
        }

    def _gen_questions(self, input: dict) -> dict:
        topic = (input.get("topic", "") or "").strip()
        count = min(int(input.get("count", "10") or 10), 50)
        qtype = input.get("qtype", "mcq").strip()
        bloom = input.get("bloom", "remember").strip()

        if not topic:
            return {"error": "Topic required"}

        question_prompts = {
            "mcq": f"Generate {count} multiple-choice questions on '{topic}' at Bloom's '{bloom}' level. Each question must have 4 options (A-D) with one correct answer marked. Include a brief explanation for each answer.",
            "short": f"Generate {count} short-answer questions (2-3 marks each) on '{topic}' at Bloom's '{bloom}' level. Include model answers with key points.",
            "long": f"Generate {count} long-answer/essay questions (10 marks each) on '{topic}' at Bloom's '{bloom}' level. Include detailed marking schemes.",
            "true_false": f"Generate {count} true/false questions on '{topic}' at Bloom's '{bloom}' level. Include the correct answer and a brief justification.",
        }

        prompt = question_prompts.get(qtype, question_prompts["mcq"])

        return {
            "topic": topic,
            "count": count,
            "qtype": qtype,
            "bloom_level": bloom,
            "prompt": prompt,
            "instruction": f"Send the prompt below to the agent chat to generate {count} {qtype} questions.",
        }

    async def _check_plagiarism(self, input: dict) -> dict:
        text = (input.get("text", "") or "").strip()
        if not text or len(text) < 100:
            return {"error": "Please provide at least 100 characters of text to check"}

        try:
            from modules.compliance.plagiarism import PlagiarismChecker
            checker = PlagiarismChecker()
            result = await checker.check_content(text[:5000])
            return {
                "overall_score": result.get("similarity_score", 0),
                "status": "safe" if result.get("similarity_score", 1) < 0.15 else (
                    "warning" if result.get("similarity_score", 1) < 0.25 else "flagged"
                ),
                "matches": result.get("matches", []),
                "sources": result.get("sources", []),
            }
        except ImportError:
            return {
                "error": "Plagiarism checker dependencies not available",
                "overall_score": 0,
                "status": "unavailable"
            }
        except Exception as e:
            return {"error": str(e), "overall_score": 0, "status": "error"}

    def _gen_lecture(self, input: dict) -> dict:
        topic = (input.get("topic", "") or "").strip()
        duration = input.get("duration", "60").strip()
        level = input.get("level", "undergraduate").strip()
        if not topic:
            return {"error": "Topic required"}

        return {
            "topic": topic,
            "duration": duration,
            "level": level,
            "learning_objectives": [
                f"Understand the fundamental concepts of {topic}",
                f"Analyze key principles and mechanisms",
                f"Apply knowledge to solve pharmaceutical problems",
            ],
            "lecture_structure": [
                {"section": "Introduction (5 min)", "content": f"Overview and relevance of {topic}"},
                {"section": "Core Concepts (20 min)", "content": "Key theories and frameworks"},
                {"section": "Case Study (15 min)", "content": "Real-world pharmaceutical application"},
                {"section": "Interactive Discussion (10 min)", "content": "Q&A and group activity"},
                {"section": "Summary (10 min)", "content": "Key takeaways and next lecture preview"},
            ],
            "suggested_reading": [
                f"Textbook chapter on {topic}",
                f"Recent review article on {topic}",
            ],
            "homework": [
                f"Write a 500-word reflection on {topic}",
                f"Find and summarize 2 recent research papers on {topic}",
            ],
        }
