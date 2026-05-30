# Chapter 5: QSAR Modeler

## 5.1 Overview

The QSAR Modeler trains machine learning models on molecular descriptors to predict biological activity. Supports both regression (continuous values like IC50) and classification (active/inactive).

### Access Path
**All Tools → QSAR Modeler** (or click ⚖️ icon)

### Tabs: Train · Predict · Batch · Read-Across · Models

---

## 5.2 Training a Model

### Step 1: Upload Dataset
- CSV file with SMILES column + activity column
- Select **Regression** or **Classification** task
- Name the model (e.g., "COX2_inhibitor_RF")

### Step 2: Configure
| Setting | Options | Default |
|---------|---------|---------|
| Task | Regression / Classification | Regression |
| Model Type | RF, GB, SVR, PLS, Ridge, Lasso / RFC, SVC, LR | RandomForest |
| CV Folds | 2-10 | 5 |
| Test Split | 0-50% | 20% |

### Step 3: Process & Train
1. **Process Dataset** — Calculates 51 RDKit descriptors (physicochemical, topological, electronic, fragment)
2. **Feature Selection** (optional) — Mutual information or ANOVA F-test
3. **Start Training** — Background thread with status polling

### Model Types

**Regression:**
| Model | Best For |
|-------|----------|
| RandomForest | General purpose, robust |
| GradientBoosting | Higher accuracy, slower |
| SVR | Small datasets |
| PLS | Correlated descriptors |
| Ridge/Lasso | Regularized linear |

**Classification:**
| Model | Best For |
|-------|----------|
| RandomForestClassifier | General purpose |
| SVC | Small datasets, high-dimensional |
| LogisticRegression | Interpretable, fast |

### Metrics
- **Regression**: CV R², RMSE, Train R², External Test R²
- **Classification**: CV Accuracy, F1, AUC, External Test Accuracy

---

## 5.3 Prediction

### Single Prediction
1. Select a trained model from dropdown
2. Enter SMILES string
3. Click **Predict**
4. View predicted value + Applicability Domain status:
   - 🟢 in_domain — within model's training space
   - 🟡 warning — near boundary
   - 🔴 out_of_domain — extrapolation

### Batch Prediction
1. Select model
2. Paste multiple SMILES (one per line)
3. Click **Batch Predict**
4. View ranked results with AD status per compound

---

## 5.4 Read-Across

Find similar compounds in the training set:
1. Select model
2. Enter query SMILES
3. Click **Find Analogues**
4. View top analogues with ECFP4 Tanimoto similarity (≥0.3)

Use for data-gap filling and SAR analysis.

---

## 5.5 Model Management

**Models tab** shows all trained models with:
- Model name, type, metrics
- Task badge (REG/CLASS)
- External test metrics
- Williams Plot button
- Delete button

### Williams Plot
Click **Williams Plot** on any model to see:
- X-axis: Hat value (leverage)
- Y-axis: Standardized residuals
- h* threshold line (applicability domain boundary)
- Points colored by domain status

---

## 5.6 Example: BBB Permeability Classifier

1. Upload CSV with SMILES + BBB permeability labels (0/1)
2. Select **Classification** → **RandomForestClassifier**
3. Process Dataset → 2000 compounds, 51 descriptors
4. Feature Selection → top 20 features by mutual information
5. Start Training → CV Accuracy: 0.85, F1: 0.83
6. Run Batch Predict on 10,000 virtual compounds
7. Filter for AD=in_domain predictions
8. Export hits for experimental validation
