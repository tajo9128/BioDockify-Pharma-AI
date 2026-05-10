"""
Academic Export Pipeline

This package provides comprehensive export functionality for theses and publications,
including LaTeX, BibTeX, and DOCX generation with multiple templates.

Export Pipeline:
Research Data → Template Selection → Content Assembly → LaTeX/DOCX → Bibliography → Output Files

Components:
- LaTeXThesisGenerator: Generate LaTeX theses with chapters, figures, tables
- BibTeXManager: Manage references with PubMed/DOI integration
- AcademicDOCXExporter: Generate DOCX with IEEE/APA/Nature templates

Example Usage:
    from export import LaTeXThesisGenerator, BibTeXManager, AcademicDOCXExporter

    # Generate BibTeX
    bib_manager = BibTeXManager()
    bib_manager.add_from_pubmed('12345678')
    bib_manager.export('references.bib')

    # Generate LaTeX thesis
    latex_gen = LaTeXThesisGenerator()
    latex_gen.add_chapter(1, "Introduction", {...})
    latex_gen.generate_and_compile('thesis')

    # Generate DOCX version
    docx_gen = AcademicDOCXExporter(template='ieee')
    docx_gen.add_chapter(1, "Introduction", [...])
    docx_gen.export('thesis.docx')
"""

from .latex_generator import LaTeXThesisGenerator, LaTeXArticleGenerator
from .bibtex_manager import BibTeXManager, BibEntry
from .docx_academic import AcademicDOCXExporter, FigureData, TableData

__version__ = '1.0.0'
__author__ = 'BioDockify Team'

__all__ = [
    'LaTeXThesisGenerator',
    'LaTeXArticleGenerator',
    'BibTeXManager',
    'BibEntry',
    'AcademicDOCXExporter',
    'FigureData',
    'TableData',
]
