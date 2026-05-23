"""Triple Debate System — multi-perspective hypothesis, method, and results debate."""
from helpers.api import ApiHandler, Request, Response
import logging, json

log = logging.getLogger("debate")


def _format_debate(topic, perspectives, round_name):
    """Format a structured debate prompt. The agent LLM will produce both sides."""
    prompt = f"""=== {round_name.upper()} DEBATE ===
Topic: {topic}
Perspectives: {', '.join(perspectives)}

You are running a structured scientific debate. Produce arguments from EACH perspective, then judge the winner.

Format your response as JSON:
{{
  "round": "{round_name}",
  "topic": "{topic}",
  "perspectives": {json.dumps(perspectives)},
  "arguments": [
    {{"perspective": "name", "position": "supporting/opposing", "argument": "main point", "evidence": "supporting facts"}},
    ...
  ],
  "winner": "winning_perspective_name",
  "rationale": "why this perspective won",
  "dissenting_opinion": "strongest counter-argument",
  "confidence": 0.0_to_1.0
}}"""
    return prompt


class DebateHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "hypothesis")

        if action == "hypothesis":
            topic = input.get("topic", "")
            perspectives = input.get("perspectives", ["pharmacologist", "biostatistician", "medicinal_chemist"])
            prompt = _format_debate(topic, perspectives, "hypothesis")
            return {
                "success": True,
                "action": "hypothesis_debate",
                "prompt": prompt,
                "perspectives": perspectives,
                "instruction": "Send this prompt to the agent LLM. The agent will produce structured debate arguments from each perspective.",
            }

        if action == "method":
            problem = input.get("problem", "")
            options = input.get("options", ["docking", "qsar", "pharmacophore", "literature_review"])
            perspectives = input.get("perspectives", ["computational_chemist", "biostatistician", "pharmacologist"])
            prompt = _format_debate(f"{problem} — Best Method: {', '.join(options)}", perspectives, "method")
            return {"success": True, "action": "method_debate", "prompt": prompt, "options": options}

        if action == "results":
            data_summary = input.get("data", "")
            interpretations = input.get("interpretations", [])
            perspectives = input.get("perspectives", ["writer", "biostatistician", "domain_expert"])
            topic = f"Results Interpretation — {data_summary}"
            if interpretations:
                topic += f" — Interpretations: {', '.join(interpretations)}"
            prompt = _format_debate(topic, perspectives, "results")
            return {"success": True, "action": "results_debate", "prompt": prompt}

        if action == "judge":
            debate_json = input.get("debate_json", "")
            try:
                debate = json.loads(debate_json) if isinstance(debate_json, str) else debate_json
                args = debate.get("arguments", [])
                scores = {}
                for arg in args:
                    persp = arg.get("perspective", "unknown")
                    scores[persp] = scores.get(persp, 0) + 1
                winner = debate.get("winner", max(scores, key=scores.get) if scores else "undecided")
                return {
                    "success": True,
                    "judged": True,
                    "winner": winner,
                    "rationale": debate.get("rationale", ""),
                    "confidence": debate.get("confidence", 0.5),
                    "score_breakdown": scores,
                }
            except Exception as e:
                return {"success": False, "error": f"Failed to parse debate JSON: {e}"}

        if action == "perspectives":
            return {
                "available": {
                    "pharmacologist": "Drug mechanism, target engagement, ADMET",
                    "biostatistician": "Statistical validity, effect size, study design",
                    "medicinal_chemist": "Synthesis feasibility, SAR, optimization",
                    "computational_chemist": "Docking accuracy, force fields, sampling",
                    "writer": "Clarity, argument structure, publication standards",
                    "domain_expert": "Disease biology, clinical relevance, translation",
                    "researcher": "Literature context, novelty, prior art",
                    "regulatory_specialist": "FDA/EMA guidelines, compliance, safety",
                }
            }

        return {"error": f"Unknown action: {action}"}
