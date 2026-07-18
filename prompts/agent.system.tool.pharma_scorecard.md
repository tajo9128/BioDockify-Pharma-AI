## Pharma Manuscript Scorecard Tool

**Purpose:** Score pharmaceutical manuscripts across 8 pharma-specific dimensions. Returns per-dimension scores (1-5), overall quality level, and actionable improvement suggestions. Essential for pre-submission quality assessment.

**When to use:**
- User has finished writing a thesis chapter, paper, or review and wants quality feedback
- Before submitting to a journal — check if manuscript meets pharma quality standards
- User wants to know which sections need improvement
- After revisions — verify quality has improved

**Actions:**
- `pharma_scorecard` — score manuscript across 8 pharma dimensions

**How to use:**

```python
import sys; sys.path.insert(0, "/a0")
from api.writing import WritingTools

w = WritingTools.__new__(WritingTools)
result = w._pharma_scorecard({
    "content": "Full manuscript text here...",
    "doc_type": "paper",  # clinical_study_report|thesis|paper|systematic_review|regulatory_submission
    "title": "Efficacy of Drug X in Treating Disease Y"
})
print(f"Overall: {result['overall_score']}/5 ({result['quality_level']})")
for dim, data in result['dimensions'].items():
    print(f"  {dim}: {data['score']}/5 — {', '.join(data['notes'][:2])}")
```

**8 Pharma-Specific Dimensions:**
1. **Study Design Rigor** (20%) — randomization, blinding, power analysis, endpoints
2. **Statistical Analysis** (15%) — CI reporting, effect sizes, appropriate tests
3. **Safety Reporting** (15%) — AEs, SAEs, dose-limiting toxicity
4. **Efficacy Evidence** (15%) — primary/secondary endpoints, clinical significance
5. **PK/PD Integration** (10%) — dose-response, exposure-response, therapeutic window
6. **Regulatory Compliance** (10%) — ICH alignment, GLP/GCP markers
7. **Citation Quality** (10%) — PubMed-indexed, recent, DOI-verified
8. **Writing Clarity** (5%) — structured, precise, appropriate length

**Quality Levels:** Exceptional (4.5+) → Strong (4.0+) → Good (3.5+) → Acceptable (3.0+) → Weak (2.0+) → Poor (<2.0)

**API endpoint:** `POST /api/writing` with `{action: "pharma_scorecard"}`
