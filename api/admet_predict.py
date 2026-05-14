from helpers.api import ApiHandler, Request

PRESET_LIBRARY = {
    "aspirin": "CC(=O)Oc1ccccc1C(=O)O",
    "ibuprofen": "CC(C)Cc1ccc(cc1)C(C)C(=O)O",
    "metformin": "CN(C)C(=N)N=C(N)N",
    "caffeine": "Cn1cnc2c1c(=O)n(c(=O)n2C)C",
    "warfarin": "CC(=O)OC(Cc1c(O)c2ccccc2oc1=O)C(c1ccccc1)=O",
    "sildenafil": "CCCC1=C2N(C(=O)N1CCC)CCCC2c3ccc(cc3)S(=O)(=O)N",
}


class AdmetPredict(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        smiles = input.get("smiles", "").strip()
        preset = input.get("preset", "").strip()

        if preset and preset in PRESET_LIBRARY:
            smiles = PRESET_LIBRARY[preset]
        if not smiles:
            return {"error": "No SMILES provided"}

        try:
            from rdkit import Chem
            from rdkit.Chem import Descriptors, Crippen, Lipinski, QED
            from rdkit.Chem import rdMolDescriptors

            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return {"error": "Invalid SMILES"}

            mw = Descriptors.MolWt(mol)
            logp = Crippen.MolLogP(mol)
            hbd = Descriptors.NumHDonors(mol)
            hba = Descriptors.NumHAcceptors(mol)
            tpsa = Descriptors.TPSA(mol)
            rot = Descriptors.NumRotatableBonds(mol)
            formula = rdMolDescriptors.CalcMolFormula(mol)

            n_o_count = sum(1 for atom in mol.GetAtoms() if atom.GetAtomicNum() in (7, 8))
            bbb_score = logp - n_o_count

            result = {
                "smiles": smiles,
                "formula": formula,
                "mw": round(mw, 2),
                "logp": round(logp, 2),
                "hbd": hbd,
                "hba": hba,
                "tpsa": round(tpsa, 2),
                "rotatable_bonds": rot,
                "lipinski_rule_of_5": mw <= 500 and logp <= 5 and hbd <= 5 and hba <= 10,
                "veber_rule": tpsa <= 140 and rot <= 10,
                "golden_triangle": 200 <= mw <= 500 and 2 <= logp <= 5,
                "gi_absorption": "High" if tpsa < 120 else ("Medium" if tpsa < 140 else "Low"),
                "bbb_score": round(bbb_score, 2),
                "bbb_pass": bbb_score <= 0,
                "herg_risk": "Medium" if logp > 3.3 and hbd > 0 else "Low",
                "bioavailability_score": "0.55",
                "synthetic_accessibility": "N/A",
                "qed": round(QED.qed(mol), 3) if hasattr(QED, 'qed') else "N/A",
            }
            return result
        except ImportError:
            return {"error": "RDKit not available"}
        except Exception as e:
            return {"error": str(e)}
