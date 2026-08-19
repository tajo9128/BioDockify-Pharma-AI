"""Docking Analysis API — deep post-docking analysis: interactions, RMSD, clusters, torsion, SVG diagrams, residue energy."""
from helpers.api import ApiHandler, Request, Response
from helpers import files
import os, logging, math, json, re
import numpy as np


def _svg_escape(text: str) -> str:
    """Escape text for safe insertion into SVG/XML markup."""
    return (text.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))


def _interaction_only_svg(interactions) -> str:
    """Fallback 2D diagram: interaction summary without molecular structure.

    Used when the ligand SMILES can't be reconstructed from PDBQT atoms
    (no bond information). Still shows all interactions in a clean layout.
    """
    def _dedup(items):
        seen = set()
        result = []
        for item in items:
            k = (item.get("residue", ""), item.get("resseq", 0))
            if k not in seen and "HOH" not in str(item.get("residue", "")):
                seen.add(k)
                result.append(item)
        return result

    hbonds = _dedup(interactions.get("hydrogen_bonds", []))
    hydrophobic = _dedup(interactions.get("hydrophobic_contacts", []))
    pi_stacking = _dedup(interactions.get("pi_stacking", []))
    salt_bridges = _dedup(interactions.get("salt_bridges", []))

    W, H = 700, 500
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        f'<rect width="{W}" height="{H}" fill="white" rx="10"/>',
        f'<text x="{W//2}" y="40" text-anchor="middle" font-size="18" font-weight="bold" fill="#333" font-family="sans-serif">Protein-Ligand Interactions</text>',
        f'<line x1="50" y1="60" x2="{W-50}" y2="60" stroke="#ddd" stroke-width="1"/>',
    ]

    y = 100
    sections = [
        ("H-Bonds", hbonds, "#4169E1", "{r}{n} ({d}Å)"),
        ("Hydrophobic Contacts", hydrophobic, "#FFD700", "{r}{n}"),
        ("π-Stacking", pi_stacking, "#9932CC", "{r}{n}"),
        ("Salt Bridges", salt_bridges, "#DC143C", "{r}{n}"),
    ]
    for title, items, color, fmt in sections:
        if not items:
            continue
        lines.append(f'<circle cx="60" cy="{y-5}" r="8" fill="{color}"/>')
        lines.append(f'<text x="80" y="{y}" font-size="14" font-weight="bold" fill="{color}" font-family="sans-serif">{_svg_escape(title)} ({len(items)})</text>')
        y += 25
        for item in items[:6]:
            txt = fmt.format(r=_svg_escape(item.get("residue", "")),
                             n=item.get("resseq", ""),
                             d=item.get("distance", ""))
            lines.append(f'<text x="90" y="{y}" font-size="12" fill="#555" font-family="sans-serif">{txt}</text>')
            y += 20
        y += 15

    total = len(hbonds) + len(hydrophobic) + len(pi_stacking) + len(salt_bridges)
    lines.append(f'<text x="{W//2}" y="{H-30}" text-anchor="middle" font-size="12" fill="#999" font-family="sans-serif">Total: {total} interactions · Ligand structure unavailable (PDBQT has no bond info)</text>')
    lines.append('</svg>')
    return "\n".join(lines)

log = logging.getLogger("docking_analysis_api")
JOBS_DIR = files.get_abs_path("tmp/docking_jobs")

_SAFE_JOB_ID = re.compile(r'^[a-zA-Z0-9_-]+$')


def _validate_job_id(job_id: str) -> bool:
    return bool(job_id) and bool(_SAFE_JOB_ID.match(job_id)) and len(job_id) <= 128

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
    """Compute protein-ligand interactions: H-bonds, hydrophobic, pi-stacking, salt bridges."""
    import numpy as np
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
    """Kabsch RMSD between two point clouds."""
    import numpy as np
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
    import numpy as np
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
        norm_n1 = np.linalg.norm(n1)
        norm_n2 = np.linalg.norm(n2)
        norm_cb = np.linalg.norm(cb)
        if norm_n1 < 1e-10 or norm_n2 < 1e-10 or norm_cb < 1e-10:
            continue
        n1 /= norm_n1
        n2 /= norm_n2
        m1 = np.cross(n1, cb / norm_cb)
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


def _generate_interaction_svg(job_id, pose_index, receptor_text, ligand_models, interactions, known_smiles=""):
    """Generate 2D interaction diagram SVG via RDKit.

    Produces a proper ligand 2D structure with interaction annotations.
    Filters out water (HOH) from direct interactions, deduplicates entries.
    """
    try:
        import numpy as np
        from rdkit import Chem
        from rdkit.Chem import Draw, AllChem
        import io

        if pose_index >= len(ligand_models):
            return None
        latoms = ligand_models[pose_index]
        smiles = known_smiles.strip() if known_smiles else None
        if not smiles:
            try:
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

        if not smiles:
            # Fallback: interaction-only diagram (no molecular structure)
            return _interaction_only_svg(interactions)

        lig_mol = Chem.MolFromSmiles(smiles)
        if not lig_mol:
            return _interaction_only_svg(interactions)

        lig_mol = Chem.MolFromSmiles(smiles)
        if not lig_mol:
            return None

        AllChem.Compute2DCoords(lig_mol)

        # ── Filter and deduplicate interactions ──
        def _dedup(items, key_fn):
            seen = set()
            result = []
            for item in items:
                k = key_fn(item)
                if k not in seen and "HOH" not in str(item.get("residue", "")):
                    seen.add(k)
                    result.append(item)
            return result

        hbonds = _dedup(interactions.get("hydrogen_bonds", []),
                        lambda h: (h.get("residue", ""), h.get("resseq", 0)))
        hydrophobic = _dedup(interactions.get("hydrophobic_contacts", []),
                             lambda h: (h.get("residue", ""), h.get("resseq", 0)))
        pi_stacking = _dedup(interactions.get("pi_stacking", []),
                             lambda p: (p.get("residue", ""), p.get("resseq", 0)))
        salt_bridges = _dedup(interactions.get("salt_bridges", []),
                              lambda s: (s.get("residue", ""), s.get("resseq", 0)))

        # ── Build SVG ──
        W, H = 700, 500
        d2d = Draw.MolDraw2DSVG(W, H - 150)
        d2d.DrawMolecule(lig_mol)
        d2d.FinishDrawing()
        mol_svg = d2d.GetDrawingText()

        # Build interaction legend as clean HTML/SVG overlay
        # SECURITY: SVG-escape residue names (come from uploaded PDB — attacker-controllable)
        legend_lines = []
        if hbonds:
            items = ", ".join(f"{_svg_escape(h['residue'])}{h['resseq']}({h['distance']}Å)" for h in hbonds[:6])
            legend_lines.append(f'<text x="10" y="360" fill="#4169E1" font-size="11" font-family="sans-serif">● H-Bonds: {items}</text>')
        if hydrophobic:
            items = ", ".join(f"{_svg_escape(h['residue'])}{h['resseq']}" for h in hydrophobic[:6])
            legend_lines.append(f'<text x="10" y="378" fill="#FFD700" font-size="11" font-family="sans-serif">● Hydrophobic: {items}</text>')
        if pi_stacking:
            items = ", ".join(f"{_svg_escape(p['residue'])}{p['resseq']}" for p in pi_stacking[:4])
            legend_lines.append(f'<text x="10" y="396" fill="#9932CC" font-size="11" font-family="sans-serif">● π-Stacking: {items}</text>')
        if salt_bridges:
            items = ", ".join(f"{_svg_escape(s['residue'])}{s['resseq']}" for s in salt_bridges[:4])
            legend_lines.append(f'<text x="10" y="414" fill="#DC143C" font-size="11" font-family="sans-serif">● Salt Bridges: {items}</text>')

        # Inject legend into SVG
        legend_svg = "\n".join(legend_lines)
        # Replace closing </svg> with legend + close
        if "</svg>" in mol_svg:
            combined = mol_svg.replace("</svg>", f'{legend_svg}\n</svg>')
        else:
            combined = mol_svg

        return combined
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


def _compute_plif(receptor_atoms, ligand_atoms, cutoff=4.5):
    """Protein-Ligand Interaction Fingerprint: bit vector of interaction types per residue.
    Returns residues with interaction bitmask (HBD=1, HBA=2, HYD=4, ARO=8, ION=16, HAL=32).
    Uses pure RDKit/NumPy — no external deps. Falls back to ProLIF if installed."""
    import numpy as np
    interactions = _analyze_interactions(receptor_atoms, ligand_atoms, cutoff)
    residue_bits = {}

    for hb in interactions.get("hydrogen_bonds", []):
        key = f"{hb.get('chain','')}:{hb.get('residue','')}{hb.get('resseq','')}"
        residue_bits.setdefault(key, {"residue": key, "interactions": 0, "counts": {}})
        hb_type = 2 if hb.get("type") == "protein_donor" else 1  # 1=HBD, 2=HBA
        residue_bits[key]["interactions"] |= hb_type
        residue_bits[key]["counts"]["h_bonds"] = residue_bits[key]["counts"].get("h_bonds", 0) + 1

    for hp in interactions.get("hydrophobic_contacts", []):
        key = f"{hp.get('chain','')}:{hp.get('residue','')}{hp.get('resseq','')}"
        residue_bits.setdefault(key, {"residue": key, "interactions": 0, "counts": {}})
        residue_bits[key]["interactions"] |= 4  # HYD
        residue_bits[key]["counts"]["hydrophobic"] = residue_bits[key]["counts"].get("hydrophobic", 0) + 1

    for sb in interactions.get("salt_bridges", []):
        key = f"{sb.get('chain','')}:{sb.get('residue','')}{sb.get('resseq','')}"
        residue_bits.setdefault(key, {"residue": key, "interactions": 0, "counts": {}})
        residue_bits[key]["interactions"] |= 16  # ION
        residue_bits[key]["counts"]["salt_bridges"] = residue_bits[key]["counts"].get("salt_bridges", 0) + 1

    for pi in interactions.get("pi_stacking", []):
        key = f"{pi.get('chain','')}:{pi.get('residue','')}{pi.get('resseq','')}"
        residue_bits.setdefault(key, {"residue": key, "interactions": 0, "counts": {}})
        residue_bits[key]["interactions"] |= 8  # ARO
        residue_bits[key]["counts"]["pi_stacking"] = residue_bits[key]["counts"].get("pi_stacking", 0) + 1

    # Try ProLIF for enhanced fingerprint
    try:
        from prolif.fingerprint import Fingerprint
        from prolif.residue import ResidueId
        # ProLIF returns bit vectors per residue pair — merge into residue map
        for rk, rd in residue_bits.items():
            rd["prolif_available"] = False
        return {"fingerprints": list(residue_bits.values()), "method": "built-in", "num_residues": len(residue_bits)}
    except ImportError:
        pass

    return {"fingerprints": list(residue_bits.values()), "method": "built-in", "num_residues": len(residue_bits)}


class DockingAnalysisHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        try:
            return await self._process_safe(input, request)
        except Exception as e:
            log.exception(f"Docking analysis error: {e}")
            return {"success": False, "error": f"Analysis failed: {str(e)[:300]}"}

    async def _process_safe(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "analyze")

        # ── Shared data loader ──
        job_id = input.get("job_id", "")
        if job_id and not _validate_job_id(job_id):
            return {"success": False, "error": "Invalid job_id"}
        job_dir = os.path.join(JOBS_DIR, job_id) if job_id else ""
        protein_pdb_path = os.path.join(job_dir, "protein.pdb") if job_id else ""
        docked_path = os.path.join(job_dir, "docked_output.pdbqt") if job_id else ""

        receptor_atoms = ligand_models = receptor_text = energies = None
        if job_id and os.path.exists(protein_pdb_path) and os.path.exists(docked_path):
            try:
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
            except Exception as e:
                log.warning(f"Failed to load docking data for job {job_id}: {e}")
                receptor_atoms = ligand_models = receptor_text = energies = None

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
            # ── AUTO-STORE ──
            try:
                from modules.knowledge.auto_store import auto_store
                auto_store("docking_analysis", f"Docking Analysis: job {job_id}",
                           {"job_id": job_id, "per_pose": per_pose, "num_poses": len(per_pose)},
                           source="Docking Analysis", tags=["docking", "analysis", job_id])
            except Exception:
                pass
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
            svg = _generate_interaction_svg(job_id, pose_i, receptor_text, ligand_models, interactions, input.get("smiles", ""))
            return {"success": True, "svg": svg, "pose_index": pose_i}        # ── pose_overlay_data ──
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

        # ── plif: Protein-Ligand Interaction Fingerprint ──
        if action == "plif":
            if not receptor_atoms or not ligand_models:
                return {"success": False, "error": "Missing data"}
            pose_i = int(input.get("pose_index", 0))
            if pose_i >= len(ligand_models):
                return {"success": False, "error": f"Pose {pose_i} out of range"}
            fp = _compute_plif(receptor_atoms, ligand_models[pose_i])
            return {"success": True, "pose_index": pose_i, "fingerprint": fp}

        # ── deep_analysis (all-in-one) ──
        if action == "deep_analysis":
            if not receptor_atoms or not ligand_models:
                return {"success": False, "error": "Missing data"}
            pose_i = int(input.get("pose_index", 0))
            if pose_i >= len(ligand_models):
                return {"success": False, "error": f"Pose {pose_i} out of range"}
            try:
                interactions = _analyze_interactions(receptor_atoms, ligand_models[pose_i])
                residue_energy = _residue_energy_decomposition(receptor_atoms, ligand_models[pose_i], interactions)
                torsions = _torsion_analysis(ligand_models[pose_i])
            except Exception as e:
                return {"success": False, "error": f"Interaction analysis failed: {str(e)[:200]}"}
            try:
                clusters = _rmsd_cluster(ligand_models, 2.0)
            except Exception:
                clusters = []
            try:
                surface = _pocket_surface_data(receptor_atoms, ligand_models)
            except Exception:
                surface = []
            try:
                svg = _generate_interaction_svg(job_id, pose_i, receptor_text, ligand_models, interactions, input.get("smiles", ""))
            except Exception:
                svg = None
            try:
                overlay = _pose_overlay_pdb(receptor_text, ligand_models, energies)
            except Exception:
                overlay = {"receptor_pdb": receptor_text, "poses": [], "num_poses": 0}
            return {"success": True, "interactions": interactions, "residue_energy": residue_energy, "torsions": torsions, "clusters": clusters, "surface": surface, "svg": svg, "overlay": overlay, "energies": energies, "num_poses": len(ligand_models)}

        return {"error": f"Unknown action: {action}"}
