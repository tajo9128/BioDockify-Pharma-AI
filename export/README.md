# Academic Export Pipeline

A comprehensive export system for theses and publications with LaTeX, BibTeX, and DOCX support.

## Export Pipeline

```
Research Data → Template Selection → Content Assembly → LaTeX/DOCX → Bibliography → Output Files
```

## Features

- **LaTeX Generation**: Complete thesis generation with chapters, figures, tables
- **BibTeX Management**: Fetch references from PubMed/DOI, multiple citation styles
- **DOCX Export**: Multiple academic templates (IEEE, APA, Nature)
- **PDF Compilation**: Automatic LaTeX to PDF compilation
- **Custom Styling**: Templates, fonts, margins, headers/footers

## Installation

### Install Python Dependencies

```bash
cd export
pip install -r requirements.txt
```

### Install LaTeX Distribution (for PDF compilation)

**Windows:**
```bash
# Install MiKTeX or TeX Live
# https://miktex.org
```

**macOS:**
```bash
# Install MacTeX
brew install --cask mactex
```

**Linux:**
```bash
# Install TeX Live
sudo apt-get install texlive-latex-base texlive-fonts-recommended
```

Verify installation:
```bash
pdflatex --version
```

## Quick Start

```python
from export import (
    LaTeXThesisGenerator,
    BibTeXManager,
    AcademicDOCXExporter
)

# 1. Generate BibTeX
bib_manager = BibTeXManager()
bib_manager.add_from_pubmed('12345678')
bib_manager.add_from_doi('10.1000/example.doi')
bib_manager.export('references.bib')

# 2. Generate LaTeX thesis
latex_gen = LaTeXThesisGenerator()
latex_gen.add_abstract("This thesis explores...")
latex_gen.add_chapter(1, "Introduction", {...})
latex_gen.add_bibliography('references')
latex_gen.generate_and_compile('thesis')

# 3. Generate DOCX version
docx_gen = AcademicDOCXExporter(template='ieee')
docx_gen.add_title_page("My PhD Thesis", "Student Name", "University")
docx_gen.add_abstract("This thesis...")
docx_gen.add_chapter(1, "Introduction", [...])
docx_gen.export('thesis.docx')
```

## Components

### 1. LaTeX Generator

Generate LaTeX theses and academic publications.

#### Usage

```python
from export import LaTeXThesisGenerator

# Initialize
latex_gen = LaTeXThesisGenerator(
    template='report',
    title='My PhD Thesis',
    author='Student Name'
)

# Add document structure
latex_gen.add_title_page()
latex_gen.add_abstract("Abstract text...")
latex_gen.add_toc()
latex_gen.add_list_of_figures()
latex_gen.add_list_of_tables()

# Add chapter
latex_gen.add_chapter(1, 'Introduction', {
    'sections': [
        {
            'title': 'Background',
            'text': 'Content here...',
            'subsections': [
                {'title': 'Subsection', 'text': '...'}
            ],
            'figures': [
                {
                    'path': 'figure.png',
                    'caption': 'Figure caption',
                    'width': '0.8\\textwidth'
                }
            ],
            'tables': [
                {
                    'headers': ['Col1', 'Col2'],
                    'rows': [['A', 'B'], ['C', 'D']],
                    'caption': 'Table caption'
                }
            ]
        }
    ]
})

# Add bibliography
latex_gen.add_bibliography('references', style='plain')

# Generate and compile
pdf_path = latex_gen.generate_and_compile('thesis')
```

#### Features

- Multiple document classes (article, report, book)
- Chapter and section structure
- Figure and table insertion
- Abstract and TOC support
- BibTeX bibliography integration
- Custom preamble packages
- PDF compilation with pdflatex
- Cross-references and labels

### 2. BibTeX Manager

Manage references with API integration.

#### Usage

```python
from export import BibTeXManager

# Initialize
bib_manager = BibTeXManager()

# Add references
# From PubMed
entry = bib_manager.add_from_pubmed('12345678')

# From DOI
entry = bib_manager.add_from_doi('10.1000/example.doi')

# Manual entry
entry = bib_manager.add_manual({
    'ID': 'smith2023',
    'ENTRYTYPE': 'article',
    'title': 'A Novel Approach',
    'author': 'Smith, J.',
    'year': '2023',
    'journal': 'Journal Name'
})

# Format citations
apa = bib_manager.format_citation('smith2023', style='apa')
ieee = bib_manager.format_citation('smith2023', style='ieee')
nature = bib_manager.format_citation('smith2023', style='nature')

# Export
bib_manager.export('references.bib')
bib_manager.export_markdown('references.md')

# Search
results = bib_manager.search('drug discovery')

# Find duplicates
duplicates = bib_manager.find_duplicates()
```

#### Supported Citation Styles

- **APA**: American Psychological Association
- **IEEE**: Institute of Electrical and Electronics Engineers
- **Nature**: Nature journal style
- **MLA**: Modern Language Association
- **Chicago**: Chicago Manual of Style

#### Features

- Fetch from PubMed by PMID
- Fetch from DOI (CrossRef)
- Manual entry creation
- Multiple citation styles
- Duplicate detection
- Reference search
- BibTeX and Markdown export

### 3. DOCX Academic Exporter

Generate DOCX documents with academic templates.

#### Usage

```python
from export import AcademicDOCXExporter

# Initialize with template
exporter = AcademicDOCXExporter(template='ieee')

# Add title page
exporter.add_title_page(
    title="My PhD Thesis",
    author="Student Name",
    institution="University Name",
    date="January 2024"
)

# Add abstract
exporter.add_abstract("Abstract text...")

# Add keywords
exporter.add_keywords(['drug', 'discovery', 'computational'])

# Add chapters
exporter.add_chapter(1, 'Introduction', [
    {
        'title': 'Background',
        'text': 'Content here...',
        'tables': [
            {
                'headers': ['Method', 'Accuracy'],
                'rows': [['A', '95%'], ['B', '92%']],
                'caption': 'Results'
            }
        ],
        'figures': [
            {
                'path': 'figure.png',
                'caption': 'Figure caption'
            }
        ]
    }
])

# Add references
exporter.add_references([
    "Smith, J. et al. (2023). Title. Journal, vol, pages."
])

# Add header and footer
exporter.add_header("Chapter 1: Introduction")
exporter.add_footer("Page ", include_page_number=True)

# Export
exporter.export('thesis.docx')
```

#### Supported Templates

- **IEEE**: Times New Roman, 10pt, single spaced
- **APA**: Times New Roman, 12pt, double spaced
- **Nature**: Arial, 11pt, 1.5 spaced
- **Custom**: User-defined styling

#### Features

- Multiple academic templates
- Title page generation
- Chapter and section structure
- Figure and table insertion
- Reference list formatting
- Header and footer support
- Custom margins
- Bullet and numbered lists

## Advanced Usage

### Custom LaTeX Styling

```python
latex_gen = LaTeXThesisGenerator(title='My Thesis', author='Me')

# Add custom packages
latex_gen.add_package('listings', options=[None])
latex_gen.add_package('xcolor', options=['dvipsnames'])

# Add custom commands
latex_gen.add_custom_preamble([
    r'\newcommand{\code}[1]{\texttt{#1}}'
])

# Add equations
latex_gen.add_equation(r'E = mc^2', label='eq:einstein')

# Add appendix
latex_gen.add_appendix('Supplementary Material')
```

### Custom DOCX Template

```python
custom_config = {
    'font_name': 'Arial',
    'font_size': 11,
    'line_spacing': 1.5,
    'margin_top': 0.75,
    'margin_bottom': 0.75,
    'margin_left': 0.75,
    'margin_right': 0.75
}

exporter = AcademicDOCXExporter(
    template='custom',
    custom_config=custom_config
)
```

### Tables from DataFrames

```python
import pandas as pd
from export import AcademicDOCXExporter

exporter = AcademicDOCXExporter(template='apa')

df = pd.DataFrame({
    'Model': ['A', 'B', 'C'],
    'Accuracy': [85.2, 89.1, 92.3],
    'Time': [12.5, 10.2, 8.7]
})

exporter.add_table_from_dataframe(
    df,
    caption='Model comparison',
    style='Light Grid Accent 1'
)
```

## Examples

Run the complete integration example:

```bash
cd export
python example_usage.py
```

## File Structure

```
export/
├── __init__.py              # Package initialization
├── latex_generator.py        # LaTeX generation
├── bibtex_manager.py        # BibTeX management
├── docx_academic.py         # DOCX export
├── example_usage.py          # Complete examples
├── requirements.txt          # Python dependencies
└── README.md               # This file
```

## Output Examples

### LaTeX Thesis Structure

```latex
\documentclass[12pt,a4paper]{report}
\usepackage{graphicx}
\usepackage{cite}
\usepackage{amsmath}

\title{My PhD Thesis}
\author{Student Name}
\date{\today}

\begin{document}
\maketitle
\begin{abstract}
This thesis explores...
\end{abstract}

\tableofcontents
\listoffigures
\listoftables

\section{Chapter 1: Introduction}
Content...

\bibliographystyle{plain}
\bibliography{references}
\end{document}
```

### BibTeX Entry

```bibtex
@article{smith2023,
  title={A Novel Approach to Drug Discovery},
  author={Smith, J. and Doe, A.},
  year={2023},
  journal={Journal of Pharmacology},
  volume={45},
  number={2},
  pages={123-145},
  doi={10.1000/example.doi}
}
```

## Troubleshooting

### LaTeX Compilation Errors

**Error: `pdflatex` not found**
```bash
# Install TeX distribution
# macOS: brew install --cask mactex
# Linux: sudo apt-get install texlive-latex-base
# Windows: Download and install MiKTeX
```

**Error: Missing packages**
```bash
# Install missing LaTeX packages
tlmgr install package-name

# Or install full TeX Live distribution
```

### Missing Python Dependencies

```bash
# Install all required packages
pip install -r requirements.txt

# Individual packages
pip install pylatex bibtexparser python-docx pandas requests
```

### DOCX Import Errors

Ensure images exist before adding figures:
```python
from pathlib import Path
if Path('figure.png').exists():
    exporter.add_figure('figure.png', 'Caption')
```

## Performance Tips

1. **Batch Operations**: Use batch methods for multiple references
2. **Image Optimization**: Compress images before adding to documents
3. **Caching**: Cache fetched references to avoid API calls
4. **Table Size**: Large tables may slow down DOCX generation
5. **LaTeX Compilation**: Compile twice for correct references

## API Reference

### LaTeXThesisGenerator

```python
class LaTeXThesisGenerator:
    def __init__(self, template='report', title='', author='')
    def add_title_page()
    def add_abstract(text)
    def add_toc()
    def add_chapter(number, title, content)
    def add_equation(equation, label=None)
    def add_bibliography(bibtex_file, style='plain')
    def generate_tex(output_path)
    def compile_pdf(tex_path)
    def generate_and_compile(output_path)
```

### BibTeXManager

```python
class BibTeXManager:
    def __init__(self, entries=None)
    def add_from_pubmed(pmid, fetch_abstract=False)
    def add_from_doi(doi)
    def add_manual(entry)
    def format_citation(entry_id, style='apa')
    def export(filepath)
    def export_markdown(filepath)
    def search(query, fields=None)
    def find_duplicates()
```

### AcademicDOCXExporter

```python
class AcademicDOCXExporter:
    def __init__(self, template='ieee')
    def add_title_page(title, author, institution, date=None)
    def add_abstract(text)
    def add_chapter(number, title, sections)
    def add_table(data)
    def add_table_from_dataframe(df, caption=None)
    def add_figure(image_path, caption, width_inches=5.0)
    def add_references(references)
    def add_header(text)
    def add_footer(text, include_page_number=False)
    def export(filepath)
```

## Contributing

This is part of the BioDockify project. Contributions welcome!

## License

BioDockify - Academic Export Pipeline

## Version

Current Version: 1.0.0
