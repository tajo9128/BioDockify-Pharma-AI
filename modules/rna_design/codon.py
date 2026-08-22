"""Codon Optimization — protein → DNA/mRNA with host codon usage bias.

CAI (Codon Adaptation Index, Sharp & Li 1987) against host tables.
Hosts: E. coli K-12, S. cerevisiae, H. sapiens, CHO (hamster).
Pure Python, offline.
"""

# Standard genetic code (DNA codons)
CODON_TABLE = {
    "TTT": "F", "TTC": "F", "TTA": "L", "TTG": "L",
    "CTT": "L", "CTC": "L", "CTA": "L", "CTG": "L",
    "ATT": "I", "ATC": "I", "ATA": "I", "ATG": "M",
    "GTT": "V", "GTC": "V", "GTA": "V", "GTG": "V",
    "TCT": "S", "TCC": "S", "TCA": "S", "TCG": "S",
    "CCT": "P", "CCC": "P", "CCA": "P", "CCG": "P",
    "ACT": "T", "ACC": "T", "ACA": "T", "ACG": "T",
    "GCT": "A", "GCC": "A", "GCA": "A", "GCG": "A",
    "TAT": "Y", "TAC": "Y", "TAA": "*", "TAG": "*",
    "CAT": "H", "CAC": "H", "CAA": "Q", "CAG": "Q",
    "AAT": "N", "AAC": "N", "AAA": "K", "AAG": "K",
    "GAT": "D", "GAC": "D", "GAA": "E", "GAG": "E",
    "TGT": "C", "TGC": "C", "TGA": "*", "TGG": "W",
    "CGT": "R", "CGC": "R", "CGA": "R", "CGG": "R",
    "AGT": "S", "AGC": "S", "AGA": "R", "AGG": "R",
    "GGT": "G", "GGC": "G", "GGA": "G", "GGG": "G",
}

AA_TO_CODONS = {}
for _c, _a in CODON_TABLE.items():
    AA_TO_CODONS.setdefault(_a, []).append(_c)

# Relative codon usage (fraction per amino acid; highest = 1.0 preferred set).
# Curated from Kazusa/Nakamura codon usage tables (representative values).
HOST_TABLES = {
    "ecoli": {
        "TTT": 0.46, "TTC": 1.00, "TTA": 0.09, "TTG": 0.14,
        "CTT": 0.11, "CTC": 0.12, "CTA": 0.05, "CTG": 1.00,
        "ATT": 0.49, "ATC": 1.00, "ATA": 0.03, "ATG": 1.00,
        "GTT": 0.74, "GTC": 0.70, "GTA": 0.29, "GTG": 1.00,
        "TCT": 0.70, "TCC": 0.81, "TCA": 0.49, "TCG": 0.12,
        "CCT": 0.55, "CCC": 0.04, "CCA": 0.39, "CCG": 1.00,
        "ACT": 0.51, "ACC": 1.00, "ACA": 0.22, "ACG": 0.13,
        "GCT": 0.87, "GCC": 1.00, "GCA": 0.81, "GCG": 0.37,
        "TAT": 0.59, "TAC": 1.00, "TAA": 1.00, "TAG": 0.03,
        "CAT": 0.57, "CAC": 1.00, "CAA": 0.38, "CAG": 1.00,
        "AAT": 0.90, "AAC": 1.00, "AAA": 1.00, "AAG": 0.34,
        "GAT": 0.94, "GAC": 1.00, "GAA": 1.00, "GAG": 0.35,
        "TGT": 0.56, "TGC": 1.00, "TGA": 0.02, "TGG": 1.00,
        "CGT": 0.94, "CGC": 1.00, "CGA": 0.11, "CGG": 0.09,
        "AGT": 0.21, "AGC": 0.41, "AGA": 0.04, "AGG": 0.05,
        "GGT": 0.94, "GGC": 1.00, "GGA": 0.09, "GGG": 0.08,
    },
    "yeast": {
        "TTT": 0.63, "TTC": 1.00, "TTA": 0.40, "TTG": 0.55,
        "CTT": 0.31, "CTC": 0.14, "CTA": 0.20, "CTG": 1.00,
        "ATT": 0.58, "ATC": 0.60, "ATA": 0.20, "ATG": 1.00,
        "GTT": 1.00, "GTC": 0.46, "GTA": 0.34, "GTG": 0.27,
        "TCT": 1.00, "TCC": 0.33, "TCA": 0.40, "TCG": 0.24,
        "CCT": 0.61, "CCC": 0.14, "CCA": 1.00, "CCG": 0.09,
        "ACT": 0.49, "ACC": 1.00, "ACA": 0.47, "ACG": 0.18,
        "GCT": 1.00, "GCC": 0.43, "GCA": 0.68, "GCG": 0.10,
        "TAT": 0.62, "TAC": 1.00, "TAA": 1.00, "TAG": 0.24,
        "CAT": 0.71, "CAC": 1.00, "CAA": 0.53, "CAG": 0.30,
        "AAT": 0.45, "AAC": 1.00, "AAA": 1.00, "AAG": 0.45,
        "GAT": 1.00, "GAC": 0.55, "GAA": 1.00, "GAG": 0.37,
        "TGT": 0.67, "TGC": 1.00, "TGA": 0.02, "TGG": 1.00,
        "CGT": 0.70, "CGC": 0.28, "CGA": 0.19, "CGG": 0.07,
        "AGT": 0.41, "AGC": 0.55, "AGA": 1.00, "AGG": 0.17,
        "GGT": 1.00, "GGC": 0.31, "GGA": 0.57, "GGG": 0.10,
    },
    "human": {
        "TTT": 0.48, "TTC": 1.00, "TTA": 0.07, "TTG": 0.22,
        "CTT": 0.14, "CTC": 0.21, "CTA": 0.07, "CTG": 1.00,
        "ATT": 0.36, "ATC": 1.00, "ATA": 0.16, "ATG": 1.00,
        "GTT": 0.20, "GTC": 0.26, "GTA": 0.12, "GTG": 1.00,
        "TCT": 0.35, "TCC": 0.39, "TCA": 0.33, "TCG": 0.08,
        "CCT": 0.38, "CCC": 0.37, "CCA": 0.43, "CCG": 1.00,
        "ACT": 0.32, "ACC": 1.00, "ACA": 0.37, "ACG": 0.09,
        "GCT": 0.33, "GCC": 1.00, "GCA": 0.42, "GCG": 0.10,
        "TAT": 0.49, "TAC": 1.00, "TAA": 0.31, "TAG": 0.17,
        "CAT": 0.45, "CAC": 1.00, "CAA": 0.33, "CAG": 1.00,
        "AAT": 0.44, "AAC": 1.00, "AAA": 0.42, "AAG": 1.00,
        "GAT": 0.53, "GAC": 1.00, "GAA": 0.63, "GAG": 1.00,
        "TGT": 0.50, "TGC": 1.00, "TGA": 0.72, "TGG": 1.00,
        "CGT": 0.10, "CGC": 0.40, "CGA": 0.08, "CGG": 0.20,
        "AGT": 0.35, "AGC": 1.00, "AGA": 0.22, "AGG": 0.26,
        "GGT": 0.22, "GGC": 1.00, "GGA": 0.34, "GGG": 0.30,
    },
    "cho": {
        "TTT": 0.48, "TTC": 1.00, "TTA": 0.07, "TTG": 0.23,
        "CTT": 0.14, "CTC": 0.23, "CTA": 0.08, "CTG": 1.00,
        "ATT": 0.34, "ATC": 1.00, "ATA": 0.15, "ATG": 1.00,
        "GTT": 0.22, "GTC": 0.28, "GTA": 0.11, "GTG": 1.00,
        "TCT": 0.35, "TCC": 0.40, "TCA": 0.33, "TCG": 0.08,
        "CCT": 0.40, "CCC": 0.36, "CCA": 0.44, "CCG": 1.00,
        "ACT": 0.34, "ACC": 1.00, "ACA": 0.38, "ACG": 0.09,
        "GCT": 0.35, "GCC": 1.00, "GCA": 0.43, "GCG": 0.10,
        "TAT": 0.48, "TAC": 1.00, "TAA": 0.38, "TAG": 0.18,
        "CAT": 0.46, "CAC": 1.00, "CAA": 0.34, "CAG": 1.00,
        "AAT": 0.44, "AAC": 1.00, "AAA": 0.42, "AAG": 1.00,
        "GAT": 0.54, "GAC": 1.00, "GAA": 0.61, "GAG": 1.00,
        "TGT": 0.51, "TGC": 1.00, "TGA": 0.66, "TGG": 1.00,
        "CGT": 0.10, "CGC": 0.38, "CGA": 0.08, "CGG": 0.21,
        "AGT": 0.36, "AGC": 1.00, "AGA": 0.21, "AGG": 0.26,
        "GGT": 0.23, "GGC": 1.00, "GGA": 0.33, "GGG": 0.29,
    },
}


def _gc(seq: str) -> float:
    return 100.0 * (seq.count("G") + seq.count("C")) / len(seq) if seq else 0.0


def cai(dna: str, host: str = "human") -> float:
    """Codon Adaptation Index (Sharp & Li 1987)."""
    table = HOST_TABLES.get(host)
    if table is None:
        raise ValueError(f"Unknown host '{host}'. Use: {', '.join(HOST_TABLES)}")
    dna = dna.upper().replace("U", "T")
    import math
    weights, rscu_max = [], {}
    for aa, codons in AA_TO_CODONS.items():
        if aa == "*":
            continue
        rscu_max[aa] = max(table[c] for c in codons if c not in ("TAA", "TAG", "TGA"))
    for i in range(0, len(dna) - 2, 3):
        codon = dna[i:i + 3]
        aa = CODON_TABLE.get(codon)
        if aa is None or aa == "*" or codon in ("TAA", "TAG", "TGA"):
            continue
        w = table[codon] / rscu_max[aa]
        weights.append(max(w, 1e-9))
    if not weights:
        return 0.0
    return math.exp(sum(math.log(w) for w in weights) / len(weights))


def translate(dna: str) -> str:
    dna = dna.upper().replace("U", "T")
    return "".join(CODON_TABLE.get(dna[i:i + 3], "X") for i in range(0, len(dna) - 2, 3))


def _avoid_bad_motifs(seq: str) -> str:
    """Remove common problem motifs for mRNA manufacturing: long GC runs,
    internal TTA/TTG? keep light: break GGGGG/CCCCC runs only."""
    out = list(seq)
    for run, repl in (("GGGGG", "GGCGG"), ("CCCCC", "CCGCC")):
        while "".join(out).count(run):
            s = "".join(out)
            idx = s.find(run)
            out = list(s[:idx] + repl + s[idx + len(run):])
    return "".join(out)


def codon_optimize(protein: str, host: str = "human", strategy: str = "balanced",
                   avoid_motifs: bool = True) -> dict:
    """Optimize a protein sequence for a host.

    strategy: 'best' (always top codon) | 'balanced' (weighted-random from top set)
    """
    table = HOST_TABLES.get(host)
    if table is None:
        return {"error": f"Unknown host '{host}'. Use: {', '.join(HOST_TABLES)}"}
    protein = "".join(c for c in protein.upper() if c.isalpha() and c != "*")
    protein = protein.strip()
    invalid = [c for c in protein if c not in AA_TO_CODONS]
    if invalid:
        return {"error": f"Invalid amino acid(s): {', '.join(sorted(set(invalid)))}"}

    import random
    rng = random.Random(42)
    dna = []
    for aa in protein:
        if aa == "M" or AA_TO_CODONS[aa] == ["ATG"]:
            dna.append("ATG")
            continue
        if aa == "W":
            dna.append("TGG")
            continue
        codons = [c for c in AA_TO_CODONS[aa] if c not in ("TAA", "TAG", "TGA")]
        scored = sorted(codons, key=lambda c: -table[c])
        if strategy == "best":
            dna.append(scored[0])
        else:
            top = scored[:3]
            weights = [max(table[c], 0.01) for c in top]
            dna.append(rng.choices(top, weights=weights, k=1)[0])
    cds = "".join(dna)
    if avoid_motifs:
        cds = _avoid_bad_motifs(cds)

    # re-verify translation is intact after motif breaking
    translated = translate(cds).rstrip("*")
    mrna = cds.replace("T", "U")
    return {
        "protein": protein,
        "length_aa": len(protein),
        "host": host,
        "strategy": strategy,
        "cds_dna": cds,
        "mrna": mrna,
        "gc_percent": round(_gc(cds), 1),
        "cai": round(cai(cds, host), 3),
        "translation_ok": translated == protein,
        "codon_count": len(protein),
        "note": "Screening-level optimization. Verify expression experimentally; "
                "CAI > 0.8 typically indicates good adaptation.",
    }
