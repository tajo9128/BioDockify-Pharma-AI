"""siRNA Design — Reynolds 2004 rules + Tuschl guidelines + off-target screening.

All pure Python, fully offline. Scores 21-mer candidates from a target mRNA,
filters by GC content, sequence motifs, and immunostimulatory flags, and can
screen candidates against user-provided off-target transcripts.
"""

# Immunostimulatory / problematic motifs (simplified screening set)
IMMUNE_MOTIFS = ["GUCCUUCAA", "UGUGC", "GUUCGU", "GUGUC"]  # TLR7/8-ish GU-rich motifs
SEED_LEN = 7          # positions 2-8 of the guide (seed region)
DEFAULT_GC_MIN, DEFAULT_GC_MAX = 31.0, 52.0


def _gc_percent(seq: str) -> float:
    seq = seq.upper()
    if not seq:
        return 0.0
    return 100.0 * (seq.count("G") + seq.count("C")) / len(seq)


def reverse_complement(seq: str) -> str:
    table = str.maketrans("ACGUacgu", "UGCAugca")
    return seq.translate(table)[::-1]


def reynolds_score(antisense19: str) -> tuple:
    """Reynolds et al. 2004 (Nat Biotechnol 22:326) — 8 criteria on the 19-mer
    antisense (guide) strand, positions 1-19. Returns (score, criteria list)."""
    s = antisense19.upper().replace("T", "U")
    criteria = []

    def pos(i):  # 1-based position
        return s[i - 1]

    # +1: GC at position 19 (3' end of antisense; less RISC cleavage bias)
    criteria.append(("GC at pos 19 (3' end)", 1 if pos(19) in "GC" else 0))
    # +1: GC at position 3
    criteria.append(("GC at pos 3", 1 if pos(3) in "GC" else 0))
    # +1: AT at position 13 (RISC cleavage site)
    criteria.append(("A/U at pos 13", 1 if pos(13) in "AU" else 0))
    # +1: at least 3 A/U in positions 13-19 (3' A/U richness)
    au3 = sum(1 for i in range(13, 20) if pos(i) in "AU")
    criteria.append((f"A/U count 13-19 = {au3} (>=3)", 1 if au3 >= 3 else 0))
    # -1: any GC stretch of length >= 9 in positions 1-19
    has_long_gc = any(
        all(s[i] in "GC" for i in range(k, k + 9))
        for k in range(len(s) - 8)
    )
    criteria.append(("no GC stretch >= 9", 0 if has_long_gc else 1))
    # -1: GC stretch >= 7 starting at position 1
    n7 = 0
    while n7 < len(s) and s[n7] in "GC":
        n7 += 1
    criteria.append(("no 5' GC run >= 7", 0 if n7 >= 7 else 1))
    # +1: total GC 30-52% approximated as sum G+C in 19-mer between 5 and 10
    gc = s.count("G") + s.count("C")
    criteria.append((f"GC count 5-10 ({gc})", 1 if 5 <= gc <= 10 else 0))
    # +1: T (U) at position 19 absent — inverted as 3' end not U
    criteria.append(("3' end not U", 1 if pos(19) != "U" else 0))

    score = sum(pts for _, pts in criteria)
    return score, criteria


def tuschl_flags(antisense19: str) -> list:
    """Tuschl lab UI guidelines — negative filters (returns violation list)."""
    s = antisense19.upper().replace("T", "U")
    flags = []
    gc = _gc_percent(s)
    if gc < DEFAULT_GC_MIN:
        flags.append(f"GC {gc:.0f}% < {DEFAULT_GC_MIN:.0f}%")
    if gc > DEFAULT_GC_MAX:
        flags.append(f"GC {gc:.0f}% > {DEFAULT_GC_MAX:.0f}%")
    for m in ("AAAA", "GGGG", "CCCC", "UUUU"):
        if m in s:
            flags.append(f"repeated {m[0]}x4 run")
    for m in IMMUNE_MOTIFS:
        if m in s:
            flags.append(f"immunostimulatory motif {m}")
    if s[:2] == "GU":
        flags.append("5' GU (potential TLR7 agonist)")
    return flags


def design_sirna(mrna: str, top: int = 10) -> dict:
    """Enumerate 21-mer siRNA candidates (19-mer duplex core + 2-nt 3' overhang)."""
    mrna = "".join(c for c in mrna.upper() if c in "ACGUT").replace("T", "U")
    mrna = mrna.replace("U", "T")  # normalize to DNA chars for slicing, back later
    if len(mrna) < 40:
        return {"error": "mRNA sequence too short (min 40 nt)"}
    mrna = mrna.replace("T", "U")

    candidates = []
    for i in range(0, len(mrna) - 20):
        target21 = mrna[i:i + 21]            # sense (target) 21-mer
        antisense19 = reverse_complement(target21[0:19])  # guide core
        sense19 = target21[0:19]
        score, criteria = reynolds_score(antisense19)
        flags = tuschl_flags(antisense19)
        gc = _gc_percent(antisense19)
        # seed = positions 2-8 of guide (for off-target lookup)
        seed = antisense19[1:8]
        candidates.append({
            "position": i + 1,
            "sense_21": f"{sense19}TT",       # classic dTdT overhang construct
            "antisense_21": f"{antisense19}TT",
            "guide_19": antisense19,
            "seed_7": seed,
            "gc_percent": round(gc, 1),
            "reynolds_score": score,
            "reynolds_detail": criteria,
            "warnings": flags,
            "passes": score >= 6 and not flags,
        })

    candidates.sort(key=lambda c: (-c["reynolds_score"], len(c["warnings"]), c["position"]))
    passing = [c for c in candidates if c["passes"]]
    return {
        "mrna_length": len(mrna),
        "total_candidates": len(candidates),
        "passing": len(passing),
        "recommended": (passing or candidates)[:top],
        "note": "Reynolds 2004 + Tuschl guidelines; scores >= 6 without warnings are recommended. "
                "21-mer with dTdT overhangs shown as sense_21/antisense_21.",
    }


def offtarget_screen(guide_19: str, transcripts: dict, max_mismatches: int = 3) -> dict:
    """Seed-region aware mismatch screen vs provided transcripts {name: sequence}."""
    guide = guide_19.upper().replace("T", "U")
    seed = guide[1:8]
    hits = []
    for name, seq in transcripts.items():
        seq = seq.upper().replace("T", "U")
        rc = reverse_complement(seq)  # screen the sense transcript for the guide's target
        for i in range(0, max(0, len(rc) - len(guide) + 1)):
            window = rc[i:i + len(guide)]
            mm = sum(1 for a, b in zip(guide, window) if a != b)
            if mm > max_mismatches:
                continue
            seed_mm = sum(1 for a, b in zip(guide[1:8], window[1:8]) if a != b)
            hits.append({
                "transcript": name,
                "position": i + 1,
                "mismatches": mm,
                "seed_mismatches": seed_mm,
                "seed_perfect": seed_mm == 0 and mm > 0,
                "aligned": window,
            })
    hits.sort(key=lambda h: (h["mismatches"], -h["seed_mismatches"]))
    perfect = [h for h in hits if h["mismatches"] == 0]
    return {
        "guide": guide,
        "seed": seed,
        "off_targets": hits[:20],
        "num_offtargets": len(hits),
        "num_perfect_matches": len(perfect),
        "has_perfect_offtarget": len(perfect) > 0,
        "note": "Screening is mismatch-count based; seed (pos 2-8) perfect matches with overall "
                "mismatches are the most risky off-targets.",
    }
