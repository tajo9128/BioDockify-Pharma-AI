"""
GROBID Integration for Scientific PDF Parsing

This module provides integration with GROBID (GeneRation Of BIbliographic Data)
for parsing scientific PDFs into structured TEI XML format.

Pipeline Flow:
PDF → GROBID → TEI XML → Structured Sections (title, abstract, sections, references)
"""

import requests
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
import time


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ParsedSection:
    """Represents a parsed section from a PDF"""
    heading: str
    text: str
    level: int = 1


@dataclass
class ParsedReference:
    """Represents a parsed reference"""
    title: str
    authors: List[str]
    year: Optional[int] = None
    journal: Optional[str] = None
    doi: Optional[str] = None


@dataclass
class ParsedPaper:
    """Complete parsed paper with all sections"""
    title: str
    abstract: str
    sections: List[Dict]
    references: List[Dict]
    figures: List[Dict]
    tables: List[Dict]
    authors: List[str]
    keywords: List[str]
    metadata: Dict


class GROBIDParser:
    """
    GROBID Integration for parsing scientific PDFs

    This class provides methods to:
    - Parse individual PDFs
    - Batch parse multiple PDFs
    - Extract structured sections from TEI XML
    - Handle errors gracefully
    """

    # TEI namespace
    TEI_NS = {'tei': 'http://www.tei-c.org/ns/1.0'}

    # GROBID endpoints
    ENDPOINTS = {
        'processFulltextDocument': '/api/processFulltextDocument',
        'processHeaderDocument': '/api/processHeaderDocument',
        'processReferences': '/api/processReferences',
        'processCitationList': '/api/processCitationList'
    }

    def __init__(
        self,
        grobid_url: str = "http://localhost:8070",
        timeout: int = 120,
        max_retries: int = 3
    ):
        """
        Initialize GROBID parser

        Args:
            grobid_url: Base URL of GROBID server
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.base_url = grobid_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries

        # Validate GROBID is accessible
        self._check_grobid_connection()

        logger.info(f"GROBID parser initialized with URL: {self.base_url}")

    def _check_grobid_connection(self) -> bool:
        """Check if GROBID server is accessible"""
        try:
            response = requests.get(
                f"{self.base_url}/api/isalive",
                timeout=10
            )
            if response.status_code == 200:
                logger.info("GROBID server is alive")
                return True
            else:
                logger.warning(f"GROBID server returned status: {response.status_code}")
                return False
        except Exception as e:
            logger.warning(f"Could not connect to GROBID: {e}")
            logger.warning("Ensure GROBID is running or the URL is correct")
            return False

    def parse_pdf(
        self,
        pdf_path: str,
        extract_sections: bool = True,
        extract_references: bool = True
    ) -> ParsedPaper:
        """
        Parse scientific PDF using GROBID

        Args:
            pdf_path: Path to PDF file
            extract_sections: Whether to extract full text sections
            extract_references: Whether to extract references

        Returns:
            ParsedPaper object with structured content

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            Exception: If GROBID parsing fails
        """
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        logger.info(f"Parsing PDF: {pdf_path}")

        # Send PDF to GROBID
        xml_text = self._send_to_grobid(pdf_path, 'processFulltextDocument')

        # Parse XML output
        parsed_data = self._parse_tei_xml(
            xml_text,
            extract_sections=extract_sections,
            extract_references=extract_references
        )

        return ParsedPaper(**parsed_data)

    def _send_to_grobid(
        self,
        pdf_path: str,
        endpoint: str = 'processFulltextDocument'
    ) -> str:
        """
        Send PDF to GROBID for processing

        Args:
            pdf_path: Path to PDF file
            endpoint: GROBID endpoint to use

        Returns:
            TEI XML as string

        Raises:
            Exception: If request fails after retries
        """
        url = f"{self.base_url}{self.ENDPOINTS[endpoint]}"

        for attempt in range(self.max_retries):
            try:
                with open(pdf_path, 'rb') as f:
                    files = {'input': f}
                    headers = {'Accept': 'application/xml'}

                    response = requests.post(
                        url,
                        files=files,
                        headers=headers,
                        timeout=self.timeout
                    )

                if response.status_code == 200:
                    return response.text
                elif response.status_code == 500:
                    # GROBID internal error, might work on retry
                    logger.warning(f"GROBID returned 500, attempt {attempt + 1}/{self.max_retries}")
                    if attempt < self.max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                else:
                    raise Exception(
                        f"GROBID error: {response.status_code} - {response.text[:200]}"
                    )

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout on attempt {attempt + 1}/{self.max_retries}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise Exception(f"GROBID request failed: {str(e)}")
                logger.warning(f"Request error on attempt {attempt + 1}: {e}")

        raise Exception(f"Failed to parse PDF after {self.max_retries} attempts")

    def _parse_tei_xml(
        self,
        xml_text: str,
        extract_sections: bool = True,
        extract_references: bool = True
    ) -> Dict[str, Any]:
        """
        Parse GROBID's TEI XML format

        Args:
            xml_text: TEI XML string from GROBID
            extract_sections: Whether to extract full text sections
            extract_references: Whether to extract references

        Returns:
            Dictionary with parsed content
        """
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            logger.error(f"Failed to parse TEI XML: {e}")
            raise

        result = {
            'title': '',
            'abstract': '',
            'sections': [],
            'references': [],
            'figures': [],
            'tables': [],
            'authors': [],
            'keywords': [],
            'metadata': {}
        }

        # Extract title
        title_elem = root.find('.//tei:titleStmt/tei:title', self.TEI_NS)
        if title_elem is not None and title_elem.text:
            result['title'] = title_elem.text.strip()

        # Extract authors
        authors = root.findall('.//tei:sourceDesc//tei:author', self.TEI_NS)
        for author in authors:
            forename = author.find('.//tei:forename', self.TEI_NS)
            surname = author.find('.//tei:surname', self.TEI_NS)
            if forename is not None and surname is not None:
                result['authors'].append(
                    f"{forename.text.strip() if forename.text else ''} "
                    f"{surname.text.strip() if surname.text else ''}"
                )

        # Extract keywords
        keywords_elem = root.find('.//tei:keywords', self.TEI_NS)
        if keywords_elem is not None:
            for term in keywords_elem.findall('.//tei:term', self.TEI_NS):
                if term.text:
                    result['keywords'].append(term.text.strip())

        # Extract publication metadata
        date_elem = root.find('.//tei:publicationStmt/tei:date', self.TEI_NS)
        if date_elem is not None and date_elem.get('when'):
            result['metadata']['publication_date'] = date_elem.get('when')

        journal_elem = root.find('.//tei:monogr/tei:title[@level="j"]', self.TEI_NS)
        if journal_elem is not None and journal_elem.text:
            result['metadata']['journal'] = journal_elem.text.strip()

        doi_elem = root.find('.//tei:idno[@type="DOI"]', self.TEI_NS)
        if doi_elem is not None and doi_elem.text:
            result['metadata']['doi'] = doi_elem.text.strip()

        # Extract abstract
        abstract_elem = root.find('.//tei:profileDesc/tei:abstract', self.TEI_NS)
        if abstract_elem is not None:
            abstract_text = ''.join(abstract_elem.itertext())
            result['abstract'] = self._clean_text(abstract_text)

        # Extract sections
        if extract_sections:
            result['sections'] = self._extract_sections(root)

            # Extract figures
            result['figures'] = self._extract_figures(root)

            # Extract tables
            result['tables'] = self._extract_tables(root)

        # Extract references
        if extract_references:
            result['references'] = self._extract_references(root)

        return result

    def _extract_sections(self, root: ET.Element) -> List[Dict]:
        """Extract all sections from document body"""
        sections = []

        body = root.find('.//tei:text/tei:body', self.TEI_NS)
        if body is None:
            return sections

        # Process divs recursively
        for div in body.findall('.//tei:div', self.TEI_NS):
            head = div.find('.//tei:head', self.TEI_NS)
            section_title = head.text.strip() if head is not None and head.text else 'Untitled Section'

            section_text = ''.join(div.itertext())
            section_text = self._clean_text(section_text)

            if len(section_text) > 50:  # Filter out very short sections
                sections.append({
                    'heading': section_title,
                    'text': section_text,
                    'level': int(div.get('n', 1))
                })

        return sections

    def _extract_references(self, root: ET.Element) -> List[Dict]:
        """Extract bibliography references"""
        references = []

        back = root.find('.//tei:text/tei:back', self.TEI_NS)
        if back is None:
            return references

        list_bibl = back.find('.//tei:listBibl', self.TEI_NS)
        if list_bibl is None:
            return references

        for bibl in list_bibl.findall('.//tei:biblStruct', self.TEI_NS):
            ref = {}

            # Extract title
            title = bibl.find('.//tei:analytic/tei:title', self.TEI_NS)
            if title is not None:
                ref['title'] = title.text.strip() if title.text else ''

            # Extract authors
            authors = []
            for author in bibl.findall('.//tei:author', self.TEI_NS):
                pers_name = author.find('.//tei:persName', self.TEI_NS)
                if pers_name is not None:
                    forename = pers_name.find('.//tei:forename', self.TEI_NS)
                    surname = pers_name.find('.//tei:surname', self.TEI_NS)
                    name_parts = []
                    if forename is not None and forename.text:
                        name_parts.append(forename.text.strip())
                    if surname is not None and surname.text:
                        name_parts.append(surname.text.strip())
                    if name_parts:
                        authors.append(' '.join(name_parts))
            ref['authors'] = authors

            # Extract year
            year = bibl.find('.//tei:imprint/tei:date', self.TEI_NS)
            if year is not None:
                ref['year'] = year.text.strip() if year.text else None

            # Extract journal
            journal = bibl.find('.//tei:monogr/tei:title[@level="j"]', self.TEI_NS)
            if journal is not None:
                ref['journal'] = journal.text.strip() if journal.text else ''

            # Extract DOI
            doi = bibl.find('.//tei:idno[@type="DOI"]', self.TEI_NS)
            if doi is not None:
                ref['doi'] = doi.text.strip() if doi.text else None

            if ref.get('title') or ref.get('authors'):
                references.append(ref)

        return references

    def _extract_figures(self, root: ET.Element) -> List[Dict]:
        """Extract figure information"""
        figures = []

        for fig in root.findall('.//tei:figure', self.TEI_NS):
            fig_data = {}

            # Get figure label
            label = fig.find('.//tei:label', self.TEI_NS)
            if label is not None and label.text:
                fig_data['label'] = label.text.strip()

            # Get figure caption
            caption = fig.find('.//tei:figDesc', self.TEI_NS)
            if caption is not None:
                caption_text = ''.join(caption.itertext())
                fig_data['caption'] = self._clean_text(caption_text)

            if fig_data:
                figures.append(fig_data)

        return figures

    def _extract_tables(self, root: ET.Element) -> List[Dict]:
        """Extract table information"""
        tables = []

        for table in root.findall('.//tei:table', self.TEI_NS):
            table_data = {}

            # Get table label
            label = table.find('.//tei:label', self.TEI_NS)
            if label is not None and label.text:
                table_data['label'] = label.text.strip()

            # Get table caption
            caption = table.find('.//tei:note', self.TEI_NS)
            if caption is not None:
                caption_text = ''.join(caption.itertext())
                table_data['caption'] = self._clean_text(caption_text)

            # Count rows and columns
            rows = table.findall('.//tei:row', self.TEI_NS)
            table_data['rows'] = len(rows)
            if rows:
                table_data['columns'] = max(
                    len(r.findall('.//tei:cell', self.TEI_NS)) for r in rows
                )

            if table_data:
                tables.append(table_data)

        return tables

    def _clean_text(self, text: str) -> str:
        """Clean extracted text"""
        if not text:
            return ''

        # Remove excessive whitespace
        text = ' '.join(text.split())

        # Remove control characters
        text = ''.join(char for char in text if ord(char) >= 32 or char == '\n')

        return text.strip()

    def batch_parse(
        self,
        pdf_paths: List[str],
        max_workers: int = 4,
        extract_sections: bool = True,
        extract_references: bool = True
    ) -> List[Dict]:
        """
        Parse multiple PDFs in parallel

        Args:
            pdf_paths: List of paths to PDF files
            max_workers: Number of parallel workers
            extract_sections: Whether to extract sections
            extract_references: Whether to extract references

        Returns:
            List of dictionaries with parsed data or errors
        """
        results = []

        logger.info(f"Batch parsing {len(pdf_paths)} PDFs with {max_workers} workers")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_path = {
                executor.submit(
                    self._parse_single_pdf,
                    path,
                    extract_sections,
                    extract_references
                ): path
                for path in pdf_paths
            }

            # Collect results as they complete
            for future in as_completed(future_to_path):
                path = future_to_path[future]

                try:
                    parsed = future.result()
                    results.append({
                        'success': True,
                        'file_path': path,
                        'data': asdict(parsed)
                    })
                    logger.info(f"Successfully parsed: {path}")
                except Exception as e:
                    logger.error(f"Error parsing {path}: {e}")
                    results.append({
                        'success': False,
                        'file_path': path,
                        'error': str(e)
                    })

        successful = sum(1 for r in results if r['success'])
        logger.info(f"Batch parsing complete: {successful}/{len(pdf_paths)} successful")

        return results

    def _parse_single_pdf(
        self,
        pdf_path: str,
        extract_sections: bool,
        extract_references: bool
    ) -> ParsedPaper:
        """Wrapper for single PDF parsing with error handling"""
        try:
            return self.parse_pdf(pdf_path, extract_sections, extract_references)
        except Exception as e:
            logger.error(f"Failed to parse {pdf_path}: {e}")
            raise

    def parse_header_only(self, pdf_path: str) -> Dict:
        """
        Parse only the header/metadata of a PDF (faster)

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary with metadata only
        """
        logger.info(f"Parsing header only: {pdf_path}")

        xml_text = self._send_to_grobid(pdf_path, 'processHeaderDocument')
        parsed = self._parse_tei_xml(
            xml_text,
            extract_sections=False,
            extract_references=False
        )

        return parsed

    def parse_references_only(self, pdf_path: str) -> List[Dict]:
        """
        Parse only the references from a PDF

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of reference dictionaries
        """
        logger.info(f"Parsing references only: {pdf_path}")

        xml_text = self._send_to_grobid(pdf_path, 'processReferences')

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            logger.error(f"Failed to parse TEI XML: {e}")
            raise

        return self._extract_references(root)

    def get_statistics(self, parsed_papers: List[ParsedPaper]) -> Dict:
        """
        Get statistics about parsed papers

        Args:
            parsed_papers: List of parsed papers

        Returns:
            Dictionary with statistics
        """
        if not parsed_papers:
            return {'total_papers': 0}

        total_sections = sum(len(p.sections) for p in parsed_papers)
        total_references = sum(len(p.references) for p in parsed_papers)
        total_figures = sum(len(p.figures) for p in parsed_papers)
        total_tables = sum(len(p.tables) for p in parsed_papers)

        # Abstract lengths
        abstract_lengths = [len(p.abstract) for p in parsed_papers if p.abstract]

        return {
            'total_papers': len(parsed_papers),
            'total_sections': total_sections,
            'total_references': total_references,
            'total_figures': total_figures,
            'total_tables': total_tables,
            'avg_sections_per_paper': total_sections / len(parsed_papers),
            'avg_references_per_paper': total_references / len(parsed_papers),
            'avg_abstract_length': sum(abstract_lengths) / len(abstract_lengths) if abstract_lengths else 0,
            'papers_with_abstract': sum(1 for p in parsed_papers if p.abstract),
            'unique_authors': len(set(author for p in parsed_papers for author in p.authors))
        }
