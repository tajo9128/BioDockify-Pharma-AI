"""Deck visuals — icon matching + editable diagram helpers.

Icons come from the vendored ppt-master icon libraries (6,000+ SVGs with
`tags:` metadata in an HTML comment header). Matched per-slide by keyword;
rendered into the deck as native PowerPoint shapes where practical
(see deck_pipeline assemble: icons are rasterized to PNG only when no
in-image rasterizer exists — text and diagrams stay fully editable).
"""
import logging
import os
import re
import threading
from functools import lru_cache
from html import unescape
from pathlib import Path

log = logging.getLogger("slides.visuals")

ICONS_ROOT = Path(__file__).resolve().parents[2] / "skills" / "ppt-master" / "templates" / "icons"
_FAMILIES = ("tabler-outline", "phosphor-duotone", "tabler-filled", "chunk-filled", "simple-icons")

# Domain keyword → icon-name hints for pharma/teaching decks (fast path)
_HINTS = {
    "drug": "pill", "medicine": "pill", "tablet": "pill", "dose": "pill", "dosage": "pill",
    "molecule": "molecule", "compound": "molecule", "chemistry": "flask-2", "chemical": "flask-2",
    "protein": "dna", "gene": "dna", "genetic": "dna", "dna": "dna", "rna": "dna",
    "brain": "brain", "mind": "brain", "neuro": "brain", "cns": "brain",
    "heart": "heart-rate-monitor", "cardiovascular": "heart-rate-monitor", "cardiac": "heart-rate-monitor",
    "search": "search", "study": "book-2", "research": "microscope", "science": "microscope",
    "experiment": "flask", "lab": "test-pipe-2", "test": "test-pipe-2", "trial": "test-pipe-2",
    "data": "chart-bar", "statistics": "chart-bar", "result": "chart-dots", "analysis": "chart-dots",
    "patient": "user", "human": "user", "people": "users-group", "population": "users-group",
    "disease": "biohazard", "infection": "biohazard", "virus": "biohazard", "bacteria": "biohazard",
    "hospital": "building-hospital", "clinic": "building-hospital", "healthcare": "building-hospital",
    "target": "target-arrow", "goal": "target-arrow", "receptor": "target-arrow",
    "warning": "alert-triangle", "risk": "alert-triangle", "side effect": "alert-triangle", "toxic": "biohazard",
    "time": "clock-hour-4", "duration": "clock-hour-4", "kinetics": "clock-hour-4",
    "absorption": "arrow-down", "distribution": "arrows-split-2", "metabolism": "arrows-shuffle",
    "excretion": "arrow-up-right", "adme": "arrows-right-left",
    "money": "coin", "cost": "coin", "market": "building-store", "business": "briefcase-2",
    "computer": "device-desktop", "software": "device-desktop", "ai": "cpu", "model": "cpu",
    "list": "list", "summary": "align-box-left-top", "introduction": "door-enter", "conclusion": "flag-3",
    "question": "help-circle", "answer": "message-circle", "note": "notebook", "reference": "book",
    "global": "world", "public": "world", "water": "droplets", "environment": "leaf", "plant": "plant-2",
    "food": "apple", "injection": "syringe", "vaccine": "syringe", "cream": "bottle",
}

_lock = threading.Lock()


@lru_cache(maxsize=1)
def _icon_index() -> list[tuple[str, str, str]]:
    """[(family, name, tags-lowercased)] for every icon with metadata."""
    idx = []
    for fam in _FAMILIES:
        d = ICONS_ROOT / fam
        if not d.is_dir():
            continue
        for f in d.glob("*.svg"):
            try:
                head = f.read_text(encoding="utf-8", errors="ignore")[:600]
                mt = re.search(r"tags:\s*\[([^\]]*)\]", head)
                tags = unescape(mt.group(1)).lower() if mt else ""
                idx.append((fam, f.stem, f"{f.stem} {tags}"))
            except Exception:
                continue
    log.info("icon index: %d icons", len(idx))
    return idx


def match_icon(keywords: str) -> Path | None:
    """Best icon for a slide's keywords (hint table → tag search → stem match)."""
    kw = (keywords or "").lower().strip()
    if not kw:
        return None
    with _lock:
        index = _icon_index()
    # 1) domain hints
    for k, name in _HINTS.items():
        if k in kw:
            for fam, stem, _t in index:
                if stem == name:
                    return ICONS_ROOT / fam / f"{stem}.svg"
            # prefix fallback (name-2-off etc.)
            for fam, stem, _t in index:
                if stem.startswith(name):
                    return ICONS_ROOT / fam / f"{stem}.svg"
    # 2) token match against tags (prefer tabler-outline)
    tokens = [t for t in re.split(r"[^a-z0-9]+", kw) if len(t) > 3]
    best, best_score = None, 0
    for fam, stem, tags in index:
        if fam == "simple-icons":
            continue  # brand logos — not slide art
        score = sum(1 for t in tokens if t in tags)
        if fam == "tabler-outline":
            score += 0.5
        if score > best_score:
            best, best_score = (fam, stem), score
    if best and best_score >= 1:
        return ICONS_ROOT / best[0] / f"{best[1]}.svg"
    return None


def icon_svg_bytes(path: Path, color: str = "#4C2A85", size: int = 128) -> bytes | None:
    """Read an icon SVG and recolor/resize it for embedding."""
    try:
        svg = path.read_text(encoding="utf-8", errors="ignore")
        svg = re.sub(r'width="\d+"', f'width="{size}"', svg, count=1)
        svg = re.sub(r'height="\d+"', f'height="{size}"', svg, count=1)
        svg = svg.replace("currentColor", color)
        return svg.encode("utf-8")
    except Exception:
        return None


# ── Editable native diagram builders (pure python-pptx shapes) ───────────────

def add_process_diagram(slide, prs, steps: list[str], x: float, y: float, w: float, h: float,
                        color: str = "4C2A85", accent: str = "F97362") -> None:
    """Chevron-style process flow built from native PPT shapes (fully editable)."""
    from pptx.util import Emu, Pt
    n = max(len(steps), 1)
    gap = Emu(int(w * 0.012))
    bw = Emu(int((w - gap * (n - 1)) / n))
    bh = Emu(int(h * 0.55))
    from pptx.enum.shapes import MSO_SHAPE
    for i, s in enumerate(steps[:7]):
        shp = slide.shapes.add_shape(MSO_SHAPE.PENTAGON, Emu(int(x + i * (bw + gap))), Emu(int(y + h * 0.22)), bw, bh)
        shp.fill.solid()
        shp.fill.fore_color.rgb = __import__("pptx.dml.color", fromlist=["RGBColor"]).RGBColor.from_string(accent if i == n - 1 else color)
        shp.line.fill.background()
        tf = shp.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = s[:40]
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = __import__("pptx.dml.color", fromlist=["RGBColor"]).RGBColor.from_string("FFFFFF")
        tf.margin_left = tf.margin_right = Emu(45720)


def add_stat_card(slide, prs, value: str, label: str, x: float, y: float, w: float, h: float,
                  color: str = "4C2A85") -> None:
    """Big-number stat card from native rounded-rect + text frames."""
    from pptx.util import Emu, Pt
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.dml.color import RGBColor
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Emu(int(x)), Emu(int(y)), Emu(int(w)), Emu(int(h)))
    card.fill.solid()
    card.fill.fore_color.rgb = RGBColor.from_string("FFFFFF")
    card.line.color.rgb = RGBColor.from_string("E4DCF5")
    card.shadow.inherit = False
    tv = slide.shapes.add_textbox(Emu(int(x + w * 0.05)), Emu(int(y + h * 0.08)), Emu(int(w * 0.9)), Emu(int(h * 0.5)))
    pv = tv.text_frame.paragraphs[0]
    pv.text = value[:12]
    pv.font.size = Pt(30)
    pv.font.bold = True
    pv.font.color.rgb = RGBColor.from_string(color)
    tl = slide.shapes.add_textbox(Emu(int(x + w * 0.05)), Emu(int(y + h * 0.58)), Emu(int(w * 0.9)), Emu(int(h * 0.38)))
    pl = tl.text_frame.paragraphs[0]
    pl.text = label[:60]
    pl.font.size = Pt(11)
    pl.font.color.rgb = RGBColor.from_string("6E6590")


def icon_png(path: Path, color: str, size: int = 160) -> bytes | None:
    """Rasterize an icon SVG to PNG via the vendored renderer
    (cairosvg/svglib; see svg_to_pptx.pptx_media). PNG icons are the only
    non-native element; everything else in the deck stays editable."""
    svg = icon_svg_bytes(path, color, size)
    if not svg:
        return None
    import tempfile, os as _os
    from modules.slides.svg_to_pptx.pptx_media import convert_svg_to_png
    with tempfile.TemporaryDirectory() as td:
        sp, pp = _os.path.join(td, "i.svg"), _os.path.join(td, "i.png")
        with open(sp, "wb") as f:
            f.write(svg)
        if convert_svg_to_png(Path(sp), Path(pp), width=size, height=size):
            with open(pp, "rb") as fo:
                return fo.read()
    return None
