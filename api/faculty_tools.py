"""Faculty Tools API - Syllabus parsing, assignment generation, question bank, plagiarism check.
All results are stored in the Knowledge Base for academic writing, slides, and notes."""
from helpers.api import ApiHandler, Request
import json
import logging

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
        else:
            return {
                "actions": ["syllabus", "plan_semester", "plan_class", "lesson_plan", "prep_notes",
                            "make_slides", "assignment", "questions", "plagiarism", "lecture",
                            "analyze_syllabus_enhanced", "divide_into_classes",
                            "find_reference_books", "generate_class_slides", "create_class_ppt",
                            "exam_paper", "rubric", "grade_calculator", "co_po_mapping", "question_blueprint"],
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
        if not text:
            return {"error": "Please paste syllabus text or provide syllabus content"}
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
                    if isinstance(paper, dict):
                        all_results.append({"title": paper.get("title", ""), "authors": paper.get("authors", []),
                                           "year": paper.get("year", ""), "url": paper.get("url", paper.get("pdf_url", "")),
                                           "source": paper.get("source", ""), "has_pdf": bool(paper.get("pdf_url"))})
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
            handler = PptMasterHandler()
            result = handler._generate_from_slides(slides, f"Class {class_num}: {topic}", theme)
            _store_to_kb("faculty", f"Class {class_num} PPT: {topic}",
                        f"PPT: {len(slides)} slides", f"{topic},ppt,class_{class_num}")
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
