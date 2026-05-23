"""Debate Tool — agent runs structured multi-perspective scientific debates."""
from helpers.tool import Tool, Response


class DebateTool(Tool):
    async def execute(self, action: str = "hypothesis", **kwargs):
        if action == "hypothesis":
            topic = kwargs.get("topic", "")
            if not topic:
                return Response(message="Provide a topic to debate. Use: Debate action=hypothesis topic=\"Is EGFR a viable target?\"", break_loop=False)
            lines = [f"=== HYPOTHESIS DEBATE ===", f"Topic: {topic}", "=" * 40]
            lines.append("Perspectives: Pharmacologist, Biostatistician, Medicinal Chemist")
            lines.append("")
            lines.append("Call POST /api/debate action=hypothesis to generate debate prompt.")
            lines.append("The agent LLM will produce structured arguments from each perspective.")
            return Response(message="\n".join(lines), break_loop=False)

        if action == "method":
            problem = kwargs.get("problem", "")
            options = kwargs.get("options", "docking,qsar,pharmacophore")
            if not problem:
                return Response(message="Provide a problem description. Use: Debate action=method problem=\"...\"", break_loop=False)
            lines = [f"=== METHOD DEBATE ===", f"Problem: {problem}", f"Options: {options}", "=" * 40]
            lines.append("Call POST /api/debate action=method to generate method debate prompt.")
            return Response(message="\n".join(lines), break_loop=False)

        if action == "results":
            data = kwargs.get("data", "")
            if not data:
                return Response(message="Provide results summary. Use: Debate action=results data=\"...\"", break_loop=False)
            lines = [f"=== RESULTS DEBATE ===", f"Data: {data[:200]}", "=" * 40]
            lines.append("Call POST /api/debate action=results to generate results debate.")
            return Response(message="\n".join(lines), break_loop=False)

        return Response(message="Debate actions: hypothesis, method, results, judge, perspectives", break_loop=False)
