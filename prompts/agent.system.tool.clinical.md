## Clinical Pharmacy Tool

**Purpose:** Clinical pharmacy tools for drug interactions, therapeutic drug monitoring, dose adjustment, and adverse drug reaction assessment.

**When to use:**
- User asks about drug-drug interactions
- User needs TDM (therapeutic drug monitoring) calculations
- User needs dose adjustments for renal or hepatic impairment
- User wants to assess ADR causality (Naranjo scale)
- User asks about GFR/CKD staging

**Actions:**
- `drug_interaction` — Check drug-drug interactions (CYP-mediated, pharmacodynamic)
- `tdm` — Therapeutic Drug Monitoring calculator (Bayesian dosing, steady-state)
- `renal_adjust` — Dose adjustment for renal impairment (CKD-EPI 2021)
- `hepatic_adjust` — Dose adjustment for hepatic impairment (Child-Pugh)
- `naranjo` — Naranjo ADR causality assessment (10-question validated tool)
- `ckd_epi` — CKD-EPI 2021 GFR calculator (race-free)

**API endpoint:** `POST /api/clinical`
