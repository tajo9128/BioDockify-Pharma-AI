# BioDockify SEO Implementation Roadmap
**Generated:** 2026-08-17

---

## KPI Targets

| Metric | Baseline (Aug 2026) | 3 Months | 6 Months | 12 Months |
|--------|---------------------|----------|----------|-----------|
| Organic Traffic | ~0 clicks/day | 50/day | 200/day | 800/day |
| Indexed Pages | 107 | 140 | 180 | 250 |
| Referring Domains | 0 | 15 | 40 | 120 |
| Keywords Top 10 | ~1 (branded) | 15 | 50 | 200 |
| Keywords Top 3 | 0 | 3 | 15 | 60 |
| Domain Rating | <5 | 10 | 20 | 35 |

---

## Phase 1: Foundation (Weeks 1–4)

**Goal:** Fix technical signals so Google understands what BioDockify is.

### Technical SEO
- [ ] **Schema markup** — Add `SoftwareApplication` to homepage, `/features`, `/pricing`
- [ ] **Article schema** — Template and apply to all 60 blog posts
- [ ] **FAQPage schema** — Apply to all 12 `/knowledge/` pages
- [ ] **Homepage H1** — Must contain "molecular docking" (currently unclear from JS rendering)
- [ ] **Meta title/description audit** — Rewrite top 20 pages to include target keywords
- [ ] **Core Web Vitals check** — Run PageSpeed on homepage; target LCP < 2.5s
- [ ] **Canonical tags** — Ensure no duplicate content between `/dock/single` and `/molecular-docking-online`
- [ ] **Internal linking** — Add 3 contextual links from each knowledge page to tool pages

### New Pages (Phase 1)
- [ ] `/solutions/academic-research`
- [ ] `/admet-prediction-online`
- [ ] `/compare/biodockify-vs-swissdock`

### Backlinks (Phase 1)
- [ ] Submit to AlternativeTo.net
- [ ] Submit to bio.tools (ELIXIR bioinformatics registry)
- [ ] Create Google Business Profile (if applicable)

**Success criteria:** Schema live on all pages; 3 new pages published; 5 backlinks acquired

---

## Phase 2: Expansion (Weeks 5–12)

**Goal:** Win comparison + long-tail keywords; start getting organic clicks.

### Content Creation
- [ ] 5 new comparison pages (see CONTENT-CALENDAR.md)
- [ ] 2 free tool pages (`/tools/molecular-weight-calculator`, `/tools/lipinski-calculator`)
- [ ] 1 solutions page (`/solutions/pharma-biotech`)
- [ ] 6 blog posts (see CONTENT-CALENDAR.md, months 2–3)
- [ ] 5 glossary pages (highest-volume terms)

### E-E-A-T Improvements
- [ ] Add author bios to all blog posts (photo, credentials, Google Scholar link)
- [ ] Add "About the methodology" section to comparison pages
- [ ] Add "Last reviewed" dates to all knowledge pages
- [ ] Create `/about` page with team credentials

### Backlinks (Phase 2)
- [ ] Launch on Product Hunt
- [ ] Publish GitHub repo with example workflows
- [ ] Email outreach to 15 university computational chemistry labs
- [ ] Submit to Capterra, G2, SourceForge

**Success criteria:** 15+ referring domains; top 10 for 5 non-branded keywords; 50 clicks/day

---

## Phase 3: Scale (Weeks 13–24)

**Goal:** Compound content; build authority; capture mid-difficulty keywords.

### Content Creation
- [ ] Complete `/glossary/` with 40+ terms
- [ ] 4 more comparison pages
- [ ] 2 solutions pages
- [ ] 2 case studies
- [ ] 8 blog posts
- [ ] 3 free tool pages (smiles converter, logP, pKa calculators)

### Link Building
- [ ] Guest post on Towards Data Science / Medium (1 post/month)
- [ ] Publish benchmark dataset on Zenodo with DOI
- [ ] Reach out to 10 more academic labs
- [ ] Submit protocol to Protocol Exchange (Springer Nature)

### GEO Optimization
- [ ] Expand `/llms.txt` with complete tool descriptions
- [ ] Add structured benchmark data tables to comparison pages
- [ ] Monitor AI Overview appearances for target keywords

**Success criteria:** 40+ referring domains; 50+ keywords in top 10; 200 clicks/day

---

## Phase 4: Authority (Months 7–12)

**Goal:** Become the reference platform in computational drug discovery.

### Content
- [ ] Monthly blog cadence (2–3 posts/month)
- [ ] Quarterly comparison page updates
- [ ] Publish original research data (docking benchmark study)
- [ ] Community/forum section or Discord for user questions

### Link Building
- [ ] Submit application note to Journal of Cheminformatics
- [ ] Conference presence (ACS, AAPS)
- [ ] Partner integrations (link exchanges with complementary tools)

### Technical
- [ ] Implement HowTo schema on tutorial blog posts
- [ ] Add Dataset schema to any benchmark data pages
- [ ] International SEO consideration (Chinese, Japanese markets have significant computational chemistry activity)

**Success criteria:** 120+ referring domains; domain rating 35+; 800 clicks/day; top 3 for primary product keywords

---

## Quick Wins Checklist (Do This Week)

1. **Submit to AlternativeTo.net** — 30 minutes, free, gets a backlink immediately
2. **Submit to bio.tools** — ELIXIR registry for bioinformatics tools — high-authority academic backlink
3. **Fix homepage H1** — ensure "molecular docking" appears in the H1 tag
4. **Add SoftwareApplication schema** to homepage — can be done in 1 hour
5. **Rewrite homepage meta description** — currently likely generic; add "molecular docking online + drug discovery platform + free trial"
6. **Run Google Search Console URL Inspection** on homepage — check if Google is correctly indexing the JS-rendered content

---

## Resource Requirements

| Phase | Pages to Create | Blog Posts | Hours Estimate |
|-------|----------------|------------|----------------|
| Phase 1 (wks 1-4) | 3 | 0 | 20 hrs |
| Phase 2 (wks 5-12) | 9 | 6 | 60 hrs |
| Phase 3 (wks 13-24) | 15 | 8 | 80 hrs |
| Phase 4 (mo 7-12) | 10 | 15 | 100 hrs |

---

## Risks & Mitigation

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| JS rendering issues (Google can't index content) | High | Test with URL Inspection; consider SSR/pre-rendering for key pages |
| Google keeps associating site with "pharma AI writing" | Medium | Explicit homepage optimization; disavow if needed |
| Competitors copy comparison pages | Medium | Keep updating with verified data; add user testimonials |
| Academic community skepticism of cloud tools | Medium | Emphasize that Vina/GROMACS algorithms are unchanged; publish validation data |
| Low blog engagement in competitive niche | Low | Focus on tutorial depth; target graduate student pain points |

