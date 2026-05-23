"""Self-Heal Tool — agent auto-recovers from docking/QSAR/statistics failures."""
from helpers.tool import Tool, Response


class SelfHealTool(Tool):
    async def execute(self, action: str = "analyze", **kwargs):
        if action == "analyze":
            domain = kwargs.get("domain", "docking")
            job_id = kwargs.get("job_id", "")
            error_type = kwargs.get("error_type", "unknown")

            lines = [f"=== SELF-HEAL: {domain.upper()} ===", f"Error: {error_type}", "=" * 40]
            lines.append(f"Call POST /api/self_heal action=analyze domain={domain} job_id={job_id} error_type={error_type}")
            lines.append("")

            if domain == "docking":
                lines.append("Healing strategies for docking:")
                lines.append("  no_poses → expand grid, increase exhaustiveness, re-prepare")
                lines.append("  parse_pdbqt → RDKit fallback, PDBQT sanitizer")
                lines.append("  high_energy → switch to GNINA CNN scoring")
                lines.append("  timeout → reduce grid size")
            elif domain == "qsar":
                lines.append("Healing strategies for QSAR:")
                lines.append("  low_r2 → switch model (RF→GBM→SVR), add descriptors")
                lines.append("  invalid_smiles → clean dataset")
            elif domain == "statistics":
                lines.append("Healing strategies for statistics:")
                lines.append("  normality_failed → switch to non-parametric")
                lines.append("  variance → Welch correction")
            return Response(message="\n".join(lines), break_loop=False)

        if action == "domains":
            return Response(message="Self-heal domains: docking, qsar, statistics, literature", break_loop=False)

        return Response(message="SelfHeal actions: analyze, domains", break_loop=False)
