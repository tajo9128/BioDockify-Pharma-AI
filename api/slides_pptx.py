"""PPTX Slides Generator — SVG→DrawingML native PPTX conversion using ppt-master engine."""
from helpers.api import ApiHandler, Request, Response
from helpers import files
import os, sys, logging, tempfile, json

log = logging.getLogger("slides_pptx")

# Ensure svg_to_pptx engine is on path
_ENGINE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "modules", "slides", "svg_to_pptx")
if os.path.isdir(_ENGINE_DIR):
    sys.path.insert(0, os.path.dirname(_ENGINE_DIR))


class SlidesPptx(ApiHandler):
    """Convert SVG slide files to native editable PowerPoint (.pptx)."""

    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "convert")

        if action == "convert":
            svg_dir = input.get("svg_dir", "")
            output_name = input.get("output_name", "presentation")
            if not svg_dir or not os.path.isdir(svg_dir):
                return {"success": False, "error": "svg_dir required — path to directory containing SVG slide files"}

            try:
                from svg_to_pptx import pptx_cli
                out_dir = input.get("output_dir", os.path.join(os.path.dirname(svg_dir), "exports"))
                os.makedirs(out_dir, exist_ok=True)
                output_path = os.path.join(out_dir, f"{output_name}.pptx")

                result = pptx_cli.convert_svgs_to_pptx(svg_dir, output_path)
                return {
                    "success": True,
                    "output_path": output_path,
                    "output_name": f"{output_name}.pptx",
                    "slides": result.get("slides", 0),
                    "download_url": f"/api/workdir_download?path={output_path}",
                }
            except ImportError:
                return {"success": False, "error": "python-pptx not available. Install: pip install python-pptx svglib reportlab"}
            except Exception as e:
                log.exception("PPTX conversion failed")
                return {"success": False, "error": str(e)}

        if action == "info":
            return {
                "module": "slides_pptx",
                "engine": "svg_to_pptx (ppt-master core)",
                "requires": ["python-pptx>=0.6.21", "svglib>=1.5.0", "reportlab>=4.0.0"],
                "capabilities": [
                    "SVG → native DrawingML PPTX (real shapes, not images)",
                    "Per-element entrance animations + page transitions",
                    "Speaker notes from SVG metadata",
                    "Narration audio embedding (edge-tts)",
                    "Dual PNG+SVG format (Office 2016+ compatibility)",
                    "Layout packs: right-column, split, horizontal-flow, top-center"
                ],
            }

        return {"error": f"Unknown action: {action}"}
