"""PubChem Lookup API — resolves compound name or CID to SMILES."""
from helpers.api import ApiHandler, Request
import logging, json, urllib.request, urllib.parse

log = logging.getLogger("pubchem_lookup")

PUBCHEM_PUG = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"


class PubchemLookup(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        query = (input.get("query") or "").strip()
        if not query:
            return {"success": False, "error": "query required"}

        try:
            encoded = urllib.parse.quote(query)
            url = f"{PUBCHEM_PUG}/compound/name/{encoded}/property/CanonicalSMILES,MolecularFormula,MolecularWeight,IUPACName/JSON"
            req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/6.4"})
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read())

            props = data.get("PropertyTable", {}).get("Properties", [])
            if not props:
                return {"success": False, "error": f"Compound '{query}' not found in PubChem"}

            p = props[0]
            return {
                "success": True,
                "name": p.get("IUPACName") or query,
                "smiles": p.get("CanonicalSMILES", ""),
                "cid": p.get("CID", 0),
                "formula": p.get("MolecularFormula", ""),
                "mw": p.get("MolecularWeight", 0),
            }
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {"success": False, "error": f"Compound '{query}' not found"}
            return {"success": False, "error": f"PubChem API error: {e.code}"}
        except Exception as e:
            log.exception("pubchem_lookup failed")
            return {"success": False, "error": f"PubChem unavailable: {str(e)}"}
