"""SwissADME API endpoint — Flask-discovered at /api/admet_swiss_endpoint."""
from helpers.api import ApiHandler, Request

PRESET_LIBRARY = {
    "aspirin": "CC(=O)Oc1ccccc1C(=O)O",
    "ibuprofen": "CC(C)Cc1ccc(cc1)C(C)C(=O)O",
    "caffeine": "Cn1cnc2c1c(=O)n(c(=O)n2C)C",
    "warfarin": "CC(=O)OC(Cc1c(O)c2ccccc2oc1=O)C(c1ccccc1)=O",
    "sildenafil": "CCCC1=C2N(C(=O)N1CCC)CCCC2c3ccc(cc3)S(=O)(=O)N",
    "paracetamol": "CC(=O)Nc1ccc(O)cc1",
    "diazepam": "CN1C(=O)CN=C(c2ccccc2)c3cc(Cl)ccc13",
    "omeprazole": "COc1ccc2nc([S@](=O)Cc3ncc(C)c(OC)c3C)[nH]c2c1",
    "metformin": "CN(C)C(=N)N=C(N)N",
    "morphine": "CN1CC[C@]23c4c5ccc(O)c4O[C@H]2[C@@H](O)C=C[C@H]3[C@H]1C5",
}


class SwissAdmeHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        smiles = input.get("smiles", "").strip()
        preset = input.get("preset", "").strip()

        if preset and preset in PRESET_LIBRARY:
            smiles = PRESET_LIBRARY[preset]
        if not smiles:
            return {"error": "No SMILES provided", "presets": list(PRESET_LIBRARY.keys())}

        try:
            from api.admet_swiss import compute_swiss_adme
            return compute_swiss_adme(smiles)
        except ImportError:
            return {"error": "RDKit not available"}
        except Exception as e:
            return {"error": str(e)}
