import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def test_docx_export_no_crash():
    from modules.export.literature_docx import LiteratureDocxExporter

    exporter = LiteratureDocxExporter()
    paper = {
        "title": "A Randomized Trial of Drug X in Hypertension",
        "authors": ["Smith J", "Doe A", "Brown K"],
        "year": 2024,
        "journal": "New England Journal of Medicine",
        "doi": "10.1056/NEJMoa240001",
        "source": "PubMed",
        "abstract": "BACKGROUND: Hypertension affects 1.3 billion people worldwide...",
    }
    full_text = (
        "Introduction\n\nHypertension is the leading modifiable risk factor...\n\n"
        "Methods\n\nThis randomized double-blind trial enrolled 5000 participants...\n\n"
        "Results\n\nSystolic BP decreased by 12 mmHg in treatment group vs 3 mmHg placebo...\n\n"
        "Discussion\n\nDrug X demonstrates superior efficacy compared to standard care..."
    )

    docx_bytes = exporter.export_article(paper, full_text)
    assert docx_bytes[:2] == b"PK"
    assert len(docx_bytes) > 2000


def test_orchestrator_syntax_valid():
    import ast
    with open("modules/literature/orchestrator.py", "r") as f:
        source = f.read()
    ast.parse(source)
    # Valid syntax


def test_orchestrator_return_includes_new_fields():
    import ast
    with open("modules/literature/orchestrator.py", "r") as f:
        source = f.read()

    assert "papers_full_text" in source
    assert "docx_stored" in source
    assert "FullTextRetriever" in source
    assert "LiteratureDocxExporter" in source
