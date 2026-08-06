from helpers.api import ApiHandler, Request, Response


class LectureGenerate(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        topic = input.get("topic", "").strip()
        duration = input.get("duration", "60")
        level = input.get("level", "undergraduate")

        if not topic:
            return {"error": "Topic is required", "lecture": None}

        try:
            import asyncio
            from modules.faculty_materials import ClassMaterialsGenerator
            gen = ClassMaterialsGenerator()

            # Build week_info dict that generate_lecture_notes expects
            week_info = {"week": 1, "topic": topic, "duration": duration, "level": level}
            resources = {"level": level}

            # Wrap blocking file I/O (_save_notes) off the async event loop
            raw = await asyncio.to_thread(gen.generate_lecture_notes, topic, week_info, resources)

            # Reshape generator output to UI-expected format
            # Generator returns: {topic, week, content: {introduction, learning_objectives, ...}}
            # UI expects: {title, sections: [{title, content}], learning_objectives}
            if isinstance(raw, str):
                lecture = {"title": topic, "sections": [{"title": "Content", "content": raw}]}
            elif isinstance(raw, dict) and "content" in raw and isinstance(raw["content"], dict):
                content = raw["content"]
                sections = []
                for key, val in content.items():
                    if isinstance(val, str) and val.strip():
                        sections.append({"title": key.replace("_", " ").title(), "content": val})
                    elif isinstance(val, list):
                        sections.append({"title": key.replace("_", " ").title(), "content": "\n".join(str(v) for v in val)})
                lecture = {
                    "title": raw.get("topic", topic),
                    "sections": sections,
                    "learning_objectives": content.get("learning_objectives", []),
                }
            elif isinstance(raw, dict):
                lecture = raw
            else:
                lecture = {"title": topic, "sections": []}

            # Homework and practical: generate from lecture content (no dedicated methods exist)
            homework = [
                f"Write a 500-word essay on the importance of {topic} in pharmaceutical research",
                f"Identify and describe three key studies related to {topic}",
                f"Prepare a short presentation on current trends in {topic}",
            ]
            practical = {"title": f"Lab: {topic}", "objective": f"To practically demonstrate {topic} concepts"}

            return {
                "topic": topic,
                "duration": duration,
                "level": level,
                "lecture": lecture,
                "homework": homework,
                "practical": practical,
            }
        except ImportError:
            # Fallback: return structured placeholder
            return {
                "topic": topic,
                "lecture": {
                    "title": topic,
                    "duration": duration,
                    "learning_objectives": [
                        f"Understand the fundamental concepts of {topic}",
                        f"Analyze key principles and mechanisms in {topic}",
                        f"Apply {topic} concepts to pharmaceutical research"
                    ],
                    "sections": [
                        {"title": "Introduction", "content": f"Overview of {topic} and its relevance to pharmaceutical sciences"},
                        {"title": "Key Concepts", "content": f"Core principles and theoretical framework of {topic}"},
                        {"title": "Applications", "content": f"Practical applications of {topic} in drug discovery and development"},
                        {"title": "Current Research", "content": f"Recent advances and ongoing research in {topic}"},
                    ],
                    "summary": f"This lecture covers the essential aspects of {topic} for {level} students over {duration} minutes."
                },
                "homework": [
                    f"Write a 500-word essay on the importance of {topic} in pharmaceutical research",
                    f"Identify and describe three key studies related to {topic}",
                    f"Prepare a short presentation on current trends in {topic}"
                ],
                "practical": {"title": f"Lab: {topic}", "objective": f"To practically demonstrate {topic} concepts"},
            }
        except Exception as e:
            return {"error": str(e)}
