"""Faculty Tools API - Syllabus parsing, assignment generation, question bank, plagiarism check.
All results are stored in the Knowledge Base for academic writing, slides, and notes."""
from helpers.api import ApiHandler, Request
import json
import logging
import base64
import io

logger = logging.getLogger("faculty_tools")


def _store_to_kb(category: str, title: str, content: str, tags: str = ""):
    """Store faculty content in knowledge base.
    Uses auto_store (stdlib-only, no Flask dependency)."""
    try:
        from modules.knowledge.auto_store import auto_store
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else ["faculty"]
        return auto_store(
            module_name="faculty",
            title=title,
            content=content,
            source=f"Faculty: {category}",
            tags=tag_list,
            category="faculty",
        )
    except Exception as e:
        logger.warning(f"KB store failed: {e}")
        return None


def _extract_text_from_file(file_content_b64: str, filename: str) -> str:
    """Extract plain text from a base64-encoded PDF or DOCX file."""
    raw = base64.b64decode(file_content_b64)
    lower = filename.lower()

    if lower.endswith(".pdf"):
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(raw))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:
            logger.warning(f"PDF extraction failed: {e}")
            return ""

    if lower.endswith(".docx"):
        try:
            import zipfile, xml.etree.ElementTree as ET
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                xml_bytes = z.read("word/document.xml")
            tree = ET.fromstring(xml_bytes)
            ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            texts = [t.text for t in tree.iter(f"{{{ns['w']}}}t") if t.text]
            return "\n".join(texts)
        except Exception as e:
            logger.warning(f"DOCX extraction failed: {e}")
            return ""

    if lower.endswith(".txt"):
        try:
            return raw.decode("utf-8", errors="replace")
        except Exception:
            return ""

    return ""


class FacultyTools(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        action = (input.get("action", "") or "").strip()

        if action == "syllabus":
            return self._parse_syllabus(input)
        elif action == "plan_semester":
            return self._plan_semester(input)
        elif action == "plan_class":
            return self._plan_class(input)
        elif action == "lesson_plan":
            return self._lesson_plan(input)
        elif action == "prep_notes":
            return self._prep_notes(input)
        elif action == "make_slides":
            return self._make_slides(input)
        elif action == "assignment":
            return self._gen_assignment(input)
        elif action == "questions":
            return self._gen_questions(input)
        elif action == "plagiarism":
            return await self._check_plagiarism(input)
        elif action == "lecture":
            return self._gen_lecture(input)
        # ── Enhanced Faculty Workflow (added) ──
        elif action == "analyze_syllabus_enhanced":
            return self._analyze_syllabus_enhanced(input)
        elif action == "divide_into_classes":
            return self._divide_into_classes(input)
        elif action == "find_reference_books":
            return await self._find_reference_books(input)
        elif action == "generate_class_slides":
            return self._generate_class_slides(input)
        elif action == "create_class_ppt":
            return self._create_class_ppt(input)
        elif action == "exam_paper":
            return self._exam_paper(input)
        elif action == "rubric":
            return self._rubric(input)
        elif action == "grade_calculator":
            return self._grade_calculator(input)
        elif action == "co_po_mapping":
            return self._co_po_mapping(input)
        elif action == "question_blueprint":
            return self._question_blueprint(input)
        # ── Bloom's Taxonomy & Lab Manual & Accreditation ──
        elif action == "bloom_questions":
            return self._bloom_questions(input)
        elif action == "bloom_analysis":
            return self._bloom_analysis(input)
        elif action == "lab_manual":
            return self._lab_manual(input)
        # ── Textbook Integration (book-to-skill) ──
        elif action == "textbook_extract":
            return self._textbook_extract(input)
        elif action == "textbook_chapter":
            return self._textbook_chapter(input)
        else:
            return {
                "actions": ["syllabus", "plan_semester", "plan_class", "lesson_plan", "prep_notes",
                            "make_slides", "assignment", "questions", "plagiarism", "lecture",
                            "analyze_syllabus_enhanced", "divide_into_classes",
                            "find_reference_books", "generate_class_slides", "create_class_ppt",
                            "exam_paper", "rubric", "grade_calculator", "co_po_mapping", "question_blueprint",
                            "bloom_questions", "bloom_analysis", "lab_manual",
                            "textbook_extract", "textbook_chapter"],
                "hint": "Send action with topic/text"
            }

    def _parse_syllabus(self, input: dict) -> dict:
        text = (input.get("text", "") or "").strip()
        # Accept uploaded file (base64) if no pasted text
        if not text and input.get("file_content"):
            text = _extract_text_from_file(input["file_content"], input.get("file_name", "syllabus.pdf"))
        if not text:
            return {"error": "Please paste syllabus text or upload a PDF/DOCX file"}

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
                result = parser._extract_syllabus_info(text)
                course_name = result.get("course_info", {}).get("title", "")
                weeks = result.get("weeks", [])
                if weeks:
                    topics = [w.get("topic", "") for w in weeks if w.get("topic")]
                else:
                    topics = result.get("topics", []) or result.get("weekly_topics", [])
                duration = str(result.get("duration", ""))
            except:
                course_name = "Course (auto-detected)"
                topics = [l for l in lines[:20] if len(l) > 20]

        # If still no topics, extract from lines that look like topics
        if not topics:
            for line in lines:
                line = line.strip()
                if len(line) > 10 and not line.startswith(("Course", "Instructor", "Professor", "Code", "Credit", "Hour", "Week 1")):
                    if any(c.isalpha() for c in line) and not line.isupper():
                        topics.append(line)

        result = {
            "course_name": course_name or "Untitled Course",
            "course_code": course_code,
            "topics": topics[:20],
            "topic_count": len(topics),
            "duration": duration,
            "assessment": assessment,
            "estimated_weeks": max(1, len(topics) // 2),
            "estimated_lectures": len(topics),
        }

        # Store syllabus in knowledge base
        kb_content = f"## Syllabus: {result['course_name']}\n\n"
        kb_content += f"**Code:** {result['course_code']}\n"
        kb_content += f"**Duration:** {result['duration']}\n"
        kb_content += f"**Topics:** {result['topic_count']}\n\n"
        kb_content += "### Topics\n\n"
        for i, t in enumerate(result['topics'], 1):
            kb_content += f"{i}. {t}\n"
        _store_to_kb("syllabus", f"Syllabus: {result['course_name']}", kb_content, f"{result['course_name']},syllabus")

        return result

    def _plan_semester(self, input: dict) -> dict:
        """Divide syllabus into semester plan with weeks and classes."""
        course_name = input.get("course_name", "Course")
        topics = input.get("topics", [])
        weeks = int(input.get("weeks", 16))
        classes_per_week = int(input.get("classes_per_week", 2))
        total_classes = weeks * classes_per_week

        if not topics:
            return {"error": "Topics required"}

        # Distribute topics across weeks
        classes = []
        class_num = 1
        for week in range(1, weeks + 1):
            for cls in range(1, classes_per_week + 1):
                topic_idx = (class_num - 1) % len(topics)
                classes.append({
                    "class_num": class_num,
                    "week": week,
                    "class_in_week": cls,
                    "topic": topics[topic_idx],
                    "status": "planned",
                })
                class_num += 1

        result = {
            "course_name": course_name,
            "weeks": weeks,
            "classes_per_week": classes_per_week,
            "total_classes": total_classes,
            "classes": classes,
        }

        # Store in KB
        kb_content = f"## Semester Plan: {course_name}\n\n"
        kb_content += f"**Weeks:** {weeks} | **Classes/Week:** {classes_per_week} | **Total:** {total_classes}\n\n"
        current_week = 0
        for c in classes:
            if c["week"] != current_week:
                current_week = c["week"]
                kb_content += f"\n### Week {current_week}\n\n"
            kb_content += f"- Class {c['class_num']}: {c['topic']}\n"
        _store_to_kb("faculty", f"Semester Plan: {course_name}", kb_content, f"{course_name},semester")

        return result

    def _plan_class(self, input: dict) -> dict:
        """Plan a single class with objectives, activities, timing."""
        topic = input.get("topic", "")
        duration = int(input.get("duration", 50))
        level = input.get("level", "undergraduate")

        if not topic:
            return {"error": "Topic required"}

        # Calculate timing
        intro_time = max(5, int(duration * 0.1))
        main_time = int(duration * 0.6)
        activity_time = int(duration * 0.2)
        summary_time = max(5, int(duration * 0.1))

        result = {
            "topic": topic,
            "duration": duration,
            "level": level,
            "objectives": [
                f"Understand the fundamental concepts of {topic}",
                f"Analyze key principles and mechanisms",
                f"Apply knowledge to solve pharmaceutical problems",
            ],
            "structure": [
                {"section": "Introduction", "time": f"{intro_time} min", "content": f"Overview and relevance of {topic}"},
                {"section": "Core Content", "time": f"{main_time} min", "content": f"Key theories, mechanisms, and frameworks"},
                {"section": "Activity", "time": f"{activity_time} min", "content": "Case study, problem-solving, or discussion"},
                {"section": "Summary", "time": f"{summary_time} min", "content": "Key takeaways and next class preview"},
            ],
            "materials": [
                "Lecture slides",
                "Handout with key concepts",
                "Practice problems",
            ],
        }

        # Store in KB
        kb_content = f"## Class Plan: {topic}\n\n"
        kb_content += f"**Duration:** {duration} min | **Level:** {level}\n\n"
        for s in result["structure"]:
            kb_content += f"### {s['section']} ({s['time']})\n{s['content']}\n\n"
        _store_to_kb("faculty", f"Class Plan: {topic}", kb_content, f"{topic},class_plan")

        return result

    def _lesson_plan(self, input: dict) -> dict:
        """Generate detailed lesson plan with teaching methods and assessment."""
        topic = input.get("topic", "")
        duration = int(input.get("duration", 50))
        level = input.get("level", "undergraduate")
        teaching_method = input.get("method", "lecture")

        if not topic:
            return {"error": "Topic required"}

        methods = {
            "lecture": {"desc": "Traditional lecture with Q&A", "activities": ["Presentation", "Examples", "Q&A"]},
            "interactive": {"desc": "Interactive session with discussions", "activities": ["Brief intro", "Group discussion", "Case study", "Wrap-up"]},
            "lab": {"desc": "Hands-on laboratory session", "activities": ["Demo", "Guided practice", "Independent work", "Debrief"]},
            "seminar": {"desc": "Student-led seminar", "activities": ["Student presentation", "Group discussion", "Summary"]},
        }
        method_info = methods.get(teaching_method, methods["lecture"])

        result = {
            "topic": topic,
            "duration": duration,
            "level": level,
            "teaching_method": teaching_method,
            "method_description": method_info["desc"],
            "learning_objectives": [
                f"Understand the fundamental concepts of {topic}",
                f"Analyze key principles and mechanisms",
                f"Apply knowledge to solve pharmaceutical problems",
            ],
            "activities": method_info["activities"],
            "assessment": "In-class questions, end-of-session quiz",
            "materials": ["Slides", "Handouts", "Whiteboard"],
            "prerequisites": "Previous lecture content",
        }

        # Store in KB
        kb_content = f"## Lesson Plan: {topic}\n\n"
        kb_content += f"**Method:** {method_info['desc']} | **Duration:** {duration} min\n\n"
        kb_content += "### Objectives\n"
        for obj in result["learning_objectives"]:
            kb_content += f"- {obj}\n"
        kb_content += "\n### Activities\n"
        for act in result["activities"]:
            kb_content += f"- {act}\n"
        _store_to_kb("faculty", f"Lesson Plan: {topic}", kb_content, f"{topic},lesson_plan")

        return result

    def _prep_notes(self, input: dict) -> dict:
        """Generate student-ready notes for a topic."""
        topic = input.get("topic", "")
        level = input.get("level", "undergraduate")

        if not topic:
            return {"error": "Topic required"}

        result = {
            "topic": topic,
            "level": level,
            "sections": [
                {"title": "Key Concepts", "content": f"Core principles and definitions related to {topic}"},
                {"title": "Important Definitions", "content": f"Key terms and their definitions"},
                {"title": "Mechanisms", "content": f"Step-by-step mechanisms and pathways"},
                {"title": "Examples", "content": f"Real-world pharmaceutical examples"},
                {"title": "Practice Questions", "content": f"Review questions for self-assessment"},
            ],
        }

        # Store in KB
        kb_content = f"## Study Notes: {topic}\n\n"
        kb_content += f"**Level:** {level}\n\n"
        for s in result["sections"]:
            kb_content += f"### {s['title']}\n{s['content']}\n\n"
        _store_to_kb("faculty", f"Notes: {topic}", kb_content, f"{topic},notes")

        return result

    def _make_slides(self, input: dict) -> dict:
        """Generate slides outline from topic."""
        topic = input.get("topic", "")
        num_slides = int(input.get("num_slides", 10))
        style = input.get("style", "academic")

        if not topic:
            return {"error": "Topic required"}

        slides = [
            {"slide": 1, "title": topic, "content": "Introduction and objectives"},
            {"slide": 2, "title": "Background", "content": f"Context and relevance of {topic}"},
            {"slide": 3, "title": "Key Concepts", "content": "Core principles and definitions"},
            {"slide": 4, "title": "Mechanisms", "content": "Step-by-step mechanisms"},
            {"slide": 5, "title": "Applications", "content": "Pharmaceutical applications"},
            {"slide": 6, "title": "Case Study", "content": "Real-world example"},
            {"slide": 7, "title": "Discussion", "content": "Analysis and implications"},
            {"slide": 8, "title": "Summary", "content": "Key takeaways"},
            {"slide": 9, "title": "References", "content": "Citations and further reading"},
            {"slide": 10, "title": "Q&A", "content": "Questions and discussion"},
        ]

        result = {
            "topic": topic,
            "num_slides": min(num_slides, len(slides)),
            "style": style,
            "slides": slides[:num_slides],
        }

        # Store in KB
        kb_content = f"## Slides Outline: {topic}\n\n"
        for s in result["slides"]:
            kb_content += f"### Slide {s['slide']}: {s['title']}\n{s['content']}\n\n"
        _store_to_kb("faculty", f"Slides: {topic}", kb_content, f"{topic},slides")

        return result

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

        result = {
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

        # Store assignment in knowledge base
        kb_content = f"## Assignment: {topic}\n\n"
        kb_content += f"**Type:** {atype} | **Level:** {level} | **Words:** {word_count}\n\n"
        kb_content += f"### Prompt\n\n{prompt}\n\n"
        kb_content += "### Rubric (100 marks)\n\n"
        for r in rubric:
            kb_content += f"**{r['criterion']}** ({r['weight']}%): {', '.join(r['levels'])}\n\n"
        _store_to_kb("assignment", f"Assignment: {topic}", kb_content, f"{topic},assignment,{atype}")

        return result

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
            # PlagiarismChecker returns 'overall_similarity' (0-100 scale), not 'similarity_score'
            sim = result.get("overall_similarity", 0)
            return {
                "overall_score": sim,
                "status": "safe" if sim < 15 else (
                    "warning" if sim < 25 else "flagged"
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

        result = {
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

        # Store lecture in knowledge base
        kb_content = f"## Lecture: {topic}\n\n"
        kb_content += f"**Duration:** {duration} min | **Level:** {level}\n\n"
        kb_content += "### Learning Objectives\n\n"
        for obj in result["learning_objectives"]:
            kb_content += f"- {obj}\n"
        kb_content += "\n### Lecture Structure\n\n"
        for sec in result["lecture_structure"]:
            kb_content += f"**{sec['section']}**: {sec['content']}\n\n"
        kb_content += "### Homework\n\n"
        for hw in result["homework"]:
            kb_content += f"- {hw}\n"
        _store_to_kb("lecture", f"Lecture: {topic}", kb_content, f"{topic},lecture")

        return result

    # ═══════════════════════════════════════════════════════════════
    # Enhanced Faculty Workflow (added)
    # ═══════════════════════════════════════════════════════════════

    def _analyze_syllabus_enhanced(self, input: dict) -> dict:
        """Enhanced syllabus parser that extracts topics AND reference books."""
        text = (input.get("text", "") or "").strip()
        if not text and input.get("file_content"):
            text = _extract_text_from_file(input["file_content"], input.get("file_name", "syllabus.pdf"))
        if not text:
            return {"error": "Please paste syllabus text or upload a PDF/DOCX file"}
        import re
        lines = text.split("\n")
        course_name, course_code, duration = "", "", ""
        topics, books, units = [], [], []
        book_patterns = ["textbook", "reference book", "recommended reading",
                        "reference:", "text:", "books:", "bibliography",
                        "essential reading", "supplementary reading"]
        current_section = "topics"
        for line in lines:
            ls = line.strip()
            if not ls: continue
            low = ls.lower()
            if "course" in low and ":" in ls and not course_name:
                course_name = ls.split(":", 1)[-1].strip()
            elif "code" in low and ":" in ls:
                course_code = ls.split(":", 1)[-1].strip()
            elif "duration" in low or "credit" in low:
                duration = ls
            if any(p in low for p in book_patterns):
                current_section = "books"
                if ":" in ls:
                    bt = ls.split(":", 1)[-1].strip()
                    if bt and len(bt) > 5:
                        books.append(self._parse_book_ref(bt))
                continue
            if any(p in low for p in ["unit", "module"]) and (":" in ls or low.startswith(("unit", "module"))):
                current_section = "units"
                units.append({"title": ls, "topics": []})
                continue
            if current_section == "books" and len(ls) > 10:
                if any(c.isalpha() for c in ls) and not ls.startswith(("#", "-")):
                    parsed = self._parse_book_ref(ls)
                    if parsed.get("title"):
                        books.append(parsed)
            elif current_section == "units" and units:
                if len(ls) > 10:
                    units[-1]["topics"].append(ls)
            elif current_section == "topics":
                if "week" in low or "topic" in low:
                    topics.append(ls)
                elif len(ls) > 10 and any(c.isalpha() for c in ls):
                    if not ls.isupper() and not ls.startswith(("Course", "Instructor", "Professor", "Code", "Credit")):
                        topics.append(ls)
        if not topics:
            basic = self._parse_syllabus(input)
            topics = basic.get("topics", [])
            if not course_name: course_name = basic.get("course_name", "")
        if not books:
            for line in lines:
                low = line.lower().strip()
                if " by " in low and len(line.strip()) > 15:
                    books.append(self._parse_book_ref(line.strip()))
                elif "isbn" in low:
                    books.append(self._parse_book_ref(line.strip()))
        result = {
            "course_name": course_name or "Untitled Course", "course_code": course_code,
            "duration": duration, "topics": topics[:30], "topic_count": len(topics),
            "units": units, "reference_books": books, "book_count": len(books),
            "estimated_classes_needed": max(len(topics), sum(len(u.get("topics", [])) for u in units)),
        }
        kb_content = f"## Enhanced Syllabus Analysis: {result['course_name']}\n\n"
        kb_content += f"**Code:** {result['course_code']} | **Duration:** {duration}\n"
        kb_content += f"**Topics:** {result['topic_count']} | **Books:** {result['book_count']}\n\n"
        if books:
            kb_content += "### Reference Books\n\n"
            for b in books:
                kb_content += f"- {b.get('title', '')} by {b.get('author', 'Unknown')} ({b.get('year', 'N/A')})\n"
        kb_content += "\n### Topics\n\n"
        for i, t in enumerate(topics, 1):
            kb_content += f"{i}. {t}\n"
        _store_to_kb("faculty", f"Syllabus Analysis: {result['course_name']}", kb_content,
                     f"{result['course_name']},syllabus,analysis")
        return result

    def _parse_book_ref(self, text: str) -> dict:
        """Parse a book reference string into structured data."""
        import re
        book = {"title": "", "author": "", "year": "", "isbn": ""}
        text = text.strip().rstrip(".")
        year_match = re.search(r'\b(19|20)\d{2}\b', text)
        if year_match: book["year"] = year_match.group()
        isbn_match = re.search(r'ISBN[:\s-]*([\d-X]+)', text, re.IGNORECASE)
        if isbn_match: book["isbn"] = isbn_match.group(1).replace("-", "")
        if " by " in text.lower():
            parts = re.split(r'\s+[bB][yY]\s+', text, maxsplit=1)
            book["title"] = parts[0].strip().strip('"').strip("'")
            if len(parts) > 1:
                author_part = parts[1].strip()
                if book["year"]: author_part = author_part.replace(book["year"], "").strip().rstrip(",").strip()
                book["author"] = author_part
        elif "," in text:
            parts = text.split(",", 1)
            if len(parts[0]) < 40:
                book["author"] = parts[0].strip(); book["title"] = parts[1].strip()
            else:
                book["title"] = parts[0].strip(); book["author"] = parts[1].strip()
        else:
            book["title"] = text
        for key in book:
            if isinstance(book[key], str): book[key] = book[key].strip().strip('"').strip("'").strip(".")
        return book

    def _divide_into_classes(self, input: dict) -> dict:
        """Divide syllabus topics into N classes intelligently."""
        topics = input.get("topics", [])
        num_classes = int(input.get("num_classes", 0))
        course_name = input.get("course_name", "Course")
        units = input.get("units", [])
        if not topics: return {"error": "Topics required"}
        if num_classes < 1: return {"error": "Number of classes required (num_classes)"}
        classes = []
        topic_idx = 0
        total_topics = len(topics)
        if units:
            for unit in units:
                unit_topics = unit.get("topics", [])
                if not unit_topics: continue
                for ut in unit_topics:
                    if topic_idx < num_classes:
                        classes.append({"class_num": len(classes) + 1, "topic": ut,
                                       "unit": unit.get("title", ""), "subtopics": [], "estimated_slides": 45})
                        topic_idx += 1
        else:
            topics_per_class = max(1, total_topics / num_classes)
            for i in range(num_classes):
                start_idx = int(i * topics_per_class)
                end_idx = int((i + 1) * topics_per_class)
                class_topics = topics[start_idx:end_idx]
                if not class_topics and topics: class_topics = [topics[-1]]
                main_topic = class_topics[0] if class_topics else f"Review & Practice"
                subtopics = class_topics[1:] if len(class_topics) > 1 else []
                classes.append({"class_num": i + 1, "topic": main_topic, "subtopics": subtopics,
                               "estimated_slides": 45, "duration": "50 min"})
        result = {"course_name": course_name, "num_classes": len(classes), "classes": classes,
                  "total_estimated_slides": sum(c.get("estimated_slides", 45) for c in classes)}
        kb_content = f"## Class Schedule: {course_name}\n\n**Total Classes:** {len(classes)} | **Slides/Class:** 45\n\n"
        for c in classes:
            kb_content += f"### Class {c['class_num']}: {c['topic']}\n"
            if c.get("subtopics"): kb_content += f"  Subtopics: {', '.join(c['subtopics'])}\n"
            kb_content += f"  Estimated: {c.get('estimated_slides', 45)} slides\n\n"
        _store_to_kb("faculty", f"Class Schedule: {course_name}", kb_content, f"{course_name},class_schedule")
        return result

    async def _find_reference_books(self, input: dict) -> dict:
        """Search for free reference books via deep research."""
        books = input.get("books", [])
        topic = input.get("topic", "")
        course_name = input.get("course_name", "")
        if not books and not topic: return {"error": "Provide books list or topic"}
        search_queries = []
        for book in books:
            if isinstance(book, dict):
                title = book.get("title", ""); author = book.get("author", "")
                if title: search_queries.append(f"{title} {author} free PDF")
            elif isinstance(book, str): search_queries.append(f"{book} free PDF")
        if topic:
            search_queries.append(f"{topic} textbook free PDF download")
            search_queries.append(f"{topic} open access book")
        all_results = []
        for query in search_queries[:5]:
            try:
                from modules.literature.discovery import discovery_engine
                import asyncio
                papers = await asyncio.wait_for(discovery_engine.search(query, limit=10), timeout=30.0)
                for paper in papers:
                    # discovery_engine returns Paper dataclass objects, not dicts
                    title = getattr(paper, "title", "") if not isinstance(paper, dict) else paper.get("title", "")
                    authors = getattr(paper, "authors", []) if not isinstance(paper, dict) else paper.get("authors", [])
                    year = getattr(paper, "year", "") if not isinstance(paper, dict) else paper.get("year", "")
                    url = getattr(paper, "url", "") or getattr(paper, "pdf_url", "") if not isinstance(paper, dict) else paper.get("url", paper.get("pdf_url", ""))
                    source = getattr(paper, "source", "") if not isinstance(paper, dict) else paper.get("source", "")
                    pdf_url = getattr(paper, "pdf_url", "") if not isinstance(paper, dict) else paper.get("pdf_url", "")
                    all_results.append({"title": title, "authors": authors,
                                       "year": year, "url": url,
                                       "source": source, "has_pdf": bool(pdf_url)})
            except Exception as e:
                logger.warning(f"Book search failed: {e}")
        seen = set(); unique = []
        for r in all_results:
            key = r.get("title", "").lower()[:50]
            if key and key not in seen: seen.add(key); unique.append(r)
        result = {"search_queries": search_queries[:5], "total_found": len(unique), "books": unique[:20], "course_name": course_name}
        _store_to_kb("faculty", f"Reference Books: {course_name or topic}", str(result), f"{course_name or topic},books")
        return result

    def _generate_class_slides(self, input: dict) -> dict:
        """Generate 40-50 slide content for a class."""
        topic = input.get("topic", "")
        subtopics = input.get("subtopics", [])
        class_num = int(input.get("class_num", 1))
        num_slides = min(max(int(input.get("num_slides", 45)), 30), 60)
        course_name = input.get("course_name", "")
        if not topic: return {"error": "Topic required"}
        slides = []
        slides.append({"slide": 1, "type": "title", "title": f"Class {class_num}: {topic}",
                       "subtitle": course_name, "notes": f"Welcome to Class {class_num}. Today we cover {topic}."})
        slides.append({"slide": 2, "type": "content", "title": "Learning Objectives",
                       "bullets": [f"Understand {topic}", f"Analyze key principles", f"Apply to pharma problems"],
                       "notes": "Learning objectives for this class."})
        slides.append({"slide": 3, "type": "content", "title": "Outline",
                       "bullets": [f"{i+1}. {s}" for i, s in enumerate([topic] + subtopics[:5])],
                       "notes": "Class outline."})
        sn = 4
        for section in (subtopics or [topic])[:8]:
            slides.append({"slide": sn, "type": "section", "title": section, "notes": f"Section: {section}"}); sn += 1
            slides.append({"slide": sn, "type": "content", "title": f"Key Concepts: {section}",
                          "bullets": [f"Definition of {section}", "Mechanism of action", "Structure-activity", "Pharma significance"],
                          "notes": f"Core concepts for {section}."}); sn += 1
            slides.append({"slide": sn, "type": "two_column", "title": f"Details: {section}",
                          "left": {"title": "Theory", "bullets": ["Framework", "Principles", "History"]},
                          "right": {"title": "Applications", "bullets": ["Pharma apps", "Clinical", "Research"]},
                          "notes": f"Theory vs applications for {section}."}); sn += 1
            slides.append({"slide": sn, "type": "content", "title": f"Case Study: {section}",
                          "bullets": ["Real-world example", "Problem analysis", "Solution", "Key points"],
                          "notes": f"Case study for {section}."}); sn += 1
        slides.append({"slide": sn, "type": "content", "title": "Key Takeaways",
                       "bullets": [f"Summary of {topic}"] + [f"• {s}" for s in subtopics[:4]]}); sn += 1
        slides.append({"slide": sn, "type": "content", "title": "Practice Questions",
                       "bullets": [f"Q1: Explain {topic}", f"Q2: Compare approaches", f"Q3: Real-world application"]}); sn += 1
        slides.append({"slide": sn, "type": "content", "title": "References",
                       "bullets": [f"Textbook on {topic}", "PubMed reviews", "Recent papers", "DrugBank/PubChem"]})
        slides = slides[:num_slides]
        result = {"class_num": class_num, "topic": topic, "subtopics": subtopics,
                  "num_slides": len(slides), "slides": slides, "estimated_duration": f"{len(slides)*1.5:.0f} min"}
        _store_to_kb("faculty", f"Class {class_num} Slides: {topic}", str(result), f"{topic},slides,class_{class_num}")
        return result

    def _create_class_ppt(self, input: dict) -> dict:
        """Create editable PPTX from class slide data using ppt-master."""
        slides = input.get("slides", [])
        topic = input.get("topic", "Class Presentation")
        theme = input.get("theme", "academic")
        class_num = int(input.get("class_num", 1))
        if not slides: return {"error": "Slides data required"}
        try:
            from api.ppt_master import PptMasterHandler
            from helpers.api import ApiHandler
            handler = PptMasterHandler.__new__(PptMasterHandler)
            ApiHandler.__init__(handler, None, None)
            result = handler._generate_from_slides(slides, f"Class {class_num}: {topic}", theme)
            # _generate_from_slides returns a Flask Response with binary PPTX
            # Extract the bytes and return as base64 dict for JSON transport
            if hasattr(result, 'response'):
                import base64
                pptx_bytes = b"".join(result.response)
                return {
                    "success": True,
                    "pptx_base64": base64.b64encode(pptx_bytes).decode(),
                    "filename": f"Class_{class_num}_{topic[:30].replace(' ','_')}.pptx",
                    "slides_count": len(slides),
                }
            return result
        except Exception as e:
            return {"error": f"PPT generation failed: {str(e)}"}

    def _exam_paper(self, input: dict) -> dict:
        """Generate a complete exam paper with question bank.

        Creates a structured exam with MCQ, short-answer, and long-answer questions,
        organized by topic with marks distribution and Bloom's taxonomy levels.
        """
        course_name = input.get("course_name", "Course")
        topics = input.get("topics", [])
        duration = int(input.get("duration", 180))
        total_marks = int(input.get("total_marks", 100))
        level = input.get("level", "undergraduate")

        if not topics:
            return {"error": "Topics list required"}

        # Marks distribution
        mcq_marks = int(total_marks * 0.20)
        short_marks = int(total_marks * 0.30)
        long_marks = int(total_marks * 0.50)

        mcq_count = mcq_marks // 2
        short_count = short_marks // 10
        long_count = long_marks // 15

        # Bloom's taxonomy levels
        blooms = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]

        sections = []

        # Section A: MCQs
        mcq_questions = []
        for i in range(mcq_count):
            topic = topics[i % len(topics)]
            bloom = blooms[i % 3]  # MCQs are usually lower Bloom's levels
            mcq_questions.append({
                "q": i + 1,
                "topic": topic,
                "bloom": bloom,
                "marks": 2,
                "type": "MCQ",
                "prompt": f"Multiple choice question on '{topic}' ({bloom} level)"
            })
        sections.append({"name": "Section A", "type": "MCQ", "questions": mcq_questions, "marks": mcq_marks})

        # Section B: Short Answer
        short_questions = []
        for i in range(short_count):
            topic = topics[i % len(topics)]
            bloom = blooms[2 + (i % 3)]  # Apply/Analyze/Evaluate
            short_questions.append({
                "q": i + 1,
                "topic": topic,
                "bloom": bloom,
                "marks": 10,
                "type": "Short Answer",
                "prompt": f"Short answer on '{topic}' ({bloom} level). Answer in 150-200 words."
            })
        sections.append({"name": "Section B", "type": "Short Answer", "questions": short_questions, "marks": short_marks})

        # Section C: Long Answer
        long_questions = []
        for i in range(long_count):
            topic = topics[i % len(topics)]
            bloom = blooms[3 + (i % 3)]  # Analyze/Evaluate/Create
            long_questions.append({
                "q": i + 1,
                "topic": topic,
                "bloom": bloom,
                "marks": 15,
                "type": "Long Answer",
                "prompt": f"Long answer on '{topic}' ({bloom} level). Answer in 500-800 words with diagrams."
            })
        sections.append({"name": "Section C", "type": "Long Answer", "questions": long_questions, "marks": long_marks})

        result = {
            "course_name": course_name,
            "duration": duration,
            "total_marks": total_marks,
            "level": level,
            "sections": sections,
            "marks_distribution": {"MCQ": mcq_marks, "Short Answer": short_marks, "Long Answer": long_marks},
            "bloom_levels_used": blooms[:5],
            "instructions": [
                "Answer ALL questions",
                "MCQs have only one correct answer",
                "Short answers: 150-200 words",
                "Long answers: 500-800 words with diagrams where applicable",
            ],
        }

        # Store in KB
        kb_content = f"## Exam Paper: {course_name}\n\n**Duration:** {duration} min | **Marks:** {total_marks}\n\n"
        for section in sections:
            kb_content += f"### {section['name']} ({section['marks']} marks)\n\n"
            for q in section["questions"]:
                kb_content += f"Q{q['q']}. [{q['topic']}] ({q['bloom']}, {q['marks']} marks) — {q['prompt']}\n\n"
        _store_to_kb("faculty", f"Exam Paper: {course_name}", kb_content, f"{course_name},exam")

        return result

    def _rubric(self, input: dict) -> dict:
        """Generate a detailed rubric for assignments or exams.

        Creates a rubric with criteria, levels, and descriptors for grading.
        """
        assignment_type = input.get("type", "essay")
        criteria_count = int(input.get("criteria_count", 5))
        levels_count = int(input.get("levels_count", 4))

        rubric_templates = {
            "essay": [
                {"criterion": "Content & Understanding", "weight": 30},
                {"criterion": "Critical Analysis", "weight": 25},
                {"criterion": "Research & Citations", "weight": 20},
                {"criterion": "Structure & Organization", "weight": 15},
                {"criterion": "Writing Quality", "weight": 10},
            ],
            "presentation": [
                {"criterion": "Content Knowledge", "weight": 25},
                {"criterion": "Organization & Flow", "weight": 20},
                {"criterion": "Visual Aids", "weight": 20},
                {"criterion": "Delivery & Communication", "weight": 20},
                {"criterion": "Q&A Handling", "weight": 15},
            ],
            "lab_report": [
                {"criterion": "Objective & Methods", "weight": 20},
                {"criterion": "Results & Data", "weight": 25},
                {"criterion": "Discussion & Analysis", "weight": 25},
                {"criterion": "Conclusions", "weight": 15},
                {"criterion": "Format & References", "weight": 15},
            ],
            "research_paper": [
                {"criterion": "Originality & Contribution", "weight": 25},
                {"criterion": "Literature Review", "weight": 20},
                {"criterion": "Methodology", "weight": 20},
                {"criterion": "Results & Discussion", "weight": 25},
                {"criterion": "Writing & Formatting", "weight": 10},
            ],
        }

        criteria = rubric_templates.get(assignment_type, rubric_templates["essay"])[:criteria_count]

        levels = [
            {"level": "Excellent", "range": "90-100%", "descriptor": "Outstanding work, exceeds expectations"},
            {"level": "Good", "range": "70-89%", "descriptor": "Solid work, meets expectations"},
            {"level": "Adequate", "range": "50-69%", "descriptor": "Acceptable work, some gaps"},
            {"level": "Poor", "range": "<50%", "descriptor": "Significant deficiencies"},
        ][:levels_count]

        rubric = []
        for c in criteria:
            rubric.append({
                "criterion": c["criterion"],
                "weight": c["weight"],
                "levels": [{"level": l["level"], "range": l["range"], "score": int(c["weight"] * float(l["range"].split("-")[0].replace("<", "").replace("%", "")) / 100)} for l in levels],
            })

        result = {
            "type": assignment_type,
            "criteria": rubric,
            "levels": levels,
            "total_marks": 100,
        }

        # Store in KB
        kb_content = f"## Rubric: {assignment_type.title()}\n\n"
        for c in rubric:
            kb_content += f"### {c['criterion']} ({c['weight']}%)\n"
            for l in c["levels"]:
                kb_content += f"  - {l['level']} ({l['range']}): {l['score']} marks\n"
        _store_to_kb("faculty", f"Rubric: {assignment_type}", kb_content, f"{assignment_type},rubric")

        return result

    def _grade_calculator(self, input: dict) -> dict:
        """Calculate weighted grades from multiple components.

        Input: components (list of {name, weight, score})
        Output: final grade, letter grade, GPA.
        """
        components = input.get("components", [])
        if not components:
            return {"error": "Components list required. Example: [{name: 'Midterm', weight: 30, score: 85}]"}

        total_weighted = 0
        total_weight = 0
        breakdown = []

        for comp in components:
            name = comp.get("name", "Component")
            weight = float(comp.get("weight", 0))
            score = float(comp.get("score", 0))
            weighted = (score * weight) / 100
            total_weighted += weighted
            total_weight += weight
            breakdown.append({
                "name": name,
                "weight": weight,
                "score": score,
                "weighted_score": round(weighted, 2),
            })

        final_score = round(total_weighted, 2) if total_weight > 0 else 0

        # Letter grade
        if final_score >= 90: letter = "A+"
        elif final_score >= 85: letter = "A"
        elif final_score >= 80: letter = "A-"
        elif final_score >= 75: letter = "B+"
        elif final_score >= 70: letter = "B"
        elif final_score >= 65: letter = "B-"
        elif final_score >= 60: letter = "C+"
        elif final_score >= 55: letter = "C"
        elif final_score >= 50: letter = "C-"
        elif final_score >= 45: letter = "D"
        else: letter = "F"

        # GPA
        gpa_map = {"A+": 4.0, "A": 4.0, "A-": 3.7, "B+": 3.3, "B": 3.0, "B-": 2.7,
                   "C+": 2.3, "C": 2.0, "C-": 1.7, "D": 1.0, "F": 0.0}
        gpa = gpa_map.get(letter, 0.0)

        result = {
            "breakdown": breakdown,
            "total_weighted": final_score,
            "total_weight": total_weight,
            "letter_grade": letter,
            "gpa": gpa,
            "pass": final_score >= 50,
        }

        _store_to_kb("faculty", f"Grade: {final_score}% ({letter})", str(result), "grade,calculator")
        return result

    def _co_po_mapping(self, input: dict) -> dict:
        """Map Course Outcomes (CO) to Program Outcomes (PO) for accreditation.

        Input: course_name, course_outcomes (list), program_outcomes (list), mapping (dict)
        Output: CO-PO mapping matrix with coverage levels.
        """
        course_name = input.get("course_name", "Course")
        course_outcomes = input.get("course_outcomes", [])
        program_outcomes = input.get("program_outcomes", [
            "PO1: Engineering knowledge",
            "PO2: Problem analysis",
            "PO3: Design/development of solutions",
            "PO4: Investigation",
            "PO5: Modern tool usage",
            "PO6: The engineer and society",
            "PO7: Environment and sustainability",
            "PO8: Ethics",
            "PO9: Individual and team work",
            "PO10: Communication",
            "PO11: Project management and finance",
            "PO12: Life-long learning",
        ])

        if not course_outcomes:
            return {"error": "Course outcomes list required. Example: ['CO1: Understand pharmacology', 'CO2: Analyze drug interactions']"}

        # Auto-generate mapping based on keywords
        mapping = {}
        co_keywords = {
            "understand": ["PO1", "PO12"],
            "analyze": ["PO2", "PO4"],
            "apply": ["PO1", "PO3"],
            "design": ["PO3", "PO5"],
            "evaluate": ["PO2", "PO4"],
            "communicate": ["PO10"],
            "team": ["PO9"],
            "ethics": ["PO8"],
            "research": ["PO4", "PO12"],
        }

        for co in course_outcomes:
            co_lower = co.lower()
            mapped_pos = []
            for keyword, pos in co_keywords.items():
                if keyword in co_lower:
                    mapped_pos.extend(pos)
            mapping[co] = list(set(mapped_pos)) if mapped_pos else ["PO1", "PO12"]

        # Calculate coverage
        covered_pos = set()
        for pos_list in mapping.values():
            covered_pos.update(pos_list)

        result = {
            "course_name": course_name,
            "course_outcomes": course_outcomes,
            "program_outcomes": program_outcomes,
            "co_po_mapping": mapping,
            "po_coverage": list(covered_pos),
            "coverage_count": len(covered_pos),
            "total_po": len(program_outcomes),
            "coverage_pct": round(len(covered_pos) / len(program_outcomes) * 100, 1) if program_outcomes else 0,
        }

        _store_to_kb("faculty", f"CO-PO Mapping: {course_name}", str(result), f"{course_name},co_po,accreditation")
        return result

    def _question_blueprint(self, input: dict) -> dict:
        """Generate a question paper blueprint with topic-wise distribution.

        Input: topics (list), total_marks, exam_type (IA/Final)
        Output: Blueprint with topic-wise marks, question types, Bloom's levels.
        """
        topics = input.get("topics", [])
        total_marks = int(input.get("total_marks", 100))
        exam_type = input.get("exam_type", "Final")

        if not topics:
            return {"error": "Topics list required"}

        # Distribute marks proportionally
        marks_per_topic = total_marks // len(topics)
        remaining = total_marks % len(topics)

        blueprint = []
        for i, topic in enumerate(topics):
            marks = marks_per_topic + (1 if i < remaining else 0)
            blueprint.append({
                "topic": topic,
                "marks": marks,
                "mcq": marks // 10,
                "short_answer": marks // 20,
                "long_answer": marks // 30,
                "bloom_levels": ["Remember", "Understand", "Apply"],
            })

        result = {
            "exam_type": exam_type,
            "total_marks": total_marks,
            "topics": len(topics),
            "blueprint": blueprint,
            "marks_per_topic": marks_per_topic,
        }

        _store_to_kb("faculty", f"Question Blueprint: {exam_type}", str(result), f"{exam_type},blueprint")
        return result

    # ═══════════════════════════════════════════════════════════════
    # Bloom's Taxonomy Integration
    # ═══════════════════════════════════════════════════════════════

    BLOOM_LEVELS = {
        "remember": {
            "level": 1,
            "name": "Remember",
            "description": "Recall facts and basic concepts",
            "verbs": ["define", "list", "memorize", "repeat", "state", "describe", "identify", "label", "name", "recognize"],
            "question_types": ["MCQ", "True/False", "Fill in the blank", "Matching"],
            "cognitive_process": "Retrieving relevant knowledge from long-term memory",
        },
        "understand": {
            "level": 2,
            "name": "Understand",
            "description": "Explain ideas or concepts",
            "verbs": ["classify", "describe", "explain", "identify", "locate", "recognize", "report", "select", "translate", "paraphrase"],
            "question_types": ["MCQ", "Short Answer", "Explain with examples"],
            "cognitive_process": "Constructing meaning from oral, written, and graphic messages",
        },
        "apply": {
            "level": 3,
            "name": "Apply",
            "description": "Use information in new situations",
            "verbs": ["calculate", "demonstrate", "apply", "implement", "execute", "use", "solve", "show", "illustrate", "compute"],
            "question_types": ["Problem-solving", "Case study", "Calculation", "Demonstration"],
            "cognitive_process": "Carrying out or using a procedure through executing or implementing",
        },
        "analyze": {
            "level": 4,
            "name": "Analyze",
            "description": "Draw connections among ideas",
            "verbs": ["analyze", "compare", "contrast", "differentiate", "examine", "experiment", "question", "test", "categorize", "distinguish"],
            "question_types": ["Compare/Contrast", "Case analysis", "Critical analysis", "Data interpretation"],
            "cognitive_process": "Breaking material into constituent parts and determining how parts relate to one another",
        },
        "evaluate": {
            "level": 5,
            "name": "Evaluate",
            "description": "Justify a stand or decision",
            "verbs": ["evaluate", "argue", "judge", "defend", "support", "critique", "weigh", "assess", "recommend", "prioritize"],
            "question_types": ["Critical evaluation", "Debate", "Review", "Assessment report"],
            "cognitive_process": "Making judgments based on criteria and standards",
        },
        "create": {
            "level": 6,
            "name": "Create",
            "description": "Produce new or original work",
            "verbs": ["design", "assemble", "construct", "conjecture", "develop", "formulate", "author", "investigate", "create", "compose"],
            "question_types": ["Research proposal", "Design project", "Original composition", "Synthesis"],
            "cognitive_process": "Putting elements together to form a coherent or functional whole",
        },
    }

    def _bloom_questions(self, input: dict) -> dict:
        """Generate questions at specific Bloom's Taxonomy levels.

        Input: topic, bloom_level (remember/understand/apply/analyze/evaluate/create),
               count, qtype (mcq/short/long/true_false/mixed)
        Output: Questions with Bloom's alignment, verbs, and cognitive processes.
        """
        topic = input.get("topic", "")
        bloom_level = input.get("bloom_level", "understand").lower()
        count = min(int(input.get("count", 10)), 50)
        qtype = input.get("qtype", "mixed")

        if not topic:
            return {"error": "Topic required"}

        bloom = self.BLOOM_LEVELS.get(bloom_level, self.BLOOM_LEVELS["understand"])
        verbs = bloom["verbs"]
        question_types = bloom["question_types"]

        # Generate questions based on Bloom's level
        questions = []
        for i in range(count):
            verb = verbs[i % len(verbs)]
            q_type = question_types[i % len(question_types)] if qtype == "mixed" else qtype

            question = {
                "q": i + 1,
                "bloom_level": bloom["name"],
                "bloom_number": bloom["level"],
                "cognitive_process": bloom["cognitive_process"],
                "verb": verb,
                "type": q_type,
                "topic": topic,
                "prompt": f"{verb.capitalize()} {topic} — {bloom['description']}",
                "marks": self._get_marks_for_bloom(bloom["level"], q_type),
            }
            questions.append(question)

        # Bloom's distribution analysis
        distribution = {
            "target_level": bloom["name"],
            "target_number": bloom["level"],
            "total_questions": count,
            "question_types_breakdown": {},
        }
        for q in questions:
            qtype_key = q["type"]
            distribution["question_types_breakdown"][qtype_key] = distribution["question_types_breakdown"].get(qtype_key, 0) + 1

        result = {
            "success": True,
            "topic": topic,
            "bloom_level": bloom["name"],
            "bloom_number": bloom["level"],
            "cognitive_process": bloom["cognitive_process"],
            "verbs_used": verbs,
            "questions": questions,
            "distribution": distribution,
            "total_marks": sum(q["marks"] for q in questions),
        }

        # Store in KB
        kb_content = f"## Bloom's Questions: {topic}\n\n"
        kb_content += f"**Level:** {bloom['name']} (Level {bloom['level']})\n"
        kb_content += f"**Cognitive Process:** {bloom['cognitive_process']}\n"
        kb_content += f"**Total Questions:** {count} | **Total Marks:** {result['total_marks']}\n\n"
        for q in questions:
            kb_content += f"Q{q['q']}. [{q['type']}] ({q['marks']} marks) — {q['prompt']}\n"
        _store_to_kb("faculty", f"Bloom's Questions: {topic} ({bloom['name']})", kb_content,
                     f"{topic},bloom,{bloom_level}")

        return result

    def _bloom_analysis(self, input: dict) -> dict:
        """Analyze Bloom's Taxonomy distribution across an exam or course.

        Input: questions (list of {topic, bloom_level}) or exam_paper
        Output: Bloom's distribution analysis with recommendations.
        """
        questions = input.get("questions", [])
        exam_paper = input.get("exam_paper", None)

        # Extract questions from exam paper if provided
        if exam_paper and not questions:
            for section in exam_paper.get("sections", []):
                for q in section.get("questions", []):
                    questions.append({
                        "topic": q.get("topic", ""),
                        "bloom_level": q.get("bloom", "understand"),
                    })

        if not questions:
            return {"error": "Questions list or exam_paper required"}

        # Count distribution
        distribution = {level: 0 for level in self.BLOOM_LEVELS.keys()}
        for q in questions:
            level = q.get("bloom_level", "understand").lower()
            if level in distribution:
                distribution[level] += 1

        total = sum(distribution.values())
        percentages = {k: round(v / total * 100, 1) if total > 0 else 0 for k, v in distribution.items()}

        # Ideal distribution (Anderson & Krathwohl)
        ideal = {
            "remember": 15,
            "understand": 20,
            "apply": 25,
            "analyze": 20,
            "evaluate": 12,
            "create": 8,
        }

        # Recommendations
        recommendations = []
        for level, pct in percentages.items():
            ideal_pct = ideal[level]
            diff = pct - ideal_pct
            if diff > 10:
                recommendations.append(f"⚠️ Too many {level} questions ({pct}% vs ideal {ideal_pct}%) — consider reducing")
            elif diff < -10:
                recommendations.append(f"📈 Need more {level} questions ({pct}% vs ideal {ideal_pct}%) — consider adding")

        # Cognitive complexity score (weighted average)
        weights = {"remember": 1, "understand": 2, "apply": 3, "analyze": 4, "evaluate": 5, "create": 6}
        complexity = sum(distribution[level] * weights[level] for level in distribution) / total if total > 0 else 0

        result = {
            "success": True,
            "total_questions": total,
            "distribution": distribution,
            "percentages": percentages,
            "ideal_distribution": ideal,
            "cognitive_complexity_score": round(complexity, 2),
            "complexity_level": "Low" if complexity < 2.5 else ("Medium" if complexity < 4 else "High"),
            "recommendations": recommendations,
            "bloom_taxonomy_reference": {
                level: {"name": info["name"], "description": info["description"]}
                for level, info in self.BLOOM_LEVELS.items()
            },
        }

        _store_to_kb("faculty", "Bloom's Taxonomy Analysis", str(result), "bloom,analysis")
        return result

    def _get_marks_for_bloom(self, bloom_level: int, qtype: str) -> int:
        """Get appropriate marks based on Bloom's level and question type."""
        marks_map = {
            "MCQ": {1: 1, 2: 2, 3: 2, 4: 2, 5: 3, 6: 3},
            "True/False": {1: 1, 2: 1, 3: 1, 4: 2, 5: 2, 6: 2},
            "Fill in the blank": {1: 1, 2: 2, 3: 2, 4: 2, 5: 2, 6: 2},
            "Short Answer": {1: 3, 2: 5, 3: 5, 4: 7, 5: 7, 6: 8},
            "Long Answer": {1: 5, 2: 8, 3: 10, 4: 12, 5: 15, 6: 15},
            "Problem-solving": {1: 3, 2: 5, 3: 8, 4: 10, 5: 10, 6: 12},
            "Case study": {1: 5, 2: 8, 3: 10, 4: 12, 5: 15, 6: 15},
            "Compare/Contrast": {1: 3, 2: 5, 3: 7, 4: 10, 5: 10, 6: 12},
            "Critical evaluation": {1: 5, 2: 8, 3: 10, 4: 12, 5: 15, 6: 15},
            "Research proposal": {1: 5, 2: 8, 3: 10, 4: 12, 5: 15, 6: 20},
        }
        return marks_map.get(qtype, {}).get(bloom_level, 5)

    # ═══════════════════════════════════════════════════════════════
    # Lab Manual Generator
    # ═══════════════════════════════════════════════════════════════

    def _lab_manual(self, input: dict) -> dict:
        """Generate a practical/lab manual with procedures.

        Input: course_name, experiments (list of {title, objective, procedure}),
               level (undergraduate/postgraduate), duration_hours
        Output: Complete lab manual with safety notes, materials, procedures, expected results.
        """
        course_name = input.get("course_name", "Pharmacy Practical")
        experiments = input.get("experiments", [])
        level = input.get("level", "undergraduate")
        duration_hours = int(input.get("duration_hours", 2))
        department = input.get("department", "Pharmacy")

        if not experiments:
            # Generate default experiments based on course type
            experiments = self._get_default_experiments(course_name, department)

        manual_sections = []
        total_marks = 0

        for i, exp in enumerate(experiments, 1):
            title = exp.get("title", f"Experiment {i}")
            objective = exp.get("objective", f"To study and demonstrate {title}")
            procedure = exp.get("procedure", [])
            materials = exp.get("materials", [])
            safety = exp.get("safety", [])

            # Generate procedure if not provided
            if not procedure:
                procedure = self._generate_procedure(title, level)

            # Generate materials if not provided
            if not materials:
                materials = self._generate_materials(title, department)

            # Generate safety notes if not provided
            if not safety:
                safety = self._generate_safety_notes(title, department)

            # Calculate marks
            exp_marks = exp.get("marks", 20)
            total_marks += exp_marks

            section = {
                "experiment_num": i,
                "title": title,
                "objective": objective,
                "duration": f"{duration_hours} hours",
                "materials": materials,
                "chemicals": exp.get("chemicals", self._generate_chemicals(title)),
                "apparatus": exp.get("apparatus", self._generate_apparatus(title)),
                "safety_notes": safety,
                "procedure": procedure,
                "observations": exp.get("observations", self._generate_observation_template(title)),
                "expected_results": exp.get("expected_results", self._generate_expected_results(title)),
                "viva_questions": exp.get("viva_questions", self._generate_viva_questions(title)),
                "marks": exp_marks,
                "bloom_level": exp.get("bloom_level", "Apply"),
            }
            manual_sections.append(section)

        result = {
            "success": True,
            "course_name": course_name,
            "department": department,
            "level": level,
            "total_experiments": len(manual_sections),
            "total_marks": total_marks,
            "duration_per_experiment": f"{duration_hours} hours",
            "experiments": manual_sections,
            "grading_scheme": {
                "procedure_following": "40%",
                "observations_recorded": "20%",
                "results_accuracy": "20%",
                "viva_voce": "10%",
                "lab_record": "10%",
            },
            "general_instructions": [
                "Wear lab coat, gloves, and safety goggles at all times",
                "Read the complete procedure before starting the experiment",
                "Record all observations immediately in the lab notebook",
                "Dispose of chemicals as per institutional waste management policy",
                "Report any accidents or spills to the lab supervisor immediately",
                "Clean your workspace after completing the experiment",
            ],
        }

        # Store in KB
        kb_content = f"## Lab Manual: {course_name}\n\n"
        kb_content += f"**Department:** {department} | **Level:** {level}\n"
        kb_content += f"**Total Experiments:** {len(manual_sections)} | **Total Marks:** {total_marks}\n\n"
        for exp in manual_sections:
            kb_content += f"### Experiment {exp['experiment_num']}: {exp['title']}\n"
            kb_content += f"**Objective:** {exp['objective']}\n"
            kb_content += f"**Duration:** {exp['duration']} | **Marks:** {exp['marks']}\n\n"
            kb_content += "**Procedure:**\n"
            for j, step in enumerate(exp["procedure"], 1):
                kb_content += f"{j}. {step}\n"
            kb_content += "\n"
        _store_to_kb("faculty", f"Lab Manual: {course_name}", kb_content,
                     f"{course_name},lab_manual,{department}")

        return result

    def _get_default_experiments(self, course_name: str, department: str) -> list:
        """Get default experiments based on course/department."""
        defaults = {
            "Pharmacy": [
                {"title": "Preparation of Aspirin (Acetylsalicylic Acid)", "objective": "To synthesize aspirin from salicylic acid and acetic anhydride", "marks": 20},
                {"title": "Determination of Melting Point", "objective": "To determine the melting point of given pharmaceutical compounds", "marks": 15},
                {"title": "Analysis of Tablets by UV Spectrophotometry", "objective": "To estimate the drug content in pharmaceutical formulations", "marks": 20},
                {"title": "Preparation of Ointment Base", "objective": "To prepare different types of ointment bases", "marks": 15},
                {"title": "Dissolution Testing of Tablets", "objective": "To perform dissolution test and calculate dissolution rate", "marks": 20},
                {"title": "Identification of Functional Groups", "objective": "To identify functional groups in organic compounds using chemical tests", "marks": 15},
            ],
            "Chemistry": [
                {"title": "Acid-Base Titration", "objective": "To determine the concentration of unknown acid/base", "marks": 15},
                {"title": "Preparation of Buffer Solutions", "objective": "To prepare buffer solutions of specific pH", "marks": 15},
                {"title": "Gravimetric Analysis", "objective": "To determine the amount of a substance by precipitation", "marks": 20},
            ],
            "Pharmacology": [
                {"title": "Dose-Response Relationship", "objective": "To study the dose-response curve of a drug", "marks": 20},
                {"title": "LD50 Determination", "objective": "To determine the median lethal dose", "marks": 20},
                {"title": "Drug Interaction Studies", "objective": "To study synergistic and antagonistic drug interactions", "marks": 20},
            ],
        }
        return defaults.get(department, defaults["Pharmacy"])

    def _generate_procedure(self, title: str, level: str) -> list:
        """Generate procedure steps based on experiment title."""
        base_steps = [
            "Read the experiment thoroughly and understand the objective",
            "Gather all required materials, chemicals, and apparatus",
            "Set up the apparatus as per the diagram/protocol",
            "Record initial observations (color, state, temperature)",
            "Carry out the procedure step by step as described",
            "Record all observations at each stage",
            "Note any changes in color, odor, temperature, or state",
            "Complete the experiment and clean the workspace",
            "Calculate results and prepare the lab report",
        ]
        if level == "postgraduate":
            base_steps.extend([
                "Perform the experiment in triplicate for accuracy",
                "Apply statistical analysis to the results",
                "Compare results with published literature",
            ])
        return base_steps

    def _generate_materials(self, title: str, department: str) -> list:
        """Generate materials list based on experiment type."""
        return [
            "Lab coat and safety goggles",
            "Analytical balance",
            "Beakers and flasks",
            "Pipettes and burette",
            "Bunsen burner or hot plate",
            "Thermometer",
            "pH meter or pH paper",
            "Filter paper and funnel",
            "Lab notebook",
        ]

    def _generate_chemicals(self, title: str) -> list:
        """Generate chemicals list based on experiment."""
        return ["Reagents as specified in procedure", "Distilled water", "Standard solutions"]

    def _generate_apparatus(self, title: str) -> list:
        """Generate apparatus list."""
        return ["Beakers", "Flasks", "Pipettes", "Burette", "Analytical balance", "Hot plate"]

    def _generate_safety_notes(self, title: str, department: str) -> list:
        """Generate safety notes."""
        return [
            "Wear protective equipment (lab coat, gloves, goggles) at all times",
            "Handle chemicals with care — use fume hood for volatile substances",
            "Know the location of fire extinguisher and first aid kit",
            "Do not pipette by mouth — use mechanical pipette fillers",
            "Dispose of waste in designated containers",
            "Wash hands thoroughly after handling chemicals",
        ]

    def _generate_observation_template(self, title: str) -> dict:
        """Generate observation recording template."""
        return {
            "initial_observations": "Record initial state, color, temperature",
            "during_experiment": "Record changes at regular intervals",
            "final_observations": "Record final state, yield, characteristics",
            "data_table": "Create a table for recording quantitative data",
        }

    def _generate_expected_results(self, title: str) -> str:
        """Generate expected results description."""
        return f"Expected outcome of {title} as per standard pharmaceutical protocols. Results should be reproducible and within acceptable limits."

    def _generate_viva_questions(self, title: str) -> list:
        """Generate viva voce questions."""
        return [
            f"What is the objective of {title}?",
            f"What are the key principles involved in {title}?",
            f"What safety precautions should be taken?",
            f"What are the possible sources of error?",
            f"How would you improve the accuracy of results?",
        ]

    # ── Textbook Integration (book-to-skill) ──────────────────────────────────

    def _textbook_extract(self, input: dict) -> dict:
        """Extract text and chapter structure from an uploaded textbook.

        Supports: PDF, EPUB, DOCX, HTML, TXT, RTF, MD.
        Returns chapter list with metadata for syllabus mapping, lecture generation, etc.

        Input:
            file_content: base64-encoded file content
            file_name: original filename (for format detection)
        """
        file_content = input.get("file_content", "")
        file_name = input.get("file_name", "textbook.pdf")

        if not file_content:
            return {"error": "file_content (base64) is required"}

        try:
            import base64
            file_bytes = base64.b64decode(file_content)
        except Exception as e:
            return {"error": f"Invalid base64 content: {e}"}

        try:
            from modules.faculty.textbook_parser import extract_textbook
            result = extract_textbook(file_bytes, file_name)
        except ImportError:
            return {"error": "Textbook parser module not available"}
        except Exception as e:
            return {"error": f"Extraction failed: {e}"}

        if not result.get("success"):
            return {"error": result.get("error", "Extraction failed")}

        # Store extracted text for later chapter queries
        import time
        textbook_id = f"tb_{int(time.time())}"
        self._textbook_cache = getattr(self, "_textbook_cache", {})
        self._textbook_cache[textbook_id] = {
            "text": result["text"],
            "chapters": result["chapters"],
            "filename": file_name,
        }

        # Auto-store to KB
        try:
            _store_to_kb(
                "Textbook",
                f"Textbook: {file_name}",
                result["text"][:5000],
                tags="textbook," + file_name
            )
        except Exception:
            pass

        # Return chapters (without full text to keep response small)
        chapters_summary = []
        for ch in result["chapters"]:
            chapters_summary.append({
                "number": ch["number"],
                "title": ch["title"],
                "word_count": ch["word_count"],
                "preview": ch["content"][:200] + "..." if len(ch["content"]) > 200 else ch["content"],
            })

        return {
            "success": True,
            "textbook_id": textbook_id,
            "filename": file_name,
            "structure": result["structure"],
            "metadata": result["metadata"],
            "chapters": chapters_summary,
            "chapter_count": len(chapters_summary),
        }

    def _textbook_chapter(self, input: dict) -> dict:
        """Generate content from a specific textbook chapter.

        Can generate: lecture notes, slides, assignment, questions from a chapter.

        Input:
            textbook_id: ID from textbook_extract
            chapter_number: which chapter to use
            action_type: "lecture" | "slides" | "assignment" | "questions"
            topic: override topic (optional, defaults to chapter title)
        """
        textbook_id = input.get("textbook_id", "")
        chapter_number = int(input.get("chapter_number", 1))
        action_type = input.get("action_type", "lecture")
        topic = input.get("topic", "")

        # Retrieve cached textbook
        self._textbook_cache = getattr(self, "_textbook_cache", {})
        textbook = self._textbook_cache.get(textbook_id)
        if not textbook:
            return {"error": "Textbook not found. Upload again with textbook_extract."}

        # Find the chapter
        from modules.faculty.textbook_parser import extract_chapter_content
        chapter_content = extract_chapter_content(textbook["text"], chapter_number)
        if not chapter_content:
            return {"error": f"Chapter {chapter_number} not found in textbook"}

        # Find chapter title
        chapter_title = topic
        if not chapter_title:
            for ch in textbook.get("chapters", []):
                if ch.get("number") == chapter_number:
                    chapter_title = ch.get("title", f"Chapter {chapter_number}")
                    break
            if not chapter_title:
                chapter_title = f"Chapter {chapter_number}"

        # Truncate content for LLM context
        content_for_llm = chapter_content[:8000]

        # Generate based on action_type
        if action_type == "lecture":
            return self._gen_lecture({
                "topic": chapter_title,
                "duration": input.get("duration", "60"),
                "level": input.get("level", "undergraduate"),
                "reference_text": content_for_llm,
            })
        elif action_type == "slides":
            return self._make_slides({
                "topic": chapter_title,
                "num_slides": input.get("num_slides", 10),
                "style": input.get("style", "academic"),
                "reference_text": content_for_llm,
            })
        elif action_type == "assignment":
            return self._gen_assignment({
                "topic": chapter_title,
                "type": input.get("type", "homework"),
                "difficulty": input.get("difficulty", "medium"),
                "reference_text": content_for_llm,
            })
        elif action_type == "questions":
            return self._gen_questions({
                "topic": chapter_title,
                "num_questions": input.get("num_questions", 10),
                "type": input.get("q_type", "mixed"),
                "reference_text": content_for_llm,
            })
        else:
            return {"error": f"Unknown action_type: {action_type}. Use: lecture, slides, assignment, questions"}
