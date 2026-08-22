"""CRISPR Guide Design — SpCas9 (NGG PAM) and Cas12a (TTTV PAM) guides.

On-target scoring is rule-based (GC, homopolymers, position penalties).
Off-target screening = mismatch-count search against user-provided sequences
with seed-region weighting (PAM-proximal ~10 nt). Pure Python, offline.
"""

from .sirna import reverse_complement

PAMS = {
    "spcas9": {"pam": "NGG", "pam_after": True, "guide_len": 20, "name": "SpCas9"},
    "cas12a": {"pam": "TTTV", "pam_after": False, "guide_len": 23, "name": "Cas12a (As/Cpf1)"},
}


def _gc(seq: str) -> float:
    return 100.0 * (seq.count("G") + seq.count("C")) / len(seq) if seq else 0.0


def _iupac_match(pattern: str, seq: str) -> bool:
    table = {"N": "ACGT", "V": "ACG", "R": "AG", "Y": "CT", "W": "AT", "S": "CG", "K": "GT", "M": "AC"}
    for p, s in zip(pattern, seq):
        if s.upper() not in table.get(p.upper(), p.upper()):
            return False
    return True


def guide_score(guide: str, nuclease: str) -> tuple:
    """Rule-based on-target score (0-100) with penalties."""
    penalties = []
    score = 100.0
    gc = _gc(guide)
    if gc < 35 or gc > 75:
        score -= 25
        penalties.append(f"GC {gc:.0f}% out of 35-75%")
    elif gc < 40 or gc > 68:
        score -= 10
        penalties.append(f"GC {gc:.0f}% suboptimal")
    for hp in ("AAAA", "TTTT", "GGGG", "CCCC"):
        if hp in guide:
            score -= 30
            penalties.append(f"homopolymer {hp}")
    if nuclease == "spcas9":
        if guide and guide[-1] == "T":
            score -= 10
            penalties.append("3' terminal T (SpCas9 disfavors)")
        if guide[:2] == "TT":
            score -= 15
            penalties.append("5' TT (U6 transcription penalty)")
    return max(0, round(score)), penalties


def design_guides(target_dna: str, nuclease: str = "spcas9", top: int = 10) -> dict:
    cfg = PAMS.get(nuclease)
    if cfg is None:
        return {"error": f"Unknown nuclease '{nuclease}'. Use: {', '.join(PAMS)}"}
    seq = "".join(c for c in target_dna.upper() if c in "ACGTN")
    if len(seq) < 40:
        return {"error": "target DNA too short (min 40 bp)"}

    pam, glen = cfg["pam"], cfg["guide_len"]
    guides = []
    strands = [("+", seq), ("-", reverse_complement(seq).replace("U", "T"))]
    for strand, s in strands:
        for i in range(len(s) - (len(pam) + glen) + 1):
            if cfg["pam_after"]:
                pam_site = s[i + glen: i + glen + len(pam)]
                proto = s[i: i + glen]
            else:
                pam_site = s[i: i + len(pam)]
                proto = s[i + len(pam): i + len(pam) + glen]
            if len(pam_site) < len(pam) or len(proto) < glen:
                continue
            if not _iupac_match(pam, pam_site):
                continue
            score, penalties = guide_score(proto, nuclease)
            # seed = PAM-proximal region
            seed = proto[-10:] if cfg["pam_after"] else proto[:10]
            guides.append({
                "strand": strand,
                "position": i + 1,  # position on the (sense for +, revcomp for -) sequence
                "guide_rna": proto,           # DNA protospacer (RNA = replace T with U)
                "guide_sgrna": proto.replace("T", "U"),
                "pam": pam_site,
                "seed_10": seed,
                "gc_percent": round(_gc(proto), 1),
                "on_target_score": score,
                "penalties": penalties,
            })
    guides.sort(key=lambda g: -g["on_target_score"])
    return {
        "nuclease": cfg["name"],
        "target_length": len(seq),
        "total_guides": len(guides),
        "recommended": [g for g in guides if g["on_target_score"] >= 70][:top] or guides[:top],
        "note": "Rule-based scoring. For publication-grade on-target scores use external ML "
                "(Doench 2016); off-targets should be screened vs the full genome.",
    }


def offtarget_screen(guide_dna: str, sequences: dict, nuclease: str = "spcas9",
                     max_mismatches: int = 4) -> dict:
    """Mismatch screen of a guide (+PAM-agnostic) against provided sequences."""
    guide = guide_dna.upper()
    hits = []
    for name, seq in sequences.items():
        seq = "".join(c for c in seq.upper() if c in "ACGTN")
        for strand_label, s in [("+", seq), ("-", reverse_complement(seq).replace("U", "T"))]:
            for i in range(len(s) - len(guide) + 1):
                window = s[i:i + len(guide)]
                mm = sum(1 for a, b in zip(guide, window) if a != b)
                if mm > max_mismatches:
                    continue
                seed_mm = sum(1 for a, b in zip(guide[-10:], window[-10:]) if a != b)
                # seed mismatches weigh heaviest (PAM-proximal)
                eff_mm = mm + (2 * seed_mm if nuclease == "spcas9" else seed_mm)
                hits.append({
                    "sequence": name, "strand": strand_label, "position": i + 1,
                    "mismatches": mm, "seed_mismatches": seed_mm,
                    "risk_weight": eff_mm, "aligned": window,
                })
    hits.sort(key=lambda h: h["risk_weight"])
    return {
        "guide": guide,
        "num_offtargets": len(hits),
        "high_risk": [h for h in hits if h["risk_weight"] <= 2][:10],
        "off_targets": hits[:20],
        "note": "Seed (PAM-proximal 10 nt) mismatches double-weighted. Screen against "
                "full transcriptome/genome for real experiments.",
    }
