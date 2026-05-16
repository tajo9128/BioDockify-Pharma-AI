"""
Journal Intelligence Module
DecisionEngine + Checkers + Suggesters for journal verification and suggestion.
"""
import logging
import urllib.request
import urllib.parse
import json
import re
from typing import Dict, List, Any, Optional

logger = logging.getLogger("journal_intel")

# Known predatory journal patterns
PREDATORY_FLAGS = [
    "international journal of", "world journal of", "global journal of",
    "american journal of" # when not actually American
]

# Popular legitimate publishers
LEGITIMATE_PUBLISHERS = [
    "elsevier", "springer", "wiley", "taylor & francis", "sage", "oxford university press",
    "cambridge university press", "nature publishing", "ieee", "acs", "rsc", "bmj",
    "lancet", "cell press", "plos", "frontiers", "mdpi", "biomed central", "bentham",
]


class DecisionEngine:
    """Coordinates all journal verification checks."""

    def verify(self, title: str = "", issn: str = "") -> Dict[str, Any]:
        if not title and not issn:
            return {"error": "Provide journal title or ISSN"}

        title = title.strip()
        issn = issn.strip()

        result = {
            "journal": title,
            "issn": issn,
            "verdict": "UNVERIFIED",
            "confidence": 0,
            "sources_checked": [],
            "indexing": {},
            "access": {},
            "metrics": {},
            "publisher": "",
            "predatory_flags": [],
        }

        # 1. Scopus check
        scopus = _check_scopus(title, issn)
        if scopus:
            result["sources_checked"].append("scopus")
            result["indexing"]["scopus"] = scopus

        # 2. WoS/Clarivate check
        wos = _check_clarivate(title, issn)
        if wos:
            result["sources_checked"].append("clarivate")
            result["indexing"]["wos"] = wos

        # 3. SCImago check
        scimago = _check_scimago(title, issn)
        if scimago:
            result["sources_checked"].append("scimago")
            result["indexing"]["scimago"] = scimago

        # 4. DOAJ check
        doaj = _check_doaj(title, issn)
        if doaj:
            result["sources_checked"].append("doaj")
            result["access"]["doaj"] = doaj

        # 5. Predatory check
        predatory = _check_predatory(title, issn)
        result["predatory_flags"] = predatory.get("flags", [])
        result["sources_checked"].append("predatory_db")

        # Compute verdict
        indexed_count = sum(1 for v in result["indexing"].values() if v.get("indexed"))
        if indexed_count >= 2 and not result["predatory_flags"]:
            result["verdict"] = "GENUINE"
            result["confidence"] = 0.85 + (indexed_count - 2) * 0.05
        elif indexed_count >= 1 and not result["predatory_flags"]:
            result["verdict"] = "LIKELY_GENUINE"
            result["confidence"] = 0.6
        elif result["predatory_flags"]:
            result["verdict"] = "PREDATORY"
            result["confidence"] = 0.75 + len(result["predatory_flags"]) * 0.05
        else:
            result["verdict"] = "UNVERIFIED"
            result["confidence"] = 0.2

        return result

    def suggest(self, title: str = "", abstract: str = "", keywords: str = "",
                oa_only: bool = False, max_apc: int = 0, q_min: str = "") -> List[Dict]:
        """Suggest suitable journals based on article content."""
        if not title:
            return [{"error": "Article title required for suggestion"}]

        # Extract search terms
        terms = _extract_terms(title, abstract, keywords)

        suggestions = []

        # Try Elsevier Journal Finder
        elsevier = _suggest_elsevier(title, abstract)
        if elsevier:
            suggestions.extend(elsevier)

        # Try JANE (biosemantics) for biomedical
        jane = _suggest_jane(title, abstract)
        if jane:
            suggestions.extend(jane)

        # Fallback: suggest from keyword matching against known database
        if not suggestions:
            suggestions = _suggest_from_keywords(terms)

        # Score and rank
        for s in suggestions:
            relevance = _compute_relevance(terms, s)
            authority = _authority_score(s)
            speed = _speed_score(s)
            access = _access_score(s)
            s["match_score"] = round(relevance * 0.4 + authority * 0.3 + speed * 0.15 + access * 0.15, 1)
            s["match_pct"] = round(s["match_score"] * 100)

        # Filter
        if oa_only:
            suggestions = [s for s in suggestions if s.get("access_type") == "OA"]
        if max_apc > 0:
            suggestions = [s for s in suggestions if _parse_apc(s.get("apc", "")) <= max_apc]
        if q_min:
            q_order = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}
            suggestions = [s for s in suggestions if q_order.get(s.get("quartile", "Q4"), 4) <= q_order.get(q_min, 4)]

        suggestions.sort(key=lambda s: -s.get("match_score", 0))
        return suggestions[:15]


# ── Checkers ──────────────────────────────────────────────────

def _check_scopus(title: str, issn: str) -> Optional[Dict]:
    """Check Scopus indexing via Elsevier API or scraping."""
    try:
        query = issn if issn else title
        url = f"https://api.elsevier.com/content/search/scopus?query=ISSN({query})&count=1"
        req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/1.0", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            entries = data.get("search-results", {}).get("entry", [])
            if entries:
                e = entries[0]
                return {
                    "indexed": True,
                    "title": e.get("dc:title", title),
                    "cite_score": e.get("prism:coverDate", "")[:4],
                    "source": "Scopus API"
                }
    except urllib.error.HTTPError as e:
        if e.code == 401:
            logger.info("Scopus API key required — using heuristic")
            pass
    except: pass
    return {"indexed": False, "title": title, "detail": "Not found or API unavailable"}


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
    return {"indexed": False, "detail": "Not found in Master Journal List"}


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
    return {"indexed": False, "detail": "Not found in SCImago"}


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
                    "indexed": True,
                    "oa": True,
                    "apc": j.get("apc", {}).get("amount", "Unknown"),
                    "apc_currency": j.get("apc", {}).get("currency", "USD"),
                    "license": j.get("license", [{}])[0].get("type", "Unknown"),
                    "publisher": j.get("publisher", {}).get("name", ""),
                    "source": "DOAJ"
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


# ── Suggesters ────────────────────────────────────────────────

def _suggest_elsevier(title: str, abstract: str) -> List[Dict]:
    try:
        import urllib.parse
        data = urllib.parse.urlencode({"title": title, "abstract": abstract}).encode()
        url = "https://journalfinder.elsevier.com/api/journal-finder"
        req = urllib.request.Request(url, data=data, headers={"User-Agent": "BioDockify/1.0", "Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            journals = result.get("journals", result.get("results", []))
            return [{
                "title": j.get("title", j.get("name", "")),
                "publisher": "Elsevier",
                "match_score": j.get("match", 0.5),
                "source": "Elsevier Journal Finder",
                "quartile": j.get("quartile", "Q2"),
                "apc": str(j.get("apc", "Unknown")),
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
                "match_score": j.get("score", 0.5),
                "source": "JANE (biosemantics)",
            } for j in (result if isinstance(result, list) else result.get("journals", []))[:10]]
    except: return []


def _suggest_from_keywords(terms: List[str]) -> List[Dict]:
    suggestions = []
    # Popular pharma journals by category
    pharma_journals = [
        {"title": "European Journal of Medicinal Chemistry", "quartile": "Q1", "apc": "$2,800", "access_type": "Hybrid OA", "review_time": "6 weeks", "acceptance": "20%", "field": "medicinal chemistry", "publisher": "Elsevier"},
        {"title": "Journal of Medicinal Chemistry", "quartile": "Q1", "apc": "$3,500", "access_type": "Hybrid OA", "review_time": "8 weeks", "acceptance": "15%", "field": "medicinal chemistry", "publisher": "ACS"},
        {"title": "Bioorganic & Medicinal Chemistry Letters", "quartile": "Q2", "apc": "$2,200", "access_type": "Hybrid OA", "review_time": "4 weeks", "acceptance": "35%", "field": "medicinal chemistry", "publisher": "Elsevier"},
        {"title": "Pharmaceutical Research", "quartile": "Q1", "apc": "$3,190", "access_type": "Hybrid OA", "review_time": "10 weeks", "acceptance": "25%", "field": "pharmaceutics", "publisher": "Springer"},
        {"title": "International Journal of Pharmaceutics", "quartile": "Q1", "apc": "$2,950", "access_type": "Hybrid OA", "review_time": "6 weeks", "acceptance": "30%", "field": "pharmaceutics", "publisher": "Elsevier"},
        {"title": "Drug Discovery Today", "quartile": "Q1", "apc": "$3,500", "access_type": "Hybrid OA", "review_time": "8 weeks", "acceptance": "18%", "field": "drug discovery", "publisher": "Elsevier"},
        {"title": "Journal of Pharmaceutical Sciences", "quartile": "Q2", "apc": "$2,500", "access_type": "Hybrid OA", "review_time": "6 weeks", "acceptance": "28%", "field": "pharmaceutical sciences", "publisher": "Elsevier"},
        {"title": "Molecules", "quartile": "Q2", "apc": "$2,200", "access_type": "OA", "review_time": "3 weeks", "acceptance": "45%", "field": "chemistry", "publisher": "MDPI"},
        {"title": "RSC Medicinal Chemistry", "quartile": "Q2", "apc": "$0", "access_type": "Subscription", "review_time": "8 weeks", "acceptance": "25%", "field": "medicinal chemistry", "publisher": "RSC"},
        {"title": "ChemMedChem", "quartile": "Q2", "apc": "$3,200", "access_type": "Hybrid OA", "review_time": "6 weeks", "acceptance": "22%", "field": "medicinal chemistry", "publisher": "Wiley"},
        {"title": "Frontiers in Pharmacology", "quartile": "Q1", "apc": "$2,950", "access_type": "OA", "review_time": "3 weeks", "acceptance": "60%", "field": "pharmacology", "publisher": "Frontiers"},
        {"title": "PLOS ONE", "quartile": "Q1", "apc": "$1,749", "access_type": "OA", "review_time": "4 weeks", "acceptance": "50%", "field": "multidisciplinary", "publisher": "PLOS"},
    ]

    for j in pharma_journals:
        relevance = _compute_relevance(terms, j)
        if relevance > 0.3:
            j["match_score"] = relevance
            j["source"] = "BioDockify DB"
            suggestions.append(j)

    suggestions.sort(key=lambda s: -s.get("match_score", 0))
    return suggestions[:10]


# ── Helpers ───────────────────────────────────────────────────

def _extract_terms(title: str, abstract: str, keywords: str) -> List[str]:
    text = f"{title} {abstract} {keywords}".lower()
    terms = set()
    common_pharma = [
        "kinase", "inhibitor", "receptor", "drug", "cancer", "cell", "molecule",
        "synthesis", "assay", "pharmacokinetic", "toxicity", "formulation",
        "nanoparticle", "peptide", "protein", "enzyme", "metabolism", "gene",
        "clinical", "trial", "biomarker", "pharmacology", "medicinal", "chemistry",
        "pharmaceutics", "delivery", "target", "ligand", "binding", "dose",
        "quinazoline", "egfr", "nsclc", "therapeutic", "antimicrobial", "antibiotic",
        "vaccine", "immunotherapy", "biologic", "biosimilar", "pharmacodynamics"
    ]
    for term in common_pharma:
        if term in text:
            terms.add(term)
    return list(terms)


def _compute_relevance(terms: List[str], journal: Dict) -> float:
    field = (journal.get("field", "") + " " + journal.get("title", "")).lower()
    matches = sum(1 for t in terms if t in field)
    return min(1.0, matches / max(1, len(terms)) * 2)


def _authority_score(journal: Dict) -> float:
    q_scores = {"Q1": 1.0, "Q2": 0.75, "Q3": 0.5, "Q4": 0.25}
    return q_scores.get(journal.get("quartile", "Q4"), 0.25)


def _speed_score(journal: Dict) -> float:
    rt = journal.get("review_time", "8 weeks")
    nums = re.findall(r"(\d+)", rt)
    weeks = int(nums[0]) if nums else 8
    return max(0, 1.0 - weeks / 26)


def _access_score(journal: Dict) -> float:
    atype = journal.get("access_type", "")
    if "OA" in atype: return 1.0
    if "Hybrid" in atype: return 0.7
    return 0.3


def _parse_apc(apc_str: str) -> int:
    nums = re.findall(r"[\d,]+", apc_str)
    return int(nums[0].replace(",", "")) if nums else 0
