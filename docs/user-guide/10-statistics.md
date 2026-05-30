# Chapter 10: Statistics Suite

## 10.1 Overview
SPSS-level biostatistics with 20 analysis types, 8 chart types, and data transformation tools.

### Access Path
**All Tools → Statistics** (or click 📊 icon)

### Tabs: Analysis · Charts · Transform

---

## 10.2 Analysis Types

| Category | Tests |
|----------|-------|
| **Descriptive** | Mean, median, SD, variance, IQR, range, skewness, kurtosis |
| **Correlation** | Pearson, Spearman, Kendall |
| **T-Tests** | Independent, paired, one-sample |
| **ANOVA** | One-way, two-way + Tukey, Bonferroni, Scheffe, LSD post-hoc |
| **Regression** | Linear, multiple, logistic, Poisson, negative binomial, stepwise |
| **Non-Parametric** | Mann-Whitney U, Wilcoxon, Kruskal-Wallis, Friedman, Chi-square, Fisher exact, McNemar |
| **Survival** | Kaplan-Meier, Cox proportional hazards |
| **Normality** | Shapiro-Wilk, Kolmogorov-Smirnov, Anderson-Darling |
| **ROC** | AUC, sensitivity, specificity, optimal cutoff (Youden), DeLong comparison |
| **Meta-Analysis** | Fixed/random effects, forest plot, heterogeneity (I², Q) |
| **PK/PD** | One-compartment, two-compartment, non-compartmental analysis |
| **Bioequivalence** | Two One-Sided Tests (TOST) |
| **Power Analysis** | Sample size calculation for t-test, ANOVA, proportion |
| **Curve Estimation** | Linear, quadratic, cubic, exponential, logarithmic, power, S-curve, logistic |

---

## 10.3 Data Import
- **CSV upload**: Auto-detect columns
- **Paste**: Tab/comma-separated data
- **Preview**: First 10 rows shown before analysis

---

## 10.4 Charts (8 types)
| Chart | Use Case |
|-------|----------|
| Histogram | Distribution visualization |
| Box Plot | Quartile + outlier display |
| Scatter Plot | Correlation visualization |
| Q-Q Plot | Normality assessment |
| Bar Chart | Category comparison |
| ROC Curve | Diagnostic performance |
| Survival Curve | Time-to-event analysis |
| Heatmap | Correlation matrix |

---

## 10.5 Data Transformation
| Operation | Description |
|-----------|-------------|
| Compute | Create new columns from formulas |
| Recode | Map old values to new values |
| Rank | Assign ranks to values |
| Fill Missing | Mean/median/mode imputation |
| Standardize | Z-score normalization |
| PCA | Principal component analysis |
| Factor Analysis | Exploratory factor analysis |
| Cronbach's Alpha | Scale reliability |
| Clustering | K-means, hierarchical |

---

## 10.6 Example: Clinical Trial Analysis
1. Upload CSV with treatment groups + outcomes
2. Run **Independent T-Test** for primary endpoint
3. Run **Kaplan-Meier** for time-to-event
4. Run **ROC** for biomarker validation
5. Generate **Box Plot** for visualization
6. Export results as CSV
