## Pharmaceutical Analysis Tool

**Purpose:** ICH Q2 method validation, dissolution testing, forced degradation planning, chromatographic calculations, and LOD/LOQ determination.

**When to use:**
- User needs method validation per ICH Q2(R2)
- User wants to compare dissolution profiles (f2 similarity)
- User needs forced degradation study conditions
- User asks about chromatographic parameters (resolution, plates, tailing)
- User needs LOD/LOQ calculations

**Actions:**
- `method_validation` — ICH Q2(R2) validation: accuracy, precision, linearity, RSD
- `dissolution_f2` — f2 similarity factor (FDA 1997)
- `forced_degradation` — Acid/base/oxidative/photolytic/thermal conditions
- `chromatography` — Resolution, plate number, tailing factor, capacity factor
- `lod_loq` — LOD/LOQ calculation (S/N and std deviation methods)

**API endpoint:** `POST /api/pharma_analysis`
