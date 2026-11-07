"""Reaction Templates — SMARTS-based forward and retro transforms.

Covers the most common medicinal chemistry reactions:
amide coupling, Suzuki, reductive amination, SNAr, Buchwald-Hartwig, etc.
"""
import logging
from typing import Dict, List, Optional, Tuple

from rdkit import Chem
from rdkit.Chem import AllChem, rdChemReactions

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
        return [    # ── Additional templates (v7.39) ──
    {
        "name": "Heck Coupling",
        "category": "C-C bond",
        "forward_smarts": "[c:1][Br].[CH2:2]=[CH2:3]>>[c:1][CH:2]=[CH2:3]",
        "retro_smarts": "[c:1]-[CH]=[CH2]>>[c:1][Br].[C]=[C]",
        "reagents": ["Pd(OAc)2", "PPh3", "Et3N"],
        "conditions": "DMF, 80-100°C, N2",
        "reliability": 0.82,
    },
    {
        "name": "Sonogashira Coupling",
        "category": "C-C bond",
        "forward_smarts": "[c:1][Br].[CH2:2]#C>>[c:1]-[CH2:2]",
        "retro_smarts": "[c:1]-C#C>>[c:1][Br]",
        "reagents": ["PdCl2(PPh3)2", "CuI", "Et3N"],
        "conditions": "THF/Et3N, rt-50°C, N2",
        "reliability": 0.85,
    },
    {
        "name": "Grignard Addition",
        "category": "C-C bond",
        "forward_smarts": "[CH3:1][Mg].[C:2]=[O:3]>>[CH3:1][C:2][OH:3]",
        "retro_smarts": "[C](-[OH])(C)-C>>[C](=O)C.C[Mg]",
        "reagents": ["RMgBr", "Et2O"],
        "conditions": "Et2O, 0C to rt, N2",
        "reliability": 0.90,
    },
    {
        "name": "Wittig Olefination",
        "category": "C=C formation",
        "forward_smarts": "[C:1]=[O:2].[CH2:3]=P>>[C:1]=[CH2:3]",
        "retro_smarts": "[C]=[C]>>[C]=O",
        "reagents": ["Ph3P=CH2", "NaH"],
        "conditions": "THF, 0C to rt",
        "reliability": 0.88,
    },
    {
        "name": "Michael Addition",
        "category": "C-C bond",
        "forward_smarts": "[C:1]=[C:2]-[C:3]=[O:4].[N:5][H]>>[C:1](-[N:5])-[C:2]-[C:3]=[O:4]",
        "retro_smarts": "C(-N)-C-C=O>>N+C=C-C=O",
        "reagents": ["Et3N", "DMAP"],
        "conditions": "MeOH, rt",
        "reliability": 0.85,
    },
    {
        "name": "Epoxide Ring Opening",
        "category": "C-N bond",
        "forward_smarts": "[C:1]1[O:2][C:3]1.[N:4][H]>>[C:1](-[OH:2])-[C:3](-[N:4])",
        "retro_smarts": "C(O)-C(N)>>epoxide+N",
        "reagents": ["NaNH2", "EtOH"],
        "conditions": "EtOH, rt",
        "reliability": 0.87,
    },
    {
        "name": "Fischer Esterification",
        "category": "Functional group",
        "forward_smarts": "[C:1](=[O:2])[OH].[CH3:3][OH]>>[C:1](=[O:2])[O:3][CH3:3]",
        "retro_smarts": "[C](=O)OC>>[C](=O)O.CO",
        "reagents": ["MeOH", "H2SO4 (cat)"],
        "conditions": "Reflux, 4-16h",
        "reliability": 0.92,
    },
    {
        "name": "Boc Protection",
        "category": "Protection",
        "forward_smarts": "[N:1][H].C(=O)O-tBu>>[N:1]-C(=O)O-tBu",
        "retro_smarts": "[N]-C(=O)O-tBu>>[N][H]",
        "reagents": ["Boc2O", "Et3N", "DMAP"],
        "conditions": "CH2Cl2, rt",
        "reliability": 0.95,
    },
    {
        "name": "Boc Deprotection",
        "category": "Deprotection",
        "forward_smarts": "[N:1]-C(=O)O-tBu>>[N:1][H]",
        "retro_smarts": "[N][H]>>[N]-C(=O)O-tBu",
        "reagents": ["TFA"],
        "conditions": "CH2Cl2, rt, 30min",
        "reliability": 0.96,
    },
    {
        "name": "DMP Oxidation",
        "category": "Oxidation",
        "forward_smarts": "[C:1]-[OH:2]>>[C:1]=[O:2]",
        "retro_smarts": "[C]=O>>[C]-O",
        "reagents": ["Dess-Martin periodinane"],
        "conditions": "CH2Cl2, rt",
        "reliability": 0.92,
    },
    {
        "name": "NaBH4 Reduction",
        "category": "Reduction",
        "forward_smarts": "[C:1]=[O:2]>>[C:1]-[OH:2]",
        "retro_smarts": "[C]-O>>[C]=O",
        "reagents": ["NaBH4"],
        "conditions": "MeOH, 0C to rt",
        "reliability": 0.94,
    },
    {
        "name": "Diels-Alder",
        "category": "Ring formation",
        "forward_smarts": "C1=CC=CC=C1.C=C>>C1CC=CCC1",
        "retro_smarts": "C1CC=CCC1>>C1=CC=CC=C1.C=C",
        "reagents": ["Lewis acid or heat"],
        "conditions": "Toluene, 80-120C",
        "reliability": 0.82,
    },
    {
        "name": "HWE Olefination",
        "category": "C=C formation",
        "forward_smarts": "[C:1]=[O:2].P(=O)(OEt)2>>[C:1]=[CH]CO2Et",
        "retro_smarts": "[C]=[CH]CO2Et>>[C]=O",
        "reagents": ["(EtO)2P(O)CH2CO2Et", "NaH"],
        "conditions": "THF, 0C",
        "reliability": 0.86,
    },
    {
        "name": "Friedel-Crafts Acylation",
        "category": "C-C bond",
        "forward_smarts": "[c:1][H].[C:2](=[O:3])Cl>>[c:1][C:2](=[O:3])",
        "retro_smarts": "[c]-C(=O)>>[c][H].C(=O)Cl",
        "reagents": ["AlCl3", "CH2Cl2"],
        "conditions": "0C to rt",
        "reliability": 0.80,
    },
    {
        "name": "Nitrile Hydrolysis",
        "category": "Functional group",
        "forward_smarts": "[C:1]#N>>[C:1](=[O])[OH]",
        "retro_smarts": "[C](=O)O>>[C]#N",
        "reagents": ["H2SO4/H2O", "or NaOH/H2O"],
        "conditions": "Reflux",
        "reliability": 0.90,
    },
]
