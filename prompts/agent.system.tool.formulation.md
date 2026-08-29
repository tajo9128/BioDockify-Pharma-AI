## Formulation Tool

**Purpose:** Pharmaceutics department tools for formulation scientists. Release kinetics modeling, dissolution profile comparison, nanoparticle characterization, stability prediction, excipient database, and formulation optimization.

**When to use:**
- User mentions release kinetics, dissolution, nanoparticle, stability, excipients, formulation optimization
- User uploads dissolution data and wants to fit kinetic models
- User wants to compare dissolution profiles (f2 similarity factor)
- User asks about nanoparticle characterization (zeta potential, PDI, encapsulation efficiency)
- User wants to predict shelf life from accelerated stability data
- User asks about excipients or formulation design

**Actions:**
- `release_kinetics` — Fit dissolution data to Zero-order, First-order, Higuchi, Korsmeyer-Peppas, Weibull models
- `dissolution_f2` — Calculate f2 similarity factor (FDA) and f1 difference factor
- `nanoparticle` — Characterize nanoparticles (zeta potential, PDI, EE%, LC%)
- `stability` — ICH Q1E shelf-life prediction from accelerated data (Arrhenius)
- `excipient_db` — Query excipient database by category (fillers, binders, disintegrants, lubricants, coatings)
- `optimize` — DOE/RSM formulation optimization

**API endpoint:** `POST /api/formulation`
