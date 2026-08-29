# BioDockify Site Structure Plan
**Generated:** 2026-08-17

---

## Current Structure (107 pages) — What Exists

```
/                           ← Home
/features                   ← Features overview  
/ecosystem                  ← Integrations/ecosystem
/pricing                    ← Pricing

/dock/single                ← Single docking tool
/dock/batch                 ← Batch docking tool
/dock/analysis              ← Docking analysis

/brain                      ← AI analysis
/ai-analysis                ← AI analysis
/pipeline                   ← Pipeline tool

/md/simulation              ← MD simulation
/md/results                 ← MD results

/pharma                     ← Pharmacology hub
/pharma/qsar                ← QSAR tool
/pharma/admet               ← ADMET tool

/tools/converter            ← File converter
/tools/viewer               ← Molecule viewer
/tools/smiles               ← SMILES tool

/workspace/research         ← Research workspace
/workspace/literature       ← Literature tool
/workspace/knowledge-base   ← Knowledge base

/publishing/writer          ← Scientific writer
/publishing/journal         ← Journal tool

/molecular-docking-online   ← Feature landing page ✅
/molecular-dynamics-simulation ← Feature landing page ✅

/knowledge/autodock-vina    ← 12 knowledge pages ✅
/knowledge/molecular-docking
/knowledge/qsar
/knowledge/admet
/knowledge/molecular-dynamics
/knowledge/protein-preparation
/knowledge/ligand-preparation
/knowledge/virtual-screening
/knowledge/drug-discovery
/knowledge/binding-affinity
/knowledge/pharmacophore
/knowledge/lead-optimization

/compare/biodockify-vs-pyrx    ← 4 comparison pages ✅
/compare/biodockify-vs-chimera
/compare/biodockify-vs-maestro
/compare/vina-vs-gnina

/blog/[107 posts]           ← Deep blog ✅

/about
/contact
/blog
```

---

## Recommended Additions (Priority Order)

### Priority 1 — Solutions Pages (new section)

```
/solutions/
├── /solutions/academic-research
│   Target: grad students, academic labs
│   KW: "molecular docking for research", "free drug discovery tools for students"
│
├── /solutions/pharma-biotech
│   Target: pharma/biotech scientists
│   KW: "drug discovery platform pharma", "in silico screening software"
│
├── /solutions/cro
│   Target: contract research organizations
│   KW: "batch virtual screening cro", "molecular docking service"
│
└── /solutions/bioinformatics
    Target: bioinformatics students and labs
    KW: "bioinformatics drug discovery tools"
```

### Priority 2 — More Comparison Pages

```
/compare/
├── /compare/biodockify-vs-pyrx        ✅ exists
├── /compare/biodockify-vs-chimera     ✅ exists
├── /compare/biodockify-vs-maestro     ✅ exists
├── /compare/vina-vs-gnina             ✅ exists
│
├── /compare/biodockify-vs-swissdock   ← ADD: free online docking alternative
├── /compare/biodockify-vs-autodock    ← ADD: command-line vs cloud
├── /compare/biodockify-vs-glide       ← ADD (already in blog — needs page)
├── /compare/biodockify-vs-dockingserver ← ADD: direct competitor
├── /compare/best-molecular-docking-software ← ADD: roundup (high traffic)
└── /compare/free-molecular-docking-software ← ADD: "free" intent capture
```

### Priority 3 — ADMET / QSAR Expansion

```
/admet/
├── /admet-prediction-online           ← Feature landing, KW: "admet prediction online" (590/mo)
├── /admet/lipinski-rule-of-5          ← KW: "lipinski rule of 5 calculator" (480/mo)
├── /admet/pkpd-modeling               ← KW: "pkpd modeling software"
└── /admet/toxicity-prediction         ← KW: "toxicity prediction online"
```

### Priority 4 — Glossary (traffic + E-E-A-T)

```
/glossary/
├── /glossary/molecular-docking        ← KW: "what is molecular docking" (2,400/mo)
├── /glossary/binding-affinity         ← KW: "binding affinity definition"
├── /glossary/rmsd                     ← KW: "what is rmsd" (720/mo)
├── /glossary/autodock-vina            ← KW: "autodock vina"
├── /glossary/virtual-screening        ← KW: "virtual screening definition"
├── /glossary/admet                    ← KW: "admet pharmacology"
├── /glossary/qsar                     ← KW: "qsar definition"
├── /glossary/force-field              ← KW: "force field molecular dynamics"
├── /glossary/gromacs                  ← KW: "what is gromacs"
└── /glossary/[40+ more terms]
```

### Priority 5 — Free Tool Landing Pages (high traffic)

```
/tools/
├── /tools/molecular-weight-calculator ← KW: "molecular weight calculator" (22,200/mo!)
├── /tools/smiles-converter            ← KW: "smiles to mol converter" (590/mo)
├── /tools/lipinski-calculator         ← KW: "lipinski calculator" (480/mo)
├── /tools/pka-calculator              ← KW: "pka calculator" (1,600/mo)
└── /tools/logp-calculator             ← KW: "logp calculator" (720/mo)
```

### Priority 6 — Case Studies

```
/case-studies/
├── /case-studies/academic-docking-workflow
├── /case-studies/virtual-screening-1000-ligands
└── /case-studies/md-simulation-protein-stability
```

---

## Internal Linking Map

### Hub → Spoke Model

**Hub: `/knowledge/molecular-docking`**
→ `/dock/single`, `/dock/batch`, `/molecular-docking-online`
→ `/blog/molecular-docking-principles-workflow-applications`
→ `/compare/biodockify-vs-pyrx`, `/compare/biodockify-vs-chimera`
→ `/glossary/binding-affinity`, `/glossary/autodock-vina`

**Hub: `/knowledge/molecular-dynamics`**
→ `/md/simulation`, `/molecular-dynamics-simulation`
→ All 25 GROMACS/MD blog posts
→ `/compare/gromacs-vs-amber` (in blog — needs linking)
→ `/glossary/rmsd`, `/glossary/force-field`

**Hub: `/knowledge/admet`**
→ `/pharma/admet`, `/admet-prediction-online`
→ `/pharma/qsar`
→ `/glossary/admet`, `/glossary/lipinski`

**Hub: `/solutions/academic-research`**
→ `/pricing` (free tier)
→ `/molecular-docking-online`, `/md/simulation`
→ 3 best tutorial blog posts

---

## URL Structure Rules

- Use hyphens, never underscores
- Keep URLs short: `/compare/biodockify-vs-pyrx` not `/compare/biodockify-versus-pyrx-molecular-docking`
- Knowledge pages: `/knowledge/{term}` (keep existing structure)
- Blog posts: `/blog/{descriptive-slug}` (keep existing)
- Tools: `/tools/{tool-name}` (keep existing)
- New solutions: `/solutions/{audience}` (new)
- Glossary: `/glossary/{term}` (new)

