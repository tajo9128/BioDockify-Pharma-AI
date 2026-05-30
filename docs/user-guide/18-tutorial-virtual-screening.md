# Chapter 18: Tutorial — Virtual Screening Campaign

## 18.1 Research Question
Screen a library of 50 flavonoids against COX-2 (PDB: 3LN1) for anti-inflammatory drug leads.

---

## 18.2 Step 1: Literature Search
1. Open **Research CMD** → Literature tab
2. Search "COX-2 inhibitors flavonoids"
3. Review papers for binding site information
4. Note key residues: Arg120, Tyr355, Ser530

---

## 18.3 Step 2: Protein Preparation
1. Download COX-2 PDB (3LN1) from RCSB
2. Open **Molecular Toolkit** → Docking tab
3. Paste PDB content in Protein card
4. Verify protein name appears

---

## 18.4 Step 3: Ligand Library
1. Prepare CSV with 50 flavonoid SMILES
2. Open **QSAR** → Train tab
3. Upload CSV for activity prediction (optional)

---

## 18.5 Step 4: Docking
1. Enter first flavonoid SMILES in Ligand card
2. Click **Run Docking**
3. View poses in Analysis tab
4. Download best pose for reference

---

## 18.6 Step 5: Batch Screening
1. Open **Pharmacophore** → Batch tab
2. Enter query pharmacophore (from known COX-2 inhibitor)
3. Enter flavonoid library SMILES
4. Set pre-filters: MW<500, LogP<5, RotBonds<10
5. Click **Screen Batch**
6. View hits with weighted scores

---

## 18.7 Step 6: Analysis
1. Open **Molecular Toolkit** → Analysis tab
2. View 3D receptor+ligand visualization
3. Check H-bond interactions with Arg120, Tyr355
4. View residue energy decomposition
5. Download interaction SVG for publication

---

## 18.8 Step 7: QSAR Validation
1. Train RF classifier on known COX-2 inhibitors
2. Predict activity for top docking hits
3. Check applicability domain (Williams Plot)
4. Filter for AD=in_domain predictions

---

## 18.9 Step 8: Results
1. Rank compounds by consensus score (Vina + GNINA)
2. Filter by drug-likeness (Lipinski, PAINS=PASS)
3. Select top 5 candidates for experimental validation
4. Generate publication figures (BOILED-Egg, interaction diagram)
