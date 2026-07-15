## Natural Products / Pharmacognosy Tool

**Purpose:** Pharmacognosy tools for phytochemical screening, extraction efficiency, IC50 calculation, medicinal plant database, dereplication, and selectivity index.

**When to use:**
- User asks about phytochemical screening protocols
- User wants to calculate extraction yield
- User needs IC50/EC50 from dose-response data
- User asks about medicinal plants or natural products
- User wants to dereplicate molecular formulas
- User needs selectivity index calculation

**Actions:**
- `phytochemical_screen` — Standard screening protocols (alkaloids, flavonoids, tannins, saponins, steroids, terpenoids, glycosides)
- `extraction_yield` — Calculate extraction efficiency (Soxhlet, maceration, ultrasound, SFE)
- `ic50` — IC50/EC50 calculator (4-parameter logistic regression)
- `plant_database` — Medicinal plant database with active compounds and pharmacology
- `dereplication` — Molecular formula dereplication (exact mass, degree of unsaturation)
- `selectivity_index` — Selectivity index calculator (IC50 cancer / IC50 normal)

**API endpoint:** `POST /api/natural_products`
