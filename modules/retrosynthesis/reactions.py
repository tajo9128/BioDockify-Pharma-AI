"""Reaction Templates — SMARTS-based forward and retro transforms.

Covers the most common medicinal chemistry reactions:
amide coupling, Suzuki, reductive amination, SNAr, Buchwald-Hartwig, etc.
"""
import logging
from typing import Dict, List, Optional, Tuple

try:
    from rdkit import Chem
    from rdkit.Chem import AllChem, rdChemReactions
    HAS_RDKIT = True
except ImportError:
    HAS_RDKIT = False
    Chem = None
    rdChemReactions = None

log = logging.getLogger("retrosynthesis.reactions")

REACTION_TEMPLATES: List[Dict] = [
    {
        "name": "Amide Coupling",
        "category": "C-N bond",
        "forward_smarts": "[C:1](=[O:2])[OH].[N:3]([H])>>[C:1](=[O:2])[N:3]",
        "retro_smarts": "[C:1](=[O:2])[N:3]>>[C:1](=[O:2])[OH].[N:3][H]",
        "reagents": ["HATU or EDC/HOBt", "DIPEA", "DMF"],
        "conditions": "RT, 2-12h",
        "reliability": 0.95,
    },
    {
        "name": "Suzuki Coupling",
        "category": "C-C bond",
        "forward_smarts": "[c:1][Br].[c:2][B]([OH])[OH]>>[c:1][c:2]",
        "retro_smarts": "[c:1]-[c:2]>>[c:1][Br].[c:2]B(O)O",
        "reagents": ["Pd(PPh3)4 or Pd(dppf)Cl2", "K2CO3", "dioxane/H2O"],
        "conditions": "80-100°C, 4-16h, N2",
        "reliability": 0.90,
    },
    {
        "name": "Reductive Amination",
        "category": "C-N bond",
        "forward_smarts": "[C:1]=[O:2].[N:3]([H])[H]>>[C:1][N:3]",
        "retro_smarts": "[C:1][N:3]>>[C:1]=O.[N:3][H]",
        "reagents": ["NaBH3CN or NaBH(OAc)3", "AcOH"],
        "conditions": "RT, MeOH or DCE, 4-24h",
        "reliability": 0.88,
    },
    {
        "name": "Buchwald-Hartwig",
        "category": "C-N bond",
        "forward_smarts": "[c:1][Br].[N:2]([H])>>[c:1][N:2]",
        "retro_smarts": "[c:1][N:2]>>[c:1][Br].[N:2][H]",
        "reagents": ["Pd2(dba)3 / XPhos or BrettPhos", "NaOtBu", "toluene"],
        "conditions": "100°C, 12-24h, N2",
        "reliability": 0.82,
    },
    {
        "name": "SNAr",
        "category": "C-N bond",
        "forward_smarts": "[c:1]([F])[n:2].[N:3]([H])>>[c:1]([N:3])[n:2]",
        "retro_smarts": "[c:1]([N:3])[n:2]>>[c:1]([F])[n:2].[N:3][H]",
        "reagents": ["DIPEA or K2CO3"],
        "conditions": "80-120°C, DMSO or NMP, 4-12h",
        "reliability": 0.85,
    },
    {
        "name": "Ester Hydrolysis",
        "category": "Deprotection",
        "forward_smarts": "[C:1](=[O:2])[O:3][C:4]>>[C:1](=[O:2])[OH]",
        "retro_smarts": "[C:1](=[O:2])[OH]>>[C:1](=[O:2])OC",
        "reagents": ["LiOH or NaOH"],
        "conditions": "RT, THF/H2O, 2-6h",
        "reliability": 0.97,
    },
    {
        "name": "N-Alkylation",
        "category": "C-N bond",
        "forward_smarts": "[N:1]([H]).[C:2][Br]>>[N:1][C:2]",
        "retro_smarts": "[N:1][C:2]>>[N:1][H].[C:2]Br",
        "reagents": ["K2CO3 or Cs2CO3"],
        "conditions": "60-80°C, DMF, 4-12h",
        "reliability": 0.85,
    },
    {
        "name": "Wittig Olefination",
        "category": "C=C bond",
        "forward_smarts": "[C:1]=[O].[C:2]=[C:3]>>[C:1]=[C:2]",
        "retro_smarts": "[C:1]=[C:2]>>[C:1]=O.[C:2]=C",
        "reagents": ["Ph3P=CHR (Wittig salt)", "nBuLi or NaH"],
        "conditions": "0°C to RT, THF, 2-12h",
        "reliability": 0.78,
    },
    {
        "name": "Sonogashira Coupling",
        "category": "C-C bond",
        "forward_smarts": "[c:1][Br].[C:2]#[C:3]>>[c:1][C:2]#[C:3]",
        "retro_smarts": "[c:1][C:2]#[C:3]>>[c:1]Br.[C:2]#[C:3]",
        "reagents": ["PdCl2(PPh3)2", "CuI", "Et3N"],
        "conditions": "RT-60°C, THF, N2, 4-16h",
        "reliability": 0.85,
    },
    {
        "name": "Boc Deprotection",
        "category": "Deprotection",
        "forward_smarts": "[N:1][C](=[O])[O][C]([C])([C])[C]>>[N:1][H]",
        "retro_smarts": "[N:1][H]>>[N:1]C(=O)OC(C)(C)C",
        "reagents": ["TFA or HCl/dioxane"],
        "conditions": "RT, DCM, 1-2h",
        "reliability": 0.98,
    },
    {
        "name": "Heck Coupling",
        "category": "C-C bond",
        "forward_smarts": "[c:1][Br].[C:2]=[C:3]>>[c:1][C:2]=[C:3]",
        "retro_smarts": "[c:1]/[C:2]=[C:3]>>[c:1]Br.[C:2]=[C:3]",
        "reagents": ["Pd(OAc)2", "P(o-tol)3", "Et3N"],
        "conditions": "100°C, DMF, 12-24h, N2",
        "reliability": 0.80,
    },
    {
        "name": "Fischer Esterification",
        "category": "C-O bond",
        "forward_smarts": "[C:1](=[O:2])[OH].[O:3]([H])[C:4]>>[C:1](=[O:2])[O:3][C:4]",
        "retro_smarts": "[C:1](=[O:2])[O:3][C:4]>>[C:1](=[O:2])O.[O:3]([H])[C:4]",
        "reagents": ["H2SO4 (cat.)"],
        "conditions": "reflux, 12-24h, Dean-Stark",
        "reliability": 0.85,
    },
]


def get_reaction_templates(category: Optional[str] = None) -> List[Dict]:
    """Return available reaction templates, optionally filtered by category."""
    if category:
        cat = category.lower()
        return [r for r in REACTION_TEMPLATES if cat in r["category"].lower()]
    return REACTION_TEMPLATES


def apply_reaction(smarts: str, reactants: List[str]) -> List[str]:
    """Apply a forward reaction SMARTS to reactants, return product SMILES."""
    try:
        rxn = rdChemReactions.ReactionFromSmarts(smarts)
        if rxn is None:
            return []
        mols = [Chem.MolFromSmiles(s) for s in reactants]
        if any(m is None for m in mols):
            return []
        products = rxn.RunReactants(tuple(mols))
        results = []
        for prod_set in products:
            for mol in prod_set:
                try:
                    Chem.SanitizeMol(mol)
                    smi = Chem.MolToSmiles(mol)
                    if smi and smi not in results:
                        results.append(smi)
                except Exception:
                    pass
        return results[:10]
    except Exception as e:
        log.debug(f"apply_reaction failed: {e}")
        return []


def reverse_reaction(smarts: str, product: str) -> List[List[str]]:
    """Apply a retro-synthetic SMARTS to a product, return possible reactant sets."""
    try:
        rxn = rdChemReactions.ReactionFromSmarts(smarts)
        if rxn is None:
            return []
        mol = Chem.MolFromSmiles(product)
        if mol is None:
            return []
        results_raw = rxn.RunReactants((mol,))
        results = []
        for reactant_set in results_raw:
            reactants = []
            valid = True
            for rmol in reactant_set:
                try:
                    Chem.SanitizeMol(rmol)
                    smi = Chem.MolToSmiles(rmol)
                    if smi:
                        reactants.append(smi)
                    else:
                        valid = False
                except Exception:
                    valid = False
            if valid and reactants and reactants not in results:
                results.append(reactants)
        return results[:10]
    except Exception as e:
        log.debug(f"reverse_reaction failed: {e}")
        return []
