"""Journal Finder API — unified search, verify, profile, history, recommend."""
from helpers.api import ApiHandler, Request, Response
import logging

logger = logging.getLogger("journal_finder")


class JournalFinder(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        action = (input.get("action") or input.get("mode") or "search").strip()
        actions = {
            "search": self._search, "verify": self._verify,
            "profile": self._profile, "history": self._history,
            "suggest": self._suggest, "stats": self._stats,
        }
        handler = actions.get(action, self._search)
        return handler(input)

    def _search(self, input: dict) -> dict:
        from modules.journal_intel import _query_db
        query = input.get("query", "").strip()
        scopus = input.get("scopus")
        wos = input.get("wos")
        oa = input.get("oa")
        subject = input.get("subject", "").strip()
        limit = min(int(input.get("limit", 25)), 100)
        offset = int(input.get("offset", 0))
        result = _query_db(query=query, scopus=scopus, wos=wos, oa=oa, subject=subject, limit=limit, offset=offset)
        return {"status": "ok", "action": "search", **result}

    def _verify(self, input: dict) -> dict:
        from modules.journal_intel import DecisionEngine
        title = input.get("title", "").strip()
        issn = input.get("issn", "").strip()
        if not title and not issn:
            return {"status": "error", "error": "Provide journal title or ISSN"}
        engine = DecisionEngine()
        result = engine.verify(title=title, issn=issn)
        return {"status": "ok", "action": "verify", **result}

    def _profile(self, input: dict) -> dict:
        from modules.journal_intel import DecisionEngine
        issn = input.get("issn", "").strip()
        title = input.get("title", "").strip()
        if not issn and not title:
            return {"status": "error", "error": "Provide ISSN or journal title"}
        engine = DecisionEngine()
        result = engine.profile(issn=issn, title=title)
        return {"status": "ok", "action": "profile", **result}

    def _history(self, input: dict) -> dict:
        from modules.journal_intel import DecisionEngine
        title = input.get("title", "").strip()
        if not title:
            return {"status": "error", "error": "Journal title required"}
        engine = DecisionEngine()
        result = engine.history(title=title)
        return {"status": "ok", "action": "history", **result}

    def _suggest(self, input: dict) -> dict:
        from modules.journal_intel import DecisionEngine
        title = input.get("title", input.get("sTitle", "")).strip()
        abstract = input.get("abstract", input.get("sAbstract", "")).strip()
        keywords = input.get("keywords", input.get("sKeywords", "")).strip()
        oa_only = input.get("oa_only", input.get("sOaOnly", False))
        max_apc = int(input.get("max_apc", 0))
        q_min = input.get("q_min", input.get("sQMin", "")).strip()
        if not title:
            return {"status": "error", "error": "Article title required"}
        engine = DecisionEngine()
        suggestions = engine.suggest(title=title, abstract=abstract, keywords=keywords, oa_only=oa_only, max_apc=max_apc, q_min=q_min)
        return {"status": "ok", "action": "suggest", "suggestions": suggestions, "count": len(suggestions)}

    def _stats(self, input: dict) -> dict:
        from modules.journal_intel import _query_db
        result = _query_db(limit=1)
        return {
            "status": "ok", "action": "stats",
            "total_journals": result.get("db_total", 0),
            "scopus_indexed": result.get("scopus_count", 0),
            "wos_indexed": result.get("wos_count", 0),
            "open_access": result.get("oa_count", 0),
            "database": "Scopus (Mar 2025) + WoS (Mar 2024)",
        }
