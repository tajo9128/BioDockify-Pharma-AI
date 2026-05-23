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

        # Source 1: DB keyword search
        db_result = _query_db(query=" ".join(terms[:3]), limit=20)
        for j in db_result.get("journals", []):
            suggestions.append({
                "title": j.get("title", ""),
                "issn": j.get("issn", ""),
                "publisher": j.get("publisher", ""),
                "scopus": bool(j.get("scopus_indexed")),
                "wos": bool(j.get("wos_indexed")),
                "oa": j.get("oa_status") == "OA",
                "source": "Biodockify DB",
                "match_score": 0.5,
            })

        # Source 2: Elsevier Journal Finder
        elsevier = _suggest_elsevier(title, abstract)
        suggestions.extend(elsevier)

        # Source 3: JANE biosemantics
        jane = _suggest_jane(title, abstract)
        suggestions.extend(jane)

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
            suggestions = [s for s in suggestions if s.get("access_type") == "OA"]
        if max_apc > 0:
            suggestions = [s for s in suggestions if _parse_apc(s.get("apc", "")) <= max_apc]
        if q_min:
            q_order = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}
            suggestions = [s for s in suggestions if q_order.get(s.get("quartile", "Q4"), 4) <= q_order.get(q_min, 4)]

        suggestions.sort(key=lambda s: -s.get("match_score", 0))
        return suggestions[:15]

    def profile(self, issn: str = "", title: str = "") -> Dict:
        """Comprehensive journal profile from DB + live enrichment."""
        if not issn and not title:
            return {"error": "Provide ISSN or title"}

        db_entry = _db_lookup(issn=issn, title=title)
        if not db_entry:
            return {"error": f"Journal not found in database (36,145 journals)", "detail": "Try verifying with live APIs instead"}

        profile = {
            "title": db_entry.get("title", ""),
            "issn": db_entry.get("issn", ""),
            "eissn": db_entry.get("eissn", ""),
            "publisher": db_entry.get("publisher", ""),
            "oa_status": db_entry.get("oa_status", ""),
            "scopus_indexed": bool(db_entry.get("scopus_indexed")),
            "wos_indexed": bool(db_entry.get("wos_indexed")),
            "scopus_subjects": db_entry.get("scopus_subjects", ""),
            "wos_categories": db_entry.get("wos_categories", ""),
            "asjc_codes": db_entry.get("asjc_codes", ""),
            "source_type": db_entry.get("source_type", ""),
        }

        # Enrich with live verification
        ver = self.verify(title=profile["title"], issn=profile.get("issn", ""))
        profile["verification"] = {
            "verdict": ver.get("verdict"),
            "confidence": ver.get("confidence"),
            "flags": ver.get("predatory_flags", []),
            "indexing_verified": {k: bool(v.get("indexed")) for k, v in ver.get("indexing", {}).items()},
        }

        # Check hijacked
        hijacked = _check_hijacked(profile["title"])
        profile["hijacked"] = {"flagged": len(hijacked) > 0, "details": hijacked}

        # Live metrics attempt
        scimago = _check_scimago(profile["title"], profile.get("issn", ""))
        if scimago and scimago.get("quartile"):
            profile["metrics"] = {"quartile": scimago.get("quartile"), "source": "SCImago"}

        # DOAJ info
        doaj = _check_doaj(profile["title"], profile.get("issn", ""))
        if doaj:
            profile["oa_policy"] = doaj

        return profile

    def history(self, title: str = "") -> Dict:
        """Research a journal's history — metrics timeline, publisher history, editorial details."""
        if not title:
            return {"error": "Journal title required"}
        result = {
            "title": title,
            "db_profile": None,
            "verification": None,
            "research_instructions": [],
        }
        db_entry = _db_lookup(title=title)
        if db_entry:
            result["db_profile"] = {
                "publisher": db_entry.get("publisher"),
                "scopus": bool(db_entry.get("scopus_indexed")),
                "wos": bool(db_entry.get("wos_indexed")),
                "subjects": db_entry.get("scopus_subjects"),
            }
        ver = self.verify(title=title)
        result["verification"] = ver

        # Instructions for agent to do deeper research
        issn = db_entry.get("issn", "") if db_entry else ""
        result["research_instructions"] = [
            f"Search SCImago for {title} SJR trend: https://www.scimagojr.com/journalsearch.php?q={urllib.parse.quote(title)}",
            f"Check JCR Impact Factor: https://jcr.clarivate.com (search {issn or title})",
            f"Search DOAJ for OA policy: https://doaj.org/search/journals/{urllib.parse.quote(title)}",
            f"Check Researcher.life for review speed: https://researcher.life/journal/{urllib.parse.quote(title.replace(' ', '-').lower())}",
            f"PubMed search for recent articles: https://pubmed.ncbi.nlm.nih.gov/?term={urllib.parse.quote(title)}[journal]",
            f"Google Scholar metrics: https://scholar.google.com/citations?view_op=search_journals&hl=en&mauthors={urllib.parse.quote(title)}",
        ]
        return result


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
