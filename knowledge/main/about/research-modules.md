# BioDockify Research Modules — Complete Reference (v7.37)

The BioDockify platform ships with 50+ research modules organized across all pharmacy departments. Each module runs as an interactive desktop window — the agent can perform the same computations via the `/api/<handler>` endpoints using `code_execution_tool`.

## Module Directory by Department

### Medicinal Chemistry & Drug Design (strongest)
| Module | API handler | What it does |
|---|---|---|
| Molecular Toolkit | `docking_prepare`, `docking_run` | AutoDock Vina docking + MM-GBSA rescoring + inline analysis |
| Docking Analysis | `docking_analysis` | 3D viewer, interactions, RMSD clusters, radial 2D diagrams |
| 3D-QSAR | `qsar3d` | MIF+PLS 3D-QSAR (CoMFA-style), model persistence |
| ADMET Prediction | `admet_predict` | SwissADME-grade ADMET panel |
| Pharmacophore | `pharmacophore` | Feature detection, screening, hypothesis, fingerprint, shape |
| Molecule Designer | `generative_chemistry` | BRICS de novo, genetic algorithm optimization, scaffold hopping |
| Retrosynthesis | `retrosynthesis` | Route planning, disconnections, complexity scoring |
| Reaction Lab | `reaction_lab` | Forward reactions, combinatorial enumeration, impurity prediction |
| Bioactivity Predictor | `bioactivity_predictor` | IC50/pIC50 prediction, similar actives, activity cliffs |
| Target Identification | `target_identification` | Disease-target links, druggability, pathway enrichment, prioritization |
| Drug Properties | `drug_properties` | hERG/Ames/pKa/BBB calculated properties |
| Drug Analysis | `drug_analysis` | PAINS/Brenk/NIH FilterCatalog (~480 structural alerts) |
| Structure Draw | `chem_canvas` | Chemical sketcher (Ketcher engine) with SketChem validation |
| MD Lite | `md_lite` | GPU-only molecular dynamics (OpenMM CUDA, auto-resume) |
| RNA Therapeutics | `rna_design` | siRNA design, codon optimization, RNA folding, CRISPR guides |

### Pharmacology & Clinical
| Module | API handler | What it does |
|---|---|---|
| Pharmacology | `pharmacology` | Dose-response 4PL, Schild pA2, operational τ/KA, NCA PK/PD |
| Pharmacovigilance Studio | `pharmacovigilance` | PRR/ROR/χ² signal detection, DDI screening (50+ pairs), ICSR drafting |
| Network Pharmacology Pro | `netpharm_pro` | Pathway ORA (BH-FDR), PPI hub analysis, herb-compound-target multilayer + Cytoscape export |
| Clinical Suite | `clinical` | TDM dosing, CKD-EPI renal, Child-Pugh hepatic, Naranjo ADR, Beers/STOPP-START |
| Pharmacoeconomics Lab | `pharmacoeconomics` | ICER/CEA with WTP sensitivity, QALYs, NNT cost, budget impact |
| EnviroTox | `envirotox` | BCF, Koc, LC50, PBT/vPvB environmental screening |

### Pharmaceutics
| Module | API handler | What it does |
|---|---|---|
| Preformulation & Delivery | `preformulation` | SMILES preformulation panel, excipient compatibility, liposome/nanoparticle/mucoadhesion/TDD calculators |
| Formulation Lab | `formulation` | Release kinetics (5 models), dissolution f2, ICH stability, QbD DoE (factorial/CCD/Box-Behnken/Plackett-Burman + mixture designs) |

### Pharmacognosy & Analysis
| Module | API handler | What it does |
|---|---|---|
| Phytochemistry Lab | `phytochem` | Fingerprint similarity, marker assay (ICH Q2 LOD/LOQ), heavy-metal limits, ethnobotany DB |
| Spectra Lab | `spectra_lab` | IR functional-group matcher, ¹H/¹³C NMR estimation, multiplet analyzer, MS fragment predictor, UV rules |
| Natural Products | `natural_products` | Phytochemical screening, extraction yield, IC50 4PL, plant DB, dereplication |

### QA & Regulatory
| Module | API handler | What it does |
|---|---|---|
| GMP Audit Suite | `gmp_audit` | WHO/EU/CFR/PIC-S checklists, EM + water limits, deviation-CAPA tracker, self-inspection planner |
| Regulatory Enhanced | `regulatory_enhanced` | eCTD/CTD structure, 40+ ICH guidelines, stability planner, BE report, IND/NDA checklists |
| Journal Finder | `journal_finder` | 36,145-journal recommender |

### Research & Teaching Tools
| Module | API handler | What it does |
|---|---|---|
| Research Hub / CMD | `literature_search`, `deep_research` | 10-database federated search, web scraping, 5-tier full-text retrieval |
| Knowledge Base | `knowledge` | RAG with hybrid retrieval (BM25 + FAISS + RRF fusion) |
| Slide Generator 2.0 | `ppt_master` (deck_* actions) | Internet research (PDFs, SlideShare, Wikipedia) → detailed editable PPTX up to 100 slides |
| Statistics | `statistics_analyze` + siblings | 56 analysis types (SPSS/jamovi level) with PDF reports |
| Academic Writer | `writing` | 12 skills, EQUATOR guidelines, PRISMA pipeline, claim verification |
| Faculty CMD | `faculty_tools` | 9 tabs: syllabus, lecture, slides, assignments, lab manuals (all dispatch to agent) |
| Molecular Toolkit (shared) | `molecular_similarity` | Tanimoto similarity screening |
| Chemical Space | `chemical_space_map` | PCA/t-SNE visualization of compound libraries |

## Inter-Module Handoffs
The platform includes a `webui/js/handoff.js` system enabling one-click result transfer between modules:
- Docking results → ADMET / QSAR / Retrosynthesis / Bioactivity
- Retrosynthesis precursors → Reaction Lab / ADMET / Docking
- Reaction products → Retrosynthesis / ADMET / Docking
- Generated molecules → ADMET / Docking / Bioactivity / Retrosynthesis

## API Access Pattern
All modules are accessible as REST endpoints at `/api/<handler_name>`:
```python
import requests
# CSRF token required for POST
resp = requests.post("http://localhost/api/qsar3d",
    json={"action": "predict", "smiles": "CCO"},
    headers={"X-CSRF-Token": "...", "Origin": "http://localhost"})
```

The agent can invoke any module programmatically via `code_execution_tool` by making HTTP calls to these endpoints, or by importing the module directly from `modules/` or `api/`.
