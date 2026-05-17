from helpers.api import ApiHandler, Request


class MolecularSimilarity(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        query_smiles = input.get("query_smiles", "").strip()
        reference_smiles_raw = input.get("reference_smiles", "").strip()

        if not query_smiles:
            return {"error": "query_smiles required"}

        try:
            from rdkit import Chem, DataStructs
            from rdkit.Chem import AllChem

            query_mol = Chem.MolFromSmiles(query_smiles)
            if query_mol is None:
                return {"error": "Invalid query SMILES"}
            query_fp = AllChem.GetMorganFingerprintAsBitVect(query_mol, 2, 2048)

            # Build reference library
            ref_smiles_list = []
            if reference_smiles_raw:
                ref_smiles_list = [s.strip() for s in reference_smiles_raw.split("\n") if s.strip()]
            else:
                # Fall back to built-in drug library
                ref_smiles_list = [
                    "CC(=O)Oc1ccccc1C(=O)O", "CC(C)Cc1ccc(cc1)C(C)C(=O)O",
                    "CN(C)C(=N)N=C(N)N", "Cn1cnc2c1c(=O)n(c(=O)n2C)C",
                    "CC(=O)OC(Cc1c(O)c2ccccc2oc1=O)C(c1ccccc1)=O",
                    "CCCC1=C2N(C(=O)N1CCC)CCCC2c3ccc(cc3)S(=O)(=O)N",
                    "CC(=O)Nc1ccc(O)cc1", "c1cc2c(cc1)C(=O)NCN2c3ccccc3",
                    "CC(C)NCC(COc1ccc(CCO)cc1)O", "CC(C)c1cccc(C(C)C)c1O",
                    "CN1C(=O)CN=C(c2ccc(Cl)cc2)c3ccccc13",
                    "CC(C)NCC(COc1ccc(CC(N)=O)cc1)O",
                ]

            results = []
            for s in ref_smiles_list:
                mol = Chem.MolFromSmiles(s)
                if mol is None:
                    continue
                fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, 2048)
                sim = DataStructs.TanimotoSimilarity(query_fp, fp)
                results.append({"smiles": s, "similarity": round(sim, 4)})

            results.sort(key=lambda x: x["similarity"], reverse=True)
            top = results[:30]
            max_sim = top[0]["similarity"] if top else 0
            return {
                "matches": top,
                "total": len(results),
                "max_similarity": max_sim,
                "query_smiles": query_smiles,
            }

        except ImportError:
            return {"error": "RDKit not available"}
        except Exception as e:
            return {"error": str(e)}
