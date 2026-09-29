# Biostatistics Demo Data

Eight ready-to-load datasets for testing every major analysis family in the
Statistics module. All values are **synthetic but realistic** (randomly
generated with true effects built in, so tests return meaningful results —
significant where an effect was planted). No real patient data.

## How to load

Statistics → **Import** → upload the CSV → pick the columns shown below → run.

## Dataset → test map

| File | Scenario | Columns | Tests it demonstrates |
|---|---|---|---|
| `demo_independent_ttest.csv` | Drug A vs placebo — systolic BP reduction (n=60) | Group, BP_Reduction | Independent t-test, Mann-Whitney U, effect size |
| `demo_paired_ttest.csv` | HbA1c before vs after 12 weeks (n=25) | HbA1c_Before, HbA1c_After | Paired t-test, Wilcoxon signed-rank |
| `demo_anova_oneway.csv` | 4 dose groups — pain VAS score (n=80) | Dose, VAS_Score | One-way ANOVA, Kruskal-Wallis, Tukey post-hoc |
| `demo_repeated_measures.csv` | LDL at baseline / week 4 / week 8 (n=15) | Baseline_LDL, Week4_LDL, Week8_LDL | Repeated-measures ANOVA, Friedman |
| `demo_chi_square.csv` | New drug vs standard — outcome counts | Treatment × (Recovered/Improved/No_Response) | Chi-square, Fisher exact |
| `demo_regression.csv` | 40 compounds — properties vs potency | LogP, MW, HBD, TPSA → pIC50 | Pearson/Spearman correlation, linear + multiple regression |
| `demo_survival.csv` | 60 patients, two arms (n=60) | Time_Weeks, Event, Group | Kaplan-Meier, log-rank, Cox regression |
| `demo_reliability.csv` | 8-item pharma QoL questionnaire (n=30) | Q1..Q8 | Cronbach's alpha, item statistics |

## Expected highlights (planted effects)

- BP reduction: Drug A ≈ 14.5 vs placebo ≈ 6.8 mmHg → **t-test p < 0.001**
- HbA1c drop ≈ 1.1 points → **paired t-test p < 0.001**
- VAS dose-response 6.5 → 3.1 across doses → **ANOVA p < 0.001**
- LDL falls ~18 then ~29 mg/dL → **time effect p < 0.001**
- Survival: new-drug median ≈ 39 wk vs control ≈ 13 wk → **log-rank p < 0.05**
- Reliability: all items load one factor → **Cronbach's α ≈ 0.94**

Generated with seed 42 — values are stable across regenerations.
