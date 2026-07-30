from helpers.api import ApiHandler, Request
import asyncio, urllib.request
import urllib.parse
import json
import xml.etree.ElementTree as ET
import logging

logger = logging.getLogger("literature_search")


async def _async_urlopen(req, timeout=30):
    """Non-blocking urlopen with proper resource cleanup."""
    def _fetch():
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    return await asyncio.to_thread(_fetch)


class LiteratureSearch(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        query = (input.get("query", "") or "").strip()
        database = input.get("database", "pubmed").strip().lower().replace(" ", "_")
        # Normalize common aliases
        DB_ALIASES = {
            "europepmc": "europe_pmc",
            "europe-pmc": "europe_pmc",
            "semantic-scholar": "semantic_scholar",
            "semanticscholar": "semantic_scholar",
            "s2": "semantic_scholar",
            "google-scholar": "google_scholar",
            "googlescholar": "google_scholar",
        }
        database = DB_ALIASES.get(database, database)
        max_results = min(int(input.get("max_results", 100) or 100), 200)
        store_to_kb = input.get("store_to_kb", False)

        # ── BATCH SEARCH: all 10 databases in parallel ──
        if database == "all" or database == "batch":
            return await self._batch_search(query, max_results, store_to_kb)

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

        # ── Fetch full text for every paper ──
        full_text_count = 0
        try:
            from modules.literature.full_text import FullTextRetriever
            retriever = FullTextRetriever()
            for paper in papers:
                if not paper.get("title"):
                    continue
                try:
                    ft = retriever.retrieve(paper)
                    if ft and len(ft) > 200:
                        paper["full_text"] = ft
                        paper["full_text_available"] = True
                        full_text_count += 1
                    else:
                        paper["full_text_available"] = False
                except Exception:
                    paper["full_text_available"] = False
        except ImportError:
            logger.warning("FullTextRetriever not available — storing abstracts only")
        except Exception as e:
            logger.warning(f"Full text fetch error: {e}")

        # Store to knowledge base — ONLY full-text articles (no metadata-only entries)
        # The user requirement: "metadata and other literature details must NOT save
        # at knowledge base — only full article must save."
        # So we skip any paper where full_text is empty/short — abstracts and
        # metadata-only entries clutter the KB and can't be cited in theses.
        kb_stored = 0
        kb_skipped = 0
        if store_to_kb and papers:
            try:
                from modules.knowledge.auto_store import auto_store
                for paper in papers[:50]:
                    title = paper.get("title", "Untitled")
                    authors = ", ".join(paper.get("authors", [])[:5])
                    full_text = paper.get("full_text", "")

                    # SKIP if no full text (only metadata/abstract available)
                    if not full_text or len(full_text) < 2000:
                        kb_skipped += 1
                        continue

                    content = f"**Authors:** {authors}\n**Year:** {paper.get('year', '')}\n**Journal:** {paper.get('journal', '')}\n**Database:** {database}\n**DOI:** {paper.get('doi', '')}\n**PMID:** {paper.get('pmid', '')}\n**URL:** {paper.get('url', '')}\n\n## Full Text\n\n{full_text}"

                    auto_store(
                        module_name="literature_search",
                        title=title,
                        content=content,
                        source=f"Literature Search: {database}",
                        tags=["literature", database, query[:30]],
                        metadata={"doi": paper.get("doi", ""), "pmid": paper.get("pmid", ""), "full_text": True},
                        category="literature",
                    )
                    kb_stored += 1
            except Exception as e:
                logger.warning(f"KB store failed: {e}")

        return {
            "papers": papers,
            "total": total,
            "query": query,
            "database": database,
            "kb_stored": kb_stored,
            "kb_skipped": kb_skipped,
            "full_text_fetched": full_text_count,
        }

    async def _batch_search(self, query: str, max_per_db: int, store_to_kb: bool) -> dict:
        """Search ALL 10 databases in parallel. Maximum coverage for first impression.

        Returns aggregate stats: total found, full text retrieved, KB stored.
        De-duplicates by DOI/PMID to avoid double-counting.
        """
        import asyncio

        ALL_DATABASES = [
            "europe_pmc", "pubmed", "semantic_scholar", "biorxiv", "arxiv",
            "google_scholar", "scopus", "wos", "elsevier", "springer",
        ]

        async def _safe_search(db_name):
            """Search one DB, return (db_name, papers, error). Never raises."""
            try:
                if db_name == "pubmed":
                    papers, _ = await self._search_pubmed(query, max_per_db)
                elif db_name == "semantic_scholar":
                    papers, _ = await self._search_semantic_scholar(query, max_per_db)
                elif db_name == "arxiv":
                    papers, _ = await self._search_arxiv(query, max_per_db)
                elif db_name == "google_scholar":
                    papers, _ = await self._search_google_scholar(query, max_per_db)
                elif db_name == "scopus":
                    papers, _ = await self._search_scopus(query, max_per_db)
                elif db_name == "wos":
                    papers, _ = await self._search_wos(query, max_per_db)
                elif db_name == "elsevier":
                    papers, _ = await self._search_elsevier(query, max_per_db)
                elif db_name == "springer":
                    papers, _ = await self._search_springer(query, max_per_db)
                elif db_name == "europe_pmc":
                    papers, _ = await self._search_europe_pmc(query, max_per_db)
                elif db_name == "biorxiv":
                    papers, _ = await self._search_biorxiv(query, max_per_db)
                else:
                    papers = []
                return (db_name, papers, None)
            except Exception as e:
                logger.warning(f"Batch search failed for {db_name}: {e}")
                return (db_name, [], str(e))

        # Run all 10 searches in parallel
        logger.info(f"[Batch Search] Starting parallel search across {len(ALL_DATABASES)} databases for: {query}")
        results = await asyncio.gather(*[_safe_search(db) for db in ALL_DATABASES])

        # Aggregate + de-duplicate
        all_papers = []
        seen_dois = set()
        seen_pmids = set()
        db_stats = {}
        for db_name, papers, err in results:
            db_papers_added = 0
            for p in papers:
                doi = (p.get("doi") or "").lower().strip()
                pmid = (p.get("pmid") or "").strip()
                # Dedupe by DOI first, then PMID
                if doi and doi in seen_dois:
                    continue
                if not doi and pmid and pmid in seen_pmids:
                    continue
                if doi:
                    seen_dois.add(doi)
                if pmid:
                    seen_pmids.add(pmid)
                p["source_database"] = db_name
                all_papers.append(p)
                db_papers_added += 1
            db_stats[db_name] = {"found": len(papers), "added": db_papers_added, "error": err}

        logger.info(f"[Batch Search] {len(all_papers)} unique papers from {len(ALL_DATABASES)} databases")

        # Fetch full text for all unique papers
        full_text_count = 0
        kb_stored = 0
        kb_skipped = 0

        if store_to_kb and all_papers:
            from modules.literature.full_text import FullTextRetriever
            from modules.knowledge.auto_store import auto_store
            retriever = FullTextRetriever()

            for paper in all_papers:
                try:
                    full_text = await retriever.retrieve_async(paper) if hasattr(retriever, "retrieve_async") else retriever.retrieve(paper)
                    if full_text and len(full_text) > 2000:
                        full_text_count += 1
                        try:
                            auto_store(
                                module_name="literature_search",
                                title=paper.get("title", "Untitled"),
                                content=f"**Authors:** {', '.join(paper.get('authors', [])[:5])}\n**Source:** {paper.get('source_database', 'unknown')}\n**DOI:** {paper.get('doi', 'N/A')}\n\n## Full Text\n\n{full_text}",
                                source=paper.get("source_database", "Literature Search"),
                                tags=["literature", "full_text", paper.get("source_database", "")],
                                category="literature",
                            )
                            kb_stored += 1
                        except Exception as e:
                            logger.warning(f"KB store failed for '{paper.get('title','?')[:40]}': {e}")
                            kb_skipped += 1
                    else:
                        kb_skipped += 1
                except Exception as e:
                    logger.warning(f"Full text failed for '{paper.get('title','?')[:40]}': {e}")
                    kb_skipped += 1

        return {
            "status": "ok",
            "query": query,
            "database": "all",
            "databases_searched": len(ALL_DATABASES),
            "papers_found": len(all_papers),
            "full_text_retrieved": full_text_count,
            "kb_stored": kb_stored,
            "kb_skipped": kb_skipped,
            "db_stats": db_stats,
            "message": f"Searched {len(ALL_DATABASES)} databases: found {len(all_papers)} unique papers, {full_text_count} full-text retrieved, {kb_stored} stored to KB.",
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
            raw = await _async_urlopen(req, timeout=30)
            data = json.loads(raw)
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
            raw = await _async_urlopen(req, timeout=30)
            xml_data = raw

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

                doi_val = self._get_text(article_data.find(".//ELocationID[@EIdType='doi']"))

                # Extract PMCID from ArticleIdList (NCBI EFetch format)
                pmcid = ""
                aid_list = article_data.find(".//ArticleIdList")
                if aid_list is not None:
                    for aid in aid_list.findall("ArticleId"):
                        if aid.attrib.get("IdType") == "pmc":
                            pmcid = (aid.text or "").strip()
                            break

                papers.append({
                    "id": pmid,
                    "pmid": pmid,
                    "pmcid": pmcid,
                    "doi": doi_val or "",
                    "title": title or "No title",
                    "abstract": abstract or "",
                    "authors": authors[:5],
                    "journal": journal or "",
                    "year": year or "",
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
                    "database": "PubMed",
                })

            # Resolve PMCIDs for papers that don't have them via Europe PMC
            if papers:
                try:
                    self._resolve_pmcids_via_europe_pmc(papers)
                except Exception as e:
                    logger.debug(f"PMCID batch resolve skipped: {e}")

            return papers, count
        except Exception as e:
            logger.warning(f"PubMed search failed for '{query}': {e}")
            return [], 0

    async def _search_semantic_scholar(self, query: str, max_results: int):
        try:
            url = (
                "https://api.semanticscholar.org/graph/v1/paper/search?"
                f"query={urllib.parse.quote(query)}&limit={max_results}"
                "&fields=title,abstract,authors,journal,year,externalIds,url,openAccessPdf"
            )
            req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/1.0"})
            raw = await _async_urlopen(req, timeout=30)
            data = json.loads(raw)

            papers = []
            for p in data.get("data", []):
                # Extract openAccessPdf URL if available (unblocks Tier-3b full text)
                open_access_pdf = ""
                oap = p.get("openAccessPdf")
                if isinstance(oap, dict):
                    open_access_pdf = oap.get("url", "")
                elif isinstance(oap, str):
                    open_access_pdf = oap

                papers.append({
                    "id": p.get("paperId", ""),
                    "title": p.get("title", "No title"),
                    "abstract": (p.get("abstract") or "")[:800],
                    "authors": [a.get("name", "") for a in (p.get("authors") or [])][:5],
                    "journal": (p.get("journal") or {}).get("name", ""),
                    "year": str(p.get("year", "")),
                    "url": p.get("url", ""),
                    "openAccessPdf": open_access_pdf,
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
            raw = await _async_urlopen(req, timeout=30)
            xml_data = raw

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
                    "abstract": abstract or "",
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
            raw = await _async_urlopen(req, timeout=15)
            data = json.loads(raw)
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
        """Search Crossref directly for Scopus-relevant journals."""
        return await self._search_crossref_unfiltered(query, max_results, "Scopus")

    async def _search_wos(self, query: str, max_results: int):
        """Search Crossref directly for WoS-relevant journals."""
        return await self._search_crossref_unfiltered(query, max_results, "Web of Science")

    async def _search_crossref_unfiltered(self, query: str, max_results: int, label: str):
        """Search CrossRef API directly without ISSN filtering."""
        try:
            encoded = urllib.parse.quote(query)
            url = (
                f"https://api.crossref.org/works"
                f"?query={encoded}&rows={max_results}"
                f"&filter=type:journal-article"
                f"&select=DOI,title,abstract,author,container-title,issued,URL,ISSN"
            )
            req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/7.0 (mailto:biodockify@example.com)"})
            raw = await _async_urlopen(req, timeout=20)
            data = json.loads(raw)

            papers = []
            for item in data.get("message", {}).get("items", [])[:max_results]:
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

                abstract = ""
                if item.get("abstract"):
                    abstract = item["abstract"][:500]

                papers.append({
                    "id": item.get("DOI", ""),
                    "title": (item.get("title", [""]) or [""])[0],
                    "abstract": abstract,
                    "authors": authors,
                    "journal": journal_name,
                    "year": year,
                    "url": item.get("URL", f"https://doi.org/{item.get('DOI', '')}"),
                    "database": label,
                    "issn": (item.get("ISSN") or [""])[0],
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
            raw = await _async_urlopen(req, timeout=20)
            data = json.loads(raw)

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
        """Search Europe PMC — free biomedical literature database.
        
        Uses resultType=core to get pmcid, doi, fullTextUrl for full-text retrieval.
        """
        try:
            encoded = urllib.parse.quote(query)
            url = (
                f"https://www.ebi.ac.uk/europepmc/webservices/rest/search"
                f"?query={encoded}&resultType=core&pageSize={max_results}"
                f"&format=json&sort=RELEVANCE"
            )
            req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/1.0"})
            raw = await _async_urlopen(req, timeout=15)
            data = json.loads(raw)

            papers = []
            for r in data.get("resultList", {}).get("result", []):
                authors = (r.get("authorString", "") or "").split(", ")[:5]
                
                # Extract PMCID (needed for Tier 1 fullTextXML)
                pmcid = r.get("pmcid", "") or ""
                
                # Extract DOI
                doi = r.get("doi", "") or ""
                
                # Extract full text / PDF URLs from fullTextUrlList
                full_text_url = ""
                pdf_url = ""
                ft_list = r.get("fullTextUrlList", {}).get("fullTextUrl", [])
                for ft in ft_list:
                    ft_url = ft.get("url", "")
                    ft_style = ft.get("style", "")
                    ft_doc_style = ft.get("documentStyle", "")
                    if "pdf" in ft_style.lower() or "pdf" in ft_doc_style.lower() or ft_url.endswith(".pdf"):
                        if not pdf_url:
                            pdf_url = ft_url
                    elif ft_url and not full_text_url:
                        full_text_url = ft_url
                
                papers.append({
                    "id": r.get("id", ""),
                    "title": r.get("title", ""),
                    "abstract": (r.get("abstractText", "") or "")[:800],
                    "authors": authors,
                    "journal": r.get("journalTitle", ""),
                    "year": str(r.get("pubYear", "")),
                    "doi": doi,
                    "pmid": r.get("pmid", "") or r.get("id", ""),
                    "pmcid": pmcid,
                    "full_text_url": full_text_url,
                    "pdf_url": pdf_url,
                    "url": f"https://europepmc.org/article/{r.get('source','')}/{r.get('id','')}",
                    "database": "Europe PMC",
                })

            return papers, len(papers)
        except Exception as e:
            logger.warning(f"Europe PMC search failed for '{query}': {e}")
            return [], 0

    async def _search_biorxiv(self, query: str, max_results: int):
        """Search bioRxiv + medRxiv preprints via Europe PMC.
        
        Uses resultType=core to get pmcid, doi, fullTextUrl for full-text retrieval.
        """
        try:
            encoded = urllib.parse.quote(query)
            url = (
                f"https://www.ebi.ac.uk/europepmc/webservices/rest/search"
                f"?query={encoded}%20AND%20(SRC:PPR%20OR%20SRC:MED)"
                f"&resultType=core&pageSize={max_results}"
                f"&format=json&sort=RELEVANCE"
            )
            req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/1.0"})
            raw = await _async_urlopen(req, timeout=15)
            data = json.loads(raw)

            papers = []
            for r in data.get("resultList", {}).get("result", []):
                authors = (r.get("authorString", "") or "").split(", ")[:5]
                
                pmcid = r.get("pmcid", "") or ""
                doi = r.get("doi", "") or ""
                
                full_text_url = ""
                pdf_url = ""
                ft_list = r.get("fullTextUrlList", {}).get("fullTextUrl", [])
                for ft in ft_list:
                    ft_url = ft.get("url", "")
                    ft_style = ft.get("style", "")
                    if "pdf" in ft_style.lower() or ft_url.endswith(".pdf"):
                        if not pdf_url:
                            pdf_url = ft_url
                    elif ft_url and not full_text_url:
                        full_text_url = ft_url
                
                papers.append({
                    "id": r.get("id", ""),
                    "title": r.get("title", ""),
                    "abstract": (r.get("abstractText", "") or "")[:800],
                    "authors": authors,
                    "journal": r.get("bookOrReportDetails", {}).get("publisher", "bioRxiv") if isinstance(r.get("bookOrReportDetails"), dict) else "bioRxiv",
                    "year": str(r.get("pubYear", "")),
                    "doi": doi,
                    "pmid": r.get("pmid", "") or r.get("id", ""),
                    "pmcid": pmcid,
                    "full_text_url": full_text_url,
                    "pdf_url": pdf_url,
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
        text = element.text
        if text:
            return text.strip()
        if hasattr(element, 'itertext'):
            return "".join(element.itertext()).strip()
        return ""

    def _resolve_pmcids_via_europe_pmc(self, papers: list):
        """Resolve PMCIDs for papers that have a PMID but no PMCID.

        Queries Europe PMC's search API with each PMID to find the
        corresponding PMCID. This unblocks Tier-1 full-text retrieval.
        """
        import urllib.request
        import json as _json
        import time as _time

        missing = [p for p in papers if not p.get("pmcid") and p.get("pmid")]
        if not missing:
            return

        resolved = 0
        for paper in missing[:20]:  # cap at 20 to avoid rate limits
            pmid = paper["pmid"]
            try:
                url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=PMID:{pmid}&resultType=core&format=json"
                req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/1.0"})
                raw = await _async_urlopen(req, timeout=10)
                data = _json.loads(raw.decode("utf-8"))
                results = data.get("resultList", {}).get("result", [])
                if results:
                    pmcid = results[0].get("pmcid", "")
                    if pmcid:
                        if not pmcid.upper().startswith("PMC"):
                            pmcid = "PMC" + pmcid
                        paper["pmcid"] = pmcid
                        resolved += 1
                await asyncio.sleep(0.3)  # be nice to Europe PMC API
            except Exception:
                pass  # silent — this is a best-effort enhancement

        if resolved:
            logger.info(f"Europe PMC resolved {resolved}/{len(missing)} PMCIDs")
