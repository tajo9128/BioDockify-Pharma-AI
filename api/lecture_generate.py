from helpers.api import ApiHandler, Request, Response


class LectureGenerate(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        topic = input.get("topic", "").strip()
        duration = input.get("duration", "60")
        level = input.get("level", "undergraduate")

        if not topic:
            return {"error": "Topic is required", "lecture": None}

        try:
            from modules.faculty_materials import ClassMaterialsGenerator
            gen = ClassMaterialsGenerator()
            lecture = gen.generate_lecture_notes(topic, duration, level)
            homework = gen.generate_homework(topic, 3, level)
            practical = gen.generate_lab_practical(topic, duration)

            return {
                "topic": topic,
                "duration": duration,
                "level": level,
                "lecture": lecture if lecture else {"title": topic, "sections": []},
                "homework": homework if homework else [],
                "practical": practical if practical else {},
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
