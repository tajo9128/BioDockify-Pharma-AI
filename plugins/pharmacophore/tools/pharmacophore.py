"""Pharmacophore Tool — agent detects pharmacophoric features."""
from helpers.tool import Tool, Response


class PharmacophoreTool(Tool):
    async def execute(self, action: str = "generate", **kwargs):
        if action == "generate":
            smiles = kwargs.get("smiles", "")
            if not smiles:
                return Response(message="Please provide a SMILES string.", break_loop=False)

            try:
                from rdkit import Chem
                from rdkit.Chem import AllChem, ChemicalFeatures
                from rdkit import RDConfig
                import os

                mol = Chem.MolFromSmiles(smiles)
                if mol is None:
                    return Response(message=f"Invalid SMILES: {smiles}", break_loop=False)

                mol = Chem.AddHs(mol)
                AllChem.EmbedMolecule(mol, AllChem.ETKDG())
                AllChem.MMFFOptimizeMolecule(mol)

                fdef_path = os.path.join(RDConfig.RDDataDir, "BaseFeatures.fdef")
                if not os.path.exists(fdef_path):
                    fdef_path = os.path.join(RDConfig.RDDataDir, "MinimalFeatureDef.fdef")

                if not os.path.exists(fdef_path):
                    return Response(message="Pharmacophore feature definitions not found.", break_loop=False)

                factory = ChemicalFeatures.BuildFeatureFactory(fdef_path)
                features = factory.GetFeaturesForMol(mol)

                if not features:
                    return Response(message=f"No pharmacophore features detected for {smiles}", break_loop=False)

                families = {}
                lines = [f"Pharmacophore Features: {smiles}", "-" * 45]
                for feat in features:
                    family = feat.GetFamily()
                    families[family] = families.get(family, 0) + 1

                for fam, count in sorted(families.items()):
                    lines.append(f"  {fam}: {count}")
                lines.append(f"  Total: {len(features)} features")

                return Response(message="\n".join(lines), break_loop=False)

            except ImportError:
                return Response(message="RDKit not available for pharmacophore detection.", break_loop=False)
            except Exception as e:
                return Response(message=f"Pharmacophore generation failed: {str(e)}", break_loop=False)

        if action == "screen":
            query_smiles = kwargs.get("query_smiles", "")
            library = kwargs.get("library", "")
            if not query_smiles or not library:
                return Response(message="Provide query_smiles and library (comma-separated SMILES).", break_loop=False)
            library_list = [s.strip() for s in library.split(",") if s.strip()]
            return Response(message=f"Pharm screen: query={query_smiles}, library={len(library_list)} molecules. Use the API for full screening.", break_loop=False)

        return Response(message="Pharmacophore actions: generate, screen. Use: Pharmacophore action=generate smiles=SMILES", break_loop=False)
