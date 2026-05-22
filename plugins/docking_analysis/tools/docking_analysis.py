"""Docking Analysis Tool — agent deep analysis: clusters, torsion, residue decomposition, overlay."""
from helpers.tool import Tool, Response
from helpers import files
import os, math, json


JOBS_DIR = files.get_abs_path("tmp/docking_jobs")


class DockingAnalysisTool(Tool):
    async def execute(self, action: str = "analyze", **kwargs):

        if action == "analyze":
            job_id = kwargs.get("job_id", "")
            if not job_id:
                return Response(message="Provide a docking job_id.", break_loop=False)
            job_dir = os.path.join(JOBS_DIR, job_id)
            protein_pdb = os.path.join(job_dir, "protein.pdb")
            docked_pdbqt = os.path.join(job_dir, "docked_output.pdbqt")
            if not os.path.exists(protein_pdb) or not os.path.exists(docked_pdbqt):
                return Response(message=f"Docking job {job_id} not found.", break_loop=False)

            with open(docked_pdbqt) as f:
                content = f.read()
            models = content.split("MODEL")
            energies = []
            for line in content.split("\n"):
                if "REMARK VINA RESULT:" in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        try:
                            energies.append(float(parts[3]))
                        except ValueError:
                            pass

            with open(protein_pdb) as f:
                pdb = f.read()
            atom_count = sum(1 for l in pdb.split("\n") if l.startswith("ATOM") or l.startswith("HETATM"))
            residues = set()
            for l in pdb.split("\n"):
                if l.startswith("ATOM"):
                    residues.add(l[17:20].strip())

            lines = [f"Docking Analysis: Job {job_id}", "=" * 40]
            lines.append(f"Poses: {len(models) - 1}")
            if energies:
                lines.append(f"Best energy: {min(energies):.2f} kcal/mol")
                lines.append(f"Worst energy: {max(energies):.2f} kcal/mol")
                lines.append(f"Spread: {max(energies) - min(energies):.2f} kcal/mol")
            lines.append(f"Receptor: {atom_count} atoms, {len(residues)} unique residues")
            return Response(message="\n".join(lines), break_loop=False)

        if action == "clusters":
            job_id = kwargs.get("job_id", "")
            if not job_id:
                return Response(message="Provide a docking job_id.", break_loop=False)
            lines = [f"Pose RMSD Clusters: Job {job_id}", "-" * 35]
            lines.append("Use the API or webui for full clustering. Run docking first.")
            return Response(message="\n".join(lines), break_loop=False)

        if action == "torsion":
            job_id = kwargs.get("job_id", "")
            pose_i = int(kwargs.get("pose_index", 0))
            if not job_id:
                return Response(message="Provide job_id and pose_index.", break_loop=False)
            lines = [f"Torsion Analysis: Job {job_id} Pose {pose_i}", "-" * 35]
            lines.append("Use /api/plugins/docking_analysis/docking_analysis action=torsion for full analysis.")
            return Response(message="\n".join(lines), break_loop=False)

        if action == "deep":
            job_id = kwargs.get("job_id", "")
            if not job_id:
                return Response(message="Provide a docking job_id.", break_loop=False)
            lines = [f"Deep Docking Analysis: Job {job_id}", "=" * 40]
            lines.append("Call /api/plugins/docking_analysis/docking_analysis?action=deep_analysis for full report.")
            return Response(message="\n".join(lines), break_loop=False)

        return Response(message="DockingAnalysis actions: analyze, clusters, torsion, deep. Use: DockingAnalysis action=analyze job_id=ID", break_loop=False)
