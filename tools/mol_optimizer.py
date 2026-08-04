"""Molecular Optimizer Tool — agent applies mutation strategies to molecules."""
from helpers.tool import Tool, Response


class MolOptimizerTool(Tool):
    async def execute(self, action: str = "mutate", **kwargs):
        if action == "mutate":
            smiles = kwargs.get("smiles", "")
            strategy = kwargs.get("strategy", "")
            if not smiles:
                return Response(message="Provide a SMILES string and strategy.", break_loop=False)

            strategies = {
                "bioisostere": "Replace carboxyl with tetrazole bioisostere",
                "hydroxyl": "Add hydroxyl to aromatic ring",
                "fluorine": "Add fluorine to aromatic ring",
                "methyl": "Add methyl to aromatic ring",
            }

            if strategy not in strategies:
                avail = ", ".join(strategies.keys())
                return Response(message=f"Available strategies: {avail}\nSource SMILES: {smiles}", break_loop=False)

            try:
                from rdkit import Chem
                mol = Chem.MolFromSmiles(smiles)
                if mol is None:
                    return Response(message="Invalid SMILES.", break_loop=False)

                new_smi = smiles
                if strategy == "bioisostere":
                    new_smi = smiles.replace("C(=O)O", "c1[nH]nnn1")
                elif strategy == "hydroxyl":
                    new_smi = smiles.replace("cc", "c(O)c")
                    if new_smi == smiles:
                        new_smi = smiles.replace("ccc", "cc(O)c")
                elif strategy == "fluorine":
                    new_smi = smiles.replace("cc", "c(F)c")
                    if new_smi == smiles:
                        new_smi = smiles.replace("ccc", "cc(F)c")
                elif strategy == "methyl":
                    new_smi = smiles.replace("cc", "c(C)c")
                    if new_smi == smiles:
                        new_smi = smiles.replace("ccc", "cc(C)c")

                new_mol = Chem.MolFromSmiles(new_smi)
                if new_mol and new_smi != smiles:
                    return Response(message=f"Mutant ({strategy}):\n  Source: {smiles}\n  Result: {new_smi}", break_loop=False)
                return Response(message=f"Mutation '{strategy}' produced no valid molecule from {smiles}", break_loop=False)
            except ImportError:
                return Response(message="RDKit not available.", break_loop=False)

        return Response(message="MolOptimizer actions: mutate. Use: MolOptimizer action=mutate smiles=SMILES strategy=NAME", break_loop=False)
