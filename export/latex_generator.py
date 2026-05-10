"""
LaTeX Thesis Generator

This module provides comprehensive LaTeX generation for PhD theses and academic publications,
including:
- Document structure with chapters and sections
- Figure and table insertion
- Bibliography integration with BibTeX
- Multiple document classes (article, report, book)
- Customizable templates
- PDF compilation support

Export Pipeline:
Research Data → Template Selection → Content Assembly → LaTeX → Bibliography → PDF Output
"""

import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass
import logging
import os


try:
    from pylatex import Document, Section, Subsection, Command, Package
    from pylatex.utils import NoEscape, italic, bold
    from pylatex.base_classes import Environment
    from pylatex import Figure, SubFigure, Table, Tabular
    PYLATEX_AVAILABLE = True
except ImportError:
    PYLATEX_AVAILABLE = False
    logging.warning("pylatex not available. Install with: pip install pylatex")


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class FigureData:
    """Data structure for figures in LaTeX"""
    path: str
    caption: str
    label: Optional[str] = None
    width: str = '0.8\\textwidth'
    position: str = 'htbp'


@dataclass
class TableData:
    """Data structure for tables in LaTeX"""
    headers: List[str]
    rows: List[List[Any]]
    caption: str
    label: Optional[str] = None
    position: str = 'htbp'
    alignment: str = '|c|'  # Default centered column


class LaTeXThesisGenerator:
    """
    LaTeX thesis and academic document generator

    Features:
    - Multiple document classes (article, report, book)
    - Chapter and section structure
    - Figure and table insertion
    - Abstract support
    - BibTeX bibliography integration
    - Custom preamble packages
    - PDF compilation with pdflatex
    - Cross-references and labels

    Supported Document Classes:
    - article: For journal articles
    - report: For reports and theses
    - book: For books and longer documents
    """

    # Standard LaTeX packages for academic documents
    STANDARD_PACKAGES = [
        'graphicx',      # For figures
        'cite',          # For citations
        'amsmath',       # For math
        'amssymb',       # For math symbols
        'hyperref',      # For hyperlinks
        'geometry',      # For page geometry
        'setspace',      # For line spacing
        'caption',       # For caption customization
        'float',         # For float positioning
        'booktabs',      # For nicer tables
    ]

    def __init__(
        self,
        template: str = 'report',
        title: str = 'PhD Thesis',
        author: str = 'Student Name',
        date: Optional[str] = None,
        document_options: Optional[List[str]] = None
    ):
        """
        Initialize LaTeX thesis generator

        Args:
            template: Document class ('article', 'report', 'book')
            title: Document title
            author: Document author
            date: Document date (None for current date)
            document_options: Additional options for document class
        """
        if not PYLATEX_AVAILABLE:
            raise ImportError(
                "pylatex is required. Install with: pip install pylatex"
            )

        self.template = template
        self.title = title
        self.author = author

        # Document class options
        if document_options is None:
            if template == 'report':
                document_options = ['12pt', 'a4paper']
            else:
                document_options = ['11pt', 'a4paper']

        self.doc = Document(documentclass=template, document_options=document_options)

        # Set default date
        if date is None:
            date = NoEscape(r'\today')

        # Add preamble
        self._setup_preamble(title, author, date)

        logger.info(f"LaTeX generator initialized with template: {template}")

    def _setup_preamble(self, title: str, author: str, date):
        """Setup document preamble with packages and metadata"""

        # Add standard packages
        for package in self.STANDARD_PACKAGES:
            self.doc.preamble.append(Package(package))

        # Set page geometry
        self.doc.preamble.append(NoEscape(r'\geometry{margin=1in}'))

        # Set line spacing
        self.doc.preamble.append(NoEscape(r'\doublespacing'))

        # Add title and author
        self.doc.preamble.append(Command('title', title))
        self.doc.preamble.append(Command('author', author))
        self.doc.preamble.append(Command('date', date))

        # Setup hyperref
        self.doc.preamble.append(NoEscape(
            r'\hypersetup{'
            r'pdfauthor={' + author + '},'
            r'pdftitle={' + title + '},'
            r'hidelinks,'
            r'colorlinks=true,'
            r'linkcolor=blue,'
            r'citecolor=blue,'
            r'urlcolor=blue'
            r'}'
        ))

    def add_package(self, package: str, options: Optional[str] = None):
        """
        Add additional LaTeX package

        Args:
            package: Package name
            options: Package options (optional)
        """
        if options:
            self.doc.preamble.append(Package(package, options=options))
        else:
            self.doc.preamble.append(Package(package))

    def add_custom_preamble(self, commands: List[str]):
        """
        Add custom LaTeX commands to preamble

        Args:
            commands: List of LaTeX command strings
        """
        for command in commands:
            self.doc.preamble.append(NoEscape(command))

    def add_title_page(self):
        """Generate title page"""
        self.doc.append(NoEscape(r'\maketitle'))
        self.doc.append(NoEscape(r'\newpage'))

    def add_abstract(self, text: str):
        """
        Add abstract section

        Args:
            text: Abstract text
        """
        with self.doc.create(Environment('abstract')):
            self.doc.append(text)

        logger.debug("Abstract added")

    def add_toc(self):
        """Add table of contents"""
        self.doc.append(NoEscape(r'\tableofcontents'))
        self.doc.append(NoEscape(r'\newpage'))
        logger.debug("Table of contents added")

    def add_list_of_figures(self):
        """Add list of figures"""
        self.doc.append(NoEscape(r'\listoffigures'))
        self.doc.append(NoEscape(r'\newpage'))
        logger.debug("List of figures added")

    def add_list_of_tables(self):
        """Add list of tables"""
        self.doc.append(NoEscape(r'\listoftables'))
        self.doc.append(NoEscape(r'\newpage'))
        logger.debug("List of tables added")

    def add_chapter(
        self,
        number: int,
        title: str,
        content: Dict[str, Any],
        add_label: Optional[str] = None
    ):
        """
        Add PhD thesis chapter

        Args:
            number: Chapter number
            title: Chapter title
            content: Dict with sections, subsections, paragraphs
            add_label: Optional label for cross-referencing
        """
        chapter_title = f'Chapter {number}: {title}'

        with self.doc.create(Section(chapter_title, numbering=True)):
            if add_label:
                self.doc.append(NoEscape(f'\\label{{{add_label}}}'))

            # Add sections
            for section_data in content.get('sections', []):
                self._add_section(section_data)

        logger.debug(f"Added chapter {number}: {title}")

    def _add_section(self, section_data: Dict[str, Any], level: int = 2):
        """
        Add section or subsection

        Args:
            section_data: Section data with title, text, figures, tables
            level: Section level (2=subsection, 3=subsubsection)
        """
        section_title = section_data.get('title', 'Untitled')

        # Create appropriate section level
        if level == 2:
            with self.doc.create(Subsection(section_title)):
                self._add_section_content(section_data)
        elif level == 3:
            with self.doc.create(Subsection(section_title)):
                with self.doc.create(Subsection('Subsection')):
                    self._add_section_content(section_data)

    def _add_section_content(self, section_data: Dict[str, Any]):
        """Add content to section (text, figures, tables)"""

        # Add text
        text = section_data.get('text', '')
        if text:
            self.doc.append(text)
            self.doc.append(NoEscape(r'\par'))

        # Add subsections
        for subsection in section_data.get('subsections', []):
            self._add_section(subsection, level=3)

        # Add figures
        for figure in section_data.get('figures', []):
            self._add_figure(figure)

        # Add tables
        for table in section_data.get('tables', []):
            self._add_table(table)

    def add_section(
        self,
        title: str,
        content: str,
        subsections: Optional[List[Dict]] = None
    ):
        """
        Add a simple section (for article class)

        Args:
            title: Section title
            content: Section content text
            subsections: Optional list of subsections
        """
        with self.doc.create(Section(title, numbering=True)):
            self.doc.append(content)

            if subsections:
                for subsection_data in subsections:
                    subsection_title = subsection_data.get('title', 'Untitled')
                    subsection_content = subsection_data.get('text', '')

                    with self.doc.create(Subsection(subsection_title)):
                        self.doc.append(subsection_content)

    def _add_figure(self, figure: Union[Dict, FigureData]):
        """
        Add figure with caption

        Args:
            figure: Figure data as dict or FigureData object
        """
        if isinstance(figure, dict):
            fig_data = FigureData(**figure)
        else:
            fig_data = figure

        with self.doc.create(Figure(position=fig_data.position)) as fig:
            fig.add_image(fig_data.path, width=NoEscape(fig_data.width))
            fig.add_caption(fig_data.caption)

            if fig_data.label:
                fig.append(NoEscape(f'\\label{{{fig_data.label}}}'))

    def _add_table(self, table: Union[Dict, TableData]):
        """
        Add table with caption

        Args:
            table: Table data as dict or TableData object
        """
        if isinstance(table, dict):
            table_data = TableData(
                headers=table['headers'],
                rows=table['rows'],
                caption=table['caption'],
                label=table.get('label'),
                alignment=table.get('alignment', '|c|')
            )
        else:
            table_data = table

        # Create alignment string based on number of columns
        num_cols = len(table_data.headers)
        if table_data.alignment == '|c|':
            alignment = '|' + '|'.join(['c'] * num_cols) + '|'
        else:
            alignment = table_data.alignment

        with self.doc.create(Table(position=table_data.position)) as tbl:
            with self.doc.create(Tabular(alignment)) as tabular:
                # Header row
                tabular.add_hline()
                tabular.add_row(table_data.headers)
                # Make header bold
                for cell in tabular.rows[0]:
                    cell.append(bold(cell.text))
                tabular.add_hline()

                # Data rows
                for row_data in table_data.rows:
                    tabular.add_row([str(cell) for cell in row_data])
                tabular.add_hline()

            tbl.add_caption(table_data.caption)

            if table_data.label:
                tbl.append(NoEscape(f'\\label{{{table_data.label}}}'))

    def add_equation(self, equation: str, label: Optional[str] = None):
        """
        Add mathematical equation

        Args:
            equation: LaTeX equation
            label: Optional label for referencing
        """
        self.doc.append(NoEscape(r'\begin{equation}'))
        self.doc.append(NoEscape(equation))
        self.doc.append(NoEscape(r'\end{equation}'))

        if label:
            self.doc.append(NoEscape(f'\\label{{{label}}}'))

    def add_bibliography(self, bibtex_file: str, style: str = 'plain'):
        """
        Include BibTeX references

        Args:
            bibtex_file: Path to .bib file (without extension)
            style: Bibliography style (plain, abbrv, alpha, etc.)
        """
        self.doc.append(NoEscape(r'\bibliographystyle{' + style + '}'))
        self.doc.append(NoEscape(rf'\bibliography{{{bibtex_file}}}'))
        logger.debug(f"Bibliography added: {bibtex_file}")

    def add_appendix(self, title: str = 'Appendix'):
        """
        Add appendix section

        Args:
            title: Appendix title
        """
        self.doc.append(NoEscape(r'\appendix'))
        with self.doc.create(Section(title)):
            pass

    def generate_tex(self, output_path: str) -> str:
        """
        Generate .tex file

        Args:
            output_path: Output file path (without .tex extension)

        Returns:
            Path to generated .tex file
        """
        # Ensure .tex extension
        if not output_path.endswith('.tex'):
            tex_path = output_path + '.tex'
        else:
            tex_path = output_path

        # Generate tex file
        self.doc.generate_tex(tex_path)

        logger.info(f"LaTeX file generated: {tex_path}")
        return tex_path

    def compile_pdf(
        self,
        tex_path: str,
        compile_twice: bool = True,
        clean_auxiliary: bool = True
    ) -> str:
        """
        Compile LaTeX to PDF using pdflatex

        Args:
            tex_path: Path to .tex file
            compile_twice: Whether to compile twice (for references)
            clean_auxiliary: Whether to clean auxiliary files

        Returns:
            Path to generated PDF file

        Raises:
            RuntimeError: If pdflatex is not found
            Exception: If compilation fails
        """
        # Check if pdflatex is available
        if not self._check_pdflatex():
            raise RuntimeError(
                "pdflatex not found. Install LaTeX distribution (TeX Live, MiKTeX, or MacTeX)"
            )

        tex_file = Path(tex_path)
        if not tex_file.exists():
            raise FileNotFoundError(f"TeX file not found: {tex_path}")

        logger.info(f"Compiling {tex_path}...")

        # Compile once or twice (twice needed for references)
        num_compilations = 2 if compile_twice else 1

        for i in range(num_compilations):
            result = subprocess.run(
                ['pdflatex', '-interaction=nonstopmode', str(tex_file)],
                capture_output=True,
                text=True,
                cwd=tex_file.parent
            )

            if result.returncode != 0:
                logger.error(f"LaTeX compilation failed (attempt {i+1})")
                logger.error(f"Error output:\n{result.stderr}")
                raise Exception(f"LaTeX compilation failed: {result.stderr}")

            logger.debug(f"Compilation {i+1} successful")

        # Clean auxiliary files
        if clean_auxiliary:
            self._clean_auxiliary_files(tex_file)

        pdf_path = tex_file.with_suffix('.pdf')
        logger.info(f"PDF generated: {pdf_path}")

        return str(pdf_path)

    def _check_pdflatex(self) -> bool:
        """Check if pdflatex is available"""
        try:
            result = subprocess.run(
                ['pdflatex', '--version'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _clean_auxiliary_files(self, tex_file: Path):
        """Clean LaTeX auxiliary files"""
        extensions = ['.aux', '.log', '.out', '.toc', '.lof', '.lot']

        for ext in extensions:
            aux_file = tex_file.with_suffix(ext)
            if aux_file.exists():
                aux_file.unlink()
                logger.debug(f"Cleaned auxiliary file: {aux_file}")

    def generate_and_compile(
        self,
        output_path: str,
        bibtex_file: Optional[str] = None,
        clean: bool = True
    ) -> str:
        """
        Generate .tex and compile to PDF in one step

        Args:
            output_path: Output file path (without extension)
            bibtex_file: Optional BibTeX file path
            clean: Whether to clean auxiliary files

        Returns:
            Path to generated PDF file
        """
        # Generate .tex
        tex_path = self.generate_tex(output_path)

        # Add bibliography if provided
        if bibtex_file:
            self.add_bibliography(bibtex_file)
            # Regenerate with bibliography
            tex_path = self.generate_tex(output_path)

        # Compile to PDF
        pdf_path = self.compile_pdf(tex_path, compile_twice=True, clean=clean)

        return pdf_path


class LaTeXArticleGenerator(LaTeXThesisGenerator):
    """Simplified generator for journal articles"""

    def __init__(
        self,
        title: str,
        author: str,
        affiliation: str = '',
        document_options: Optional[List[str]] = None
    ):
        """Initialize article generator"""
        super().__init__(
            template='article',
            title=title,
            author=author,
            document_options=document_options
        )

        # Add affiliation
        if affiliation:
            self.doc.preamble.append(NoEscape(
                f'\\affiliation{{{affiliation}}}'
            ))

    def add_abstract(self, text: str):
        """Add abstract with keywords"""
        super().add_abstract(text)
        logger.debug("Abstract added for article")


def create_simple_document(
    title: str,
    author: str,
    content: str,
    output_path: str = 'document'
) -> str:
    """
    Helper function to create a simple LaTeX document

    Args:
        title: Document title
        author: Document author
        content: Document content
        output_path: Output file path

    Returns:
        Path to generated PDF
    """
    gen = LaTeXThesisGenerator(template='article', title=title, author=author)

    gen.add_title_page()
    gen.add_abstract("Abstract text here...")

    gen.add_section('Introduction', content)

    return gen.generate_and_compile(output_path)


if __name__ == '__main__':
    # Example usage
    gen = LaTeXThesisGenerator(
        template='report',
        title='My PhD Thesis',
        author='John Doe'
    )

    gen.add_title_page()
    gen.add_abstract("This thesis explores...")

    gen.add_toc()
    gen.add_list_of_figures()
    gen.add_list_of_tables()

    gen.add_chapter(1, 'Introduction', {
        'sections': [
            {
                'title': 'Background',
                'text': 'Drug discovery is...',
                'subsections': [
                    {'title': 'History', 'text': 'Historical context...'}
                ]
            }
        ]
    })

    gen.generate_and_compile('thesis')
