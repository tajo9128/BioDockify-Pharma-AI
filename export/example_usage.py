"""
Complete Export Pipeline Integration Example

This example demonstrates the complete academic export workflow:
1. Generate BibTeX references from PubMed/DOI
2. Create LaTeX thesis with chapters, figures, tables
3. Generate DOCX version with templates
4. Compile LaTeX to PDF

Make sure you have required dependencies installed:
    pip install pylatex bibtexparser python-docx pandas requests

For LaTeX compilation, ensure pdflatex is available:
    - Windows: Install MiKTeX or TeX Live
    - macOS: Install MacTeX
    - Linux: Install texlive-latex-base
"""

from pathlib import Path


def example_bibtex_workflow():
    """Demonstrate BibTeX reference management workflow"""

    print("\n" + "="*60)
    print("1. BibTeX Reference Management")
    print("="*60)

    from export.bibtex_manager import BibTeXManager

    # Initialize BibTeX manager
    bib_manager = BibTeXManager()

    print("\nAdding references...")

    # Add manual entry
    print("\n1a. Adding manual reference")
    manual_entry = {
        'ID': 'smith2023',
        'ENTRYTYPE': 'article',
        'title': 'A Novel Approach to Drug Discovery',
        'author': 'Smith, J. and Doe, A. and Johnson, M.',
        'year': '2023',
        'journal': 'Journal of Pharmacology',
        'volume': '45',
        'number': '2',
        'pages': '123-145',
        'doi': '10.1000/example.doi'
    }
    bib_manager.add_manual(manual_entry)
    print(f"✓ Added: {manual_entry['title']}")

    # Note: PubMed/DOI fetching requires internet connection
    # Uncomment to test real API calls:

    # print("\n1b. Fetching from PubMed (requires internet)")
    # try:
    #     entry = bib_manager.add_from_pubmed('12345678')
    #     print(f"✓ Fetched from PubMed: {entry['title']}")
    # except Exception as e:
    #     print(f"✗ Failed: {e}")

    # print("\n1c. Fetching from DOI (requires internet)")
    # try:
    #     entry = bib_manager.add_from_doi('10.1000/example.doi')
    #     print(f"✓ Fetched from DOI: {entry['title']}")
    # except Exception as e:
    #     print(f"✗ Failed: {e}")

    # Format citations
    print("\nFormatting citations...")
    entry_id = 'smith2023'

    apa = bib_manager.format_citation(entry_id, style='apa')
    print(f"\nAPA: {apa}")

    ieee = bib_manager.format_citation(entry_id, style='ieee')
    print(f"IEEE: {ieee}")

    nature = bib_manager.format_citation(entry_id, style='nature')
    print(f"Nature: {nature}")

    mla = bib_manager.format_citation(entry_id, style='mla')
    print(f"MLA: {mla}")

    chicago = bib_manager.format_citation(entry_id, style='chicago')
    print(f"Chicago: {chicago}")

    # Export bibliography
    print("\nExporting bibliography...")
    bib_file = bib_manager.export('references.bib')
    print(f"✓ Exported to: {bib_file}")

    # Export as Markdown
    md_file = bib_manager.export_markdown('references.md')
    print(f"✓ Exported to: {md_file}")

    # Get statistics
    stats = bib_manager.get_statistics()
    print(f"\nBibliography statistics:")
    print(f"  Total entries: {stats['total_entries']}")
    print(f"  Entry types: {stats['entry_types']}")

    return bib_manager


def example_latex_workflow():
    """Demonstrate LaTeX thesis generation workflow"""

    print("\n" + "="*60)
    print("2. LaTeX Thesis Generation")
    print("="*60)

    from export.latex_generator import LaTeXThesisGenerator

    # Initialize LaTeX generator
    latex_gen = LaTeXThesisGenerator(
        template='report',
        title='Novel Approaches to Drug Discovery',
        author='John Doe'
    )

    print("\nCreating LaTeX document structure...")

    # Add title page
    latex_gen.add_title_page()
    print("✓ Title page added")

    # Add abstract
    latex_gen.add_abstract(
        "This thesis presents novel computational approaches for accelerating "
        "drug discovery processes. We propose new methods for molecular docking, "
        "virtual screening, and lead optimization that significantly reduce "
        "computational time while improving accuracy."
    )
    print("✓ Abstract added")

    # Add table of contents
    latex_gen.add_toc()
    print("✓ Table of contents added")

    # Add chapter
    print("\nAdding chapter 1...")
    chapter_content = {
        'sections': [
            {
                'title': 'Introduction',
                'text': (
                    "Drug discovery is a complex and expensive process that typically "
                    "takes 10-15 years and costs billions of dollars. Traditional "
                    "methods involve high-throughput screening of large compound "
                    "libraries, but this approach has limitations in terms of cost "
                    "and time."
                ),
                'subsections': [
                    {
                        'title': 'Background',
                        'text': (
                            "The pharmaceutical industry faces increasing pressure to "
                            "develop new drugs more efficiently. Computational methods "
                            "have emerged as powerful tools to complement experimental "
                            "approaches."
                        )
                    },
                    {
                        'title': 'Problem Statement',
                        'text': (
                            "Despite advances in computational drug discovery, there "
                            "remain significant challenges in accuracy, speed, and "
                            "scalability of existing methods."
                        )
                    }
                ]
            },
            {
                'title': 'Literature Review',
                'text': (
                    "Previous research in this area has focused on improving "
                    "molecular docking algorithms cite{pmid12345678} and developing "
                    "new virtual screening methods cite{smith2023}."
                ),
                'figures': [
                    {
                        'path': 'figures/method_comparison.png',
                        'caption': 'Comparison of molecular docking methods',
                        'label': 'fig:methods'
                    }
                ],
                'tables': [
                    {
                        'headers': ['Method', 'Accuracy (%)', 'Time (h)'],
                        'rows': [
                            ['AutoDock Vina', 78.5, 12.3],
                            ['Glide', 82.1, 24.7],
                            ['Our Method', 89.3, 8.5]
                        ],
                        'caption': 'Performance comparison of docking methods',
                        'label': 'tab:performance'
                    }
                ]
            }
        ]
    }

    latex_gen.add_chapter(1, 'Introduction', chapter_content)
    print("✓ Chapter 1 added")

    # Add bibliography
    print("\nAdding bibliography...")
    latex_gen.add_bibliography('references', style='plain')
    print("✓ Bibliography added")

    # Generate .tex file
    print("\nGenerating LaTeX file...")
    tex_file = latex_gen.generate_tex('thesis')
    print(f"✓ Generated: {tex_file}")

    # Note: PDF compilation requires pdflatex
    # Uncomment to compile if pdflatex is available:
    # try:
    #     pdf_file = latex_gen.compile_pdf(tex_file)
    #     print(f"✓ Compiled PDF: {pdf_file}")
    # except Exception as e:
    #     print(f"✗ PDF compilation failed: {e}")
    #     print("  Note: Install TeX distribution (MiKTeX, TeX Live, or MacTeX)")

    print("\nTo compile to PDF:")
    print("  1. Ensure pdflatex is installed")
    print("  2. Place images in figures/ directory")
    print("  3. Run: pdflatex -interaction=nonstopmode thesis.tex")
    print("  4. Run again for references: pdflatex thesis.tex")

    return latex_gen


def example_docx_workflow():
    """Demonstrate DOCX export workflow"""

    print("\n" + "="*60)
    print("3. DOCX Academic Export")
    print("="*60)

    from export.docx_academic import AcademicDOCXExporter

    # Test with IEEE template
    print("\n3a. Using IEEE template")
    ieee_exporter = AcademicDOCXExporter(template='ieee')

    # Add title page
    ieee_exporter.add_title_page(
        "Novel Approaches to Drug Discovery",
        "John Doe",
        "University of Technology",
        date="January 2024"
    )
    print("✓ Title page added")

    # Add abstract
    ieee_exporter.add_abstract(
        "This thesis presents novel computational approaches for accelerating "
        "drug discovery processes through improved algorithms for molecular "
        "docking and virtual screening."
    )
    print("✓ Abstract added")

    # Add chapter
    chapter_sections = [
        {
            'title': 'Introduction',
            'text': (
                "Drug discovery is a complex process that typically takes "
                "10-15 years and costs billions of dollars. Our research "
                "aims to develop computational methods that significantly "
                "reduce this time and cost."
            ),
            'subsections': [
                {
                    'title': 'Background',
                    'text': (
                        "Traditional drug discovery involves high-throughput "
                        "screening of large compound libraries. While effective, "
                        "this approach is expensive and time-consuming."
                    )
                },
                {
                    'title': 'Objectives',
                    'text': (
                        "The main objectives of this research are:\n"
                        "1. Improve molecular docking accuracy\n"
                        "2. Reduce computational time\n"
                        "3. Develop scalable algorithms"
                    )
                }
            ],
            'tables': [
                {
                    'headers': ['Method', 'Accuracy (%)', 'Time (h)'],
                    'rows': [
                        ['Traditional', 75.2, 48.3],
                        ['Proposed', 89.3, 8.5]
                    ],
                    'caption': 'Performance comparison'
                }
            ]
        },
        {
            'title': 'Methods',
            'text': (
                "We propose a novel approach to molecular docking that "
                "combines deep learning with traditional physics-based methods."
            )
        }
    ]

    ieee_exporter.add_chapter(1, 'Introduction', chapter_sections)
    print("✓ Chapter 1 added")

    # Add references
    ieee_exporter.add_references([
        "Smith, J. et al. (2023). A novel approach to drug discovery. "
        "Journal of Pharmacology, 45(2), 123-145.",
        "Doe, A. et al. (2022). Advanced molecular docking methods. "
        "Nature Communications, 13, 4567."
    ])
    print("✓ References added")

    # Export IEEE version
    ieee_file = ieee_exporter.export('thesis_ieee.docx')
    print(f"✓ Exported IEEE template: {ieee_file}")

    # Test with APA template
    print("\n3b. Using APA template")
    apa_exporter = AcademicDOCXExporter(template='apa')

    apa_exporter.add_title_page(
        "Novel Approaches to Drug Discovery",
        "John Doe",
        "University of Technology"
    )

    apa_exporter.add_abstract(
        "This thesis presents novel computational approaches..."
    )

    apa_exporter.add_chapter(1, 'Introduction', chapter_sections)
    apa_exporter.add_references([
        "Smith, J. et al. (2023). A novel approach to drug discovery.",
        "Doe, A. et al. (2022). Advanced molecular docking methods."
    ])

    apa_file = apa_exporter.export('thesis_apa.docx')
    print(f"✓ Exported APA template: {apa_file}")

    return ieee_exporter


def example_complete_workflow():
    """Demonstrate complete export pipeline"""

    print("\n" + "="*60)
    print("COMPLETE EXPORT PIPELINE DEMONSTRATION")
    print("="*60)
    print("\nThis demonstration shows:")
    print("  1. BibTeX reference management")
    print("  2. LaTeX thesis generation")
    print("  3. DOCX academic export")

    try:
        # Step 1: BibTeX
        bib_manager = example_bibtex_workflow()

        # Step 2: LaTeX
        latex_gen = example_latex_workflow()

        # Step 3: DOCX
        docx_gen = example_docx_workflow()

        print("\n" + "="*60)
        print("PIPELINE DEMONSTRATION COMPLETE")
        print("="*60)
        print("\nGenerated files:")
        print("  - references.bib")
        print("  - references.md")
        print("  - thesis.tex")
        print("  - thesis_ieee.docx")
        print("  - thesis_apa.docx")

    except Exception as e:
        print(f"\nError during pipeline demonstration: {e}")
        import traceback
        traceback.print_exc()


def example_advanced_latex():
    """Demonstrate advanced LaTeX features"""

    print("\n" + "="*60)
    print("4. Advanced LaTeX Features")
    print("="*60)

    from export.latex_generator import LaTeXThesisGenerator

    latex_gen = LaTeXThesisGenerator(
        template='report',
        title='Advanced LaTeX Example',
        author='Jane Smith'
    )

    # Add custom packages
    latex_gen.add_package('listings', options=[None])
    latex_gen.add_package('xcolor', options=['dvipsnames'])

    # Add custom commands
    latex_gen.add_custom_preamble([
        r'\definecolor{codegray}{rgb}{0.5,0.5,0.5}',
        r'\newcommand{\code}[1]{\texttt{\color{codegray}#1}}'
    ])

    latex_gen.add_title_page()
    latex_gen.add_abstract("This example demonstrates advanced LaTeX features...")

    # Add chapters with figures and tables
    chapter = {
        'sections': [
            {
                'title': 'Methods',
                'text': 'We used the following approaches:',
                'figures': [
                    {
                        'path': 'figures/architecture.png',
                        'caption': 'System architecture',
                        'width': '0.6\\textwidth',
                        'label': 'fig:architecture'
                    }
                ]
            }
        ]
    }

    latex_gen.add_chapter(1, 'Methodology', chapter)

    # Add equations
    latex_gen.add_equation(r'E = mc^2', label='eq:einstein')
    latex_gen.add_equation(r'f(x) = \int_{-\infty}^{\infty} e^{-x^2} dx', label='eq:gaussian')

    # Add appendix
    latex_gen.add_appendix('Supplementary Material')

    # Generate
    tex_file = latex_gen.generate_tex('advanced_example')
    print(f"✓ Generated: {tex_file}")


def example_advanced_docx():
    """Demonstrate advanced DOCX features"""

    print("\n" + "="*60)
    print("5. Advanced DOCX Features")
    print("="*60)

    from export.docx_academic import AcademicDOCXExporter
    import pandas as pd

    exporter = AcademicDOCXExporter(template='apa')

    # Add custom margins
    exporter.set_margins(top=0.75, bottom=0.75, left=1.0, right=1.0)
    print("✓ Custom margins set")

    # Add header and footer
    exporter.add_header("PhD Thesis - John Doe")
    exporter.add_footer("Confidential", include_page_number=True)
    print("✓ Header and footer added")

    # Add table of contents placeholder
    exporter.add_table_of_contents()

    # Add title page
    exporter.add_title_page(
        "Advanced DOCX Example",
        "Jane Smith",
        "Research University",
        date="2024"
    )

    # Add formatted paragraphs
    exporter.add_paragraph(
        "This is a normal paragraph with some text.",
        align='justify'
    )

    exporter.add_paragraph(
        "This is a bold paragraph.",
        bold=True
    )

    exporter.add_paragraph(
        "This is an indented paragraph.",
        first_line_indent=0.5
    )

    # Add lists
    exporter.add_bullet_list([
        "First bullet point",
        "Second bullet point",
        "Third bullet point"
    ])
    print("✓ Lists added")

    exporter.add_numbered_list([
        "First item",
        "Second item",
        "Third item"
    ])

    # Add table from DataFrame
    df = pd.DataFrame({
        'Model': ['A', 'B', 'C'],
        'Accuracy': [85.2, 89.1, 92.3],
        'Time (s)': [12.5, 10.2, 8.7]
    })

    exporter.add_table_from_dataframe(
        df,
        caption='Model comparison results'
    )
    print("✓ Table from DataFrame added")

    # Add horizontal line
    exporter.add_horizontal_line()

    # Export
    output_file = exporter.export('advanced_example.docx')
    print(f"✓ Exported: {output_file}")


def main():
    """Main function to run all demonstrations"""

    print("\n" + "="*60)
    print("ACADEMIC EXPORT PIPELINE - INTEGRATION EXAMPLES")
    print("="*60)

    print("\nAvailable demonstrations:")
    print("  1. BibTeX reference management")
    print("  2. LaTeX thesis generation")
    print("  3. DOCX academic export")
    print("  4. Advanced LaTeX features")
    print("  5. Advanced DOCX features")
    print("  6. Complete workflow (all components)")

    # Run complete workflow
    example_complete_workflow()

    # Uncomment to run advanced examples:
    # example_advanced_latex()
    # example_advanced_docx()

    print("\n" + "="*60)
    print("USAGE NOTES")
    print("="*60)
    print("\nBibTeX Manager:")
    print("  - Fetch from PubMed: bib_manager.add_from_pubmed('pmid')")
    print("  - Fetch from DOI: bib_manager.add_from_doi('doi')")
    print("  - Manual entry: bib_manager.add_manual({...})")
    print("  - Format citations: bib_manager.format_citation('id', style='apa')")

    print("\nLaTeX Generator:")
    print("  - Compile requires pdflatex (TeX Live, MiKTeX, or MacTeX)")
    print("  - Generate .tex: latex_gen.generate_tex('output')")
    print("  - Compile PDF: latex_gen.compile_pdf('output.tex')")
    print("  - One-step: latex_gen.generate_and_compile('output')")

    print("\nDOCX Exporter:")
    print("  - Templates: 'ieee', 'apa', 'nature', 'custom'")
    print("  - Export: exporter.export('output.docx')")
    print("  - Tables from DataFrame: exporter.add_table_from_dataframe(df)")

    print("\n" + "="*60)


if __name__ == '__main__':
    main()
