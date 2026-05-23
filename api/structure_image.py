"""Structure Image API — generates 2D molecular structure PNG from SMILES."""
from helpers.api import ApiHandler, Request, Response
import logging, io, base64

log = logging.getLogger("structure_image")


class StructureImage(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        smiles = input.get("smiles", request.args.get("smiles", ""))
        if not smiles:
            return {"error": "smiles required"}

        try:
            from rdkit import Chem
            from rdkit.Chem import Draw, AllChem

            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return {"error": "Invalid SMILES"}

            AllChem.Compute2DCoords(mol)
            img = Draw.MolToImage(mol, size=(400, 300), kekulize=True)

            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)

            return Response(
                response=buf.getvalue(),
                status=200,
                mimetype="image/png",
            )
        except ImportError:
            return {"error": "RDKit not available"}
        except Exception as e:
            return {"error": str(e)}
