"""Slides PPTX Tool — agent generates native editable PowerPoint presentations from research."""
from helpers.tool import Tool, Response
import os, sys

_ENGINE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "modules", "slides", "svg_to_pptx")
if os.path.isdir(_ENGINE_DIR):
    sys.path.insert(0, os.path.dirname(_ENGINE_DIR))


class SlidesPptxTool(Tool):
    async def execute(self, action: str = "convert", **kwargs):

        if action == "convert":
            svg_dir = kwargs.get("svg_dir", "")
            output_name = kwargs.get("output_name", "presentation")
            if not svg_dir or not os.path.isdir(svg_dir):
                return Response(
                    message="Provide svg_dir (path to directory with SVG slide files) and output_name.",
                    break_loop=False
                )

            try:
                from svg_to_pptx import pptx_cli
                out_dir = os.path.join(os.path.dirname(svg_dir), "exports")
                os.makedirs(out_dir, exist_ok=True)
                output_path = os.path.join(out_dir, f"{output_name}.pptx")
                result = pptx_cli.convert_svgs_to_pptx(svg_dir, output_path)
                slides = result.get("slides", 0)
                return Response(
                    message=f"PPTX generated: {output_path}\nSlides: {slides}\nFormat: Native DrawingML (real shapes, editable in PowerPoint)",
                    break_loop=False
                )
            except ImportError:
                return Response(
                    message="python-pptx not installed. Run: pip install python-pptx svglib reportlab",
                    break_loop=False
                )
            except Exception as e:
                return Response(message=f"PPTX conversion failed: {str(e)}", break_loop=False)

        if action == "design":
            topic = kwargs.get("topic", "Research Presentation")
            slides_count = kwargs.get("slides", 6)
            lines = [f"Slide Design Plan: {topic}", "=" * 40]
            lines.append(f"Target: {slides_count} slides (16:9 format)")
            lines.append("")
            lines.append("Design Instructions:")
            lines.append("1. Create a workdir/{topic}/ directory")
            lines.append("2. Design SVG slides using standard 16:9 canvas (1280x720px)")
            lines.append("3. Each SVG file named slide_01.svg, slide_02.svg, ...")
            lines.append("4. Use python-pptx compatible SVG (basic shapes, text, gradients)")
            lines.append("5. Add speaker notes via <desc> element in each SVG")
            lines.append("6. When ready, call: SlidesPptx action=convert svg_dir=workdir/{topic}/ output_name={topic}")
            lines.append("")
            lines.append("Recommended structure:")
            lines.append("  Slide 1: Title slide (topic + subtitle)")
            lines.append("  Slide 2: Outline/Agenda")
            for i in range(3, slides_count + 1):
                if i == slides_count:
                    lines.append(f"  Slide {i}: Summary/Conclusions")
                else:
                    lines.append(f"  Slide {i}: Content section {i-2}")
            return Response(message="\n".join(lines), break_loop=False)

        return Response(
            message="SlidesPptx actions: convert (SVGs→PPTX), design (get template plan). Use: SlidesPptx action=convert svg_dir=DIR output_name=NAME",
            break_loop=False
        )
