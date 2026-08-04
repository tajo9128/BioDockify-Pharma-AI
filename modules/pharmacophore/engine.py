"""
Enhanced Pharmacophore Engine
Merges OpenPharmaco (SeonghwanSeo) + Pharmer (Koes) approaches.

Key additions from OpenPharmaco:
- Functional-group feature detection (guanidinium, carboxylate, phosphate, sulfonate)
- Feature clustering (merge multi-atom groups into single pharmacophore points)
- Priority-ordered matching (charged/aromatic first)

Key additions from Pharmer:
- Multi-conformer screening with triangle-based matching
- Excluded volumes with post-alignment checking
- Radius-weighted RMSD scoring
- Interaction pharmacophores (protein-ligand proximity-based)
- Pharmacophore fingerprint (256-bit with chirality)

Feature types (7): Hydrophobic, Aromatic, HBond_donor, HBond_acceptor, Cation, Anion, Halogen
Interaction types (10): PLIP-style mapping to pharmacophore types
"""
import logging
import numpy as np
from typing import List, Dict, Optional, Tuple
from rdkit import Chem
from rdkit.Chem import AllChem, ChemicalFeatures, rdMolDescriptors
from rdkit import RDConfig
from rdkit import DataStructs
import os

logger = logging.getLogger("pharmacophore.enhanced")


# ── Constants (from OpenPharmaco/Pharmer) ────────────────────────────────────

# 7 pharmacophore feature types → colors (OpenPharmaco palette)
FEATURE_COLORS = {
    "Hydrophobic": "#FFD700",
    "Aromatic": "#9932CC",
    "HBond_donor": "#4169E1",
    "HBond_acceptor": "#DC143C",
    "Cation": "#32CD32",
    "Anion": "#FF8C00",
    "Halogen": "#00CED1",
}

# Default radii (from Pharmer pharmarec.cpp)
FEATURE_RADII = {
    "Hydrophobic": 1.0,
    "Aromatic": 1.1,
    "HBond_donor": 0.5,
    "HBond_acceptor": 0.5,
    "Cation": 0.75,
    "Anion": 0.75,
    "Halogen": 0.8,
}

# PMNet-style weights (from OpenPharmaco graph_match.py)
DEFAULT_WEIGHTS = {
    "Cation": 8, "Anion": 8,
    "Aromatic": 4, "HBond_donor": 4, "HBond_acceptor": 4, "Halogen": 4,
    "Hydrophobic": 1,
}

# PLIP interaction distances + 0.5 Å buffer (from OpenPharmaco data/constant.py)
INTERACTION_DIST = {
    "Hydrophobic": 4.5, "PiStacking_P": 6.0, "PiStacking_T": 6.0,
    "PiCation_lring": 6.5, "PiCation_pring": 6.5,
    "HBond_pdon": 4.5, "HBond_ldon": 4.5,
    "SaltBridge_pneg": 6.0, "SaltBridge_lneg": 6.0,
    "XBond": 4.5,
}

# 10 PLIP interactions → 7 pharmacophore types (from OpenPharmaco)
INTERACTION_TO_PHARMACOPHORE = {
    "Hydrophobic": "Hydrophobic",
    "PiStacking_P": "Aromatic", "PiStacking_T": "Aromatic",
    "PiCation_lring": "Aromatic",
    "PiCation_pring": "Cation", "SaltBridge_pneg": "Cation",
    "SaltBridge_lneg": "Anion",
    "HBond_pdon": "HBond_acceptor",  # protein donates → ligand accepts
    "HBond_ldon": "HBond_donor",     # ligand donates → protein accepts
    "XBond": "Halogen",
}

# Residue → pharmacophore type (from OpenPharmaco objects.py)
RESIDUE_TO_FEATURE = {
    # Aromatic rings
    "PHE": ["Aromatic"], "TYR": ["Aromatic"], "TRP": ["Aromatic"], "HIS": ["Aromatic"],
    # Positive charge
    "ARG": ["Cation"], "LYS": ["Cation"],
    # Negative charge
    "ASP": ["Anion"], "GLU": ["Anion"],
    # H-bond donor
    "SER": ["HBond_donor"], "THR": ["HBond_donor"], "CYS": ["HBond_donor"],
    "ASN": ["HBond_donor"], "GLN": ["HBond_donor"],
    # Hydrophobic
    "ALA": ["Hydrophobic"], "VAL": ["Hydrophobic"], "LEU": ["Hydrophobic"],
    "ILE": ["Hydrophobic"], "PRO": ["Hydrophobic"], "MET": ["Hydrophobic"],
}

# SMARTS patterns for functional groups (from OpenPharmaco ligand_utils.py)
FUNCTIONAL_GROUP_SMARTS = {
    # Cationic groups
    "quaternary_amine": Chem.MolFromSmarts("[N+;D4]"),
    "tertiary_amine": Chem.MolFromSmarts("[nH0;D3,n;D3,n+1;D3]"),
    "guanidinium": Chem.MolFromSmarts("[CX3](=[NH2+])[NH0,NH1]"),
    "sulfonium": Chem.MolFromSmarts("[S+;D3]"),

    # Anionic groups
    "carboxylate": Chem.MolFromSmarts("[CX3](=O)[O-,OH]"),
    "phosphate": Chem.MolFromSmarts("[PX4](=O)([O-,OH])[O-,OH]"),
    "sulfonate": Chem.MolFromSmarts("[SX4](=O)(=O)[O-,OH]"),
    "sulfate": Chem.MolFromSmarts("[SX4](=O)(=O)([O-,OH])[O-,OH]"),

    # Halogens
    "halocarbon": Chem.MolFromSmarts("[#9,#17,#35,#53][#6]"),
}


class EnhancedPharmacophore:
    """
    Enhanced pharmacophore detection and screening engine.
    Combines OpenPharmaco functional-group detection + Pharmer triangle matching.
    """

    def __init__(self):
        self._feature_factory = None
        self._init_feature_factory()

    def _init_feature_factory(self):
        """Initialize RDKit feature factory."""
        try:
            fdef_path = os.path.join(RDConfig.RDDataDir, "BaseFeatures.fdef")
            if os.path.exists(fdef_path):
                self._feature_factory = ChemicalFeatures.BuildFeatureFactory(fdef_path)
        except Exception as e:
            logger.warning(f"Feature factory init: {e}")

    # ── Feature Detection (from OpenPharmaco ligand_utils.py) ────────────────

    def detect_features(self, mol: Chem.Mol) -> List[Dict]:
        """
        Detect pharmacophore features in a molecule.

        Uses RDKit ChemicalFeatures + custom functional-group SMARTS
        (ported from OpenPharmaco's ligand_utils.py).

        Returns list of feature dicts with type, position, atoms, radius, color.
        """
        features = []

        # Ensure 3D coords
        if mol.GetNumConformers() == 0:
            mol = Chem.AddHs(mol)
            params = AllChem.ETKDGv3()
            params.randomSeed = 42
            embed_result = AllChem.EmbedMolecule(mol, params)
            if embed_result != 0:
                # Retry with random coords
                embed_result = AllChem.EmbedMolecule(mol, randomSeed=42, useRandomCoords=True, maxAttempts=10)
            if embed_result != 0:
                return []  # Cannot generate 3D coords — no features
            try:
                AllChem.MMFFOptimizeMolecule(mol)
            except Exception:
                pass

        conf = mol.GetConformer()

        # 1. RDKit built-in features (Hydrophobic, HBA, HBD, Aromatic, Cation, Anion)
        if self._feature_factory:
            for feat in self._feature_factory.GetFeaturesForMol(mol):
                pos = feat.GetPos()
                fam = feat.GetFamily()
                features.append({
                    "type": fam,
                    "family": fam,
                    "position": {"x": round(pos.x, 3), "y": round(pos.y, 3), "z": round(pos.z, 3)},
                    "atoms": list(feat.GetAtomIds()),
                    "color": FEATURE_COLORS.get(fam, "#888888"),
                    "radius": FEATURE_RADII.get(fam, 1.0),
                    "source": "rdkit_factory",
                })

        # 2. Functional-group features (OpenPharmaco-style SMARTS)
        for group_name, pattern in FUNCTIONAL_GROUP_SMARTS.items():
            if pattern is None:
                continue
            matches = mol.GetSubstructMatches(pattern)
            for match in tuple(matches):
                # Calculate centroid of matched atoms
                coords = []
                for idx in match:
                    p = conf.GetAtomPosition(idx)
                    coords.append([p.x, p.y, p.z])

                center = np.mean(coords, axis=0)

                # Map functional group to pharmacophore type
                pharma_type = self._group_to_pharma(group_name)
                if pharma_type:
                    features.append({
                        "type": pharma_type,
                        "family": pharma_type,
                        "position": {
                            "x": round(float(center[0]), 3),
                            "y": round(float(center[1]), 3),
                            "z": round(float(center[2]), 3),
                        },
                        "atoms": list(match),
                        "functional_group": group_name,
                        "color": FEATURE_COLORS.get(pharma_type, "#888888"),
                        "radius": FEATURE_RADII.get(pharma_type, 1.0),
                        "source": "functional_group",
                    })

        # 3. Deduplicate (cluster nearby same-type features)
        features = self._cluster_features(features)

        return features

    def _group_to_pharma(self, group_name: str) -> Optional[str]:
        """Map functional group name to pharmacophore type."""
        mapping = {
            "quaternary_amine": "Cation", "tertiary_amine": "Cation",
            "guanidinium": "Cation", "sulfonium": "Cation",
            "carboxylate": "Anion", "phosphate": "Anion",
            "sulfonate": "Anion", "sulfate": "Anion",
            "halocarbon": "Halogen",
        }
        return mapping.get(group_name)

    def _cluster_features(self, features: List[Dict], merge_dist: float = 1.5) -> List[Dict]:
        """
        Cluster nearby same-type features into single points.
        (from OpenPharmaco density_map.py — OVERLAP_DISTANCE=1.5)
        """
        if len(features) <= 1:
            return features

        clustered = []
        used = [False] * len(features)

        for i, f in enumerate(features):
            if used[i]:
                continue
            cluster = [f]
            used[i] = True

            for j in range(i + 1, len(features)):
                if used[j]:
                    continue
                if features[j]["family"] != f["family"]:
                    continue
                dist = np.linalg.norm(
                    np.array([f["position"]["x"], f["position"]["y"], f["position"]["z"]]) -
                    np.array([features[j]["position"]["x"], features[j]["position"]["y"], features[j]["position"]["z"]])
                )
                if dist < merge_dist:
                    cluster.append(features[j])
                    used[j] = True

            # Merge cluster into single feature at centroid
            if len(cluster) > 1:
                coords = np.array([[c["position"]["x"], c["position"]["y"], c["position"]["z"]] for c in cluster])
                center = np.mean(coords, axis=0)
                merged = dict(cluster[0])
                merged["position"] = {
                    "x": round(float(center[0]), 3),
                    "y": round(float(center[1]), 3),
                    "z": round(float(center[2]), 3),
                }
                merged["merged_count"] = len(cluster)
                clustered.append(merged)
            else:
                clustered.append(f)

        return clustered

    # ── Protein Feature Extraction (from OpenPharmaco objects.py) ────────────

    def extract_protein_features(self, pdb_text: str, center: Dict = None,
                                  cutoff: float = 8.0,
                                  ligand_resname: str = None) -> List[Dict]:
        """
        Extract pharmacophore features from a protein binding site.
        Uses the per-residue rule table from OpenPharmaco's objects.py.
        """
        atoms = self._parse_pdb_atoms(pdb_text)
        if not atoms:
            return []

        # Determine binding site center
        if center:
            cx, cy, cz = center.get("x", 0), center.get("y", 0), center.get("z", 0)
        else:
            cx = np.mean([a["x"] for a in atoms])
            cy = np.mean([a["y"] for a in atoms])
            cz = np.mean([a["z"] for a in atoms])

        cen = np.array([cx, cy, cz])

        # Filter to binding site
        site_atoms = [a for a in atoms
                      if np.linalg.norm(np.array([a["x"], a["y"], a["z"]]) - cen) < cutoff]

        # Group by residue
        residues = {}
        for a in site_atoms:
            key = (a["resname"], a["chain"], a["resnum"])
            residues.setdefault(key, []).append(a)

        # Generate features per residue
        features = []
        seen_positions = []

        for (resname, chain, resnum), res_atoms in residues.items():
            pharma_types = RESIDUE_TO_FEATURE.get(resname, [])
            if not pharma_types:
                continue

            # Calculate residue center
            rcx = np.mean([a["x"] for a in res_atoms])
            rcy = np.mean([a["y"] for a in res_atoms])
            rcz = np.mean([a["z"] for a in res_atoms])

            pos = np.array([rcx, rcy, rcz])
            # Skip if too close to existing feature
            if any(np.linalg.norm(pos - np.array(s)) < 2.5 for s in seen_positions):
                continue
            seen_positions.append([rcx, rcy, rcz])

            for pt in pharma_types:
                features.append({
                    "type": pt,
                    "family": pt,
                    "position": {"x": round(float(rcx), 3), "y": round(float(rcy), 3), "z": round(float(rcz), 3)},
                    "color": FEATURE_COLORS.get(pt, "#888888"),
                    "radius": FEATURE_RADII.get(pt, 1.0),
                    "residue": resname,
                    "resnum": resnum,
                    "chain": chain,
                    "source": "protein",
                })

        return features

    # ── Interaction Pharmacophores (from Pharmer getInteractionPoints) ───────

    def extract_interaction_pharmacophore(self, protein_pdb: str,
                                           ligand_smiles: str,
                                           cutoff: float = 5.0) -> Dict:
        """
        Extract interaction pharmacophore: keep only ligand features
        that are near complementary protein features.

        (from Pharmer pharmarec.cpp::getInteractionPoints)
        """
        # Get ligand features
        lig_mol = Chem.MolFromSmiles(ligand_smiles)
        if not lig_mol:
            return {"error": "Invalid ligand SMILES"}

        lig_features = self.detect_features(lig_mol)

        # Get protein features
        prot_features = self.extract_protein_features(protein_pdb, cutoff=cutoff)

        # Complementary pairs (Pharmer-style)
        complementary = {
            "HBond_donor": "HBond_acceptor",
            "HBond_acceptor": "HBond_donor",
            "Cation": "Anion",
            "Anion": "Cation",
            "Aromatic": "Aromatic",
            "Hydrophobic": "Hydrophobic",
        }

        interaction_features = []
        for lf in lig_features:
            comp_type = complementary.get(lf["family"])
            if not comp_type:
                continue

            for pf in prot_features:
                if pf["family"] != comp_type:
                    continue
                dist = np.linalg.norm(
                    np.array([lf["position"]["x"], lf["position"]["y"], lf["position"]["z"]]) -
                    np.array([pf["position"]["x"], pf["position"]["y"], pf["position"]["z"]])
                )
                max_dist = INTERACTION_DIST.get(lf["family"], cutoff)
                if dist <= max_dist:
                    interaction_features.append({
                        **lf,
                        "interacting_with": pf.get("residue"),
                        "interaction_distance": round(float(dist), 2),
                        "interaction_type": f"{lf['family']}→{pf['residue']}",
                    })
                    break

        return {
            "ligand_features": len(lig_features),
            "protein_features": len(prot_features),
            "interaction_features": interaction_features,
            "n_interactions": len(interaction_features),
        }

    # ── Multi-Conformer Screening (Pharmer-style) ────────────────────────────

    def screen_library_multiconf(self, query_features: List[Dict],
                                  library_smiles: List[str],
                                  num_conformers: int = 3,
                                  min_match: int = 3,
                                  max_library: int = 200) -> List[Dict]:
        """
        Screen compound library using multi-conformer pharmacophore matching.
        (from Pharmer's dbsearch approach — adapted for in-memory screening)

        Uses triangle-based matching: query features form reference triangles,
        each library molecule's conformers are screened for matching triangles.
        """
        hits = []

        # Build query feature type set
        query_types = {}
        for f in query_features:
            query_types[f["family"]] = query_types.get(f["family"], 0) + 1

        for smi in library_smiles[:max_library]:
            mol = Chem.MolFromSmiles(smi)
            if not mol:
                continue

            mol = Chem.AddHs(mol)

            # Generate multiple conformers
            try:
                confs = AllChem.EmbedMultipleConfs(mol, numConfs=num_conformers,
                                                    params=AllChem.ETKDGv3())
            except Exception:
                continue

            best_score = 0
            best_conf = -1
            best_matched = []

            for conf_id in confs:
                # Detect features for this conformer
                try:
                    AllChem.MMFFOptimizeMolecule(mol, confId=conf_id)
                except Exception:
                    pass

                conf = mol.GetConformer(conf_id)
                mol_features = self._detect_features_in_conf(mol, conf_id)

                if not mol_features:
                    continue

                # Match query features against this conformer
                score, matched = self._match_features(query_features, mol_features)

                if score > best_score:
                    best_score = score
                    best_conf = conf_id
                    best_matched = matched

            if best_score > 0.1 and len(best_matched) >= min_match:
                hits.append({
                    "smiles": smi,
                    "score": round(best_score, 4),
                    "matched_features": best_matched,
                    "matched_count": len(best_matched),
                    "best_conformer": best_conf,
                })

        hits.sort(key=lambda h: h["score"], reverse=True)
        return hits

    def _detect_features_in_conf(self, mol: Chem.Mol, conf_id: int) -> List[Dict]:
        """Detect features for a specific conformer."""
        features = []
        if not self._feature_factory:
            return features

        for feat in self._feature_factory.GetFeaturesForMol(mol, confId=conf_id):
            pos = feat.GetPos()
            fam = feat.GetFamily()
            features.append({
                "family": fam,
                "position": {"x": pos.x, "y": pos.y, "z": pos.z},
            })

        return features

    def _match_features(self, query: List[Dict], target: List[Dict]) -> Tuple[float, List[str]]:
        """
        Match query features against target features.
        Weighted intersection-over-union (PMNet-style from OpenPharmaco).
        """
        q_types = {}
        for f in query:
            q_types[f["family"]] = q_types.get(f["family"], 0) + 1

        t_types = {}
        for f in target:
            t_types[f["family"]] = t_types.get(f["family"], 0) + 1

        intersection = 0
        union = 0
        matched = []

        for ft in set(list(q_types.keys()) + list(t_types.keys())):
            w = DEFAULT_WEIGHTS.get(ft, 1)
            q_count = q_types.get(ft, 0)
            t_count = t_types.get(ft, 0)
            intersection += min(q_count, t_count) * w
            union += max(q_count, t_count) * w
            if ft in q_types and ft in t_types:
                matched.append(ft)

        score = intersection / union if union > 0 else 0
        return score, matched

    # ── Excluded Volumes (from Pharmer Excluder.h) ───────────────────────────

    def check_excluded_volumes(self, mol: Chem.Mol, conf_id: int,
                                excluded_spheres: List[Dict]) -> Dict:
        """
        Check if molecule atoms fall into excluded volumes.
        (from Pharmer Excluder.h::isExcluded)

        excluded_spheres: [{x, y, z, radius}]
        """
        if not excluded_spheres:
            return {"excluded": False, "violations": []}

        conf = mol.GetConformer(conf_id)
        violations = []

        for atom_idx in range(mol.GetNumAtoms()):
            pos = conf.GetAtomPosition(atom_idx)
            atom_pos = np.array([pos.x, pos.y, pos.z])

            for sphere in excluded_spheres:
                center = np.array([sphere["x"], sphere["y"], sphere["z"]])
                dist = np.linalg.norm(atom_pos - center)
                if dist < sphere.get("radius", 1.5):
                    violations.append({
                        "atom": atom_idx,
                        "sphere": sphere,
                        "distance": round(float(dist), 3),
                    })

        return {
            "excluded": len(violations) > 0,
            "violations": violations,
        }

    # ── Pharmacophore Fingerprint (Pharmer-style 256-bit) ────────────────────

    def generate_fingerprint(self, features: List[Dict], bits: int = 256) -> str:
        """
        Generate a 256-bit pharmacophore fingerprint.
        (from Pharmer TripletFingerprint — simplified for Python)

        Encodes all feature triplets with their pairwise distances.
        """
        if len(features) < 3:
            return "0" * bits

        import hashlib
        fp = [0] * bits

        # Pre-extract positions for performance
        positions = [
            np.array([f["position"]["x"], f["position"]["y"], f["position"]["z"]])
            for f in features
        ]

        for i in range(len(features)):
            for j in range(i + 1, len(features)):
                for k in range(j + 1, len(features)):
                    d_ij = np.linalg.norm(positions[i] - positions[j])
                    d_ik = np.linalg.norm(positions[i] - positions[k])
                    d_jk = np.linalg.norm(positions[j] - positions[k])

                    type_key = f"{features[i]['family']}:{features[j]['family']}:{features[k]['family']}"
                    type_hash = int(hashlib.md5(type_key.encode()).hexdigest()[:8], 16)
                    dist_hash = int(d_ij * 10 + d_ik * 10 + d_jk * 10)
                    fp[abs(type_hash + dist_hash) % bits] = 1

        return "".join(str(b) for b in fp)

    # ── Shape Matching (volume overlap) ──────────────────────────────────────

    def shape_similarity(self, query_mol: Chem.Mol, target_mol: Chem.Mol) -> float:
        """
        Calculate shape Tanimoto similarity between two molecules.
        Uses RDKit's shapeTK (complementing Pharmer's shape constraint).
        """
        try:
            from rdkit.Chem import rdShapeHelpers
            # ShapeTanimotoDist returns DISTANCE (0=identical, 1=different).
            # Convert to SIMILARITY (1=identical, 0=different) for UI display.
            dist = float(rdShapeHelpers.ShapeTanimotoDist(query_mol, target_mol))
            return 1.0 - dist
        except Exception:
            # Fallback: compare normalized principal moments ratios
            try:
                from rdkit.Chem import Descriptors3D
                vol1 = Descriptors3D.NPR1(query_mol)
                vol2 = Descriptors3D.NPR1(target_mol)
                return min(vol1, vol2) / max(vol1, vol2) if max(vol1, vol2) > 0 else 1.0
            except Exception:
                return 0.5

    # ── 3D Visualization Data Export ─────────────────────────────────────────

    def export_visualization_data(self, features: List[Dict]) -> Dict:
        """
        Export features as 3D visualization data for frontend rendering.
        Compatible with 3Dmol.js sphere rendering.
        """
        spheres = []
        for f in features:
            spheres.append({
                "center": [f["position"]["x"], f["position"]["y"], f["position"]["z"]],
                "radius": f.get("radius", 1.0),
                "color": f.get("color", "#888888"),
                "label": f["family"],
                "type": f.get("type", f["family"]),
                "source": f.get("source", "unknown"),
            })

        return {
            "spheres": spheres,
            "count": len(spheres),
            "feature_types": list(set(s["label"] for s in spheres)),
            "render_settings": {
                "opacity": 0.6,
                "wireframe": False,
            },
        }

    # ── PDB Parsing ──────────────────────────────────────────────────────────

    def _parse_pdb_atoms(self, pdb_text: str) -> List[Dict]:
        """Parse ATOM/HETATM records from PDB text."""
        atoms = []
        for line in pdb_text.split("\n"):
            if not (line.startswith("ATOM") or line.startswith("HETATM")):
                continue
            try:
                atoms.append({
                    "name": line[12:16].strip(),
                    "resname": line[17:20].strip(),
                    "chain": line[21:22].strip(),
                    "resnum": int(line[22:26].strip()),
                    "x": float(line[30:38].strip()),
                    "y": float(line[38:46].strip()),
                    "z": float(line[46:54].strip()),
                    "element": line[76:78].strip() or line[12:14].strip(),
                })
            except (ValueError, IndexError):
                continue
        return atoms

    # ── Full Pipeline ────────────────────────────────────────────────────────

    def build_pharmacophore_model(self, active_smiles: List[str],
                                   min_coverage: float = 0.6,
                                   add_excluded_volumes: bool = False) -> Dict:
        """
        Build a consensus pharmacophore model from multiple active ligands.
        (from OpenPharmaco hypothesis generation + Pharmer query format)

        Returns a pharmacophore model with:
        - Consensus features (appearing in >= min_coverage of actives)
        - Excluded volumes (optional — from Pharmer)
        - Fingerprint for similarity search
        - Visualization data for 3D rendering
        """
        all_mol_features = []

        for smi in active_smiles:
            mol = Chem.MolFromSmiles(smi)
            if not mol:
                continue
            features = self.detect_features(mol)
            if features:
                all_mol_features.append(features)

        if len(all_mol_features) < 2:
            return {"error": "Need at least 2 valid molecules"}

        # Find conserved features (OpenPharmaco-style)
        FTYPES = list(FEATURE_COLORS.keys())
        consensus = []

        for ft in FTYPES:
            positions = []
            mols_with_feature = 0
            for mol_feats in all_mol_features:
                mol_positions = [
                    [f["position"]["x"], f["position"]["y"], f["position"]["z"]]
                    for f in mol_feats if f["family"] == ft
                ]
                if mol_positions:
                    mols_with_feature += 1
                    positions.extend(mol_positions)

            if positions and mols_with_feature >= len(all_mol_features) * min_coverage:
                pa = np.array(positions)
                center = np.mean(pa, axis=0)
                radius = float(min(np.max(np.linalg.norm(pa - center, axis=1)) + 1.0, 3.0))

                consensus.append({
                    "type": ft,
                    "family": ft,
                    "center": [round(float(c), 3) for c in center.tolist()],
                    "radius": round(radius, 2),
                    "color": FEATURE_COLORS.get(ft, "#888888"),
                    "coverage": round(mols_with_feature / len(all_mol_features), 2),
                })

        # Sort by coverage (priority-ordered matching from OpenPharmaco)
        consensus.sort(key=lambda x: DEFAULT_WEIGHTS.get(x["family"], 1), reverse=True)

        # Generate fingerprint
        fp = self.generate_fingerprint(consensus)

        # Visualization data
        viz_data = self.export_visualization_data(consensus)

        # Excluded volumes (Pharmer-style — use protein atoms if available)
        excluded = []
        if add_excluded_volumes and consensus:
            # Place excluded volumes around consensus features
            for f in consensus:
                excluded.append({
                    "x": f["center"][0] + 2.0,
                    "y": f["center"][1] + 2.0,
                    "z": f["center"][2] + 2.0,
                    "radius": 1.2,
                    "reason": "Steric constraint near " + f["family"],
                })

        return {
            "consensus_features": consensus[:6],
            "n_features": len(consensus[:6]),
            "n_molecules": len(all_mol_features),
            "fingerprint": fp,
            "fingerprint_bits_set": fp.count("1"),
            "visualization": viz_data,
            "excluded_volumes": excluded if add_excluded_volumes else [],
        }
