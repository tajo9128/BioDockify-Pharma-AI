"""Writing Tools API — Flask handler for LaTeX export, gap analysis, lit matrix, PRISMA, faculty review, citation verification, journal suggestions."""
from helpers.api import ApiHandler, Request, Response
import logging

log = logging.getLogger("writing_tools")


class WritingTools(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        action = input.get("action", "")
        if action == "export-latex":       return self._export_latex(input)
        if action == "export-docx":        return self._export_docx(input)
        if action == "gap-analysis":       return self._gap_analysis(input)
        if action == "literature-matrix":  return self._lit_matrix(input)
        if action == "prisma-flowchart":   return self._prisma_flowchart(input)
        if action == "faculty-review":     return self._faculty_review(input)
        if action == "verify-citations":   return self._verify_citations(input)
        if action == "suggest-journals":   return self._suggest_journals(input)
        if action == "kb_sources":         return self._kb_sources(input)
        if action == "kb_categories":      return self._kb_categories(input)
        return {"actions": ["export-latex","export-docx","gap-analysis","literature-matrix","prisma-flowchart","faculty-review","verify-citations","suggest-journals","kb_sources","kb_categories"]}

    def _kb_categories(self, input: dict) -> dict:
        """List all KB categories with entry counts — for the writer's category dropdown."""
        try:
            import sys; sys.path.insert(0, "/a0")
            from modules.knowledge.auto_store import _load_index
            idx = _load_index()
            cats = {}
            for e in idx.get("entries", []):
                c = e.get("category", "misc")
                cats[c] = cats.get(c, 0) + 1
            # Sort by count desc
            sorted_cats = sorted(cats.items(), key=lambda x: -x[1])
            return {
                "status": "ok",
                "categories": [{"key": c, "count": n} for c, n in sorted_cats],
                "total_entries": len(idx.get("entries", [])),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _kb_sources(self, input: dict) -> dict:
        """Load KB entries by category, formatted as a source bundle for the Academic Writer.

        Keeps categories SEPARATE — caller picks which category(ies) to pull from.
        Applies a 100K character budget: full text for top entries, abstracts/titles for the rest.
        """
        try:
            import sys, os; sys.path.insert(0, "/a0")
            from modules.knowledge.auto_store import _load_index

            category = input.get("category", "literature")        # single category or "all"
            categories = input.get("categories", [])                # OR list of categories
            max_chars = int(input.get("max_chars", 100000))         # 100K char budget
            max_entries = int(input.get("max_entries", 300))

            if categories:
                target_cats = set(categories)
            elif category and category != "all":
                target_cats = {category}
            else:
                target_cats = None  # all categories

            idx = _load_index()
            entries = idx.get("entries", [])

            # Filter by category
            if target_cats is not None:
                entries = [e for e in entries if e.get("category") in target_cats]

            # Sort newest first
            entries.sort(key=lambda e: e.get("created_at", ""), reverse=True)
            entries = entries[:max_entries]

            if not entries:
                return {
                    "status": "ok",
                    "sources": [],
                    "count": 0,
                    "total_chars": 0,
                    "message": f"No entries found in category '{category}'",
                }

            # ── Budget loading: full text first, then abstracts, then titles only ──
            sources = []
            total_chars = 0
            FULL_BUDGET = int(max_chars * 0.7)   # 70% for full content
            ABS_BUDGET = int(max_chars * 0.25)   # 25% for abstracts
            # 5% reserved for titles

            # Pass 1: load full content until FULL_BUDGET reached
            full_count = 0
            for e in entries:
                if total_chars >= FULL_BUDGET:
                    break
                filepath = e.get("file", "")
                content = ""
                if filepath and os.path.exists(filepath):
                    try:
                        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                            content = f.read(max_chars)
                    except Exception:
                        pass
                if content and len(content) > 100:
                    # Truncate if this entry would blow the budget
                    remaining = FULL_BUDGET - total_chars
                    if len(content) > remaining:
                        content = content[:remaining] + "\n...[truncated]"
                    sources.append({
                        "title": e.get("title", "Untitled"),
                        "category": e.get("category", ""),
                        "source": e.get("source", ""),
                        "content": content,
                        "content_type": "full",
                        "created_at": e.get("created_at", ""),
                    })
                    total_chars += len(content)
                    full_count += 1

            # Pass 2: for entries not loaded as full, add abstract/summary if budget allows
            loaded_titles = {s["title"] for s in sources}
            abs_count = 0
            for e in entries:
                if total_chars >= FULL_BUDGET + ABS_BUDGET:
                    break
                if e.get("title") in loaded_titles:
                    continue
                # Try to extract abstract (first 500-2000 chars after metadata)
                filepath = e.get("file", "")
                snippet = ""
                if filepath and os.path.exists(filepath):
                    try:
                        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                            text = f.read(3000)
                        # Find abstract section
                        if "## Abstract" in text:
                            snippet = text.split("## Abstract", 1)[1][:1500].strip()
                        elif "## Full Text" in text:
                            snippet = text.split("## Full Text", 1)[1][:1500].strip()
                        else:
                            snippet = text[:1000]
                    except Exception:
                        pass
                if snippet:
                    remaining = (FULL_BUDGET + ABS_BUDGET) - total_chars
                    if len(snippet) > remaining:
                        snippet = snippet[:remaining] + "...[truncated]"
                    sources.append({
                        "title": e.get("title", "Untitled"),
                        "category": e.get("category", ""),
                        "source": e.get("source", ""),
                        "content": snippet,
                        "content_type": "abstract",
                        "created_at": e.get("created_at", ""),
                    })
                    total_chars += len(snippet)
                    abs_count += 1
                    loaded_titles.add(e["title"])

            # Pass 3: titles-only for the rest (citations)
            title_count = 0
            for e in entries:
                if e.get("title") in loaded_titles:
                    continue
                sources.append({
                    "title": e.get("title", "Untitled"),
                    "category": e.get("category", ""),
                    "source": e.get("source", ""),
                    "content": "",
                    "content_type": "title_only",
                    "created_at": e.get("created_at", ""),
                })
                title_count += 1

            return {
                "status": "ok",
                "sources": sources,
                "count": len(sources),
                "category": category,
                "full_text_count": full_count,
                "abstract_count": abs_count,
                "title_only_count": title_count,
                "total_chars": total_chars,
                "budget_chars": max_chars,
                "message": (
                    f"Loaded {len(sources)} sources from '{category}': "
                    f"{full_count} full text, {abs_count} abstracts, {title_count} titles only. "
                    f"Total {total_chars:,} chars (budget {max_chars:,})."
                ),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


    def _export_latex(self, input: dict):
        title = input.get("title", "")
        sections = input.get("sections", [])
        abstract = input.get("abstract", "")
        authors = input.get("authors", "")
        try:
            doc = (
                f"\\documentclass{{article}}\n"
                f"\\usepackage{{hyperref}}\n"
                f"\\title{{{_sanitize(title)}}}\n"
                f"\\author{{{_sanitize(authors)}}}\n"
                f"\\begin{{document}}\n\\maketitle\n"
            )
            if abstract:
                doc += f"\\begin{{abstract}}\n{_sanitize(abstract)}\n\\end{{abstract}}\n"
            for s in sections:
                h = s.get("heading", "Section")
                c = s.get("content", "")
                doc += f"\\section{{{_sanitize(h)}}}\n{c}\n"
            doc += "\\end{document}"
            return {"status": "ok", "latex": doc}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _export_docx(self, input: dict):
        title = input.get("title", "Manuscript")
        content = input.get("content", "")
        try:
            from docx import Document
            from docx.shared import Pt, Inches
            import base64, io
            doc = Document()
            doc.styles['Normal'].font.size = Pt(11)
            doc.add_heading(title, level=0)
            for para in content.split("\n\n"):
                if para.strip():
                    p = doc.add_paragraph(para.strip())
                    p.style.font.size = Pt(11)
            buf = io.BytesIO()
            doc.save(buf)
            buf.seek(0)
            return {"status": "ok", "docx_base64": base64.b64encode(buf.read()).decode()}
        except ImportError:
            return {"status": "error", "error": "python-docx not installed. Run: pip install python-docx"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _gap_analysis(self, input: dict):
        topic = input.get("topic", "")
        try:
            from nlp.gap_analyzer import PreclinicalGapAnalyzer
            analyzer = PreclinicalGapAnalyzer()
            gaps = analyzer.detect_research_gaps([], topic=topic or "Pharmaceutical Research")
            report = analyzer.generate_gap_report(gaps, top_n=10)
            return {"status": "ok", "gaps": gaps[:10], "report": report}
        except ImportError:
            return {"status": "error", "error": "Gap analyzer requires numpy. Install dependencies."}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _lit_matrix(self, input: dict):
        papers = input.get("papers", [])
        try:
            from modules.writing.lit_matrix import generate_lit_matrix
            return {"status": "ok", "matrix": generate_lit_matrix(papers)}
        except ImportError:
            return {"status": "error", "error": "Literature matrix module not available"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _prisma_flowchart(self, input: dict):
        try:
            from modules.writing.prisma_flowchart import generate_prisma
            result = generate_prisma(
                identification=input.get("identification", 100),
                screening=input.get("screening", 80),
                eligibility=input.get("eligibility", 40),
                included=input.get("included", 15),
                exclusion_reasons=input.get("reasons", {}),
                topic=input.get("topic", "Systematic Review")
            )
            return {"status": "ok", "prisma": result}
        except ImportError:
            return {"status": "error", "error": "PRISMA module not available"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _faculty_review(self, input: dict):
        content = input.get("content", "")
        title = input.get("title", "")
        try:
            from modules.writing.review_checker import review_manuscript
            return {"status": "ok", "review": review_manuscript(content, title)}
        except ImportError:
            return {"status": "error", "error": "Review checker not available"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _verify_citations(self, input: dict):
        text = input.get("text", "")
        try:
            from api.verification import extract_citations, verify_citation
            cites = extract_citations(text)
            results = []
            for c in cites:
                v = verify_citation(c)
                results.append({"citation": c, "verified": v.get("verified", False), "details": v})
            verified = sum(1 for r in results if r["verified"])
            confidence = round(verified / max(len(results), 1), 2)
            return {"status": "ok", "confidence": confidence, "total": len(results), "verified": verified, "results": results}
        except ImportError:
            return {"status": "error", "error": "Verification module not available"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _suggest_journals(self, input: dict):
        title = input.get("title", "")
        abstract = input.get("abstract", "")
        try:
            from api.journal_finder import JournalFinder
            finder = JournalFinder()
            result = finder.suggest(title=title, abstract=abstract)
            return {"status": "ok", "journals": result}
        except Exception:
            return {"status": "ok", "journals": [
                {"name": "Journal of Pharmaceutical Sciences", "quartile": "Q1", "if": "3.5", "issn": "0022-3549"},
                {"name": "European Journal of Pharmacology", "quartile": "Q2", "if": "2.8", "issn": "0014-2999"},
                {"name": "Bioorganic & Medicinal Chemistry", "quartile": "Q2", "if": "2.5", "issn": "0968-0896"},
                {"name": "Chemical Biology & Drug Design", "quartile": "Q3", "if": "1.9", "issn": "1747-0277"},
                {"name": "Drug Development Research", "quartile": "Q3", "if": "1.5", "issn": "0272-4391"},
            ]}


def _sanitize(text: str) -> str:
    if not text:
        return ""
    for c, r in [("\\", "\\textbackslash "), ("&", "\\&"), ("%", "\\%"), ("$", "\\$"),
                  ("#", "\\#"), ("_", "\\_"), ("{", "\\{"), ("}", "\\}"),
                  ("~", "\\textasciitilde "), ("^", "\\textasciicircum ")]:
        text = text.replace(c, r)
    return text
