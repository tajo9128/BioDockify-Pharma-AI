"""Similarity-based activity analysis — find analogues, detect activity cliffs."""
import logging
import numpy as np
from typing import Dict, List, Optional

from rdkit import Chem, DataStructs
from rdkit.Chem import AllChem, Descriptors

from .fingerprints import compute_ecfp4

log = logging.getLogger("bioactivity_predictor.similarity")

REFERENCE_ACTIVES = {
    "kinase": [
        ("c1ccc2c(c1)c(cn2)c1ccnc(Nc2ccc(cc2)NC(=O)C)n1", 7.8, "Imatinib-like"),
        ("Nc1ncnc2c1cc(-c1cccc(c1)C#C)n2C1CCCC1", 7.2, "CDK inhibitor scaffold"),
        ("c1ccc(Nc2nccc(-c3cn[nH]c3)n2)cc1", 6.8, "Pyrimidine-pyrazole kinase"),
    ],
    "gpcr": [
        ("Clc1ccc(cc1)C(c1ccccc1)N1CCN(CC1)CCOC", 7.5, "Diphenylmethyl piperazine"),
        ("c1ccc2c(c1)[nH]c1c2cccc1CCN(C)C", 7.0, "Tryptamine scaffold"),
        ("O=C1NC(=O)c2ccccc2N1c1ccc(cc1)N1CCNCC1", 6.5, "Benzodiazepine-like GPCR"),
    ],
    "protease": [
        ("CC(C)CC(NC(=O)C(CC1CCCCC1)NC(=O)OCC1c2ccccc2-c2ccccc21)C(=O)O", 7.0, "Peptidomimetic"),
        ("O=C(NC(CC1CCCCC1)B(O)O)C1CCCN1C(=O)OCC(C)(C)C", 8.0, "Boronate warhead"),
    ],
    "nuclear_receptor": [
        ("OC1(c2ccc(O)cc2)CCc2cc(O)ccc2C1c1ccc(OCCN(CC)CC)cc1", 7.5, "SERM scaffold"),
        ("CC(C)c1ccc(cc1)C(=O)c1cc(c(cc1F)OCC(=O)O)S(=O)(=O)c1ccccc1", 6.8, "PPAR modulator"),
    ],
}


def find_similar_actives(smiles: str, target_class: str = "general",
                         threshold: float = 0.3) -> Dict:
    """Find known active molecules similar to the query.

    Uses Tanimoto similarity on ECFP4 fingerprints against reference actives.
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"error": "Invalid SMILES"}

    canonical = Chem.MolToSmiles(mol)
    query_fp = compute_ecfp4(canonical)
    if query_fp is None:
        return {"error": "Fingerprint computation failed"}

    refs = REFERENCE_ACTIVES.get(target_class, [])
    if not refs:
        all_refs = []
        for class_refs in REFERENCE_ACTIVES.values():
            all_refs.extend(class_refs)
        refs = all_refs

    hits = []
    for ref_smi, ref_pic50, ref_name in refs:
        ref_fp = compute_ecfp4(ref_smi)
        if ref_fp is None:
            continue
        # Tanimoto
        intersection = np.sum(query_fp & ref_fp)
        union = np.sum(query_fp | ref_fp)
        sim = intersection / union if union > 0 else 0.0

        if sim >= threshold:
            hits.append({
                "smiles": ref_smi,
                "name": ref_name,
                "pic50": ref_pic50,
                "similarity": round(float(sim), 3),
            })

    hits.sort(key=lambda x: x["similarity"], reverse=True)

    return {
        "query": canonical,
        "target_class": target_class,
        "num_similar": len(hits),
        "similar_actives": hits[:10],
        "most_similar": hits[0] if hits else None,
    }


def activity_cliff_analysis(smiles_list: List[str], activities: List[float]) -> Dict:
    """Detect activity cliffs — pairs with high structural similarity but large activity difference.

    Activity cliffs are critical SAR insights: small structural changes → big potency shifts.
    """
    if len(smiles_list) != len(activities):
        return {"error": "SMILES list and activities must be same length"}
    if len(smiles_list) < 2:
        return {"error": "Need at least 2 molecules"}

    n = min(len(smiles_list), 50)
    fps = []
    valid_idx = []
    for i in range(n):
        fp = compute_ecfp4(smiles_list[i])
        if fp is not None:
            fps.append(fp)
            valid_idx.append(i)

    if len(fps) < 2:
        return {"error": "Need at least 2 valid molecules"}

    cliffs = []
    for i in range(len(fps)):
        for j in range(i + 1, len(fps)):
            intersection = np.sum(fps[i] & fps[j])
            union = np.sum(fps[i] | fps[j])
            sim = intersection / union if union > 0 else 0.0

            if sim >= 0.5:
                act_diff = abs(activities[valid_idx[i]] - activities[valid_idx[j]])
                if act_diff >= 1.0:
                    cliffs.append({
                        "mol_a": smiles_list[valid_idx[i]],
                        "mol_b": smiles_list[valid_idx[j]],
                        "similarity": round(float(sim), 3),
                        "activity_a": activities[valid_idx[i]],
                        "activity_b": activities[valid_idx[j]],
                        "activity_diff": round(act_diff, 2),
                        "cliff_score": round(float(sim) * act_diff, 2),
                    })

    cliffs.sort(key=lambda x: x["cliff_score"], reverse=True)

    return {
        "num_molecules": len(valid_idx),
        "num_cliffs": len(cliffs),
        "cliffs": cliffs[:20],
        "top_cliff": cliffs[0] if cliffs else None,
    }
