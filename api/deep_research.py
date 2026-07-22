"""Deep Research API — collect thousands of sources from multiple databases, scan, filter, store."""
from helpers.api import ApiHandler, Request, Response
import logging, json, re, os, urllib.request, urllib.parse
from typing import Dict, List, Any
from datetime import datetime

log = logging.getLogger("deep_research")

STORAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "deep_research")
os.makedirs(STORAGE_DIR, exist_ok=True)


class DeepResearchHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "collect")

        if action == "collect":
            return await self._collect_sources(input)
        elif action == "scan":
            return self._scan_results(input)
        elif action == "store":
            return self._store_to_kb(input)
        elif action == "status":
            return self._get_status(input)
        elif action == "list":
            return self._list_sessions()

        return {"status": "error", "error": f"Unknown action: {action}"}

    async def _collect_sources(self, input: dict) -> dict:
        """Collect sources from multiple databases."""
        topic = input.get("topic", "").strip()
        if not topic:
            return {"status": "error", "error": "Topic required"}

        max_sources = int(input.get("max_sources", 100))
        databases = input.get("databases", ["pubmed", "semantic_scholar", "crossref", "openalex", "arxiv", "europe_pmc", "biorxiv"])
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

        # ── Fetch full text for every collected source ──
        full_text_count = 0
        try:
            from modules.literature.full_text import FullTextRetriever
            retriever = FullTextRetriever()
            for src in unique_sources:
                if not src.get("title"):
                    continue
                try:
                    ft = retriever.retrieve(src)
                    if ft and len(ft) > 200:
                        src["full_text"] = ft
                        src["full_text_available"] = True
                        full_text_count += 1
                    else:
                        src["full_text_available"] = False
                except Exception:
                    src["full_text_available"] = False
            log.info(f"Full text retrieved for {full_text_count}/{len(unique_sources)} sources")
        except ImportError:
            log.warning("FullTextRetriever not available — storing metadata only")
        except Exception as e:
            log.warning(f"Full text retrieval error: {e}")
        stats["full_text_count"] = full_text_count

        # Save session (with full text included)
        session_path = os.path.join(STORAGE_DIR, f"session_{session_id}.json")
        with open(session_path, "w", encoding="utf-8") as f:
            json.dump({"topic": topic, "sources": unique_sources, "stats": stats, "created_at": datetime.now().isoformat()}, f, ensure_ascii=False, indent=2)

        # ── AUTO-STORE to Knowledge Base — ONLY full-text articles ──
        # User requirement: metadata/abstracts must NOT be saved to KB.
        # Only full-text articles get stored (so they're citable in theses).
        kb_stored = 0
        kb_skipped = 0
        try:
            from modules.knowledge.auto_store import auto_store
            for src in unique_sources[:30]:
                title = src.get("title", "Untitled")
                authors = ", ".join(src.get("authors", [])[:5])
                full_text = src.get("full_text", "")

                # SKIP if no full text (only metadata/abstract available)
                if not full_text or len(full_text) < 2000:
                    kb_skipped += 1
                    continue

                content = f"**Authors:** {authors}\n**Year:** {src.get('year','')}\n**Source:** {src.get('database','')}\n**DOI:** {src.get('doi','')}\n**PMID:** {src.get('pmid','')}\n**URL:** {src.get('url','')}\n\n## Full Text\n\n{full_text}"

                auto_store(
                    module_name="deep_research",
                    title=title,
                    content=content,
                    source=f"Research: {topic}",
                    tags=["deep_research", src.get('database',''), topic[:30]],
                    metadata={"doi": src.get("doi",""), "pmid": src.get("pmid",""), "full_text": True},
                    category="deep_research",
                )
                kb_stored += 1
        except Exception as e:
            log.warning(f"KB store failed: {e}")

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
            year = src.get("year", 0) or 0
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

                # Store in knowledge base
                from modules.knowledge.auto_store import auto_store
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
        """Search PubMed via E-utilities API."""
        results = []
        try:
            query = urllib.parse.quote(topic)
            url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={query}&retmax={min(limit, 500)}&retmode=json&sort=relevance"
            if year_from:
                url += f"&mindate={year_from}&maxdate={year_to or '2026'}"
            req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/7.0"})
            resp = urllib.request.urlopen(req, timeout=30)
            data = json.loads(resp.read())
            ids = data.get("esearchresult", {}).get("idlist", [])

            if ids:
                id_str = ",".join(ids[:100])
                url2 = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={id_str}&retmode=json"
                req2 = urllib.request.Request(url2, headers={"User-Agent": "BioDockify/7.0"})
                resp2 = urllib.request.urlopen(req2, timeout=30)
                details = json.loads(resp2.read())
                for pid in ids[:100]:
                    rec = details.get("result", {}).get(pid, {})
                    if rec:
                        results.append({
                            "title": rec.get("title", ""),
                            "authors": [a.get("name", "") for a in rec.get("authors", [])],
                            "year": rec.get("pubdate", "")[:4],
                            "journal": rec.get("source", ""),
                            "pmid": pid,
                            "doi": rec.get("elocationid", ""),
                            "abstract": "",
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
            url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={query}&limit={min(limit, 100)}&fields=title,authors,year,abstract,citationCount,journal,externalIds"
            req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/7.0"})
            resp = urllib.request.urlopen(req, timeout=30)
            data = json.loads(resp.read())
            for paper in data.get("data", []):
                results.append({
                    "title": paper.get("title", ""),
                    "authors": [a.get("name", "") for a in paper.get("authors", [])],
                    "year": paper.get("year", 0),
                    "journal": paper.get("journal", {}).get("name", "") if paper.get("journal") else "",
                    "abstract": paper.get("abstract", ""),
                    "doi": paper.get("externalIds", {}).get("DOI", ""),
                    "pmid": paper.get("externalIds", {}).get("PubMed", ""),
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
            resp = urllib.request.urlopen(req, timeout=30)
            data = json.loads(resp.read())
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
            resp = urllib.request.urlopen(req, timeout=30)
            data = json.loads(resp.read())
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
            url = f"http://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results={min(limit, 100)}&sortBy=relevance"
            req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/7.0"})
            resp = urllib.request.urlopen(req, timeout=30)
            xml = resp.read().decode("utf-8")
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
            resp = urllib.request.urlopen(req, timeout=30)
            data = json.loads(resp.read())
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
            resp = urllib.request.urlopen(req, timeout=30)
            data = json.loads(resp.read())
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
            resp = urllib.request.urlopen(req, timeout=30)
            data = json.loads(resp.read())
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
            resp = urllib.request.urlopen(req, timeout=30)
            data = json.loads(resp.read())
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
            resp = urllib.request.urlopen(req, timeout=30)
            data = json.loads(resp.read())
            for r in data.get("records",[]):
                results.append({"title":r.get("title",""),"authors":[a.get("creator","") for a in r.get("creators",[])],"year":r.get("publicationDate","")[:4],"journal":r.get("publicationName",""),"doi":r.get("doi",""),"abstract":r.get("abstract","")[:500],"citations":0,"database":"Springer"})
        except Exception as e:
            log.warning(f"Springer failed: {e}")
        return results
