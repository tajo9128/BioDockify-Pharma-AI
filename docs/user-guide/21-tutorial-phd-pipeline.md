# Chapter 21: Tutorial — PhD Research Pipeline

## 21.1 Defining the Research Question
1. Open **Research CMD** → Projects tab
2. Enter topic: "Machine learning for predicting drug-target interactions"
3. Select type: PhD
4. Add objectives:
   - Review current ML methods for DTI
   - Build QSAR model on BindingDB dataset
   - Validate on independent test set
   - Compare with literature benchmarks
5. Click **Start Pipeline**

---

## 21.2 Pipeline Stages (25 stages, 9 phases)

| Phase | Stages | Duration |
|-------|--------|----------|
| Scoping | Topic detection, scope definition | 1 day |
| Literature | 10-database search, gap analysis | 3 days |
| Molecular | Descriptor calculation, feature selection | 1 day |
| QSAR | Model training, validation | 2 days |
| Docking | Protein preparation, virtual screening | 2 days |
| Statistics | Hypothesis testing, power analysis | 1 day |
| Decision | Results synthesis, recommendation | 1 day |
| Writing | Paper drafting, figure generation | 3 days |
| Publication | Journal selection, submission prep | 1 day |

---

## 21.3 HITL Mode Selection

| Mode | When to Use |
|------|-------------|
| **Auto** | Routine tasks, well-defined problems |
| **Confirm** | Before each phase transition |
| **Review** | At quality gates |
| **Guide** | Agent suggests, you decide |
| **Co-pilot** | Side-by-side collaboration |
| **Override** | Manual intervention needed |
| **Pause** | Stop and resume later |
| **Audit** | Review all decisions |

---

## 21.4 Monitoring Quality Gates

| Gate | Threshold |
|------|-----------|
| Literature completeness | ≥20 relevant papers |
| Descriptor validity | 0 NaN values |
| Model performance | R² ≥ 0.6 or Accuracy ≥ 0.7 |
| Docking success | ≥1 pose with energy < -5 kcal/mol |
| Statistical significance | p < 0.05 |

---

## 21.5 Literature Synthesis
1. Pipeline searches 10 databases automatically
2. Agent synthesizes findings into structured review
3. Identifies research gaps
4. Suggests methodological improvements

---

## 21.6 Molecular Analysis
1. Auto-calculates descriptors for all compounds
2. Selects optimal feature set
3. Trains multiple models (RF, GB, SVR)
4. Selects best model by CV performance

---

## 21.7 Statistical Analysis
1. Runs hypothesis tests on results
2. Generates publication-ready figures
3. Calculates effect sizes and confidence intervals
4. Validates statistical assumptions

---

## 21.8 Manuscript Writing
1. Generates IMRaD structure
2. Includes methods section with reproducibility details
3. Formats references in target journal style
4. Creates figure legends

---

## 21.9 Journal Selection
1. Pipeline suggests journals based on topic
2. Runs **Journal Finder** verification
3. Checks for predatory/hijacked journals
4. Recommends top 3 journals with justification

---

## 21.10 Long-Term Memory
1. All decisions logged with rationale
2. Knowledge retained across sessions (30-day decay)
3. Cross-project knowledge evolution
4. Export research log for thesis
