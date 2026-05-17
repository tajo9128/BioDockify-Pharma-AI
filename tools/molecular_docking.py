"""Molecular Docking Tool — lets the agent run AutoDock Vina via chat."""
import subprocess
import tempfile
import os
from helpers.tool import Tool, Response


class MolecularDocking(Tool):
    async def execute(self, receptor_pdb: str = "", ligand_smiles: str = "", **kwargs):
        if not receptor_pdb or not ligand_smiles:
            return Response(
                message="Please provide a protein PDB file path and a ligand SMILES string.",
                break_loop=False
            )

        workdir = tempfile.mkdtemp(prefix="docking_")
        try:
            # Prepare receptor PDBQT (proteins already have 3D coords)
            receptor_pdbqt = os.path.join(workdir, "receptor.pdbqt")
            subprocess.run(
                ["obabel", receptor_pdb, "-O", receptor_pdbqt, "-xr"],
                capture_output=True, text=True, timeout=60
            )

            # Convert SMILES to SDF
            ligand_sdf = os.path.join(workdir, "ligand.sdf")
            subprocess.run(
                ["obabel", f"-:{ligand_smiles}", "-O", ligand_sdf, "--gen3D"],
                capture_output=True, text=True, timeout=60
            )

            # Prepare ligand PDBQT
            ligand_pdbqt = os.path.join(workdir, "ligand.pdbqt")
            subprocess.run(
                ["obabel", ligand_sdf, "-O", ligand_pdbqt],
                capture_output=True, text=True, timeout=60
            )

            # Auto-detect center from receptor
            center = [0, 0, 0]
            count = 0
            with open(receptor_pdb) as f:
                for line in f:
                    if line.startswith("ATOM") or line.startswith("HETATM"):
                        try:
                            center[0] += float(line[30:38])
                            center[1] += float(line[38:46])
                            center[2] += float(line[46:54])
                            count += 1
                        except ValueError:
                            pass
            if count:
                center = [c / count for c in center]

            # Run Vina
            result = subprocess.run(
                [
                    "vina",
                    "--receptor", receptor_pdbqt,
                    "--ligand", ligand_pdbqt,
                    "--center_x", str(round(center[0], 2)),
                    "--center_y", str(round(center[1], 2)),
                    "--center_z", str(round(center[2], 2)),
                    "--size_x", "20", "--size_y", "20", "--size_z", "20",
                    "--exhaustiveness", "8",
                    "--num_modes", "5",
                ],
                capture_output=True, text=True, timeout=600
            )

            # Parse energies
            energies = []
            for line in result.stdout.split("\n"):
                if "REMARK VINA RESULT:" in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        try:
                            energies.append(float(parts[3]))
                        except ValueError:
                            pass

            output = f"Docking complete. Found {len(energies)} poses.\n"
            if energies:
                output += f"Best binding energy: {min(energies):.2f} kcal/mol\n"
                for i, e in enumerate(energies):
                    output += f"  Pose {i+1}: {e:.2f} kcal/mol\n"
            if result.stderr:
                output += f"\nLog: {result.stderr[:500]}"

            return Response(message=output, break_loop=False)

        except FileNotFoundError as e:
            return Response(
                message=f"Dependency not found: {e}. Install with: apt-get install autodock-vina openbabel",
                break_loop=False
            )
        except subprocess.TimeoutExpired:
            return Response(message="Docking timed out (10 min limit). Try a smaller grid.", break_loop=False)
        except Exception as e:
            return Response(message=f"Docking error: {str(e)}", break_loop=False)
        finally:
            import shutil
            shutil.rmtree(workdir, ignore_errors=True)
