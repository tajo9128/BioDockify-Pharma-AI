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
            "deep_research": self._deep_research,
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

    def _deep_research(self, input: dict) -> dict:
        """Trigger the full BioDockify research pipeline for a journal."""
        import threading
        title = input.get("title", "").strip()
        issn = input.get("issn", "").strip()
        if not title:
            return {"status": "error", "error": "Journal title required"}

        topic = f"Comprehensive Deep Research on Academic Journal: {title}" + (f" (ISSN: {issn})" if issn else "")
        research_prompt = (
            f"Conduct exhaustive deep research on the academic journal '{title}'{issn and f' (ISSN: {issn})' or ''}.\n\n"
            f"Search and compile:\n"
            f"1. Founding year, original name, any name changes, publisher history\n"
            f"2. Current indexing: Scopus, Web of Science, DOAJ, PubMed, SCImago quartile\n"
            f"3. Impact Factor history (last 5 years), SJR trend, h-index, Google Scholar h5-index\n"
            f"4. Peer review process: acceptance rate, average review time, editorial board members\n"
            f"5. Total articles published, publication frequency, special issues\n"
            f"6. Open Access policy: APC costs, embargo periods, Creative Commons license type\n"
            f"7. Any controversies, retractions, predatory journal flags, Cabell's blacklist status\n"
            f"8. Comparison with 2-3 competing journals in the same field\n"
            f"9. Scimago Journal Rank trend over past 5 years\n"
            f"10. Final recommendation: suitable for submission? (with reasoning)\n\n"
            f"Sources to consult: SCImago, DOAJ API, PubMed, Google Scholar, Clarivate Master Journal List, "
            f"Researcher.life, Scilit, Crossref API, Retraction Watch database."
        )

        try:
            from orchestration.planner.orchestrator import ResearchOrchestrator, OrchestratorConfig
            config = OrchestratorConfig(use_cloud_api=False)
            orchestrator = ResearchOrchestrator(config)

            def _run():
                try:
                    orchestrator.run(title=title, topic=research_prompt, source="journal_finder")
                except Exception as e:
                    logger.warning(f"Research pipeline for '{title}' failed: {e}")

            t = threading.Thread(target=_run, daemon=True)
            t.start()
            return {
                "status": "ok", "action": "deep_research",
                "message": f"Deep research pipeline started for: {title}",
                "research_active": True,
            }
        except ImportError as e:
            logger.warning(f"Research orchestrator not available: {e}")
            return {
                "status": "ok", "action": "deep_research",
                "message": f"Research prompt generated for Agent Zero chat",
                "research_active": False,
                "prompt": research_prompt,
            }
