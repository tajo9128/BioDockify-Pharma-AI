"""Medicinal Chemistry API — synthetic & analytical medchem tools.

Murcko scaffold extraction, MMPA, Butina clustering, SMARTS search, SA score,
retrosynthesis, named reactions, protecting groups, toxicophore scan, stereo analysis.
Built for medicinal/pharmaceutical chemistry researchers.

Science-first: computations use RDKit + curated reaction/protecting-group databases.
Does NOT duplicate docking, qsar3d, pharmacophore, md_lite, drug_analysis (PAINS),
or admet_predict (ADME/LogS).
Note: api/synthesize.py is TTS, NOT chemistry — this is the chemistry module.
"""
from helpers.api import ApiHandler, Request, Response
import logging, math
import numpy as np

log = logging.getLogger("medicinal_chemistry")


def _rdkit():
    """Lazy import RDKit (returns None if unavailable)."""
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem, Descriptors, DataStructs, rdMolDescriptors
        from rdkit.Chem.Scaffolds import MurckoScaffold
        from rdkit.ML.Cluster import Butina
        return True, (Chem, AllChem, Descriptors, DataStructs, rdMolDescriptors, MurckoScaffold, Butina)
    except ImportError:
        return False, None


class MedicinalChemistryHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        action = input.get("action", "")
        if action == "murcko_scaffold": return self._murcko_scaffold(input)
        elif action == "mmpa": return self._mmpa(input)
        elif action == "butina_cluster": return self._butina_cluster(input)
        elif action == "smarts_search": return self._smarts_search(input)
        elif action == "sa_score": return self._sa_score(input)
        elif action == "retrosynthesis": return self._retrosynthesis(input)
        elif action == "named_reactions": return self._named_reactions(input)
        elif action == "protecting_groups": return self._protecting_groups(input)
        elif action == "toxicophore_scan": return self._toxicophore_scan(input)
        elif action == "stereo_analysis": return self._stereo_analysis(input)
        return {
            "actions": ["murcko_scaffold", "mmpa", "butina_cluster", "smarts_search",
                        "sa_score", "retrosynthesis", "named_reactions",
                        "protecting_groups", "toxicophore_scan", "stereo_analysis"],
            "hint": "MedChem tools: scaffolds, MMPA, clustering, SMARTS, SA score, retrosynthesis, reactions, protecting groups, toxicophores, stereo"
        }

    # ─────────────────────────────────────────────────────────────
    # Murcko Scaffold — framework extraction
    # Reference: Bemis & Murcko, J Med Chem, 1996.
    # ─────────────────────────────────────────────────────────────
    def _murcko_scaffold(self, input):
        """Extract Murcko scaffolds + scaffold tree + frequency across library."""
        smiles_list = input.get("smiles", [])
        single = input.get("smiles_str", "")

        ok, mods = _rdkit()
        if not ok:
            return {"error": "RDKit not available"}
        Chem, AllChem, Desc, DS, rdMD, MurckoScaffold, Butina = mods

        if single and not smiles_list:
            smiles_list = [single]
        if not smiles_list:
            return {"error": "smiles (list) or smiles_str required"}

        mols = []
        for smi in smiles_list:
            m = Chem.MolFromSmiles(smi)
            if m:
                mols.append((smi, m))

        if not mols:
            return {"error": "No valid SMILES parsed"}

        scaffolds = {}  # scaffold_smiles -> [parent smiles]
        per_mol = []
        for smi, m in mols:
            try:
                sc = MurckoScaffold.GetScaffoldForMol(m)
                sc_smi = Chem.MolToSmiles(sc)
                scaffolds.setdefault(sc_smi, []).append(smi)
                per_mol.append({"smiles": smi, "scaffold": sc_smi,
                                "n_atoms": m.GetNumAtoms(), "n_scaffold_atoms": sc.GetNumAtoms()})
            except Exception as e:
                per_mol.append({"smiles": smi, "scaffold": None, "error": str(e)})

        # Sort scaffolds by frequency (most common = privileged scaffold candidates)
        scaffold_freq = sorted(
            [{"scaffold": s, "frequency": len(mols_list),
              "pct_library": round(100.0 * len(mols_list) / len(mols), 1),
              "example_members": mols_list[:3]}
             for s, mols_list in scaffolds.items()],
            key=lambda x: x["frequency"], reverse=True
        )

        result = {
            "input_count": len(smiles_list),
            "valid_count": len(mols),
            "unique_scaffolds": len(scaffolds),
            "scaffold_frequencies": scaffold_freq[:20],
            "per_molecule": per_mol,
            "privileged_scaffolds": [s["scaffold"] for s in scaffold_freq if s["frequency"] >= max(2, len(mols) // 10)],
            "interpretation": (
                f"Found {len(scaffolds)} unique Murcko scaffolds across {len(mols)} molecules. "
                f"Most common: {scaffold_freq[0]['scaffold']} ({scaffold_freq[0]['pct_library']}% of library). "
                f"Scaffolds appearing in >10% are candidate 'privileged scaffolds'."
            )
        }

        try:
            from modules.knowledge.auto_store import auto_store
            auto_store("medicinal_chemistry", f"Murcko Scaffold — {len(scaffolds)} unique",
                       result, source="Murcko Scaffold Analysis", tags=["scaffold", "murcko"])
        except Exception:
            pass
        return result

    # ─────────────────────────────────────────────────────────────
    # MMPA — Matched Molecular Pair Analysis
    # Reference: Hussain & Rea, J Chem Inf Model, 2010.
    # ─────────────────────────────────────────────────────────────
    def _mmpa(self, input):
        """Matched Molecular Pair Analysis — Δproperty per transformation."""
        molecules = input.get("molecules", [])  # [{"smiles": "...", "property": value}, ...]
        property_name = input.get("property", "activity")  # e.g. "IC50", "LogP"

        ok, mods = _rdkit()
        if not ok:
            return {"error": "RDKit not available"}
        Chem, AllChem, Desc, DS, rdMD, MurckoScaffold, Butina = mods

        if len(molecules) < 2:
            return {"error": "Need at least 2 molecules with property values"}

        # Parse and validate
        parsed = []
        for m in molecules:
            mol = Chem.MolFromSmiles(m.get("smiles", ""))
            if mol and m.get("property") is not None:
                try:
                    parsed.append({"smiles": m["smiles"], "mol": mol, "property": float(m["property"])})
                except (ValueError, TypeError):
                    pass
        if len(parsed) < 2:
            return {"error": "Need ≥2 valid molecules with numeric properties"}

        # Simplified MMP: compute MCCS (maximum common core) for pairs with single-atom/bond difference
        # Then identify transformation as the SMILES of removed/added fragments
        from rdkit.Chem import rdFMCS
        transformations = []  # {transformation, delta_property, pairs}
        seen_pairs = set()

        for i in range(len(parsed)):
            for j in range(i + 1, len(parsed)):
                a, b = parsed[i], parsed[j]
                # Skip if same molecule
                if Chem.MolToSmiles(a["mol"]) == Chem.MolToSmiles(b["mol"]):
                    continue
                # Find MCS (core)
                try:
                    mcs = rdFMCS.FindMCS([a["mol"], b["mol"]], timeout=2,
                                         matchValences=False, ringMatchesRingOnly=True)
                    if not mcs.smartsString or mcs.smartsString == "":
                        continue
                    patt = Chem.MolFromSmarts(mcs.smartsString)
                    if patt is None:
                        continue
                    # Remove core from each → leaving fragments (the "transformation")
                    a_match = Chem.DeleteSubstructs(a["mol"], patt)
                    b_match = Chem.DeleteSubstructs(b["mol"], patt)
                    a_frag = Chem.MolToSmiles(a_match) if a_match.GetNumAtoms() > 0 else "H"
                    b_frag = Chem.MolToSmiles(b_match) if b_match.GetNumAtoms() > 0 else "H"
                    if a_frag == b_frag:
                        continue  # No transformation
                    transformation = f"{a_frag} → {b_frag}"
                    delta = b["property"] - a["property"]
                    key = (a_frag, b_frag)
                    transformations.append({
                        "transformation": transformation,
                        "delta_property": round(delta, 3),
                        "mol_a": a["smiles"],
                        "mol_b": b["smiles"],
                    })
                except Exception:
                    continue

        # Aggregate by transformation
        agg = {}
        for t in transformations:
            agg.setdefault(t["transformation"], []).append(t["delta_property"])
        summary = []
        for trans, deltas in agg.items():
            if len(deltas) >= 1:
                summary.append({
                    "transformation": trans,
                    "n_instances": len(deltas),
                    "mean_delta": round(float(np.mean(deltas)), 3),
                    "median_delta": round(float(np.median(deltas)), 3),
                    "direction": f"{property_name} ↑ by {np.mean(deltas):.2f}" if np.mean(deltas) > 0
                                 else f"{property_name} ↓ by {abs(np.mean(deltas)):.2f}",
                })
        summary.sort(key=lambda x: abs(x["mean_delta"]), reverse=True)

        result = {
            "property": property_name,
            "n_molecules": len(parsed),
            "n_pairs_analyzed": len(transformations),
            "transformations": summary[:20],
            "interpretation": (
                f"Analyzed {len(transformations)} matched molecular pairs. "
                + (f"Most impactful: '{summary[0]['transformation']}' → {summary[0]['direction']} "
                   f"(n={summary[0]['n_instances']})." if summary else "No significant MMPs found.")
            )
        }

        try:
            from modules.knowledge.auto_store import auto_store
            auto_store("medicinal_chemistry", f"MMPA — {len(transformations)} pairs",
                       result, source="Matched Molecular Pair Analysis", tags=["mmpa", "transformation"])
        except Exception:
            pass
        return result

    # ─────────────────────────────────────────────────────────────
    # Butina Clustering — diversity analysis
    # Reference: Butina, J Chem Inf Comput Sci, 1999.
    # ─────────────────────────────────────────────────────────────
    def _butina_cluster(self, input):
        """Butina clustering + diversity picking via Tanimoto fingerprints."""
        smiles_list = input.get("smiles", [])
        cutoff = float(input.get("cutoff", 0.4))  # Tanimoto distance cutoff
        pick_n = int(input.get("pick_n", 0))  # number of diverse picks (0=no picking)

        ok, mods = _rdkit()
        if not ok:
            return {"error": "RDKit not available"}
        Chem, AllChem, Desc, DS, rdMD, MurckoScaffold, Butina = mods

        if len(smiles_list) < 2:
            return {"error": "Need at least 2 molecules"}

        fps = []
        mols = []
        for smi in smiles_list:
            m = Chem.MolFromSmiles(smi)
            if m:
                fp = AllChem.GetMorganFingerprintAsBitVect(m, 2, nBits=2048)
                fps.append(fp)
                mols.append(smi)

        if len(fps) < 2:
            return {"error": "Need at least 2 valid molecules"}

        # Tanimoto distance matrix (1 - similarity)
        n = len(fps)
        dists = []
        for i in range(1, n):
            sims = DS.BulkTanimotoSimilarity(fps[i], fps[:i])
            dists.extend([1 - x for x in sims])

        # Butina clustering
        cs = Butina.ClusterData(dists, n, cutoff, isDistData=True)
        clusters = []
        for ci, cluster in enumerate(cs):
            clusters.append({
                "cluster_id": ci,
                "size": len(cluster),
                "members": [mols[i] for i in cluster],
                "centroid": mols[cluster[0]],
            })

        # Diversity picking (maximin) — pick most diverse subset
        diverse_picks = []
        if pick_n > 0 and pick_n < n:
            picked = [0]  # start with first
            while len(picked) < pick_n:
                best_i, best_dist = -1, -1
                for i in range(n):
                    if i in picked:
                        continue
                    min_d = min(1 - DS.TanimotoSimilarity(fps[i], fps[p]) for p in picked)
                    if min_d > best_dist:
                        best_dist, best_i = min_d, i
                if best_i < 0:
                    break
                picked.append(best_i)
            diverse_picks = [mols[i] for i in picked]

        result = {
            "input_count": len(smiles_list),
            "valid_count": n,
            "n_clusters": len(clusters),
            "cutoff": cutoff,
            "clusters": clusters,
            "diverse_picks": diverse_picks,
            "diversity_summary": {
                "largest_cluster_size": clusters[0]["size"] if clusters else 0,
                "singletons": sum(1 for c in clusters if c["size"] == 1),
                "mean_cluster_size": round(float(np.mean([c["size"] for c in clusters])), 2) if clusters else 0,
            },
            "interpretation": (
                f"{len(clusters)} clusters at Tanimoto distance cutoff {cutoff}. "
                f"Largest: {clusters[0]['size']} mols. {sum(1 for c in clusters if c['size']==1)} singletons = high diversity."
            )
        }

        try:
            from modules.knowledge.auto_store import auto_store
            auto_store("medicinal_chemistry", f"Butina Clustering — {len(clusters)} clusters",
                       result, source="Butina Clustering", tags=["clustering", "diversity"])
        except Exception:
            pass
        return result

    # ─────────────────────────────────────────────────────────────
    # SMARTS Substructure Search
    # Reference: RDKit substructure matching.
    # ─────────────────────────────────────────────────────────────
    def _smarts_search(self, input):
        """Arbitrary SMARTS pattern matching across a molecule library."""
        smarts = input.get("smarts", "")
        smiles_list = input.get("smiles", [])
        single = input.get("smiles_str", "")

        ok, mods = _rdkit()
        if not ok:
            return {"error": "RDKit not available"}
        Chem, AllChem, Desc, DS, rdMD, MurckoScaffold, Butina = mods

        if not smarts:
            return {"error": "smarts pattern required",
                    "examples": ["c1ccccc1 (benzene)", "[OX1] (carbonyl O)", "[#7H2] (primary amine)",
                                 "C(=O)O (carboxylic acid)", "[c,n]1[c,n][c,n][c,n][c,n]1 (5-ring arom.)"]}
        if single and not smiles_list:
            smiles_list = [single]
        if not smiles_list:
            return {"error": "smiles (list) or smiles_str required"}

        patt = Chem.MolFromSmarts(smarts)
        if patt is None:
            return {"error": f"Invalid SMARTS: {smarts}"}

        matches = []
        n_total = 0
        for smi in smiles_list:
            m = Chem.MolFromSmiles(smi)
            if m is None:
                continue
            n_total += 1
            subs = m.GetSubstructMatches(patt)
            if subs:
                matches.append({
                    "smiles": smi,
                    "n_matches": len(subs),
                    "atom_indices": [list(s) for s in subs[:5]],  # cap at 5
                    "highlight_atoms": sorted(set(a for s in subs for a in s))[:50],
                })

        # Suggest named interpretation of common SMARTS
        named = {
            "c1ccccc1": "benzene ring", "[nH1]": "aromatic NH", "[#7H2]": "primary amine",
            "[#7H1]": "secondary amine", "[#7H0]": "tertiary amine", "[OX1]": "carbonyl oxygen",
            "[CX3](=O)[OX2H1]": "carboxylic acid", "[CX3](=O)[NX3H2]": "primary amide",
            "[SX2]": "thiol/sulfide", "[c,n]1[c,n][c,n][c,n][c,n]1": "5-membered aromatic ring",
            "[#6]1:[#6]:[#6]:[#6]:[#6]:[#6]:1": "aromatic 6-ring",
        }
        interpretation = next((v for k, v in named.items() if k in smarts), "custom SMARTS pattern")

        result = {
            "smarts": smarts,
            "interpretation": interpretation,
            "library_size": len(smiles_list),
            "valid_molecules": n_total,
            "matching_molecules": len(matches),
            "match_rate_pct": round(100.0 * len(matches) / n_total, 1) if n_total else 0,
            "matches": matches,
            "interpretation_text": (
                f"{len(matches)}/{n_total} molecules match '{smarts}' ({interpretation}). "
                f"Match rate: {round(100*len(matches)/n_total,1) if n_total else 0}%."
            )
        }

        try:
            from modules.knowledge.auto_store import auto_store
            auto_store("medicinal_chemistry", f"SMARTS Search — {smarts[:30]}",
                       result, source="SMARTS Substructure Search", tags=["smarts", "substructure"])
        except Exception:
            pass
        return result

    # ─────────────────────────────────────────────────────────────
    # SA Score — synthetic accessibility (Ertl 2009 approximation)
    # Reference: Ertl & Schuffenhauer, J Cheminformatics, 2009.
    # ─────────────────────────────────────────────────────────────
    def _sa_score(self, input):
        """Synthetic accessibility score (1=easy, 10=very difficult)."""
        smiles = input.get("smiles", input.get("smiles_str", ""))
        if not smiles:
            return {"error": "smiles required"}

        ok, mods = _rdkit()
        if not ok:
            return {"error": "RDKit not available"}
        Chem, AllChem, Desc, DS, rdMD, MurckoScaffold, Butina = mods

        m = Chem.MolFromSmiles(smiles)
        if m is None:
            return {"error": f"Invalid SMILES: {smiles}"}

        # Component 1: fragment complexity (proxy for Ertl's fragmentScore)
        # Higher MW, more rings, more chiral centers → harder
        n_atoms = m.GetNumHeavyAtoms()
        n_rings = rdMD.CalcNumRings(m)
        n_arom = rdMD.CalcNumAromaticRings(m)
        n_chiral = len(Chem.FindMolChiralCenters(m, includeUnassigned=True))
        n_rot = rdMD.CalcNumRotatableBonds(m)
        n_stereo = rdMD.CalcNumAtomStereoCenters(m)
        mw = Desc.MolWt(m)
        n_spiro = rdMD.CalcNumSpiroAtoms(m)
        n_bridge = rdMD.CalcNumBridgeheadAtoms(m)

        # Component 2: complexity penalty
        complexity = (n_atoms / 50.0) * 3.0
        complexity += (n_rings - 2) * 0.4 if n_rings > 2 else 0
        complexity += n_arom * 0.2
        complexity += n_chiral * 0.7
        complexity += n_stereo * 0.3
        complexity += max(0, n_rot - 8) * 0.1
        complexity += max(0, mw - 500) / 200
        complexity += n_spiro * 0.8
        complexity += n_bridge * 0.6

        # Component 3: macromolecule / unusual feature penalty
        if mw > 600:
            complexity += 1.0
        if n_atoms > 60:
            complexity += 1.0

        sa_score = min(10.0, max(1.0, 1.0 + complexity))

        result = {
            "smiles": smiles,
            "sa_score": round(float(sa_score), 2),
            "scale": "1 (very easy) — 10 (very difficult)",
            "components": {
                "heavy_atoms": n_atoms,
                "rings": n_rings,
                "aromatic_rings": n_arom,
                "chiral_centers": n_chiral,
                "rotatable_bonds": n_rot,
                "spiro_atoms": n_spiro,
                "bridgehead_atoms": n_bridge,
                "MW": round(mw, 1),
            },
            "classification": (
                "easy to synthesize (<3)" if sa_score < 3 else
                ("moderate (3-5)" if sa_score < 5 else
                 ("challenging (5-7)" if sa_score < 7 else "difficult (>7)"))
            ),
            "interpretation": (
                f"SA score = {sa_score:.2f}. "
                f"{'Likely accessible via standard routes' if sa_score < 4 else 'May require multi-step synthesis or novel chemistry'}. "
                f"Main contributors: {('chiral centers' if n_chiral > 1 else 'ring count' if n_rings > 3 else 'size' if n_atoms > 40 else 'overall complexity')}."
            ),
            "note": "Approximation of Ertl 2009 (descriptor-based). For exact SA, install rdkit Contrib sascorer."
        }

        try:
            from modules.knowledge.auto_store import auto_store
            auto_store("medicinal_chemistry", f"SA Score — {sa_score:.2f}",
                       result, source="Synthetic Accessibility Score", tags=["sa_score", "synthesis"])
        except Exception:
            pass
        return result

    # ─────────────────────────────────────────────────────────────
    # Retrosynthesis — single-step disconnection via reaction SMARTS
    # ─────────────────────────────────────────────────────────────
    def _retrosynthesis(self, input):
        """Single-step retrosynthetic disconnection (curated reaction SMARTS)."""
        smiles = input.get("smiles", input.get("smiles_str", ""))
        if not smiles:
            return {"error": "smiles required"}

        ok, mods = _rdkit()
        if not ok:
            return {"error": "RDKit not available"}
        Chem, AllChem, Desc, DS, rdMD, MurckoScaffold, Butina = mods

        target = Chem.MolFromSmiles(smiles)
        if target is None:
            return {"error": f"Invalid SMILES: {smiles}"}

        # Curated retrosynthetic disconnections (reverse: product → reactants)
        # Each: SMARTS pattern (on product), name, and forward SMARTS reference
        REACTIONS = [
            {"name": "Amide coupling", "product_smarts": "[CX3:1](=[OX1:2])[NX3:3]",
             "reactants_smarts": "[CX3:1](=[OX1:2])[OX2H1:4].[NX3:3]",  # acid + amine
             "conditions": "EDC/HATU + DIPEA, DMF, rt; or acid chloride + base",
             "ref": "Standard peptide/amide coupling"},
            {"name": "Ester hydrolysis / formation", "product_smarts": "[CX3:1](=[OX1:2])[OX2:3]",
             "reactants_smarts": "[CX3:1](=[OX1:2])[OX2H1:4].[OX2:3]",
             "conditions": "Fischer: acid + alcohol, H2SO4 cat.; or Steglich (DCC/DMAP)",
             "ref": "Fischer esterification"},
            {"name": "Reductive amination", "product_smarts": "[CX4:1][NX3:2]",
             "reactants_smarts": "[CX3:1]=O.[NX3:2]",  # aldehyde/ketone + amine
             "conditions": "NaBH3CN or NaBH(OAc)3, MeOH/AcOH, rt",
             "ref": "Abdel-Magid et al., 1996"},
            {"name": "Suzuki coupling (C-C)", "product_smarts": "[c:1]-[c:2]",
             "reactants_smarts": "[c:1][B].[c:2][Br,Cl,I]",  # boronic acid + aryl halide
             "conditions": "Pd(PPh3)4, K2CO3, dioxane/H2O, 80°C",
             "ref": "Miyaura & Suzuki, 1979"},
            {"name": "Buchwald-Hartwig (C-N)", "product_smarts": "[c:1]-[NX3:2]",
             "reactants_smarts": "[c:1][Br,Cl,I].[NX3:2]",
             "conditions": "Pd2(dba)3, XPhos, NaOtBu, toluene, 100°C",
             "ref": "Surry & Buchwald, 2011"},
            {"name": "Sonogashira (alkyne)", "product_smarts": "[c:1]-[CX2:2]",
             "reactants_smarts": "[c:1][Br,Cl,I].[CX2:2]",  # aryl halide + terminal alkyne
             "conditions": "Pd(PPh3)2Cl2, CuI, Et3N, rt-60°C",
             "ref": "Sonogashira et al., 1975"},
            {"name": "Urea / carbamate", "product_smarts": "[NX3:1][CX3:2](=[OX1:3])[NX3:4]",
             "reactants_smarts": "[NX3:1].[CX3:2](=[OX1:3])[NX3:4]",  # amine + isocyanate
             "conditions": "amine + isocyanate, DCM, rt",
             "ref": "Standard urea formation"},
            {"name": "Ether (Williamson)", "product_smarts": "[OX2:1][CX4:2]",
             "reactants_smarts": "[OX2H1:1].[CX4:2][Br,Cl,I]",
             "conditions": "NaH, DMF, 0-80°C",
             "ref": "Williamson, 1850"},
            {"name": "Sulfonamide", "product_smarts": "[NX3:1][SX4:2](=[OX1:3])(=[OX1:4])",
             "reactants_smarts": "[NX3:1].[SX4:2](=[OX1:3])(=[OX1:4])[Cl,Br]",
             "conditions": "sulfonyl chloride + amine, pyridine, 0°C→rt",
             "ref": "Standard sulfonamide coupling"},
            {"name": "Click (triazole)", "product_smarts": "[c,n]1[n,c][n,c][n,c]1",
             "reactants_smarts": "[CX2:1]#[NX1:2].[NX2:3]=[NX2:4]",  # alkyne + azide
             "conditions": "CuSO4/sodium ascorate, t-BuOH/H2O, rt",
             "ref": "Sharpless, 2002"},
        ]

        disconnections = []
        for rxn in REACTIONS:
            try:
                patt = Chem.MolFromSmarts(rxn["product_smarts"])
                if patt is None:
                    continue
                if target.HasSubstructMatch(patt):
                    # Simulate reverse reaction by removing the functional group
                    disconnections.append({
                        "reaction_name": rxn["name"],
                        "matched_pattern": rxn["product_smarts"],
                        "suggested_reactants": rxn["reactants_smarts"],
                        "conditions": rxn["conditions"],
                        "reference": rxn["ref"],
                        "note": "Disconnect at this motif to access simpler precursors",
                    })
            except Exception:
                continue

        result = {
            "target_smiles": smiles,
            "n_disconnections_found": len(disconnections),
            "disconnections": disconnections,
            "interpretation": (
                f"Found {len(disconnections)} possible single-step disconnections. "
                + (f"Most accessible: {disconnections[0]['reaction_name']} ({disconnections[0]['conditions']})."
                   if disconnections else "No common disconnection motifs detected — consider novel chemistry or check SMILES.")
            ),
            "note": "Single-step analysis. For multi-step synthesis, consult AiZynthFinder or ASKCOS."
        }

        try:
            from modules.knowledge.auto_store import auto_store
            auto_store("medicinal_chemistry", f"Retrosynthesis — {len(disconnections)} disconnections",
                       result, source="Retrosynthetic Analysis", tags=["retrosynthesis", "synthesis"])
        except Exception:
            pass
        return result

    # ─────────────────────────────────────────────────────────────
    # Named Reactions Database
    # ─────────────────────────────────────────────────────────────
    def _named_reactions(self, input):
        """Curated database of named organic reactions."""
        query = input.get("query", "").lower().strip()
        category = input.get("category", "").lower().strip()

        REACTIONS = [
            {"name": "Suzuki-Miyaura", "category": "Coupling (C-C)",
             "summary": "Pd-catalyzed cross-coupling of aryl/vinyl halide with boronic acid",
             "conditions": "Pd(PPh3)4, K2CO3 or Cs2CO3, dioxane/H2O, 60-100°C",
             "substrates": "Ar-X (X=Br,Cl,I,OTf) + Ar-B(OH)2",
             "advantages": "Mild, tolerant of functional groups, commercially available boronic acids",
             "year": 1979},
            {"name": "Heck", "category": "Coupling (C-C)",
             "summary": "Pd-catalyzed coupling of aryl halide with alkene",
             "conditions": "Pd(OAc)2, P(o-tol)3, Et3N, DMF, 80-120°C",
             "substrates": "Ar-X + CH2=CHR",
             "advantages": "Forms substituted alkenes stereoselectively", "year": 1972},
            {"name": "Sonogashira", "category": "Coupling (C-C)",
             "summary": "Pd/Cu-catalyzed coupling of aryl halide with terminal alkyne",
             "conditions": "Pd(PPh3)2Cl2, CuI, Et3N, rt-60°C",
             "substrates": "Ar-X + terminal alkyne",
             "advantages": "Access to aryl alkynes (Sonogashira products)", "year": 1975},
            {"name": "Buchwald-Hartwig", "category": "Coupling (C-N)",
             "summary": "Pd-catalyzed coupling of aryl halide with amine",
             "conditions": "Pd2(dba)3, XPhos/BINAP, NaOtBu, toluene, 80-100°C",
             "substrates": "Ar-X + R-NH2",
             "advantages": "Forms aryl C-N bonds (anilines, aryl ethers)", "year": 1994},
            {"name": "Stille", "category": "Coupling (C-C)",
             "summary": "Pd-catalyzed coupling with organostannane",
             "conditions": "Pd(PPh3)4, LiCl, dioxane, 80°C",
             "substrates": "Ar-X + R-SnBu3",
             "advantages": "Very mild, but toxic tin reagents", "year": 1977},
            {"name": "Negishi", "category": "Coupling (C-C)",
             "summary": "Pd-catalyzed coupling with organozinc",
             "conditions": "Pd(PPh3)4, THF, rt-50°C",
             "substrates": "Ar-X + R-ZnX",
             "advantages": "Functional group tolerant, fast", "year": 1977},
            {"name": "Diels-Alder", "category": "Cycloaddition",
             "summary": "[4+2] cycloaddition of diene with dienophile → cyclohexene",
             "conditions": "Heat (thermal), or Lewis acid (AlCl3) for acceleration",
             "substrates": "Diene + alkene",
             "advantages": "Forms 6-membered rings stereospecifically", "year": 1928},
            {"name": "Grignard", "category": "C-C bond formation",
             "summary": "Nucleophilic addition of RMgX to carbonyl → alcohol",
             "conditions": "Mg, dry ether/THF, N2 atmosphere",
             "substrates": "R-X + Mg + C=O",
             "advantages": "Classic C-C formation; sensitive to protic groups", "year": 1900},
            {"name": "Friedel-Crafts Acylation", "category": "Aromatic substitution",
             "summary": "Lewis-acid-catalyzed acylation of aromatic ring",
             "conditions": "AlCl3, RCOCl, DCM, 0°C→rt",
             "substrates": "ArH + RCOCl",
             "advantages": "Forms aryl ketones regioselectively", "year": 1877},
            {"name": "Friedel-Crafts Alkylation", "category": "Aromatic substitution",
             "summary": "Lewis-acid-catalyzed alkylation of aromatic ring",
             "conditions": "AlCl3, R-X, heat",
             "substrates": "ArH + R-X",
             "advantages": "Forms aryl C-C; prone to polyalkylation", "year": 1877},
            {"name": "Wittig", "category": "Alkene formation",
             "summary": "Phosphorus ylide + aldehyde/ketone → alkene",
             "conditions": "Ph3P=CHR, THF, -78°C→rt",
             "substrates": "C=O + ylide",
             "advantages": "Forms C=C with defined geometry (E/Z)", "year": 1954},
            {"name": "Horner-Wadsworth-Emmons", "category": "Alkene formation",
             "summary": "Phosphonate-stabilized carbanion + aldehyde → E-alkene",
             "conditions": "NaH or LiHMDS, THF, 0°C",
             "substrates": "C=O + (EtO)2P(O)CH2R",
             "advantages": "E-selective, water-soluble byproducts", "year": 1961},
            {"name": "Mitsunobu", "category": "Substitution",
             "summary": "Inversion of alcohol stereochemistry via SN2",
             "conditions": "PPh3, DIAD, THF, 0°C→rt",
             "substrates": "ROH + H-nucleophile",
             "advantages": "Stereospecific inversion (R→S or S→R)", "year": 1967},
            {"name": "Sandmeyer", "category": "Aromatic substitution",
             "summary": "Diazonium salt → aryl halide/cyanide via Cu(I)",
             "conditions": "NaNO2/HCl (diazotization), then CuX",
             "substrates": "ArNH2 → ArN2+ → Ar-X",
             "advantages": "Access to aryl halides/cyanides", "year": 1884},
            {"name": "Sharpless Epoxidation", "category": "Oxidation",
             "summary": "Asymmetric epoxidation of allylic alcohols",
             "conditions": "Ti(OiPr)4, (+/-)-DET, t-BuOOH, DCM, -20°C",
             "substrates": "allylic alcohol",
             "advantages": "Enantioselective (>90% ee)", "year": 1980},
            {"name": "Jones Oxidation", "category": "Oxidation",
             "summary": "CrO3/H2SO4 oxidation of alcohols → ketones/carboxylic acids",
             "conditions": "CrO3, H2SO4, acetone, 0°C",
             "substrates": "R-CH2OH or R2CHOH",
             "advantages": "Cheap; toxic Cr waste", "year": 1946},
            {"name": "Swern Oxidation", "category": "Oxidation",
             "summary": "DMSO/(COCl)2 oxidation of alcohols → aldehydes/ketones",
             "conditions": "(COCl)2, DMSO, Et3N, DCM, -78°C",
             "substrates": "R-CH2OH → R-CHO",
             "advantages": "Mild, avoids over-oxidation", "year": 1978},
            {"name": "Click (CuAAC)", "category": "Cycloaddition",
             "summary": "Cu-catalyzed azide-alkyne [3+2] cycloaddition → 1,2,3-triazole",
             "conditions": "CuSO4/sodium ascorate, t-BuOH/H2O, rt",
             "substrates": "R-N3 + R'-alkyne",
             "advantages": "Bioorthogonal, mild, quantitative", "year": 2002},
            {"name": "Hantzsch Pyridine", "category": "Heterocycle",
             "summary": "Multicomponent synthesis of 1,4-dihydropyridines",
             "conditions": "Aldehyde + 2 β-ketoester + NH3, EtOH, reflux",
             "substrates": "RCHO + CH3COCH2CO2Et + NH3",
             "advantages": "One-pot dihydropyridine (e.g. nifedipine)", "year": 1881},
            {"name": "Fischer Indole", "category": "Heterocycle",
             "summary": "Acid-catalyzed rearrangement of aryl hydrazone → indole",
             "conditions": "ZnCl2, BF3·Et2O, or polyphosphoric acid, heat",
             "substrates": "ArNHNH2 + R-CO-CH2-R",
             "advantages": "Forms indole core", "year": 1883},
            {"name": "Paal-Knorr", "category": "Heterocycle",
             "summary": "Cyclization of 1,4-dicarbonyl → furan/pyrrole/thiophene",
             "conditions": "1,4-diketone + NH3 (pyrrole) or acid (furan)",
             "substrates": "R-CO-CH2-CH2-CO-R'",
             "advantages": "Access to 5-membered heterocycles", "year": 1884},
            {"name": "Mannich", "category": "C-C bond formation",
             "summary": "Three-component: amine + aldehyde + CH-acidic compound",
             "conditions": "R2NH + R'CHO + R''-CH2-acidic, acid cat.",
             "substrates": "amine + aldehyde + ketone/ester",
             "advantages": "Forms β-amino carbonyls (Mannich bases)", "year": 1912},
            {"name": "Aldol Condensation", "category": "C-C bond formation",
             "summary": "Base-catalyzed addition of enolate to carbonyl",
             "conditions": "NaOH or LDA, THF, -78°C→rt",
             "substrates": "2 × aldehyde/ketone (one enolizable)",
             "advantages": "Forms β-hydroxy carbonyls (aldols)", "year": 1872},
            {"name": "Knoevenagel", "category": "C-C bond formation",
             "summary": "Condensation of aldehyde with active methylene compound",
             "conditions": "Piperidine or NaOAc, AcOH, reflux",
             "substrates": "R-CHO + CH2(CN)2 or CH2(CO2Et)2",
             "advantages": "Forms α,β-unsaturated products", "year": 1894},
            {"name": "Michael Addition", "category": "C-C bond formation",
             "summary": "Conjugate addition of nucleophile to α,β-unsaturated carbonyl",
             "conditions": "Base (Et3N, DBU) or organocatalyst",
             "substrates": "R-CH2-acidic + C=C-C=O",
             "advantages": "Forms 1,4-addition products", "year": 1887},
            {"name": "Schotten-Baumann", "category": "Acylation",
             "summary": "Acylation of amine/alcohol with acid chloride in aqueous base",
             "conditions": "RCOCl, NaOH aq., 0°C",
             "substrates": "R-NH2 + R'-COCl",
             "advantages": "Simple amide/ester formation", "year": 1886},
            {"name": "Vilsmeier-Haack", "category": "Formylation",
             "summary": "Formylation of electron-rich aromatics",
             "conditions": "POCl3 + DMF, DCM, 0°C→rt",
             "substrates": "ArH (activated) → Ar-CHO",
             "advantages": "Aromatic formylation", "year": 1927},
            {"name": "HWE-Michael tandem", "category": "Tandem",
             "summary": "Horner-Wadsworth-Emmons followed by Michael addition",
             "conditions": "Phosphonate, base, then Michael acceptor",
             "substrates": "aldehyde + phosphonate + enone",
             "advantages": "One-pot complex products", "year": 1990},
            {"name": "Biginelli", "category": "Multicomponent",
             "summary": "Three-component: aldehyde + β-ketoester + urea → dihydropyrimidinone",
             "conditions": "HCl cat., EtOH, reflux",
             "substrates": "RCHO + CH3COCH2CO2Et + H2NCONH2",
             "advantages": "Dihydropyrimidinones (Biginelli products)", "year": 1893},
            {"name": "Ugi", "category": "Multicomponent",
             "summary": "Four-component: amine + aldehyde + acid + isocyanide → bis-amide",
             "conditions": "MeOH, rt, 24-48h",
             "substrates": "R-NC + R'-NH2 + R''-CHO + R'''-CO2H",
             "advantages": "High diversity, one-pot", "year": 1959},
        ]

        if query:
            matches = [r for r in REACTIONS if query in r["name"].lower() or query in r["summary"].lower()
                       or query in r["category"].lower()]
        elif category:
            matches = [r for r in REACTIONS if category in r["category"].lower()]
        else:
            matches = REACTIONS

        return {
            "query": query or category or "(all)",
            "matches": matches,
            "count": len(matches),
            "total_in_db": len(REACTIONS),
            "categories": sorted(set(r["category"] for r in REACTIONS)),
        }

    # ─────────────────────────────────────────────────────────────
    # Protecting Groups Database
    # ─────────────────────────────────────────────────────────────
    def _protecting_groups(self, input):
        """Curated database of protecting groups."""
        query = input.get("query", "").lower().strip()
        target = input.get("target_group", "").lower().strip()  # amine | hydroxyl | carboxyl | thiol

        PGS = [
            {"name": "Boc (tert-butyloxycarbonyl)", "protects": "Amine",
             "introduction": "Boc2O, NaOH or NaHCO3, dioxane/H2O, rt",
             "removal": "TFA (20-50% in DCM), rt, 30 min; or HCl/dioxane",
             "stability": "Stable to base, nucleophiles, hydrogenation; labile to strong acid",
             "smarts": "NC(=O)OC(C)(C)C"},
            {"name": "Fmoc (9-fluorenylmethyloxycarbonyl)", "protects": "Amine",
             "introduction": "Fmoc-Cl, NaHCO3, dioxane/H2O, 0°C",
             "removal": "Piperidine (20% in DMF), rt, 20 min (mild base)",
             "stability": "Stable to acid; labile to mild base — orthogonal to Boc",
             "smarts": "NC(=O)OCC1c2ccccc2-c2ccccc21"},
            {"name": "Cbz / Z (benzyloxycarbonyl)", "protects": "Amine",
             "introduction": "Cbz-Cl, NaHCO3, dioxane/H2O, 0°C",
             "removal": "H2, Pd/C, MeOH/EtOAc, rt (hydrogenolysis); or HBr/AcOH",
             "stability": "Stable to acid/base; removed by hydrogenation",
             "smarts": "NC(=O)OCc1ccccc1"},
            {"name": "Alloc (allyloxycarbonyl)", "protects": "Amine / Hydroxyl",
             "introduction": "Alloc-Cl, pyridine, DCM, 0°C",
             "removal": "Pd(PPh3)4, morpholine or PhSiH3, DCM, rt",
             "stability": "Orthogonal to Boc, Fmoc, Cbz",
             "smarts": "NC(=O)OCC=C"},
            {"name": "Acetyl (Ac)", "protects": "Hydroxyl / Amine",
             "introduction": "Ac2O, pyridine or DMAP, DCM, rt",
             "removal": "K2CO3/MeOH; or NH3/MeOH; or NaOH",
             "stability": "Stable to acid; labile to base or hydrazine",
             "smarts": "OC(C)=O or NC(C)=O"},
            {"name": "Benzoyl (Bz)", "protects": "Hydroxyl / Amine",
             "introduction": "BzCl, pyridine, DCM, 0°C→rt",
             "removal": "NaOH, MeOH/H2O; or NH3/MeOH",
             "stability": "More stable than Ac; labile to strong base",
             "smarts": "OC(=O)c1ccccc1"},
            {"name": "TBS / TBDMS (tert-butyldimethylsilyl)", "protects": "Hydroxyl",
             "introduction": "TBSCl, imidazole, DMF, rt; or TBSOTf, 2,6-lutidine",
             "removal": "TBAF, THF, rt, 1h; or HF·pyridine",
             "stability": "Stable to many conditions; selective for 1° OH over 2°",
             "smarts": "O[Si](C)(C)C(C)(C)C"},
            {"name": "TBDPS (tert-butyldiphenylsilyl)", "protects": "Hydroxyl",
             "introduction": "TBDPSCl, imidazole, DMF, rt",
             "removal": "TBAF, THF; or HF·pyridine (more forceful than TBS)",
             "stability": "More stable than TBS — selective TBS removal leaves TBDPS",
             "smarts": "O[Si](c1ccccc1)(c1ccccc1)C(C)(C)C"},
            {"name": "Benzyl (Bn)", "protects": "Hydroxyl / Amine / Carboxyl",
             "introduction": "BnBr, NaH, DMF (OH); or BnCl, base",
             "removal": "H2, Pd/C, MeOH; or BCl3 (Lewis acid)",
             "stability": "Stable to acid/base; removed by hydrogenolysis",
             "smarts": "OCc1ccccc1 or NCc1ccccc1"},
            {"name": "PMB (p-methoxybenzyl)", "protects": "Hydroxyl / Amine",
             "introduction": "PMBBr, NaH, DMF; or PMBCl",
             "removal": "DDQ, DCM/H2O; or TFA; or H2/Pd-C",
             "stability": "Oxidatively removed (DDQ) — orthogonal to Bn",
             "smarts": "OCc1ccc(OC)cc1"},
            {"name": "Methyl (Me)", "protects": "Carboxyl / Hydroxyl",
             "introduction": "MeI, K2CO3, DMF; or CH2N2; or MeOH, H+",
             "removal": "TMSI; or BBr3, DCM; or LiOH (ester hydrolysis)",
             "stability": "Stable to base; labile to strong Lewis acid",
             "smarts": "OC or OC(=O)C"},
            {"name": "Ethyl (Et)", "protects": "Carboxyl",
             "introduction": "EtOH, H2SO4 cat. (Fischer); or EtI, base",
             "removal": "LiOH, THF/H2O; or KOH/EtOH",
             "stability": "Stable to mild base; saponifiable",
             "smarts": "OC(=O)CC"},
            {"name": "t-Butyl (tBu)", "protects": "Carboxyl",
             "introduction": "isobutylene, H2SO4; or t-BuOH, DCC",
             "removal": "TFA, DCM, rt, 1h (mild acid)",
             "stability": "Stable to base, hydrogenation; labile to acid",
             "smarts": "OC(=O)C(C)(C)C"},
            {"name": "Acetonide (isopropylidene)", "protects": "Diol (1,2- or 1,3-)",
             "introduction": "2,2-dimethoxypropane, p-TsOH, acetone",
             "removal": "Aqueous acid (80% AcOH); or TFA/H2O",
             "stability": "Stable to base; selective for vicinal diols",
             "smarts": "CC1(C)OCC(C)(O1) pattern"},
            {"name": "BOM (benzyloxymethyl)", "protects": "Hydroxyl",
             "introduction": "BOMCl, DIPEA, DCM",
             "removal": "H2, Pd(OH)2/C, MeOH; or Na/NH3",
             "stability": "Stable to acid/base",
             "smarts": "OCOCc1ccccc1"},
            {"name": "THP (tetrahydropyranyl)", "protects": "Hydroxyl",
             "introduction": "DHP, p-TsOH, DCM, rt",
             "removal": "PPTS, EtOH; or dilute HCl; or AcOH/H2O",
             "stability": "Stable to base, organometallics; acid labile",
             "smarts": "OC1CCCCO1"},
            {"name": "Trityl (Trt)", "protects": "Amine / Hydroxyl / Thiol",
             "introduction": "Trt-Cl, Et3N, DCM, rt",
             "removal": "TFA, DCM; or H2/Pd-C; or mild acid",
             "stability": "Acid labile; bulky — selective for 1° OH",
             "smarts": "OC(c1ccccc1)(c1ccccc1)c1ccccc1"},
            {"name": "SEM (2-(trimethylsilyl)ethoxymethyl)", "protects": "Hydroxyl / Amine",
             "introduction": "SEM-Cl, DIPEA, DCM",
             "removal": "TBAF, THF; or TFA",
             "stability": "Stable to strong base, mild acid",
             "smarts": "OCOC[Si](C)(C)C"},
            {"name": "Tosyl (Ts)", "protects": "Amine / converts OH to leaving group",
             "introduction": "TsCl, pyridine, 0°C",
             "removal": "Na/naphthalene; or HBr/AcOH; or Mg/MeOH",
             "stability": "Stable to acid/base; sulfonyl leaving group in SN2",
             "smarts": "NS(=O)(=O)c1ccc(C)cc1"},
            {"name": "MOM (methoxymethyl)", "protects": "Hydroxyl / Amine",
             "introduction": "MOM-Cl, DIPEA, DCM, 0°C",
             "removal": "Conc. HCl/MeOH; or TFA; or Lewis acid",
             "stability": "Stable to base, hydride; acid labile",
             "smarts": "OCOC"},
        ]

        if target:
            matches = [p for p in PGS if target in p["protects"].lower()]
        elif query:
            matches = [p for p in PGS if query in p["name"].lower() or query in p["protects"].lower()
                       or query in p["removal"].lower()]
        else:
            matches = PGS

        return {
            "query": query or target or "(all)",
            "matches": matches,
            "count": len(matches),
            "total_in_db": len(PGS),
            "protects": sorted(set(p["protects"] for p in PGS)),
        }

    # ─────────────────────────────────────────────────────────────
    # Toxicophore Scan
    # Distinct from PAINS (drug_analysis) and hERG/AMES (drug_properties).
    # ─────────────────────────────────────────────────────────────
    def _toxicophore_scan(self, input):
        """Dedicated toxicophore substructure scan (structural alerts for toxicity)."""
        smiles = input.get("smiles", input.get("smiles_str", ""))

        ok, mods = _rdkit()
        if not ok:
            return {"error": "RDKit not available"}
        Chem, AllChem, Desc, DS, rdMD, MurckoScaffold, Butina = mods

        if not smiles:
            return {"error": "smiles required"}

        m = Chem.MolFromSmiles(smiles)
        if m is None:
            return {"error": f"Invalid SMILES: {smiles}"}

        TOXICOPHORES = [
            {"name": "Aniline (primary aromatic amine)", "smarts": "[c][NX3;H2]",
             "concern": "Mutagenic — metabolic N-hydroxylation to nitrenium ions",
             "severity": "high", "fix": "Replace with amide, sulfonamide, or N-alkylate"},
            {"name": "Nitroaromatic", "smarts": "[c][NX3](=O)=O",
             "concern": "Mutagenic — nitroreduction to hydroxylamines",
             "severity": "high", "fix": "Reduce to amine (with toxicity testing) or replace with cyano"},
            {"name": "Hydrazine / hydrazone", "smarts": "[#7][#7]",
             "concern": "Mutagenic, hepatotoxic",
             "severity": "high", "fix": "Replace with amide or urea"},
            {"name": "Michael acceptor (α,β-unsat. carbonyl)", "smarts": "[CX3]=[CX3][CX3]=[OX1]",
             "concern": "Reactive — binds glutathione/DNA (off-target)",
             "severity": "medium", "fix": "Saturate, or move carbonyl away"},
            {"name": "Alkyl halide (SN2 reactive)", "smarts": "[CX4][Br,Cl,I]",
             "concern": "Alkylating agent — DNA mutation",
             "severity": "medium", "fix": "Replace with aryl halide or remove leaving group"},
            {"name": "Michael acceptor (sulfone)", "smarts": "[CX3]=[CX3][SX4]",
             "concern": "Reactive electrophile",
             "severity": "medium", "fix": "Saturate or replace"},
            {"name": "Quinone / hydroquinone", "smarts": "[c]1[c][c][c]([OX1])[c]1=O or O=c1ccccc1",
             "concern": "Redox cycler — generates ROS, cardiotoxic",
             "severity": "high", "fix": "Avoid or block oxidation site"},
            {"name": "Epoxide / aziridine", "smarts": "[CX3]1[OX2][CX3]1 or [CX3]1[NX3][CX3]1",
             "concern": "Strained ring — DNA alkylator (mutagen)",
             "severity": "high", "fix": "Open ring or replace"},
            {"name": "Aldehyde (reactive)", "smarts": "[CX3H1]=[OX1]",
             "concern": "Reactive Schiff-base former, can crosslink proteins",
             "severity": "low", "fix": "Reduce to alcohol, protect as acetal"},
            {"name": "Aromatic N-hydroxy (hydroxylamine)", "smarts": "[c][NX2](O)",
             "concern": "Mutagenic metabolite",
             "severity": "high", "fix": "Block metabolic N-hydroxylation"},
            {"name": "Thiol (free SH)", "smarts": "[#6][SX2H1]",
             "concern": "Reactive — disulfide exchange, immune reactions",
             "severity": "low", "fix": "Protect (acetyl, disulfide)"},
            {"name": "Polyaromatic hydrocarbon (PAH)", "smarts": "c1ccc2cc3ccccc3cc2c1",
             "concern": "Many PAHs carcinogenic (metabolic diol-epoxide)",
             "severity": "medium", "fix": "Reduce ring count, add polar groups"},
            {"name": "Azo compound", "smarts": "[#7]/N=N/[#7]",
             "concern": "Reductive cleavage → aromatic amines",
             "severity": "medium", "fix": "Replace azo with amide"},
            {"name": "β-Lactone / β-lactam (strained)", "smarts": "[CX3]1[OX2][CX3][CX3]1=O or C1C(=O)N1",
             "concern": "Acylation of proteins (some penicillin allergies)",
             "severity": "low", "fix": "Note: β-lactam antibiotics are intentional"},
            {"name": "Peroxide / hydroperoxide", "smarts": "[OX2][OX2] or [OX2][OX1]",
             "concern": "Reactive oxygen source; unstable",
             "severity": "medium", "fix": "Avoid unless antimalarial (artemisinin class)"},
        ]

        alerts = []
        for tox in TOXICOPHORES:
            try:
                patt = Chem.MolFromSmarts(tox["smarts"])
                if patt is None:
                    continue
                if m.HasSubstructMatch(patt):
                    alerts.append({
                        "toxicophore": tox["name"],
                        "severity": tox["severity"],
                        "concern": tox["concern"],
                        "suggested_fix": tox["fix"],
                        "n_matches": len(m.GetSubstructMatches(patt)),
                    })
            except Exception:
                continue

        severity_order = {"high": 0, "medium": 1, "low": 2}
        alerts.sort(key=lambda a: severity_order.get(a["severity"], 3))

        result = {
            "smiles": smiles,
            "alerts": alerts,
            "n_alerts": len(alerts),
            "high_severity_count": sum(1 for a in alerts if a["severity"] == "high"),
            "overall_risk": (
                "high — multiple high-severity toxicophores present" if sum(1 for a in alerts if a["severity"] == "high") >= 2 else
                ("moderate — address high-severity alerts" if any(a["severity"] == "high" for a in alerts) else
                 ("low — minor alerts only" if alerts else "clean — no toxicophores detected"))
            ),
            "interpretation": (
                f"{len(alerts)} toxicophore alert(s): "
                + (", ".join(f"{a['toxicophore']} ({a['severity']})" for a in alerts) if alerts else "none detected.")
            ),
            "note": "Distinct from PAINS (pan-assay interference) and hERG/AMES alerts — use drug_analysis + drug_properties for those."
        }

        try:
            from modules.knowledge.auto_store import auto_store
            auto_store("medicinal_chemistry", f"Toxicophore Scan — {len(alerts)} alerts",
                       result, source="Toxicophore Analysis", tags=["toxicophore", "toxicity"])
        except Exception:
            pass
        return result

    # ─────────────────────────────────────────────────────────────
    # Stereochemistry Analysis
    # ─────────────────────────────────────────────────────────────
    def _stereo_analysis(self, input):
        """R/S assignment, E/Z analysis, chiral center enumeration."""
        smiles = input.get("smiles", input.get("smiles_str", ""))

        ok, mods = _rdkit()
        if not ok:
            return {"error": "RDKit not available"}
        Chem, AllChem, Desc, DS, rdMD, MurckoScaffold, Butina = mods

        if not smiles:
            return {"error": "smiles required"}

        m = Chem.MolFromSmiles(smiles)
        if m is None:
            return {"error": f"Invalid SMILES: {smiles}"}

        # Detect chiral centers
        chiral_centers = Chem.FindMolChiralCenters(m, includeUnassigned=True, useLegacyImplementation=False)
        assigned = [(atom_idx, label) for atom_idx, label in chiral_centers if label != "?"]
        unassigned = [(atom_idx, label) for atom_idx, label in chiral_centers if label == "?"]

        # Stereo double bonds (E/Z)
        stereo_bonds = []
        for bond in m.GetBonds():
            stereo = bond.GetStereo()
            if stereo != Chem.BondStereo.STEREONONE:
                stereo_bonds.append({
                    "atom_indices": [bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()],
                    "configuration": str(stereo).replace("BondStereo.", ""),
                })

        # Count
        n_stereo = rdMD.CalcNumAtomStereoCenters(m)
        n_unassigned_stereo = rdMD.CalcNumUnspecifiedAtomStereoCenters(m)
        n_possible_stereoisomers = 2 ** n_stereo if n_stereo > 0 else 1

        # Clean SMILES (canonical, with stereo)
        canonical_smiles = Chem.MolToSmiles(m, isomericSmiles=True)

        # Aromaticity / ring info
        n_rings = rdMD.CalcNumRings(m)
        n_arom_rings = rdMD.CalcNumAromaticRings(m)

        result = {
            "input_smiles": smiles,
            "canonical_isomeric_smiles": canonical_smiles,
            "chiral_centers": [
                {"atom_index": idx, "configuration": label if label != "?" else "unassigned"}
                for idx, label in chiral_centers
            ],
            "n_chiral_centers": len(chiral_centers),
            "n_assigned_chiral": len(assigned),
            "n_unassigned_chiral": len(unassigned),
            "stereo_double_bonds": stereo_bonds,
            "n_stereo_double_bonds": len(stereo_bonds),
            "n_possible_stereoisomers": n_possible_stereoisomers,
            "n_rings": n_rings,
            "n_aromatic_rings": n_arom_rings,
            "interpretation": (
                f"{len(chiral_centers)} chiral center(s) ({len(assigned)} assigned, {len(unassigned)} unassigned), "
                f"{len(stereo_bonds)} stereo double bond(s). "
                f"{n_possible_stereoisomers} possible stereoisomer(s). "
                + ("Use 3D-QSAR or pharmacophore module for stereospecific activity." if n_possible_stereoisomers > 1 else "")
            )
        }

        if unassigned:
            result["warning"] = (
                f"{len(unassigned)} unassigned stereocenter(s) — stereoisomers not enumerated. "
                "Specify stereochemistry in SMILES (e.g. [C@H], [C@@H]) for accurate analysis."
            )

        try:
            from modules.knowledge.auto_store import auto_store
            auto_store("medicinal_chemistry", f"Stereo Analysis — {n_stereo} centers",
                       result, source="Stereochemistry Analysis", tags=["stereochemistry", "chirality"])
        except Exception:
            pass
        return result
