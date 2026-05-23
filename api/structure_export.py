"""Structure Export API — exports molecule in PNG/SVG/MOL/SDF formats."""
from helpers.api import ApiHandler, Request, Response
import logging, io

log = logging.getLogger("structure_export")


class StructureExport(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        smiles = (input.get("smiles") or "").strip()
        fmt = (input.get("format") or "png").strip().lower()
        if not smiles:
            return {"error": "smiles required"}
        if fmt not in ("png", "svg", "mol", "sdf"):
            return {"error": f"Unsupported format: {fmt}. Use png, svg, mol, or sdf"}

        try:
            from rdkit import Chem
            from rdkit.Chem import Draw, AllChem

            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return {"error": "Invalid SMILES"}

            mol_name = smiles[:20].replace("/", "_").replace("\\", "_")

            if fmt == "png":
                AllChem.Compute2DCoords(mol)
                img = Draw.MolToImage(mol, size=(600, 400), kekulize=True)
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                buf.seek(0)
                return Response(
                    response=buf.getvalue(), status=200, mimetype="image/png",
                    headers={"Content-Disposition": f"attachment; filename={mol_name}.png"},
                )

            elif fmt == "svg":
                AllChem.Compute2DCoords(mol)
                svg = Draw.MolToSVG(mol, size=(600, 400))
                return Response(
                    response=svg.encode(), status=200, mimetype="image/svg+xml",
                    headers={"Content-Disposition": f"attachment; filename={mol_name}.svg"},
                )

            elif fmt == "mol":
                mol_block = Chem.MolToMolBlock(mol)
                return Response(
                    response=mol_block.encode(), status=200, mimetype="chemical/x-mdl-molfile",
                    headers={"Content-Disposition": f"attachment; filename={mol_name}.mol"},
                )

            elif fmt == "sdf":
                mol = Chem.AddHs(mol)
                AllChem.EmbedMolecule(mol, AllChem.ETKDG())
                AllChem.MMFFOptimizeMolecule(mol)
                sdf_block = Chem.MolToMolBlock(mol)
                return Response(
                    response=sdf_block.encode(), status=200, mimetype="chemical/x-mdl-sdfile",
                    headers={"Content-Disposition": f"attachment; filename={mol_name}.sdf"},
                )

        except ImportError:
            return {"error": "RDKit not available"}
        except Exception as e:
            log.exception("structure_export failed")
            return {"error": str(e)}
