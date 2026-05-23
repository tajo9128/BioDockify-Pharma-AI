"""Verification Tool — agent verifies citations, claims, and compounds."""
from helpers.tool import Tool, Response


class VerificationTool(Tool):
    async def execute(self, action: str = "verify", **kwargs):
        if action == "verify":
            text = kwargs.get("text", "")
            if not text:
                return Response(message="Provide text containing citations. Use: Verify action=verify text=\"...\"", break_loop=False)
            lines = ["=== CITATION VERIFICATION ===", "=" * 40]
            lines.append("5-Layer Verification Stack:")
            lines.append("  L1: PubMed ID check")
            lines.append("  L2: CrossRef DOI verification")
            lines.append("  L3: ClinicalTrials.gov NCT check")
            lines.append("  L4: PubChem CID validation")
            lines.append("  L5: LLM relevance check (agent-performed)")
            lines.append("")
            lines.append("Call POST /api/verification action=verify with your text.")
            return Response(message="\n".join(lines), break_loop=False)

        if action == "claims":
            text = kwargs.get("text", "")
            if not text:
                return Response(message="Provide text to extract claims from. Use: Verify action=claims text=\"...\"", break_loop=False)
            return Response(message="Call POST /api/verification action=verify_claims to extract factual claims.", break_loop=False)

        if action == "compound":
            smiles = kwargs.get("smiles", "")
            if not smiles:
                return Response(message="Provide SMILES. Use: Verify action=compound smiles=\"...\"", break_loop=False)
            return Response(message="Call POST /api/verification action=verify_compound to check PubChem.", break_loop=False)

        return Response(message="Verify actions: verify, claims, compound, layers", break_loop=False)
