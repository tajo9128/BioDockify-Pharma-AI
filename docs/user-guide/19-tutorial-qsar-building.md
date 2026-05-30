# Chapter 19: Tutorial — QSAR Model Building

## 19.1 Dataset Curation
1. Collect 2000 compounds with BBB permeability labels (0/1)
2. Format as CSV: `smiles,label`
3. Open **QSAR Modeler** → Train tab
4. Upload CSV, set task=Classification

---

## 19.2 Descriptor Calculation
1. Click **Process Dataset**
2. View: 2000 compounds, 51 descriptors
3. Note descriptor groups: physicochemical, topological, electronic, fragment

---

## 19.3 Feature Selection
1. Click **Feature Selection** (k=20)
2. View top features by mutual information:
   - TPSA (highest)
   - MolLogP
   - NumHDonors
   - NumHAcceptors
   - Molecular Weight

---

## 19.4 Model Training
1. Select **RandomForestClassifier**
2. Set CV folds=5, test split=20%
3. Click **Start Training**
4. Wait for completion → CV Accuracy: 0.85, F1: 0.83

---

## 19.5 External Validation
1. View test set metrics:
   - Test Accuracy: 0.82
   - Test F1: 0.80
   - Test Precision: 0.84
   - Test Recall: 0.78

---

## 19.6 Applicability Domain
1. Click **Williams Plot** button
2. View leverage vs standardized residuals
3. Check h* threshold line
4. Most compounds in domain (green dots)

---

## 19.7 Batch Screening
1. Switch to **Batch** tab
2. Select trained model
3. Paste 10,000 virtual compound SMILES
4. Click **Batch Predict**
5. View ranked results with AD status

---

## 19.8 Read-Across
1. Switch to **Read-Across** tab
2. Select model
3. Enter query SMILES (new compound)
4. Click **Find Analogues**
5. View top 10 training set analogues with Tanimoto similarity

---

## 19.9 Reporting
1. Document OECD QSAR principles:
   - Defined endpoint (BBB permeability)
   - Unambiguous algorithm (RandomForest)
   - Defined domain of applicability
   - Measures of goodness-of-fit
   - Mechanistic interpretation (if possible)
2. Export model for regulatory submission
