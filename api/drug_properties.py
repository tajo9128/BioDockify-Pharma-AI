from helpers.api import ApiHandler, Request
import re

DRUG_LIBRARY = {
    "aspirin": {"smiles": "CC(=O)Oc1ccccc1C(=O)O", "name": "Aspirin"},
    "caffeine": {"smiles": "Cn1cnc2c1c(=O)n(c(=O)n2C)C", "name": "Caffeine"},
    "ibuprofen": {"smiles": "CC(C)Cc1ccc(cc1)C(C)C(=O)O", "name": "Ibuprofen"},
    "metformin": {"smiles": "CN(C)C(=N)N=C(N)N", "name": "Metformin"},
    "morphine": {"smiles": "CN1CCc2c(O)ccc(c2C1)C(O)=O", "name": "Morphine"},
    "warfarin": {"smiles": "CC(=O)OC(Cc1c(O)c2ccccc2oc1=O)C(c1ccccc1)=O", "name": "Warfarin"},
    "sildenafil": {"smiles": "CCCC1=C2N(C(=O)N1CCC)CCCC2c3ccc(cc3)S(=O)(=O)N", "name": "Sildenafil"},
    "glucose": {"smiles": "OC[C@H]1OC(O)[C@H](O)[C@@H](O)[C@@H]1O", "name": "Glucose"},
    "paracetamol": {"smiles": "CC(=O)Nc1ccc(O)cc1", "name": "Paracetamol"},
    "captopril": {"smiles": "CC(CS)C(=O)N1CCCC1C(=O)O", "name": "Captopril"},
}

ATOMIC_WEIGHTS = {
    "H": 1.008, "C": 12.011, "N": 14.007, "O": 15.999, "F": 18.998,
    "P": 30.974, "S": 32.065, "Cl": 35.453, "Br": 79.904, "I": 126.904,
    "Na": 22.990, "K": 39.098, "Ca": 40.078, "Fe": 55.845, "Zn": 65.380,
}

def _parse_atoms(smiles: str) -> dict:
    atoms = {}
    i = 0
    while i < len(smiles):
        c = smiles[i]
        if c in "()[]{}.-=#:;/,@+\\%0123456789":
            i += 1
            continue
        if i + 1 < len(smiles) and smiles[i+1].islower():
            atom = c + smiles[i+1]
            i += 2
        else:
            atom = c
            i += 1
        atoms[atom] = atoms.get(atom, 0) + 1
    return atoms

def _calc_mw(atoms: dict) -> float:
    return round(sum(ATOMIC_WEIGHTS.get(a, 0) * c for a, c in atoms.items()), 2)

def _calc_logp(atoms: dict) -> float:
    c = atoms.get("C", 0)
    o = atoms.get("O", 0)
    n = atoms.get("N", 0)
    hal = sum(atoms.get(x, 0) for x in ("F", "Cl", "Br", "I"))
    return round(0.3 * c - 0.5 * o - 0.4 * n + 0.5 * hal, 2)

def _calc_lipinski(mw, logp, hbd, hba):
    rules = {
        "MW < 500": mw < 500,
        "LogP < 5": logp < 5,
        "HBD < 5": hbd < 5,
        "HBA < 10": hba < 10,
    }
    violations = sum(1 for v in rules.values() if not v)
    return {"passed": violations <= 1, "violations": violations, "rules": rules}

def _format_properties(smiles, mw, logp, hbd, hba, tpsa, formula="", atoms_raw=None):
    lipinski = _calc_lipinski(mw, logp, hbd, hba)
    atoms = atoms_raw or _parse_atoms(smiles)
    return {
        "smiles": smiles,
        "atoms": {a: c for a, c in sorted(atoms.items())} if atoms else {},
        "properties": {
            "molecular_weight": {"value": mw, "unit": "g/mol", "label": "Molecular Weight"},
            "logp": {"value": logp, "unit": "", "label": "LogP (lipophilicity)"},
            "h_bond_donors": {"value": hbd, "unit": "", "label": "H-Bond Donors"},
            "h_bond_acceptors": {"value": hba, "unit": "", "label": "H-Bond Acceptors"},
            "tpsa": {"value": tpsa, "unit": "Å²", "label": "Topological Polar Surface Area"},
        },
        "formula": formula or "",
        "lipinski": lipinski,
        "drug_likeness": "Pass" if lipinski["passed"] else "Fail",
    }


class DrugProperties(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        smiles = (input.get("smiles", "") or "").strip()
        preset = (input.get("preset", "") or "").strip()

        if preset and preset in DRUG_LIBRARY:
            smiles = DRUG_LIBRARY[preset]["smiles"]

        if not smiles:
            return {
                "error": "",
                "library": {k: v["name"] for k, v in DRUG_LIBRARY.items()},
                "hint": "Enter a SMILES string or select a preset drug",
            }

        # Try RDKit first (precise), fall back to approximate
        try:
            from rdkit import Chem
            from rdkit.Chem import Descriptors, Crippen, rdMolDescriptors

            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return {"error": "Invalid SMILES string"}

            mw = round(Descriptors.MolWt(mol), 2)
            logp = round(Crippen.MolLogP(mol), 2)
            hbd = Descriptors.NumHDonors(mol)
            hba = Descriptors.NumHAcceptors(mol)
            tpsa = round(Descriptors.TPSA(mol), 2)
            formula = rdMolDescriptors.CalcMolFormula(mol) if hasattr(rdMolDescriptors, "CalcMolFormula") else ""

            return _format_properties(smiles, mw, logp, hbd, hba, tpsa, formula)
        except ImportError:
            pass
        except Exception as e:
            import logging; logging.getLogger("drug_properties").warning(f"RDKit failed: {e}")

        # Fallback: approximate from SMILES atoms
        atoms = _parse_atoms(smiles)
        if not atoms:
            return {"error": "Could not parse SMILES string"}

        mw = _calc_mw(atoms)
        logp = _calc_logp(atoms)
        hbd = atoms.get("O", 0) + atoms.get("N", 0)
        hba = atoms.get("O", 0) + atoms.get("N", 0)
        tpsa = round(atoms.get("O", 0) * 20.0 + atoms.get("N", 0) * 15.0, 1)

        return _format_properties(smiles, mw, logp, hbd, hba, tpsa, atoms_raw=atoms)
