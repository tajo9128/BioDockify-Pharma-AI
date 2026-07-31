"""Literature Matrix Generator — structured comparison table from paper set."""
import logging, re

log = logging.getLogger("lit_matrix")

MATRIX_COLUMNS = ["Author", "Year", "Objective", "Methods", "Key Findings", "Limitations"]

# Pharma-specific columns — differentiator vs generic lit review tools
PHARMA_MATRIX_COLUMNS = MATRIX_COLUMNS + ["Target", "Assay", "IC50/Ki", "Model", "Dose"]


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


def generate_pharma_matrix(papers: list) -> dict:
    """Pharma-specific lit matrix with Target / Assay / IC50 / Model / Dose columns.

    These columns are a key differentiator — generic tools (SciSpace, Jenni)
    don't extract pharmacological parameters. Every row is backed by an
    explicit extraction from the abstract, or shows "—" if not found.
    """
    if not papers:
        return {"columns": PHARMA_MATRIX_COLUMNS, "rows": [], "count": 0,
                "hint": "No papers provided."}

    rows = []
    for i, paper in enumerate(papers):
        if not isinstance(paper, dict):
            continue
        abstract = paper.get("abstract", paper.get("content", paper.get("summary", "")))
        year = paper.get("year", paper.get("publication_year", ""))
        authors = paper.get("authors", paper.get("author", ""))
        if isinstance(authors, list):
            authors = (authors[0] + " et al.") if authors else ""
        elif isinstance(authors, str):
            parts = authors.split(",")
            authors = parts[0].strip() if parts else authors

        rows.append({
            "index": i + 1,
            "Author": authors or "—",
            "Year": str(year) or "—",
            "Objective": _extract_objective(abstract) or _truncate(paper.get("title", ""), 80),
            "Methods": _extract_methods(abstract) or "—",
            "Key Findings": _extract_findings(abstract) or "—",
            "Limitations": _extract_limitations(abstract) or "Not stated",
            "Target": _extract_target(abstract),
            "Assay": _extract_assay(abstract),
            "IC50/Ki": _extract_ic50(abstract),
            "Model": _extract_model(abstract),
            "Dose": _extract_dose(abstract),
            "doi": paper.get("doi", ""),
            "pmid": paper.get("pmid", ""),
        })

    html = _build_html_table(rows, PHARMA_MATRIX_COLUMNS)
    md = _build_markdown_table(rows, PHARMA_MATRIX_COLUMNS)

    return {
        "columns": PHARMA_MATRIX_COLUMNS,
        "rows": rows,
        "count": len(rows),
        "html_table": html,
        "markdown_table": md,
    }


def _extract_target(text: str) -> str:
    """Extract drug target (receptor, enzyme, kinase)."""
    patterns = [
        r"(?i)\btarget(?:s|ed|ing)?\s*[:\-]?\s*([A-Z][A-Za-z0-9\-]{1,20}(?:\s?[A-Za-z0-9\-]{1,15})?)",
        r"(?i)\b(?:against|inhibit(?:s|or)?\s+of|bind(?:s|ing)?\s+to)\s+([A-Z][A-Za-z0-9\-]{2,25})",
        r"(?i)\b(receptor|kinase|enzyme|transporter|channel|protease|polymerase)\s+([A-Z][A-Za-z0-9\-]{2,20})",
        r"(?i)\b(TNF|IL-?\d|VEGF|EGFR|HER2|ACE2?|COX-?2|Bcl-2|p53|PARP|mTOR|JAK|BRAF|CDK\d?)\b",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(1) if m.lastindex else m.group(0)
    return "—"


def _extract_assay(text: str) -> str:
    """Extract assay type."""
    patterns = [
        r"(?i)\b(MTT assay|MTS assay|SRB assay|colony formation|wound healing|Transwell|flow cytometry|ELISA|western blot|qPCR|RT-PCR|HPLC|LC-?MS|MS/MS|radioligand binding|fluorescence polarization|surface plasmon resonance|SPR|isothermal titration calorimetry|ITC|FRET|alpha screen|kinase assay|enzymatic assay|cell viability assay|proliferation assay)\b",
    ]
    matches = []
    for p in patterns:
        for m in re.finditer(p, text):
            matches.append(m.group(1))
    return ", ".join(set(matches)) if matches else "—"


def _extract_ic50(text: str) -> str:
    """Extract IC50 / Ki / Kd values."""
    patterns = [
        r"(?i)\bIC50\s*[:=]?\s*([0-9]+\.?[0-9]*)\s*(nM|μM|uM|mM|pM|M)",
        r"(?i)\bKi\s*[:=]?\s*([0-9]+\.?[0-9]*)\s*(nM|μM|uM|mM|pM|M)",
        r"(?i)\bKd\s*[:=]?\s*([0-9]+\.?[0-9]*)\s*(nM|μM|uM|mM|pM|M)",
        r"(?i)([0-9]+\.?[0-9]*)\s*(nM|μM|uM|mM)\s*\(IC50\)",
    ]
    values = []
    for p in patterns:
        for m in re.finditer(p, text):
            values.append(f"{m.group(1)} {m.group(2)}")
    return ", ".join(set(values)) if values else "—"


def _extract_model(text: str) -> str:
    """Extract experimental model (cell line or animal)."""
    cell_lines = re.findall(
        r"(?i)\b(MCF-?7|HEK293|HeLa|HepG2|A549|RAW264\.7|B16-?F10|PC-?3|MDA-?MB-?231|HCT116|Caco-?2|SH-?SY5Y|NIH3T3|Jurkat|THP-?1|HUVEC|COS-?7|CHO|VERO|Vero)\b",
        text)
    animals = re.findall(
        r"(?i)\b(Wistar|Sprague-?Dawley|C57BL/?6|BALB/c|Swiss albino|nude mice|SD rats|CD-?1 mice|zebrafish|C\. elegans)\b",
        text)
    models = list(set(cell_lines + animals))
    if models:
        return ", ".join(models[:3])
    # Generic fallback
    m = re.search(r"(?i)(in vitro|in vivo|in silico|ex vivo)", text)
    return m.group(1) if m else "—"


def _extract_dose(text: str) -> str:
    """Extract dose/concentration values."""
    patterns = [
        r"(?i)\b(?:dose|dosage)\s*[:=]?\s*([0-9]+\.?[0-9]*)\s*(mg/kg|µg/kg|ug/kg|g/kg|mg|µg|ug|g)\b",
        r"(?i)\b([0-9]+\.?[0-9]*)\s*(mg/kg|µg/mL|ug/mL|μg/mL|mg/mL|µM|uM|μM|mM|nM)\b",
    ]
    values = []
    for p in patterns:
        for m in re.finditer(p, text):
            values.append(f"{m.group(1)} {m.group(2)}")
    return ", ".join(set(values[:3])) if values else "—"


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


def _build_html_table(rows: list, columns=None) -> str:
    columns = columns or MATRIX_COLUMNS
    html = '<table class="lit-matrix"><thead><tr>'
    for col in columns:
        html += f"<th>{col}</th>"
    html += "</tr></thead><tbody>"
    for row in rows:
        html += "<tr>"
        for col in columns:
            html += f"<td>{row.get(col, '—')}</td>"
        html += "</tr>"
    html += "</tbody></table>"
    return html


def _build_latex_table(rows: list, columns=None) -> str:
    columns = columns or MATRIX_COLUMNS
    cols = "|c|" + "|".join(["p{2cm}"] * (len(columns) - 1)) + "|"
    latex = (
        "\\begin{table}[htbp]\n\\centering\n\\caption{Literature Comparison Matrix}\n"
        f"\\begin{{tabular}}{{{cols}}}\n\\hline\n"
    )
    latex += " & ".join(columns) + " \\\\\n\\hline\n"
    for row in rows:
        vals = [str(row.get(c, "—")).replace("&", "\\&").replace("%", "\\%") for c in columns]
        latex += " & ".join(vals) + " \\\\\n"
    latex += "\\hline\n\\end{tabular}\n\\end{table}"
    return latex


def _build_markdown_table(rows: list, columns=None) -> str:
    columns = columns or MATRIX_COLUMNS
    lines = ["| " + " | ".join(columns) + " |",
             "|" + "|".join(["---"] * len(columns)) + "|"]
    for row in rows:
        vals = [str(row.get(c, "—")).replace("|", "\\|") for c in columns]
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)
