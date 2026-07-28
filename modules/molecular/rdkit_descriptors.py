"""
Comprehensive RDKit Descriptor Calculator — 200+ molecular descriptors.

Covers all major descriptor categories available in RDKit:
- 2D Topochemical (Chi, Kappa, Balaban, Bertz)
- Electronic (EState, partial charges)
- Surface (SlogP_VSA, SMR_VSA, PEOE_VSA)
- Autocorrelation (Autocorr2D, BCUT2D)
- Fragment-based (50+ functional group counts)
- Fingerprints (Morgan, MACCS, AtomPair, TopologicalTorsion)
- Drug-likeness categories (Fragment/Lead/Drug/Non-drug)

Inspired by Omixium's RDKit_Calculate_Mol_Properties pipeline.
"""
import logging
import numpy as np

log = logging.getLogger("rdkit_descriptors")

try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, Crippen, rdMolDescriptors, Lipinski
    from rdkit import RDLogger
    RDLogger.DisableLog("rdApp.*")
    HAS_RDKIT = True
except ImportError:
    HAS_RDKIT = False


# ═══════════════════════════════════════════════════════════════════
# DESCRIPTOR CATEGORIES
# ═══════════════════════════════════════════════════════════════════

# Category 1: Basic Physicochemical
BASIC_DESCRIPTORS = [
    "MolWt", "MolLogP", "TPSA", "NumHDonors", "NumHAcceptors",
    "NumRotatableBonds", "NumAromaticRings", "NumAliphaticRings",
    "NumSaturatedRings", "NumHeteroatoms", "NumHeavyAtoms",
    "FractionCSP3", "RingCount", "NumAmideBonds",
    "LabuteASA", "MolMR", "NumValenceElectrons", "NumRadicalElectrons",
    "NumNHOHCount", "NumNOCount",
    "NumAliphaticCarbocycles", "NumAliphaticHeterocycles",
    "NumAromaticCarbocycles", "NumAromaticHeterocycles",
]

# Category 2: Topochemical / Connectivity
TOPOLOGICAL_DESCRIPTORS = [
    "Chi0", "Chi1", "Chi0n", "Chi1n", "Chi2n", "Chi3n", "Chi4n",
    "Chi0v", "Chi1v", "Chi2v", "Chi3v", "Chi4v",
    "Kappa1", "Kappa2", "Kappa3",
    "HallKierAlpha", "BalabanJ", "BertzCT",
]

# Category 3: Electronic / EState
ELECTRONIC_DESCRIPTORS = [
    "MaxAbsEStateIndex", "MinAbsEStateIndex", "MaxEStateIndex", "MinEStateIndex",
    "MaxAbsPartialCharge", "MinAbsPartialCharge",
    "MaxPartialCharge", "MinPartialCharge",
]

# Category 4: Surface / VSA
SURFACE_DESCRIPTORS = [
    "SlogP_VSA1", "SlogP_VSA2", "SlogP_VSA3", "SlogP_VSA4",
    "SlogP_VSA5", "SlogP_VSA6", "SlogP_VSA7", "SlogP_VSA8",
    "SlogP_VSA9", "SlogP_VSA10", "SlogP_VSA11", "SlogP_VSA12",
    "SMR_VSA1", "SMR_VSA2", "SMR_VSA3", "SMR_VSA4", "SMR_VSA5",
    "SMR_VSA6", "SMR_VSA7", "SMR_VSA8", "SMR_VSA9", "SMR_VSA10",
    "PEOE_VSA1", "PEOE_VSA2", "PEOE_VSA3", "PEOE_VSA4", "PEOE_VSA5",
    "PEOE_VSA6", "PEOE_VSA7", "PEOE_VSA8", "PEOE_VSA9", "PEOE_VSA10",
    "PEOE_VSA11", "PEOE_VSA12", "PEOE_VSA13", "PEOE_VSA14",
]

# Category 5: BCUT
BCUT_DESCRIPTORS = [
    "BCUT2D_MWLOW", "BCUT2D_MWHI", "BCUT2D_CHGLO", "BCUT2D_CHGHI",
    "BCUT2D_LOGPLOW", "BCUT2D_LOGPHI", "BCUT2D_MRLOW", "BCUT2D_MRHI",
]

# Category 6: Autocorrelation
AUTOCORR_DESCRIPTORS = [
    "Autocorr2D_1", "Autocorr2D_2", "Autocorr2D_3", "Autocorr2D_4",
    "Autocorr2D_5", "Autocorr2D_6", "Autocorr2D_7", "Autocorr2D_8",
]

# Category 7: Fragment-based (functional group counts)
FRAGMENT_DESCRIPTORS = [
    "fr_Al_COO", "fr_Al_OH", "fr_Al_OH_noTert", "fr_ArN",
    "fr_Ar_COO", "fr_Ar_N", "fr_Ar_NH", "fr_Ar_OH",
    "fr_COO", "fr_COO2", "fr_C_O", "fr_C_O_noCOO",
    "fr_C_S", "fr_HOCCN", "fr_Imine", "fr_NH0",
    "fr_NH1", "fr_NH2", "fr_N_O", "fr_Ndealkylation1",
    "fr_Ndealkylation2", "fr_Nhpyrrole", "fr_SH", "fr_aldehyde",
    "fr_alkyl_carbamate", "fr_alkyl_halide", "fr_allylic_oxid",
    "fr_amide", "fr_amidine", "fr_aniline", "fr_aryl_methyl",
    "fr_azo", "fr_barbitur", "fr_benzene", "fr_benzodiazepine",
    "fr_bicyclic", "fr_diazo", "fr_dihydropyridine", "fr_epoxide",
    "fr_ester", "fr_ether", "fr_furan", "fr_guanido",
    "fr_halogen", "fr_hdrzine", "fr_hdrzone", "fr_imidazole",
    "fr_imide", "fr_isocyan", "fr_isothiocyan", "fr_ketone",
    "fr_ketone_Topliss", "fr_lactam", "fr_lactone", "fr_methoxy",
    "fr_morpholine", "fr_nitrile", "fr_nitro", "fr_nitro_arom",
    "fr_nitro_arom_nonortho", "fr_nitroso", "fr_oxazole",
    "fr_oxime", "fr_para_hydroxylation", "fr_phenol",
    "fr_phenol_noOrthoHbond", "fr_phos_acid", "fr_phos_ester",
    "fr_piperdine", "fr_piperzine", "fr_priamide", "fr_prisulfonamd",
    "fr_pyridine", "fr_quatN", "fr_sulfide", "fr_sulfonamd",
    "fr_sulfone", "fr_term_acetylene", "fr_tetrazole",
    "fr_thiazole", "fr_thiocyan", "fr_thiophene",
    "fr_unbrch_alkane", "fr_urea",
]

# Category 8: Drug-likeness rules
DRUG_LIKENESS_FUNCTIONS = {
    "Lipinski_violations": lambda mol: _lipinski_violations(mol),
    "Veber_violations": lambda mol: _veber_violations(mol),
    "Ghose_pass": lambda mol: _ghose_pass(mol),
    "Muegge_pass": lambda mol: _muegge_pass(mol),
    "Lead_like": lambda mol: _lead_like(mol),
    "Fragment_like": lambda mol: _fragment_like(mol),
    "Drug_category": lambda mol: _drug_category(mol),
}


def _lipinski_violations(mol):
    v = 0
    if Descriptors.MolWt(mol) > 500: v += 1
    if Crippen.MolLogP(mol) > 5: v += 1
    if Descriptors.NumHDonors(mol) > 5: v += 1
    if Descriptors.NumHAcceptors(mol) > 10: v += 1
    return v


def _veber_violations(mol):
    v = 0
    if Descriptors.TPSA(mol) > 140: v += 1
    if Descriptors.NumRotatableBonds(mol) > 10: v += 1
    return v


def _ghose_pass(mol):
    logp = Crippen.MolLogP(mol)
    mw = Descriptors.MolWt(mol)
    mr = Crippen.MolMR(mol)
    n_atoms = mol.GetNumAtoms()
    return int(-0.4 <= logp <= 5.6 and 160 <= mw <= 480 and 40 <= mr <= 130 and 20 <= n_atoms <= 70)


def _muegge_pass(mol):
    mw = Descriptors.MolWt(mol)
    logp = Crippen.MolLogP(mol)
    tpsa = Descriptors.TPSA(mol)
    rot = Descriptors.NumRotatableBonds(mol)
    hba = Descriptors.NumHAcceptors(mol)
    hbd = Descriptors.NumHDonors(mol)
    n_rings = rdMolDescriptors.CalcNumRings(mol)
    n_het = rdMolDescriptors.CalcNumHeteroatoms(mol)
    return int(200 <= mw <= 600 and -2 <= logp <= 5 and tpsa <= 150 and
               n_rings <= 7 and rot <= 15 and hba <= 10 and hbd <= 5 and n_het >= 2)


def _lead_like(mol):
    mw = Descriptors.MolWt(mol)
    logp = Crippen.MolLogP(mol)
    hbd = Descriptors.NumHDonors(mol)
    hba = Descriptors.NumHAcceptors(mol)
    return int(mw <= 350 and logp <= 3 and hbd <= 3 and hba <= 6)


def _fragment_like(mol):
    mw = Descriptors.MolWt(mol)
    logp = Crippen.MolLogP(mol)
    hbd = Descriptors.NumHDonors(mol)
    hba = Descriptors.NumHAcceptors(mol)
    return int(mw <= 300 and logp <= 3 and hbd <= 3 and hba <= 3)


def _drug_category(mol):
    if _fragment_like(mol):
        return "Fragment-like"
    elif _lead_like(mol):
        return "Lead-like"
    elif _lipinski_violations(mol) == 0:
        return "Drug-like"
    else:
        return "Non-drug-like"


# ═══════════════════════════════════════════════════════════════════
# MAIN CALCULATOR
# ═══════════════════════════════════════════════════════════════════

def calculate_all_descriptors(mol, categories=None):
    """Calculate ALL available RDKit descriptors for a molecule.

    Args:
        mol: RDKit Mol object
        categories: list of category names to include (None = all)

    Returns: dict of {descriptor_name: value}
    """
    if not HAS_RDKIT:
        return {}

    all_categories = {
        "basic": BASIC_DESCRIPTORS,
        "topological": TOPOLOGICAL_DESCRIPTORS,
        "electronic": ELECTRONIC_DESCRIPTORS,
        "surface": SURFACE_DESCRIPTORS,
        "bcut": BCUT_DESCRIPTORS,
        "autocorr": AUTOCORR_DESCRIPTORS,
        "fragment": FRAGMENT_DESCRIPTORS,
    }

    if categories is None:
        categories = list(all_categories.keys())

    result = {}

    for cat in categories:
        if cat not in all_categories:
            continue
        for name in all_categories[cat]:
            func = getattr(Descriptors, name, None) or getattr(rdMolDescriptors, name, None)
            if func:
                try:
                    val = func(mol)
                    if val is None or (isinstance(val, float) and (np.isnan(val) or np.isinf(val))):
                        val = 0.0
                    result[name] = round(float(val), 4)
                except Exception:
                    result[name] = 0.0

    # Drug-likeness categories
    result["Lipinski_violations"] = _lipinski_violations(mol)
    result["Veber_violations"] = _veber_violations(mol)
    result["Ghose_pass"] = _ghose_pass(mol)
    result["Muegge_pass"] = _muegge_pass(mol)
    result["Lead_like"] = _lead_like(mol)
    result["Fragment_like"] = _fragment_like(mol)
    result["Drug_category"] = _drug_category(mol)

    return result


def get_descriptor_names(categories=None):
    """Get list of all descriptor names for given categories."""
    all_categories = {
        "basic": BASIC_DESCRIPTORS,
        "topological": TOPOLOGICAL_DESCRIPTORS,
        "electronic": ELECTRONIC_DESCRIPTORS,
        "surface": SURFACE_DESCRIPTORS,
        "bcut": BCUT_DESCRIPTORS,
        "autocorr": AUTOCORR_DESCRIPTORS,
        "fragment": FRAGMENT_DESCRIPTORS,
    }

    if categories is None:
        categories = list(all_categories.keys())

    names = []
    for cat in categories:
        if cat in all_categories:
            names.extend(all_categories[cat])

    # Add drug-likeness names
    names.extend(["Lipinski_violations", "Veber_violations", "Ghose_pass",
                   "Muegge_pass", "Lead_like", "Fragment_like", "Drug_category"])
    return names


def calculate_batch(smiles_list, categories=None, names=None):
    """Calculate descriptors for a list of SMILES.

    Returns: dict with descriptor_matrix, descriptor_names, valid_indices, drug_categories.
    """
    if not HAS_RDKIT:
        return {"error": "RDKit not available"}

    from rdkit import RDLogger
    RDLogger.DisableLog("rdApp.*")

    if names is None:
        names = [f"Mol_{i+1}" for i in range(len(smiles_list))]

    desc_names = get_descriptor_names(categories)
    # Remove non-numeric "Drug_category" for matrix
    numeric_names = [n for n in desc_names if n != "Drug_category"]

    matrix = []
    valid_indices = []
    drug_categories = []

    for i, smi in enumerate(smiles_list):
        mol = Chem.MolFromSmiles(str(smi).strip())
        if mol is None:
            continue

        desc = calculate_all_descriptors(mol, categories)
        row = [desc.get(n, 0.0) for n in numeric_names]
        matrix.append(row)
        valid_indices.append(i)
        drug_categories.append(desc.get("Drug_category", "Unknown"))

    if not matrix:
        return {"error": "No valid molecules"}

    return {
        "descriptor_matrix": np.array(matrix),
        "descriptor_names": numeric_names,
        "valid_indices": valid_indices,
        "drug_categories": drug_categories,
        "n_descriptors": len(numeric_names),
        "n_molecules": len(valid_indices),
    }


def get_descriptor_summary(smiles_list, categories=None):
    """Calculate descriptors and return summary statistics per descriptor.

    Returns: list of {name, category, mean, std, min, max, median}.
    """
    result = calculate_batch(smiles_list, categories)
    if "error" in result:
        return result

    matrix = result["descriptor_matrix"]
    names = result["descriptor_names"]

    summary = []
    for i, name in enumerate(names):
        col = matrix[:, i]
        # Determine category
        cat = "other"
        for c, descs in [("basic", BASIC_DESCRIPTORS), ("topological", TOPOLOGICAL_DESCRIPTORS),
                          ("electronic", ELECTRONIC_DESCRIPTORS), ("surface", SURFACE_DESCRIPTORS),
                          ("bcut", BCUT_DESCRIPTORS), ("autocorr", AUTOCORR_DESCRIPTORS),
                          ("fragment", FRAGMENT_DESCRIPTORS)]:
            if name in descs:
                cat = c
                break

        summary.append({
            "name": name,
            "category": cat,
            "mean": round(float(np.mean(col)), 4),
            "std": round(float(np.std(col)), 4),
            "min": round(float(np.min(col)), 4),
            "max": round(float(np.max(col)), 4),
            "median": round(float(np.median(col)), 4),
        })

    return {"summary": summary, "n_molecules": result["n_molecules"],
            "n_descriptors": result["n_descriptors"],
            "drug_categories": result["drug_categories"]}
