## Pharma Citation Verify Tool

**Purpose:** Verify pharmaceutical citations against real databases (PubMed, CrossRef). Detects hallucinated, suspicious, and verified citations. Essential for ensuring research papers cite real, verifiable sources.

**When to use:**
- User has a manuscript with citations that need verification
- User wants to check if DOIs/PMIDs are real and resolvable
- User is preparing a thesis/review and needs citation integrity check
- Before submitting a paper — verify all references are real

**Actions:**
- `pharma_citation_verify` — verify citations against PubMed + CrossRef APIs

**How to use:** Call via `code_execution_tool` or through the Academic Writer "Verify & Score" tab.

```python
import sys; sys.path.insert(0, "/a0")
from api.writing import WritingTools

w = WritingTools.__new__(WritingTools)
result = w._pharma_citation_verify({
    "text": "Manuscript text with DOIs like 10.1038/nature12373 and PMIDs like PMID:12345678",
    # OR provide explicit citations:
    # "citations": [{"doi": "10.1038/nature12373"}, {"pmid": "12345678"}]
})
print(f"Verified: {result['verified']}/{result['total']}")
print(f"Integrity score: {result['integrity_score']}%")
for r in result['results']:
    print(f"  {r['status']}: {r.get('title', r['input'])}")
```

**Pharma focus:** Prioritizes PubMed-indexed citations. PubMed-indexed > Scopus > non-indexed.

**API endpoint:** `POST /api/writing` with `{action: "pharma_citation_verify"}`
