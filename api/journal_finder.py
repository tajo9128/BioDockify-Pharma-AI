"""Journal Finder API - Verify journals and suggest where to publish."""
from helpers.api import ApiHandler, Request
import logging

logger = logging.getLogger("journal_finder")


class JournalFinder(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        mode = (input.get("mode", "verify") or "verify").strip()

        if mode == "verify":
            return self._verify(input)
        elif mode == "suggest":
            return self._suggest(input)
        else:
            return {"modes": ["verify", "suggest"], "hint": "Use mode=verify or mode=suggest"}

    def _verify(self, input: dict) -> dict:
        title = (input.get("title", "") or "").strip()
        issn = (input.get("issn", "") or "").strip()

        if not title and not issn:
            return {"error": "Provide journal title or ISSN"}

        try:
            from modules.journal_intel import DecisionEngine
            engine = DecisionEngine()
            result = engine.verify(title=title, issn=issn)
            return result
        except ImportError as e:
            return {"error": f"Journal intelligence module not available: {e}"}

    def _suggest(self, input: dict) -> dict:
        title = (input.get("title", "") or "").strip()
        abstract = (input.get("abstract", "") or "").strip()
        keywords = (input.get("keywords", "") or "").strip()
        oa_only = input.get("oa_only", False)
        max_apc = int(input.get("max_apc", 0) or 0)
        q_min = input.get("q_min", "").strip()

        if not title:
            return {"error": "Article title required for journal suggestion"}

        try:
            from modules.journal_intel import DecisionEngine
            engine = DecisionEngine()
            journals = engine.suggest(
                title=title, abstract=abstract, keywords=keywords,
                oa_only=oa_only, max_apc=max_apc, q_min=q_min
            )
            return {
                "mode": "suggest",
                "title": title,
                "count": len(journals),
                "journals": journals,
            }
        except ImportError as e:
            return {"error": f"Journal intelligence module not available: {e}"}
