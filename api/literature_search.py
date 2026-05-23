from helpers.api import ApiHandler, Request
import urllib.request
import urllib.parse
import json
import xml.etree.ElementTree as ET
import logging

logger = logging.getLogger("literature_search")


class LiteratureSearch(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        query = (input.get("query", "") or "").strip()
        database = input.get("database", "pubmed").strip()
        max_results = min(int(input.get("max_results", 10) or 10), 50)

        if not query:
            return {"error": "Search query required", "papers": [], "total": 0}

        papers = []
        total = 0

        if database == "pubmed":
            papers, total = await self._search_pubmed(query, max_results)
        elif database == "semantic_scholar":
            papers, total = await self._search_semantic_scholar(query, max_results)
        elif database == "arxiv":
            papers, total = await self._search_arxiv(query, max_results)
        elif database == "google_scholar":
            papers, total = await self._search_google_scholar(query, max_results)
        elif database == "scopus":
            papers, total = await self._search_scopus(query, max_results)
        elif database == "wos":
            papers, total = await self._search_wos(query, max_results)
        elif database == "elsevier":
            papers, total = await self._search_elsevier(query, max_results)
        elif database == "springer":
            papers, total = await self._search_springer(query, max_results)
        elif database == "europe_pmc":
            papers, total = await self._search_europe_pmc(query, max_results)
        elif database == "biorxiv":
            papers, total = await self._search_biorxiv(query, max_results)
        else:
            return {"error": f"Unknown database: {database}", "papers": [], "total": 0}

        return {
            "papers": papers,
            "total": total,
            "query": query,
            "database": database,
        }

    async def _search_pubmed(self, query: str, max_results: int):
        try:
            # ESearch to find IDs
            esearch_url = (
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?"
                f"db=pubmed&retmax={max_results}&retmode=json&sort=relevance&"
                f"term={urllib.parse.quote(query)}"
            )
            req = urllib.request.Request(esearch_url, headers={"User-Agent": "BioDockify/1.0"})
            with urllib.request.urlopen(req, timeout=(15, 30)) as resp:
                data = json.loads(resp.read())
            id_list = data.get("esearchresult", {}).get("idlist", [])
            count = int(data.get("esearchresult", {}).get("count", 0))

            if not id_list:
                return [], 0

            # EFetch for details
            ids = ",".join(id_list)
            efetch_url = (
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?"
                f"db=pubmed&id={ids}&retmode=xml&rettype=abstract"
            )
            req = urllib.request.Request(efetch_url, headers={"User-Agent": "BioDockify/1.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                xml_data = resp.read()

            root = ET.fromstring(xml_data)
            papers = []
            for article in root.findall(".//PubmedArticle"):
                medline = article.find(".//MedlineCitation")
                article_data = medline.find(".//Article") if medline is not None else None
                if article_data is None:
                    continue

                title = self._get_text(article_data.find(".//ArticleTitle"))
                abstract = self._get_text(article_data.find(".//Abstract/AbstractText"))
                pmid = self._get_text(medline.find(".//PMID")) if medline is not None else ""

                # Authors
                authors = []
                author_list = article_data.find(".//AuthorList")
                if author_list is not None:
                    for auth in author_list.findall("Author"):
                        last = self._get_text(auth.find("LastName"))
                        init = self._get_text(auth.find("Initials"))
                        if last:
                            authors.append(f"{last} {init}".strip())

                # Journal
                journal = self._get_text(article_data.find(".//Journal/Title"))
                pub_date = article_data.find(".//Journal/JournalIssue/PubDate")
                year = ""
                if pub_date is not None:
                    year = self._get_text(pub_date.find("Year")) or self._get_text(pub_date.find("MedlineDate"))

                papers.append({
                    "id": pmid,
                    "title": title or "No title",
                    "abstract": (abstract or "")[:800],
                    "authors": authors[:5],
                    "journal": journal or "",
                    "year": year or "",
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
                    "database": "PubMed",
                })

            return papers, count
        except Exception as e:
            logger.warning(f"PubMed search failed for '{query}': {e}")
            return [], 0

    async def _search_semantic_scholar(self, query: str, max_results: int):
        try:
            url = (
                "https://api.semanticscholar.org/graph/v1/paper/search?"
                f"query={urllib.parse.quote(query)}&limit={max_results}"
                "&fields=title,abstract,authors,journal,year,externalIds,url"
            )
            req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/1.0"})
            with urllib.request.urlopen(req, timeout=(15, 30)) as resp:
                data = json.loads(resp.read())

            papers = []
            for p in data.get("data", []):
                papers.append({
                    "id": p.get("paperId", ""),
                    "title": p.get("title", "No title"),
                    "abstract": (p.get("abstract") or "")[:800],
                    "authors": [a.get("name", "") for a in (p.get("authors") or [])][:5],
                    "journal": (p.get("journal") or {}).get("name", ""),
                    "year": str(p.get("year", "")),
                    "url": p.get("url", ""),
                    "database": "Semantic Scholar",
                })
            return papers, data.get("total", 0)
        except Exception as e:
            logger.warning(f"Semantic Scholar search failed for '{query}': {e}")
            return [], 0

    async def _search_arxiv(self, query: str, max_results: int):
        try:
            url = (
                "https://export.arxiv.org/api/query?"
                f"search_query=all:{urllib.parse.quote(query)}&"
                f"start=0&max_results={max_results}&sortBy=relevance"
            )
            req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/1.0"})
            with urllib.request.urlopen(req, timeout=(15, 30)) as resp:
                xml_data = resp.read()

            root = ET.fromstring(xml_data)
            ns = {"atom": "http://www.w3.org/2005/Atom",
                  "arxiv": "http://arxiv.org/schemas/atom"}
            papers = []
            for entry in root.findall("atom:entry", ns):
                title = self._get_text(entry.find("atom:title", ns))
                abstract = self._get_text(entry.find("atom:summary", ns))
                arxiv_id = self._get_text(entry.find("atom:id", ns)).split("/abs/")[-1] if entry.find("atom:id", ns) is not None else ""

                authors = []
                for auth in entry.findall("atom:author", ns):
                    name = self._get_text(auth.find("atom:name", ns))
                    if name:
                        authors.append(name)

                published = self._get_text(entry.find("atom:published", ns))
                year = published[:4] if published else ""

                papers.append({
                    "id": arxiv_id,
                    "title": title or "No title",
                    "abstract": (abstract or "")[:800],
                    "authors": authors[:5],
                    "journal": "arXiv preprint",
                    "year": year,
                    "url": f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else "",
                    "database": "arXiv",
                })
            return papers, len(papers)
        except Exception as e:
            logger.warning(f"arXiv search failed for '{query}': {e}")
            return [], 0

    async def _search_google_scholar(self, query: str, max_results: int):
        """Search via Semantic Scholar with Google-Scholar-like ranking (citation-weighted)."""
        try:
            encoded = urllib.parse.quote(query)
            url = (
                f"https://api.semanticscholar.org/graph/v1/paper/search"
                f"?query={encoded}&limit={max_results}"
                f"&fields=title,abstract,authors,year,url,externalIds,journal,citationCount,publicationTypes"
                f"&sort=citationCount:desc"
            )
            req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
            papers = []
            for d in data.get("data", []):
                authors = [a.get("name", "") for a in d.get("authors", [])[:5]]
                ext = d.get("externalIds", {}) or {}
                paper_id = ext.get("DOI") or d.get("paperId", "")
                papers.append({
                    "id": paper_id,
                    "title": d.get("title", ""),
                    "abstract": (d.get("abstract", "") or "")[:800],
                    "authors": authors,
                    "journal": (d.get("journal", {}) or {}).get("name", "") if d.get("journal") else "",
                    "year": str(d.get("year", "")),
                    "url": d.get("url", ""),
                    "database": "Google Scholar",
                    "citations": d.get("citationCount", 0),
                })
            return papers, len(papers)
        except Exception as e:
            logger.warning(f"Google Scholar search failed for '{query}': {e}")
            return [], 0

    async def _search_scopus(self, query: str, max_results: int):
        """Search via CrossRef, filtered to Scopus-indexed journals from our database."""
        return await self._search_crossref_filtered(query, max_results, "scopus", "Scopus")

    async def _search_wos(self, query: str, max_results: int):
        """Search via CrossRef, filtered to WoS-indexed journals from our database."""
        return await self._search_crossref_filtered(query, max_results, "wos", "Web of Science")

    async def _search_crossref_filtered(self, query: str, max_results: int, index_column: str, label: str):
        """Search CrossRef API, then filter results to only {index_column}-indexed journals."""
        try:
            import sqlite3, os
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "journal-recommender", "assets", "journals.db")
            has_db = os.path.exists(db_path)

            encoded = urllib.parse.quote(query)
            url = (
                f"https://api.crossref.org/works"
                f"?query={encoded}&rows={max_results * 3}"
                f"&filter=type:journal-article"
                f"&select=DOI,title,abstract,author,container-title,issued,URL"
            )
            req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/1.0 (mailto:biodockify@example.com)"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read())

            # Load indexed ISSNs from our journal database
            indexed_issns = set()
            if has_db:
                try:
                    conn = sqlite3.connect(db_path)
                    col = "scopus_indexed" if index_column == "scopus" else "wos_indexed"
                    rows = conn.execute(f"SELECT issn, eissn FROM journals WHERE {col}=1").fetchall()
                    for r in rows:
                        for v in r:
                            if v:
                                indexed_issns.add(str(v).strip().upper())
                    conn.close()
                except Exception:
                    pass

            papers = []
            for item in data.get("message", {}).get("items", []):
                if len(papers) >= max_results:
                    break

                # Check if journal is in our indexed database
                issns = item.get("ISSN", [])
                container_issn = ""
                in_index = not has_db  # If no DB, include all
                for issn_val in (issns if isinstance(issns, list) else [issns]):
                    issn_str = str(issn_val).strip().upper()
                    container_issn = container_issn or issn_str
                    if issn_str in indexed_issns:
                        in_index = True
                        break

                if not in_index:
                    continue

                authors = []
                for a in (item.get("author", []) or [])[:5]:
                    family = a.get("family", "")
                    given = a.get("given", "")
                    authors.append(f"{given} {family}".strip() or family)

                container = item.get("container-title", []) or []
                journal_name = container[0] if container else ""

                issued = item.get("issued", {}) or {}
                date_parts = issued.get("date-parts", [[None]])[0]
                year = str(date_parts[0]) if date_parts and date_parts[0] else ""

                papers.append({
                    "id": item.get("DOI", ""),
                    "title": (item.get("title", [""]) or [""])[0],
                    "abstract": "",  # CrossRef doesn't include abstracts in search results
                    "authors": authors,
                    "journal": journal_name,
                    "year": year,
                    "url": item.get("URL", f"https://doi.org/{item.get('DOI', '')}"),
                    "database": label,
                    "issn": container_issn,
                })

            return papers, len(papers)
        except Exception as e:
            logger.warning(f"{label} search failed for '{query}': {e}")
            return [], 0

    async def _search_elsevier(self, query: str, max_results: int):
        """Search CrossRef filtered to Elsevier/ScienceDirect journals."""
        return await self._search_publisher_filtered(query, max_results, "Elsevier", "ScienceDirect (Elsevier)")

    async def _search_springer(self, query: str, max_results: int):
        """Search CrossRef filtered to Springer Nature journals."""
        return await self._search_publisher_filtered(query, max_results, "Springer", "Springer Nature")

    async def _search_publisher_filtered(self, query: str, max_results: int, publisher_name: str, label: str):
        """Search CrossRef, filter to specific publisher's journals using our ISSN database."""
        try:
            import sqlite3, os
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "journal-recommender", "assets", "journals.db")
            has_db = os.path.exists(db_path)

            encoded = urllib.parse.quote(query)
            url = (
                f"https://api.crossref.org/works"
                f"?query={encoded}&rows={max_results * 3}"
                f"&filter=type:journal-article"
            )
            req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/1.0 (mailto:biodockify@example.com)"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read())

            publisher_issns = set()
            if has_db:
                try:
                    conn = sqlite3.connect(db_path)
                    rows = conn.execute(
                        "SELECT issn, eissn FROM journals WHERE publisher LIKE ?", 
                        (f"%{publisher_name}%",)
                    ).fetchall()
                    for r in rows:
                        for v in r:
                            if v:
                                publisher_issns.add(str(v).strip().upper())
                    conn.close()
                except Exception:
                    pass

            papers = []
            for item in data.get("message", {}).get("items", []):
                if len(papers) >= max_results:
                    break

                issns = item.get("ISSN", [])
                in_publisher = not has_db
                for issn_val in (issns if isinstance(issns, list) else [issns]):
                    if str(issn_val).strip().upper() in publisher_issns:
                        in_publisher = True
                        break
                    # Also check publisher from CrossRef response
                    pub = (item.get("publisher", "") or "").lower()
                    if publisher_name.lower() in pub:
                        in_publisher = True
                        break

                if not in_publisher:
                    continue

                authors = []
                for a in (item.get("author", []) or [])[:5]:
                    authors.append(f"{a.get('given','')} {a.get('family','')}".strip() or a.get('family',''))

                container = item.get("container-title", []) or []
                issued = item.get("issued", {}) or {}
                date_parts = issued.get("date-parts", [[None]])[0]

                papers.append({
                    "id": item.get("DOI", ""),
                    "title": (item.get("title", [""]) or [""])[0],
                    "abstract": "",
                    "authors": authors,
                    "journal": container[0] if container else "",
                    "year": str(date_parts[0]) if date_parts and date_parts[0] else "",
                    "url": item.get("URL", f"https://doi.org/{item.get('DOI','')}"),
                    "database": label,
                })

            return papers, len(papers)
        except Exception as e:
            logger.warning(f"{label} search failed for '{query}': {e}")
            return [], 0

    async def _search_europe_pmc(self, query: str, max_results: int):
        """Search Europe PMC — free biomedical literature database."""
        try:
            encoded = urllib.parse.quote(query)
            url = (
                f"https://www.ebi.ac.uk/europepmc/webservices/rest/search"
                f"?query={encoded}&resultType=lite&pageSize={max_results}"
                f"&format=json&sort=RELEVANCE"
            )
            req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())

            papers = []
            for r in data.get("resultList", {}).get("result", []):
                authors = (r.get("authorString", "") or "").split(", ")[:5]
                papers.append({
                    "id": r.get("id", ""),
                    "title": r.get("title", ""),
                    "abstract": (r.get("abstractText", "") or "")[:800],
                    "authors": authors,
                    "journal": r.get("journalTitle", ""),
                    "year": str(r.get("pubYear", "")),
                    "url": f"https://europepmc.org/article/{r.get('source','')}/{r.get('id','')}",
                    "database": "Europe PMC",
                })

            return papers, len(papers)
        except Exception as e:
            logger.warning(f"Europe PMC search failed for '{query}': {e}")
            return [], 0

    async def _search_biorxiv(self, query: str, max_results: int):
        """Search bioRxiv + medRxiv preprints via Europe PMC."""
        try:
            encoded = urllib.parse.quote(query)
            url = (
                f"https://www.ebi.ac.uk/europepmc/webservices/rest/search"
                f"?query={encoded}%20AND%20(SRC:PPR%20OR%20SRC:MED)"
                f"&resultType=lite&pageSize={max_results}"
                f"&format=json&sort=RELEVANCE"
            )
            req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())

            papers = []
            for r in data.get("resultList", {}).get("result", []):
                authors = (r.get("authorString", "") or "").split(", ")[:5]
                papers.append({
                    "id": r.get("id", ""),
                    "title": r.get("title", ""),
                    "abstract": (r.get("abstractText", "") or "")[:800],
                    "authors": authors,
                    "journal": r.get("bookOrReportDetails", {}).get("publisher", "bioRxiv") if isinstance(r.get("bookOrReportDetails"), dict) else "bioRxiv",
                    "year": str(r.get("pubYear", "")),
                    "url": f"https://europepmc.org/article/PPR/{r.get('id','')}",
                    "database": "bioRxiv/medRxiv",
                })

            return papers, len(papers)
        except Exception as e:
            logger.warning(f"bioRxiv search failed for '{query}': {e}")
            return [], 0

    def _get_text(self, element):
        if element is None:
            return ""
        return element.text or "".join(element.itertext()) if hasattr(element, 'itertext') else str(element) or ""
