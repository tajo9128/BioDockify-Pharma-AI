"""PPT Master API — Editable PowerPoint generation via ppt-master skill.
Full SVG-based pipeline: Source → Strategy → SVG → Charts → Animations → Speaker Notes → PPTX.
Based on github.com/hugohe3/ppt-master."""
from helpers.api import ApiHandler, Request, Response
import logging, os, json, tempfile, asyncio

log = logging.getLogger("ppt_master")

SKILL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "ppt-master")
SCRIPTS_DIR = os.path.join(SKILL_DIR, "scripts")


class PptMasterHandler(ApiHandler):
    """PPT Master — generates real editable PowerPoint files with native shapes, charts, animations, and speaker notes."""

    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "")

        if action == "status":
            return self._status()
        elif action == "generate":
            return await self._generate(input)
        elif action == "list_templates":
            return self._list_templates()
        elif action == "list_workflows":
            return self._list_workflows()

        return {
            "actions": ["status", "generate", "list_templates", "list_workflows"],
            "hint": "PPT Master: SVG-based editable PPTX with native charts, animations, speaker notes audio. "
                    "Use action=generate with topic + slides_data, or use the ppt-master skill directly for full pipeline."
        }

    def _status(self):
        """Check ppt-master skill availability."""
        skill_exists = os.path.exists(os.path.join(SKILL_DIR, "SKILL.md"))
        scripts_count = len([f for f in os.listdir(SCRIPTS_DIR) if f.endswith(".py")]) if os.path.exists(SCRIPTS_DIR) else 0

        # Check python-pptx
        try:
            import pptx
            pptx_available = True
        except ImportError:
            pptx_available = False

        return {
            "status": "ok",
            "engine": "PPT Master (github.com/hugohe3/ppt-master)",
            "skill_installed": skill_exists,
            "scripts_available": scripts_count,
            "python_pptx": pptx_available,
            "capabilities": [
                "Native editable PPTX (not images)",
                "SVG-based slide generation",
                "Editable charts & tables (change data in PowerPoint)",
                "Animations & transitions",
                "Speaker notes with audio narration (TTS)",
                "Custom .pptx template support",
                "Multi-role AI collaboration (Strategist → Executor → QA)",
                "Multiple color palettes & rendering styles",
                "AI image generation & search",
                "Source document parsing (PDF/DOCX/URL/Markdown)",
            ],
            "pipeline": "Source → Create Project → [Template] → Strategist → [Image_Generator] → Executor → Quality Check → Post-processing → Export PPTX",
        }

    async def _generate(self, input: dict) -> dict:
        """Generate PPTX using ppt-master pipeline.
        This delegates to the ppt-master skill scripts for SVG generation + PPTX export."""
        topic = input.get("topic", "").strip()
        slides_data = input.get("slides", [])
        theme = input.get("theme", "academic")
        language = input.get("language", "English")
        template_path = input.get("template_path", "")
        source_file = input.get("source_file", "")

        if not topic and not slides_data and not source_file:
            return {"success": False, "error": "Provide 'topic' or 'slides' or 'source_file'"}

        # Auto-store to KB
        try:
            from modules.knowledge.auto_store import auto_store
            auto_store("ppt_master", f"PPT Generation: {topic[:40]}", {
                "topic": topic, "slides": len(slides_data), "theme": theme,
                "has_source": bool(source_file), "has_template": bool(template_path),
            }, source="PPT Master", tags=["faculty", "ppt", "slides"])
        except Exception:
            pass

        # If slides_data provided directly, generate PPTX immediately
        if slides_data:
            return self._generate_from_slides(slides_data, topic or "Presentation", theme)

        # Otherwise, return instructions for full pipeline via the skill
        return {
            "success": True,
            "message": "Use the ppt-master skill for full SVG pipeline generation.",
            "skill": "ppt-master",
            "instructions": (
                f"Load the ppt-master skill and generate a presentation on: {topic}. "
                f"Theme: {theme}, Language: {language}. "
                + (f"Use template: {template_path}. " if template_path else "")
                + (f"Parse source: {source_file}. " if source_file else "")
                + "Follow the full pipeline: Strategist → Executor → Quality Check → Export PPTX."
            ),
            "skill_path": SKILL_DIR,
        }

    def _generate_from_slides(self, slides_data, title, theme_name):
        """Generate editable PPTX directly from structured slide data using python-pptx."""
        try:
            from pptx import Presentation
            from pptx.util import Inches, Pt, Emu
            from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
            from pptx.dml.color import RGBColor
        except ImportError:
            return {"success": False, "error": "python-pptx not installed"}

        themes = {
            "academic": {"bg": "FFFFFF", "title": "1a365d", "accent": "2563eb", "text": "1a202c", "subtitle": "4a5568"},
            "clinical": {"bg": "FAFAFA", "title": "0d4d4d", "accent": "0d9488", "text": "1a202c", "subtitle": "4a5568"},
            "corporate": {"bg": "FFFFFF", "title": "111827", "accent": "3b82f6", "text": "1a202c", "subtitle": "4a5568"},
            "minimal": {"bg": "FFFFFF", "title": "111827", "accent": "111827", "text": "1a202c", "subtitle": "4a5568"},
            "dark": {"bg": "0f172a", "title": "f8fafc", "accent": "38bdf8", "text": "e2e8f0", "subtitle": "94a3b8"},
        }
        theme = themes.get(theme_name, themes["academic"])

        prs = Presentation()
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)

        for idx, slide_data in enumerate(slides_data):
            layout = prs.slide_layouts[6]  # Blank
            slide = prs.slides.add_slide(layout)
            self._build_slide(slide, slide_data, theme, idx, len(slides_data))

        # Speaker notes
        for slide, data in zip(prs.slides, slides_data):
            if data.get("notes"):
                slide.notes_slide.notes_text_frame.text = data["notes"]

        # Save
        output_path = os.path.join(tempfile.gettempdir(), f"pptmaster_{title[:20].replace(' ','_')}.pptx")
        prs.save(output_path)

        with open(output_path, "rb") as f:
            pptx_bytes = f.read()

        return Response(
            response=pptx_bytes,
            status=200,
            mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={"Content-Disposition": f'attachment; filename="{title[:30].replace(" ","_")}.pptx"'}
        )

    def _build_slide(self, slide, data, theme, idx, total):
        """Build slide with native shapes."""
        bg = RGBColor.from_string(theme["bg"])
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = bg

        slide_type = data.get("type", "content")

        if slide_type == "title":
            self._build_title(slide, data, theme)
        elif slide_type == "section":
            self._build_section(slide, data, theme)
        elif slide_type == "chart":
            self._build_chart(slide, data, theme)
        elif slide_type == "two_column":
            self._build_two_column(slide, data, theme)
        else:
            self._build_content(slide, data, theme)

        self._add_slide_number(slide, idx + 1, total, theme)

    def _build_title(self, slide, data, theme):
        box = slide.shapes.add_textbox(Inches(1), Inches(2.2), Inches(11), Inches(1.5))
        tf = box.text_frame; tf.word_wrap = True
        p = tf.paragraphs[0]; p.text = data.get("title", "")
        p.font.size = Pt(36); p.font.bold = True
        p.font.color.rgb = RGBColor.from_string(theme["title"])
        p.alignment = PP_ALIGN.CENTER

        if data.get("subtitle"):
            sub = slide.shapes.add_textbox(Inches(2), Inches(3.9), Inches(9), Inches(1))
            tf2 = sub.text_frame; tf2.word_wrap = True
            p2 = tf2.paragraphs[0]; p2.text = data["subtitle"]
            p2.font.size = Pt(18)
            p2.font.color.rgb = RGBColor.from_string(theme["subtitle"])
            p2.alignment = PP_ALIGN.CENTER

    def _build_section(self, slide, data, theme):
        accent = RGBColor.from_string(theme["accent"])
        bar = slide.shapes.add_shape(1, Inches(0), Inches(2.8), Inches(13.333), Inches(2))
        bar.fill.solid(); bar.fill.fore_color.rgb = accent
        bar.line.fill.background()

        box = slide.shapes.add_textbox(Inches(0.8), Inches(2.8), Inches(11.5), Inches(2))
        tf = box.text_frame; tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]; p.text = data.get("title", "")
        p.font.size = Pt(32); p.font.bold = True
        p.font.color.rgb = RGBColor.from_string("FFFFFF")
        p.alignment = PP_ALIGN.CENTER

    def _build_content(self, slide, data, theme):
        box = slide.shapes.add_textbox(Inches(0.6), Inches(0.3), Inches(12), Inches(1))
        tf = box.text_frame; tf.word_wrap = True
        p = tf.paragraphs[0]; p.text = data.get("title", "")
        p.font.size = Pt(28); p.font.bold = True
        p.font.color.rgb = RGBColor.from_string(theme["title"])

        body = slide.shapes.add_textbox(Inches(0.6), Inches(1.5), Inches(12), Inches(5.5))
        tf2 = body.text_frame; tf2.word_wrap = True

        bullets = data.get("bullets", [])
        if isinstance(bullets, str): bullets = [bullets]
        for i, bullet in enumerate(bullets):
            p = tf2.paragraphs[0] if i == 0 else tf2.add_paragraph()
            p.text = bullet; p.font.size = Pt(16)
            p.font.color.rgb = RGBColor.from_string(theme["text"])
            p.space_after = Pt(6)

    def _build_chart(self, slide, data, theme):
        self._build_content(slide, data, theme)
        table_data = data.get("table", [])
        if table_data and len(table_data) > 1:
            rows, cols = len(table_data), len(table_data[0])
            tbl = slide.shapes.add_table(rows, cols, Inches(0.6), Inches(3.5), Inches(12), Inches(3))
            for r, row in enumerate(table_data):
                for c, cell in enumerate(row):
                    tbl.table.cell(r, c).text = str(cell)
                    for para in tbl.table.cell(r, c).text_frame.paragraphs:
                        para.font.size = Pt(12)
                        para.font.color.rgb = RGBColor.from_string(theme["text"])

    def _build_two_column(self, slide, data, theme):
        box = slide.shapes.add_textbox(Inches(0.6), Inches(0.3), Inches(12), Inches(1))
        tf = box.text_frame; tf.word_wrap = True
        p = tf.paragraphs[0]; p.text = data.get("title", "")
        p.font.size = Pt(28); p.font.bold = True
        p.font.color.rgb = RGBColor.from_string(theme["title"])

        left = data.get("left", {})
        right = data.get("right", {})

        left_box = slide.shapes.add_textbox(Inches(0.6), Inches(1.5), Inches(5.8), Inches(5.5))
        ltf = left_box.text_frame; ltf.word_wrap = True
        if left.get("title"):
            lp = ltf.paragraphs[0]; lp.text = left["title"]
            lp.font.size = Pt(20); lp.font.bold = True
            lp.font.color.rgb = RGBColor.from_string(theme["accent"])
        for bullet in left.get("bullets", []):
            lp = ltf.add_paragraph(); lp.text = bullet; lp.font.size = Pt(14)
            lp.font.color.rgb = RGBColor.from_string(theme["text"])

        right_box = slide.shapes.add_textbox(Inches(6.9), Inches(1.5), Inches(5.8), Inches(5.5))
        rtf = right_box.text_frame; rtf.word_wrap = True
        if right.get("title"):
            rp = rtf.paragraphs[0]; rp.text = right["title"]
            rp.font.size = Pt(20); rp.font.bold = True
            rp.font.color.rgb = RGBColor.from_string(theme["accent"])
        for bullet in right.get("bullets", []):
            rp = rtf.add_paragraph(); rp.text = bullet; rp.font.size = Pt(14)
            rp.font.color.rgb = RGBColor.from_string(theme["text"])

    def _add_slide_number(self, slide, num, total, theme):
        box = slide.shapes.add_textbox(Inches(12.3), Inches(7.0), Inches(1), Inches(0.4))
        tf = box.text_frame
        p = tf.paragraphs[0]; p.text = f"{num}/{total}"
        p.font.size = Pt(10)
        p.font.color.rgb = RGBColor.from_string(theme["subtitle"])
        p.alignment = PP_ALIGN.RIGHT

    def _list_templates(self):
        """List available ppt-master templates."""
        templates_dir = os.path.join(SKILL_DIR, "templates")
        templates = []
        if os.path.exists(templates_dir):
            for item in os.listdir(templates_dir):
                item_path = os.path.join(templates_dir, item)
                if os.path.isdir(item_path):
                    templates.append({"name": item, "path": item_path})
        return {"status": "ok", "templates": templates}

    def _list_workflows(self):
        """List available ppt-master workflows."""
        workflows_dir = os.path.join(SKILL_DIR, "workflows")
        workflows = []
        if os.path.exists(workflows_dir):
            for f in os.listdir(workflows_dir):
                if f.endswith(".md"):
                    workflows.append({"name": f.replace(".md", ""), "path": os.path.join(workflows_dir, f)})
        return {"status": "ok", "workflows": workflows}
