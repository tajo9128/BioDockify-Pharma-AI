"""
BibTeX Reference Management

This module provides comprehensive BibTeX reference management for academic writing,
including:
- Fetch references from PubMed by PMID
- Fetch references from DOI (CrossRef)
- Manual BibTeX entry creation
- BibTeX file export
- Citation formatting in multiple styles (APA, IEEE, Nature, MLA, Chicago)
- Reference validation
- Duplicate detection and merging

Export Pipeline:
Research Data → PubMed/DOI API → BibTeX Entries → Formatting → Bibliography Output
"""

import requests
from typing import Dict, List, Optional, Union, Set
from pathlib import Path
import logging
import re
from dataclasses import dataclass, asdict
from datetime import datetime


try:
    import bibtexparser
    from bibtexparser.bwriter import BibTexWriter
    from bibtexparser.bibdatabase import BibDatabase
    BIBTEXPARSER_AVAILABLE = True
except ImportError:
    BIBTEXPARSER_AVAILABLE = False
    bibtexparser = None
    logging.warning("bibtexparser not available. Install with: pip install bibtexparser")


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class BibEntry:
    """Data class for BibTeX entry"""
    ID: str
    ENTRYTYPE: str
    title: str
    author: str
    year: str
    journal: Optional[str] = None
    volume: Optional[str] = None
    number: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None
    publisher: Optional[str] = None
    abstract: Optional[str] = None
    keywords: Optional[str] = None
    url: Optional[str] = None
    note: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {k: v for k, v in asdict(self).items() if v is not None}


class BibTeXManager:
    """
    BibTeX reference manager

    Features:
    - Fetch from PubMed by PMID
    - Fetch from DOI using CrossRef
    - Manual entry creation
    - BibTeX file export
    - Multiple citation styles (APA, IEEE, Nature, MLA, Chicago)
    - Reference validation
    - Duplicate detection
    - Entry merging
    - Batch operations

    Supported Citation Styles:
    - APA: American Psychological Association
    - IEEE: Institute of Electrical and Electronics Engineers
    - Nature: Nature journal style
    - MLA: Modern Language Association
    - Chicago: Chicago Manual of Style
    """

    # Required fields by entry type
    REQUIRED_FIELDS = {
        'article': ['ID', 'ENTRYTYPE', 'title', 'author', 'journal', 'year'],
        'book': ['ID', 'ENTRYTYPE', 'title', 'author', 'publisher', 'year'],
        'inproceedings': ['ID', 'ENTRYTYPE', 'title', 'author', 'booktitle', 'year'],
        'techreport': ['ID', 'ENTRYTYPE', 'title', 'author', 'institution', 'year']
    }

    def __init__(self, entries: Optional[List[Dict]] = None):
        """
        Initialize BibTeX manager

        Args:
            entries: Optional list of existing BibTeX entries
        """
        if not BIBTEXPARSER_AVAILABLE:
            raise ImportError(
                "bibtexparser is required. Install with: pip install bibtexparser"
            )

        self.entries = entries or []
        logger.info(f"BibTeX manager initialized with {len(self.entries)} entries")

    def add_from_pubmed(
        self,
        pmid: str,
        fetch_abstract: bool = False
    ) -> Dict:
        """
        Fetch citation from PubMed ID

        Uses NCBI E-utilities API to fetch article metadata

        Args:
            pmid: PubMed ID
            fetch_abstract: Whether to fetch abstract

        Returns:
            BibTeX entry dictionary

        Raises:
            Exception: If PubMed API request fails
        """
        logger.info(f"Fetching from PubMed: PMID {pmid}")

        # Build API URL
        base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        params = {
            'db': 'pubmed',
            'id': pmid,
            'retmode': 'xml'
        }

        try:
            response = requests.get(base_url, params=params, timeout=10)

            if response.status_code != 200:
                raise Exception(
                    f"PubMed API error: HTTP {response.status_code}"
                )

            # Parse XML and convert to BibTeX
            entry = self._parse_pubmed_xml(
                response.text,
                pmid,
                fetch_abstract=fetch_abstract
            )

            # Check for duplicates
            if not self._is_duplicate(entry):
                self.entries.append(entry)
                logger.info(f"Added PubMed entry: {entry.get('title', 'Unknown')}")
            else:
                logger.warning(f"Duplicate entry detected for PMID {pmid}")

            return entry

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching PubMed: {e}")
            raise Exception(f"PubMed API request failed: {str(e)}")

    def add_from_doi(self, doi: str) -> Dict:
        """
        Fetch citation from DOI

        Uses CrossRef API to fetch publication metadata

        Args:
            doi: Digital Object Identifier

        Returns:
            BibTeX entry dictionary

        Raises:
            Exception: If CrossRef API request fails
        """
        logger.info(f"Fetching from DOI: {doi}")

        # Build API URL
        url = f"https://api.crossref.org/works/{doi}"
        headers = {
            'Accept': 'application/x-bibtex',
            'User-Agent': 'BioDockify/1.0 (mailto:example@email.com)'
        }

        try:
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code != 200:
                raise Exception(
                    f"CrossRef API error: HTTP {response.status_code}"
                )

            # Parse BibTeX response
            bib_database = bibtexparser.loads(response.text)

            if not bib_database.entries:
                raise Exception("No BibTeX entry found in response")

            entry = bib_database.entries[0]

            # Add DOI to entry
            entry['doi'] = doi

            # Check for duplicates
            if not self._is_duplicate(entry):
                self.entries.append(entry)
                logger.info(f"Added DOI entry: {entry.get('title', 'Unknown')}")
            else:
                logger.warning(f"Duplicate entry detected for DOI {doi}")

            return entry

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching DOI: {e}")
            raise Exception(f"CrossRef API request failed: {str(e)}")

    def add_manual(self, entry: Union[Dict, BibEntry]) -> Dict:
        """
        Add manual BibTeX entry

        Args:
            entry: BibTeX entry as dictionary or BibEntry object

        Returns:
            Added entry dictionary

        Raises:
            ValueError: If required fields are missing
        """
        if isinstance(entry, BibEntry):
            entry_dict = entry.to_dict()
        else:
            entry_dict = entry

        # Validate entry
        self._validate_entry(entry_dict)

        # Check for duplicates
        if self._is_duplicate(entry_dict):
            logger.warning(f"Duplicate entry detected: {entry_dict.get('ID', 'Unknown')}")
        else:
            self.entries.append(entry_dict)
            logger.info(f"Added manual entry: {entry_dict.get('title', 'Unknown')}")

        return entry_dict

    def add_batch_from_pubmed(
        self,
        pmids: List[str],
        fetch_abstract: bool = False
    ) -> List[Dict]:
        """
        Batch fetch from PubMed

        Args:
            pmids: List of PubMed IDs
            fetch_abstract: Whether to fetch abstracts

        Returns:
            List of added entries
        """
        logger.info(f"Fetching {len(pmids)} entries from PubMed")

        added_entries = []
        for pmid in pmids:
            try:
                entry = self.add_from_pubmed(pmid, fetch_abstract=fetch_abstract)
                added_entries.append(entry)
            except Exception as e:
                logger.error(f"Failed to fetch PMID {pmid}: {e}")

        logger.info(f"Successfully added {len(added_entries)}/{len(pmids)} entries")
        return added_entries

    def add_batch_from_doi(self, dois: List[str]) -> List[Dict]:
        """
        Batch fetch from DOI

        Args:
            dois: List of DOIs

        Returns:
            List of added entries
        """
        logger.info(f"Fetching {len(dois)} entries from DOI")

        added_entries = []
        for doi in dois:
            try:
                entry = self.add_from_doi(doi)
                added_entries.append(entry)
            except Exception as e:
                logger.error(f"Failed to fetch DOI {doi}: {e}")

        logger.info(f"Successfully added {len(added_entries)}/{len(dois)} entries")
        return added_entries

    def export(self, filepath: str, encoding: str = 'utf-8') -> str:
        """
        Export entries to .bib file

        Args:
            filepath: Path to output .bib file
            encoding: File encoding

        Returns:
            Path to exported file
        """
        # Create BibDatabase
        db = BibDatabase()
        db.entries = self.entries

        # Write to file
        writer = BibTexWriter()

        output_path = Path(filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding=encoding) as bibfile:
            bibfile.write(writer.write(db))

        logger.info(f"Exported {len(self.entries)} entries to {filepath}")
        return str(output_path)

    def export_markdown(self, filepath: str) -> str:
        """
        Export references as Markdown

        Args:
            filepath: Path to output .md file

        Returns:
            Path to exported file
        """
        output_path = Path(filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# References\n\n")

            for i, entry in enumerate(self.entries, 1):
                citation = self.format_citation(
                    entry.get('ID', ''),
                    style='apa'
                )
                f.write(f"{i}. {citation}\n\n")

        logger.info(f"Exported {len(self.entries)} references to {filepath}")
        return str(output_path)

    def format_citation(
        self,
        entry_id: str,
        style: str = 'apa',
        in_text: bool = False
    ) -> str:
        """
        Format citation in specified style

        Args:
            entry_id: BibTeX entry ID
            style: Citation style ('apa', 'ieee', 'nature', 'mla', 'chicago')
            in_text: Whether to format as in-text citation

        Returns:
            Formatted citation string
        """
        entry = next((e for e in self.entries if e.get('ID') == entry_id), None)

        if not entry:
            logger.warning(f"Entry not found: {entry_id}")
            return ''

        # Format based on style
        if style.lower() == 'apa':
            return self._format_apa(entry, in_text)
        elif style.lower() == 'ieee':
            return self._format_ieee(entry, in_text)
        elif style.lower() == 'nature':
            return self._format_nature(entry, in_text)
        elif style.lower() == 'mla':
            return self._format_mla(entry, in_text)
        elif style.lower() == 'chicago':
            return self._format_chicago(entry, in_text)
        else:
            logger.warning(f"Unknown citation style: {style}")
            return self._format_apa(entry, in_text)

    def format_all_citations(self, style: str = 'apa') -> List[str]:
        """
        Format all citations

        Args:
            style: Citation style

        Returns:
            List of formatted citations
        """
        citations = []

        for entry in self.entries:
            entry_id = entry.get('ID', '')
            citation = self.format_citation(entry_id, style)
            if citation:
                citations.append(citation)

        return citations

    def find_duplicates(self) -> Dict[str, List[Dict]]:
        """
        Find potential duplicate entries

        Returns:
            Dictionary with duplicate groups
        """
        duplicates = {}
        seen_titles = {}

        for entry in self.entries:
            title = entry.get('title', '').lower().strip()
            title_key = re.sub(r'[^\w\s]', '', title)

            if title_key in seen_titles:
                # Found duplicate
                original_id = seen_titles[title_key]

                if original_id not in duplicates:
                    duplicates[original_id] = [self._get_entry_by_id(original_id)]

                duplicates[original_id].append(entry)
            else:
                seen_titles[title_key] = entry.get('ID', '')

        return duplicates

    def merge_duplicates(self, keep_newest: bool = True) -> int:
        """
        Merge duplicate entries

        Args:
            keep_newest: Whether to keep the newest entry

        Returns:
            Number of merged entries
        """
        duplicates = self.find_duplicates()
        merged_count = 0

        for original_id, duplicate_entries in duplicates.items():
            if len(duplicate_entries) > 1:
                # Determine which to keep
                if keep_newest:
                    # Keep entry with latest year
                    sorted_entries = sorted(
                        duplicate_entries,
                        key=lambda x: x.get('year', '0'),
                        reverse=True
                    )
                    keep_entry = sorted_entries[0]
                    remove_entries = sorted_entries[1:]
                else:
                    keep_entry = duplicate_entries[0]
                    remove_entries = duplicate_entries[1:]

                # Remove duplicates
                for entry in remove_entries:
                    if entry in self.entries:
                        self.entries.remove(entry)
                        merged_count += 1

        logger.info(f"Merged {merged_count} duplicate entries")
        return merged_count

    def _parse_pubmed_xml(
        self,
        xml_text: str,
        pmid: str,
        fetch_abstract: bool = False
    ) -> Dict:
        """Convert PubMed XML to BibTeX entry"""
        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            logger.error(f"Failed to parse PubMed XML: {e}")
            raise

        # Find article
        article = root.find('.//Article')

        if article is None:
            raise Exception("Article not found in PubMed XML")

        # Extract title
        title_elem = article.find('.//ArticleTitle')
        title = title_elem.text if title_elem is not None else ''

        # Extract authors
        authors = []
        for author_elem in article.findall('.//Author'):
            last_name = author_elem.find('LastName')
            first_name = author_elem.find('ForeName')
            initials = author_elem.find('Initials')

            if last_name is not None:
                if first_name is not None:
                    author_str = f"{last_name.text}, {first_name.text}"
                elif initials is not None:
                    author_str = f"{last_name.text}, {initials.text}"
                else:
                    author_str = last_name.text
                authors.append(author_str)

        # Extract year
        year_elem = article.find('.//PubDate/Year')
        year = year_elem.text if year_elem is not None else 'n.d.'

        # Extract journal
        journal_elem = article.find('.//Journal/Title')
        journal = journal_elem.text if journal_elem is not None else ''

        # Extract abstract
        abstract_text = ''
        if fetch_abstract:
            abstract_elem = article.find('.//Abstract/AbstractText')
            if abstract_elem is not None:
                abstract_text = abstract_elem.text or ''

        # Extract DOI
        doi = ''
        article_ids = root.find('.//ArticleIdList')
        if article_ids is not None:
            for aid in article_ids.findall('.//ArticleId'):
                if aid.get('IdType') == 'doi':
                    doi = aid.text
                    break

        # Create entry
        entry = {
            'ID': f'pmid{pmid}',
            'ENTRYTYPE': 'article',
            'title': title,
            'author': ' and '.join(authors),
            'year': year,
            'journal': journal,
            'pmid': pmid
        }

        if abstract_text:
            entry['abstract'] = abstract_text

        if doi:
            entry['doi'] = doi

        return entry

    def _format_apa(self, entry: Dict, in_text: bool = False) -> str:
        """Format in APA style"""
        authors = entry.get('author', '')
        year = entry.get('year', '')
        title = entry.get('title', '')
        journal = entry.get('journal', '')
        volume = entry.get('volume', '')
        number = entry.get('number', '')
        pages = entry.get('pages', '')
        doi = entry.get('doi', '')

        if in_text:
            # In-text citation: (Author, Year)
            first_author = authors.split(' and ')[0]
            return f"({first_author.split(',')[0]}, {year})"

        # Full citation
        citation = f"{authors} ({year}). {title}. {journal}"

        if volume:
            citation += f", {volume}"

        if number:
            citation += f"({number})"

        if pages:
            citation += f", {pages}"

        if doi:
            citation += f". https://doi.org/{doi}"

        return citation

    def _format_ieee(self, entry: Dict, in_text: bool = False) -> str:
        """Format in IEEE style"""
        authors = entry.get('author', '')
        year = entry.get('year', '')
        title = entry.get('title', '')
        journal = entry.get('journal', '')
        volume = entry.get('volume', '')
        number = entry.get('number', '')
        pages = entry.get('pages', '')

        if in_text:
            # In-text citation: [1] or [2,3]
            idx = self.entries.index(entry) + 1
            return f"[{idx}]"

        # Full citation
        citation = f"{authors}, \"{title},\" {journal}"

        if volume and number:
            citation += f", vol. {volume}, no. {number}"
        elif volume:
            citation += f", vol. {volume}"

        if pages:
            citation += f", pp. {pages}"

        citation += f", {year}."

        return citation

    def _format_nature(self, entry: Dict, in_text: bool = False) -> str:
        """Format in Nature style"""
        authors = entry.get('author', '')
        year = entry.get('year', '')
        title = entry.get('title', '')
        journal = entry.get('journal', '')
        volume = entry.get('volume', '')
        pages = entry.get('pages', '')

        if in_text:
            # In-text citation: (Author et al., Year)
            first_author = authors.split(' and ')[0].split(',')[0]
            return f"({first_author} et al., {year})"

        # Full citation
        citation = f"{authors} {title}. {journal}"

        if volume:
            citation += f" {volume}"

        if pages:
            citation += f", {pages}"

        citation += f" ({year})"

        return citation

    def _format_mla(self, entry: Dict, in_text: bool = False) -> str:
        """Format in MLA style"""
        authors = entry.get('author', '')
        year = entry.get('year', '')
        title = entry.get('title', '')
        journal = entry.get('journal', '')
        volume = entry.get('volume', '')
        number = entry.get('number', '')
        pages = entry.get('pages', '')

        if in_text:
            # In-text citation: (Author Page)
            first_author = authors.split(' and ')[0].split(',')[0]
            return f"({first_author} {pages})"

        # Full citation
        citation = f"{authors}. \"{title}.\" {journal}"

        if volume and number:
            citation += f", vol. {volume}, no. {number}"
        elif volume:
            citation += f", vol. {volume}"

        citation += f", {year}"

        if pages:
            citation += f", pp. {pages}"

        return citation

    def _format_chicago(self, entry: Dict, in_text: bool = False) -> str:
        """Format in Chicago style"""
        authors = entry.get('author', '')
        year = entry.get('year', '')
        title = entry.get('title', '')
        journal = entry.get('journal', '')
        volume = entry.get('volume', '')
        number = entry.get('number', '')
        pages = entry.get('pages', '')

        if in_text:
            # In-text citation: (Author Year)
            first_author = authors.split(' and ')[0].split(',')[0]
            return f"({first_author} {year})"

        # Full citation
        citation = f"{authors}. {year}. \"{title}.\" {journal}"

        if volume:
            citation += f" {volume}"

        if number:
            citation += f", no. {number}"

        if pages:
            citation += f": {pages}"

        citation += "."

        return citation

    def _validate_entry(self, entry: Dict) -> bool:
        """Validate BibTeX entry has required fields"""
        entry_type = entry.get('ENTRYTYPE', 'article')
        required = self.REQUIRED_FIELDS.get(entry_type, [])

        missing = [field for field in required if field not in entry]

        if missing:
            raise ValueError(
                f"Missing required fields for {entry_type}: {missing}"
            )

        return True

    def _is_duplicate(self, entry: Dict) -> bool:
        """Check if entry is duplicate"""
        title = entry.get('title', '').lower().strip()
        title_key = re.sub(r'[^\w\s]', '', title)

        for existing in self.entries:
            existing_title = existing.get('title', '').lower().strip()
            existing_key = re.sub(r'[^\w\s]', '', existing_title)

            if title_key == existing_key:
                return True

        return False

    def _get_entry_by_id(self, entry_id: str) -> Optional[Dict]:
        """Get entry by ID"""
        for entry in self.entries:
            if entry.get('ID') == entry_id:
                return entry
        return None

    def search(
        self,
        query: str,
        fields: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Search entries by query

        Args:
            query: Search query string
            fields: Fields to search (default: all)

        Returns:
            List of matching entries
        """
        if fields is None:
            fields = ['title', 'author', 'journal', 'abstract']

        query_lower = query.lower()
        results = []

        for entry in self.entries:
            for field in fields:
                field_value = entry.get(field, '')

                if field_value and query_lower in field_value.lower():
                    results.append(entry)
                    break

        logger.info(f"Found {len(results)} entries matching '{query}'")
        return results

    def get_statistics(self) -> Dict:
        """Get bibliography statistics"""
        total = len(self.entries)

        # Count by entry type
        types = {}
        for entry in self.entries:
            entry_type = entry.get('ENTRYTYPE', 'unknown')
            types[entry_type] = types.get(entry_type, 0) + 1

        # Count by year
        years = {}
        for entry in self.entries:
            year = entry.get('year', 'unknown')
            years[year] = years.get(year, 0) + 1

        return {
            'total_entries': total,
            'entry_types': types,
            'years': years
        }

    def load_from_file(self, filepath: str) -> int:
        """
        Load entries from existing .bib file

        Args:
            filepath: Path to .bib file

        Returns:
            Number of loaded entries
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            bib_database = bibtexparser.load(f)

        loaded_count = 0
        for entry in bib_database.entries:
            if not self._is_duplicate(entry):
                self.entries.append(entry)
                loaded_count += 1

        logger.info(f"Loaded {loaded_count} entries from {filepath}")
        return loaded_count


if __name__ == '__main__':
    # Example usage
    bib_manager = BibTeXManager()

    # Add manual entry
    manual_entry = {
        'ID': 'smith2023',
        'ENTRYTYPE': 'article',
        'title': 'A Novel Approach to Drug Discovery',
        'author': 'Smith, J. and Doe, A.',
        'year': '2023',
        'journal': 'Journal of Pharmacology',
        'volume': '45',
        'number': '2',
        'pages': '123-145'
    }
    bib_manager.add_manual(manual_entry)

    # Format citations
    apa_citation = bib_manager.format_citation('smith2023', style='apa')
    print(f"APA: {apa_citation}")

    ieee_citation = bib_manager.format_citation('smith2023', style='ieee')
    print(f"IEEE: {ieee_citation}")

    # Export
    bib_manager.export('references.bib')
    bib_manager.export_markdown('references.md')
