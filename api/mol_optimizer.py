"""Molecular Optimizer API — AI-driven mutation strategies for lead optimization."""
from helpers.api import ApiHandler, Request, Response
import logging

log = logging.getLogger("mol_optimizer_api")

MUTATION_STRATEGIES = {
    "bioisostere_carboxyl_tetrazole": {"desc": "Replace carboxyl group with tetrazole bioisostere", "pattern": "C(=O)O", "replace": "c1[nH]nnn1"},
    "bioisostere_ester_amide": {"desc": "Replace ester with amide bond", "pattern": "C(=O)OC", "replace": "C(=O)NC"},
    "add_hydroxyl": {"desc": "Add hydroxyl group to aromatic ring (meta)", "fragment": "O", "position": "aromatic"},
    "add_fluorine": {"desc": "Add fluorine to aromatic ring", "fragment": "F", "position": "aromatic"},
    "add_methyl": {"desc": "Add methyl group to scaffold", "fragment": "C", "position": "aromatic"},
    "ring_expansion_5to6": {"desc": "Expand 5-membered ring to 6-membered", "from_size": 5, "to_size": 6},
    "reduce_flexibility_cyclize": {"desc": "Cyclize flexible linker to reduce rotatable bonds", "strategy": "cyclize"},
}


def _apply_bioisostere(smiles: str, pattern: str, replacement: str):
    from rdkit import Chem
    from rdkit.Chem import AllChem
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    pat = Chem.MolFromSmarts(pattern)
    if pat is None:
        return None
    matches = mol.GetSubstructMatches(pat)
    if not matches:
        return None
    repl = Chem.MolFromSmiles(replacement)
    if repl is None:
        return None

    try:
        result = Chem.ReplaceSubstructs(mol, Chem.Mol(pat), Chem.Mol(repl))
        return Chem.MolToSmiles(result[0]) if result else None
    except Exception:
        return None


def _add_fragment(smiles: str, fragment: str):
    from rdkit import Chem
    from rdkit.Chem import AllChem
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return []
    mol = Chem.AddHs(mol)
    AllChem.EmbedMolecule(mol, AllChem.ETKDG())

    results = []
    aromatic_atoms = [a.GetIdx() for a in mol.GetAtoms() if a.GetIsAromatic() and a.GetSymbol() == "C" and a.GetTotalNumHs() >= 1]
    for aidx in aromatic_atoms[:3]:
        try:
            rw = Chem.RWMol(Chem.Mol(mol))
            rw.ReplaceAtom(aidx, Chem.Atom(7))  # replace with N temporarily to attach
            results.append(Chem.MolToSmiles(rw.GetMol()))
        except Exception:
            continue
    return results


class MolOptimizerHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "mutate")

        if action == "strategies":
            return {"strategies": [{"id": k, **v} for k, v in MUTATION_STRATEGIES.items()]}

        if action == "mutate":
            smiles = input.get("smiles", "")
            strategy = input.get("strategy", "")
            if not smiles or not strategy:
                return {"success": False, "error": "smiles and strategy required"}

            try:
                from rdkit import Chem
                from rdkit.Chem import Descriptors

                mol = Chem.MolFromSmiles(smiles)
                if mol is None:
                    return {"success": False, "error": "Invalid SMILES"}

                mutants = []
                si = MUTATION_STRATEGIES.get(strategy, {})
                if not si:
                    return {"success": False, "error": f"Unknown strategy: {strategy}"}

                if strategy.startswith("bioisostere"):
                    new_smi = _apply_bioisostere(smiles, si["pattern"], si["replace"])
                    if new_smi:
                        mutants.append(new_smi)
                elif strategy == "add_hydroxyl":
                    new_smi = smiles.replace("cc", "c(O)c")
                    if new_smi == smiles:
                        new_smi = smiles.replace("ccc", "cc(O)c")
                    if new_smi != smiles:
                        mutants.append(new_smi)
                elif strategy == "add_fluorine":
                    new_smi = smiles.replace("cc", "c(F)c")
                    if new_smi == smiles:
                        new_smi = smiles.replace("ccc", "cc(F)c")
                    if new_smi != smiles:
                        mutants.append(new_smi)
                elif strategy == "add_methyl":
                    new_smi = smiles.replace("cc", "c(C)c")
                    if new_smi == smiles:
                        new_smi = smiles.replace("ccc", "cc(C)c")
                    if new_smi != smiles:
                        mutants.append(new_smi)
                elif strategy == "reduce_flexibility_cyclize":
                    log.info("reduce_flexibility_cyclize: not yet implemented")
                    return {"success": True, "mutants": [], "note": "Cyclization strategy not yet implemented"}

                result_mutants = []
                for smi in mutants:
                    m = Chem.MolFromSmiles(smi)
                    if m is None:
                        continue
                    result_mutants.append({
                        "smiles": smi,
                        "mw": round(Descriptors.MolWt(m), 2),
                        "logp": round(Descriptors.MolLogP(m), 2),
                        "hbd": Descriptors.NumHDonors(m),
                        "hba": Descriptors.NumHAcceptors(m),
                        "rot": Descriptors.NumRotatableBonds(m),
                    })

                return {"success": True, "source_smiles": smiles, "strategy": strategy, "mutants": result_mutants}
            except ImportError:
                return {"success": False, "error": "RDKit not available"}
            except Exception as e:
                return {"success": False, "error": str(e)}

        if action == "flexible_residues":
            receptor_pdb = input.get("receptor_pdb", "")
            ligand_smiles = input.get("ligand_smiles", "")
            cutoff = float(input.get("cutoff", 6.0))

            if not receptor_pdb:
                return {"success": False, "error": "receptor_pdb required"}

            FLEXIBLE = {"ARG","LYS","GLU","ASP","PHE","TYR","TRP","HIS","MET","LEU","ILE","VAL","SER","THR"}

            flexible = []
            seen = set()
            for line in receptor_pdb.split("\n"):
                if line.startswith("ATOM") or line.startswith("HETATM"):
                    try:
                        resname = line[17:20].strip()
                        resseq = int(line[22:26])
                        chain = line[21:22].strip() or "A"
                        if resname in FLEXIBLE:
                            key = (resname, resseq, chain)
                            if key not in seen:
                                seen.add(key)
                                flexible.append({"resname": resname, "resseq": resseq, "chain": chain})
                    except (ValueError, IndexError):
                        continue

            return {"success": True, "flexible_residues": flexible, "count": len(flexible)}

        return {"error": f"Unknown action: {action}"}
