"""Literature Matrix Generator — structured comparison table from paper set."""
import logging, re

log = logging.getLogger("lit_matrix")

MATRIX_COLUMNS = ["Author", "Year", "Objective", "Methods", "Key Findings", "Limitations"]


def generate_lit_matrix(papers: list) -> dict:
    """
    Generate a structured literature comparison matrix from a list of papers.

    Args:
        papers: List of dicts with keys: title, authors, year, abstract (or content)

    Returns:
        dict with keys: columns, rows, html_table, latex_table, markdown_table
    """
    if not papers:
        return {"columns": MATRIX_COLUMNS, "rows": [], "count": 0, "hint": "No papers provided. Upload papers from Knowledge Base or Literature Search."}

    rows = []
    for i, paper in enumerate(papers):
        if not isinstance(paper, dict):
            continue
        year = paper.get("year", paper.get("publication_year", ""))
        authors = paper.get("authors", paper.get("author", ""))
        if isinstance(authors, list):
            authors = authors[0] + (" et al." if len(authors) > 1 else "") if authors else ""
        elif isinstance(authors, str):
            parts = authors.split(",")
            authors = parts[0].strip().split()[-1] if parts else authors
            authors = authors.split(" and ")[0].split(";")[0].strip()

        abstract = paper.get("abstract", paper.get("content", paper.get("summary", "")))
        objective = _extract_objective(abstract)
        methods = _extract_methods(abstract)
        findings = _extract_findings(abstract)
        limitations = _extract_limitations(abstract)

        rows.append({
            "index": i + 1,
            "Author": authors or "—",
            "Year": str(year) or "—",
            "Objective": objective or _truncate(paper.get("title", ""), 80),
            "Methods": methods or "—",
            "Key Findings": findings or "—",
            "Limitations": limitations or "Not explicitly stated",
        })

    html = _build_html_table(rows)
    latex = _build_latex_table(rows)
    md = _build_markdown_table(rows)

    return {
        "columns": MATRIX_COLUMNS,
        "rows": rows,
        "count": len(rows),
        "html_table": html,
        "latex_table": latex,
        "markdown_table": md,
    }


def _extract_objective(text: str) -> str:
    patterns = [
        r"(?:objective|aim|goal|purpose)(?:.{0,50}?)(?:was|is|were)\s+(?:to\s+)?(.+?)(?:\.|;|The|We)",
        r"this study (?:aimed|aims|sought|seeks) to (.+?)(?:\.|;|The|We)",
        r"we (?:investigated|examined|evaluated|studied|explored) (.+?)(?:\.|;|The|We)",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1).strip().rstrip(".,;")
    return ""


def _extract_methods(text: str) -> str:
    patterns = [
        r"(?:method|methodology|approach)(?:.{0,30}?)(?:used|employed|utilized|was|were)\s+(.+?)(?:\.|;|The|Results|We)",
        r"(?:using|employing|utilizing)\s+(.+?)(?:,|\.|;|and we|we)",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return _truncate(m.group(1).strip().rstrip(".,;"), 60)
    return ""


def _extract_findings(text: str) -> str:
    patterns = [
        r"(?:found|revealed|demonstrated|showed|indicated|observed)\s+that\s+(.+?)(?:\.|;|These|The|Our)",
        r"(?:results|findings)(?:.{0,30}?)(?:showed|indicated|demonstrated|revealed)\s+that\s+(.+?)(?:\.|;|These|The|Our)",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return _truncate(m.group(1).strip().rstrip(".,;"), 70)
    return ""


def _extract_limitations(text: str) -> str:
    patterns = [
        r"(?:limitation|limitations|limitation of)(?:.{0,30}?)(?:include|includes|is|are|was|were)\s+(.+?)(?:\.|;|Further|Future|Additional)",
        r"(?:however|although|despite)(?:.{0,60}?)(?:limitation|limited|constrained|restricted)(?:.{0,30}?)(?:by|to|in|due to)\s+(.+?)(?:\.|;|Further|Future)",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return _truncate(m.group(1).strip().rstrip(".,;"), 60)
    return ""


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len - 3].rstrip() + "..."


def _build_html_table(rows: list) -> str:
    html = '<table class="lit-matrix"><thead><tr>'
    for col in MATRIX_COLUMNS:
        html += f"<th>{col}</th>"
    html += "</tr></thead><tbody>"
    for row in rows:
        html += "<tr>"
        for col in MATRIX_COLUMNS:
            html += f"<td>{row.get(col, '—')}</td>"
        html += "</tr>"
    html += "</tbody></table>"
    return html


def _build_latex_table(rows: list) -> str:
    cols = "|c|c|p{2.5cm}|p{2cm}|p{2.5cm}|p{2cm}|"
    latex = (
        "\\begin{table}[htbp]\n\\centering\n\\caption{Literature Comparison Matrix}\n"
        f"\\begin{{tabular}}{{{cols}}}\n\\hline\n"
    )
    latex += " & ".join(MATRIX_COLUMNS) + " \\\\\n\\hline\n"
    for row in rows:
        vals = [str(row.get(c, "—")).replace("&", "\\&").replace("%", "\\%") for c in MATRIX_COLUMNS]
        latex += " & ".join(vals) + " \\\\\n"
    latex += "\\hline\n\\end{tabular}\n\\end{table}"
    return latex


def _build_markdown_table(rows: list) -> str:
    lines = ["| " + " | ".join(MATRIX_COLUMNS) + " |",
             "|" + "|".join(["---"] * len(MATRIX_COLUMNS)) + "|"]
    for row in rows:
        vals = [str(row.get(c, "—")).replace("|", "\\|") for c in MATRIX_COLUMNS]
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)
