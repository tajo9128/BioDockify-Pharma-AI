"""RNA Secondary Structure — ViennaRNA when available, Nussinov fallback.

Nussinov O(n^3) with Watson-Crick + wobble pairs gives a reasonable MFE-like
structure for short sequences (siRNA/mRNA segments). ViennaRNA gives exact MFE.
"""

try:
    import RNA as VIENNA_RNA  # pip install viennarna
    HAS_VIENNA = True
except ImportError:
    VIENNA_RNA = None
    HAS_VIENNA = False

PAIRS = {("A", "U"), ("U", "A"), ("G", "C"), ("C", "G"), ("G", "U"), ("U", "G")}
ENERGY = {("A", "U"): -1.0, ("U", "A"): -1.0, ("G", "C"): -2.0, ("C", "G"): -2.0, ("G", "U"): -0.5, ("U", "G"): -0.5}
MAX_NT = 400


def _nussinov(seq: str) -> dict:
    n = len(seq)
    dp = [[0.0] * n for _ in range(n)]
    for span in range(1, n):
        for i in range(n - span):
            j = i + span
            if j - i < 4:
                continue  # minimum hairpin loop of 3
            best = min(dp[i + 1][j], dp[i][j - 1])
            if (seq[i], seq[j]) in PAIRS:
                best = min(best, dp[i + 1][j - 1] + ENERGY[(seq[i], seq[j])])
                for k in range(i + 1, j):
                    best = min(best, dp[i + 1][k] + dp[k + 1][j])
            dp[i][j] = best
    # traceback
    pairs = []
    stack = [(0, n - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 4:
            continue
        if dp[i][j] == dp[i + 1][j]:
            stack.append((i + 1, j))
        elif dp[i][j] == dp[i][j - 1]:
            stack.append((i, j - 1))
        elif (seq[i], seq[j]) in PAIRS and abs(dp[i][j] - (dp[i + 1][j - 1] + ENERGY[(seq[i], seq[j])])) < 1e-9:
            pairs.append((i, j))
            stack.append((i + 1, j - 1))
        else:
            for k in range(i + 1, j):
                if abs(dp[i][j] - (dp[i + 1][k] + dp[k + 1][j])) < 1e-9:
                    stack.append((i + 1, k))
                    stack.append((k + 1, j))
                    break
    pairs.sort()
    # dot-bracket
    struct = ["."] * n
    for i, j in pairs:
        struct[i] = "("
        struct[j] = ")"
    return {"mfe": round(dp[0][n - 1], 2), "structure": "".join(struct), "pairs": pairs,
            "engine": "nussinov", "num_pairs": len(pairs)}


def fold(sequence: str) -> dict:
    seq = "".join(c for c in sequence.upper() if c in "ACGUT").replace("T", "U")
    if not seq:
        return {"error": "sequence required"}
    if len(seq) > MAX_NT:
        return {"error": f"sequence too long ({len(seq)} nt; max {MAX_NT}) — fold a segment instead"}
    gc = 100.0 * (seq.count("G") + seq.count("C")) / len(seq)
    if HAS_VIENNA:
        try:
            fc = VIENNA_RNA.fold_compound(seq)
            struct, mfe = fc.mfe()
            pairs = []
            stack = []
            for idx, ch in enumerate(struct):
                if ch == "(":
                    stack.append(idx)
                elif ch == ")" and stack:
                    pairs.append((stack.pop(), idx))
            result = {"mfe": round(float(mfe), 2), "structure": struct, "pairs": sorted(pairs),
                      "engine": "viennarna", "num_pairs": len(pairs)}
        except Exception:
            result = _nussinov(seq)
    else:
        result = _nussinov(seq)
    result.update({
        "sequence": seq,
        "length": len(seq),
        "gc_percent": round(gc, 1),
        "paired_fraction": round(2 * result["num_pairs"] / len(seq), 3),
        "viennarna_available": HAS_VIENNA,
    })
    return result


def mrna_properties(cds_or_mrna: str) -> dict:
    """Design-relevant mRNA properties: GC, 5'/3' GC, start context, UTR-free metrics."""
    seq = "".join(c for c in cds_or_mrna.upper() if c in "ACGUT").replace("T", "U")
    if len(seq) < 30:
        return {"error": "sequence too short"}
    f = fold(seq[:min(len(seq), MAX_NT)])
    props = {
        "length_nt": len(seq),
        "gc_percent": round(100.0 * (seq.count("G") + seq.count("C")) / len(seq), 1),
        "gc_5p": round(100.0 * sum(seq[i] in "GC" for i in range(min(30, len(seq)))) / min(30, len(seq)), 1),
        "gc_3p": round(100.0 * sum(seq[i] in "GC" for i in range(max(0, len(seq) - 30), len(seq))) / min(30, len(seq)), 1),
        "kozak_like": seq.startswith("GCCACC" + "AUG") or seq.startswith("AUG"),
        "polya_signal_present": "AAUAAA" in seq,
        "longest_gc_run": _longest_run(seq, "GC"),
        "longest_au_run": _longest_run(seq, "AU"),
    }
    if "error" not in f:
        props["mfe_first_segment"] = f["mfe"]
        props["fold_engine"] = f["engine"]
    props["note"] = "Design screening: GC 40-70% overall, avoid extreme GC runs; " \
                    "mfe shown for first segment only for long sequences."
    return props


def _longest_run(seq: str, chars: str) -> int:
    best = cur = 0
    for c in seq:
        cur = cur + 1 if c in chars else 0
        best = max(best, cur)
    return best
