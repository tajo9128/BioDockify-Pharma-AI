"""Pharmacophore Modeler API — RDKit-based feature detection and library screening."""
from helpers.api import ApiHandler, Request, Response
import logging, os

log = logging.getLogger("pharmacophore_api")

FEATURE_COLORS = {
    "Donor": "#4169E1", "Acceptor": "#DC143C", "Hydrophobic": "#FFD700",
    "Aromatic": "#9932CC", "PosIonizable": "#32CD32", "NegIonizable": "#FF8C00",
    "LumpedHydrophobic": "#DAA520",
}
FEATURE_RADII = {
    "Donor": 1.5, "Acceptor": 1.5, "Hydrophobic": 1.8, "Aromatic": 2.0,
    "PosIonizable": 1.5, "NegIonizable": 1.5, "LumpedHydrophobic": 1.6,
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
    factory = _get_factory()
    if factory is None:
        return []
    features = []
    for feat in factory.GetFeaturesForMol(mol):
        pos = feat.GetPos()
        features.append({
            "type": feat.GetType(),
            "family": feat.GetFamily(),
            "position": {"x": round(pos.x, 3), "y": round(pos.y, 3), "z": round(pos.z, 3)},
            "atoms": list(feat.GetAtomIds()),
            "color": FEATURE_COLORS.get(feat.GetFamily(), "#888888"),
            "radius": FEATURE_RADII.get(feat.GetFamily(), 1.5),
        })
    return features


class PharmacophoreHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "generate")

        if action == "generate":
            smiles = input.get("smiles", "")
            pdb = input.get("pdb", "")
            if not smiles and not pdb:
                return {"success": False, "error": "Provide SMILES or PDB", "features": []}

            try:
                from rdkit import Chem
                if smiles:
                    mol = _generate_3d_mol(smiles)
                elif "\n" in pdb or pdb.strip().startswith("ATOM") or pdb.strip().startswith("HEADER"):
                    mol = Chem.MolFromPDBBlock(pdb)
                    if mol:
                        mol = Chem.AddHs(mol)
                        from rdkit.Chem import AllChem
                        try:
                            AllChem.EmbedMolecule(mol, AllChem.ETKDG())
                            AllChem.MMFFOptimizeMolecule(mol)
                        except Exception:
                            pass
                else:
                    return {"success": False, "error": "Invalid PDB content", "features": []}

                if mol is None:
                    return {"success": False, "error": "Failed to parse molecule", "features": []}

                features = _extract_features(mol)
                families = {}
                for f in features:
                    families[f["family"]] = families.get(f["family"], 0) + 1

                return {"success": True, "smiles": smiles, "features": features, "num_features": len(features), "feature_summary": families}
            except ImportError:
                return {"success": False, "error": "RDKit not available", "features": []}
            except Exception as e:
                return {"success": False, "error": str(e), "features": []}

        if action == "screen":
            query_smiles = input.get("query_smiles", "")
            library = input.get("library_smiles", [])
            if isinstance(library, str):
                library = [s.strip() for s in library.split("\n") if s.strip()]

            if not query_smiles or not library:
                return {"success": False, "error": "query_smiles and library_smiles required"}

            try:
                qmol = _generate_3d_mol(query_smiles)
                if qmol is None:
                    return {"success": False, "error": "Invalid query SMILES"}
                q_features = _extract_features(qmol)
                q_families = set(f["family"] for f in q_features)

                hits = []
                for smi in library:
                    lmol = _generate_3d_mol(smi)
                    if lmol is None:
                        continue
                    l_features = _extract_features(lmol)
                    l_families = set(f["family"] for f in l_features)
                    overlap = len(q_families & l_families)
                    union = len(q_families | l_families)
                    score = overlap / union if union > 0 else 0
                    if overlap >= 2:
                        hits.append({"smiles": smi, "score": round(score, 3), "matched_features": overlap, "features": [f["family"] for f in l_features]})

                hits.sort(key=lambda h: h["score"], reverse=True)
                return {"success": True, "query_features": list(q_families), "total_screened": len(library), "total_hits": len(hits), "hits": hits[:50]}
            except Exception as e:
                return {"success": False, "error": str(e)}

        if action == "hypothesis":
            actives = input.get("active_smiles", [])
            if isinstance(actives, str):
                actives = [s.strip() for s in actives.split("\n") if s.strip()]
            if len(actives) < 2:
                return {"success": False, "error": "Need at least 2 active molecules"}

            try:
                import numpy as np
                FTYPES = ["Donor", "Acceptor", "Hydrophobic", "Aromatic", "PosIonizable", "NegIonizable"]
                common = []
                all_entries = []
                for smi in actives:
                    mol = _generate_3d_mol(smi)
                    if mol:
                        all_entries.append({"smiles": smi, "features": _extract_features(mol)})

                for ft in FTYPES:
                    positions = []
                    for entry in all_entries:
                        type_feats = [f for f in entry["features"] if f["family"] == ft]
                        if type_feats:
                            for tf in type_feats:
                                positions.append([tf["position"]["x"], tf["position"]["y"], tf["position"]["z"]])
                    if positions and len(positions) >= len(all_entries) * 0.6:
                        pa = np.array(positions)
                        center = np.mean(pa, axis=0).tolist()
                        radius = float(min(np.max(np.linalg.norm(pa - center, axis=1)) + 1.0, 3.0))
                        common.append({"type": ft, "center": center, "radius": round(radius, 2), "color": FEATURE_COLORS.get(ft, "#888888"), "coverage": len(positions) / len(all_entries)})

                common.sort(key=lambda x: x["coverage"], reverse=True)
                return {"success": True, "hypothesis": common[:6], "n_features": len(common[:6]), "n_molecules": len(all_entries)}
            except Exception as e:
                return {"success": False, "error": str(e)}

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
                        atoms.append({"resname": line[17:20].strip(), "element": line[76:78].strip() or line[12:14].strip(), "pos": [float(line[30:38]), float(line[38:46]), float(line[46:54])]})
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
                pos_arr = np.array(atom["pos"])
                if any(np.linalg.norm(pos_arr - u) < 2.0 for u in used):
                    continue
                used.append(pos_arr)
                radius = 1.5 if atom["element"] == "C" else 1.7
                spheres.append({"center": atom["pos"], "radius": radius, "color": "#FF6600" if atom["resname"] in hydrophobic else "#CCCCCC", "residue": atom["resname"], "element": atom["element"]})

            return {"success": True, "exclusion_spheres": spheres, "n_spheres": len(spheres)}

        return {"error": f"Unknown action: {action}"}
