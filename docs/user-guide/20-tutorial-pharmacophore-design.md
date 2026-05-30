# Chapter 20: Tutorial — Pharmacophore Design

## 20.1 Ligand Set Preparation
1. Collect 15 known CDK2 inhibitors
2. Format as SMILES (one per line)
3. Open **Pharmacophore** → Ligand tab

---

## 20.2 Pharmacophore Generation
1. Enter first inhibitor SMILES
2. Click **Generate**
3. View features: Donor, Acceptor, Hydrophobic, Aromatic
4. Note feature positions and radii

---

## 20.3 Shared Model
1. Switch to **Models** tab
2. Select **Shared (∩)** mode
3. Paste all 15 inhibitor SMILES
4. Click **Generate**
5. View conserved features (present in all molecules)
6. Note: 6 shared features identified

---

## 20.4 Validation
1. Test pharmacophore against known actives
2. Verify all actives match ≥4 features
3. Test against known inactives
4. Verify inactives match <3 features

---

## 20.5 Virtual Screening
1. Switch to **Screen** tab
2. Enter query (shared model features)
3. Enter library SMILES (ZINC subset)
4. Click **Screen Library**
5. View hits with weighted scores

---

## 20.6 ZINCPharmer Batch Screen
1. Switch to **Batch** tab
2. Enter query SMILES
3. Enter large library (10,000 compounds)
4. Set pre-filters:
   - MW: 200-500
   - LogP: -2 to 5
   - RotBonds: ≤10
   - TPSA: ≤140
   - HBA: ≤10
   - HBD: ≤5
5. Click **Screen Batch**
6. View: 10,000 total → 7,500 passed filter → 150 hits (2.0% hit rate)

---

## 20.7 Target Identification
1. Switch to **Target** tab
2. Enter query SMILES
3. Set conformers=10
4. Click **Profile**
5. View consensus feature profile across conformers
6. Rank conformers by richness + consensus score

---

## 20.8 Results
1. Select top 20 hits from batch screen
2. View 3D overlay of hits with pharmacophore
3. Download hit list as SDF
4. Select top 5 for experimental testing
