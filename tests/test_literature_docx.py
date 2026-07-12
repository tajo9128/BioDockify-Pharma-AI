import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from modules.export.literature_docx import LiteratureDocxExporter


def test_exporter_creates():
    e = LiteratureDocxExporter()
    assert e is not None


def test_export_with_full_text():
    e = LiteratureDocxExporter()
    paper = {
        "title": "Test Article Title",
        "authors": ["Smith J", "Doe A"],
        "year": 2024,
        "journal": "Journal of Testing",
        "doi": "10.1234/test.001",
        "source": "PubMed",
        "abstract": "This is a test abstract for the article.",
    }
    full_text = (
        "Introduction. This is the full text body with multiple paragraphs. "
        "Methods. The study used test methods. "
        "Results. The results show significance. "
        "Discussion. These findings are important."
    )

    docx_bytes = e.export_article(paper, full_text)
    assert docx_bytes is not None
    assert len(docx_bytes) > 1000
    assert docx_bytes[:2] == b"PK"


def test_export_abstract_only():
    e = LiteratureDocxExporter()
    paper = {
        "title": "Abstract Only Article",
        "authors": ["Jones K"],
        "year": 2023,
        "source": "Semantic Scholar",
        "abstract": "Only abstract available.",
    }

    docx_bytes = e.export_article(paper, None)
    assert docx_bytes is not None
    assert len(docx_bytes) > 500
    assert docx_bytes[:2] == b"PK"


def test_export_with_structured_full_text():
    e = LiteratureDocxExporter()
    paper = {
        "title": "Structured Article",
        "authors": ["Brown R", "Lee M", "Patel S"],
        "year": 2025,
        "journal": "Nature Methods",
        "doi": "10.1038/nmeth.0001",
        "source": "Europe PMC",
        "abstract": "METHODS SUMMARY: We developed a novel approach...",
    }
    full_text = (
        "Introduction\n\nThis is background context about the research area.\n\n"
        "Methods\n\nWe used a randomized controlled trial design.\n\n"
        "Results\n\nThe treatment showed significant improvement.\n\n"
        "Discussion\n\nThese results confirm the hypothesis.\n\n"
        "References\n\n1. Smith et al. 2023."
    )

    docx_bytes = e.export_article(paper, full_text)
    assert len(docx_bytes) > 3000
    assert docx_bytes[:2] == b"PK"
