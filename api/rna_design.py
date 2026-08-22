"""RNA Therapeutics API — siRNA design, codon optimization, RNA folding, CRISPR guides."""
from helpers.api import ApiHandler, Request, Response
import logging

log = logging.getLogger("api.rna_design")


class RNADesignHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        action = input.get("action", "")

        if action == "sirna_design":
            return self._sirna(input)
        elif action == "sirna_offtarget":
            return self._sirna_ot(input)
        elif action == "codon_optimize":
            return self._codon(input)
        elif action == "codon_hosts":
            from modules.rna_design.codon import HOST_TABLES
            return {"hosts": list(HOST_TABLES)}
        elif action == "fold":
            return self._fold(input)
        elif action == "mrna_properties":
            return self._mrna_props(input)
        elif action == "crispr_guides":
            return self._crispr(input)
        elif action == "crispr_offtarget":
            return self._crispr_ot(input)
        else:
            return {
                "actions": ["sirna_design", "sirna_offtarget", "codon_optimize", "codon_hosts",
                            "fold", "mrna_properties", "crispr_guides", "crispr_offtarget"],
                "hint": "RNA Therapeutics: siRNA rules, codon optimization, RNA folding, CRISPR guide design",
            }

    def _sirna(self, input: dict) -> dict:
        mrna = input.get("mrna", input.get("sequence", ""))
        if not mrna:
            return {"error": "mrna required (target sequence)"}
        from modules.rna_design import design_sirna
        return design_sirna(mrna, top=int(input.get("top", 10)))

    def _sirna_ot(self, input: dict) -> dict:
        guide = input.get("guide", input.get("guide_19", ""))
        transcripts = input.get("transcripts", {})  # {name: sequence}
        if not guide:
            return {"error": "guide required (19-mer antisense)"}
        if not transcripts:
            return {"error": "transcripts required ({name: sequence} dict) for off-target screening"}
        from modules.rna_design import sirna_offtarget
        return sirna_offtarget(guide, transcripts, int(input.get("max_mismatches", 3)))

    def _codon(self, input: dict) -> dict:
        protein = input.get("protein", "")
        if not protein:
            return {"error": "protein sequence required (single-letter amino acids)"}
        from modules.rna_design import codon_optimize
        return codon_optimize(
            protein,
            host=input.get("host", "human"),
            strategy=input.get("strategy", "balanced"),
            avoid_motifs=bool(input.get("avoid_motifs", True)),
        )

    def _fold(self, input: dict) -> dict:
        seq = input.get("sequence", "")
        if not seq:
            return {"error": "sequence required"}
        from modules.rna_design import fold
        return fold(seq)

    def _mrna_props(self, input: dict) -> dict:
        seq = input.get("sequence", input.get("mrna", ""))
        if not seq:
            return {"error": "sequence required"}
        from modules.rna_design import mrna_properties
        return mrna_properties(seq)

    def _crispr(self, input: dict) -> dict:
        dna = input.get("target_dna", input.get("sequence", ""))
        if not dna:
            return {"error": "target_dna required"}
        from modules.rna_design import design_guides
        return design_guides(dna, nuclease=input.get("nuclease", "spcas9"),
                             top=int(input.get("top", 10)))

    def _crispr_ot(self, input: dict) -> dict:
        guide = input.get("guide", "")
        sequences = input.get("sequences", {})
        if not guide:
            return {"error": "guide required (20-mer protospacer DNA)"}
        if not sequences:
            return {"error": "sequences required ({name: sequence} dict)"}
        from modules.rna_design import crispr_offtarget
        return crispr_offtarget(guide, sequences,
                                nuclease=input.get("nuclease", "spcas9"),
                                max_mismatches=int(input.get("max_mismatches", 4)))
