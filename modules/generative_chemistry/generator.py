"""Molecule Generator — fragment-based (BRICS), genetic algorithm, scaffold enumeration.

Pure RDKit — no ML training required. Generates novel drug-like molecules from:
1. BRICS: decompose known actives → recombine fragments in new ways
2. Genetic Algorithm: seed molecules → mutate SMILES → score → evolve
3. Scaffold Enumeration: keep core scaffold → attach different R-groups
"""
import logging
import random
from typing import Dict, List, Optional, Tuple

from rdkit import Chem, RDLogger
from rdkit.Chem import BRICS, Descriptors, rdMolDescriptors, Lipinski
from rdkit.Chem.Scaffolds import MurckoScaffold

RDLogger.DisableLog("rdApp.*")
log = logging.getLogger("generative_chemistry.generator")

# Common R-groups for scaffold enumeration (medicinally relevant)
R_GROUPS = [
    "C", "CC", "CCC", "C(C)C", "C(C)(C)C",
    "O", "OC", "OCC", "OCCC", "N", "NC", "NCC",
    "F", "Cl", "Br", "I",
    "C(F)(F)F", "C#N", "C(=O)O", "C(=O)N", "C(=O)NC",
    "c1ccccc1", "c1ccncc1", "c1ccnc c1", "c1cccnc1",
    "C1CCCCC1", "C1CCOCC1", "C1CCNCC1",
    "CO", "COC", "COCC", "C(N)=O", "CS(=O)(=O)C",
    "N[C@@H](C)C(=O)O", "N[C@H](Cc1ccccc1)C(=O)O",
]

# Common bioisosteric replacements (from medicinal chemistry)
BIOISOSTERES = {
    "C(=O)O": ["C(=O)N", "S(=O)(=O)N", "c1nn[nH]n1", "C(=O)C(=O)N"],
    "c1ccccc1": ["c1ccncc1", "c1cccnc1", "c1cc(cc1)C", "C1CCCCC1"],
    "C(=O)N": ["S(=O)(=O)N", "c1nn[nH]n1", "NC(=O)C"],
    "N": ["NC", "N(C)C", "S", "O"],
    "O": ["S", "NH", "N(C)C"],
    "C": ["CC", "C(C)C", "CF"],
    "Cl": ["F", "Br", "C(F)(F)F", "CN"],
    "F": ["Cl", "Br", "C(F)(F)F", "OC(F)(F)F"],
}

# Mutation operations for genetic algorithm
MUTATION_SMARTS = [
    # Add a methyl
    ("[cH]", "[cC]"),
    ("[CH3]", "[CH2]C"),
    # Add fluorine
    ("[cH]", "[cF]"),
    ("[CH2]", "[CH](F)"),
    # Add hydroxyl
    ("[cH]", "[cO]"),
    ("[CH2]", "[CH](O)"),
    # Add amine
    ("[cH]", "[cN]"),
    # Ring substitution
    ("CC", "C(C)C"),
    ("CO", "COC"),
]


def sanitize_smiles(smiles: str) -> Optional[str]:
    """Sanitize and canonicalize a SMILES string. Returns None if invalid."""
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        Chem.SanitizeMol(mol)
        return Chem.MolToSmiles(mol)
    except Exception:
        return None


def get_property_constraints(mol) -> Dict:
    """Get molecular properties for constraint checking."""
    return {
        "mw": Descriptors.MolWt(mol),
        "logp": Descriptors.MolLogP(mol),
        "tpsa": Descriptors.TPSA(mol),
        "hbd": Lipinski.NumHDonors(mol),
        "hba": Lipinski.NumHAcceptors(mol),
        "rotb": Lipinski.NumRotatableBonds(mol),
        "n_rings": rdMolDescriptors.CalcNumRings(mol),
        "n_atoms": mol.GetNumAtoms(),
        "n_heavy": mol.GetNumHeavyAtoms(),
    }


def passes_constraints(mol, constraints: Dict) -> bool:
    """Check if a molecule passes user-defined property constraints."""
    if mol is None:
        return False
    props = get_property_constraints(mol)

    for key, value in constraints.items():
        if key not in props:
            continue
        if isinstance(value, dict):
            lo = value.get("min", 0)
            hi = value.get("max", float("inf"))
            if not (lo <= props[key] <= hi):
                return False
        elif isinstance(value, (int, float)):
            if abs(props[key] - value) > value * 0.2:  # 20% tolerance
                return False
    return True


# ═══════════════════════════════════════════════════════════════
# METHOD 1: BRICS Fragment-Based Generation
# ═══════════════════════════════════════════════════════════════

def brics_generate(seed_smiles: List[str], n_candidates: int = 50,
                   constraints: Optional[Dict] = None) -> List[Dict]:
    """Generate novel molecules by BRICS decomposition and recombination.

    Args:
        seed_smiles: List of known active molecules (SMILES)
        n_candidates: Number of candidate molecules to generate
        constraints: Property constraints (e.g., {"mw": {"min": 300, "max": 500}})

    Returns:
        List of dicts with SMILES, source_fragments, and properties
    """
    if constraints is None:
        constraints = {}

    # Decompose all seeds into fragments
    all_fragments = set()
    for smi in seed_smiles:
        try:
            mol = Chem.MolFromSmiles(smi)
            if mol is None:
                continue
            frags = BRICS.BRICSDecompose(mol)
            all_fragments.update(frags)
        except Exception as e:
            log.warning(f"BRICS decompose failed for {smi}: {e}")

    if not all_fragments:
        log.warning("No BRICS fragments extracted from seeds")
        return []

    log.info(f"Extracted {len(all_fragments)} fragments from {len(seed_smiles)} seeds")

    # Build new molecules by recombining fragments
    frag_list = list(all_fragments)
    candidates = []
    attempts = 0
    max_attempts = n_candidates * 20  # Don't loop forever

    while len(candidates) < n_candidates and attempts < max_attempts:
        attempts += 1
        try:
            # Pick 2-3 random fragments
            n_frags = random.randint(2, min(3, len(frag_list)))
            selected = random.sample(frag_list, n_frags)

            # Build molecule from fragments
            frag_mols = [Chem.MolFromSmiles(f) for f in selected]
            if any(m is None for m in frag_mols):
                continue

            built = BRICS.BRICSBuild(frag_mols, maxDepth=1)
            built_mols = list(built)

            for mol in built_mols[:5]:  # Take up to 5 per combination
                try:
                    Chem.SanitizeMol(mol)
                    smi = Chem.MolToSmiles(mol)
                    if not smi or len(smi) < 10:
                        continue
                    if not passes_constraints(mol, constraints):
                        continue
                    props = get_property_constraints(mol)
                    candidates.append({
                        "smiles": smi,
                        "method": "brics",
                        "source_fragments": selected[:3],
                        "properties": props,
                        "qed": _safe_qed(mol),
                        "sa_score": _sa_score(mol),
                    })
                    if len(candidates) >= n_candidates:
                        break
                except Exception:
                    continue
        except Exception as e:
            log.debug(f"BRICS build attempt {attempts} failed: {e}")
            continue

    log.info(f"BRICS generated {len(candidates)} candidates from {attempts} attempts")
    return candidates[:n_candidates]


# ═══════════════════════════════════════════════════════════════
# METHOD 2: Genetic Algorithm
# ═══════════════════════════════════════════════════════════════

def genetic_generate(seed_smiles: List[str], n_candidates: int = 50,
                     n_generations: int = 10, population_size: int = 100,
                     constraints: Optional[Dict] = None) -> List[Dict]:
    """Generate optimized molecules via genetic algorithm.

    Evolves a population of molecules toward the target constraints using
    SMILES mutations and selection.

    Args:
        seed_smiles: Starting molecules (SMILES)
        n_candidates: Number of final candidates to return
        n_generations: Number of GA generations
        population_size: Population size per generation
        constraints: Target properties to optimize toward

    Returns:
        List of dicts with SMILES, generation, fitness, and properties
    """
    if constraints is None:
        constraints = {"mw": {"min": 200, "max": 550},
                       "logp": {"min": 0, "max": 5},
                       "hbd": {"min": 0, "max": 5},
                       "hba": {"min": 0, "max": 10}}

    # Initialize population from seeds
    population = []
    for smi in seed_smiles:
        clean = sanitize_smiles(smi)
        if clean:
            population.append(clean)

    # Fill population with mutations of seeds
    while len(population) < population_size:
        parent = random.choice(seed_smiles) if seed_smiles else "CCO"
        mutant = _mutate_smiles(parent)
        clean = sanitize_smiles(mutant)
        if clean and clean not in population:
            population.append(clean)
        if len(population) >= population_size * 2:
            break

    best_candidates = []
    for gen in range(n_generations):
        # Score population
        scored = []
        for smi in population:
            mol = Chem.MolFromSmiles(smi)
            if mol is None:
                continue
            fitness = _fitness(mol, constraints)
            props = get_property_constraints(mol)
            scored.append({
                "smiles": smi,
                "fitness": fitness,
                "generation": gen,
                "properties": props,
                "qed": _safe_qed(mol),
                "sa_score": _sa_score(mol),
                "method": "genetic",
            })

        # Sort by fitness
        scored.sort(key=lambda x: x["fitness"], reverse=True)

        # Track best candidates
        for s in scored[:5]:
            if s["smiles"] not in [b["smiles"] for b in best_candidates]:
                best_candidates.append(dict(s))

        # Selection: keep top 50%
        elite = scored[:max(1, len(scored) // 2)]

        # Create next generation through mutation
        next_gen = [s["smiles"] for s in elite]
        while len(next_gen) < population_size:
            parent = random.choice(elite)["smiles"]
            mutant = _mutate_smiles(parent)
            clean = sanitize_smiles(mutant)
            if clean and clean not in next_gen:
                next_gen.append(clean)

        population = next_gen
        log.debug(f"GA generation {gen}: best fitness = {elite[0]['fitness']:.3f}" if elite else f"GA gen {gen}: empty")

    # Return top candidates
    best_candidates.sort(key=lambda x: x["fitness"], reverse=True)
    return best_candidates[:n_candidates]


def _mutate_smiles(smiles: str) -> str:
    """Apply a random mutation to a SMILES string."""
    mutation_type = random.random()

    if mutation_type < 0.3:
        # SMARTS-based mutation
        smarts_pair = random.choice(MUTATION_SMARTS)
        old, new = smarts_pair
        if old in smiles:
            return smiles.replace(old, new, 1)

    elif mutation_type < 0.5:
        # Add a substituent at a random position
        substituent = random.choice(R_GROUPS[:20])
        pos = random.randint(0, max(0, len(smiles) - 2))
        return smiles[:pos] + substituent + smiles[pos:]

    elif mutation_type < 0.7:
        # Delete a random substring
        if len(smiles) > 10:
            start = random.randint(0, len(smiles) - 5)
            end = min(len(smiles), start + random.randint(1, 3))
            return smiles[:start] + smiles[end:]

    elif mutation_type < 0.85:
        # Bioisosteric replacement
        for old, replacements in BIOISOSTERES.items():
            if old in smiles and random.random() < 0.3:
                new = random.choice(replacements)
                return smiles.replace(old, new, 1)

    # Random character mutation
    if len(smiles) > 5:
        pos = random.randint(0, len(smiles) - 1)
        char = random.choice("CNOSFClBrI#c()[]=@")
        return smiles[:pos] + char + smiles[pos + 1:]

    return smiles


def _fitness(mol, constraints: Dict) -> float:
    """Compute multi-objective fitness score for a molecule.

    Higher is better. Combines constraint satisfaction with drug-likeness.
    """
    props = get_property_constraints(mol)
    score = 0.0

    # Constraint satisfaction (50% of score)
    for key, value in constraints.items():
        if key not in props:
            continue
        if isinstance(value, dict):
            lo, hi = value.get("min", 0), value.get("max", float("inf"))
            if lo <= props[key] <= hi:
                score += 1.0
            else:
                # Penalty proportional to distance outside range
                dist = min(abs(props[key] - lo), abs(props[key] - hi))
                score += max(0, 1.0 - dist / (hi - lo + 1))

    # Drug-likeness bonuses (30%)
    qed = _safe_qed(mol)
    score += qed * 3.0

    # Lipinski compliance (20%)
    lipinski_pass = all([
        props["mw"] <= 500, props["logp"] <= 5,
        props["hbd"] <= 5, props["hba"] <= 10,
    ])
    if lipinski_pass:
        score += 2.0

    # Diversity bonus (reward less common structures)
    n_rings = props.get("n_rings", 0)
    if 1 <= n_rings <= 4:
        score += 0.5

    return score


# ═══════════════════════════════════════════════════════════════
# METHOD 3: Scaffold Enumeration
# ═══════════════════════════════════════════════════════════════

def scaffold_enumerate(scaffold_smiles: str, n_candidates: int = 50,
                       constraints: Optional[Dict] = None) -> List[Dict]:
    """Generate molecules by attaching R-groups to a scaffold.

    Args:
        scaffold_smiles: Core scaffold SMILES (with [*] attachment points)
        n_candidates: Number of molecules to generate
        constraints: Property constraints

    Returns:
        List of dicts with SMILES, scaffold, r_groups, and properties
    """
    if constraints is None:
        constraints = {}

    scaffold = Chem.MolFromSmiles(scaffold_smiles)
    if scaffold is None:
        log.error(f"Invalid scaffold SMILES: {scaffold_smiles}")
        return []

    # Find attachment points (dummy atoms [*])
    attachment_points = [atom.GetIdx() for atom in scaffold.GetAtoms()
                         if atom.GetAtomicNum() == 0]
    if not attachment_points:
        # If no explicit attachment points, add one at a random position
        log.warning("No attachment points found — using ring positions")
        attachment_points = [atom.GetIdx() for atom in scaffold.GetAtoms()
                             if atom.GetIsAromatic()]

    candidates = []
    used_smiles = set()

    for r_group in R_GROUPS:
        if len(candidates) >= n_candidates:
            break

        for ap in attachment_points[:3]:  # Max 3 positions per R-group
            try:
                # Build RWMol and replace dummy with R-group
                rw = Chem.RWMol(scaffold)
                # Create the R-group molecule
                rg = Chem.MolFromSmiles(r_group)
                if rg is None:
                    continue
                # Combine scaffold + R-group
                combo = Chem.CombineMols(Chem.MolFromSmiles(
                    Chem.MolToSmiles(scaffold).replace("[*]", f"[{r_group}]")), rg)
                # This is a simplified approach — in practice, use reactions
                smi = Chem.MolToSmiles(scaffold).replace("[*]", f"({r_group})")
                clean = sanitize_smiles(smi)
                if clean and clean not in used_smiles:
                    mol = Chem.MolFromSmiles(clean)
                    if mol and passes_constraints(mol, constraints):
                        used_smiles.add(clean)
                        candidates.append({
                            "smiles": clean,
                            "method": "scaffold",
                            "scaffold": scaffold_smiles,
                            "r_group": r_group,
                            "position": ap,
                            "properties": get_property_constraints(mol),
                            "qed": _safe_qed(mol),
                            "sa_score": _sa_score(mol),
                        })
                        if len(candidates) >= n_candidates:
                            break
            except Exception as e:
                log.debug(f"Scaffold enumeration failed for {r_group}: {e}")
                continue

    return candidates[:n_candidates]


# ═══════════════════════════════════════════════════════════════
# Helper functions
# ═══════════════════════════════════════════════════════════════

def _safe_qed(mol) -> float:
    """Compute QED score safely (returns 0 on failure)."""
    try:
        from rdkit.Chem.QED import qed
        return round(qed(mol), 4)
    except Exception:
        return 0.0


def _sa_score(mol) -> float:
    """Estimate Synthetic Accessibility score (1=easy, 10=very hard).

    Uses a simplified approach based on ring complexity and
    fragment frequency (inspired by Ertl's SAscore).
    """
    try:
        props = get_property_constraints(mol)
        n_rings = props["n_rings"]
        n_rotb = props["rotb"]
        mw = props["mw"]
        n_heavy = props["n_heavy"]

        # Simple heuristic
        score = 1.0
        score += min(n_rings * 0.5, 3.0)  # More rings = harder
        score += min(n_rotb * 0.1, 1.5)   # More rotatable = slightly harder
        if mw > 500:
            score += 1.0
        if n_heavy > 40:
            score += 0.5
        # Macrocycles are hard
        ri = mol.GetRingInfo()
        for ring in ri.AtomRings():
            if len(ring) > 6:
                score += 1.0
                break

        return round(min(score, 10.0), 2)
    except Exception:
        return 5.0


def generate_molecules(method: str, seed_smiles: List[str],
                       n_candidates: int = 50,
                       constraints: Optional[Dict] = None,
                       scaffold: Optional[str] = None) -> List[Dict]:
    """Main entry point — generate molecules using the specified method.

    Args:
        method: "brics" | "genetic" | "scaffold"
        seed_smiles: Starting molecules (SMILES)
        n_candidates: Number of candidates to generate
        constraints: Property constraints
        scaffold: Scaffold SMILES (for scaffold method)

    Returns:
        List of candidate molecule dicts
    """
    if method == "brics":
        return brics_generate(seed_smiles, n_candidates, constraints)
    elif method == "genetic":
        return genetic_generate(seed_smiles, n_candidates, constraints=constraints)
    elif method == "scaffold":
        if not scaffold:
            # Extract scaffold from first seed
            if seed_smiles:
                mol = Chem.MolFromSmiles(seed_smiles[0])
                if mol:
                    scaffold = MurckoScaffold.MurckoScaffoldSmiles(mol=mol)
            if not scaffold:
                scaffold = "c1ccccc1[*]"
        return scaffold_enumerate(scaffold, n_candidates, constraints)
    else:
        log.error(f"Unknown method: {method}")
        return []
