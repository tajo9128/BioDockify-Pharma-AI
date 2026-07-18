## Pharma Reporting Guidelines Tool

**Purpose:** Check pharmaceutical study compliance with ICH/FDA/EMA reporting guidelines. Validates manuscripts against CONSORT (RCTs), STROBE (observational), PRISMA (systematic reviews), ARRIVE (animal studies), and FDA/EMA bioequivalence guidelines. Essential for regulatory submissions.

**When to use:**
- User has a clinical trial report that needs CONSORT compliance check
- User is writing an observational study and needs STROBE compliance
- User is doing a systematic review and needs PRISMA checklist
- User has animal study data and needs ARRIVE compliance
- User is preparing a bioequivalence study for FDA/EMA submission
- Before any regulatory submission — verify guideline compliance

**Actions:**
- `pharma_reporting_check` — check manuscript against pharma reporting guidelines

**How to use:**

```python
import sys; sys.path.insert(0, "/a0")
from api.writing import WritingTools

w = WritingTools.__new__(WritingTools)
result = w._pharma_reporting_check({
    "study_type": "clinical_trial",  # clinical_trial|observational|systematic_review|animal_study|bioequivalence
    "sections": [
        {"section_name": "title", "content": "A Randomized, Double-Blind, Placebo-Controlled Trial..."},
        {"section_name": "methods", "content": "Patients were randomized 1:1 to receive..."},
        {"section_name": "results", "content": "The primary endpoint was met with..."},
    ]
})
print(f"Guideline: {result['guideline']}")
print(f"Compliance: {result['compliance_score']}%")
print(f"Missing items: {result['missing']}")
```

**Supported study types:**
- `clinical_trial` — CONSORT 2021 (25 items)
- `observational` — STROBE (21 items)
- `systematic_review` — PRISMA 2020 (24 items)
- `animal_study` — ARRIVE 2.0 (12 items)
- `bioequivalence` — FDA/EMA BE Guidelines (10 items)

**API endpoint:** `POST /api/writing` with `{action: "pharma_reporting_check"}`
