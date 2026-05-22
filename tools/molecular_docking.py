"""Molecular Docking Tool — lets the agent run AutoDock Vina via chat."""
import subprocess
import tempfile
import os
from helpers.tool import Tool, Response


def _read_pdb_coords(pdb_path: str):
    """Read ATOM coordinates from a PDB file. Returns (center, size, atom_count)."""
    xs, ys, zs = [], [], []
    try:
        with open(pdb_path) as f:
            for line in f:
                if line.startswith("ATOM") or line.startswith("HETATM"):
                    try:
                        xs.append(float(line[30:38]))
                        ys.append(float(line[38:46]))
                        zs.append(float(line[46:54]))
                    except ValueError:
                        pass
    except Exception:
        pass

    if not xs:
        return [0, 0, 0], (20, 20, 20), 0

    cx = round(sum(xs) / len(xs), 2)
    cy = round(sum(ys) / len(ys), 2)
    cz = round(sum(zs) / len(zs), 2)

    margin = 8.0
    sx = min(max((max(xs) - min(xs)) + margin * 2, 15.0), 30.0)
    sy = min(max((max(ys) - min(ys)) + margin * 2, 15.0), 30.0)
    sz = min(max((max(zs) - min(zs)) + margin * 2, 15.0), 30.0)

    return [cx, cy, cz], (sx, sy, sz), len(xs)


class MolecularDocking(Tool):
    async def execute(self, receptor_pdb: str = "", ligand_smiles: str = "", **kwargs):
        if not receptor_pdb or not ligand_smiles:
            return Response(
                message="Please provide a protein PDB file path and a ligand SMILES string.",
                break_loop=False
            )

        if not os.path.exists(receptor_pdb):
            return Response(
                message=f"Receptor PDB file not found: {receptor_pdb}",
                break_loop=False
            )

        workdir = tempfile.mkdtemp(prefix="docking_")
        try:
            # Prepare receptor PDBQT (proteins already have 3D coords)
            receptor_pdbqt = os.path.join(workdir, "receptor.pdbqt")
            r = subprocess.run(
                ["obabel", receptor_pdb, "-O", receptor_pdbqt, "-xr"],
                capture_output=True, text=True, timeout=60
            )
            if r.returncode != 0:
                return Response(
                    message=f"Failed to prepare receptor PDBQT: {r.stderr.strip() or 'unknown error'}",
                    break_loop=False
                )

            # Convert SMILES to SDF
            ligand_sdf = os.path.join(workdir, "ligand.sdf")
            r = subprocess.run(
                ["obabel", f"-:{ligand_smiles}", "-O", ligand_sdf, "--gen3D"],
                capture_output=True, text=True, timeout=60
            )
            if r.returncode != 0:
                return Response(
                    message=f"Failed to convert SMILES to SDF: {r.stderr.strip() or 'unknown error'}",
                    break_loop=False
                )

            # Prepare ligand PDBQT
            ligand_pdbqt = os.path.join(workdir, "ligand.pdbqt")
            r = subprocess.run(
                ["obabel", ligand_sdf, "-O", ligand_pdbqt],
                capture_output=True, text=True, timeout=60
            )
            if r.returncode != 0:
                return Response(
                    message=f"Failed to prepare ligand PDBQT: {r.stderr.strip() or 'unknown error'}",
                    break_loop=False
                )

            # Auto-detect center and grid size from receptor
            center, size_box, atom_count = _read_pdb_coords(receptor_pdb)

            # Run Vina
            output_pdbqt = os.path.join(workdir, "docked_output.pdbqt")
            result = subprocess.run(
                [
                    "vina",
                    "--receptor", receptor_pdbqt,
                    "--ligand", ligand_pdbqt,
                    "--out", output_pdbqt,
                    "--center_x", str(center[0]),
                    "--center_y", str(center[1]),
                    "--center_z", str(center[2]),
                    "--size_x", str(round(size_box[0], 1)),
                    "--size_y", str(round(size_box[1], 1)),
                    "--size_z", str(round(size_box[2], 1)),
                    "--exhaustiveness", "8",
                    "--num_modes", "9",
                ],
                capture_output=True, text=True, timeout=600
            )

            if result.returncode != 0:
                return Response(
                    message=f"Vina docking failed (exit code {result.returncode}): {result.stderr.strip() or result.stdout.strip() or 'unknown error'}",
                    break_loop=False
                )

            # Parse energies: first try the detailed table, then REMARK lines
            energies = []
            stdout = result.stdout
            table_mode = False
            for line in stdout.split("\n"):
                stripped = line.strip()
                # Detect table header
                if "mode" in stripped.lower() and "affinity" in stripped.lower():
                    table_mode = True
                    continue
                if "-----+" in stripped:
                    table_mode = True
                    continue
                if table_mode:
                    parts = stripped.split()
                    if len(parts) >= 2:
                        try:
                            energies.append(float(parts[1]))
                            continue
                        except ValueError:
                            pass
                    if not stripped:
                        table_mode = False

            if not energies:
                for line in stdout.split("\n"):
                    if "REMARK VINA RESULT:" in line:
                        parts = line.split()
                        if len(parts) >= 4:
                            try:
                                energies.append(float(parts[3]))
                            except ValueError:
                                pass

            # Sort: most negative (strongest binding) first
            energies.sort()

            summary = [f"Docking complete."]
            summary.append(f"Grid center: ({center[0]:.2f}, {center[1]:.2f}, {center[2]:.2f}) from {atom_count} atoms")
            summary.append(f"Grid size: {size_box[0]:.1f} x {size_box[1]:.1f} x {size_box[2]:.1f} Å")
            summary.append(f"Found {len(energies)} poses:")
            if energies:
                summary.append(f"  Best binding energy: {min(energies):.2f} kcal/mol")
                for i, e in enumerate(energies):
                    label = "  <<< BEST" if i == 0 else ""
                    summary.append(f"  Pose {i+1}: {e:.2f} kcal/mol{label}")
            if result.stderr:
                summary.append(f"\nLog: {result.stderr[:500]}")

            return Response(message="\n".join(summary), break_loop=False)

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
