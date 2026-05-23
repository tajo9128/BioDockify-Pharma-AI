from helpers.tool import Tool, Response


class JournalRecommenderTool(Tool):

    async def execute(self, action="search", **kwargs):
        action = (action or "search").strip()

        if action == "search":
            return await self._action_search(**kwargs)
        elif action == "verify":
            return await self._action_verify(**kwargs)
        elif action == "profile":
            return await self._action_profile(**kwargs)
        elif action == "recommend":
            return await self._action_recommend(**kwargs)
        elif action == "history":
            return await self._action_history(**kwargs)
        elif action == "stats":
            return await self._action_stats(**kwargs)
        else:
            return Response(
                message=f"Unknown action: {action}. Use search, verify, profile, recommend, history, or stats.",
                break_loop=False,
            )

    async def _action_search(self, **kwargs):
        query = kwargs.get("query", kwargs.get("keywords", ""))
        scopus = kwargs.get("scopus_only")
        wos = kwargs.get("wos_only")
        oa = kwargs.get("open_access")
        subject = kwargs.get("subject", "")
        limit = int(kwargs.get("limit", 25))

        from modules.journal_intel import _query_db
        result = _query_db(query=query, scopus=scopus, wos=wos, oa=oa, subject=subject, limit=min(limit, 30))

        if result.get("error"):
            return Response(message=f"Database error: {result['error']}", break_loop=False)

        journals = result.get("journals", [])
        total = result.get("total", 0)
        lines = [f"Journal Search Results ({total} total, showing {len(journals)}):", ""]
        for i, j in enumerate(journals, 1):
            idx = "S+W" if j.get("scopus_indexed") and j.get("wos_indexed") else "S" if j.get("scopus_indexed") else "W" if j.get("wos_indexed") else "—"
            oa_tag = " [OA]" if j.get("oa_status") == "OA" else ""
            lines.append(f"{i}. {j.get('title', '')} ({j.get('issn', '')}) — {j.get('publisher', '')} [{idx}]{oa_tag}")
            if j.get("scopus_subjects"):
                lines.append(f"   Subjects: {j['scopus_subjects'][:120]}")
        lines.append("")
        lines.append(f"To get full details on any journal, use action=profile with the ISSN.")
        return Response(message="\n".join(lines), break_loop=False)

    async def _action_verify(self, **kwargs):
        title = kwargs.get("title", "")
        issn = kwargs.get("issn", "")
        if not title and not issn:
            return Response(message="Provide journal title or ISSN to verify.", break_loop=False)

        from modules.journal_intel import DecisionEngine
        engine = DecisionEngine()
        result = engine.verify(title=title, issn=issn)

        lines = [f"Journal Verification: {result.get('journal', title)}"]
        lines.append(f"Verdict: {result.get('verdict')} (confidence: {result.get('confidence', 0):.0%})")
        indexing = result.get("indexing", {})
        for source, data in indexing.items():
            status = "Indexed" if data.get("indexed") else "Not found"
            lines.append(f"  {source.upper()}: {status}")
        access = result.get("access", {})
        doaj_info = access.get("doaj", {})
        if doaj_info:
            lines.append(f"  DOAJ: OA, APC {doaj_info.get('apc', 'N/A')} {doaj_info.get('apc_currency', 'USD')}")
        flags = result.get("predatory_flags", [])
        if flags:
            lines.append("WARNING — Predatory flags:")
            for f in flags:
                lines.append(f"  - {f}")
        lines.append("")
        lines.append("Sources checked: " + ", ".join(result.get("sources_checked", [])))
        return Response(message="\n".join(lines), break_loop=False)

    async def _action_profile(self, **kwargs):
        issn = kwargs.get("issn", "")
        title = kwargs.get("title", "")
        if not issn and not title:
            return Response(message="Provide ISSN or journal title.", break_loop=False)

        from modules.journal_intel import DecisionEngine
        engine = DecisionEngine()
        result = engine.profile(issn=issn, title=title)

        if result.get("error"):
            return Response(message=f"Journal not found: {result.get('detail', result['error'])}. Try action=verify for live API check.", break_loop=False)

        lines = [f"Journal Profile: {result.get('title', '')}"]
        lines.append(f"Publisher: {result.get('publisher', 'N/A')}")
        lines.append(f"ISSN: {result.get('issn', 'N/A')} | eISSN: {result.get('eissn', 'N/A')}")
        lines.append(f"Scopus: {'Yes' if result.get('scopus_indexed') else 'No'} | WoS: {'Yes' if result.get('wos_indexed') else 'No'}")
        lines.append(f"OA Status: {result.get('oa_status', 'N/A')}")
        if result.get("scopus_subjects"):
            lines.append(f"Subjects: {result['scopus_subjects'][:200]}")
        ver = result.get("verification", {})
        lines.append(f"Verification: {ver.get('verdict', 'N/A')} (confidence {ver.get('confidence', 0):.0%})")
        hijacked = result.get("hijacked", {})
        if hijacked.get("flagged"):
            lines.append(f"WARNING: Hijacked journal detected! {hijacked.get('details', [])}")
        metrics = result.get("metrics", {})
        if metrics:
            lines.append(f"SCImago Quartile: {metrics.get('quartile', 'N/A')}")
        oa_policy = result.get("oa_policy", {})
        if oa_policy and oa_policy.get("apc"):
            lines.append(f"APC: {oa_policy.get('apc', 'N/A')} {oa_policy.get('apc_currency', 'USD')} | License: {oa_policy.get('license', 'N/A')}")
        return Response(message="\n".join(lines), break_loop=False)

    async def _action_recommend(self, **kwargs):
        title = kwargs.get("title", "")
        abstract = kwargs.get("abstract", "")
        keywords = kwargs.get("keywords", "")
        if not title:
            return Response(message="Provide article title to get journal recommendations.", break_loop=False)

        from modules.journal_intel import DecisionEngine
        engine = DecisionEngine()
        suggestions = engine.suggest(title=title, abstract=abstract, keywords=keywords)

        if not suggestions or (len(suggestions) == 1 and suggestions[0].get("error")):
            return Response(message=f"No suggestions found: {suggestions[0].get('error', 'unknown')}", break_loop=False)

        lines = [f"Journal Recommendations for: {title[:80]}"]
        lines.append(f"Found {len(suggestions)} potential journals:")
        lines.append("")
        for i, s in enumerate(suggestions[:12], 1):
            idx_tags = []
            if s.get("scopus"): idx_tags.append("Scopus")
            if s.get("wos"): idx_tags.append("WoS")
            idx_str = "+".join(idx_tags) if idx_tags else "Unindexed"
            lines.append(f"{i}. {s.get('title', 'N/A')}")
            lines.append(f"   Publisher: {s.get('publisher', 'N/A')} | Index: {idx_str}")
            lines.append(f"   Match: {s.get('match_pct', 0)}% | Quartile: {s.get('quartile', 'N/A')} | Source: {s.get('source', 'N/A')}")
        lines.append("")
        lines.append("To verify any of these journals: use action=verify with the journal title or ISSN.")
        lines.append("To get a full profile: use action=profile with the ISSN.")
        return Response(message="\n".join(lines), break_loop=False)

    async def _action_history(self, **kwargs):
        title = kwargs.get("title", "")
        if not title:
            return Response(message="Provide journal title for history research.", break_loop=False)

        from modules.journal_intel import DecisionEngine
        engine = DecisionEngine()
        result = engine.history(title=title)

        lines = [f"Journal History Research: {title}"]
        lines.append("")
        db = result.get("db_profile")
        if db:
            lines.append(f"Database: Publisher={db.get('publisher', 'N/A')}, Scopus={db.get('scopus')}, WoS={db.get('wos')}")
        ver = result.get("verification", {})
        lines.append(f"Verification: {ver.get('verdict', 'N/A')} ({ver.get('confidence', 0):.0%} confidence)")
        lines.append("")
        lines.append("Research your journal deeper using these links:")
        for instr in result.get("research_instructions", []):
            lines.append(f"  - {instr}")
        lines.append("")
        lines.append("To scrape detailed metrics from these sources, use the SearchEngine tool or call_subordinate Hacker agent to extract acceptance rate, review timeline, and impact factor data.")
        return Response(message="\n".join(lines), break_loop=False)

    async def _action_stats(self, **kwargs):
        from modules.journal_intel import _query_db
        result = _query_db(limit=1)
        lines = [
            "Journal Database Statistics",
            f"Total journals: {result.get('db_total', 0):,}",
            f"Scopus-indexed: {result.get('scopus_count', 0):,}",
            f"WoS-indexed: {result.get('wos_count', 0):,}",
            f"Open Access: {result.get('oa_count', 0):,}",
            "Database: Scopus (Mar 2025) + WoS (Mar 2024)",
            "",
            "Use action=search to query the database.",
        ]
        return Response(message="\n".join(lines), break_loop=False)
