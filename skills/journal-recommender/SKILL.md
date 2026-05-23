---
name: journal-recommender
description: >
  Recommends the best journals for an academic paper. Use this skill whenever an author wants to know where to submit their paper, asks for journal suggestions, wants to find suitable journals for their research, or asks "which journal should I submit to". Takes the paper abstract or full manuscript, gathers the author's preferences via interactive buttons, evaluates the quality and scope of the work, then produces an exhaustive ranked list of suitable journals drawn exclusively from the Scopus and WoS indexed journal database bundled with this skill. Enriches each recommendation with live metrics (IF, CiteScore, SJR, quartile) fetched from Scimago, JCR, and publisher pages. Delivers a formatted PDF report. Always trigger this skill — do not attempt journal recommendations without it.
---

# Journal Recommender Skill

## Overview

This skill recommends journals for academic papers and delivers results as a formatted PDF report. Every recommendation comes from the bundled SQLite database of 36,145 Scopus- and/or WoS-indexed journals (processed from official March 2025 Scopus and March 2024 WoS master lists). No journal outside this database is ever recommended.

**Database:** `assets/journals.db`  
**Report generator:** `scripts/generate_report.py`  
**Schema:** title, issn, eissn, publisher, oa_status, asjc_codes, scopus_subjects, wos_indexed, scopus_indexed, wos_categories, source_type

---

## Step 1 — Collect the Paper

Ask the author to paste their **abstract** (minimum) or full manuscript. A title alone is insufficient — the abstract is needed to extract field, methodology, and contribution.

---

## Step 2 — Gather Preferences (interactive buttons, one turn)

Use `ask_user_input_v0` with two questions in a single call — do not ask the author to type:

```python
ask_user_input_v0(questions=[
  {
    "question": "Which indexing databases should the journals be in?",
    "type": "single_select",
    "options": ["Scopus only", "WoS only", "Both (dual-indexed)", "No preference"]
  },
  {
    "question": "What type of journal access do you prefer?",
    "type": "single_select",
    "options": ["Open Access only", "Subscription only", "No preference"]
  }
])
```

Both preferences are fully actionable from the database. Do not ask about acceptance rates or decision times — this data is not publicly disclosed by the majority of publishers and cannot be reliably applied as a filter.

Proceed with selections immediately; do not ask follow-up questions.

---

## Step 3 — Analyse the Paper (internal)

### 3a. Subject Mapping

Extract from the abstract/manuscript:
- **Primary field**: the main discipline (e.g. "Surface Engineering", "Oncology", "Machine Learning")
- **Secondary fields**: adjacent disciplines touched by the paper
- **Methodology type**: empirical/experimental | review/meta-analysis | modelling/simulation | theoretical | clinical trial | case study | mixed methods
- **Keywords**: 6–10 terms that would appear in a journal's aims & scope

Map to:
- **WoS Categories** — match against `wos_categories` column
- **Scopus ASJC subjects** — match against `scopus_subjects` column

### 3b. Quality Assessment & Tier Assignment (internal — scores never shown to author in raw form)

Score on five dimensions, 1–5 each:

| Dimension | 5 | 3 | 1 |
|-----------|---|---|---|
| **Novelty** | New method/framework, first-of-kind finding | Clear extension of prior work | Replication, descriptive |
| **Methodological Rigor** | Multi-method, validated, large n | Standard methods, adequate n | Anecdotal, no controls |
| **Contribution Breadth** | Changes the wider field | Advances a sub-field | Answers one narrow question |
| **Evidence Quality** | Longitudinal, validated instruments, robust stats | Cross-sectional, standard stats | Pilot, n<30, no validation |
| **Clarity of Advance** | Clearly surpasses prior work, benchmarked | Incremental but documented | Unclear advance |

**Score → tier anchor:**
- 21–25 → **Ambitious**
- 16–20 → **Target**
- 11–15 → **Safe**
- ≤10 → **Safe** only

Always present all three tiers regardless of score. The scores determine composition and ordering — not whether a tier appears.

The scores ARE shown in the PDF report as a Quality Assessment section (with visual bars and written assessments per dimension), but framed as "how we evaluated the paper" — not as a judgment passed on the author.

### Tier Definitions

| Tier | Journal Profile | Selectivity |
|------|----------------|-------------|
| 🔴 **Ambitious** | Top 10–15% of field by SJR/CiteScore. High-profile specialty or flagship journals. | Typically <25% acceptance |
| 🟡 **Target** | Top 15–50% of field. Strong specialty journals with direct scope match. Best realistic fit. | Typically 20–50% acceptance |
| 🟢 **Safe** | Lower half of field ranking. Broad or less selective scope. High acceptance probability. | Typically >35% acceptance |

### Tier Sizing

| Tier | Target count |
|------|-------------|
| Ambitious | 8–12 journals |
| Target | 12–18 journals |
| Safe | 8–14 journals |

If a tier exceeds target count, show top N by SJR/CiteScore and offer: *"X more journals match in this tier — ask me to expand."*

---

## Step 4 — Query the Database

```python
import sqlite3, os

DB = os.path.join(os.path.dirname(__file__), '..', 'assets', 'journals.db')
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

filters = []
params = []

if indexing == 'wos_only':
    filters.append('wos_indexed = 1')
elif indexing == 'scopus_only':
    filters.append('scopus_indexed = 1')
elif indexing == 'both':
    filters.append('wos_indexed = 1 AND scopus_indexed = 1')

if oa == 'oa_only':
    filters.append("oa_status = 'Open Access'")
elif oa == 'subscription_only':
    filters.append("oa_status = 'Subscription'")

subject_clauses = []
for kw in subject_keywords:
    subject_clauses.append("(wos_categories LIKE ? OR scopus_subjects LIKE ? OR title LIKE ?)")
    params.extend([f'%{kw}%', f'%{kw}%', f'%{kw}%'])

if subject_clauses:
    filters.append('(' + ' OR '.join(subject_clauses) + ')')

where = ' AND '.join(filters) if filters else '1=1'
rows = conn.execute(f"""
    SELECT title, publisher, oa_status, wos_indexed, scopus_indexed,
           wos_categories, scopus_subjects, issn, eissn
    FROM journals WHERE {where}
    ORDER BY (wos_indexed + scopus_indexed) DESC, title ASC
    LIMIT 150
""", params).fetchall()
conn.close()
```

If fewer than 20 results, broaden keywords (drop methodology terms, keep only primary field). If still fewer than 10, inform the author.

---

## Step 5 — Enrich with Live Metrics

For the top ~50 most subject-relevant candidates, fetch live metrics via web search. **Do not rely on training data for IF or CiteScore** — these change annually (e.g., the June 2025 JCR update moved Carbohydrate Polymers from 12.5 → 13.58).

### Sources in order of preference

1. **Clarivate JCR (June 2025)** → Impact Factor, WoS quartile  
2. **Scimago** → SJR score, Scopus quartile  
   Search: `[journal title] SJR scimago 2024`  
3. **Researcher.life / Resurchify** → CiteScore, combined view  
   Search: `[journal title] CiteScore impact factor 2024`  
4. **Publisher pages** (RSC, MDPI, ACS, Elsevier) → often publish their own metrics

### Metrics to collect per journal

| Metric | Used for |
|--------|----------|
| Impact Factor (IF) | Table display |
| CiteScore | Table display |
| SJR score | Internal tier placement |
| Quartile (primary category) | Table display |

**Do NOT collect or display acceptance rates or decision times.** These are inconsistently published by fewer than 20% of journals, creating misleading blank fields. They were removed from the output format.

### Quartile note

WoS and Scopus quartiles can differ depending on the subject category chosen. Always show the most relevant category for the paper. If they differ meaningfully (e.g., Q3 Scopus / Q1 WoS Textiles), show both.

### Tier refinement using live metrics

- **Ambitious**: Top 15% by SJR in primary category, OR IF > 2× the field median
- **Target**: 15–50% by SJR, OR IF within 0.5–2× field median
- **Safe**: Bottom 50% by SJR, broadly-scoped, or high-volume/lower selectivity

If metrics unavailable: dual-indexed → lean Target; single-indexed unknown → Safe.

---

## Step 6 — Generate the PDF Report

Use `scripts/generate_report.py` as the template base. Adapt paper-specific content (title, field, scores, journal lists) for each new paper.

### Report structure (8 sections in order)

1. **Cover banner** — paper title, authors, institution, date generated
2. **Paper Summary table** — field, methodology, key contribution, keywords, preferences, total journals found
3. **🔴 Ambitious journals** — table + fit notes
4. **🟡 Target journals** — table + fit notes
5. **🟢 Safe journals** — table + fit notes
6. **Paper Quality Assessment** — 5-dimension table with visual score bars + written assessment per dimension + total score banner with plain-language verdict
7. **What the Tiers Mean** — Ambitious/Target/Safe definitions with selectivity ranges + disclaimer about database
8. **Notes on Metrics & Methodology**

### Table format (8 columns)

| # | Journal | Publisher | Index | Access | IF (2024) | CiteScore | Quartile |

No acceptance rate column. No decision time column.

### Tier banners

Plain headers only — `🔴 AMBITIOUS JOURNALS`, `🟡 TARGET JOURNALS`, `🟢 SAFE JOURNALS`. No subtitle or description line under the banner. The tier definitions section at the end of the report already covers this. Adding it again under the banner is redundant.

### Fit notes

One sentence per journal, placed immediately below the table row as a left-bordered callout block. Must be:
- **Paper-specific** — reference the actual methodology, topic, or finding
- **Informative** — tell the author something they couldn't infer themselves
- **Concise** — one sharp sentence only

**Good:** *"Directly covers ZnO nanoparticle surface engineering for functional textiles; the dual silanization mechanism and AATCC-standardised durability data are precisely what this journal's reviewers evaluate."*  
**Bad:** *"A leading journal covering nanoscience and materials."*

---

## Important Rules

1. **Never recommend a journal outside the database.** If a well-known journal is missing from results, state: *"[Journal] was not found in the March 2025 Scopus / March 2024 WoS master lists and is therefore not included."*

2. **Never fabricate metrics.** Show "—" if a metric cannot be found after searching. Never estimate or guess.

3. **Always search live** for every report. Metrics change with each annual JCR/Scopus release.

4. **Coloration Technology** and similar specialty textiles journals: prefer the WoS category quartile over the Scopus one when they differ significantly — the textiles community recognises WoS rankings.

5. **MDPI journals** (Polymers, Nanomaterials, Coatings, Fibers): Polymers is genuinely Q1 with IF 4.9 → place in Target. Nanomaterials (IF 4.3, Q1 Scopus) → Target or Safe depending on field. Coatings and Fibers → Safe.

6. **Offer to expand** at the end of every report with: *"Want me to expand any tier, filter by sub-field, or focus on open-access journals only?"*
