"""Protein Preparation API — wraps pdbfixer for PDB cleaning."""
from helpers.api import ApiHandler, Request, Response
import logging, os

log = logging.getLogger("protein_prep")

class ProteinPrep(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        action = input.get("action", "")
        if action == "prepare":    return self._prepare(input)
        if action == "health":     return self._health()
        return {"actions": ["prepare","health"]}

    def _health(self):
        try:
            from modules.protein_prep import prepare_protein
            return {"status": "ok", "pdbfixer": True}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _prepare(self, input: dict):
        try:
            from modules.protein_prep import prepare_protein
            pdb = input.get("pdb", "")
            if not pdb:
                return {"status": "error", "error": "No PDB content provided"}
            out = input.get("output")
            ph = float(input.get("ph", 7.4))
            return prepare_protein(pdb, out, ph=ph)
        except Exception as e:
            return {"status": "error", "error": str(e)}
