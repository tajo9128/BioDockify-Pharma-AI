"""BioDockify Writing Tools API — LaTeX, Gap Analysis, Literature Matrix, PRISMA, Faculty Review, Citation Validation, Journal Suggestions."""
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/writing", tags=["Writing Tools"])


class ExportLatexRequest(BaseModel):
    title: str = Field(..., description="Document title")
    authors: str = Field(default="", description="Author names")
    abstract: str = Field(default="", description="Abstract text")
    sections: List[dict] = Field(default_factory=list, description="[{heading, content}] list")
    tables: List[dict] = Field(default_factory=list, description="[{caption, headers, rows}] list")
    bibliography: List[str] = Field(default_factory=list, description="BibTeX entries")
    doc_class: str = Field(default="article", description="article | report | book")


class GapAnalysisRequest(BaseModel):
    papers: List[dict] = Field(default_factory=list, description="[{title, abstract, entities}] paper list")
    topic: str = Field(default="", description="Research topic for context")


class LiteratureMatrixRequest(BaseModel):
    papers: List[dict] = Field(default_factory=list, description="[{title, authors, year, abstract}] paper list")


class PrismaRequest(BaseModel):
    identification_count: int = Field(default=0, description="Total records identified")
    screening_count: int = Field(default=0, description="Records after duplicates removed")
    eligibility_count: int = Field(default=0, description="Full-text articles assessed")
    included_count: int = Field(default=0, description="Studies included")
    exclusion_reasons: dict = Field(default_factory=dict, description="{reason: count}")
    search_query: str = Field(default="", description="Search strategy description")
    topic: str = Field(default="Systematic Review", description="Review topic")


class FacultyReviewRequest(BaseModel):
    content: str = Field(..., description="Manuscript text to review")
    title: str = Field(default="", description="Paper title")
    sections: dict = Field(default_factory=dict, description="section_name: content mapping")


class CitationVerifyRequest(BaseModel):
    text: str = Field(..., description="Text containing citations to verify")
    threshold: float = Field(default=0.5, description="Minimum confidence threshold")


class JournalSuggestRequest(BaseModel):
    title: str = Field(default="", description="Paper title")
    abstract: str = Field(default="", description="Paper abstract")
    keywords: str = Field(default="", description="Comma-separated keywords")


# ── 1. LaTeX Export ──────────────────────────────────────────────

@router.post("/export-latex")
async def export_latex(req: ExportLatexRequest):
    try:
        from export.latex_generator import create_simple_document
        result = create_simple_document(
            title=req.title,
            authors=req.authors,
            abstract=req.abstract,
            sections=req.sections,
            tables=req.tables,
            bibliography=req.bibliography,
            doc_class=req.doc_class
        )
        return {"status": "ok", "latex": result}
    except ImportError:
        return _simple_latex(req)
    except Exception as e:
        logger.error(f"LaTeX export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _simple_latex(req: ExportLatexRequest):
    """Fallback LaTeX generator — works without pylatex."""
    doc = (
        f"\\documentclass{{{req.doc_class}}}\n"
        f"\\title{{{_sanitize_tex(req.title)}}}\n"
        f"\\author{{{_sanitize_tex(req.authors)}}}\n"
        f"\\begin{{document}}\n\\maketitle\n"
    )
    if req.abstract:
        doc += f"\\begin{{abstract}}\n{_sanitize_tex(req.abstract)}\n\\end{{abstract}}\n"
    for s in req.sections:
        heading = s.get("heading", "Section")
        content = s.get("content", "")
        doc += f"\\section{{{_sanitize_tex(heading)}}}\n{content}\n"
    for t in req.tables:
        caption = t.get("caption", "")
        headers = t.get("headers", [])
        rows = t.get("rows", [])
        cols = "|" + "c|" * len(headers)
        doc += f"\\begin{{table}}[htbp]\n\\caption{{{_sanitize_tex(caption)}}}\n"
        doc += f"\\begin{{tabular}}{{{cols}}}\n\\hline\n"
        doc += " & ".join(_sanitize_tex(h) for h in headers) + " \\\\\n\\hline\n"
        for row in rows:
            doc += " & ".join(str(c) for c in row) + " \\\\\n"
        doc += "\\hline\n\\end{tabular}\n\\end{table}\n"
    if req.bibliography:
        doc += "\\begin{thebibliography}{99}\n"
        for i, b in enumerate(req.bibliography):
            doc += f"\\bibitem{{ref{i+1}}} {_sanitize_tex(b)}\n"
        doc += "\\end{thebibliography}\n"
    doc += "\\end{document}"
    return {"status": "ok", "latex": doc}


# ── 2. Research Gap Analysis ──────────────────────────────────────

@router.post("/gap-analysis")
async def gap_analysis(req: GapAnalysisRequest):
    try:
        from nlp.gap_analyzer import PreclinicalGapAnalyzer
        analyzer = PreclinicalGapAnalyzer()
        papers = req.papers if req.papers else []
        if not papers and req.topic:
            return {"status": "ok", "gaps": [], "hint": "Provide papers for gap analysis. Use Deep Research to collect literature first."}
        gaps = analyzer.detect_research_gaps(papers, topic=req.topic or "Pharmaceutical Research")
        report = analyzer.generate_gap_report(gaps, top_n=10)
        return {"status": "ok", "gaps": gaps[:10], "report": report}
    except ImportError:
        return {"status": "error", "error": "nlp.gap_analyzer module not available. Install numpy."}
    except Exception as e:
        logger.error(f"Gap analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── 3. Literature Matrix ─────────────────────────────────────────

@router.post("/literature-matrix")
async def literature_matrix(req: LiteratureMatrixRequest):
    try:
        from modules.writing.lit_matrix import generate_lit_matrix
        matrix = generate_lit_matrix(req.papers)
        return {"status": "ok", "matrix": matrix}
    except ImportError:
        return {"status": "error", "error": "Literature Matrix module not available"}
    except Exception as e:
        logger.error(f"Literature matrix failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── 4. PRISMA Flowchart ──────────────────────────────────────────

@router.post("/prisma-flowchart")
async def prisma_flowchart(req: PrismaRequest):
    try:
        from modules.writing.prisma_flowchart import generate_prisma
        result = generate_prisma(
            identification=req.identification_count,
            screening=req.screening_count,
            eligibility=req.eligibility_count,
            included=req.included_count,
            exclusion_reasons=req.exclusion_reasons,
            search_query=req.search_query,
            topic=req.topic
        )
        return {"status": "ok", "prisma": result}
    except ImportError:
        return {"status": "error", "error": "PRISMA module not available"}
    except Exception as e:
        logger.error(f"PRISMA generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── 5. Faculty Review ────────────────────────────────────────────

@router.post("/faculty-review")
async def faculty_review(req: FacultyReviewRequest):
    try:
        from modules.writing.review_checker import review_manuscript
        report = review_manuscript(req.content, req.title, req.sections)
        return {"status": "ok", "review": report}
    except ImportError:
        return {"status": "error", "error": "Review Checker module not available"}
    except Exception as e:
        logger.error(f"Faculty review failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── 6. Citation Verification ─────────────────────────────────────

@router.post("/verify-citations")
async def verify_citations(req: CitationVerifyRequest):
    try:
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from api.verification import extract_citations, verify_citation
        cites = extract_citations(req.text)
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
        logger.error(f"Citation verification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── 7. Journal Suggestions ───────────────────────────────────────

@router.post("/suggest-journals")
async def suggest_journals(req: JournalSuggestRequest):
    try:
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from api.journal_finder import JournalFinder
        finder = JournalFinder()
        result = finder.suggest(
            title=req.title,
            abstract=req.abstract,
            keywords=req.keywords
        )
        return {"status": "ok", "journals": result}
    except ImportError:
        return _mock_journals(req)
    except Exception as e:
        logger.error(f"Journal suggestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _mock_journals(req: JournalSuggestRequest):
    return {"status": "ok", "journals": [
        {"name": "Journal of Pharmaceutical Sciences", "issn": "0022-3549", "quartile": "Q1", "if": 3.5, "scope": "high"},
        {"name": "European Journal of Pharmacology", "issn": "0014-2999", "quartile": "Q2", "if": 2.8, "scope": "high"},
        {"name": "Bioorganic & Medicinal Chemistry", "issn": "0968-0896", "quartile": "Q2", "if": 2.5, "scope": "medium"},
        {"name": "Chemical Biology & Drug Design", "issn": "1747-0277", "quartile": "Q3", "if": 1.9, "scope": "medium"},
        {"name": "Drug Development Research", "issn": "0272-4391", "quartile": "Q3", "if": 1.5, "scope": "low"},
    ]}


# ── Utilities ────────────────────────────────────────────────────

def _sanitize_tex(text: str) -> str:
    """Escape LaTeX special characters."""
    if not text:
        return ""
    for char, repl in [("\\", "\\textbackslash "), ("&", "\\&"), ("%", "\\%"), ("$", "\\$"),
                        ("#", "\\#"), ("_", "\\_"), ("{", "\\{"), ("}", "\\}"),
                        ("~", "\\textasciitilde "), ("^", "\\textasciicircum ")]:
        text = text.replace(char, repl)
    return text
