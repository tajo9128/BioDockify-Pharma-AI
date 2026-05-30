# Chapter 7: Journal Finder

## 7.1 Overview
The Journal Finder contains 36,145 Scopus/WoS journals with deep research capabilities, hijacked journal detection, and fake website analysis.

### Access Path
**All Tools → Journal Finder** (or click ✅ icon)

### Tabs: Verify · Search DB · Suggest · Dossier

---

## 7.2 Verify Tab
Enter journal name + optional ISSN → **Verify**:
- **GENUINE** (green) — indexed in ≥2 databases, no predatory flags
- **LIKELY_GENUINE** (blue) — indexed in 1+ database
- **PREDATORY** (red) — predatory flags detected
- **UNVERIFIED** (yellow) — no verification possible

Checks: Scopus API, Clarivate MJL, SCImago, DOAJ, Predatory pattern database, Hijacked journal database

---

## 7.3 Search DB Tab
Search 36,145 journals with filters:
- **Scopus** — Scopus-indexed only
- **WoS** — Web of Science indexed only
- **Open Access** — DOAJ-listed only
- **Subject** — filter by ASJC codes or subject keywords

Results show: title, publisher, ISSN, indexing badges, subject categories

---

## 7.4 Suggest Tab
Enter paper title + abstract + keywords → ranked journal suggestions:
- Sources: BioDockify DB + Elsevier Journal Finder + JANE (biosemantics)
- Scored by: relevance (40%) + authority (30%) + speed (15%) + access (15%)
- Filters: OA only, max APC, minimum quartile

---

## 7.5 Dossier Tab
Comprehensive journal profile with 5 live source scraping:

| Data | Source |
|------|--------|
| Article count + recency | PubMed API |
| SJR + quartile + H-index | SCImago HTML scrape |
| APC + license + waiver | DOAJ API |
| h5-index + h5-median | Google Scholar scrape |
| Review time + acceptance rate | Researcher.life scrape |
| Publication frequency | Crossref API |

**Deep Research** button triggers ResearchOrchestrator + Agent Zero for full journal investigation.

---

## 7.6 Fake Website Detector
Checks journal website authenticity with 6 tests:
1. **Known Publisher Domain** — matches 23 legitimate publishers
2. **Free TLD Detection** — flags .tk, .ml, .ga, .cf, Blogspot, Wix, WordPress
3. **ISSN Registry URL** — queries portal.issn.org for official URL
4. **Crossref ISSN** — verifies ISSN is registered
5. **Domain Age** — detects very new domains
6. **Hijacked Journal DB** — matches against known clones

Risk levels: verified / low / medium / high

---

## 7.7 Example: Finding a Journal for a QSAR Study
1. Click **Suggest** tab
2. Enter title: "Predicting BBB permeability of CNS drug candidates using machine learning"
3. Enter abstract keywords
4. Set **OA Only** filter, **Q1+** minimum
5. Click **Suggest Journals**
6. View ranked results with match percentages
7. Click **Verify** on top result to check legitimacy
8. Click **Dossier** for full profile (APC, review time, h5-index)
