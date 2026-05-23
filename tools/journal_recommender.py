"""Journal Recommender Tool — agent recommends Scopus/WoS journals for a paper."""
from helpers.tool import Tool, Response


class JournalRecommenderTool(Tool):
    async def execute(self, action: str = "search", **kwargs):
        if action == "search":
            query = kwargs.get("query", kwargs.get("keywords", ""))
            subject = kwargs.get("subject", kwargs.get("field", ""))
            lines = [f"=== JOURNAL RECOMMENDER ===", f"Query: {query or '(all)'}", f"Subject: {subject or '(all)'}", "=" * 45]
            lines.append("")
            lines.append("Call POST /api/journal_recommender action=search with your criteria.")
            lines.append("")
            lines.append("Filters available:")
            lines.append("  scopus=true — Scopus indexed only")
            lines.append("  wos=true — WoS indexed only")
            lines.append("  oa=Open Access — Open Access only")
            lines.append("  subject=Oncology — match by ASJC/WoS category")
            lines.append("")
            lines.append("Database: 36,145 journals from Scopus (Mar 2025) + WoS (Mar 2024)")
            return Response(message="\n".join(lines), break_loop=False)

        if action == "recommend":
            abstract = kwargs.get("abstract", "")
            if not abstract:
                return Response(message="Provide paper abstract. Use: JournalRecommender action=recommend abstract=\"...\"", break_loop=False)
            lines = ["=== JOURNAL RECOMMENDATION ===", "=" * 45]
            lines.append("1. Extract keywords and field from the abstract")
            lines.append("2. Query database for matching journals")
            lines.append("3. Filter by indexing preference (Scopus/WoS/dual)")
            lines.append("4. Filter by OA preference")
            lines.append("5. Quality-score the paper (novelty, rigor, breadth, evidence, clarity)")
            lines.append("6. Rank journals by tier (Ambitious/Target/Safe)")
            lines.append("")
            lines.append("Call POST /api/journal_recommender action=search with extracted keywords.")
            return Response(message="\n".join(lines), break_loop=False)

        if action == "info":
            lines = ["=== JOURNAL RECOMMENDER DATABASE ===", "=" * 45]
            lines.append("36,145 journals from:")
            lines.append("  - Scopus Source List (March 2025)")
            lines.append("  - Web of Science Master List (March 2024)")
            lines.append("")
            lines.append("Actions: search, recommend, info, stats, subjects")
            lines.append("Filters: scopus, wos, oa, subject, query")
            return Response(message="\n".join(lines), break_loop=False)

        if action == "stats":
            return Response(message="Call POST /api/journal_recommender action=stats for database statistics.", break_loop=False)

        return Response(message="JournalRecommender actions: search, recommend, info, stats, subjects", break_loop=False)
