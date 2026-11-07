"""Deck pipeline — internet research → outline → detailed content → editable PPTX.

Job model mirrors MD Lite: /a0/tmp/deck_jobs/<id>/{status.json, sources.json,
outline.json, content/*.json, deck.pptx}. Batches checkpoint so a 100-slide
run survives restarts. All text lands in real text frames (editable); icons
are PNG; diagrams are native shapes.
"""
import json
import logging
import os
import re
import threading
import traceback
import uuid
from datetime import datetime
from pathlib import Path

log = logging.getLogger("slides.deck")

JOBS_ROOT = Path("/a0/tmp/deck_jobs") if os.name != "nt" else Path(os.environ.get("DECK_JOBS_ROOT", "tmp/deck_jobs"))
BATCH = 8
MAX_SLIDES = 100

TEMPLATES = {
    "violet_academic": {"name": "Violet Academic", "bg": "F7F5FC", "panel": "FFFFFF", "primary": "4C2A85",
                        "accent": "F97362", "muted": "6E6590", "head_font": "Georgia", "body_font": "Segoe UI",
                        "desc": "Serif headings, lavender panels — lectures & defenses"},
    "mint_clinical": {"name": "Mint Clinical", "bg": "F4FBF9", "panel": "FFFFFF", "primary": "0F766E",
                      "accent": "F59E0B", "muted": "5B7A75", "head_font": "Georgia", "body_font": "Segoe UI",
                      "desc": "Calm teal — clinical, pharmacology, healthcare"},
    "slate_corporate": {"name": "Slate Corporate", "bg": "F4F6FA", "panel": "FFFFFF", "primary": "1E3A5F",
                        "accent": "2563EB", "muted": "64748B", "head_font": "Calibri", "body_font": "Calibri",
                      "desc": "Blue business — reports, reviews, industry"},
    "rose_research": {"name": "Rose Research", "bg": "FDF7F9", "panel": "FFFFFF", "primary": "9D174D",
                      "accent": "DB2777", "muted": "83707A", "head_font": "Georgia", "body_font": "Segoe UI",
                      "desc": "Warm rose — seminars, journal clubs"},
    "ink_minimal": {"name": "Ink Minimal", "bg": "FAFAF8", "panel": "FFFFFF", "primary": "18181B",
                    "accent": "EA580C", "muted": "71717A", "head_font": "Calibri", "body_font": "Calibri",
                    "desc": "Black & orange minimal — any topic"},
}

_jobs_lock = threading.Lock()
_threads: dict[str, threading.Thread] = {}


# ── LLM plumbing (uses the user's configured model, same as the agent) ───────

_llm = None
_llm_tried = False


def _get_llm():
    global _llm, _llm_tried
    if _llm_tried:
        return _llm
    _llm_tried = True
    try:
        from plugins._model_config.helpers.model_config import build_chat_model, build_utility_model
        try:
            _llm = build_chat_model()
        except Exception:
            _llm = build_utility_model()
        log.info("deck LLM ready: %s", type(_llm).__name__)
    except Exception as e:
        log.warning("deck LLM unavailable: %s", e)
    return _llm


def _invoke(llm, system: str, prompt: str, max_retries: int) -> str:
    for attempt in range(max_retries + 1):
        try:
            resp = llm.invoke([("system", system), ("human", prompt)])
            text = getattr(resp, "content", "") or ""
            if isinstance(text, list):
                text = "".join(str(p) for p in text)
            if text.strip():
                return text
        except Exception as e:
            log.warning("LLM attempt %d failed: %s", attempt + 1, str(e)[:160])
    return ""


def _ask(system: str, prompt: str, max_retries: int = 2) -> str:
    global _llm
    llm = _get_llm()
    if llm is None:
        return ""
    out = _invoke(llm, system, prompt, max_retries)
    if not out and not getattr(llm, "_deck_is_utility", False):
        # chat model auth/unavailable → fall back to the utility model
        try:
            from plugins._model_config.helpers.model_config import build_utility_model
            util = build_utility_model()
            if util is not None:
                util._deck_is_utility = True
                _llm = util  # stick with utility for the rest of the job
                out = _invoke(util, system, prompt, 1)
        except Exception as e:
            log.warning("utility model fallback failed: %s", e)
    return out


def _json_from(text: str) -> dict | list | None:
    """Extract the first JSON object/array from LLM output."""
    if not text:
        return None
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.M).strip()
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(text)):
            if text[i] == opener:
                depth += 1
            elif text[i] == closer:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except Exception:
                        break
        break
    return None


# ── Job management ─────────────────────────────────────────────────────────────

def _job_dir(job_id: str) -> Path:
    d = JOBS_ROOT / job_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write_status(job_id: str, **patch):
    with _jobs_lock:
        p = _job_dir(job_id) / "status.json"
        st = {}
        if p.exists():
            try:
                st = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                st = {}
        st.update(patch)
        st["updated"] = datetime.now().isoformat(timespec="seconds")
        p.write_text(json.dumps(st, indent=1), encoding="utf-8")


def read_status(job_id: str) -> dict:
    p = JOBS_ROOT / job_id / "status.json"
    if not p.exists():
        return {"error": "unknown job"}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"error": "corrupt status"}


def list_templates() -> list[dict]:
    return [{"id": k, **v} for k, v in TEMPLATES.items()]


def create_job(title: str, topic: str, num_slides: int, template_id: str,
               style: str = "academic", audience: str = "students",
               photos: bool = True, citations: bool = True) -> dict:
    job_id = uuid.uuid4().hex[:8]
    n = max(1, min(int(num_slides or 10), MAX_SLIDES))
    _write_status(job_id, title=title, topic=topic, num_slides=n,
                  template_id=template_id if template_id in TEMPLATES else "violet_academic",
                  style=style, audience=audience, photos=photos, citations=citations,
                  stage="queued", progress=0, detail="", slides_done=0,
                  outline=[], created=datetime.now().isoformat(timespec="seconds"))
    t = threading.Thread(target=_run_job, args=(job_id,), daemon=True)
    _threads[job_id] = t
    t.start()
    return {"job_id": job_id}


def _run_job(job_id: str):
    try:
        st = read_status(job_id)
        topic = st["topic"]
        n = st["num_slides"]

        # ── Stage 1: research (internet: PDFs, SlideShare, notes) ──
        _write_status(job_id, stage="research", progress=5, detail="searching the open web…")
        from modules.slides.deck_research import collect_sources
        sources = []
        try:
            sources = collect_sources(topic, target_chars=250_000,
                                      progress_cb=lambda m: _write_status(job_id, detail=m[:120]))
        except Exception as e:
            log.warning("research failed: %s", e)
        corpus_text = sum(len(s["text"]) for s in sources)
        _write_status(job_id, progress=25, detail=f"{len(sources)} sources · {corpus_text//1000}k chars")
        (_job_dir(job_id) / "sources.json").write_text(json.dumps(sources[:40]), encoding="utf-8")

        # ── Stage 2: outline ──
        _write_status(job_id, stage="outline", progress=28, detail="planning the deck…")
        outline = _make_outline(job_id, title=st["title"], topic=topic, n=n, sources=sources,
                                audience=st.get("audience", "students"))
        _write_status(job_id, progress=35, outline=[o["title"] for o in outline])

        # ── Stage 3: content in checkpointed batches ──
        _write_status(job_id, stage="content", progress=38)
        slides = _generate_content(job_id, outline, sources, topic, st)

        # ── Stage 4+5: visuals + assemble ──
        _write_status(job_id, stage="visuals", progress=82, detail="drawing icons & diagrams…")
        _write_status(job_id, stage="assemble", progress=90, detail="building the .pptx…")
        tpl = TEMPLATES[st["template_id"]]
        out = _job_dir(job_id) / "deck.pptx"
        _assemble(out, st["title"], slides, tpl, sources, photos=st.get("photos", True),
                  citations=st.get("citations", True))

        _write_status(job_id, stage="done", progress=100, detail=f"{len(slides)} slides ready",
                      slides_done=len(slides), file=str(out))
    except Exception as e:
        log.error("deck job %s failed: %s\n%s", job_id, e, traceback.format_exc())
        _write_status(job_id, stage="error", detail=str(e)[:300])


# ── Stage 2: outline ──────────────────────────────────────────────────────────

_TYPES = ("title", "toc", "section", "content", "two_column", "stats", "process", "quote", "reference", "ending")


def _make_outline(job_id, title, topic, n, sources, audience) -> list[dict]:
    p = _job_dir(job_id) / "outline.json"
    if p.exists():  # resume
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    src_brief = "\n".join(f"- {s['title']} ({s['kind']}, {len(s['text'])//1000}k chars)" for s in sources[:15])
    sys_p = ("You are a presentation architect. Reply with ONLY a JSON array — no prose, no markdown fences.")
    user = (f"Design a {n}-slide teaching deck titled \"{title}\" on \"{topic}\" for {audience}.\n"
            f"Available researched sources:\n{src_brief or '(none — rely on your knowledge)'}\n\n"
            f"Return exactly {n} items: [{{\"title\": str, \"type\": one of {json.dumps(_TYPES)}, \"icon_hint\": 1-3 keywords}}].\n"
            "Slide 1 must be type \"title\", slide 2 \"toc\", last slide \"ending\".\n"
            "Order slides into logical sections; include 1-3 \"section\" dividers for decks >20 slides.")
    data = _json_from(_ask(sys_p, user))
    items = data if isinstance(data, list) else []
    # sanitize + guarantee count/type structure
    clean = []
    for i in range(n):
        it = items[i] if i < len(items) and isinstance(items[i], dict) else {}
        t = it.get("type") if it.get("type") in _TYPES else "content"
        if i == 0:
            t = "title"
        elif i == 1 and n >= 4:
            t = "toc"
        elif i == n - 1:
            t = "ending"
        clean.append({"title": str(it.get("title") or (title if i == 0 else f"{topic} — part {i}"))[:110],
                      "type": t,
                      "icon_hint": str(it.get("icon_hint") or topic)[:60]})
    if not items:  # offline/no-LLM skeleton
        for i, c in enumerate(clean):
            if i not in (0, 1, n - 1):
                c["type"] = "section" if i % 10 == 2 and n > 20 else "content"
    p.write_text(json.dumps(clean), encoding="utf-8")
    return clean


# ── Stage 3: detailed, lengthy content in batches ──────────────────────────────

def _source_excerpt_for(sources, idx: int, n: int) -> str:
    """Round-robin source material so every batch sees relevant research."""
    if not sources:
        return "(no external sources — use your knowledge)"
    parts = []
    per = max(1, 18000 // max(1, BATCH))
    for k in range(BATCH):
        s = sources[(idx * BATCH + k) % len(sources)]
        parts.append(f"[{s['title'][:70]}] ({s['url'][:80]})\n{s['text'][:per]}")
    return "\n\n".join(parts)[:60000]


def _generate_content(job_id, outline, sources, topic, st) -> list[dict]:
    cdir = _job_dir(job_id) / "content"
    cdir.mkdir(exist_ok=True)
    slides: list[dict] = []
    for i, o in enumerate(outline):
        p = cdir / f"{i:03d}.json"
        if p.exists():
            try:
                slides.append(json.loads(p.read_text(encoding="utf-8")))
                continue
            except Exception:
                pass
        slides.append({**o, "index": i, "bullets": [], "body": "", "notes": ""})

    total = len(outline)
    for b0 in range(0, total, BATCH):
        batch = slides[b0:b0 + BATCH]
        pending = [s for s in batch if not s.get("body")]
        if pending:
            sys_p = ("You write DETAILED teaching-slide content. Reply with ONLY a JSON array — no prose, "
                     "no markdown fences. Text must be plain (no markdown symbols).")
            brief = "\n".join(f"{i}. \"{s['title']}' [{s['type']}]" for i, s in enumerate(pending))
            user = (f"Deck topic: {topic}. Audience: {st.get('audience','students')}.\n"
                    f"Researched material (cite facts from it where relevant):\n"
                    f"{_source_excerpt_for(sources, b0 // BATCH, total)}\n\n"
                    f"Write content for these slides (batch positions {b0}-{b0+len(pending)-1}):\n{brief}\n\n"
                    "For EACH slide return: {\"i\": position, \"title\": improved title (<=90 chars), "
                    "\"bullets\": [4-6 punchy bullets <=110 chars each], "
                    "\"body\": 2-3 detailed paragraphs (120-200 words TOTAL, substantive, specific, "
                    "readable on a slide as small print), "
                    "\"notes\": speaker notes 60-120 words, "
                    "\"icon_hint\": 1-3 icon keywords, "
                    "\"chart\": optional {\"kind\":\"bar|process|stats\",\"data\":...}}.")
            data = _json_from(_ask(sys_p, user))
            by_i = {}
            if isinstance(data, list):
                for d in data:
                    if isinstance(d, dict):
                        try:
                            by_i[int(d.get("i", -1))] = d
                        except Exception:
                            pass
            for k, s in enumerate(pending):
                d = by_i.get(s["index"]) or by_i.get(k)
                if d:
                    s["title"] = str(d.get("title") or s["title"])[:110]
                    s["bullets"] = [str(x)[:120] for x in (d.get("bullets") or [])][:6]
                    s["body"] = str(d.get("body") or "")[:1600]
                    s["notes"] = str(d.get("notes") or "")[:1200]
                    s["icon_hint"] = str(d.get("icon_hint") or s.get("icon_hint") or topic)[:60]
                    if isinstance(d.get("chart"), dict):
                        s["chart"] = d["chart"]
                if not s["body"]:  # never ship empty — fill from researched corpus
                    excerpt = ""
                    if sources:
                        src = sources[(b0 + s["index"]) % len(sources)]
                        mid = len(src["text"]) // 2
                        excerpt = src["text"][mid:mid + 900].strip()
                    s["body"] = (excerpt or
                                 (f"{s['title']}. {topic} — key concepts, mechanisms, evidence and "
                                  f"practical takeaways for {st.get('audience','students')}."))
                    s["bullets"] = s["bullets"] or [f"Overview of {s['title'].lower()}", "Key mechanisms",
                                                    "Evidence & examples", "Practice implications"]
                    s["notes"] = s["notes"] or f"Expand on {s['title']} using the researched sources."
                (cdir / f"{s['index']:03d}.json").write_text(json.dumps(s), encoding="utf-8")
        _write_status(job_id, slides_done=min(b0 + BATCH, total),
                      progress=38 + int(44 * min(b0 + BATCH, total) / total),
                      detail=f"writing slide {min(b0 + BATCH, total)}/{total}")
    return slides


# ── Stage 5: assemble — every text element a real, editable text frame ────────

def _assemble(out_path: Path, title: str, slides: list[dict], tpl: dict, sources: list,
              photos: bool, citations: bool):
    from pptx import Presentation
    from pptx.util import Inches, Pt, Emu
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN
    from modules.slides import deck_visuals as dv

    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    blank = prs.slide_layouts[6]
    C = {k: RGBColor.from_string(v) for k, v in
         {"bg": tpl["bg"], "panel": tpl["panel"], "primary": tpl["primary"],
          "accent": tpl["accent"], "muted": tpl["muted"], "white": "FFFFFF"}.items()}
    HEAD_F, BODY_F = tpl["head_font"], tpl["body_font"]
    W, H = 13.333, 7.5
    icons_used = 0

    def bg(slide):
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = C["bg"]

    def txt(slide, x, y, w, h, text, size, color, bold=False, font=BODY_F, align=PP_ALIGN.LEFT, spacing=None):
        tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = tb.text_frame
        tf.word_wrap = True
        first = True
        for para_text in (text if isinstance(text, list) else [text]):
            p = tf.paragraphs[0] if first else tf.add_paragraph()
            first = False
            p.text = para_text
            p.alignment = align
            p.font.size = Pt(size)
            p.font.bold = bold
            p.font.color.rgb = color
            p.font.name = font
            if spacing:
                p.space_after = Pt(spacing)
        return tb

    def add_icon(slide, hint, x, y, size=0.85):
        nonlocal icons_used
        icon = dv.match_icon(hint or "")
        png = dv.icon_png(icon, color=tpl["primary"], size=160) if icon else None
        if png:
            import io
            slide.shapes.add_picture(io.BytesIO(png), Inches(x), Inches(y), Inches(size), Inches(size))
            icons_used += 1
            return True
        # native fallback: tinted tile + 1-2 letter monogram (fully editable)
        from pptx.enum.shapes import MSO_SHAPE
        mono = (re.sub(r"[^A-Za-z]", "", hint or "")[:2] or "SL").upper()
        tile = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(size), Inches(size))
        tile.fill.solid()
        tile.fill.fore_color.rgb = RGBColor.from_string("EFEAF9" if tpl["primary"] != "EFEAF9" else "E8EDF7")
        tile.line.fill.background()
        tile.shadow.inherit = False
        tf = tile.text_frame
        tf.word_wrap = False
        pt = tf.paragraphs[0]
        pt.text = mono
        pt.alignment = PP_ALIGN.CENTER
        pt.font.size = Pt(int(size * 22))
        pt.font.bold = True
        pt.font.color.rgb = C["primary"]
        pt.font.name = BODY_F
        icons_used += 1
        return True

    def notes(slide, text):
        if text:
            slide.notes_slide.notes_text_frame.text = text[:1100]

    for s in slides:
        sl = prs.slides.add_slide(blank)
        bg(sl)
        t = s["type"]
        title_s, body_s, bullet_s = (40, 14, 16) if t in ("title", "section") else (28, 12.5, 15)

        if t == "title":
            txt(sl, 0.8, 2.3, 11.7, 1.6, s["title"], 44, C["primary"], True, HEAD_F, PP_ALIGN.LEFT)
            if s.get("body"):
                txt(sl, 0.85, 4.0, 11.0, 1.6, s["body"][:500], 16, C["muted"])
            add_icon(sl, s.get("icon_hint") or "presentation", 11.2, 1.0, 1.3)
        elif t == "toc":
            txt(sl, 0.8, 0.5, 12, 0.9, s["title"], 30, C["primary"], True, HEAD_F)
            entries = [f"{k+1}.  {o['title']}" for k, o in
                       [(k, o) for k, o in enumerate(slides) if o["type"] == "section" or (k < 8 and o["type"] == "content")][:14]]
            half = (len(entries) + 1) // 2
            txt(sl, 0.9, 1.8, 5.8, 5, entries[:half], 14, C["muted"], spacing=8)
            if entries[half:]:
                txt(sl, 7.0, 1.8, 5.8, 5, entries[half:], 14, C["muted"], spacing=8)
        elif t == "section":
            bar = sl.shapes.add_shape(1, Inches(0.8), Inches(3.4), Inches(1.1), Inches(0.12))  # accent line
            bar.fill.solid(); bar.fill.fore_color.rgb = C["accent"]; bar.line.fill.background(); bar.shadow.inherit = False
            txt(sl, 0.8, 2.1, 11.5, 1.2, s["title"], 36, C["primary"], True, HEAD_F)
            if s.get("body"):
                txt(sl, 0.85, 3.9, 11.0, 2.2, s["body"][:700], 14, C["muted"])
            add_icon(sl, s.get("icon_hint"), 11.4, 1.0, 1.1)
        elif t == "stats" and isinstance(s.get("chart"), dict) and s["chart"].get("kind") == "stats":
            txt(sl, 0.8, 0.45, 12, 0.9, s["title"], 28, C["primary"], True, HEAD_F)
            data = s["chart"].get("data") or []
            cards = data[:4] if isinstance(data, list) else []
            n = max(1, len(cards) or 1)
            cw = 11.7 / n
            for i, cd in enumerate(cards):
                dv.add_stat_card(sl, prs, str(cd.get("value", "—")), str(cd.get("label", "")),
                                 0.8 + i * (cw + 0.12), 1.7, cw - 0.12, 2.3, tpl["primary"])
            if s.get("body"):
                txt(sl, 0.8, 4.4, 11.7, 2.6, s["body"], body_s, C["muted"])
        elif t == "process" and isinstance(s.get("chart"), dict) and s["chart"].get("kind") == "process":
            txt(sl, 0.8, 0.45, 12, 0.9, s["title"], 28, C["primary"], True, HEAD_F)
            steps = [str(x.get("label", x)) if isinstance(x, dict) else str(x)
                     for x in (s["chart"].get("data") or [])][:6] or s.get("bullets", [])[:5]
            dv.add_process_diagram(sl, prs, steps, 0.8, 1.6, 11.7, 1.6, tpl["primary"], tpl["accent"])
            if s.get("bullets"):
                txt(sl, 0.8, 3.5, 11.7, 1.8, [f"•  {b}" for b in s["bullets"]], bullet_s, C["primary"], spacing=6)
            if s.get("body"):
                txt(sl, 0.8, 5.3, 11.7, 1.8, s["body"], body_s, C["muted"])
        elif t == "quote":
            txt(sl, 1.2, 2.2, 10.9, 2.2, f"“{s['body'][:600]}”", 20, C["primary"], False, HEAD_F)
            txt(sl, 1.2, 4.6, 10.9, 0.8, s["title"], 14, C["muted"], True)
        elif t == "reference" and citations:
            txt(sl, 0.8, 0.5, 12, 0.9, "Sources", 28, C["primary"], True, HEAD_F)
            refs = [f"{i+1}. {src['title'][:80]} — {src['url'][:85]} ({src['kind']})"
                    for i, src in enumerate(sources[:12])]
            txt(sl, 0.9, 1.7, 11.6, 5, refs or ["—"], 12, C["muted"], spacing=7)
        elif t == "ending":
            txt(sl, 0.8, 2.9, 11.7, 1.2, s["title"], 40, C["primary"], True, HEAD_F, PP_ALIGN.LEFT)
            if s.get("body"):
                txt(sl, 0.85, 4.3, 11.0, 1.5, s["body"][:400], 15, C["muted"])
        else:  # content / two_column
            txt(sl, 0.8, 0.45, 10.9, 0.95, s["title"], title_s, C["primary"], True, HEAD_F)
            icon_ok = add_icon(sl, s.get("icon_hint"), 11.75, 0.5, 0.95)
            if s.get("bullets"):
                bx = 0.8
                bw = 6.1 if (s.get("body") and t == "content") else 11.7
                txt(sl, bx, 1.6, bw, 2.6, [f"•  {b}" for b in s["bullets"]], bullet_s, C["primary"], spacing=8)
            if s.get("body"):
                bx2 = 7.2 if s.get("bullets") and t == "content" else 0.8
                bw2 = 5.3 if bx2 > 1 else 11.7
                panel = sl.shapes.add_shape(5, Inches(bx2 - 0.15), Inches(1.5), Inches(bw2 + 0.3), Inches(5.35))
                panel.fill.solid(); panel.fill.fore_color.rgb = C["panel"]
                panel.line.color.rgb = RGBColor.from_string("E4DCF5"); panel.shadow.inherit = False
                txt(sl, bx2, 1.75, bw2, 4.9, s["body"], body_s, C["muted"])
        notes(sl, s.get("notes", ""))

    prs.save(str(out_path))
    log.info("deck assembled: %s (%d slides, %d icons)", out_path, len(slides), icons_used)
    return out_path
