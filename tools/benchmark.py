"""Benchmark Tool — agent runs validation diagnostics."""
from helpers.tool import Tool, Response


class BenchmarkTool(Tool):
    async def execute(self, action: str = "run", **kwargs):
        if action == "run":
            lines = ["BioDockify Diagnostics", "=" * 30]

            for mod in ["rdkit", "numpy", "sklearn"]:
                try:
                    __import__(mod)
                    lines.append(f"  {mod}: available")
                except ImportError:
                    lines.append(f"  {mod}: MISSING")

            import subprocess
            for cmd in ["vina", "obabel"]:
                try:
                    subprocess.run([cmd, "--version"], capture_output=True, timeout=5)
                    lines.append(f"  {cmd}: available")
                except Exception:
                    lines.append(f"  {cmd}: MISSING")

            try:
                from rdkit import Chem
                mol = Chem.MolFromSmiles("CC(=O)Oc1ccccc1C(=O)O")
                lines.append(f"  RDKit test: {'PASS' if mol else 'FAIL'}")
            except Exception as e:
                lines.append(f"  RDKit test: FAIL ({e})")

            return Response(message="\n".join(lines), break_loop=False)

        return Response(message="Benchmark actions: run. Use: Benchmark action=run", break_loop=False)
