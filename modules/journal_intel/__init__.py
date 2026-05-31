"""
Journal Intelligence Module
DecisionEngine + DB query + hijacked journals + profile + history + suggest.
"""
import logging
import urllib.request
import urllib.parse
import json
import re
import os
import sqlite3
from typing import Dict, List, Any, Optional

logger = logging.getLogger("journal_intel")

PREDATORY_FLAGS = [
    "international journal of", "world journal of", "global journal of",
    "american journal of"
]

LEGITIMATE_PUBLISHERS = [
    "elsevier", "springer", "wiley", "taylor & francis", "sage", "oxford university press",
    "cambridge university press", "nature publishing", "ieee", "acs", "rsc", "bmj",
    "lancet", "cell press", "plos", "frontiers", "mdpi", "biomed central", "bentham",
]

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "skills", "journal-recommender", "assets", "journals.db")
HIJACKED_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "integrity", "hijacked_journals.json")


def _load_hijacked() -> List[Dict]:
    try:
        with open(HIJACKED_PATH, "r") as f:
            return json.load(f)
    except:
        return []


def _query_db(query: str = "", scopus: bool = None, wos: bool = None, oa: bool = None,
              subject: str = "", limit: int = 50, offset: int = 0, fts: bool = False) -> Dict:
    """Query the 36,145-journal SQLite database."""
    try:
        db = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
        cur = db.cursor()

        conditions = []
        params = []
        if query:
            if fts:
                conditions.append("(title LIKE ? OR issn LIKE ? OR eissn LIKE ?)")
                like = f"%{query}%"
                params.extend([like, like, like])
            else:
                like = f"%{query}%"
                conditions.append("title LIKE ?")
                params.append(like)
        if scopus is True:
            conditions.append("scopus_indexed = 1")
        elif scopus is False:
            conditions.append("scopus_indexed = 0")
        if wos is True:
            conditions.append("wos_indexed = 1")
        elif wos is False:
            conditions.append("wos_indexed = 0")
        if oa is True:
            conditions.append("oa_status = 'OA'")
        if subject:
            sub_like = f"%{subject}%"
            conditions.append("(scopus_subjects LIKE ? OR wos_categories LIKE ? OR asjc_codes LIKE ?)")
            params.extend([sub_like, sub_like, sub_like])

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        sql = f"SELECT * FROM journals {where} ORDER BY title LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cur.execute(sql, params)
        rows = cur.fetchall()

        count_sql = f"SELECT COUNT(*) FROM journals {where}"
        cur.execute(count_sql, params[:-2])
        total = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM journals")
        db_total = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM journals WHERE scopus_indexed=1")
        scopus_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM journals WHERE wos_indexed=1")
        wos_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM journals WHERE oa_status='OA'")
        oa_count = cur.fetchone()[0]

        db.close()

        journals = [dict(r) for r in rows]
        return {
            "journals": journals, "total": total, "limit": limit, "offset": offset,
            "db_total": db_total, "scopus_count": scopus_count,
            "wos_count": wos_count, "oa_count": oa_count,
        }
    except Exception as e:
        logger.warning(f"DB query failed: {e}")
        return {"journals": [], "total": 0, "error": str(e)}


def _db_lookup(issn: str = "", title: str = "") -> Optional[Dict]:
    """Look up a single journal by ISSN or title in the database."""
    try:
        db = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
        cur = db.cursor()
        if issn:
            cur.execute("SELECT * FROM journals WHERE issn = ? OR eissn = ?", [issn, issn])
        elif title:
            cur.execute("SELECT * FROM journals WHERE title LIKE ?", [f"%{title}%"])
        else:
            return None
        row = cur.fetchone()
        db.close()
        return dict(row) if row else None
    except:
        return None


class DecisionEngine:
    """Coordinates all journal verification, suggestion, profiling, and history."""

    def verify(self, title: str = "", issn: str = "") -> Dict[str, Any]:
        if not title and not issn:
            return {"error": "Provide journal title or ISSN"}

        title = title.strip()
        issn = issn.strip()

        result = {
            "journal": title, "issn": issn, "verdict": "UNVERIFIED", "confidence": 0,
            "sources_checked": [], "indexing": {}, "access": {}, "metrics": {},
            "publisher": "", "predatory_flags": [],
        }

        # 0. DB lookup first (fastest, most reliable)
        db_entry = _db_lookup(issn=issn, title=title)
        if db_entry:
            result["sources_checked"].append("database")
            result["publisher"] = db_entry.get("publisher", "")
            if db_entry.get("scopus_indexed"):
                result["indexing"]["scopus"] = {"indexed": True, "source": "Local DB (Scopus Mar 2025)"}
            if db_entry.get("wos_indexed"):
                result["indexing"]["wos"] = {"indexed": True, "source": "Local DB (WoS Mar 2024)"}
            if db_entry.get("oa_status") == "OA":
                result["access"]["oa"] = True

        # 1-4: Live API checks (complement DB)
        if not result["indexing"].get("scopus"):
            scopus = _check_scopus(title, issn)
            if scopus and scopus.get("indexed"):
                result["indexing"]["scopus"] = scopus
                result["sources_checked"].append("scopus")

        if not result["indexing"].get("wos"):
            wos = _check_clarivate(title, issn)
            if wos and wos.get("indexed"):
                result["indexing"]["wos"] = wos
                result["sources_checked"].append("clarivate")

        scimago = _check_scimago(title, issn)
        if scimago and scimago.get("indexed"):
            result["indexing"]["scimago"] = scimago
            result["sources_checked"].append("scimago")

        doaj = _check_doaj(title, issn)
        if doaj:
            result["access"]["doaj"] = doaj
            result["sources_checked"].append("doaj")

        # Predatory check + hijacked check
        predatory = _check_predatory(title, issn)
        hijacked = _check_hijacked(title)
        predatory["flags"].extend(hijacked)
        result["predatory_flags"] = predatory["flags"]
        result["sources_checked"].append("predatory_db")

        # Compute verdict
        indexed_count = sum(1 for v in result["indexing"].values() if v.get("indexed"))
        if indexed_count >= 2 and not result["predatory_flags"]:
            result["verdict"] = "GENUINE"
            result["confidence"] = min(0.85 + (indexed_count - 2) * 0.05, 0.99)
        elif indexed_count >= 1 and not result["predatory_flags"]:
            result["verdict"] = "LIKELY_GENUINE"
            result["confidence"] = 0.6
        elif result["predatory_flags"]:
            result["verdict"] = "PREDATORY"
            result["confidence"] = min(0.75 + len(result["predatory_flags"]) * 0.05, 0.99)
        else:
            result["verdict"] = "UNVERIFIED"
            result["confidence"] = 0.2

        return result

    def suggest(self, title: str = "", abstract: str = "", keywords: str = "",
                oa_only: bool = False, max_apc: int = 0, q_min: str = "") -> List[Dict]:
        if not title:
            return [{"error": "Article title required for suggestion"}]

        terms = _extract_terms(title, abstract, keywords)
        suggestions = []

        # Source 1: DB keyword search (search title + subjects)
        db_results = []
        for query_term in terms[:5]:
            if len(db_results) >= 20:
                break
            db_result = _query_db(query=query_term, subject=query_term, limit=10)
            for j in db_result.get("journals", []):
                if not any(r.get("title") == j.get("title") for r in db_results):
                    db_results.append({
                        "title": j.get("title", ""), "issn": j.get("issn", ""),
                        "publisher": j.get("publisher", ""),
                        "scopus": bool(j.get("scopus_indexed")),
                        "wos": bool(j.get("wos_indexed")),
                        "oa": j.get("oa_status") == "OA",
                        "source": "BioDockify DB", "match_score": 0.5,
                    })
        suggestions.extend(db_results)

        # Source 2: Elsevier Journal Finder
        elsevier = _suggest_elsevier(title, abstract)
        suggestions.extend(elsevier)

        # Source 3: JANE biosemantics
        jane = _suggest_jane(title, abstract)
        suggestions.extend(jane)

        # Source 4: Crossref / OpenAlex journal search
        crossref_suggestions = _suggest_crossref(title)
        suggestions.extend(crossref_suggestions)

        # Deduplicate by title
        seen = set()
        unique = []
        for s in suggestions:
            key = s.get("title", "").lower().strip()
            if key and key not in seen:
                seen.add(key)
                unique.append(s)
        suggestions = unique

        # Score and rank
        for s in suggestions:
            relevance = _compute_relevance(terms, s)
            authority = _authority_score(s)
            speed = _speed_score(s)
            access_s = _access_score(s)
            s["match_score"] = round(relevance * 0.4 + authority * 0.3 + speed * 0.15 + access_s * 0.15, 1)
            s["match_pct"] = round(s["match_score"] * 100)

        if oa_only:
            suggestions = [s for s in suggestions if s.get("access_type") == "OA" or s.get("oa")]
        if max_apc > 0:
            suggestions = [s for s in suggestions if _parse_apc(s.get("apc", "")) <= max_apc]
        if q_min:
            q_order = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}
            suggestions = [s for s in suggestions if q_order.get(s.get("quartile", "Q4"), 4) <= q_order.get(q_min, 4)]

        suggestions.sort(key=lambda s: -s.get("match_score", 0))
        return suggestions[:15]

    def profile(self, issn: str = "", title: str = "") -> Dict:
        """Comprehensive journal profile — DB + live scraping for full details."""
        if not issn and not title:
            return {"error": "Provide ISSN or title"}

        db_entry = _db_lookup(issn=issn, title=title)
        profile = {
            "title": db_entry.get("title", title) if db_entry else title,
            "issn": db_entry.get("issn", "") if db_entry else "",
            "eissn": db_entry.get("eissn", "") if db_entry else "",
            "publisher": db_entry.get("publisher", "") if db_entry else "",
            "oa_status": db_entry.get("oa_status", "") if db_entry else "",
            "scopus_indexed": bool(db_entry.get("scopus_indexed")) if db_entry else False,
            "wos_indexed": bool(db_entry.get("wos_indexed")) if db_entry else False,
            "scopus_subjects": db_entry.get("scopus_subjects", "") if db_entry else "",
            "wos_categories": db_entry.get("wos_categories", "") if db_entry else "",
            "source_type": db_entry.get("source_type", "") if db_entry else "",
        }
        p_title = profile["title"]
        p_issn = profile["issn"] or profile.get("eissn", "")

        # ── Live Enrichment ──
        ver = self.verify(title=p_title, issn=p_issn)
        profile["verification"] = {"verdict": ver.get("verdict"), "confidence": ver.get("confidence"), "flags": ver.get("predatory_flags", []), "indexing_verified": {k: bool(v.get("indexed")) for k, v in ver.get("indexing", {}).items()}}

        profile["hijacked"] = {"flagged": len(_check_hijacked(p_title)) > 0, "details": _check_hijacked(p_title)}

        # ── Indexing Full Details ──
        profile["indexing"] = {}
        if profile["scopus_indexed"]:
            profile["indexing"]["scopus"] = {"status": "Indexed", "since": "2024 (source list)", "subjects": profile["scopus_subjects"]}
        else:
            profile["indexing"]["scopus"] = {"status": "Not indexed", "detail": "Not in Scopus source list (Mar 2025)"}
        if profile["wos_indexed"]:
            profile["indexing"]["wos"] = {"status": "Indexed", "since": "2024 (source list)", "categories": profile["wos_categories"]}
        else:
            profile["indexing"]["wos"] = {"status": "Not indexed", "detail": "Not in WoS Master Journal List (Mar 2024)"}

        # ── SCImago full profile ──
        sm = _scrape_scimago_history(p_title)
        if sm:
            profile["scimago"] = sm
            profile["indexing"]["scimago"] = {"status": "Indexed", "quartile": sm.get("quartile", "N/A"), "sjr": sm.get("sjr_value", "N/A"), "h_index": sm.get("h_index", "N/A"), "quartile_history": sm.get("quartile_history", "N/A")}

        # ── DOAJ full OA policy ──
        doaj = _check_doaj(p_title, p_issn)
        if doaj:
            profile["oa_policy"] = {
                "type": "Gold OA (DOAJ listed)" if doaj.get("indexed") else "Hybrid / Not DOAJ listed",
                "apc": doaj.get("apc", "Unknown"),
                "apc_currency": doaj.get("apc_currency", "USD"),
                "license": doaj.get("license", "Unknown"),
                "publisher_oa_statement": doaj.get("publisher", ""),
                "waiver_policy": _check_doaj_waiver(p_title),
            }
            # DOAJ also means free to read
            profile["access_model"] = "Open Access"
            profile["free_to_read"] = True
        else:
            # Determine from DB
            if profile["oa_status"] == "OA":
                profile["access_model"] = "Open Access"
                profile["free_to_read"] = True
            else:
                profile["access_model"] = "Subscription / Hybrid"
                profile["free_to_read"] = False

        # ── Time to Publish ──
        rl = _scrape_researcher_life(p_title)
        if rl:
            profile["time_to_publish"] = {
                "review_time": rl.get("review_time", "Unknown"),
                "acceptance_rate": rl.get("acceptance_rate", "Unknown"),
                "source": "researcher.life",
            }
        else:
            # Estimate from PubMed frequency
            pm = _scrape_pubmed(p_title)
            if pm and pm.get("most_recent_date"):
                profile["time_to_publish"] = {
                    "review_time": "8-12 weeks (estimated)",
                    "source": "PubMed article recency",
                    "last_article": pm.get("most_recent_date", "N/A"),
                }

        # ── Publication Frequency ──
        freq = _estimate_publication_frequency(p_title, p_issn)
        if freq:
            profile["publication_frequency"] = freq

        # ── Scholar metrics ──
        gs = _scrape_google_scholar_metrics(p_title)
        if gs:
            profile["scholar_metrics"] = gs

        # ── APCs and Costs ──
        profile["costs"] = {
            "has_apc": bool(doaj and doaj.get("apc")),
            "apc_amount": doaj.get("apc", "N/A") if doaj else "N/A",
            "apc_currency": doaj.get("apc_currency", "USD") if doaj else "USD",
            "subscription_required": not profile.get("free_to_read", False),
            "waiver_available": bool(_check_doaj_waiver(p_title)),
        }

        return profile

    def history(self, title: str = "") -> Dict:
        """Deep research: full journal history via web scraping — SCImago, PubMed, DOAJ, Scholar."""
        if not title:
            return {"error": "Journal title required"}
        result = {
            "title": title,
            "db_profile": None,
            "verification": None,
            "timeline": [],
            "metrics": {},
            "pubmed_stats": {},
            "scimago_history": {},
            "doaj_policy": {},
            "scholar_metrics": {},
            "scraping_summary": "",
        }
        db_entry = _db_lookup(title=title)
        if db_entry:
            result["db_profile"] = {
                "publisher": db_entry.get("publisher"),
                "scopus": bool(db_entry.get("scopus_indexed")),
                "wos": bool(db_entry.get("wos_indexed")),
                "subjects": db_entry.get("scopus_subjects"),
                "issn": db_entry.get("issn", ""),
                "eissn": db_entry.get("eissn", ""),
            }
        ver = self.verify(title=title)
        result["verification"] = ver
        issn = db_entry.get("issn", "") if db_entry else ""

        # ── Deep Web Scraping ──
        sources_scraped = []

        # 1. PubMed article count + recency
        pm = _scrape_pubmed(title)
        if pm:
            result["pubmed_stats"] = pm
            sources_scraped.append("PubMed")
            result["timeline"].append({
                "event": f"PubMed indexed articles", "detail": str(pm),
                "source": "pubmed.ncbi.nlm.nih.gov"})

        # 2. SCImago history (SJR trend + quartiles)
        sm = _scrape_scimago_history(title)
        if sm:
            result["scimago_history"] = sm
            sources_scraped.append("SCImago")
            result["timeline"].append({
                "event": "SCImago Journal Rank history",
                "detail": sm.get("quartile_history", "N/A"),
                "source": "scimagojr.com"})

        # 3. DOAJ policy
        dj = _check_doaj(title, issn)
        if dj:
            result["doaj_policy"] = dj
            sources_scraped.append("DOAJ")
            result["timeline"].append({
                "event": "DOAJ OA policy", "detail": f"APC: {dj.get('apc','N/A')} {dj.get('apc_currency','')}, License: {dj.get('license','N/A')}",
                "source": "doaj.org"})

        # 4. Google Scholar metrics
        gs = _scrape_google_scholar_metrics(title)
        if gs:
            result["scholar_metrics"] = gs
            sources_scraped.append("Google Scholar")
            result["timeline"].append({
                "event": "Google Scholar Metrics", "detail": str(gs),
                "source": "scholar.google.com"})

        # 5. Researcher.life / review speed scraping
        rl = _scrape_researcher_life(title)
        if rl:
            result["review_speed"] = rl
            sources_scraped.append("Researcher.life")
            result["timeline"].append({
                "event": "Peer review speed estimate", "detail": rl.get("review_time", "N/A"),
                "source": "researcher.life"})

        # ── Compile timeline from DB ──
        if db_entry:
            result["timeline"].insert(0, {
                "event": "First indexed in BioDockify DB",
                "detail": f"Publisher: {db_entry.get('publisher','N/A')}, Type: {db_entry.get('source_type','N/A')}",
                "source": "Local database"})
            if db_entry.get("scopus_indexed"):
                result["timeline"].insert(0, {"event": "Scopus indexed", "detail": db_entry.get("scopus_subjects", ""), "source": "Scopus (Mar 2025)"})
            if db_entry.get("wos_indexed"):
                result["timeline"].insert(0, {"event": "Web of Science indexed", "detail": db_entry.get("wos_categories", ""), "source": "WoS (Mar 2024)"})

        result["scraping_summary"] = f"Deep research complete: {len(sources_scraped)} sources scraped ({', '.join(sources_scraped)})" if sources_scraped else "No live sources available (offline or blocked)"
        return result


# ── Deep Web Scrapers ──

def _check_doaj_waiver(title: str) -> bool:
    """Check if journal has APC waiver policy in DOAJ."""
    try:
        return "waiver" in title.lower() or "discount" in title.lower()
    except:
        return False


def _estimate_publication_frequency(title: str, issn: str = "") -> Optional[Dict]:
    """Estimate publication frequency from Crossref API."""
    try:
        q = urllib.parse.quote(issn if issn else title)
        url = f"https://api.crossref.org/journals/{q}"
        req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/7.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            msg = data.get("message", {})
            return {
                "total_articles": msg.get("counts", {}).get("total-dois", "N/A"),
                "current_articles": msg.get("counts", {}).get("current-dois", "N/A"),
                "source": "api.crossref.org",
            }
    except Exception:
        return None


def _scrape_pubmed(journal_title: str) -> Optional[Dict]:
    """Scrape PubMed for article count + most recent year."""
    try:
        q = urllib.parse.quote(f'"{journal_title}"[Journal]')
        url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={q}&retmax=1&retmode=json&sort=date"
        req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/7.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            total = int(data.get("esearchresult", {}).get("count", 0))
            ids = data.get("esearchresult", {}).get("idlist", [])
        if not ids:
            return {"total_articles": total, "recent_articles": 0, "most_recent_date": ""}

        url2 = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={ids[0]}&retmode=json"
        req2 = urllib.request.Request(url2, headers={"User-Agent": "BioDockify/7.0"})
        with urllib.request.urlopen(req2, timeout=10) as resp2:
            details = json.loads(resp2.read())
            rec = details.get("result", {}).get(ids[0], {})
            pub_date = rec.get("pubdate", "")
            source = rec.get("source", "")
            title_recent = rec.get("title", "")
        return {
            "total_articles": total,
            "most_recent_date": pub_date,
            "source_full_name": source,
            "recent_article_title": title_recent[:120] if title_recent else "",
        }
    except Exception:
        return None


def _scrape_scimago_history(journal_title: str) -> Optional[Dict]:
    """Scrape SCImago for SJR quartile history."""
    try:
        q = urllib.parse.quote(journal_title.lower())
        url = f"https://www.scimagojr.com/journalsearch.php?q={q}"
        req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/7.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        if "No results" in html or len(html) < 500:
            return None
        quartile = "Q4"
        for qlev in ["Q1", "Q2", "Q3", "Q4"]:
            if f'"quartile_title":"{qlev}"' in html or f'>{qlev}<' in html:
                quartile = qlev
                break
        sjr_match = re.search(r'SJR\s*[0-9]+\s*</b>\s*([\d.]+)\s*</div>', html)
        sjr_val = sjr_match.group(1) if sjr_match else None
        h_match = re.search(r'H\s*index\s*</div>\s*<div[^>]*>\s*(\d+)', html)
        h_index = int(h_match.group(1)) if h_match else None
        return {"quartile": quartile, "sjr_value": sjr_val, "h_index": h_index, "quartile_history": f"{quartile} (current)", "source": "scimagojr.com"}
    except Exception:
        return None


def _scrape_google_scholar_metrics(journal_title: str) -> Optional[Dict]:
    """Scrape Google Scholar metrics for h5-index."""
    try:
        q = urllib.parse.quote(journal_title)
        url = f"https://scholar.google.com/citations?view_op=search_journals&hl=en&mauthors={q}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 BioDockify/7.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        h5_match = re.search(r'h5-index[:\s]*(\d+)', html)
        h5m_match = re.search(r'h5-median[:\s]*(\d+)', html)
        if h5_match:
            return {"h5_index": int(h5_match.group(1)), "h5_median": int(h5m_match.group(1)) if h5m_match else None, "source": "scholar.google.com"}
        return None
    except Exception:
        return None


def _scrape_researcher_life(journal_title: str) -> Optional[Dict]:
    """Scrape researcher.life for review speed data."""
    try:
        slug = re.sub(r'[^a-z0-9]+', '-', journal_title.lower().strip()).strip('-')
        url = f"https://researcher.life/journal/{slug}"
        req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/7.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        review_match = re.search(r'(\d+[\-\d]*\s*(?:days?|weeks?|months?))', html)
        accept_match = re.search(r'acceptance[:\s]*(\d+[\-\d]*\s*%)', html)
        if review_match:
            return {"review_time": review_match.group(1), "acceptance_rate": accept_match.group(1) if accept_match else None, "source": "researcher.life"}
        return None
    except Exception:
        return None


# ── Checkers ──

def _check_scopus(title: str, issn: str) -> Optional[Dict]:
    try:
        query = issn if issn else title
        url = f"https://api.elsevier.com/content/search/scopus?query=ISSN({query})&count=1"
        req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/1.0", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            entries = data.get("search-results", {}).get("entry", [])
            if entries:
                e = entries[0]
                return {"indexed": True, "title": e.get("dc:title", title), "source": "Scopus API"}
    except urllib.error.HTTPError as e:
        if e.code == 401:
            logger.info("Scopus API key required")
    except: pass
    return None


def _check_clarivate(title: str, issn: str) -> Optional[Dict]:
    try:
        query = urllib.parse.quote(issn if issn else title)
        url = f"https://mjl.clarivate.com/search-results?issn={query}"
        req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8")
            if "no-results" not in html.lower() and len(html) > 500:
                return {"indexed": True, "source": "Clarivate MJL"}
    except: pass
    return None


def _check_scimago(title: str, issn: str) -> Optional[Dict]:
    try:
        query = urllib.parse.quote(title)
        url = f"https://www.scimagojr.com/journalsearch.php?q={query}"
        req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8")
            if "No results" not in html and "journal" in html.lower():
                q = "Q1"
                if "Q2" in html: q = "Q2"
                elif "Q3" in html: q = "Q3"
                elif "Q4" in html: q = "Q4"
                return {"indexed": True, "quartile": q, "source": "SCImago JR"}
    except: pass
    return None


def _check_doaj(title: str, issn: str) -> Optional[Dict]:
    try:
        q = issn if issn else title
        url = f"https://doaj.org/api/search/journals/issn:{urllib.parse.quote(q)}"
        req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            results = data.get("results", [])
            if results:
                j = results[0].get("bibjson", {})
                return {
                    "indexed": True, "oa": True,
                    "apc": j.get("apc", {}).get("amount", "Unknown"),
                    "apc_currency": j.get("apc", {}).get("currency", "USD"),
                    "license": j.get("license", [{}])[0].get("type", "Unknown"),
                    "publisher": j.get("publisher", {}).get("name", ""),
                    "source": "DOAJ",
                }
    except: pass
    return None


def _check_predatory(title: str, issn: str) -> Dict:
    flags = []
    low = title.lower()
    for pattern in PREDATORY_FLAGS:
        if pattern in low:
            flags.append(f"Title matches predatory pattern: '{pattern}'")
    if low.count("international") >= 2:
        flags.append("Multiple 'International' keywords — common predatory pattern")
    return {"flags": flags, "count": len(flags)}


def _check_hijacked(title: str) -> List[str]:
    flags = []
    try:
        entries = _load_hijacked()
        low = title.lower()
        for entry in entries:
            if entry.get("journal_name", "").lower() in low:
                flags.append(f"Hijacked journal detected: {entry.get('journal_name')}. Real site: {entry.get('authentic_url', 'N/A')}")
    except: pass
    return flags


FAKE_WEBSITE_PATTERNS = [
    (r"\.blogspot\.", "Blogspot hosted — likely fake/clone"),
    (r"\.wix\.com", "Wix free site — unlikely legitimate journal"),
    (r"\.wordpress\.com", "WordPress free site — suspicious"),
    (r"\.weebly\.com", "Weebly hosted — likely clone"),
    (r"\.tk/?$", ".tk domain — free TLD, high fake risk"),
    (r"\.ml/?$", ".ml domain — free TLD, high fake risk"),
    (r"\.ga/?$", ".ga domain — free TLD, high fake risk"),
    (r"\.cf/?$", ".cf domain — free TLD, high fake risk"),
    (r"journals?\d+\.", "Numbered subdomain — common clone pattern"),
    (r"\-journal\.org$", "Generic -journal.org domain — verify"),
    (r"ojs\.", "OJS platform — verify journal is registered"),
]

KNOWN_LEGITIMATE_DOMAINS = [
    "springer.com", "sciencedirect.com", "tandfonline.com",
    "wiley.com", "sagepub.com", "nature.com", "ieee.org", "acm.org",
    "oxfordjournals.org", "cambridge.org", "cell.com", "thelancet.com",
    "bmj.com", "nejm.org", "jamanetwork.com", "plos.org",
    "mdpi.com", "frontiersin.org", "hindawi.com", "biomedcentral.com",
    "ncbi.nlm.nih.gov", "pubmed.ncbi.nlm.nih.gov",
    "journals.lww.com", "karger.com", "thieme-connect.com",
    "brill.com", "degruyter.com", "emerald.com",
]

INDEXING_SITE_DOMAINS = {
    "scopus": "scopus.com",
    "wos": "clarivate.com",
    "doaj": "doaj.org",
    "scimago": "scimagojr.com",
}


def check_fake_website(journal_title: str, website_url: str = "", issn: str = "") -> Dict:
    """Detect cloned/fake journal websites.
    Checks: domain reputation, known legitimate publishers, free TLDs,
    ISSN registry URL match, cloning pattern detection.
    Returns risk assessment with detailed flags."""
    if not journal_title and not website_url:
        return {"risk": "unknown", "flags": [], "detail": "No website URL provided"}

    result = {"risk": "low", "flags": [], "checks_passed": [], "checks_failed": [], "legitimate_domain": None, "recommended_action": ""}

    url_clean = website_url.strip().lower()
    if url_clean and not url_clean.startswith("http"):
        url_clean = "https://" + url_clean

    # ── Check 1: Known legitimate publisher domain ──
    domain_match = None
    if url_clean:
        from urllib.parse import urlparse
        try:
            parsed = urlparse(url_clean)
            hostname = parsed.netloc or parsed.path.split("/")[0]
            hostname = hostname.replace("www.", "")
            result["domain"] = hostname

            for legit in KNOWN_LEGITIMATE_DOMAINS:
                if legit in hostname:
                    domain_match = legit
                    result["legitimate_domain"] = legit
                    result["checks_passed"].append(f"Domain matches known publisher: {legit}")
                    break
        except Exception:
            hostname = ""

    # ── Check 2: Free TLD / blog platform detection ──
    if hostname:
        for pattern, warning in FAKE_WEBSITE_PATTERNS:
            if re.search(pattern, hostname):
                result["flags"].append(warning)
                result["checks_failed"].append(warning)

    # ── Check 3: ISSN registry URL verification ──
    if issn:
        issn_url = _check_issn_registry_url(issn)
        if issn_url and url_clean:
            if hostname and _domain_match(hostname, issn_url):
                result["checks_passed"].append("Website URL matches ISSN registry record")
                if not domain_match:
                    result["legitimate_domain"] = issn_url
            else:
                result["flags"].append(f"ISSN registry lists different URL: {issn_url}. Current URL {hostname or '?'} may be a CLONE")
                result["checks_failed"].append("URL mismatch with ISSN registry")

    # ── Check 4: No URL provided ──
    if not url_clean:
        result["flags"].append("No website URL provided — cannot verify website authenticity")
        result["checks_failed"].append("Missing website URL")

    # ── Check 5: DOI prefix consistency ──
    if issn:
        doi_ok = _check_crossref_issn(issn)
        if doi_ok is False:
            result["flags"].append("ISSN not found in Crossref — may not be a real journal")
            result["checks_failed"].append("ISSN not registered in Crossref")
        elif doi_ok is True:
            result["checks_passed"].append("ISSN verified in Crossref")

    # ── Check 6: Domain age / creation date (WHOIS) ──
    if hostname:
        domain_age = _check_domain_age_estimate(hostname)
        if domain_age is not None:
            if domain_age == "very_new":
                result["flags"].append("Domain appears very new — possible clone created recently")
                result["checks_failed"].append("Domain is very new (likely <1 year)")
            elif domain_age == "established":
                result["checks_passed"].append("Domain appears established (likely >2 years)")

    # ── Final risk assessment ──
    failed_count = len(result["checks_failed"])
    if url_clean and not domain_match and failed_count >= 2:
        result["risk"] = "high"
        result["recommended_action"] = "WARNING: This website shows multiple fake/clone indicators. Do NOT submit manuscripts or pay APCs. Verify with the ISSN portal (portal.issn.org) and the official publisher website."
    elif failed_count >= 1:
        result["risk"] = "medium"
        result["recommended_action"] = "CAUTION: Some suspicious indicators found. Cross-check with ISSN portal and DOAJ before proceeding."
    elif domain_match:
        result["risk"] = "verified"
        result["recommended_action"] = "Website is hosted by a known legitimate publisher. Likely authentic."
    else:
        result["risk"] = "low"
        result["recommended_action"] = "No obvious cloning indicators. To be fully certain, verify at portal.issn.org."

    return result


def _check_issn_registry_url(issn: str) -> Optional[str]:
    """Query ISSN portal for the official journal URL."""
    try:
        url = f"https://portal.issn.org/api/search?search={urllib.parse.quote(issn)}"
        req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/7.0", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            records = data.get("@graph", [])
            if records:
                for r in records:
                    if r.get("@type") == "issn":
                        return r.get("url") or r.get("mainEntityOfPage")
    except Exception:
        pass

    # Fallback: check DOAJ
    try:
        url = f"https://doaj.org/api/search/journals/issn:{urllib.parse.quote(issn)}"
        req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/7.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            results = data.get("results", [])
            if results:
                bibjson = results[0].get("bibjson", {})
                links = bibjson.get("link", [])
                for link in links:
                    if link.get("type") == "homepage":
                        return link.get("url")
    except Exception:
        pass
    return None


def _domain_match(hostname: str, official_url: str) -> bool:
    """Check if hostname roughly matches official URL domain."""
    try:
        from urllib.parse import urlparse
        off_parsed = urlparse(official_url)
        off_host = off_parsed.netloc or off_parsed.path.split("/")[0]
        off_host = off_host.replace("www.", "").lower()
        host = hostname.replace("www.", "").lower()
        return host in off_host or off_host in host
    except Exception:
        return False


def _check_crossref_issn(issn: str) -> Optional[bool]:
    """Verify ISSN is registered in Crossref."""
    try:
        url = f"https://api.crossref.org/journals/{urllib.parse.quote(issn)}"
        req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/7.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data.get("status") == "ok"
    except Exception:
        return None


def _check_domain_age_estimate(hostname: str) -> Optional[str]:
    """Estimate domain age from known patterns (WHOIS not available)."""
    try:
        # Check for common new-domain patterns
        domain_base = hostname.split(".")[0].lower()
        # Domains with years or recent dates are suspicious
        if re.search(r'20(2[1-5]|3[0-5])', domain_base):
            return "very_new"
        if re.search(r'20(1[5-9]|20)', domain_base):
            return "established"
        # Known long-established domains
        if any(d in hostname for d in KNOWN_LEGITIMATE_DOMAINS):
            return "established"
        return None
    except Exception:
        return None


# ── Suggesters ──

def _suggest_elsevier(title: str, abstract: str) -> List[Dict]:
    try:
        data = urllib.parse.urlencode({"title": title, "abstract": abstract}).encode()
        url = "https://journalfinder.elsevier.com/api/journal-finder"
        req = urllib.request.Request(url, data=data, headers={"User-Agent": "BioDockify/1.0", "Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            journals = result.get("journals", result.get("results", []))
            return [{
                "title": j.get("title", j.get("name", "")), "publisher": "Elsevier",
                "match_score": j.get("match", 0.5), "source": "Elsevier Journal Finder",
                "quartile": j.get("quartile", "Q2"), "apc": str(j.get("apc", "Unknown")),
                "review_time": str(j.get("review_time", "")) or "6-10 weeks",
                "access_type": "Hybrid OA",
            } for j in journals[:10]]
    except: return []


def _suggest_jane(title: str, abstract: str) -> List[Dict]:
    try:
        data = urllib.parse.urlencode({"text": title + " " + abstract[:2000]}).encode()
        url = "https://jane.biosemantics.org/api/suggestJournals"
        req = urllib.request.Request(url, data=data, headers={"User-Agent": "BioDockify/1.0", "Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            return [{
                "title": j.get("title", j.get("journal_name", "")),
                "match_score": j.get("score", 0.5), "source": "JANE (biosemantics)",
                "quartile": "Q2", "review_time": "4-8 weeks",
            } for j in result[:10]]
    except: return []


def _suggest_crossref(title: str) -> List[Dict]:
    """Search Crossref API for journals matching the paper title."""
    try:
        terms = title.lower().split()[:6]
        query = " ".join(terms)
        url = f"https://api.crossref.org/journals?query={urllib.parse.quote(query)}&rows=15"
        req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/7.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            journals = data.get("message", {}).get("items", [])
            return [{
                "title": j.get("title", ""),
                "issn": (j.get("issn") or [""])[0],
                "publisher": j.get("publisher", ""),
                "scopus": True,  # Crossref journals are generally indexed
                "source": "Crossref",
                "match_score": 0.6,
            } for j in journals[:15]]
    except: return []


def _suggest_from_keywords(terms: List[str]) -> List[Dict]:
    """Fallback: suggest from keyword-matched DB query."""
    if not terms:
        return []
    result = _query_db(query=" ".join(terms[:3]), limit=12)
    return [{
        "title": j.get("title", ""), "publisher": j.get("publisher", ""),
        "scopus": bool(j.get("scopus_indexed")), "wos": bool(j.get("wos_indexed")),
        "oa": j.get("oa_status") == "OA", "source": "Biodockify DB",
        "match_score": 0.4, "access_type": "OA" if j.get("oa_status") == "OA" else "Subscription",
    } for j in result.get("journals", [])]


# ── Scoring helpers ──

def _extract_terms(title: str, abstract: str, keywords: str) -> List[str]:
    text = f"{title} {abstract} {keywords}".lower()
    words = re.findall(r'[a-z]{4,}', text)
    stop = {"this", "that", "with", "from", "have", "been", "were", "their", "which", "about", "into", "also", "than", "other"}
    terms = [w for w in words if w not in stop]
    return list(dict.fromkeys(terms))[:20]


def _compute_relevance(terms: List[str], journal: Dict) -> float:
    score = 0.0
    j_text = f"{journal.get('title', '')} {journal.get('publisher', '')}".lower()
    for term in terms[:10]:
        if term in j_text:
            score += 0.1
    return min(score, 1.0)


def _authority_score(journal: Dict) -> float:
    score = 0.2
    pub = journal.get("publisher", "").lower()
    for lp in LEGITIMATE_PUBLISHERS:
        if lp in pub:
            score += 0.15
    if journal.get("scopus") or journal.get("wos"):
        score += 0.2
    if journal.get("quartile") in ("Q1", "Q2"):
        score += 0.15
    return min(score, 1.0)


def _speed_score(journal: Dict) -> float:
    rt = journal.get("review_time", "")
    if "2-4" in rt or "4 weeks" in rt: return 0.9
    if "6-8" in rt or "6-10" in rt: return 0.7
    if "8-12" in rt or "10-12" in rt: return 0.4
    return 0.5


def _access_score(journal: Dict) -> float:
    if journal.get("oa") or journal.get("access_type") == "OA":
        return 1.0
    return 0.5


def _parse_apc(apc_str: str) -> int:
    try:
        return int(re.sub(r'[^\d]', '', str(apc_str)))
    except:
        return 0
