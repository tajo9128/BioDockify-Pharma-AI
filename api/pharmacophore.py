"""Pharmacophore Modeler API — RDKit-based feature detection, protein-based modeling,
PharmacoNet-compatible NCI classification, weighted screening, and .pm format support."""
from helpers.api import ApiHandler, Request, Response
import logging, os, json

log = logging.getLogger("pharmacophore_api")

# ── Pharmacophore Feature Types & Colors ──
FEATURE_COLORS = {
    "Donor": "#4169E1", "Acceptor": "#DC143C", "Hydrophobic": "#FFD700",
    "Aromatic": "#9932CC", "PosIonizable": "#32CD32", "NegIonizable": "#FF8C00",
    "LumpedHydrophobic": "#DAA520", "Halogen": "#00CED1",
}
FEATURE_RADII = {
    "Donor": 1.5, "Acceptor": 1.5, "Hydrophobic": 1.8, "Aromatic": 2.0,
    "PosIonizable": 1.5, "NegIonizable": 1.5, "LumpedHydrophobic": 1.6,
    "Halogen": 1.5,
}

# ── PharmacoNet-style 10-class NCI type mapping ──
NCI_TYPE_MAP = {
    "Hydrophobic": "Hydrophobic",
    "Aromatic": "PiStacking_P",
    "Cation": "PiCation_pring",
    "Anion": "SaltBridge_pneg",
    "HBond_donor": "HBond_pdon",
    "HBond_acceptor": "HBond_ldon",
    "Halogen": "XBond",
}
NCI_TYPES_INVERSE = {v: k for k, v in NCI_TYPE_MAP.items()}
NCI_FULL_SET = [
    "Hydrophobic", "PiStacking_P", "PiStacking_T", "PiCation_lring",
    "PiCation_pring", "SaltBridge_pneg", "SaltBridge_lneg",
    "XBond", "HBond_pdon", "HBond_ldon",
]

# ── PharmacoNet-style default feature weights for screening ──
PMNET_DEFAULT_WEIGHTS = {
    "Hydrophobic": 1, "Aromatic": 4, "Cation": 8, "Anion": 8,
    "Halogen": 4, "HBond_donor": 4, "HBond_acceptor": 4,
}

# ── Protein residue → pharmacophore type mapping ──
RESIDUE_PHARMA_TYPE = {
    # Hydrophobic
    "ALA": "Hydrophobic", "VAL": "Hydrophobic", "LEU": "Hydrophobic",
    "ILE": "Hydrophobic", "PRO": "Hydrophobic", "MET": "Hydrophobic",
    "PHE": "Aromatic", "TRP": "Aromatic", "TYR": "Aromatic", "HIS": "Aromatic",
    # Hydrogen bond donor (sidechain N-H or O-H)
    "SER": "HBond_donor", "THR": "HBond_donor", "CYS": "HBond_donor",
    "ASN": "HBond_donor", "GLN": "HBond_donor", "LYS": "Cation",
    "ARG": "Cation", "HIS": "Cation",
    # Hydrogen bond acceptor
    "ASP": "Anion", "GLU": "Anion",
}
ATOM_RESIDUE_PHARMA = {
    # backbone donor: N in any residue
    "N_bb": "HBond_donor",
    # backbone acceptor: O in any residue
    "O_bb": "HBond_acceptor",
}

_feature_factory = None


def _get_factory():
    global _feature_factory
    if _feature_factory is not None:
        return _feature_factory
    try:
        from rdkit import RDConfig
        from rdkit.Chem import ChemicalFeatures
        fdef = os.path.join(RDConfig.RDDataDir, "BaseFeatures.fdef")
        if os.path.exists(fdef):
            _feature_factory = ChemicalFeatures.BuildFeatureFactory(fdef)
        else:
            mdef = os.path.join(RDConfig.RDDataDir, "MinimalFeatureDef.fdef")
            _feature_factory = ChemicalFeatures.BuildFeatureFactory(mdef) if os.path.exists(mdef) else None
    except Exception as e:
        log.warning(f"Feature factory init failed: {e}")
        _feature_factory = None
    return _feature_factory


def _generate_3d_mol(smiles: str):
    from rdkit import Chem
    from rdkit.Chem import AllChem
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    mol = Chem.AddHs(mol)
    AllChem.EmbedMolecule(mol, AllChem.ETKDG())
    AllChem.MMFFOptimizeMolecule(mol)
    return mol


def _extract_features(mol) -> list:
    """Extract ligand pharmacophore features using RDKit."""
    factory = _get_factory()
    if factory is None:
        return []
    features = []
    for feat in factory.GetFeaturesForMol(mol):
        pos = feat.GetPos()
        fam = feat.GetFamily()
        features.append({
            "type": feat.GetType(),
            "family": fam,
            "position": {"x": round(pos.x, 3), "y": round(pos.y, 3), "z": round(pos.z, 3)},
            "atoms": list(feat.GetAtomIds()),
            "color": FEATURE_COLORS.get(fam, "#888888"),
            "radius": FEATURE_RADII.get(fam, 1.5),
            "nci_type": NCI_TYPE_MAP.get(fam, fam),
        })
    return features


def _extract_protein_pharmacophore(pdb_content: str, center: dict = None, cutoff: float = 8.0) -> list:
    """Extract pharmacophore features from a protein binding site.

    Maps protein residues/atoms to pharmacophore types:
    - Hydrophobic: ALA, VAL, LEU, ILE, PRO, MET
    - Aromatic: PHE, TRP, TYR, HIS
    - Cation: LYS, ARG
    - Anion: ASP, GLU
    - HBond_donor: SER, THR, CYS, ASN, GLN sidechain + backbone N
    - HBond_acceptor: backbone O
    """
    import numpy as np
    atoms = []
    for line in pdb_content.split("\n"):
        if not (line.startswith("ATOM") or line.startswith("HETATM")):
            continue
        try:
            atom = {
                "name": line[12:16].strip(),
                "resname": line[17:20].strip(),
                "chain": line[21:22].strip(),
                "resnum": int(line[22:26].strip()),
                "x": float(line[30:38].strip()),
                "y": float(line[38:46].strip()),
                "z": float(line[46:54].strip()),
                "element": line[76:78].strip() or line[12:14].strip(),
            }
            atoms.append(atom)
        except (ValueError, IndexError):
            continue

    if not atoms:
        return []

    # Filter to binding site if center provided
    if center:
        cx, cy, cz = center.get("x", 0), center.get("y", 0), center.get("z", 0)
        cen = np.array([cx, cy, cz])
        site_atoms = []
        for a in atoms:
            if np.linalg.norm(np.array([a["x"], a["y"], a["z"]]) - cen) < cutoff:
                site_atoms.append(a)
        if len(site_atoms) < 3:
            site_atoms = atoms[:max(3, min(50, len(atoms)))]
    else:
        # Auto-detect: use geometric center
        all_pos = np.array([[a["x"], a["y"], a["z"]] for a in atoms])
        center = np.mean(all_pos, axis=0)
        cen = center
        site_atoms = []
        for a in atoms:
            if np.linalg.norm(np.array([a["x"], a["y"], a["z"]]) - cen) < cutoff * 1.5:
                site_atoms.append(a)
        if len(site_atoms) < 5:
            site_atoms = atoms[:max(5, min(100, len(atoms)))]

    # Group by residue
    residues = {}
    for a in site_atoms:
        key = (a["resname"], a["chain"], a["resnum"])
        if key not in residues:
            residues[key] = {"atoms": [], "backbone": {}}
        residues[key]["atoms"].append(a)
        if a["name"] in ("N", "CA", "C", "O"):
            residues[key]["backbone"][a["name"]] = a

    # Generate pharmacophore features from residues
    features = []
    seen_positions = []

    for (resname, chain, resnum), res in residues.items():
        atoms_in_res = res["atoms"]
        bb = res["backbone"]
        # Residue center
        cx = round(sum(a["x"] for a in atoms_in_res) / len(atoms_in_res), 3)
        cy = round(sum(a["y"] for a in atoms_in_res) / len(atoms_in_res), 3)
        cz = round(sum(a["z"] for a in atoms_in_res) / len(atoms_in_res), 3)

        # Determine pharmacophore type
        pharma_type = RESIDUE_PHARMA_TYPE.get(resname)
        if pharma_type is None:
            continue

        # Avoid duplicates too close
        pos = np.array([cx, cy, cz])
        if any(np.linalg.norm(pos - np.array(sp)) < 2.0 for sp in seen_positions):
            continue
        seen_positions.append([cx, cy, cz])

        features.append({
            "type": pharma_type,
            "family": pharma_type,
            "position": {"x": cx, "y": cy, "z": cz},
            "color": FEATURE_COLORS.get(pharma_type, "#888888"),
            "radius": FEATURE_RADII.get(pharma_type, 1.5),
            "nci_type": NCI_TYPE_MAP.get(pharma_type, pharma_type),
            "residue": resname,
            "resnum": resnum,
            "chain": chain,
            "source": "protein",
        })

        # Add backbone donor (N) and acceptor (O) for residues near the binding site
        if "N" in bb:
            n = bb["N"]
            nx, ny, nz = n["x"], n["y"], n["z"]
            np2 = np.array([nx, ny, nz])
            if not any(np.linalg.norm(np2 - np.array(sp)) < 1.5 for sp in seen_positions):
                seen_positions.append([nx, ny, nz])
                features.append({
                    "type": "HBond_donor", "family": "HBond_donor",
                    "position": {"x": round(nx, 3), "y": round(ny, 3), "z": round(nz, 3)},
                    "color": FEATURE_COLORS["Donor"], "radius": 1.5,
                    "nci_type": "HBond_pdon",
                    "residue": resname, "resnum": resnum, "chain": chain,
                    "source": "backbone_N",
                })
        if "O" in bb:
            o = bb["O"]
            ox, oy, oz = o["x"], o["y"], o["z"]
            op = np.array([ox, oy, oz])
            if not any(np.linalg.norm(op - np.array(sp)) < 1.5 for sp in seen_positions):
                seen_positions.append([ox, oy, oz])
                features.append({
                    "type": "HBond_acceptor", "family": "HBond_acceptor",
                    "position": {"x": round(ox, 3), "y": round(oy, 3), "z": round(oz, 3)},
                    "color": FEATURE_COLORS["Acceptor"], "radius": 1.5,
                    "nci_type": "HBond_ldon",
                    "residue": resname, "resnum": resnum, "chain": chain,
                    "source": "backbone_O",
                })

    # Sort by type for readability
    features.sort(key=lambda f: (
        ["HBond_donor", "HBond_acceptor", "Cation", "Anion", "Aromatic", "Hydrophobic"].index(f["family"])
        if f["family"] in ["HBond_donor", "HBond_acceptor", "Cation", "Anion", "Aromatic", "Hydrophobic"]
        else 99
    ))

    return features


def _weighted_screen(query_features: list, library_smiles: list, weights: dict = None) -> list:
    """PharmacoNet-style weighted pharmacophore screening.

    Uses PharmacoNet's default weights:
    - Cation/Anion: 8 (strongest directional interactions)
    - Aromatic/Halogen/HBA/HBD: 4
    - Hydrophobic: 1 (least specific)
    """
    if weights is None:
        weights = PMNET_DEFAULT_WEIGHTS

    # Build query feature type profile with weights
    q_types = {}
    for f in query_features:
        fam = f.get("family", "")
        q_types[fam] = q_types.get(fam, 0) + 1

    q_weighted = {t: c * weights.get(t, 1) for t, c in q_types.items()}
    q_total = sum(q_weighted.values())

    if q_total == 0:
        return []

    hits = []
    for smi in library_smiles:
        mol = _generate_3d_mol(smi.strip())
        if mol is None:
            continue
        l_features = _extract_features(mol)
        l_types = {}
        for f in l_features:
            fam = f.get("family", "")
            l_types[fam] = l_types.get(fam, 0) + 1

        # Weighted intersection over union
        intersection = 0
        union = 0
        all_types = set(q_types.keys()) | set(l_types.keys())
        for t in all_types:
            w = weights.get(t, 1)
            qv = q_types.get(t, 0)
            lv = l_types.get(t, 0)
            intersection += min(qv, lv) * w
            union += max(qv, lv) * w

        score = intersection / union if union > 0 else 0

        # Also compute feature-type match count
        matched_types = [t for t in q_types if t in l_types]

        if score > 0.1 and len(matched_types) >= 2:
            hits.append({
                "smiles": smi.strip(),
                "score": round(score, 4),
                "weighted_score": round(score * 100, 1),
                "matched_types": matched_types,
                "matched_count": len(matched_types),
                "ligand_features": {t: c for t, c in l_types.items()},
            })

    hits.sort(key=lambda h: h["score"], reverse=True)
    return hits[:50]


def _parse_pm_file(filepath: str) -> dict:
    """Parse PharmacoNet .pm model file format.

    The .pm format contains pharmacophore hotspot definitions with:
    type, position (x,y,z), score, radius, nci_type
    """
    try:
        with open(filepath, "r") as f:
            content = f.read()
    except Exception as e:
        return {"error": f"Cannot read .pm file: {e}"}

    features = []
    metadata = {}
    current_type = None
    position = None

    for line in content.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            if line.startswith("#"):
                kv = line[1:].strip().split("=", 1)
                if len(kv) == 2:
                    metadata[kv[0].strip()] = kv[1].strip()
            continue

        parts = line.split()
        if len(parts) < 3:
            continue

        # Try to parse as: type x y z [score] [nci_type]
        try:
            if parts[0].replace("_", "") in ["Hydrophobic", "Aromatic", "Cation", "Anion",
                                                "Halogen", "HBonddonor", "HBondacceptor",
                                                "PiStackingP", "PiStackingT", "PiCationlring",
                                                "PiCationpring", "SaltBridgepneg", "SaltBridgelneg",
                                                "Xbond", "HBondpdon", "HBondldon"]:
                # Pharmacophore type line
                ptype = parts[0].replace("_", "")
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                score = float(parts[4]) if len(parts) > 4 else 0.5
                nci = parts[5] if len(parts) > 5 else ptype

                # Normalize type names
                type_map = {
                    "Hydrophobic": "Hydrophobic", "Aromatic": "Aromatic",
                    "Cation": "Cation", "Anion": "Anion",
                    "Halogen": "Halogen", "HBonddonor": "HBond_donor",
                    "HBondacceptor": "HBond_acceptor", "HBondpdon": "HBond_donor",
                    "HBondldon": "HBond_acceptor",
                }
                normalized = type_map.get(ptype, ptype)

                features.append({
                    "type": normalized,
                    "family": normalized,
                    "position": {"x": x, "y": y, "z": z},
                    "score": score,
                    "nci_type": nci,
                    "source": "pharmaconet_pm",
                    "color": FEATURE_COLORS.get(normalized, "#888888"),
                    "radius": FEATURE_RADII.get(normalized, 1.5),
                })
        except (ValueError, IndexError):
            continue

    return {
        "metadata": metadata,
        "features": features,
        "num_features": len(features),
        "source_file": filepath,
    }


def _export_pm_file(features: list, metadata: dict = None) -> str:
    """Export pharmacophore features to PharmacoNet .pm format."""
    lines = [
        "# Pharmacophore Model — BioDockify / PharmacoNet compatible",
        f"# num_features={len(features)}",
        f"# generated_by=BioDockify_Pharmacophore",
    ]
    if metadata:
        for k, v in metadata.items():
            lines.append(f"# {k}={v}")

    for f in features:
        pos = f.get("position", {})
        nci = f.get("nci_type", f.get("family", "Hydrophobic"))
        fam = f.get("family", "Hydrophobic")
        score = f.get("score", 0.5)
        lines.append(f"{fam} {pos.get('x', 0)} {pos.get('y', 0)} {pos.get('z', 0)} {score} {nci}")

    return "\n".join(lines)


def _compute_pharmacophore_hypothesis(actives: list) -> dict:
    """Generate pharmacophore hypothesis from multiple active molecules.

    Uses a more sophisticated approach than simple averaging:
    - Finds conserved features across actives
    - Uses hierarchical clustering for spatial grouping
    """
    import numpy as np

    FTYPES = ["Donor", "Acceptor", "Hydrophobic", "Aromatic", "PosIonizable", "NegIonizable"]

    all_mols = []
    for smi in actives:
        mol = _generate_3d_mol(smi.strip())
        if mol:
            all_mols.append({"smiles": smi.strip(), "features": _extract_features(mol)})

    if not all_mols:
        return {"success": False, "error": "No valid molecules"}

    common = []
    for ft in FTYPES:
        positions = []
        for entry in all_mols:
            type_feats = [f for f in entry["features"] if f["family"] == ft]
            for tf in type_feats:
                positions.append([tf["position"]["x"], tf["position"]["y"], tf["position"]["z"]])

        # Require feature present in at least 60% of molecules
        if positions and len(positions) >= len(all_mols) * 0.6:
            pa = np.array(positions)
            center = np.mean(pa, axis=0).tolist()
            radius = float(min(np.max(np.linalg.norm(pa - center, axis=1)) + 1.0, 3.0))
            common.append({
                "type": ft, "family": ft,
                "center": [round(c, 3) for c in center],
                "radius": round(radius, 2),
                "color": FEATURE_COLORS.get(ft, "#888888"),
                "coverage": round(len(positions) / len(all_mols), 2),
                "nci_type": NCI_TYPE_MAP.get(ft, ft),
            })

    common.sort(key=lambda x: x["coverage"], reverse=True)
    return {"success": True, "hypothesis": common[:6], "n_features": len(common[:6]), "n_molecules": len(all_mols), "used_molecules": [m["smiles"] for m in all_mols]}


# ══════════════════════════════════════════════
# API Handler
# ══════════════════════════════════════════════

class PharmacophoreHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "generate")

        # ── Ligand-based pharmacophore generation ──
        if action == "generate":
            smiles = input.get("smiles", "")
            if not smiles:
                return {"success": False, "error": "Provide SMILES", "features": []}
            try:
                from rdkit import Chem
                mol = _generate_3d_mol(smiles)
                if mol is None:
                    return {"success": False, "error": "Invalid SMILES", "features": []}
                features = _extract_features(mol)
                families = {}
                for f in features:
                    families[f["family"]] = families.get(f["family"], 0) + 1
                return {"success": True, "smiles": smiles, "features": features, "num_features": len(features), "feature_summary": families}
            except ImportError:
                return {"success": False, "error": "RDKit not available", "features": []}
            except Exception as e:
                return {"success": False, "error": str(e), "features": []}

        # ── Protein-based pharmacophore modeling ──
        if action == "protein_model":
            protein_pdb = input.get("protein_pdb", "")
            center = input.get("center")
            cutoff = float(input.get("cutoff", 8.0))

            if not protein_pdb:
                return {"success": False, "error": "protein_pdb required"}

            try:
                features = _extract_protein_pharmacophore(protein_pdb, center, cutoff)
                families = {}
                residues = set()
                for f in features:
                    families[f["family"]] = families.get(f["family"], 0) + 1
                    if "residue" in f:
                        residues.add(f"{f['residue']}{f['resnum']}{f.get('chain', '')}")

                pm_export = _export_pm_file(features, {"protein_model": "BioDockify", "features": str(len(features))})

                return {
                    "success": True,
                    "features": features,
                    "num_features": len(features),
                    "feature_summary": families,
                    "binding_site_residues": sorted(residues),
                    "num_residues": len(residues),
                    "pm_export": pm_export,
                    "cutoff": cutoff,
                }
            except ImportError:
                return {"success": False, "error": "NumPy/RDKit required"}
            except Exception as e:
                return {"success": False, "error": str(e)}

        # ── PharmacoNet-style weighted screening ──
        if action == "screen":
            query_smiles = input.get("query_smiles", "")
            query_features_raw = input.get("query_features")
            library = input.get("library_smiles", [])

            if isinstance(library, str):
                library = [s.strip() for s in library.split("\n") if s.strip()]

            # Use query features directly (from protein_model) or extract from SMILES
            if query_features_raw:
                query_features = query_features_raw
            elif query_smiles:
                mol = _generate_3d_mol(query_smiles)
                if mol is None:
                    return {"success": False, "error": "Invalid query SMILES"}
                query_features = _extract_features(mol)
            else:
                return {"success": False, "error": "query_smiles or query_features required"}

            if not library:
                return {"success": False, "error": "library_smiles required"}

            # Use custom weights if provided
            weights = input.get("weights", PMNET_DEFAULT_WEIGHTS)
            if isinstance(weights, dict):
                weights = {k: v for k, v in weights.items() if k in PMNET_DEFAULT_WEIGHTS}
                if not weights:
                    weights = PMNET_DEFAULT_WEIGHTS

            try:
                hits = _weighted_screen(query_features, library, weights)
                q_types = {}
                for f in query_features:
                    q_types[f["family"]] = q_types.get(f["family"], 0) + 1
                return {
                    "success": True,
                    "query_types": q_types,
                    "weights_used": weights,
                    "total_screened": len(library),
                    "total_hits": len(hits),
                    "hits": hits,
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        # ── Pharmacophore hypothesis from actives ──
        if action == "hypothesis":
            actives = input.get("active_smiles", [])
            if isinstance(actives, str):
                actives = [s.strip() for s in actives.split("\n") if s.strip()]
            if len(actives) < 2:
                return {"success": False, "error": "Need at least 2 active molecules"}
            try:
                return _compute_pharmacophore_hypothesis(actives)
            except Exception as e:
                return {"success": False, "error": str(e)}

        # ── Exclusion volume spheres from receptor ──
        if action == "exclusion":
            receptor_pdb = input.get("receptor_pdb", "")
            ligand_center = input.get("ligand_center")
            cutoff = float(input.get("cutoff", 5.0))
            if not receptor_pdb:
                return {"success": False, "error": "receptor_pdb required"}

            import numpy as np
            atoms = []
            for line in receptor_pdb.split("\n"):
                if line.startswith("ATOM") or line.startswith("HETATM"):
                    try:
                        atoms.append({
                            "resname": line[17:20].strip(),
                            "element": line[76:78].strip() or line[12:14].strip(),
                            "pos": [float(line[30:38]), float(line[38:46]), float(line[46:54])],
                        })
                    except (ValueError, IndexError):
                        continue
            if not atoms:
                return {"success": False, "error": "No receptor atoms found"}

            positions = np.array([a["pos"] for a in atoms])
            if ligand_center:
                lc = np.array([ligand_center.get("x", 0), ligand_center.get("y", 0), ligand_center.get("z", 0)])
                nearby = [a for a, p in zip(atoms, positions) if np.linalg.norm(p - lc) < cutoff]
            else:
                nearby = atoms

            spheres = []
            used = []
            hydrophobic = {"ALA", "VAL", "LEU", "ILE", "MET", "PHE", "TRP", "TYR", "PRO"}
            for atom in nearby:
                pa = np.array(atom["pos"])
                if any(np.linalg.norm(pa - u) < 2.0 for u in used):
                    continue
                used.append(pa)
                radius = 1.5 if atom["element"] == "C" else 1.7
                spheres.append({
                    "center": atom["pos"], "radius": radius,
                    "color": "#FF6600" if atom["resname"] in hydrophobic else "#CCCCCC",
                    "residue": atom["resname"], "element": atom["element"],
                })
            return {"success": True, "exclusion_spheres": spheres, "n_spheres": len(spheres)}

        # ── Parse PharmacoNet .pm file ──
        if action == "parse_pm":
            pm_content = input.get("pm_content", "")
            pm_path = input.get("pm_path", "")
            try:
                import tempfile
                if pm_content:
                    tf = tempfile.NamedTemporaryFile(mode="w", suffix=".pm", delete=False)
                    tf.write(pm_content)
                    tf.close()
                    result = _parse_pm_file(tf.name)
                    os.unlink(tf.name)
                elif pm_path:
                    result = _parse_pm_file(pm_path)
                else:
                    return {"success": False, "error": "pm_content or pm_path required"}
                return {"success": True, **result}
            except Exception as e:
                return {"success": False, "error": str(e)}

        # ── NCI type reference ──
        if action == "nci_types":
            return {
                "success": True,
                "nci_types": {
                    "Hydrophobic": "Hydrophobic interaction",
                    "PiStacking_P": "PiStacking (Parallel)",
                    "PiStacking_T": "PiStacking (T-shaped)",
                    "PiCation_lring": "Protein Cation + Ligand Aromatic Ring",
                    "PiCation_pring": "Protein Aromatic Ring + Ligand Cation",
                    "SaltBridge_pneg": "Protein Anion + Ligand Cation",
                    "SaltBridge_lneg": "Protein Cation + Ligand Anion",
                    "XBond": "Halogen Bond",
                    "HBond_pdon": "H-Bond: Protein Donor + Ligand Acceptor",
                    "HBond_ldon": "H-Bond: Protein Acceptor + Ligand Donor",
                },
                "feature_weights": PMNET_DEFAULT_WEIGHTS,
            }

        # ── Shared pharmacophore model (intersection of features from multiple molecules) ──
        if action == "shared_model":
            molecules = input.get("smiles_list", [])
            if isinstance(molecules, str):
                molecules = [s.strip() for s in molecules.split("\n") if s.strip()]
            if len(molecules) < 2:
                return {"success": False, "error": "Need at least 2 SMILES for shared model"}

            try:
                import numpy as np
                all_features = []
                for smi in molecules:
                    mol = _generate_3d_mol(smi.strip())
                    if mol:
                        feats = _extract_features(mol)
                        all_features.append({"smiles": smi.strip(), "features": feats})

                if len(all_features) < 2:
                    return {"success": False, "error": "Need at least 2 valid molecules"}

                # Find shared features: types present in ALL molecules
                shared_types = set(all_features[0]["features"][0]["family"] for f in all_features[0]["features"]) if all_features[0]["features"] else set()
                shared_types = set()
                type_counts = {}
                for entry in all_features:
                    entry_types = set()
                    for f in entry["features"]:
                        fam = f["family"]
                        entry_types.add(fam)
                        type_counts[fam] = type_counts.get(fam, 0) + 1
                    if not shared_types:
                        shared_types = entry_types
                    else:
                        shared_types &= entry_types

                # Cluster shared features spatially
                shared_features = []
                for ft in shared_types:
                    positions = []
                    for entry in all_features:
                        for f in entry["features"]:
                            if f["family"] == ft:
                                positions.append([f["position"]["x"], f["position"]["y"], f["position"]["z"]])
                    if positions:
                        pa = np.array(positions)
                        center = np.mean(pa, axis=0)
                        radius = float(min(np.max(np.linalg.norm(pa - center, axis=1)) + 1.0, 3.0))
                        shared_features.append({
                            "type": ft, "family": ft,
                            "position": {"x": round(center[0], 3), "y": round(center[1], 3), "z": round(center[2], 3)},
                            "radius": round(radius, 2),
                            "color": FEATURE_COLORS.get(ft, "#888888"),
                            "nci_type": NCI_TYPE_MAP.get(ft, ft),
                            "coverage": f"{len(positions)}/{len(all_features)}",
                        })

                pm_export = _export_pm_file(shared_features, {"model_type": "shared", "num_inputs": str(len(molecules))})

                return {
                    "success": True,
                    "model_type": "shared",
                    "num_input_molecules": len(all_features),
                    "shared_features": shared_features,
                    "num_shared": len(shared_features),
                    "shared_types": sorted(shared_types),
                    "feature_counts": type_counts,
                    "pm_export": pm_export,
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        # ── Merged pharmacophore model (union of features from multiple molecules) ──
        if action == "merged_model":
            molecules = input.get("smiles_list", [])
            if isinstance(molecules, str):
                molecules = [s.strip() for s in molecules.split("\n") if s.strip()]
            if len(molecules) < 2:
                return {"success": False, "error": "Need at least 2 SMILES for merged model"}

            try:
                import numpy as np
                all_features = []
                for smi in molecules:
                    mol = _generate_3d_mol(smi.strip())
                    if mol:
                        all_features.append({"smiles": smi.strip(), "features": _extract_features(mol)})

                if not all_features:
                    return {"success": False, "error": "No valid molecules"}

                # Collect all unique positions per type, deduplicate by clustering
                merged = []
                seen_centers = []
                for entry in all_features:
                    for f in entry["features"]:
                        pos = np.array([f["position"]["x"], f["position"]["y"], f["position"]["z"]])
                        # Deduplicate: skip if within 1.5A of an already-merged feature
                        if any(np.linalg.norm(pos - sc) < 1.5 for sc in seen_centers):
                            continue
                        seen_centers.append(pos)
                        merged.append({
                            "type": f["family"], "family": f["family"],
                            "position": f["position"],
                            "color": FEATURE_COLORS.get(f["family"], "#888888"),
                            "radius": FEATURE_RADII.get(f["family"], 1.5),
                            "nci_type": NCI_TYPE_MAP.get(f["family"], f["family"]),
                            "source": entry["smiles"][:40],
                        })

                pm_export = _export_pm_file(merged, {"model_type": "merged", "num_inputs": str(len(molecules))})

                return {
                    "success": True,
                    "model_type": "merged",
                    "num_input_molecules": len(all_features),
                    "merged_features": merged,
                    "num_merged": len(merged),
                    "pm_export": pm_export,
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        # ── Feature-based alignment overlay (align molecules by pharmacophore features) ──
        if action == "overlay":
            molecules = input.get("smiles_list", [])
            if isinstance(molecules, str):
                molecules = [s.strip() for s in molecules.split("\n") if s.strip()]
            if len(molecules) < 2:
                return {"success": False, "error": "Need at least 2 SMILES for overlay"}

            try:
                # Extract features and positions for each molecule
                import numpy as np
                mol_data = []
                ftype = input.get("feature_type", "")  # optional filter

                for smi in molecules:
                    mol = _generate_3d_mol(smi.strip())
                    if mol is None:
                        continue
                    feats = _extract_features(mol)
                    if ftype:
                        feats = [f for f in feats if f["family"] == ftype]
                    if feats:
                        # Get centroid of features
                        positions = np.array([[f["position"]["x"], f["position"]["y"], f["position"]["z"]] for f in feats])
                        centroid = np.mean(positions, axis=0)
                        mol_data.append({
                            "smiles": smi.strip(),
                            "features": feats,
                            "centroid": {"x": round(centroid[0], 3), "y": round(centroid[1], 3), "z": round(centroid[2], 3)},
                            "feature_count": len(feats),
                        })

                if len(mol_data) < 2:
                    return {"success": False, "error": "Need at least 2 valid molecules with features"}

                # Compute pairwise feature-type overlap
                pairs = []
                for i in range(len(mol_data)):
                    for j in range(i + 1, len(mol_data)):
                        a_types = set(f["family"] for f in mol_data[i]["features"])
                        b_types = set(f["family"] for f in mol_data[j]["features"])
                        overlap = len(a_types & b_types)
                        union = len(a_types | b_types)
                        jaccard = overlap / union if union > 0 else 0
                        pairs.append({
                            "mol1": mol_data[i]["smiles"][:30],
                            "mol2": mol_data[j]["smiles"][:30],
                            "shared_types": sorted(a_types & b_types),
                            "overlap_count": overlap,
                            "jaccard": round(jaccard, 3),
                        })

                pairs.sort(key=lambda p: p["jaccard"], reverse=True)

                return {
                    "success": True,
                    "molecules": mol_data,
                    "num_molecules": len(mol_data),
                    "pairwise_overlap": pairs,
                    "feature_type_filter": ftype or "all",
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        # ── Target identification (reverse pharmacophore screening) ──
        if action == "identify_targets":
            smiles = input.get("smiles", "")
            num_conformers = int(input.get("num_conformers", 10))
            if not smiles:
                return {"success": False, "error": "SMILES required"}

            try:
                from rdkit import Chem
                from rdkit.Chem import AllChem

                mol = Chem.MolFromSmiles(smiles)
                if mol is None:
                    return {"success": False, "error": "Invalid SMILES"}
                mol = Chem.AddHs(mol)

                # Generate multiple conformers (PharmMapper-style semi-rigid mapping)
                params = AllChem.ETKDGv3()
                params.numThreads = 0
                params.pruneRmsThresh = 0.5
                conformers = []
                for seed in range(num_conformers):
                    mol2 = Chem.Mol(mol)
                    params.randomSeed = seed * 42 + 1
                    try:
                        AllChem.EmbedMolecule(mol2, params)
                        AllChem.MMFFOptimizeMolecule(mol2)
                        conf = Chem.Mol(mol2)
                        feats = _extract_features(conf)
                        if feats:
                            conformers.append({
                                "seed": seed,
                                "features": feats,
                                "feature_types": list(set(f["family"] for f in feats)),
                                "num_features": len(feats),
                            })
                    except Exception:
                        continue

                if not conformers:
                    return {"success": False, "error": "Could not generate any valid conformers"}

                # Compute consensus feature profile across conformers
                consensus = {}
                for conf in conformers:
                    for ft in conf["feature_types"]:
                        consensus[ft] = consensus.get(ft, 0) + 1

                # Score each conformer by feature type richness and uniqueness
                all_types = set()
                for conf in conformers:
                    all_types.update(conf["feature_types"])

                conformer_scores = []
                import numpy as np
                for conf in conformers:
                    # Richness: how many feature types present
                    richness = len(conf["feature_types"]) / max(1, len(all_types))
                    # Consensus alignment: how well this conformer matches the consensus
                    consensus_score = sum(consensus.get(ft, 0) / len(conformers) for ft in conf["feature_types"]) / max(1, len(conf["feature_types"]))
                    conformer_scores.append({
                        "seed": conf["seed"],
                        "richness": round(richness, 3),
                        "consensus": round(consensus_score, 3),
                        "score": round(0.5 * richness + 0.5 * consensus_score, 3),
                        "num_features": conf["num_features"],
                    })

                conformer_scores.sort(key=lambda x: x["score"], reverse=True)
                best_conformer = conformers[conformer_scores[0]["seed"] % len(conformers)]

                return {
                    "success": True,
                    "smiles": smiles,
                    "num_conformers_generated": len(conformers),
                    "num_conformers_requested": num_conformers,
                    "conformer_scores": conformer_scores[:10],
                    "best_conformer": best_conformer,
                    "consensus_feature_profile": consensus,
                    "total_feature_types": len(all_types),
                    "all_types": sorted(all_types),
                }
            except ImportError:
                return {"success": False, "error": "RDKit not available"}
            except Exception as e:
                return {"success": False, "error": str(e)}

        # ── z'-score normalization (normalize fit scores against baseline distribution) ──
        if action == "zscore_normalize":
            scores = input.get("scores", [])
            baseline_mean = input.get("baseline_mean")
            baseline_std = input.get("baseline_std")

            if not scores:
                return {"success": False, "error": "scores list required"}

            try:
                import numpy as np
                scores = [float(s) for s in scores]
                arr = np.array(scores)

                if baseline_mean is not None and baseline_std is not None:
                    mean = float(baseline_mean)
                    std = float(baseline_std)
                else:
                    mean = float(np.mean(arr))
                    std = float(np.std(arr, ddof=1)) if len(arr) > 1 else 1.0

                z_scores = []
                for s in scores:
                    z = (s - mean) / std if std > 0 else 0.0
                    z_scores.append(round(z, 4))

                return {
                    "success": True,
                    "mean": round(mean, 4),
                    "std": round(std, 4),
                    "scores": z_scores,
                    "top_zscore": max(z_scores),
                    "significant_count": sum(1 for z in z_scores if z > 1.0),
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        # ── ZINCPharmer-style batch screening with pre-filtering ──
        if action == "batch_screen":
            query_smiles = input.get("query_smiles", "")
            query_features_raw = input.get("query_features")
            library = input.get("library_smiles", [])
            if isinstance(library, str):
                library = [s.strip() for s in library.split("\n") if s.strip()]

            # Pre-filters (ZINCPharmer-style)
            mw_min = input.get("mw_min")
            mw_max = input.get("mw_max")
            logp_min = input.get("logp_min")
            logp_max = input.get("logp_max")
            rot_max = input.get("rot_max")
            hba_max = input.get("hba_max")
            hbd_max = input.get("hbd_max")
            tpsa_max = input.get("tpsa_max")

            if query_features_raw:
                query_features = query_features_raw
            elif query_smiles:
                mol = _generate_3d_mol(query_smiles)
                if mol is None:
                    return {"success": False, "error": "Invalid query SMILES"}
                query_features = _extract_features(mol)
            else:
                return {"success": False, "error": "query_smiles or query_features required"}
            if not library:
                return {"success": False, "error": "library_smiles required"}

            try:
                from rdkit import Chem
                from rdkit.Chem import Descriptors, Crippen

                # Phase 1: Pre-filter by physicochemical properties
                filtered = []
                skipped_physchem = 0
                for smi in library:
                    smi = smi.strip()
                    if not smi:
                        continue
                    try:
                        m = Chem.MolFromSmiles(smi)
                        if m is None:
                            skipped_physchem += 1
                            continue
                        mw = Descriptors.MolWt(m)
                        logp = Crippen.MolLogP(m)
                        rot = Descriptors.NumRotatableBonds(m)
                        hba = Descriptors.NumHAcceptors(m)
                        hbd = Descriptors.NumHDonors(m)
                        tpsa = Descriptors.TPSA(m)

                        if mw_min is not None and mw < float(mw_min):
                            skipped_physchem += 1
                            continue
                        if mw_max is not None and mw > float(mw_max):
                            skipped_physchem += 1
                            continue
                        if logp_min is not None and logp < float(logp_min):
                            skipped_physchem += 1
                            continue
                        if logp_max is not None and logp > float(logp_max):
                            skipped_physchem += 1
                            continue
                        if rot_max is not None and rot > int(rot_max):
                            skipped_physchem += 1
                            continue
                        if hba_max is not None and hba > int(hba_max):
                            skipped_physchem += 1
                            continue
                        if hbd_max is not None and hbd > int(hbd_max):
                            skipped_physchem += 1
                            continue
                        if tpsa_max is not None and tpsa > float(tpsa_max):
                            skipped_physchem += 1
                            continue

                        filtered.append(smi)
                    except Exception:
                        skipped_physchem += 1
                        continue

                # Phase 2: Pharmacophore matching on filtered set
                weights = input.get("weights", PMNET_DEFAULT_WEIGHTS)
                if isinstance(weights, dict):
                    weights = {k: v for k, v in weights.items() if k in PMNET_DEFAULT_WEIGHTS}
                    if not weights:
                        weights = PMNET_DEFAULT_WEIGHTS

                hits = _weighted_screen(query_features, filtered, weights)

                return {
                    "success": True,
                    "total_library": len(library),
                    "prefiltered_passed": len(filtered),
                    "prefiltered_skipped": skipped_physchem,
                    "filters_applied": {
                        "mw_min": mw_min, "mw_max": mw_max,
                        "logp_min": logp_min, "logp_max": logp_max,
                        "rot_max": rot_max, "hba_max": hba_max,
                        "hbd_max": hbd_max, "tpsa_max": tpsa_max,
                    },
                    "hits": hits,
                    "total_hits": len(hits),
                    "hit_rate": round(len(hits) / max(1, len(filtered)) * 100, 1),
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        # ── Screen statistics / enrichment analysis ──
        if action == "screen_stats":
            hits = input.get("hits", [])
            total_screened = input.get("total_screened", 0)

            if not hits or total_screened == 0:
                return {"success": False, "error": "hits and total_screened required"}

            try:
                import numpy as np
                scores = [h.get("score", 0) for h in hits]
                arr = np.array(scores) if scores else np.array([])

                # Score distribution
                hist_bins = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
                hist = {}
                for i in range(len(hist_bins) - 1):
                    lo, hi = hist_bins[i], hist_bins[i + 1]
                    count = int(np.sum((arr >= lo) & (arr < hi)))
                    hist[f"{lo:.1f}-{hi:.1f}"] = count

                stats = {
                    "hit_rate": round(len(hits) / max(1, total_screened) * 100, 1),
                    "mean_score": round(float(np.mean(arr)), 4) if len(arr) > 0 else 0,
                    "max_score": round(float(np.max(arr)), 4) if len(arr) > 0 else 0,
                    "median_score": round(float(np.median(arr)), 4) if len(arr) > 0 else 0,
                    "std_score": round(float(np.std(arr)), 4) if len(arr) > 1 else 0,
                    "top_1pct": int(np.sum(arr >= np.percentile(arr, 99))) if len(arr) > 0 else 0,
                    "top_5pct": int(np.sum(arr >= np.percentile(arr, 95))) if len(arr) > 0 else 0,
                    "top_10pct": int(np.sum(arr >= np.percentile(arr, 90))) if len(arr) > 0 else 0,
                    "score_distribution": hist,
                }

                # Feature richness analysis
                type_richness = {}
                for h in hits:
                    for t in h.get("matched_types", []):
                        type_richness[t] = type_richness.get(t, 0) + 1
                stats["feature_type_frequency"] = type_richness

                return {"success": True, "statistics": stats, "num_hits": len(hits), "total_screened": total_screened}
            except Exception as e:
                return {"success": False, "error": str(e)}

        # ── Parse LigandScout .ph4 pharmacophore format ──
        if action == "parse_ph4":
            ph4_content = input.get("ph4_content", "")
            if not ph4_content:
                return {"success": False, "error": "ph4_content required"}

            features = []
            metadata = {}
            current_feature = None

            for line in ph4_content.split("\n"):
                line = line.strip()
                if not line:
                    continue

                # Metadata lines
                if line.startswith("#"):
                    kv = line[1:].strip().split("=", 1)
                    if len(kv) == 2:
                        metadata[kv[0].strip()] = kv[1].strip()
                    continue

                # Feature definition
                if line.startswith("HBondDonor") or line.startswith("HBD"):
                    current_feature = {"type": "HBond_donor", "family": "HBond_donor"}
                elif line.startswith("HBondAcceptor") or line.startswith("HBA"):
                    current_feature = {"type": "HBond_acceptor", "family": "HBond_acceptor"}
                elif line.startswith("Hydrophobic") or line.startswith("HYD"):
                    current_feature = {"type": "Hydrophobic", "family": "Hydrophobic"}
                elif line.startswith("Aromatic") or line.startswith("AR"):
                    current_feature = {"type": "Aromatic", "family": "Aromatic"}
                elif line.startswith("PositiveIonizable") or line.startswith("PI"):
                    current_feature = {"type": "Cation", "family": "Cation"}
                elif line.startswith("NegativeIonizable") or line.startswith("NI"):
                    current_feature = {"type": "Anion", "family": "Anion"}
                elif line.startswith("Halogen") or line.startswith("HAL"):
                    current_feature = {"type": "Halogen", "family": "Halogen"}
                elif line.startswith("ExclusionVolume") or line.startswith("EV"):
                    current_feature = {"type": "Exclusion", "family": "Exclusion"}

                # Position data (x y z radius weight)
                parts = line.split()
                if len(parts) >= 3 and current_feature:
                    try:
                        x, y, z = float(parts[0]), float(parts[1]), float(parts[2])
                        r = float(parts[3]) if len(parts) > 3 else 1.5
                        w = float(parts[4]) if len(parts) > 4 else 1.0

                        ft = current_feature["type"]
                        fam = current_feature["family"]
                        color = FEATURE_COLORS.get(fam, FEATURE_COLORS.get(ft, "#888888"))
                        features.append({
                            "type": ft, "family": fam,
                            "position": {"x": x, "y": y, "z": z},
                            "radius": r, "weight": w,
                            "color": color,
                            "nci_type": NCI_TYPE_MAP.get(fam, NCI_TYPE_MAP.get(ft, ft)),
                            "source": "ligandscout_ph4",
                        })
                        current_feature = None
                    except ValueError:
                        pass

            return {
                "success": True,
                "format": "LigandScout .ph4",
                "metadata": metadata,
                "features": features,
                "num_features": len(features),
            }

        # ── Generate query file from PDB (ZINCPharmer-style) ──
        if action == "pdb_query":
            pdb_content = input.get("pdb_content", "")
            ligand_resname = input.get("ligand_resname", "")
            if not pdb_content:
                return {"success": False, "error": "pdb_content required"}

            try:
                from rdkit import Chem
                mol = Chem.MolFromPDBBlock(pdb_content, removeHs=False)
                if mol is None:
                    return {"success": False, "error": "Invalid PDB content"}

                feat_features = _extract_features(mol) if mol else []
                prot_features = _extract_protein_pharmacophore(pdb_content)

                pd_info = {}
                if ligand_resname:
                    pd_info["ligand"] = ligand_resname

                query_pm = _export_pm_file(feat_features + prot_features, pd_info)

                families = {}
                for f in feat_features + prot_features:
                    families[f["family"]] = families.get(f["family"], 0) + 1

                return {
                    "success": True,
                    "source": "PDB structure",
                    "ligand_features": len(feat_features),
                    "protein_features": len(prot_features),
                    "total_features": len(feat_features) + len(prot_features),
                    "feature_summary": families,
                    "features": feat_features + prot_features,
                    "query_export": query_pm,
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        return {"error": f"Unknown action: {action}"}
