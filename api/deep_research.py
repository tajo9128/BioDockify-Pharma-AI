"""Deep Research API — collect thousands of sources from multiple databases, scan, filter, store."""
from helpers.api import ApiHandler, Request, Response
import asyncio, logging, json, re, os, urllib.request, urllib.parse
from typing import Dict, List, Any
from datetime import datetime

log = logging.getLogger("deep_research")


async def _async_urlopen(req, timeout=30):
    """Non-blocking urlopen with proper resource cleanup (fixes event-loop blocking + FD leaks)."""
    def _fetch():
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    return await asyncio.to_thread(_fetch)

STORAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "deep_research")
os.makedirs(STORAGE_DIR, exist_ok=True)


class DeepResearchHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "collect")

        if action == "collect":
            return await self._collect_sources(input)
        elif action == "scan":
            return self._scan_results(input)
        elif action == "screen":
            return self._screen_sources(input)
        elif action == "screen_decision":
            return self._record_screen_decision(input)
        elif action == "store":
            return self._store_to_kb(input)
        elif action == "status":
            return self._get_status(input)
        elif action == "list":
            return self._list_sessions()
        elif action == "prisma_counts":
            return self._prisma_counts(input)
        elif action == "literature_map":
            return await self._literature_map(input)

        return {"status": "error", "error": f"Unknown action: {action}"}

    async def _collect_sources(self, input: dict) -> dict:
        """Collect sources from multiple databases."""
        topic = input.get("topic", "").strip()
        if not topic:
            return {"status": "error", "error": "Topic required"}

        max_sources = int(input.get("max_sources", 20))
        databases = input.get("databases", ["pubmed", "europe_pmc", "semantic_scholar"])
        if not databases:
            return {"error": "At least one database must be selected"}
        year_from = input.get("year_from", "")
        year_to = input.get("year_to", "")

        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        all_sources = []
        stats = {"total": 0, "by_database": {}, "duplicates_removed": 0, "session_id": session_id}

        # Collect from each database
        for db in databases:
            try:
                if db == "pubmed":
                    sources = await self._search_pubmed(topic, max_sources // len(databases), year_from, year_to)
                elif db == "semantic_scholar":
                    sources = await self._search_semantic_scholar(topic, max_sources // len(databases))
                elif db == "crossref":
                    sources = await self._search_crossref(topic, max_sources // len(databases))
                elif db == "openalex":
                    sources = await self._search_openalex(topic, max_sources // len(databases))
                elif db == "arxiv":
                    sources = await self._search_arxiv(topic, max_sources // len(databases))
                elif db == "europe_pmc":
                    sources = await self._search_europe_pmc(topic, max_sources // len(databases))
                elif db == "biorxiv":
                    sources = await self._search_biorxiv(topic, max_sources // len(databases))
                elif db == "google_scholar":
                    sources = await self._search_google_scholar(topic, max_sources // len(databases))
                elif db == "scopus":
                    sources = await self._search_scopus(topic, max_sources // len(databases))
                elif db == "springer":
                    sources = await self._search_springer(topic, max_sources // len(databases))
                else:
                    sources = []

                stats["by_database"][db] = len(sources)
                all_sources.extend(sources)
            except Exception as e:
                log.warning(f"Search {db} failed: {e}")
                stats["by_database"][db] = 0

        # Deduplicate by title similarity
        seen_titles = set()
        unique_sources = []
        for src in all_sources:
            title_key = re.sub(r'[^a-z0-9]', '', src.get("title", "").lower())[:50]
            if title_key and title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_sources.append(src)
            else:
                stats["duplicates_removed"] += 1

        stats["total"] = len(unique_sources)

        # ── Split into 2 rounds: return first 50% immediately, fetch rest in background ──
        max_store = int(input.get("max_store", 10))
        retrieval_pool = unique_sources[:max_store]
        mid = len(retrieval_pool) // 2
        first_half = retrieval_pool[:mid] if mid > 0 else retrieval_pool[:1]
        second_half = retrieval_pool[mid:] if mid > 0 else []

        # Save session immediately (metadata only — no full text yet)
        session_path = os.path.join(STORAGE_DIR, f"session_{session_id}.json")
        with open(session_path, "w", encoding="utf-8") as f:
            json.dump({"topic": topic, "sources": unique_sources, "stats": stats,
                        "created_at": datetime.now().isoformat()}, f, ensure_ascii=False, indent=2)

        # ── Background: fetch full text for ALL sources + store to KB ──
        def _fetch_and_store():
            ft_count = 0
            kb_count = 0
            try:
                from modules.literature.full_text import FullTextRetriever
                retriever = FullTextRetriever()
                for src in retrieval_pool:
                    if not src.get("title"):
                        continue
                    try:
                        ft = retriever.retrieve(src)
                        if ft and len(ft) > 200:
                            src["full_text"] = ft
                            src["full_text_available"] = True
                            ft_count += 1
                        else:
                            src["full_text_available"] = False
                    except Exception:
                        src["full_text_available"] = False
                log.info(f"Full text retrieved for {ft_count}/{len(retrieval_pool)} sources")
            except Exception as e:
                log.warning(f"Full text retrieval error: {e}")

            # Store full-text articles to KB
            try:
                from modules.knowledge.auto_store import auto_store
                for src in retrieval_pool:
                    full_text = src.get("full_text", "")
                    if not full_text or len(full_text) < 2000:
                        continue
                    title = src.get("title", "Untitled")
                    authors = ", ".join(src.get("authors", [])[:5])
                    year = src.get("year", "")
                    doi = src.get("doi", "")
                    content = f"**Authors:** {authors}\n**Year:** {year}\n**DOI:** {doi}\n\n## Full Text\n\n{full_text}"
                    auto_store(module_name="deep_research", title=title, content=content,
                               source="Deep Research", tags=["deep_research", "literature"],
                               category="deep_research", metadata={"doi": doi, "authors": authors, "year": year})
                    kb_count += 1
            except Exception as e:
                log.warning(f"KB store error: {e}")

            # Update session with full text
            try:
                stats["full_text_count"] = ft_count
                stats["kb_stored"] = kb_count
                with open(session_path, "w", encoding="utf-8") as f:
                    json.dump({"topic": topic, "sources": unique_sources, "stats": stats,
                                "created_at": datetime.now().isoformat()}, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

        # Start background fetch (don't await)
        import threading
        threading.Thread(target=_fetch_and_store, daemon=True).start()

        # Return first 50% immediately (metadata only — fast response)
        stats["full_text_count"] = 0
        stats["kb_stored"] = 0

        return {
            "status": "ok",
            "session_id": session_id,
            "topic": topic,
            "sources": unique_sources[:50],
            "stats": stats,
            "kb_stored": kb_stored,
            "kb_skipped": kb_skipped,
            "full_text_fetched": full_text_count,
        }

    def _scan_results(self, input: dict) -> dict:
        """Scan collected sources for relevance."""
        session_id = input.get("session_id", "")
        keywords = input.get("keywords", [])
        min_citations = int(input.get("min_citations", 0))

        session_path = os.path.join(STORAGE_DIR, f"session_{session_id}.json")
        if not os.path.exists(session_path):
            return {"status": "error", "error": "Session not found"}

        with open(session_path, "r", encoding="utf-8") as f:
            session = json.load(f)

        sources = session.get("sources", [])
        scanned = []
        for src in sources:
            score = 0
            title_lower = src.get("title", "").lower()
            abstract_lower = src.get("abstract", "").lower()
            combined = title_lower + " " + abstract_lower

            # Keyword relevance
            for kw in keywords:
                if kw.lower() in combined:
                    score += 1

            # Citation count bonus
            citations = src.get("citations", 0) or 0
            if citations >= min_citations:
                score += min(citations // 10, 5)

            # Year recency bonus
            try:
                year = int(src.get("year", 0) or 0)
            except (ValueError, TypeError):
                year = 0
            if year >= 2020:
                score += 2
            elif year >= 2015:
                score += 1

            src["relevance_score"] = score
            scanned.append(src)

        scanned.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        session["scanned_sources"] = scanned
        session["scan_keywords"] = keywords

        session_path = os.path.join(STORAGE_DIR, f"session_{session_id}.json")
        with open(session_path, "w", encoding="utf-8") as f:
            json.dump(session, f, ensure_ascii=False, indent=2)

        return {
            "status": "ok",
            "session_id": session_id,
            "scanned": len(scanned),
            "top_sources": scanned[:20],
        }

    def _screen_sources(self, input: dict) -> dict:
        """Title/Abstract screening workspace — mark each paper include/exclude/maybe.

        This is the screening step of the systematic review golden path:
        topic → collect → scan → SCREEN (here) → store to KB → synthesis
        """
        session_id = input.get("session_id", "")
        session_path = os.path.join(STORAGE_DIR, f"session_{session_id}.json")
        if not os.path.exists(session_path):
            return {"status": "error", "error": "Session not found"}

        with open(session_path, "r", encoding="utf-8") as f:
            session = json.load(f)

        sources = session.get("scanned_sources") or session.get("sources", [])
        # Initialize screening state
        for src in sources:
            if "screen_decision" not in src:
                src["screen_decision"] = "pending"  # include | exclude | maybe | pending
            if "screen_reason" not in src:
                src["screen_reason"] = ""

        session["screening_started"] = True
        with open(session_path, "w", encoding="utf-8") as f:
            json.dump(session, f, ensure_ascii=False, indent=2)

        counts = self._count_screen_decisions(sources)
        return {
            "status": "ok",
            "session_id": session_id,
            "total": len(sources),
            "counts": counts,
            "sources": sources,
        }

    def _record_screen_decision(self, input: dict) -> dict:
        """Record a single screening decision (include/exclude/maybe + reason)."""
        session_id = input.get("session_id", "")
        source_idx = int(input.get("source_idx", -1))
        decision = input.get("decision", "pending").lower()  # include|exclude|maybe
        reason = input.get("reason", "")

        session_path = os.path.join(STORAGE_DIR, f"session_{session_id}.json")
        if not os.path.exists(session_path):
            return {"status": "error", "error": "Session not found"}

        with open(session_path, "r", encoding="utf-8") as f:
            session = json.load(f)

        sources = session.get("scanned_sources") or session.get("sources", [])
        if 0 <= source_idx < len(sources):
            sources[source_idx]["screen_decision"] = decision
            sources[source_idx]["screen_reason"] = reason
            with open(session_path, "w", encoding="utf-8") as f:
                json.dump(session, f, ensure_ascii=False, indent=2)

        counts = self._count_screen_decisions(sources)
        return {
            "status": "ok",
            "session_id": session_id,
            "source_idx": source_idx,
            "decision": decision,
            "counts": counts,
        }

    def _prisma_counts(self, input: dict) -> dict:
        """Return PRISMA 2020 counts for this session — auto-computed from screening decisions."""
        session_id = input.get("session_id", "")
        session_path = os.path.join(STORAGE_DIR, f"session_{session_id}.json")
        if not os.path.exists(session_path):
            return {"status": "error", "error": "Session not found"}

        with open(session_path, "r", encoding="utf-8") as f:
            session = json.load(f)

        sources = session.get("scanned_sources") or session.get("sources", [])
        counts = self._count_screen_decisions(sources)
        # Duplicates removed during collect
        duplicates = session.get("duplicates_removed", 0)
        identification = len(sources) + duplicates

        return {
            "status": "ok",
            "session_id": session_id,
            "prisma": {
                "identification": identification,
                "duplicates_removed": duplicates,
                "screened": len(sources),
                "title_abstract_excluded": counts.get("exclude", 0),
                "sought_for_retrieval": counts.get("include", 0) + counts.get("maybe", 0),
                "included": counts.get("include", 0),
            },
        }

    @staticmethod
    def _count_screen_decisions(sources):
        counts = {"include": 0, "exclude": 0, "maybe": 0, "pending": 0}
        for src in sources:
            d = src.get("screen_decision", "pending")
            counts[d] = counts.get(d, 0) + 1
        return counts

    def _store_to_kb(self, input: dict) -> dict:
        """Store selected sources to knowledge base with proper categorization."""
        session_id = input.get("session_id", "")
        max_store = int(input.get("max_store", 50))
        topic = input.get("topic", "")

        session_path = os.path.join(STORAGE_DIR, f"session_{session_id}.json")
        if not os.path.exists(session_path):
            return {"status": "error", "error": "Session not found"}

        with open(session_path, "r", encoding="utf-8") as f:
            session = json.load(f)

        if not topic:
            topic = session.get("topic", "Deep Research")

        sources = session.get("scanned_sources", session.get("sources", []))[:max_store]
        stored = 0
        skipped = 0
        from modules.knowledge.auto_store import auto_store
        for src in sources:
            try:
                title = src.get("title", "Untitled")
                authors = ", ".join(src.get("authors", [])[:5])
                year = src.get("year", "")
                full_text = src.get("full_text", "")
                doi = src.get("doi", "")
                journal = src.get("journal", "")
                database = src.get("database", "")

                # SKIP if no full text — only full articles go into KB
                if not full_text or len(full_text) < 2000:
                    skipped += 1
                    continue

                content = f"**Authors:** {authors}\n**Year:** {year}\n**Journal:** {journal}\n**Database:** {database}\n**DOI:** {doi}\n**URL:** {src.get('url','')}\n\n## Full Text\n\n{full_text}"

                auto_store(
                    module_name="deep_research",
                    title=title,
                    content=content,
                    source=f"Deep Research: {topic}",
                    tags=["deep_research", database, str(year), topic[:30]],
                    metadata={"doi": doi, "pmid": src.get("pmid", ""), "citations": src.get("citations", 0), "full_text": True},
                    category="deep_research",
                )
                stored += 1
            except Exception as e:
                log.warning(f"Store paper failed: {e}")

        # Also store a summary
        summary_content = f"## Deep Research Summary: {topic}\n\n"
        summary_content += f"**Date:** {datetime.now().strftime('%Y-%m-%d')}\n"
        summary_content += f"**Total Sources:** {len(sources)}\n\n"
        summary_content += "### Key Papers\n\n"
        for i, src in enumerate(sources[:10], 1):
            summary_content += f"{i}. {src.get('title', '')} ({src.get('year', '')}) - {src.get('journal', '')}\n"

        from modules.knowledge.auto_store import auto_store
        auto_store(
            module_name="deep_research",
            title=f"Research Summary: {topic}",
            content=summary_content,
            source="Deep Research Summary",
            tags=["deep_research", "summary", topic[:30]],
            category="deep_research",
        )

        return {"status": "ok", "stored": stored, "skipped": skipped, "session_id": session_id, "topic": topic}

    def _get_status(self, input: dict) -> dict:
        session_id = input.get("session_id", "")
        session_path = os.path.join(STORAGE_DIR, f"session_{session_id}.json")
        if not os.path.exists(session_path):
            return {"status": "error", "error": "Session not found"}
        with open(session_path, "r", encoding="utf-8") as f:
            session = json.load(f)
        return {"status": "ok", "session_id": session_id, "stats": session.get("stats", {}), "total": len(session.get("sources", []))}

    def _list_sessions(self) -> dict:
        sessions = []
        for f in os.listdir(STORAGE_DIR):
            if f.startswith("session_") and f.endswith(".json"):
                try:
                    with open(os.path.join(STORAGE_DIR, f)) as fh:
                        s = json.load(fh)
                    sessions.append({"session_id": s.get("stats", {}).get("session_id", ""), "topic": s.get("topic", ""), "total": s.get("stats", {}).get("total", 0), "created_at": s.get("created_at", "")})
                except Exception as e:
                    log.debug(f"Failed to load session {f}: {e}")
        return {"status": "ok", "sessions": sorted(sessions, key=lambda x: x.get("created_at", ""), reverse=True)}

    # ── Database Scrapers ──

    async def _search_pubmed(self, topic: str, limit: int, year_from: str = "", year_to: str = "") -> List[Dict]:
        """Search PubMed via E-utilities API (esearch + efetch for full data)."""
        results = []
        try:
            query = urllib.parse.quote(topic)
            url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={query}&retmax={min(limit, 500)}&retmode=json&sort=relevance"
            if year_from:
                url += f"&mindate={year_from}&maxdate={year_to or '2026'}"
            req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/7.0"})
            raw = await _async_urlopen(req)
            data = json.loads(raw)
            ids = data.get("esearchresult", {}).get("idlist", [])

            if ids:
                id_str = ",".join(ids[:100])
                # Use efetch (not esummary) — returns full abstracts + PMCIDs
                import xml.etree.ElementTree as ET
                url2 = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={id_str}&retmode=xml&rettype=abstract"
                req2 = urllib.request.Request(url2, headers={"User-Agent": "BioDockify/7.0"})
                raw2 = await _async_urlopen(req2)
                root = ET.fromstring(raw2)

                for article in root.findall(".//PubmedArticle"):
                    pmid = ""
                    pmid_elem = article.find(".//PMID")
                    if pmid_elem is not None:
                        pmid = (pmid_elem.text or "").strip()

                    title = ""
                    title_elem = article.find(".//ArticleTitle")
                    if title_elem is not None:
                        title = "".join(title_elem.itertext()).strip()

                    # Get abstract
                    abstract_parts = []
                    for abs_text in article.findall(".//Abstract/AbstractText"):
                        label = abs_text.attrib.get("Label", "")
                        text = "".join(abs_text.itertext()).strip()
                        if label:
                            abstract_parts.append(f"{label}: {text}")
                        else:
                            abstract_parts.append(text)
                    abstract = " ".join(abstract_parts)

                    # Get authors
                    authors = []
                    for author in article.findall(".//Author"):
                        last = author.find("LastName")
                        init = author.find("Initials")
                        name = ""
                        if last is not None and last.text:
                            name = last.text
                        if init is not None and init.text:
                            name += " " + init.text
                        if name:
                            authors.append(name)

                    # Get journal and year
                    journal = ""
                    journal_elem = article.find(".//Journal/Title")
                    if journal_elem is not None:
                        journal = (journal_elem.text or "").strip()

                    year = ""
                    year_elem = article.find(".//PubDate/Year")
                    if year_elem is not None:
                        year = (year_elem.text or "").strip()
                    else:
                        medline = article.find(".//MedlineDate")
                        if medline is not None and medline.text:
                            year = medline.text[:4]

                    # Get DOI
                    doi = ""
                    doi_elem = article.find(".//ELocationID[@EIdType='doi']")
                    if doi_elem is not None:
                        doi = (doi_elem.text or "").strip()

                    # Get PMCID from ArticleIdList
                    pmcid = ""
                    aid_list = article.find(".//ArticleIdList")
                    if aid_list is not None:
                        for aid in aid_list.findall("ArticleId"):
                            if aid.attrib.get("IdType") == "pmc":
                                pmcid = (aid.text or "").strip()
                                break

                    results.append({
                        "title": title,
                        "authors": authors[:5],
                        "year": year,
                        "journal": journal,
                        "pmid": pmid,
                        "pmcid": pmcid,
                        "doi": doi,
                        "abstract": abstract,
                        "database": "PubMed",
                        "citations": 0,
                    })
        except Exception as e:
            log.warning(f"PubMed search failed: {e}")
        return results

    async def _search_semantic_scholar(self, topic: str, limit: int) -> List[Dict]:
        """Search Semantic Scholar API."""
        results = []
        try:
            query = urllib.parse.quote(topic)
            url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={query}&limit={min(limit, 100)}&fields=title,authors,year,abstract,citationCount,journal,externalIds,openAccessPdf"
            req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/7.0"})
            raw = await _async_urlopen(req)
            data = json.loads(raw)
            for paper in data.get("data", []):
                # Extract openAccessPdf URL (unblocks Tier-3b full text retrieval)
                open_access_pdf = ""
                oap = paper.get("openAccessPdf")
                if isinstance(oap, dict):
                    open_access_pdf = oap.get("url", "")
                elif isinstance(oap, str):
                    open_access_pdf = oap

                results.append({
                    "title": paper.get("title", ""),
                    "authors": [a.get("name", "") for a in paper.get("authors", [])],
                    "year": paper.get("year", 0),
                    "journal": paper.get("journal", {}).get("name", "") if paper.get("journal") else "",
                    "abstract": paper.get("abstract", ""),
                    "doi": paper.get("externalIds", {}).get("DOI", ""),
                    "pmid": paper.get("externalIds", {}).get("PubMed", ""),
                    "openAccessPdf": open_access_pdf,
                    "citations": paper.get("citationCount", 0),
                    "database": "Semantic Scholar",
                })
        except Exception as e:
            log.warning(f"Semantic Scholar search failed: {e}")
        return results

    async def _search_crossref(self, topic: str, limit: int) -> List[Dict]:
        """Search Crossref API."""
        results = []
        try:
            query = urllib.parse.quote(topic)
            url = f"https://api.crossref.org/works?query={query}&rows={min(limit, 100)}&select=DOI,title,author,published-print,container-title,abstract,is-referenced-by-count"
            req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/7.0"})
            raw = await _async_urlopen(req)
            data = json.loads(raw)
            for item in data.get("message", {}).get("items", []):
                title_list = item.get("title", [])
                title = title_list[0] if title_list else ""
                authors = [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in item.get("author", [])]
                year_parts = item.get("published-print", {}).get("date-parts", [[]])
                year = year_parts[0][0] if year_parts and year_parts[0] else 0
                journal_list = item.get("container-title", [])
                journal = journal_list[0] if journal_list else ""
                results.append({
                    "title": title,
                    "authors": authors,
                    "year": year,
                    "journal": journal,
                    "abstract": item.get("abstract", "")[:500],
                    "doi": item.get("DOI", ""),
                    "citations": item.get("is-referenced-by-count", 0),
                    "database": "Crossref",
                })
        except Exception as e:
            log.warning(f"Crossref search failed: {e}")
        return results

    async def _search_openalex(self, topic: str, limit: int) -> List[Dict]:
        """Search OpenAlex API."""
        results = []
        try:
            query = urllib.parse.quote(topic)
            url = f"https://api.openalex.org/works?search={query}&per_page={min(limit, 100)}&select=id,title,authorships,publication_year,doi,cited_by_count,primary_location"
            req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/7.0"})
            raw = await _async_urlopen(req)
            data = json.loads(raw)
            for work in data.get("results", []):
                authors = [a.get("author", {}).get("display_name", "") for a in work.get("authorships", [])]
                loc = work.get("primary_location", {}) or {}
                source = loc.get("source", {}) or {}
                results.append({
                    "title": work.get("title", ""),
                    "authors": authors[:10],
                    "year": work.get("publication_year", 0),
                    "journal": source.get("display_name", ""),
                    "doi": work.get("doi", ""),
                    "citations": work.get("cited_by_count", 0),
                    "abstract": "",
                    "database": "OpenAlex",
                })
        except Exception as e:
            log.warning(f"OpenAlex search failed: {e}")
        return results

    async def _search_arxiv(self, topic: str, limit: int) -> List[Dict]:
        """Search arXiv API."""
        results = []
        try:
            query = urllib.parse.quote(topic)
            url = f"https://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results={min(limit, 100)}&sortBy=relevance"
            req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/7.0"})
            raw = await _async_urlopen(req)
            xml = raw.decode("utf-8")
            # Simple XML parsing
            entries = xml.split("<entry>")[1:]
            for entry in entries:
                title_match = re.search(r"<title>(.*?)</title>", entry, re.DOTALL)
                abstract_match = re.search(r"<summary>(.*?)</summary>", entry, re.DOTALL)
                authors = re.findall(r"<name>(.*?)</name>", entry)
                year_match = re.search(r"<published>(\d{4})", entry)
                doi_match = re.search(r"<arxiv:doi>(.*?)</arxiv:doi>", entry)
                arxiv_match = re.search(r"<id>(.*?)</id>", entry)
                results.append({
                    "title": title_match.group(1).strip() if title_match else "",
                    "authors": authors[:10],
                    "year": int(year_match.group(1)) if year_match else 0,
                    "journal": "arXiv",
                    "abstract": abstract_match.group(1).strip()[:500] if abstract_match else "",
                    "doi": doi_match.group(1) if doi_match else "",
                    "arxiv_id": arxiv_match.group(1) if arxiv_match else "",
                    "citations": 0,
                    "database": "arXiv",
                })
        except Exception as e:
            log.warning(f"arXiv search failed: {e}")
        return results

    async def _search_europe_pmc(self, topic, limit):
        results = []
        try:
            q = urllib.parse.quote(topic)
            url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={q}&resultType=core&pageSize={min(limit,100)}&format=json&sort=RELEVANCE"
            req = urllib.request.Request(url, headers={"User-Agent":"BioDockify/7.0"})
            raw = await _async_urlopen(req)
            data = json.loads(raw)
            for r in data.get("resultList",{}).get("result",[]):
                authors = (r.get("authorString","") or "").split(", ")[:5]
                results.append({"title":r.get("title",""),"authors":authors,"year":str(r.get("pubYear","")),"journal":r.get("journalTitle",""),"pmid":r.get("pmid",""),"pmcid":r.get("pmcid",""),"doi":r.get("doi",""),"abstract":(r.get("abstractText","") or "")[:500],"citations":r.get("citedByCount",0),"database":"Europe PMC","url":f"https://europepmc.org/article/{r.get('source','')}/{r.get('id','')}"})
        except Exception as e:
            log.warning(f"Europe PMC failed: {e}")
        return results

    async def _search_biorxiv(self, topic, limit):
        results = []
        try:
            q = urllib.parse.quote(topic)
            url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={q}%20AND%20(SRC:PPR%20OR%20SRC:MED)&resultType=lite&pageSize={min(limit,100)}&format=json&sort=RELEVANCE"
            req = urllib.request.Request(url, headers={"User-Agent":"BioDockify/7.0"})
            raw = await _async_urlopen(req)
            data = json.loads(raw)
            for r in data.get("resultList",{}).get("result",[]):
                authors = (r.get("authorString","") or "").split(", ")[:5]
                results.append({"title":r.get("title",""),"authors":authors,"year":str(r.get("pubYear","")),"journal":"bioRxiv/medRxiv","abstract":(r.get("abstractText","") or "")[:500],"doi":r.get("doi",""),"citations":0,"database":"bioRxiv","url":f"https://europepmc.org/article/PPR/{r.get('id','')}"})
        except Exception as e:
            log.warning(f"bioRxiv failed: {e}")
        return results

    async def _search_google_scholar(self, topic, limit):
        results = []
        api_key = os.getenv("SERPAPI_KEY","")
        if not api_key:
            log.warning("Google Scholar needs SERPAPI_KEY - skipping")
            return results
        try:
            q = urllib.parse.quote(topic)
            url = f"https://serpapi.com/search.json?engine=google_scholar&q={q}&num={min(limit,20)}&api_key={api_key}"
            req = urllib.request.Request(url, headers={"User-Agent":"BioDockify/7.0"})
            raw = await _async_urlopen(req)
            data = json.loads(raw)
            for r in data.get("organic_results",[]):
                pub = r.get("publication_info",{})
                results.append({"title":r.get("title",""),"authors":pub.get("authors",[]),"year":pub.get("year",0),"journal":pub.get("summary",""),"abstract":r.get("snippet",""),"doi":"","citations":r.get("inline_links",{}).get("cited_by",{}).get("total",0),"database":"Google Scholar","url":r.get("link","")})
        except Exception as e:
            log.warning(f"Google Scholar failed: {e}")
        return results

    async def _search_scopus(self, topic, limit):
        results = []
        api_key = os.getenv("SCOPUS_API_KEY","")
        if not api_key:
            log.warning("Scopus needs SCOPUS_API_KEY - skipping")
            return results
        try:
            q = urllib.parse.quote(topic)
            url = f"https://api.elsevier.com/content/search/scopus?query={q}&count={min(limit,25)}&sort=relevance"
            req = urllib.request.Request(url, headers={"User-Agent":"BioDockify/7.0","X-ELS-APIKey":api_key,"Accept":"application/json"})
            raw = await _async_urlopen(req)
            data = json.loads(raw)
            for r in data.get("search-results",{}).get("entry",[]):
                results.append({"title":r.get("dc:title",""),"authors":[r.get("dc:creator","")],"year":r.get("prism:coverDate","")[:4],"journal":r.get("prism:publicationName",""),"doi":r.get("prism:doi",""),"abstract":"","citations":int(r.get("citedby-count",0)),"database":"Scopus"})
        except Exception as e:
            log.warning(f"Scopus failed: {e}")
        return results

    async def _search_springer(self, topic, limit):
        results = []
        api_key = os.getenv("SPRINGER_API_KEY","")
        if not api_key:
            log.warning("Springer needs SPRINGER_API_KEY - skipping")
            return results
        try:
            q = urllib.parse.quote(topic)
            url = f"https://api.springernature.com/meta/v2/json?q={q}&s=1&p={min(limit,25)}&api_key={api_key}"
            req = urllib.request.Request(url, headers={"User-Agent":"BioDockify/7.0"})
            raw = await _async_urlopen(req)
            data = json.loads(raw)
            for r in data.get("records",[]):
                results.append({"title":r.get("title",""),"authors":[a.get("creator","") for a in r.get("creators",[])],"year":r.get("publicationDate","")[:4],"journal":r.get("publicationName",""),"doi":r.get("doi",""),"abstract":r.get("abstract","")[:500],"citations":0,"database":"Springer"})
        except Exception as e:
            log.warning(f"Springer failed: {e}")
        return results

    async def _literature_map(self, input: dict) -> dict:
        """Literature map — seed paper → related papers (similar / cited_by / references).

        Uses OpenAlex API (free, no key required) to build a ResearchRabbit-style
        discovery graph. Three directions:
          - similar: papers that cite the same sources (co-citation)
          - cited_by: newer papers citing this one (later work)
          - references: older papers this one cites (earlier work / foundation)

        Input:
            seed_query: search for a seed paper by title/topic
            seed_doi:   OR provide a DOI directly
            direction:  similar | cited_by | references | all (default: all)
            limit:      max papers per direction (default 10)

        Returns:
            seed paper + related papers grouped by direction, ready for
            "Add to KB" / "Start review from these" actions.
        """
        import urllib.parse

        seed_doi = (input.get("seed_doi", "") or "").strip().lower()
        seed_query = (input.get("seed_query", "") or "").strip()
        direction = (input.get("direction", "all") or "all").strip().lower()
        limit = min(int(input.get("limit", 10)), 25)

        if not seed_doi and not seed_query:
            return {"status": "error", "error": "Provide seed_doi or seed_query"}

        # ── Step 1: Resolve seed paper via OpenAlex ──
        async def _resolve_seed():
            if seed_doi:
                # OpenAlex DOI lookup: https://api.openalex.org/works/doi:10.xxxx/yyy
                clean_doi = seed_doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
                url = f"https://api.openalex.org/works/doi:{clean_doi}"
            else:
                # Search by title
                params = {"search": seed_query, "per_page": 1}
                url = f"https://api.openalex.org/works?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/1.0"})
            raw = await _async_urlopen(req, timeout=20)
            data = json.loads(raw)
            if seed_doi:
                return data
            else:
                results = data.get("results", [])
                return results[0] if results else None

        try:
            seed = await _resolve_seed()
        except Exception as e:
            return {"status": "error", "error": f"Seed paper lookup failed: {e}"}

        if not seed:
            return {"status": "error", "error": "Seed paper not found. Try a different query or DOI."}

        seed_id = seed.get("id", "").replace("https://openalex.org/", "")
        seed_title = seed.get("title", "Untitled")
        seed_authors = [a.get("author", {}).get("display_name", "") for a in seed.get("authorships", [])[:3]]
        seed_year = (seed.get("publication_date") or "")[:4]
        seed_doi_found = seed.get("doi", "")
        seed_cited_by = seed.get("cited_by_count", 0)
        seed_concepts = [c.get("display_name", "") for c in seed.get("concepts", [])[:5] if c.get("score", 0) > 0.3]

        seed_paper = {
            "openalex_id": seed_id,
            "title": seed_title,
            "authors": seed_authors,
            "year": seed_year,
            "doi": (seed_doi_found or "").replace("https://doi.org/", ""),
            "cited_by_count": seed_cited_by,
            "concepts": seed_concepts,
            "abstract": self._openalex_abstract(seed.get("abstract_inverted_index")),
        }

        # ── Step 2: Fetch related papers ──
        related = {"similar": [], "cited_by": [], "references": []}

        async def _fetch_direction(dir_name, endpoint_key):
            """Fetch papers for one direction from OpenAlex."""
            ids_list = seed.get(endpoint_key, [])
            # OpenAlex returns only counts, need to fetch actual works
            if endpoint_key == "referenced_works":
                # This paper's references (earlier work)
                ref_count = seed.get("referenced_works_count", len(ids_list))
                if not ids_list or ref_count == 0:
                    return
                # Fetch up to `limit` references
                sample_ids = ids_list[:limit]
                for batch_start in range(0, len(sample_ids), 25):
                    batch = sample_ids[batch_start:batch_start + 25]
                    filter_val = "|".join(batch)
                    url = f"https://api.openalex.org/works?filter=openalex_id:{filter_val}&per_page={min(len(batch), limit)}"
                    try:
                        req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/1.0"})
                        raw = await _async_urlopen(req, timeout=20)
                        data = json.loads(raw)
                        for w in data.get("results", []):
                            related[dir_name].append(self._format_openalex_paper(w))
                    except Exception:
                        pass
                    if len(related[dir_name]) >= limit:
                        break
            else:
                # cited_by: papers citing this one (later work)
                if endpoint_key == "cited_by_count" and seed_cited_by > 0:
                    url = f"https://api.openalex.org/works?filter=cites:{seed_id}&per_page={limit}&sort=cited_by_count:desc"
                    try:
                        req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/1.0"})
                        raw = await _async_urlopen(req, timeout=20)
                        data = json.loads(raw)
                        for w in data.get("results", []):
                            related[dir_name].append(self._format_openalex_paper(w))
                    except Exception:
                        pass
                # similar: co-cited papers (cited_by the same sources)
                elif endpoint_key == "concepts" and seed_concepts:
                    # Use top concepts to find similar work
                    concept_filter = ",".join(f"concepts.id:{c}" for c in seed.get("concepts", [])[:3] if c.get("id"))
                    if concept_filter:
                        url = (f"https://api.openalex.org/works?filter={concept_filter}"
                               f"&per_page={limit}&sort=cited_by_count:desc")
                        try:
                            req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/1.0"})
                            raw = await _async_urlopen(req, timeout=20)
                            data = json.loads(raw)
                            for w in data.get("results", []):
                                if w.get("id", "").replace("https://openalex.org/", "") != seed_id:
                                    related[dir_name].append(self._format_openalex_paper(w))
                        except Exception:
                            pass

        # Fetch the requested directions
        import asyncio as _aio
        tasks = []
        if direction in ("all", "cited_by"):
            tasks.append(_fetch_direction("cited_by", "cited_by_count"))
        if direction in ("all", "similar"):
            tasks.append(_fetch_direction("similar", "concepts"))
        if direction in ("all", "references"):
            tasks.append(_fetch_direction("references", "referenced_works"))
        if tasks:
            await _aio.gather(*tasks, return_exceptions=True)

        # Dedupe across directions
        seen = {seed_id}
        for dir_name in related:
            deduped = []
            for p in related[dir_name]:
                pid = p.get("openalex_id", "")
                if pid and pid not in seen:
                    seen.add(pid)
                    deduped.append(p)
            related[dir_name] = deduped[:limit]

        return {
            "status": "ok",
            "seed": seed_paper,
            "similar": related["similar"],
            "cited_by": related["cited_by"],
            "references": related["references"],
            "counts": {
                "similar": len(related["similar"]),
                "cited_by": len(related["cited_by"]),
                "references": len(related["references"]),
            },
        }

    @staticmethod
    def _openalex_abstract(inverted_index):
        """Reconstruct abstract from OpenAlex inverted index format."""
        if not inverted_index:
            return ""
        word_positions = []
        for word, positions in inverted_index.items():
            for pos in positions:
                word_positions.append((pos, word))
        word_positions.sort()
        return " ".join(w for _, w in word_positions)[:1000]

    @staticmethod
    def _format_openalex_paper(w):
        """Format an OpenAlex work into our standard paper dict."""
        return {
            "openalex_id": w.get("id", "").replace("https://openalex.org/", ""),
            "title": w.get("title", "Untitled"),
            "authors": [a.get("author", {}).get("display_name", "") for a in w.get("authorships", [])[:3]],
            "year": (w.get("publication_date") or "")[:4],
            "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
            "cited_by_count": w.get("cited_by_count", 0),
            "journal": (w.get("primary_location") or {}).get("source", {}).get("display_name", "") if w.get("primary_location") else "",
            "abstract": DeepResearchHandler._openalex_abstract(w.get("abstract_inverted_index")),
            "database": "OpenAlex",
        }
