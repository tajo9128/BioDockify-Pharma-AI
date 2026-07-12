"""Generate formatted .docx files for literature articles."""
import logging
import re
from typing import Dict, List, Optional, Tuple
from io import BytesIO

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

logger = logging.getLogger("export.literature_docx")


class LiteratureDocxExporter:
    """Export a single article as a formatted .docx document.

    Handles both full-text and abstract-only modes.
    Output is DOCX bytes (ZIP/OpenXML format) for storage.
    """

    def export_article(self, paper: Dict, full_text: Optional[str]) -> bytes:
        """Generate DOCX bytes for an article.

        Args:
            paper: Dict with title, authors, year, journal, doi, source, abstract
            full_text: Full body text (or None for abstract-only mode)

        Returns:
            DOCX file as bytes (valid .docx / ZIP archive)
        """
        doc = Document()

        style = doc.styles["Normal"]
        font = style.font
        font.name = "Times New Roman"
        font.size = Pt(11)

        # --- Title ---
        title_para = doc.add_paragraph()
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = title_para.add_run(paper.get("title", "Untitled"))
        run.bold = True
        run.font.size = Pt(16)

        # --- Metadata ---
        meta = doc.add_paragraph()
        meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
        meta.paragraph_format.space_after = Pt(6)

        authors = paper.get("authors", [])
        if isinstance(authors, list):
            authors_str = ", ".join(authors)
        else:
            authors_str = str(authors or "")
        meta.add_run(authors_str).italic = True

        journal = paper.get("journal", "")
        year = paper.get("year", "")
        doi = paper.get("doi", "")
        if journal or year:
            meta.add_run(f"\n{journal}, {year}").font.size = Pt(10)
        if doi:
            doi_run = meta.add_run(f"\nDOI: {doi}")
            doi_run.font.size = Pt(9)
            doi_run.font.color.rgb = RGBColor(80, 80, 80)

        doc.add_paragraph()

        # --- Abstract ---
        abstract = paper.get("abstract", "")
        if abstract:
            doc.add_heading("Abstract", level=2)
            doc.add_paragraph(abstract)

        # --- Full Text ---
        if full_text:
            doc.add_heading("Full Text", level=2)
            sections = self._split_sections(full_text)
            for sec_title, body in sections:
                if sec_title:
                    doc.add_heading(sec_title, level=3)
                for para_text in body.split("\n\n"):
                    para_text = para_text.strip()
                    if para_text:
                        doc.add_paragraph(para_text)
        else:
            doc.add_heading("Full Text Unavailable", level=2)
            note = doc.add_paragraph()
            note_run = note.add_run(
                "Abstract Only — Full text could not be retrieved from any source."
            )
            note_run.italic = True
            note_run.font.color.rgb = RGBColor(150, 0, 0)

        # --- Source Info ---
        doc.add_paragraph()
        doc.add_heading("Source Information", level=2)
        info = doc.add_paragraph()
        info_lines = [
            f"Database: {paper.get('source', 'Unknown')}",
            "Retrieved by: BioDockify AI Literature Pipeline",
            f"Retrieval method: {'Full Text' if full_text else 'Abstract Only'}",
        ]
        for line in info_lines:
            run = info.add_run(line + "\n")
            run.font.size = Pt(9)
            run.font.color.rgb = RGBColor(100, 100, 100)

        # --- Footer ---
        section = doc.sections[0]
        footer = section.footer
        footer_para = footer.paragraphs[0]
        footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        footer_para.add_run("Retrieved by BioDockify AI").font.size = Pt(8)

        buf = BytesIO()
        doc.save(buf)
        return buf.getvalue()

    def _split_sections(
        self, text: str
    ) -> List[Tuple[str, str]]:
        """Split full text into titled sections using common heading patterns."""
        pattern = re.compile(
            r"(?:\n|^)((?:Abstract|Introduction|Background|"
            r"Methods?|Materials?\s*(?:and|&)\s*Methods?|Experimental|"
            r"Results?(?:\s*and\s*Discussion)?|Discussion|Conclusion|Summary|"
            r"Acknowledgments?|References?|Bibliography|Supplementary)\s*[:\n]?)",
            re.IGNORECASE,
        )
        parts = pattern.split(text)
        sections = []

        if parts and parts[0].strip():
            sections.append(("", parts[0]))

        for i in range(1, len(parts) - 1, 2):
            title = parts[i].strip().rstrip(":")
            body = parts[i + 1] if i + 1 < len(parts) else ""
            sections.append((title, body))

        if not sections:
            sections.append(("", text))

        return sections
