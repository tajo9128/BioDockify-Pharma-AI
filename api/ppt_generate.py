"""PPT Generator API — native editable PPTX via python-pptx.

Generates real PowerPoint files with native shapes, text boxes, and charts.
All elements are directly clickable and editable in PowerPoint.

Inspired by PPT-Master (github.com/hugohe3/ppt-master)."""
from helpers.api import ApiHandler, Request, Response
import logging, os, tempfile, io, json

log = logging.getLogger("ppt_generate")

try:
    from pptx import Presentation
    from pptx.util import Inches, Pt, Emu
    from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
    from pptx.dml.color import RGBColor
    HAS_PPTX = True
except ImportError:
    HAS_PPTX = False


# ── Theme presets ──
THEMES = {
    "academic": {"bg": "#FFFFFF", "title": "#1a365d", "accent": "#2563eb", "text": "#1a202c", "subtitle": "#4a5568"},
    "clinical": {"bg": "#FAFAFA", "title": "#0d4d4d", "accent": "#0d9488", "text": "#1a202c", "subtitle": "#4a5568"},
    "corporate": {"bg": "#FFFFFF", "title": "#111827", "accent": "#3b82f6", "text": "#1a202c", "subtitle": "#4a5568"},
    "minimal": {"bg": "#FFFFFF", "title": "#111827", "accent": "#111827", "text": "#1a202c", "subtitle": "#4a5568"},
    "dark": {"bg": "#0f172a", "title": "#f8fafc", "accent": "#38bdf8", "text": "#e2e8f0", "subtitle": "#94a3b8"},
}


class PptGenerateHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        if not HAS_PPTX:
            return {"success": False, "error": "python-pptx not installed. Run: pip install python-pptx"}

        action = input.get("action", "generate")

        if action == "generate":
            return self._generate_pptx(input)
        elif action == "themes":
            return {"success": True, "themes": list(THEMES.keys())}

        return {"success": False, "error": f"Unknown action: {action}"}

    def _generate_pptx(self, input: dict) -> dict | Response:
        """Generate a native editable PPTX from structured slide data."""
        slides_data = input.get("slides", [])
        theme_name = input.get("theme", "academic")
        title = input.get("title", "BioDockify Presentation")
        include_notes = input.get("include_notes", True)

        if not slides_data:
            return {"success": False, "error": "No slides data provided"}

        theme = THEMES.get(theme_name, THEMES["academic"])
        prs = Presentation()
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)

        for idx, slide_data in enumerate(slides_data):
            layout = prs.slide_layouts[6]  # Blank layout
            slide = prs.slides.add_slide(layout)
            self._build_slide(slide, slide_data, theme, idx, len(slides_data))

        # Add speaker notes if provided
        if include_notes and any(s.get("notes") for s in slides_data):
            for slide, data in zip(prs.slides, slides_data):
                if data.get("notes"):
                    notes_slide = slide.notes_slide
                    notes_slide.notes_text_frame.text = data["notes"]

        # Save to temp file
        output_path = os.path.join(tempfile.gettempdir(), f"biodockify_{title[:20].replace(' ','_')}.pptx")
        prs.save(output_path)

        # Read bytes for download
        with open(output_path, "rb") as f:
            pptx_bytes = f.read()

        return Response(
            response=pptx_bytes,
            status=200,
            mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={"Content-Disposition": f'attachment; filename="{title[:30].replace(" ", "_")}.pptx"'}
        )

    def _build_slide(self, slide, data, theme, idx, total):
        """Build a single slide with native PPTX shapes."""
        bg_color = RGBColor.from_string(theme["bg"].lstrip("#"))
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = bg_color

        slide_type = data.get("type", "content")

        if slide_type == "title":
            self._build_title_slide(slide, data, theme)
        elif slide_type == "section":
            self._build_section_slide(slide, data, theme)
        elif slide_type == "chart":
            self._build_chart_slide(slide, data, theme)
        else:
            self._build_content_slide(slide, data, theme)

        # Add slide number
        self._add_slide_number(slide, idx + 1, total, theme)

    def _build_title_slide(self, slide, data, theme):
        """Title slide with centered title and subtitle."""
        w, h = slide.part.slide_layout.slide_master.part.slide_master.slide_width, slide.part.slide_layout.slide_master.part.slide_master.slide_height
        title_box = slide.shapes.add_textbox(Inches(1), Inches(2.2), Inches(11), Inches(1.5))
        tf = title_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = data.get("title", "")
        p.font.size = Pt(36)
        p.font.bold = True
        p.font.color.rgb = RGBColor.from_string(theme["title"].lstrip("#"))
        p.alignment = PP_ALIGN.CENTER

        sub_box = slide.shapes.add_textbox(Inches(2), Inches(3.9), Inches(9), Inches(1))
        tf2 = sub_box.text_frame
        tf2.word_wrap = True
        p2 = tf2.paragraphs[0]
        p2.text = data.get("subtitle", "")
        p2.font.size = Pt(18)
        p2.font.color.rgb = RGBColor.from_string(theme["subtitle"].lstrip("#"))
        p2.alignment = PP_ALIGN.CENTER

    def _build_section_slide(self, slide, data, theme):
        """Section divider slide with colored accent bar."""
        accent = RGBColor.from_string(theme["accent"].lstrip("#"))
        accent_box = slide.shapes.add_shape(1, Inches(0), Inches(2.8), Inches(13.333), Inches(2))
        accent_box.fill.solid()
        accent_box.fill.fore_color.rgb = accent

        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(2.8), Inches(11.5), Inches(2))
        tf = title_box.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]
        p.text = data.get("title", "")
        p.font.size = Pt(32)
        p.font.bold = True
        p.font.color.rgb = RGBColor.from_string("FFFFFF")
        p.alignment = PP_ALIGN.CENTER

    def _build_content_slide(self, slide, data, theme):
        """Standard content slide with title + bullets."""
        title_box = slide.shapes.add_textbox(Inches(0.6), Inches(0.3), Inches(12), Inches(1))
        tf = title_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = data.get("title", "")
        p.font.size = Pt(28)
        p.font.bold = True
        p.font.color.rgb = RGBColor.from_string(theme["title"].lstrip("#"))

        body_box = slide.shapes.add_textbox(Inches(0.6), Inches(1.5), Inches(12), Inches(5.5))
        tf2 = body_box.text_frame
        tf2.word_wrap = True

        bullets = data.get("bullets", [])
        if isinstance(bullets, str):
            bullets = [bullets]

        for i, bullet in enumerate(bullets):
            if i == 0:
                p = tf2.paragraphs[0]
            else:
                p = tf2.add_paragraph()
            p.text = bullet
            p.font.size = Pt(16)
            p.font.color.rgb = RGBColor.from_string(theme["text"].lstrip("#"))
            p.space_after = Pt(6)
            p.level = 0

        # Add accent line
        accent = RGBColor.from_string(theme["accent"].lstrip("#"))
        line = slide.shapes.add_shape(1, Inches(0.6), Inches(1.25), Inches(3), Inches(2))
        line.fill.solid()
        line.fill.fore_color.rgb = accent

    def _build_chart_slide(self, slide, data, theme):
        """Slide with a data table (chart placeholder)."""
        self._build_content_slide(slide, data, theme)
        # Add data table below bullets if present
        table_data = data.get("table")
        if table_data and len(table_data) > 1:
            rows = len(table_data)
            cols = len(table_data[0])
            table_shape = slide.shapes.add_table(rows, cols, Inches(0.6), Inches(3.5), Inches(12), Inches(3))
            table = table_shape.table
            for r, row in enumerate(table_data):
                for c, cell in enumerate(row):
                    table.cell(r, c).text = str(cell)
                    for para in table.cell(r, c).text_frame.paragraphs:
                        para.font.size = Pt(12)
                        para.font.color.rgb = RGBColor.from_string(theme["text"].lstrip("#"))

    def _add_slide_number(self, slide, num, total, theme):
        """Add slide number to bottom-right."""
        num_box = slide.shapes.add_textbox(Inches(12.3), Inches(7.0), Inches(1), Inches(0.4))
        tf = num_box.text_frame
        p = tf.paragraphs[0]
        p.text = f"{num}/{total}"
        p.font.size = Pt(10)
        p.font.color.rgb = RGBColor.from_string(theme["subtitle"].lstrip("#"))
        p.alignment = PP_ALIGN.RIGHT
