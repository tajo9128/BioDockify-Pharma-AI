"""Docking Analysis API — deep post-docking analysis: interactions, RMSD, clusters, torsion, SVG diagrams, residue energy."""
from helpers.api import ApiHandler, Request, Response
from helpers import files
import os, logging, math, json
import numpy as np

log = logging.getLogger("docking_analysis_api")
JOBS_DIR = files.get_abs_path("tmp/docking_jobs")

HYDROPHOBIC_RESIDUES = {"ALA", "VAL", "LEU", "ILE", "MET", "PHE", "TRP", "TYR", "PRO"}
AROMATIC_RESIDUES = {"PHE", "TYR", "TRP", "HIS"}
POSITIVE_RESIDUES = {"ARG", "LYS", "HIS"}
NEGATIVE_RESIDUES = {"ASP", "GLU"}
HBOND_DONORS = {"N", "O"}
HBOND_ACCEPTORS = {"N", "O", "S"}

# Kyte-Doolittle hydropathy scale
KD_SCALE = {"ALA": 1.8, "ARG": -4.5, "ASN": -3.5, "ASP": -3.5, "CYS": 2.5, "GLN": -3.5, "GLU": -3.5, "GLY": -0.4, "HIS": -3.2, "ILE": 4.5, "LEU": 3.8, "LYS": -3.9, "MET": 1.9, "PHE": 2.8, "PRO": -1.6, "SER": -0.8, "THR": -0.7, "TRP": -0.9, "TYR": -1.3, "VAL": 4.2}


def _parse_pdb_atoms(pdb_text: str) -> list:
    atoms = []
    for line in pdb_text.split("\n"):
        if line.startswith("ATOM") or line.startswith("HETATM"):
            try:
                atoms.append({"serial": int(line[6:11]), "name": line[12:16].strip(), "resname": line[17:20].strip(), "chain": line[21:22].strip() or "A", "resseq": int(line[22:26]), "x": float(line[30:38]), "y": float(line[38:46]), "z": float(line[46:54]), "element": (line[76:78] or line[12:14]).strip()})
            except (ValueError, IndexError):
                pass
    return atoms


def _parse_pdbqt_models(pdbqt_text: str) -> list:
    models, current = [], []
    for line in pdbqt_text.split("\n"):
        if line.startswith("MODEL"):
            current = []
        elif line.startswith("ENDMDL"):
            if current:
                models.append(current)
            current = []
        elif line.startswith("ATOM") or line.startswith("HETATM"):
            try:
                current.append({"serial": int(line[6:11]), "name": line[12:16].strip(), "resname": line[17:20].strip(), "chain": line[21:22].strip() or "L", "resseq": int(line[22:26]) if line[22:26].strip() else 1, "x": float(line[30:38]), "y": float(line[38:46]), "z": float(line[46:54]), "element": (line[76:78] or line[12:14]).strip(), "charge": float(line[70:76]) if line[70:76].strip() else 0.0})
            except (ValueError, IndexError):
                pass
    return models


def _distance(a1, a2):
    return math.sqrt((a1["x"] - a2["x"])**2 + (a1["y"] - a2["y"])**2 + (a1["z"] - a2["z"])**2)


def _analyze_interactions(receptor_atoms, ligand_atoms, pocket_cutoff=5.0):
    hbonds, hydrophobic, pi_stacking, salt_bridges = [], [], [], []
    binding_site = set()
    receptor_by_res = {}
    for a in receptor_atoms:
        receptor_by_res.setdefault((a["resname"], a["resseq"], a["chain"]), []).append(a)

    for la in ligand_atoms:
        for ra in receptor_atoms:
            d = _distance(la, ra)
            if d > 6.0:
                continue
            if d <= pocket_cutoff:
                binding_site.add((ra["resname"], ra["resseq"], ra["chain"]))
            if d <= 3.5:
                if ra["element"] in HBOND_DONORS and la["element"] in HBOND_ACCEPTORS:
                    hbonds.append({"type": "protein_donor", "residue": ra["resname"], "resseq": ra["resseq"], "chain": ra["chain"], "atom": ra["name"], "ligand_atom": la["name"], "distance": round(d, 2)})
                if la["element"] in HBOND_DONORS and ra["element"] in HBOND_ACCEPTORS:
                    hbonds.append({"type": "ligand_donor", "residue": ra["resname"], "resseq": ra["resseq"], "chain": ra["chain"], "atom": ra["name"], "ligand_atom": la["name"], "distance": round(d, 2)})
            if d <= 4.0 and ra["resname"] in HYDROPHOBIC_RESIDUES and ra["element"] == "C" and la["element"] in ("C", "S"):
                hydrophobic.append({"residue": ra["resname"], "resseq": ra["resseq"], "chain": ra["chain"], "atom": ra["name"], "ligand_atom": la["name"], "distance": round(d, 2)})
            if d <= 4.5:
                if ra["resname"] in POSITIVE_RESIDUES and la.get("charge", 0) < 0:
                    salt_bridges.append({"type": "cation_anion", "residue": ra["resname"], "resseq": ra["resseq"], "chain": ra["chain"], "distance": round(d, 2)})
                if ra["resname"] in NEGATIVE_RESIDUES and la.get("charge", 0) > 0:
                    salt_bridges.append({"type": "anion_cation", "residue": ra["resname"], "resseq": ra["resseq"], "chain": ra["chain"], "distance": round(d, 2)})

    for res_key, res_atoms in receptor_by_res.items():
        if res_key[0] not in AROMATIC_RESIDUES:
            continue
        ring_carbons = [a for a in res_atoms if a["element"] == "C"]
        if len(ring_carbons) < 4:
            continue
        rc = np.mean([[a["x"], a["y"], a["z"]] for a in ring_carbons], axis=0)
        for la in ligand_atoms:
            if la["element"] != "C":
                continue
            ld = math.sqrt((rc[0] - la["x"])**2 + (rc[1] - la["y"])**2 + (rc[2] - la["z"])**2)
            if ld < 5.5:
                pi_stacking.append({"residue": res_key[0], "resseq": res_key[1], "chain": res_key[2], "distance": round(float(ld), 2)})
                break

    binding_site_list = sorted([{"resname": r[0], "resseq": r[1], "chain": r[2]} for r in binding_site], key=lambda x: (x["chain"], x["resseq"]))
    return {"hydrogen_bonds": hbonds, "hydrophobic_contacts": hydrophobic, "pi_stacking": pi_stacking, "salt_bridges": salt_bridges, "binding_site_residues": binding_site_list, "summary": {"total_hbonds": len(hbonds), "total_hydrophobic": len(hydrophobic), "total_pi_stacking": len(pi_stacking), "total_salt_bridges": len(salt_bridges), "binding_site_size": len(binding_site_list)}}


def _kabsch_rmsd(P, Q):
    Pc = P - P.mean(axis=0)
    Qc = Q - Q.mean(axis=0)
    C = Qc.T @ Pc
    V, S, Wt = np.linalg.svd(C)
    d = np.sign(np.linalg.det(V @ Wt))
    U = V @ np.diag([1, 1, d]) @ Wt
    Qr = Qc @ U
    return float(np.sqrt(np.sum((Pc - Qr)**2) / len(P)))


def _rmsd_cluster(ligand_models, cutoff=2.0):
    """Cluster poses by RMSD using scipy hierarchical clustering."""
    n = len(ligand_models)
    if n <= 1:
        return [{"representative": 0, "members": list(range(n)), "size": n}]
    coords = []
    for m in ligand_models:
        coords.append(np.array([[a["x"], a["y"], a["z"]] for a in m]))
    min_len = min(len(c) for c in coords)
    coords = [c[:min_len] for c in coords]
    dist_matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            d = _kabsch_rmsd(coords[i], coords[j])
            dist_matrix[i][j] = d
            dist_matrix[j][i] = d
    try:
        from scipy.cluster.hierarchy import fcluster, linkage
        Z = linkage(dist_matrix[np.triu_indices(n, 1)], method="average")
        labels = fcluster(Z, cutoff, criterion="distance")
    except Exception:
        labels = list(range(n))
    clusters = {}
    for i, lbl in enumerate(labels):
        clusters.setdefault(int(lbl), []).append(i)
    result = []
    for lbl, members in clusters.items():
        avg_energy = None
        result.append({"cluster_id": lbl, "representative": members[0], "members": sorted(members), "size": len(members)})
    result.sort(key=lambda c: c["size"], reverse=True)
    return result


def _torsion_analysis(ligand_atoms):
    """Calculate dihedral angles from consecutive atom quartets."""
    dihedrals = []
    if len(ligand_atoms) < 4:
        return dihedrals
    coords = np.array([[a["x"], a["y"], a["z"]] for a in ligand_atoms])
    for i in range(len(ligand_atoms) - 3):
        a, b, c, d = coords[i], coords[i + 1], coords[i + 2], coords[i + 3]
        ba = b - a
        cb = c - b
        dc = d - c
        n1 = np.cross(ba, cb)
        n2 = np.cross(cb, dc)
        n1 /= np.linalg.norm(n1)
        n2 /= np.linalg.norm(n2)
        m1 = np.cross(n1, cb / np.linalg.norm(cb))
        x = np.dot(n1, n2)
        y = np.dot(m1, n2)
        angle = math.degrees(math.atan2(y, x))
        dihedrals.append({"atoms": [ligand_atoms[i]["name"], ligand_atoms[i + 1]["name"], ligand_atoms[i + 2]["name"], ligand_atoms[i + 3]["name"]], "angle": round(angle, 1)})
    return dihedrals


def _residue_energy_decomposition(receptor_atoms, ligand_atoms, interactions):
    """Estimate per-residue energy contribution from interaction counts."""
    residue_energy = {}
    for hb in interactions.get("hydrogen_bonds", []):
        key = f"{hb['chain']}:{hb['residue']}{hb['resseq']}"
        residue_energy[key] = residue_energy.get(key, 0) - 0.5
    for hp in interactions.get("hydrophobic_contacts", []):
        key = f"{hp['chain']}:{hp['residue']}{hp['resseq']}"
        residue_energy[key] = residue_energy.get(key, 0) - 0.15
    for pi in interactions.get("pi_stacking", []):
        key = f"{pi['chain']}:{pi['residue']}{pi['resseq']}"
        residue_energy[key] = residue_energy.get(key, 0) - 0.3
    for sb in interactions.get("salt_bridges", []):
        key = f"{sb['chain']}:{sb['residue']}{sb['resseq']}"
        residue_energy[key] = residue_energy.get(key, 0) - 0.8
    result = [{"residue_label": k, "energy": round(v, 3), "is_favorable": v < 0} for k, v in residue_energy.items()]
    result.sort(key=lambda r: r["energy"])
    return result


def _generate_interaction_svg(job_id, pose_index, receptor_text, ligand_models, interactions):
    """Generate 2D interaction diagram SVG via RDKit."""
    try:
        from rdkit import Chem
        from rdkit.Chem import Draw, AllChem
        from rdkit.Chem.Draw import IPythonConsole
        import io

        if pose_index >= len(ligand_models):
            return None
        latoms = ligand_models[pose_index]
        smiles = None
        try:
            from rdkit.Chem import rdFMCS
            lig_coords = np.array([[a["x"], a["y"], a["z"]] for a in latoms])
            lig_symbols = [a["element"] for a in latoms]
            rw = Chem.RWMol()
            conf = Chem.Conformer(len(latoms))
            for i, (sym, pos) in enumerate(zip(lig_symbols, lig_coords)):
                atom = Chem.Atom(sym)
                rw.AddAtom(atom)
                conf.SetAtomPosition(i, [float(pos[0]), float(pos[1]), float(pos[2])])
            mol = rw.GetMol()
            mol.AddConformer(conf)
            try:
                mol = Chem.RemoveHs(mol)
            except Exception:
                pass
            smiles = Chem.MolToSmiles(mol) if mol.GetNumAtoms() > 0 else None
        except Exception:
            pass

        if smiles:
            lig_mol = Chem.MolFromSmiles(smiles)
            if lig_mol:
                AllChem.Compute2DCoords(lig_mol)
                d2d = Draw.MolDraw2DSVG(600, 400)
                d2d.DrawMolecule(lig_mol)

                hb_legend = [f"{hb['residue']}{hb['resseq']} ({hb['distance']}\u00c5)" for hb in interactions.get("hydrogen_bonds", [])[:8]]
                hp_legend = [f"{hp['residue']}{hp['resseq']}" for hp in interactions.get("hydrophobic_contacts", [])[:8]]
                pi_legend = [f"pi-pi: {pi['residue']}{pi['resseq']}" for pi in interactions.get("pi_stacking", [])[:4]]

                y = 340
                d2d.DrawString(f"H-Bonds: {', '.join(hb_legend) if hb_legend else 'none'}", 10, y, size=12)
                y += 18
                d2d.DrawString(f"Hydrophobic: {', '.join(hp_legend) if hp_legend else 'none'}", 10, y, size=12)
                y += 18
                d2d.DrawString(f"Pi-Stacking: {', '.join(pi_legend) if pi_legend else 'none'}", 10, y, size=12)

                d2d.FinishDrawing()
                return d2d.GetDrawingText()
        return None
    except Exception as e:
        log.warning(f"SVG generation failed: {e}")
        return None


def _pocket_surface_data(receptor_atoms, ligand_models, cutoff=5.0):
    """Generate binding site surface atoms colored by Kyte-Doolittle hydrophobicity."""
    if not ligand_models:
        return []
    binding_residues = set()
    for la in ligand_models[0]:
        for ra in receptor_atoms:
            if _distance(la, ra) <= cutoff:
                binding_residues.add((ra["resname"], ra["resseq"], ra["chain"]))
    surface = []
    for ra in receptor_atoms:
        key = (ra["resname"], ra["resseq"], ra["chain"])
        if key in binding_residues:
            kd = KD_SCALE.get(ra["resname"], 0)
            r = min(int(255 * max(0, min(1, (kd + 4.5) / 9.0))), 255)
            b = min(int(255 * max(0, min(1, (4.5 - kd) / 9.0))), 255)
            surface.append({"x": ra["x"], "y": ra["y"], "z": ra["z"], "resname": ra["resname"], "resseq": ra["resseq"], "hydrophobicity": kd, "color": f"rgb({r},100,{b})"})
    return surface


def _pose_overlay_pdb(receptor_text, ligand_models, energies=None):
    """Extract all poses as individual PDB blocks + receptor for 3D overlay."""
    poses = []
    for i, latoms in enumerate(ligand_models):
        lines = ["MODEL    1"]
        for a in latoms:
            lines.append(f"HETATM{a['serial']:5d}  {a['name']:<4s}UNL     1    {a['x']:8.3f}{a['y']:8.3f}{a['z']:8.3f}  1.00  0.00          {a['element']:>2s}")
        lines.append("ENDMDL")
        pose_data = {"pose_index": i, "pdb": "\n".join(lines)}
        if energies and i < len(energies):
            pose_data["energy"] = energies[i]
        poses.append(pose_data)
    return {"receptor_pdb": receptor_text, "poses": poses, "num_poses": len(poses)}


class DockingAnalysisHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "analyze")

        # ── Shared data loader ──
        job_id = input.get("job_id", "")
        job_dir = os.path.join(JOBS_DIR, job_id) if job_id else ""
        protein_pdb_path = os.path.join(job_dir, "protein.pdb") if job_id else ""
        docked_path = os.path.join(job_dir, "docked_output.pdbqt") if job_id else ""

        receptor_atoms = ligand_models = receptor_text = energies = None
        if job_id and os.path.exists(protein_pdb_path) and os.path.exists(docked_path):
            with open(protein_pdb_path) as f:
                receptor_text = f.read()
            with open(docked_path) as f:
                pdbqt_text = f.read()
            receptor_atoms = _parse_pdb_atoms(receptor_text)
            ligand_models = _parse_pdbqt_models(pdbqt_text)
            energies = []
            for line in pdbqt_text.split("\n"):
                if "REMARK VINA RESULT:" in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        try:
                            energies.append(float(parts[3]))
                        except ValueError:
                            pass

        # ── analyze ──
        if action == "analyze":
            if not job_id:
                return {"success": False, "error": "Missing job_id"}
            if not receptor_atoms:
                return {"success": False, "error": "protein.pdb not found"}
            if not ligand_models:
                return {"success": False, "error": "docked_output.pdbqt not found"}
            per_pose = []
            for i, latoms in enumerate(ligand_models):
                interactions = _analyze_interactions(receptor_atoms, latoms)
                interactions["pose_index"] = i
                if energies and i < len(energies):
                    interactions["energy"] = energies[i]
                per_pose.append(interactions)
            return {"success": True, "job_id": job_id, "per_pose": per_pose, "num_poses": len(per_pose)}

        # ── rmsd ──
        if action == "rmsd":
            pdb1 = input.get("pdb1", "")
            pdb2 = input.get("pdb2", "")
            if not pdb1 or not pdb2:
                return {"success": False, "error": "Both pdb1 and pdb2 required"}
            a1, a2 = _parse_pdb_atoms(pdb1), _parse_pdb_atoms(pdb2)
            n = min(len(a1), len(a2))
            if n < 3:
                return {"success": False, "error": "Need at least 3 atoms"}
            P = np.array([[a1[i]["x"], a1[i]["y"], a1[i]["z"]] for i in range(n)])
            Q = np.array([[a2[i]["x"], a2[i]["y"], a2[i]["z"]] for i in range(n)])
            return {"success": True, "rmsd": round(_kabsch_rmsd(P, Q), 4), "n_atoms": n}

        # ── rmsd_cluster ──
        if action == "rmsd_cluster":
            if not ligand_models or len(ligand_models) < 2:
                return {"success": False, "error": "Need at least 2 poses"}
            cutoff = float(input.get("rmsd_cutoff", 2.0))
            clusters = _rmsd_cluster(ligand_models, cutoff)
            for c in clusters:
                if energies and c["members"]:
                    c["avg_energy"] = round(np.mean([energies[m] for m in c["members"] if m < len(energies)]), 2)
            return {"success": True, "clusters": clusters, "num_clusters": len(clusters), "rmsd_cutoff": cutoff}

        # ── torsion ──
        if action == "torsion":
            if not ligand_models:
                return {"success": False, "error": "No ligand poses found"}
            pose_i = int(input.get("pose_index", 0))
            if pose_i >= len(ligand_models):
                return {"success": False, "error": f"Pose {pose_i} out of range"}
            torsions = _torsion_analysis(ligand_models[pose_i])
            return {"success": True, "pose_index": pose_i, "dihedrals": torsions, "num_dihedrals": len(torsions)}

        # ── residue_energy ──
        if action == "residue_energy":
            if not receptor_atoms or not ligand_models:
                return {"success": False, "error": "Missing data. Run docking + analyze first."}
            pose_i = int(input.get("pose_index", 0))
            if pose_i >= len(ligand_models):
                return {"success": False, "error": f"Pose {pose_i} out of range"}
            interactions = _analyze_interactions(receptor_atoms, ligand_models[pose_i])
            decomposition = _residue_energy_decomposition(receptor_atoms, ligand_models[pose_i], interactions)
            return {"success": True, "pose_index": pose_i, "residue_energies": decomposition, "num_residues": len(decomposition)}

        # ── pocket_surface ──
        if action == "pocket_surface":
            if not receptor_atoms or not ligand_models:
                return {"success": False, "error": "Missing data. Run docking + analyze first."}
            surface = _pocket_surface_data(receptor_atoms, ligand_models)
            return {"success": True, "surface_atoms": surface, "num_surface_atoms": len(surface)}

        # ── interaction_svg ──
        if action == "interaction_svg":
            if not receptor_text or not ligand_models:
                return {"success": False, "error": "Missing data. Run docking + analyze first."}
            pose_i = int(input.get("pose_index", 0))
            if pose_i >= len(ligand_models):
                return {"success": False, "error": f"Pose {pose_i} out of range"}
            interactions = _analyze_interactions(receptor_atoms, ligand_models[pose_i])
            svg = _generate_interaction_svg(job_id, pose_i, receptor_text, ligand_models, interactions)
            return {"success": True, "svg": svg, "pose_index": pose_i}

        # ── pose_overlay_data ──
        if action == "pose_overlay":
            if not receptor_text or not ligand_models:
                return {"success": False, "error": "Missing data. Run docking first."}
            data = _pose_overlay_pdb(receptor_text, ligand_models, energies)
            return {"success": True, **data}

        # ── binding_site ──
        if action == "binding_site":
            if not receptor_atoms or not ligand_models:
                return {"success": False, "error": "Job files not found"}
            cutoff = float(input.get("cutoff", 5.0))
            binding_site = set()
            for la in ligand_models[0]:
                for ra in receptor_atoms:
                    if _distance(la, ra) <= cutoff:
                        binding_site.add((ra["resname"], ra["resseq"], ra["chain"]))
            residues = sorted([{"resname": r[0], "resseq": r[1], "chain": r[2]} for r in binding_site])
            return {"success": True, "residues": residues, "count": len(residues)}

        # ── deep_analysis (all-in-one) ──
        if action == "deep_analysis":
            if not receptor_atoms or not ligand_models:
                return {"success": False, "error": "Missing data"}
            pose_i = int(input.get("pose_index", 0))
            if pose_i >= len(ligand_models):
                return {"success": False, "error": f"Pose {pose_i} out of range"}
            interactions = _analyze_interactions(receptor_atoms, ligand_models[pose_i])
            residue_energy = _residue_energy_decomposition(receptor_atoms, ligand_models[pose_i], interactions)
            torsions = _torsion_analysis(ligand_models[pose_i])
            clusters = _rmsd_cluster(ligand_models, 2.0)
            surface = _pocket_surface_data(receptor_atoms, ligand_models)
            svg = _generate_interaction_svg(job_id, pose_i, receptor_text, ligand_models, interactions)
            overlay = _pose_overlay_pdb(receptor_text, ligand_models, energies)
            return {"success": True, "interactions": interactions, "residue_energy": residue_energy, "torsions": torsions, "clusters": clusters, "surface": surface, "svg": svg, "overlay": overlay, "energies": energies, "num_poses": len(ligand_models)}

        return {"error": f"Unknown action: {action}"}
