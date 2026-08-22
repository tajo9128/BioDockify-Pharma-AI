## RNA Therapeutics Tool

**Purpose:** RNA biologics design — siRNA candidates (Reynolds 2004 + Tuschl rules + seed-region off-target screening), codon optimization (E. coli / yeast / human / CHO with CAI), RNA secondary structure folding (ViennaRNA when installed, Nussinov fallback — always offline), mRNA design properties, and CRISPR guide design (SpCas9 NGG, Cas12a TTTV) with mismatch off-target screening. Fills the RNA/DNA gap — 20 Boltzmann-class features in one module, all pure-Python algorithms.

**When to use:**
- User wants siRNA against a gene/mRNA sequence → `sirna_design`, then `sirna_offtarget` against other transcripts
- User asks to optimize a protein sequence for expression in E. coli / yeast / human / CHO → `codon_optimize`
- User asks about RNA structure, MFE, hairpins → `fold`
- User is designing an mRNA (vaccine/therapeutic) → `mrna_properties` (GC windows, runs, polyA signal)
- User wants CRISPR guides for a DNA target → `crispr_guides`, then `crispr_offtarget` vs provided sequences
- User mentions gene silencing, knockdown, gRNA, sgRNA, protospacer, PAM

**How to use:** Call via `code_execution_tool`.

```python
import sys; sys.path.insert(0, "/a0")
import asyncio
from api.rna_design import RNADesignHandler

async def main():
    h = RNADesignHandler()
    r = await h.process({"action": "sirna_design", "mrna": "AUGCGAUUCGAUGGC...", "top": 5}, None)
    for c in r["recommended"]:
        print(c["position"], c["antisense_21"], "Reynolds", c["reynolds_score"])

asyncio.run(main())
```

**Actions:**
- `sirna_design` — ranked 21-mer candidates from mRNA (`mrna`, `top`); dTdT overhang constructs; warnings for GC/motifs/immune motifs
- `sirna_offtarget` — seed-aware mismatch screen (`guide`, `transcripts` {name: seq}, `max_mismatches`)
- `codon_optimize` — protein → optimized CDS/mRNA (`protein`, `host` ecoli/yeast/human/cho, `strategy` balanced/best); returns CAI, GC, translation-verified
- `codon_hosts` — available host tables
- `fold` — MFE + dot-bracket structure (≤400 nt)
- `mrna_properties` — GC windows, GC/AU runs, Kozak-like start, polyA signal, segment MFE
- `crispr_guides` — ranked guides (`target_dna`, `nuclease` spcas9/cas12a); scores, penalties, seed
- `crispr_offtarget` — mismatch screen with seed double-weighting (`guide`, `sequences`, `nuclease`)

**Critical rules:**
1. Always screen siRNA/CRISPR candidates for off-targets before recommending; report seed-perfect partial matches as risky.
2. Off-target screens run against USER-PROVIDED sequences — recommend genome/transcriptome-wide screening for real experiments.
3. Scoring is rule-based (not ML like Doench 2016) — say so when precision matters.
4. Codon optimization output is verified by re-translation; CAI > 0.8 is generally good.

**Pipeline context:** Target ID → (gene sequence) → RNA Therapeutics → off-target screen → wet lab / KB notes
