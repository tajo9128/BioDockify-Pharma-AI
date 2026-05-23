"""Evolution Tool — agent stores and retrieves cross-run pharma knowledge."""
from helpers.tool import Tool, Response


class EvolutionTool(Tool):
    async def execute(self, action: str = "store", **kwargs):
        if action == "store":
            category = kwargs.get("category", "target")
            lesson = kwargs.get("lesson", "")
            if not lesson:
                return Response(message="Provide category and lesson. Use: Evolution action=store category=target lesson=\"Strong binding for EGFR with -9.5\"", break_loop=False)
            lines = [f"=== KNOWLEDGE EVOLUTION: STORE ===", f"Category: {category}", f"Lesson: {lesson[:200]}", "=" * 40]
            lines.append("Call POST /api/evolution action=store to save this lesson.")
            lines.append("Categories: target, compound, method, literature, failure, quality")
            return Response(message="\n".join(lines), break_loop=False)

        if action == "query":
            category = kwargs.get("category", "target")
            context = kwargs.get("context", "")
            lines = [f"=== KNOWLEDGE EVOLUTION: QUERY ===", f"Category: {category}", "=" * 40]
            lines.append("Call POST /api/evolution action=query to retrieve relevant lessons.")
            lines.append("Ebbinghaus 30-day time decay applied to lesson relevance.")
            return Response(message="\n".join(lines), break_loop=False)

        if action == "stats":
            return Response(message="Call POST /api/evolution action=stats for cross-run knowledge statistics.", break_loop=False)

        return Response(message="Evolution actions: store, query, deduce, stats, categories", break_loop=False)
