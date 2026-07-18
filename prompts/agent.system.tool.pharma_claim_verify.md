## Pharma Claim Verification Tool

**Purpose:** 3-layer defense against hallucinated pharmaceutical claims. Extracts drug claims from text, maps to evidence, and audits methodology rigor. Essential for verifying that pharmaceutical research papers don't contain unsupported claims.

**When to use:**
- User has a manuscript and wants to verify drug efficacy/safety claims
- User is reviewing a paper and needs to check claim validity
- Before submission — verify all pharmaceutical claims are supported
- User wants to identify high-risk claims that need stronger evidence

**Actions:**
- `extract_claims` — extract pharma claims (efficacy, safety, PK/PD, mechanism, comparative, dosing)
- `audit_rigor` — check methodology rigor (randomization, blinding, power, safety, registration)
- `full_verify` — both extraction + rigor audit combined

**How to use:**

```python
import sys; sys.path.insert(0, "/a0")
from api.claim_verify import ClaimVerifyHandler

h = ClaimVerifyHandler.__new__(ClaimVerifyHandler)

# Extract claims only
claims = h._extract_claims({"text": "Aspirin reduced cardiovascular events by 25%..."})
print(f"Found {claims['total_claims']} claims")
for c in claims['claims'][:5]:
    print(f"  [{c['risk_level']}] {c['type']}: {c['text'][:80]}")

# Full verification
result = h._full_verify({
    "text": "Full manuscript text...",
    "study_type": "clinical_trial"
})
print(f"Assessment: {result['overall_assessment']}")
print(f"Rigor score: {result['rigor']['rigor_score']}/100")
```

**Claim Types Extracted:**
- Efficacy claims (drug X reduces Y by Z%)
- Safety claims (well tolerated, lower AE rate)
- PK/PD claims (half-life, bioavailability, Cmax, EC50/IC50)
- Mechanism claims (inhibits, blocks, binds to)
- Comparative claims (superior to, non-inferiority)
- Dosing claims (recommended dose, mg/kg)

**Risk Levels:** critical (safety) > high (efficacy, comparative, dosing) > medium (PK/PD, mechanism)

**API endpoint:** `POST /api/claim_verify` with `{action: "extract_claims"|"audit_rigor"|"full_verify"}`
