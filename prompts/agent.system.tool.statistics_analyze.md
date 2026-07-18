## Statistics Tool

**Purpose:** Comprehensive statistical analysis — 20+ analysis types (descriptive, ANOVA, t-test, regression, PCA, survival, bioequivalence, non-parametric, Bayesian). Generates publication-quality plots. Results auto-store to the Knowledge Base.

**When to use:**
- User has experimental data (CSV/JSON) and needs statistical analysis
- User asks for ANOVA, t-test, regression, correlation, PCA
- User needs to compare groups (treatment vs control)
- User wants publication-quality plots (histogram, boxplot, scatter, volcano)
- User needs bioequivalence testing (90% CI, GMR)
- For PRISMA flowcharts in systematic reviews

**How to use:** Call via `code_execution_tool`.

```python
import sys; sys.path.insert(0, "/a0")
import asyncio
from api.statistics_analyze import StatisticsAnalyze

async def analyze():
    h = StatisticsAnalyze()
    result = await h.process({
        "action": "anova",
        "data": [
            {"group": "control", "value": 10.2},
            {"group": "control", "value": 11.5},
            {"group": "treatment", "value": 15.8},
            {"group": "treatment", "value": 16.2},
        ],
        "groups": "group",
        "values": "value",
    }, None)
    print("F-statistic:", result.get("f_statistic"))
    print("p-value:", result.get("p_value"))
    # Results auto-store to KB as category=statistics

asyncio.run(analyze())
```

**Actions:** `descriptive`, `ttest`, `anova`, `kruskal`, `regression`, `correlation`, `pca`, `clustering`, `survival`, `bioequivalence`, `bayesian`, `plot` (20+ total — call with no action to see the list)

**Critical rules:**
1. Results auto-store to KB — they appear under "Statistical Analysis" in the Knowledge Base UI.
2. For publication, use the `plot` action to generate figures.
3. Always report effect sizes and CIs, not just p-values.
4. Pair with the Pharmacology module for dose-response analysis (EC50/IC50).
