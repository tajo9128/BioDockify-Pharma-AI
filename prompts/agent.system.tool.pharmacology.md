## Pharmacology Tool

**Purpose:** Receptor pharmacology tools — saturation binding analysis, dose-response curves (EC50/IC50), Schild antagonist analysis, Black-Leff operational model, selectivity ratios, receptor database, and in-vivo study design. Fills the pharmacology department gap (PK is in pkpd, ADMET is in admet_predict, this module covers receptor theory and efficacy).

**When to use:**
- User asks for receptor binding affinity (Kd, Bmax), receptor occupancy, or Scatchard/Hill analysis
- User has dose-response data and needs EC50, IC50, Hill slope, or 4PL curve fit
- User is studying competitive antagonists and needs pA2, KB, or Schild slope
- User wants to separate drug efficacy from affinity (operational model: τ, KA)
- User asks about drug selectivity across multiple targets
- User needs reference info on receptors, transporters, kinases, or ion channels
- User is designing an in-vivo efficacy study (animal model + group sizing + dosing)

**Actions:**
- `receptor_binding` — radioligand saturation → Kd, Bmax, Scatchard, Hill plot, occupancy table
- `dose_response` — 4PL fit with direction (agonist=EC50 / inhibitor=IC50), Hill slope, 95% CI, EC90/95
- `schild_analysis` — competitive antagonist potency → pA2, KB, Schild slope (≈1 = competitive)
- `operational_model` — Black-Leff model → τ (efficacy), KA (affinity), receptor reserve
- `selectivity_ratio` — Kd/IC50 ratios across targets, therapeutic window, ≥30× rule
- `receptor_database` — 25+ curated targets (GPCRs, RTKs, ion channels, transporters, enzymes)


**Enzyme Kinetics (v7.30.0, ported from biodockify-web):**
- `enzyme_kinetics` — Michaelis-Menten nonlinear fit: Vmax, Km, R², LB cross-check, optional kcat → catalytic efficiency. Input: substrate[], velocity[].
- `inhibition` — two modes: `competitive` (velocity matrix [I][S] → Lineweaver-Burk slopes vs [I] → Ki, shared Vmax, Km at I=0) or `ic50` (4PL → IC50, Hill; Ki via Cheng-Prusoff when km + [S] given). Input: inhibitor[], velocities (flat or matrix), substrate[], km.
- Use kinetics when the user has enzyme velocity data, asks for Vmax/Km/Ki/IC50 of an ENZYME (dose_response is for receptor/ligand assays).
- Report nonlinear-fit R² as primary; LB is a cross-check only.- `in_vivo_design` — animal model selection + power analysis (Lehr) + dosing for 5 endpoints

**API endpoint:** `POST /api/pharmacology`
