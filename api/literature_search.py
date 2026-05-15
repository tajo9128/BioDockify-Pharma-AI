from helpers.api import ApiHandler, Request
import urllib.request
import urllib.parse
import json
import xml.etree.ElementTree as ET


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
            with urllib.request.urlopen(req, timeout=15) as resp:
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
            return [], 0

    async def _search_semantic_scholar(self, query: str, max_results: int):
        try:
            url = (
                "https://api.semanticscholar.org/graph/v1/paper/search?"
                f"query={urllib.parse.quote(query)}&limit={max_results}"
                "&fields=title,abstract,authors,journal,year,externalIds,url"
            )
            req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
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
        except Exception:
            return [], 0

    async def _search_arxiv(self, query: str, max_results: int):
        try:
            url = (
                "http://export.arxiv.org/api/query?"
                f"search_query=all:{urllib.parse.quote(query)}&"
                f"start=0&max_results={max_results}&sortBy=relevance"
            )
            req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
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
        except Exception:
            return [], 0

    def _get_text(self, element):
        if element is None:
            return ""
        return element.text or "".join(element.itertext()) if hasattr(element, 'itertext') else str(element) or ""
