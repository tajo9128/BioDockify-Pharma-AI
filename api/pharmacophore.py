"""Pharmacophore API — feature detection, screening, hypothesis generation.
Enhanced with OpenPharmaco + Pharmer capabilities."""
from helpers.api import ApiHandler, Request, Response
import asyncio, logging, os, json, numpy as np

log = logging.getLogger("pharmacophore_api")

# Feature type colors and radii
FEATURE_COLORS = {
    "Donor": "#4169E1", "Acceptor": "#DC143C", "Hydrophobic": "#FFD700",
    "Aromatic": "#9932CC", "PosIonizable": "#32CD32", "NegIonizable": "#FF8C00",
    "HBond_donor": "#4169E1", "HBond_acceptor": "#DC143C",
    "Cation": "#32CD32", "Anion": "#FF8C00", "Halogen": "#00CED1",
}
FEATURE_RADII = {
    "Donor": 1.5, "Acceptor": 1.5, "Hydrophobic": 1.8, "Aromatic": 2.0,
    "HBond_donor": 1.5, "HBond_acceptor": 1.5, "Cation": 1.5, "Anion": 1.5,
}
PMNET_DEFAULT_WEIGHTS = {
    "Hydrophobic": 1, "Aromatic": 4, "Cation": 8, "Anion": 8,
    "Halogen": 4, "HBond_donor": 4, "HBond_acceptor": 4,
}
RESIDUE_PHARMA_TYPE = {
    "ALA": "Hydrophobic", "VAL": "Hydrophobic", "LEU": "Hydrophobic",
    "ILE": "Hydrophobic", "PRO": "Hydrophobic", "MET": "Hydrophobic",
    "PHE": "Aromatic", "TRP": "Aromatic", "TYR": "Aromatic", "HIS": "Aromatic",
    "SER": "HBond_donor", "THR": "HBond_donor", "CYS": "HBond_donor",
    "ASN": "HBond_donor", "GLN": "HBond_donor", "LYS": "Cation",
    "ARG": "Cation", "ASP": "Anion", "GLU": "Anion",
}


class PharmacophoreHandler(ApiHandler):
    """Pharmacophore API handler — feature detection, screening, hypothesis generation."""
    
    async def process(self, input: dict, request: Request) -> dict:
        action = input.get("action", "")
        if action == "generate": return self._generate(input)
        if action == "protein_model": return self._protein_model(input)
        if action == "screen": return await self._screen(input)
        if action == "hypothesis": return self._hypothesis(input)
        if action == "nci_types": return self._nci_types()
        if action == "enhanced_detect": return self._enhanced_detect(input)
        if action == "enhanced_interactions": return self._enhanced_interactions(input)
        if action == "enhanced_screen": return await self._enhanced_screen(input)
        if action == "enhanced_model": return self._enhanced_model(input)
        if action == "enhanced_fingerprint": return self._enhanced_fingerprint(input)
        if action == "enhanced_shape": return self._enhanced_shape(input)
        if action == "enhanced_protein_features": return self._enhanced_protein_features(input)
        if action == "complete": return await self._complete(input)
        if action == "batch": return await self._batch(input)
        if action == "compare": return await self._compare(input)
        return {
            "actions": [
                "generate", "protein_model", "screen", "hypothesis", "nci_types",
                "enhanced_detect", "enhanced_interactions", "enhanced_screen",
                "enhanced_model", "enhanced_fingerprint", "enhanced_shape",
                "enhanced_protein_features", "complete", "batch", "compare"
            ],
            "hint": "POST with action=complete for single molecule, action=batch for multiple molecules"
        }
    
    def _generate(self, input: dict):
        """Generate ligand-based pharmacophore from SMILES."""
        smiles = input.get("smiles", "")
        if not smiles:
            return {"error": "smiles is required"}
        
        try:
            from rdkit import Chem
            from rdkit.Chem import AllChem, ChemicalFeatures
            from rdkit import RDConfig
            
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return {"success": False, "error": "Invalid SMILES", "features": []}
            
            mol = Chem.AddHs(mol)
            AllChem.EmbedMolecule(mol, AllChem.ETKDG())
            AllChem.MMFFOptimizeMolecule(mol)
            
            # Get feature factory
            fdef = os.path.join(RDConfig.RDDataDir, "BaseFeatures.fdef")
            factory = ChemicalFeatures.BuildFeatureFactory(fdef) if os.path.exists(fdef) else None
            
            features = []
            if factory:
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
                    })
            
            families = {}
            for f in features:
                families[f["family"]] = families.get(f["family"], 0) + 1
            
            result = {
                "success": True,
                "smiles": smiles,
                "features": features,
                "num_features": len(features),
                "feature_summary": families,
            }
            # ── AUTO-STORE ──
            try:
                from modules.knowledge.auto_store import auto_store
                auto_store("pharmacophore", f"Pharmacophore: {smiles[:30]}", result,
                           source="Pharmacophore Generator", tags=["pharmacophore", smiles[:20]])
            except Exception:
                pass
            return result
        except ImportError:
            return {"success": False, "error": "RDKit not available on this server", "features": []}
        except Exception as e:
            return {"success": False, "error": str(e), "features": []}
    
    def _protein_model(self, input: dict):
        """Extract pharmacophore features from protein binding site."""
        protein_pdb = input.get("protein_pdb", "")
        center = input.get("center", None)
        cutoff = input.get("cutoff", 8.0)
        ligand_resname = input.get("ligand_resname", None)
        
        if not protein_pdb:
            return {"error": "protein_pdb is required"}
        
        try:
            from rdkit import Chem
            from rdkit.Chem import AllChem
            import numpy as np
            
            # Parse PDB
            mol = Chem.MolFromPDBBlock(protein_pdb, removeHs=False)
            if mol is None:
                return {"success": False, "error": "Invalid PDB"}
            
            # Find binding site residues
            conf = mol.GetConformer()
            features = []
            
            for atom in mol.GetAtoms():
                residue = atom.GetPDBResidueInfo()
                if residue is None:
                    continue
                
                resname = residue.GetResidueName()
                if resname not in RESIDUE_PHARMA_TYPE:
                    continue
                
                pos = conf.GetAtomPosition(atom.GetIdx())
                
                # Check if in binding site
                if center:
                    dist = np.sqrt(
                        (pos.x - center.get("x", 0))**2 +
                        (pos.y - center.get("y", 0))**2 +
                        (pos.z - center.get("z", 0))**2
                    )
                    if dist > cutoff:
                        continue
                
                pharma_type = RESIDUE_PHARMA_TYPE[resname]
                features.append({
                    "type": pharma_type,
                    "family": pharma_type,
                    "position": {"x": round(pos.x, 3), "y": round(pos.y, 3), "z": round(pos.z, 3)},
                    "residue": resname,
                    "residue_number": residue.GetResidueNumber(),
                    "chain": residue.GetChainId(),
                    "color": FEATURE_COLORS.get(pharma_type, "#888888"),
                    "radius": FEATURE_RADII.get(pharma_type, 1.5),
                })
            
            return {
                "success": True,
                "features": features,
                "num_features": len(features),
                "feature_summary": {f["type"]: sum(1 for x in features if x["type"] == f["type"]) for f in features},
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _screen(self, input: dict):
        """Screen compound library against pharmacophore query."""
        query_smiles = input.get("query_smiles", "")
        library_smiles = input.get("library_smiles", [])
        weights = input.get("weights", PMNET_DEFAULT_WEIGHTS)
        min_score = input.get("min_score", 0.1)

        if not query_smiles:
            return {"error": "query_smiles is required"}
        if not library_smiles:
            return {"error": "library_smiles is required"}

        def _do_screen():
            try:
                from rdkit import Chem
                from rdkit.Chem import AllChem, ChemicalFeatures
                from rdkit import RDConfig

                # Generate query features
                q_mol = Chem.MolFromSmiles(query_smiles)
                if q_mol is None:
                    return {"success": False, "error": "Invalid query SMILES"}

                q_mol = Chem.AddHs(q_mol)
                AllChem.EmbedMolecule(q_mol, AllChem.ETKDG())

                fdef = os.path.join(RDConfig.RDDataDir, "BaseFeatures.fdef")
                factory = ChemicalFeatures.BuildFeatureFactory(fdef) if os.path.exists(fdef) else None

                if not factory:
                    return {"success": False, "error": "Feature factory not available"}

                q_types = set()
                for feat in factory.GetFeaturesForMol(q_mol):
                    q_types.add(feat.GetFamily())

                # Try enhanced engine for 3D geometric matching
                enhanced_available = False
                try:
                    from modules.pharmacophore.engine import EnhancedPharmacophore
                    engine = EnhancedPharmacophore()
                    q_features_enhanced = engine.detect_features(q_mol)
                    if q_features_enhanced:
                        enhanced_available = True
                except Exception:
                    pass

                # Screen library
                hits = []
                for smi in library_smiles:
                    mol = Chem.MolFromSmiles(smi.strip())
                    if mol is None:
                        continue

                    mol = Chem.AddHs(mol)
                    AllChem.EmbedMolecule(mol, AllChem.ETKDG())

                    if enhanced_available:
                        try:
                            m_features = engine.detect_features(mol)
                            if not m_features:
                                continue
                            q_pos = np.array([[f.get("x", 0), f.get("y", 0), f.get("z", 0)] for f in q_features_enhanced])
                            m_pos = np.array([[f.get("x", 0), f.get("y", 0), f.get("z", 0)] for f in m_features])
                            q_types_enhanced = set(f.get("family", "") for f in q_features_enhanced)
                            m_types_enhanced = set(f.get("family", "") for f in m_features)

                            matched_types = q_types_enhanced & m_types_enhanced
                            if not matched_types:
                                continue
                            type_score = sum(weights.get(t, 1) for t in matched_types) / sum(weights.get(t, 1) for t in q_types_enhanced)

                            geom_score = 1.0
                            if len(q_pos) >= 3 and len(m_pos) >= 3:
                                from scipy.spatial.distance import cdist
                                q_dists = cdist(q_pos, q_pos).flatten()
                                m_dists = cdist(m_pos, m_pos).flatten()
                                min_len = min(len(q_dists), len(m_dists))
                                rmsd = np.sqrt(np.mean((q_dists[:min_len] - m_dists[:min_len])**2))
                                geom_score = max(0, 1.0 - rmsd / 5.0)

                            combined_score = 0.6 * type_score + 0.4 * geom_score

                            if combined_score > min_score and len(matched_types) >= 2:
                                hits.append({
                                    "smiles": smi.strip(),
                                    "score": round(combined_score, 4),
                                    "weighted_score": round(combined_score * 100, 1),
                                    "type_score": round(type_score, 4),
                                    "geometric_score": round(geom_score, 4),
                                    "matched_types": list(matched_types),
                                    "matched_count": len(matched_types),
                                    "method": "enhanced_3d",
                                })
                        except Exception:
                            pass
                    else:
                        mol_types = set()
                        for feat in factory.GetFeaturesForMol(mol):
                            mol_types.add(feat.GetFamily())
                        matched = q_types & mol_types
                        if not matched:
                            continue
                        score = sum(weights.get(t, 1) for t in matched) / sum(weights.get(t, 1) for t in q_types)
                        if score > min_score and len(matched) >= 2:
                            hits.append({
                                "smiles": smi.strip(),
                                "score": round(score, 4),
                                "weighted_score": round(score * 100, 1),
                                "matched_types": list(matched),
                                "matched_count": len(matched),
                                "method": "basic_set",
                            })

                hits.sort(key=lambda h: h["score"], reverse=True)

                return {
                    "success": True,
                    "query_types": list(q_types),
                    "weights_used": weights,
                    "total_screened": len(library_smiles),
                    "total_hits": len(hits),
                    "hits": hits[:50],
                    "method": "enhanced_3d" if enhanced_available else "basic_set",
                }
            except ImportError:
                return {"success": False, "error": "RDKit not available"}
            except Exception as e:
                return {"success": False, "error": str(e)}

        return await asyncio.to_thread(_do_screen)
    
    def _hypothesis(self, input: dict):
        """Generate pharmacophore hypothesis from multiple active molecules."""
        active_smiles = input.get("active_smiles", [])
        min_coverage = input.get("min_coverage", 0.6)
        
        if len(active_smiles) < 2:
            return {"error": "Need at least 2 active molecules"}
        
        try:
            from rdkit import Chem
            from rdkit.Chem import AllChem, ChemicalFeatures
            from rdkit import RDConfig
            import numpy as np
            
            fdef = os.path.join(RDConfig.RDDataDir, "BaseFeatures.fdef")
            factory = ChemicalFeatures.BuildFeatureFactory(fdef) if os.path.exists(fdef) else None
            if not factory:
                return {"success": False, "error": "Feature factory not available"}
            
            all_mols = []
            for smi in active_smiles:
                mol = Chem.MolFromSmiles(smi.strip())
                if mol is None:
                    continue
                mol = Chem.AddHs(mol)
                AllChem.EmbedMolecule(mol, AllChem.ETKDG())
                feats = []
                for feat in factory.GetFeaturesForMol(mol):
                    pos = feat.GetPos()
                    feats.append({
                        "family": feat.GetFamily(),
                        "position": {"x": pos.x, "y": pos.y, "z": pos.z},
                    })
                all_mols.append({"smiles": smi.strip(), "features": feats})
            
            if not all_mols:
                return {"success": False, "error": "No valid molecules"}
            
            # Find conserved features
            FTYPES = ["Donor", "Acceptor", "Hydrophobic", "Aromatic", "PosIonizable", "NegIonizable"]
            common = []
            for ft in FTYPES:
                positions = []
                for entry in all_mols:
                    for f in entry["features"]:
                        if f["family"] == ft:
                            positions.append([f["position"]["x"], f["position"]["y"], f["position"]["z"]])
                if positions and len(positions) >= len(all_mols) * min_coverage:
                    pa = np.array(positions)
                    center = np.mean(pa, axis=0)
                    radius = float(min(np.max(np.linalg.norm(pa - center, axis=1)) + 1.0, 3.0))
                    common.append({
                        "type": ft, "family": ft,
                        "center": [round(c, 3) for c in center.tolist()],
                        "radius": round(radius, 2),
                        "color": FEATURE_COLORS.get(ft, "#888888"),
                        "coverage": round(len(positions) / len(all_mols), 2),
                    })
            
            common.sort(key=lambda x: x["coverage"], reverse=True)
            
            return {
                "success": True,
                "hypothesis": common[:6],
                "n_features": len(common[:6]),
                "n_molecules": len(all_mols),
            }
        except ImportError:
            return {"success": False, "error": "RDKit/NumPy required"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _nci_types(self):
        """Return NCI type reference data."""
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
            "feature_colors": FEATURE_COLORS,
        }
    
    def _enhanced_detect(self, input: dict):
        """Detect pharmacophore features with functional-group SMARTS (OpenPharmaco)."""
        smiles = input.get("smiles", "")
        if not smiles:
            return {"error": "smiles is required"}
        
        try:
            from modules.pharmacophore.engine import EnhancedPharmacophore
            engine = EnhancedPharmacophore()
            
            from rdkit import Chem
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return {"success": False, "error": "Invalid SMILES"}
            
            features = engine.detect_features(mol)
            viz = engine.export_visualization_data(features)
            
            return {
                "success": True,
                "smiles": smiles,
                "features": features,
                "num_features": len(features),
                "visualization": viz,
            }
        except Exception as e:
            log.error(f"Enhanced detect failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _enhanced_interactions(self, input: dict):
        """Extract protein-ligand interaction pharmacophore (Pharmer-style)."""
        protein_pdb = input.get("protein_pdb", "")
        ligand_smiles = input.get("ligand_smiles", "")
        cutoff = input.get("cutoff", 5.0)
        
        if not protein_pdb:
            return {"error": "protein_pdb is required"}
        if not ligand_smiles:
            return {"error": "ligand_smiles is required"}
        
        try:
            from modules.pharmacophore.engine import EnhancedPharmacophore
            engine = EnhancedPharmacophore()
            
            result = engine.extract_interaction_pharmacophore(
                protein_pdb, ligand_smiles, cutoff
            )
            
            # Add visualization data
            if result.get("interaction_features"):
                viz = engine.export_visualization_data(result["interaction_features"])
                result["visualization"] = viz
            
            result["success"] = True
            return result
        except Exception as e:
            log.error(f"Interaction pharmacophore failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _enhanced_screen(self, input: dict):
        """Screen compound library with multi-conformer matching (Pharmer-style)."""
        query_smiles = input.get("query_smiles", "")
        library_smiles = input.get("library_smiles", [])
        num_conformers = input.get("num_conformers", 3)
        min_score = input.get("min_score", 0.1)

        if not query_smiles:
            return {"error": "query_smiles is required"}
        if not library_smiles:
            return {"error": "library_smiles is required"}

        def _do_enhanced_screen():
            try:
                from modules.pharmacophore.engine import EnhancedPharmacophore
                engine = EnhancedPharmacophore()

                from rdkit import Chem
                query_mol = Chem.MolFromSmiles(query_smiles)
                if query_mol is None:
                    return {"success": False, "error": "Invalid SMILES"}

                # Detect query features
                query_features = engine.detect_features(query_mol)
                if not query_features:
                    return {"success": False, "error": "No features detected in query"}

                # Multi-conformer screen
                hits = engine.screen_library_multiconf(
                    query_features,
                    library_smiles,
                    num_conformers=num_conformers or 3,
                    min_match=3,
                )

                return {
                    "success": True,
                    "query_features": len(query_features),
                    "total_screened": len(library_smiles),
                    "total_hits": len(hits),
                    "hits": hits[:50],
                }
            except Exception as e:
                log.error(f"Enhanced screen failed: {e}")
                return {"success": False, "error": str(e)}

        return await asyncio.to_thread(_do_enhanced_screen)
    
    def _enhanced_model(self, input: dict):
        """Build consensus pharmacophore model (OpenPharmaco + Pharmer)."""
        active_smiles = input.get("active_smiles", [])
        min_coverage = input.get("min_coverage", 0.6)
        excluded_volume = input.get("excluded_volume", False)
        
        if len(active_smiles) < 2:
            return {"error": "Need at least 2 active molecules"}
        
        try:
            from modules.pharmacophore.engine import EnhancedPharmacophore
            engine = EnhancedPharmacophore()
            
            result = engine.build_pharmacophore_model(
                active_smiles,
                min_coverage=min_coverage or 0.6,
                add_excluded_volumes=excluded_volume if excluded_volume else False,
            )
            
            if "error" in result:
                return {"success": False, "error": result["error"]}
            
            result["success"] = True
            return result
        except Exception as e:
            log.error(f"Enhanced model failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _enhanced_fingerprint(self, input: dict):
        """Generate pharmacophore fingerprint (Pharmer-style 256-bit)."""
        smiles = input.get("smiles", "")
        if not smiles:
            return {"error": "smiles is required"}
        
        try:
            from modules.pharmacophore.engine import EnhancedPharmacophore
            engine = EnhancedPharmacophore()
            
            from rdkit import Chem
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return {"success": False, "error": "Invalid SMILES"}
            
            features = engine.detect_features(mol)
            fp = engine.generate_fingerprint(features)
            
            return {
                "success": True,
                "smiles": smiles,
                "num_features": len(features),
                "fingerprint": fp,
                "bits_set": fp.count("1"),
                "bits_total": len(fp),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _enhanced_shape(self, input: dict):
        """Calculate shape similarity between two molecules."""
        query_smiles = input.get("query_smiles", "")
        target_smiles = input.get("target_smiles", "")
        threshold = input.get("threshold", 0.5)
        
        if not query_smiles or not target_smiles:
            return {"error": "Both query_smiles and target_smiles are required"}
        
        try:
            from modules.pharmacophore.engine import EnhancedPharmacophore
            engine = EnhancedPharmacophore()
            
            from rdkit import Chem
            from rdkit.Chem import AllChem
            
            q_mol = Chem.MolFromSmiles(query_smiles)
            t_mol = Chem.MolFromSmiles(target_smiles)
            
            if q_mol is None or t_mol is None:
                return {"success": False, "error": "Invalid SMILES"}
            
            # Generate 3D
            q_mol = Chem.AddHs(q_mol)
            t_mol = Chem.AddHs(t_mol)
            AllChem.EmbedMolecule(q_mol, AllChem.ETKDGv3())
            AllChem.EmbedMolecule(t_mol, AllChem.ETKDGv3())
            
            similarity = engine.shape_similarity(q_mol, t_mol)
            
            return {
                "success": True,
                "query": query_smiles,
                "target": target_smiles,
                "shape_similarity": round(float(similarity), 4),
                "match": bool(similarity >= (threshold or 0.5)),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _enhanced_protein_features(self, input: dict):
        """Extract per-residue protein features (OpenPharmaco-style)."""
        protein_pdb = input.get("protein_pdb", "")
        cutoff = input.get("cutoff", 8.0)
        ligand_resname = input.get("ligand_resname", None)
        
        if not protein_pdb:
            return {"error": "protein_pdb is required"}
        
        try:
            from modules.pharmacophore.engine import EnhancedPharmacophore
            engine = EnhancedPharmacophore()

            features = engine.extract_protein_features(
                protein_pdb, cutoff=cutoff, ligand_resname=ligand_resname
            )

            return {
                "success": True,
                "features": features,
                "num_features": len(features),
                "feature_summary": {f["type"]: sum(1 for x in features if x["type"] == f["type"]) for f in features},
            }
        except Exception as e:
            log.error(f"Protein features failed: {e}")
            return {"success": False, "error": str(e)}

    async def _complete(self, input: dict):
        """Complete pharmacophore analysis — 8 publication-grade outputs.

        Inspired by Omixium's pharmacophore modeling pipeline.
        Returns: 2D plot, 3D HTML, distance CSV, distance heatmap,
        distribution plot, feature CSV, fingerprint summary, properties CSV.
        """
        smiles = input.get("smiles", "")
        name = input.get("name", "Molecule")
        if not smiles:
            return {"error": "smiles is required"}

        def _do_complete():
            try:
                from modules.pharmacophore.complete_analysis import complete_pharmacophore_analysis
                result = complete_pharmacophore_analysis(smiles, name)

                # Auto-store to KB
                if result.get("success"):
                    try:
                        from modules.knowledge.auto_store import auto_store
                        auto_store("pharmacophore",
                            "Complete Pharmacophore: " + name,
                            {"smiles": smiles, "feature_summary": result.get("feature_summary"),
                             "num_features": result.get("num_features"),
                             "molecular_properties": result.get("molecular_properties")},
                            source="Pharmacophore Complete Analysis",
                            tags=["pharmacophore", "complete", smiles[:20]])
                    except Exception:
                        pass

                return result
            except Exception as e:
                log.error(f"Complete pharmacophore failed: {e}")
                return {"success": False, "error": str(e)}

        return await asyncio.to_thread(_do_complete)

    async def _batch(self, input: dict):
        """Batch pharmacophore analysis — analyze multiple molecules at once.

        Returns per-molecule analysis + similarity matrix + batch summary.
        Inspired by Omixium's batch_pharmacophore_analyzer.py.
        """
        smiles_list = input.get("smiles_list", [])
        names = input.get("names", [])
        if not smiles_list:
            return {"error": "smiles_list is required"}

        def _do_batch():
            try:
                import numpy as np
                from modules.pharmacophore.complete_analysis import complete_pharmacophore_analysis
                from rdkit import Chem
                from rdkit.Chem import AllChem
                from rdkit import DataStructs

                results = []
                fingerprints = []

                for i, smi in enumerate(smiles_list):
                    name = names[i] if i < len(names) else f"Molecule_{i+1}"
                    try:
                        r = complete_pharmacophore_analysis(smi, name)
                        if r.get("success"):
                            results.append(r)
                        # Generate fingerprint for similarity
                        mol = Chem.MolFromSmiles(smi.strip())
                        if mol:
                            fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)
                            fingerprints.append(fp)
                        else:
                            fingerprints.append(None)
                    except Exception as e:
                        log.warning(f"Batch analysis failed for {name}: {e}")

                if not results:
                    return {"error": "No valid molecules analyzed"}

                # Similarity matrix (Tanimoto)
                n = len(results)
                sim_matrix = np.zeros((n, n))
                for i in range(n):
                    for j in range(i, n):
                        if i == j:
                            sim_matrix[i, j] = 1.0
                        elif fingerprints[i] and fingerprints[j]:
                            sim = DataStructs.TanimotoSimilarity(fingerprints[i], fingerprints[j])
                            sim_matrix[i, j] = sim
                            sim_matrix[j, i] = sim

                # Summary
                summary = {
                    "total_molecules": len(smiles_list),
                    "analyzed": len(results),
                    "avg_features": round(sum(r.get("num_features", 0) for r in results) / len(results), 1),
                    "feature_types": list(set(
                        t for r in results for t in r.get("feature_summary", {}).keys()
                    )),
                }

                return {
                    "success": True,
                    "summary": summary,
                    "molecule_count": len(results),
                    "similarity_matrix": sim_matrix.tolist(),
                    "molecule_names": [r.get("name", f"Mol_{i}") for i, r in enumerate(results)],
                    "results": results,
                }
            except Exception as e:
                log.error(f"Batch pharmacophore failed: {e}")
                return {"success": False, "error": str(e)}

        return await asyncio.to_thread(_do_batch)

    async def _compare(self, input: dict) -> dict:
        """Compare two pharmacophores — feature overlap, distance RMSD, similarity score.

        Input: smiles_1, smiles_2 (or features_1, features_2)
        Output: comparison metrics, matched/unmatched features, RMSD, similarity score.
        """
        smiles_1 = input.get("smiles_1", "")
        smiles_2 = input.get("smiles_2", "")
        features_1 = input.get("features_1", None)
        features_2 = input.get("features_2", None)

        def _do_compare():
          try:
            from rdkit import Chem
            from rdkit.Chem import AllChem, ChemicalFeatures
            from rdkit import RDConfig
            import numpy as np

            def get_features(smiles):
                mol = Chem.MolFromSmiles(smiles)
                if mol is None:
                    return []
                mol = Chem.AddHs(mol)
                AllChem.EmbedMolecule(mol, AllChem.ETKDG())
                AllChem.MMFFOptimizeMolecule(mol)
                fdef = os.path.join(RDConfig.RDDataDir, "BaseFeatures.fdef")
                factory = ChemicalFeatures.BuildFeatureFactory(fdef) if os.path.exists(fdef) else None
                if not factory:
                    return []
                feats = []
                for feat in factory.GetFeaturesForMol(mol):
                    pos = feat.GetPos()
                    feats.append({
                        "type": feat.GetType(),
                        "family": feat.GetFamily(),
                        "position": np.array([pos.x, pos.y, pos.z]),
                    })
                return feats

            # Get features
            if features_1 and features_2:
                def _extract_pos(f):
                    """Extract position as np.array — handles both flat {x,y,z} and nested {position:{x,y,z}}."""
                    pos = f.get("position", f)
                    if isinstance(pos, dict):
                        return np.array([pos.get("x", 0), pos.get("y", 0), pos.get("z", 0)])
                    return np.array([f.get("x", 0), f.get("y", 0), f.get("z", 0)])
                f1 = [{"type": f.get("type", ""), "family": f.get("family", ""),
                        "position": _extract_pos(f)} for f in features_1]
                f2 = [{"type": f.get("type", ""), "family": f.get("family", ""),
                        "position": _extract_pos(f)} for f in features_2]
            elif smiles_1 and smiles_2:
                f1 = get_features(smiles_1)
                f2 = get_features(smiles_2)
            else:
                return {"error": "Provide smiles_1/smiles_2 or features_1/features_2"}

            if not f1 or not f2:
                return {"error": "Could not extract features from one or both molecules"}

            # Match features by type
            matched = []
            unmatched_1 = []
            unmatched_2 = list(range(len(f2)))

            for i, feat1 in enumerate(f1):
                best_j = None
                best_dist = float('inf')
                for j in unmatched_2:
                    if f2[j]["family"] == feat1["family"]:
                        dist = np.linalg.norm(feat1["position"] - f2[j]["position"])
                        if dist < best_dist:
                            best_dist = dist
                            best_j = j
                if best_j is not None and best_dist < 5.0:  # 5Å tolerance
                    matched.append({
                        "type": feat1["family"],
                        "distance": round(float(best_dist), 3),
                        "mol1_idx": i,
                        "mol2_idx": best_j,
                    })
                    unmatched_2.remove(best_j)
                else:
                    unmatched_1.append({"type": feat1["family"], "mol1_idx": i})

            unmatched_2_features = [{"type": f2[j]["family"], "mol2_idx": j} for j in unmatched_2]

            # RMSD of matched features
            if matched:
                rmsd = round(float(np.sqrt(np.mean([m["distance"]**2 for m in matched]))), 3)
            else:
                rmsd = None

            # Similarity score
            total_features = len(f1) + len(f2)
            matched_count = len(matched)
            similarity = round(2 * matched_count / total_features, 3) if total_features > 0 else 0.0

            result = {
                "success": True,
                "mol1_features": len(f1),
                "mol2_features": len(f2),
                "matched": matched,
                "unmatched_mol1": unmatched_1,
                "unmatched_mol2": unmatched_2_features,
                "match_count": matched_count,
                "rmsd": rmsd,
                "similarity": similarity,
                "pharmacophore_overlap_pct": round(matched_count / max(len(f1), len(f2)) * 100, 1) if max(len(f1), len(f2)) > 0 else 0,
            }

            try:
                from modules.knowledge.auto_store import auto_store
                auto_store("pharmacophore", f"Pharmacophore Comparison",
                           {"similarity": similarity, "rmsd": rmsd, "matched_count": matched_count},
                           source="Pharmacophore Comparison", tags=["pharmacophore", "comparison"])
            except Exception:
                pass
            return result
          except Exception as e:
            log.error(f"Pharmacophore comparison failed: {e}")
            return {"success": False, "error": str(e)}

        return await asyncio.to_thread(_do_compare)
