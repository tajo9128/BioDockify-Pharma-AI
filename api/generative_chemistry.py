"""Generative Chemistry API — de novo molecule design, optimization, scaffold hopping.

Actions:
  generate       — generate novel molecules (BRICS / genetic / scaffold methods)
  optimize       — optimize a seed molecule toward target properties
  score          — score a single molecule on all objectives
  scaffold_hop   — find alternative scaffolds for a molecule
  scaffolds      — extract scaffolds from seed molecules
  r_groups       — analyze R-groups on a molecule
  fragments      — build fragment library from seeds
  rank_docking   — select top diverse candidates for docking
"""
from helpers.api import ApiHandler, Request
import asyncio
import logging

log = logging.getLogger("generative_chemistry")


def _kb_store(title, content, tags):
    try:
        from modules.knowledge.auto_store import auto_store
        auto_store("generative_chemistry", title, content,
                   source="Generative Chemistry", tags=tags, category="drug_design")
    except Exception:
        pass


class GenerativeChemistryHandler(ApiHandler):

    async def process(self, input: dict, request: Request) -> dict:
        action = input.get("action", "")

        if action == "generate":
            return await self._generate(input)
        elif action == "optimize":
            return await self._optimize(input)
        elif action == "score":
            return self._score(input)
        elif action == "scaffold_hop":
            return self._scaffold_hop(input)
        elif action == "scaffolds":
            return self._scaffolds(input)
        elif action == "r_groups":
            return self._r_groups(input)
        elif action == "fragments":
            return self._fragments(input)
        elif action == "rank_docking":
            return self._rank_docking(input)

        return {
            "actions": ["generate", "optimize", "score", "scaffold_hop",
                        "scaffolds", "r_groups", "fragments", "rank_docking"],
            "hint": "POST with action=generate + smiles[] + method=brics|genetic|scaffold"
        }

    async def _generate(self, input: dict) -> dict:
        """Generate novel molecules from seeds using the specified method."""
        seed_smiles = input.get("smiles", input.get("seeds", []))
        method = input.get("method", "brics")  # brics | genetic | scaffold
        n_candidates = int(input.get("n_candidates", 50))
        constraints = input.get("constraints", {})
        scaffold = input.get("scaffold", "")

        if not seed_smiles and method != "scaffold":
            return {"error": "Provide seed molecules (smiles array) for generation"}

        def _do_generate():
            from modules.generative_chemistry.generator import generate_molecules
            from modules.generative_chemistry.scorer import score_library

            molecules = generate_molecules(
                method=method,
                seed_smiles=seed_smiles,
                n_candidates=n_candidates,
                constraints=constraints,
                scaffold=scaffold,
            )

            if not molecules:
                return {"status": "ok", "molecules": [], "message": "No molecules generated"}

            # Score the library
            scored = score_library(molecules, seed_smiles=seed_smiles)

            return {
                "status": "ok",
                "method": method,
                "total_generated": len(scored),
                "molecules": scored[:100],  # Cap at 100 for response size
                "message": f"Generated {len(scored)} molecules via {method}",
            }

        result = await asyncio.to_thread(_do_generate)

        # Auto-store to KB
        if result.get("molecules"):
            summary = "\n".join(
                f"{i+1}. {m['smiles']} (score: {m['scores']['combined']:.3f})"
                for i, m in enumerate(result["molecules"][:10])
            )
            _kb_store(f"Generated Molecules ({method})",
                      f"## Top 10 Generated Molecules\n\n{summary}",
                      ["generative", method])

        return result

    async def _optimize(self, input: dict) -> dict:
        """Optimize a molecule toward target properties using genetic algorithm."""
        seed_smiles = list(filter(None, [input.get("smiles", input.get("seed", ""))]))
        if not seed_smiles:
            return {"error": "Provide a seed molecule (smiles)"}

        constraints = input.get("constraints", {
            "mw": {"min": 250, "max": 500},
            "logp": {"min": 1, "max": 4},
            "hbd": {"min": 0, "max": 4},
            "hba": {"min": 2, "max": 8},
        })
        n_candidates = int(input.get("n_candidates", 20))
        n_generations = int(input.get("generations", 15))

        def _do_optimize():
            from modules.generative_chemistry.generator import genetic_generate
            from modules.generative_chemistry.scorer import score_library

            molecules = genetic_generate(
                seed_smiles=seed_smiles,
                n_candidates=n_candidates,
                n_generations=n_generations,
                constraints=constraints,
            )
            scored = score_library(molecules, seed_smiles=seed_smiles)
            return {
                "status": "ok",
                "seed": seed_smiles[0],
                "total_optimized": len(scored),
                "molecules": scored[:50],
                "generations": n_generations,
                "message": f"Optimized to {len(scored)} candidates over {n_generations} generations",
            }

        return await asyncio.to_thread(_do_optimize)

    def _score(self, input: dict) -> dict:
        """Score a single molecule."""
        smiles = input.get("smiles", "")
        if not smiles:
            return {"error": "smiles required"}

        from modules.generative_chemistry.scorer import score_molecule
        weights = input.get("weights", None)
        result = score_molecule(smiles, weights)
        return {"status": "ok", "smiles": smiles, "scores": result}

    def _scaffold_hop(self, input: dict) -> dict:
        """Find alternative scaffolds for a molecule."""
        smiles = input.get("smiles", "")
        if not smiles:
            return {"error": "smiles required"}

        from modules.generative_chemistry.scaffolds import scaffold_hop
        hops = scaffold_hop(smiles, n_hops=int(input.get("n_hops", 10)))
        return {
            "status": "ok",
            "smiles": smiles,
            "scaffold_hops": hops,
            "total": len(hops),
        }

    def _scaffolds(self, input: dict) -> dict:
        """Extract Murcko scaffolds from seed molecules."""
        seed_smiles = input.get("smiles", input.get("seeds", []))
        if not seed_smiles:
            return {"error": "Provide seed molecules"}

        from modules.generative_chemistry.scaffolds import extract_scaffolds
        scaffolds = extract_scaffolds(seed_smiles)
        return {
            "status": "ok",
            "scaffolds": scaffolds[:20],
            "total": len(scaffolds),
        }

    def _r_groups(self, input: dict) -> dict:
        """Analyze R-groups on a molecule."""
        smiles = input.get("smiles", "")
        if not smiles:
            return {"error": "smiles required"}

        from modules.generative_chemistry.scaffolds import get_r_groups
        r_groups = get_r_groups(smiles)
        return {
            "status": "ok",
            "smiles": smiles,
            "scaffold": extract_scaffold_safe(smiles),
            "r_groups": r_groups,
            "total": len(r_groups),
        }

    def _fragments(self, input: dict) -> dict:
        """Build fragment library from seeds."""
        seed_smiles = input.get("smiles", input.get("seeds", []))
        if not seed_smiles:
            return {"error": "Provide seed molecules"}

        from modules.generative_chemistry.scaffolds import fragment_library
        fragments = fragment_library(seed_smiles)
        return {
            "status": "ok",
            "fragments": fragments[:50],
            "total": len(fragments),
        }

    def _rank_docking(self, input: dict) -> dict:
        """Select top diverse candidates for docking."""
        molecules = input.get("molecules", [])
        top_n = int(input.get("top_n", 10))
        if not molecules:
            return {"error": "Provide molecules to rank"}

        from modules.generative_chemistry.scorer import rank_for_docking
        selected = rank_for_docking(molecules, top_n=top_n)
        return {
            "status": "ok",
            "selected": selected,
            "total_selected": len(selected),
            "message": f"Selected {len(selected)} diverse candidates for docking",
        }


def extract_scaffold_safe(smiles):
    try:
        from modules.generative_chemistry.scaffolds import extract_scaffold
        return extract_scaffold(smiles)
    except Exception:
        return None
