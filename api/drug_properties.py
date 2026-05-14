from helpers.api import ApiHandler, Request
from helpers import files
import json

DRUG_LIBRARY = {
    "aspirin": {"smiles": "CC(=O)Oc1ccccc1C(=O)O", "name": "Aspirin"},
    "caffeine": {"smiles": "Cn1cnc2c1c(=O)n(c(=O)n2C)C", "name": "Caffeine"},
    "ibuprofen": {"smiles": "CC(C)Cc1ccc(cc1)C(C)C(=O)O", "name": "Ibuprofen"},
    "metformin": {"smiles": "CN(C)C(=N)N=C(N)N", "name": "Metformin"},
    "morphine": {"smiles": "CN1CCc2c(O)ccc(c2C1)C(O)=O", "name": "Morphine"},
    "warfarin": {"smiles": "CC(=O)OC(Cc1c(O)c2ccccc2oc1=O)C(c1ccccc1)=O", "name": "Warfarin"},
    "sildenafil": {"smiles": "CCCC1=C2N(C(=O)N1CCC)CCCC2c3ccc(cc3)S(=O)(=O)N", "name": "Sildenafil"},
    "glucose": {"smiles": "OC[C@H]1OC(O)[C@H](O)[C@@H](O)[C@@H]1O", "name": "Glucose"},
}


class DrugProperties(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        smiles = input.get("smiles", "").strip()
        preset = input.get("preset", "").strip()

        if preset and preset in DRUG_LIBRARY:
            smiles = DRUG_LIBRARY[preset]["smiles"]

        if not smiles:
            return {"error": "No SMILES provided", "library": list(DRUG_LIBRARY.keys())}

        try:
            from rdkit import Chem
            from rdkit.Chem import Descriptors, Lipinski, Crippen

            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return {"error": "Invalid SMILES string"}

            mw = Descriptors.MolWt(mol)
            logp = Crippen.MolLogP(mol)
            hbd = Lipinski.RingCount(mol)  # fallback
            hbd = Descriptors.NumHDonors(mol)
            hba = Descriptors.NumHAcceptors(mol)
            tpsa = Descriptors.TPSA(mol)
            rotatable = Descriptors.NumRotatableBonds(mol)
            heavy_atoms = mol.GetNumHeavyAtoms()

            lipinski_passes = sum([
                mw <= 500,
                logp <= 5,
                hbd <= 5,
                hba <= 10
            ])

            properties = {
                "mw": round(mw, 2),
                "logp": round(logp, 2),
                "hbd": hbd,
                "hba": hba,
                "tpsa": round(tpsa, 2),
                "rotatable_bonds": rotatable,
                "heavy_atoms": heavy_atoms,
                "formula": Chem.rdMolDescriptors.CalcMolFormula(mol),
                "lipinski_passes": lipinski_passes,
                "lipinski_rule_of_5": lipinski_passes >= 4,
                "smiles": smiles,
            }
            return properties
        except ImportError:
            return {"error": "RDKit not available"}
        except Exception as e:
            return {"error": str(e)}
