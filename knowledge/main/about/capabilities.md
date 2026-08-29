# BioDockify Pharma AI v7.0.0 - Capabilities Reference

## Code Execution

The agent can write and execute code in any language available in the Docker container. The execution environment is a Kali Linux container with two Python runtimes:
- `/opt/venv-a0` (Python 3.12) - the BioDockify AI framework runtime
- `/opt/venv` (Python 3.13) - the agent's execution runtime (default for agent-run code)

The agent installs packages into the execution runtime (`/opt/venv`) via `pip install`. Packages needed by the framework itself must target `/opt/venv-a0`.

Supported runtimes for code execution: Python, Node.js, Bash/shell. Other languages (Go, Rust, PHP, etc.) can be used if the compiler/runtime is installed in the container.

Code runs in the terminal with real-time output streaming. Long-running processes, background jobs, and interactive sessions are supported. The agent can pause and resume code execution and interact with running processes.

## Terminal and System Operations

The agent has full root access to the Kali Linux Docker container. It can:
- Install packages via `apt`, `pip`, `npm`, and other package managers
- Create, read, write, move, and delete files anywhere in the container
- Run any system command, manage processes, set up services
- Access the network (HTTP requests, SSH, port scanning, etc.)
- Use Kali Linux security tools pre-installed in the container

## Skills (SKILL.md Standard)

Skills are structured markdown files that provide contextual expertise for specific tasks. When a skill is relevant to the current task, it is loaded into the agent's context and followed as a set of instructions. Skills are discovered from:
- `usr/skills/` (user-added skills)
- Project-scoped skills in `.a0proj/skills/`
- Skills imported via the web UI

Skills follow the open SKILL.md standard, making them portable across tools that support it. The agent executes skill instructions using `code_execution_tool` or `skills_tool`.

## Projects

Projects provide isolated workspaces with their own:
- Working directory (`usr/projects/<name>/`)
- Memory and knowledge scope
- Custom agent instructions (`.a0proj/agent.instructions.md`)
- Secrets and credentials (stored encrypted, not visible in agent context)
- MCP server configurations
- Git repository (can be cloned directly with authentication)

When a project is active, the agent's file operations, memory, and knowledge are scoped to that project. Projects prevent context bleed between separate work streams.

## Knowledge Base Access

The agent has automatic access to its knowledge base via similarity search. Knowledge is indexed from `knowledge/` (framework-level) and `usr/knowledge/<subdir>/` (user-level). The agent does not need to explicitly query knowledge - relevant content is surfaced automatically with memory recall. The `knowledge_tool` can also be called explicitly for targeted lookups.

## Multi-Agent Delegation

The agent can spawn subordinate agents with the `call_subordinate` tool. Subordinates can be given:
- Specific prompt profiles (`developer`, `researcher`, custom profiles)
- A defined role and task scope
- Access to the same tool set

Delegation is used to: parallelize work, maintain clean context per task, apply specialized profiles, and isolate long subtasks from the main context.

## Document Query

The `document_query_tool` can load and query arbitrary documents (local files or URLs) using a separate RAG pipeline. Unlike the knowledge base (which is pre-indexed), this tool indexes documents on demand with a configurable chunk size. Useful for analyzing large documents, codebases, or external content without polluting the persistent knowledge store.

## Scheduler

The agent can schedule tasks to run at specified times or intervals using the scheduler tool. Scheduled tasks run in the background with their own agent instances. Tasks are managed via the Scheduler UI in the web interface.

## External API and MCP

BioDockify Pharma AI can act as both an MCP server and an MCP client:
- As an **MCP server**: exposes agent capabilities to other MCP-compatible clients
- As an **MCP client**: uses tools from external MCP servers (configured per project or globally)

An external REST API is available for programmatic task submission. Agent-to-Agent (A2A) protocol is supported for inter-system agent communication.

## Limitations

- **No persistent state between chats** unless explicitly memorized or saved to files.
- **Context window**: long conversations are summarized automatically, which can lose detail.
- **Memory recall is approximate**: similarity search may miss relevant memories or surface irrelevant ones.
- **No GUI interaction** outside built-in browser tooling or configured computer-use integrations.
- **Container boundary**: the agent cannot affect systems outside the Docker container unless network access or volume mounts are configured.

## MD Lite — Molecular Dynamics

The agent can manage long-running OpenMM molecular dynamics simulations via the MD Lite module:

- **24-48 hour background runs**: Simulations execute in background threads with automatic checkpoint/resume. Container can restart, PC can sleep — simulation continues from last checkpoint.
- **Auto-monitoring**: Agent periodically checks simulation progress (ns completed, percentage, GPU status) and alerts user on completion.
- **Result gathering**: On completion, agent automatically collects RMSD/RMSF/Energy plots and values, generates scientific interpretation, and saves to Knowledge Base.
- **GPU-first architecture**: Auto-detects CUDA GPU (10-50x faster), falls back to OpenCL, then CPU. User can override.
- **Import from docking**: MD simulations can use protein-ligand complexes from the Molecular Toolkit docking module.

## Pre-Installed Python Environment

The following statistical and scientific packages are pre-installed and ready to use — NEVER run `pip install` for them:

- `numpy`, `scipy`, `pandas`, `statsmodels`, `scikit-learn`, `matplotlib`, `seaborn`, `rdkit`

If you need additional packages, use `pip install` only for packages NOT in this list.
- **Model capability ceiling**: tool usage quality and reasoning depth are bounded by the underlying LLM. Small models may struggle with complex multi-step tool use.
- **No real-time data** beyond web search. The agent's own knowledge cutoff is the underlying model's training cutoff.

## Molecular Docking & Analysis

### AutoDock Vina Docking
The Docking Studio module (Molecular Toolkit → Docking tab) runs full AutoDock Vina docking:
- Input: Protein structure (PDB/PDBQT/CIF/MOL2/ENT) + Ligand (SMILES/SDF/MOL/PDB/MOL2)
- Auto-detects binding site center from atom coordinates and computes optimal grid size
- Returns docked poses sorted by binding energy (most negative = strongest binding = 1st)
- Downloadable: docked_output.pdbqt, docked_poses.sdf, vina_log.txt

### MM-GBSA Free Energy Scoring (Auto-Chained)
After Vina completes, MM-GBSA scoring runs automatically (CPU-only, no GPU):
- Combines Vina MM term + GB desolvation + SA surface area + protein interaction bonus
- Per-pose MM-GBSA energies, Z-scores, and consensus with Vina (`0.4*Vina_Z + 0.6*MMGBSA_Z`)
- External upload: Upload receptor + ligand from any platform (Glide, GOLD, AutoDock-GPU, rDock, PLANTS)
- Use when: Free energy estimation needed for publication or high-confidence binding prediction

### Deep Docking Analysis (3Dmol.js + Interaction Analysis)
After docking, use the Deep Analysis panel (6-tab UI) for:
- **3D View**: All 16 MoleculeViewer features (cartoon/stick/sphere/line, chain coloring, surface, H-bond cylinders, snapshot PNG, 4 quick presets, zoom/spin controls)
- **2D Diagram**: RDKit-generated SVG interaction map with annotated H-bonds/Hydrophobic/Pi-stacking
- **Interactions**: Summary cards + expandable per-interaction details
- **Residue Energy**: Per-residue binding contribution bar chart (identifies key binding residues)
- **Clusters**: RMSD-based hierarchical clustering of poses
- **Torsion**: Dihedral angle analysis of ligand conformations

## QSAR Modeling (ML on Molecular Descriptors)
Train and predict using 6 ML models on 42 molecular descriptors across 4 groups:
- **Models**: RandomForest, GradientBoosting, SVR, PLS, Ridge, Lasso
- **Descriptors**: Physicochemical (MW, LogP, TPSA, etc.), Topological, Electronic, Fragment
- **CV metrics**: R², RMSE, MAE with k-fold cross-validation
- **Applicability domain**: Leverage-based in-domain/warning/out-of-domain assessment
- Use when: User wants to predict bioactivity, toxicity, solubility, or any quantitative endpoint from SMILES

## Pharmacophore Modeling
RDKit-based pharmacophore feature detection:
- **6 feature types**: H-bond Donor (blue), Acceptor (red), Hydrophobic (gold), Aromatic (purple), PosIonizable (green), NegIonizable (orange)
- **Input**: SMILES string → 3D conformer generation (ETKDG + MMFF) → feature extraction
- **Library screening**: Screen compound libraries against a pharmacophore query
- **Hypothesis generation**: Find common features across multiple active molecules
- **Exclusion volumes**: Generate receptor surface clash spheres
- Use when: User wants pharmacophore-based screening, feature visualization, or hypothesis from active compounds

## Molecular Optimization
AI-driven lead optimization with mutation strategies:
- **Bioisosteric replacement**: Carboxyl→Tetrazole, Ester→Amide
- **Group addition**: Hydroxyl, Fluorine, Methyl on aromatic rings
- **Ring expansion**: 5→6 membered rings
- **Flexible receptor docking**: Identify flexible residues (16 residue types with Dunbrack rotamer library)
- Each mutant shows calculated MW, LogP, HBD, HBA with "Dock This" action

## Advanced Drug-Likeness Filters
Beyond Lipinski Rule of 5:
- **PAINS**: 8 Pan-Assay Interference Compound substructures (false positives)
- **Brenk**: 10 undesirable functional groups (toxicity alerts)
- **NIH**: 8 unwanted substructures
- Use when: User wants to validate compounds for screening library suitability

## Benchmarking & Diagnostics
System integrity checks available via Benchmark plugin:
- Dependency checks: RDKit, NumPy, sklearn, Vina, MM-GBSA, OpenBabel
- API health: Response time and status code validation
- Storage: Disk free space check
- RDKit test: SMILES parsing and descriptor calculation validation

## SPSS Statistics Suite (20 Analysis Types)
BioDockify offers a comprehensive statistics module comparable to IBM SPSS:
- **Descriptive Statistics**: Mean, median, SD, min, max, quartiles, frequencies
- **Correlation**: Pearson, Spearman, Kendall with correlation heatmap
- **T-Test**: Independent, paired, Welch's (unequal variance)
- **ANOVA**: One-way with Tukey, Bonferroni, Dunnett, Scheffe post-hoc tests
- **Regression**: Linear, multiple, logistic, Poisson, negative binomial, stepwise (AIC/BIC forward/backward)
- **Non-Parametric**: Mann-Whitney U, Wilcoxon Signed Rank, Kruskal-Wallis, Friedman, Chi-Square, Fisher Exact, McNemar
- **Survival Analysis**: Kaplan-Meier, Log-Rank, Cox Proportional Hazards
- **Diagnostics**: Normality (Shapiro-Wilk, K-S, Anderson-Darling), Homogeneity (Levene, Bartlett), VIF, Outliers
- **Data Reduction**: PCA/Factor Analysis (eigenvalues, loadings, scree plot), Cronbach's Alpha reliability, K-Means + Hierarchical clustering with dendrogram
- **Data Transformation**: Compute variable (formula), Recode, Rank cases, Fill missing (mean/median/interpolate), Standardize (z-score/minmax/robust)
- **ROC Analysis**: AUC, optimal cutoff (Youden Index), sensitivity/specificity coordinates, DeLong comparison
- **Curve Estimation**: 11 models (linear through exponential, logistic, power, growth, s-curve)
- **Missing Value Analysis**: Patterns, per-column/per-row stats, mean imputation recommendations
- **Charts**: Histogram, boxplot, scatter, Q-Q plot, bar chart, ROC curve, survival curve, correlation heatmap — auto-generated base64 PNG from results
- **Power Analysis**: Sample size calculation for t-tests
- **PK/PD**: Non-compartmental analysis, AUC, Cmax/Tmax, half-life, bioavailability
- **Multiplicity Control**: Bonferroni, Holm, Benjamini-Hochberg FDR, Sidak
- **Bioequivalence**: TOST, crossover ANOVA
- **Meta-Analysis**: Fixed-effects and random-effects models with forest plots
- Use when: User needs statistical analysis of clinical/experimental data, normality checking, appropriate test selection, automated chart generation

## Autonomous Research Pipeline (25-Stage, 9-Phase)
A complete autonomous drug discovery workflow comparable to AutoResearchClaw:
- **Phase A — Scoping**: Topic decomposition, research question formulation
- **Phase B — Literature Discovery**: Multi-source search across 10 databases with PRISMA screening
- **Phase C — Molecular Analysis**: Drug properties, ADMET, PAINS/Brenk/NIH filters, pharmacophore detection
- **Phase D — QSAR**: Train/predict with 6 ML models, screen compound libraries
- **Phase E — Docking**: Vina → MM-GBSA scoring with deep analysis (3D, interactions, clusters)
- **Phase F — Statistics & Analysis**: Statistical testing, RMSD clustering, multi-perspective result analysis
- **Phase G — Decision**: PIVOT/REFINE/PROCEED auto-decision with rationale
- **Phase H — Writing**: Paper outline, section-by-section drafting, multi-agent peer review
- **Phase I — Finalization**: 5 quality gates, 5-layer citation verification, export to LaTeX/DOCX/slides
- Pipeline API: `POST /api/pipeline` (start, status, advance, retry, abort, history, stages)
- Quality Gates: Literature (≥5 papers), Molecular (Lipinski, PAINS, MW), Docking (≥3 poses, energy check), Statistical (significance, normality, effect size), Publication (citation integrity, IMRAD)
- Agent tool: `Pipeline action=start topic="..."`
- Use when: User wants end-to-end autonomous research from topic to paper

## Multi-Agent Debate System
Structured scientific debate for rigorous hypothesis testing:
- **Hypothesis Debate**: Pharmacologist vs Biostatistician vs Medicinal Chemist
- **Method Debate**: Docking vs QSAR vs Pharmacophore vs Literature Review
- **Results Debate**: Writer (interpretation) vs Biostatistician (statistical validity)
- Each produces: winner, rationale, dissenting opinion, confidence score
- Agent tool: `Debate action=hypothesis topic="..."`

## Self-Healing Execution (PIVOT/REFINE)
Autonomous error recovery for computational workflows:
- **Docking failures**: Grid expansion, exhaustiveness increase, MM-GBSA rescoring, PDBQT sanitizer
- **QSAR failures**: Model switch (RF→GBM→SVR→PLS→Ridge→Lasso), descriptor group expansion
- **Statistics failures**: Normality violation → non-parametric, variance → Welch correction
- **Literature failures**: Query expansion, database switch
- Max 3 retries per domain, then PIVOT to alternative method
- Agent tool: `SelfHeal action=analyze domain=docking error_type=no_poses`

## 5-Layer Citation & Claim Verification
Pharma-grade verification stack:
- Layer 1: PubMed ID validation via NCBI e-utilities
- Layer 2: CrossRef DOI resolution
- Layer 3: ClinicalTrials.gov NCT verification
- Layer 4: PubChem CID validation
- Layer 5: LLM relevance check (agent-performed)
- Claim extraction: numeric, statistical, significance claims auto-extracted from text
- Agent tool: `Verify action=verify text="..."`

## Human-in-the-Loop (HITL) Control
8 intervention modes for research oversight:
- Full Auto, Gate Only (3 gates), Checkpoint (9 phases), Co-Pilot, Step-by-Step, Express, Regulatory (ICH E9), Custom
- Gate approval/reject/collaborate/inject guidance
- Agent tool: `HITL action=approve pipeline_id=ID gate_id=5`

## Cross-Run Knowledge Evolution
Pharma knowledge retention across research sessions:
- 6 categories: target memory, compound memory, method memory, literature memory, failure patterns, quality lessons
- Ebbinghaus 30-day time decay for lesson relevance
- Auto-deduction from completed pipeline runs
- Agent tool: `Evolution action=store category=target lesson="..."`

## Literature Search (10 Databases)
Multi-source academic literature discovery:
- PubMed, Semantic Scholar, Google Scholar (citation-ranked), Scopus, Web of Science
- arXiv, Elsevier (ScienceDirect), Springer Nature, Europe PMC, bioRxiv/medRxiv
- Scopus/WoS/Elsevier/Springer use CrossRef proxy + 36,145-journal ISSN database for filtering
- PRISMA screening, BioNER entity extraction, APA/BibTeX citation export
- Agent tool: "Search PubMed for recent papers on EGFR inhibitors"

## Journal Recommender & Research Engine
Full journal intelligence suite:
- **Database**: 36,145 journals from Scopus (Mar 2025) + WoS (Mar 2024) master lists
- **Search**: Full-text search across title, ISSN, eISSN with Scopus/WoS/OA filters
- **Verify**: Multi-source legitimacy check (Scopus API, Clarivate MJL, SCImago JR, DOAJ API, local DB, hijacked journal database). Returns GENUINE/LIKELY_GENUINE/PREDATORY/UNVERIFIED with confidence score.
- **Profile/Dossier**: Comprehensive journal snapshot — publisher, indexing status, OA policy, APC, SCImago quartile, subjects, hijacked alert, verification verdict
- **History/Deep Research**: Provides research URLs for SCImago SJR trend, JCR Impact Factor, DOAJ policy, PubMed landmark papers, Google Scholar metrics. Agent can delegate to Hacker sub-agent for deeper web scraping.
- **Suggest**: Find journals for a paper using DB keyword search + Elsevier Journal Finder + JANE biosemantics, scored by relevance + authority + speed + access
- **Hijacked Check**: Cross-references against `data/integrity/hijacked_journals.json`
- **DB Stats**: Real-time counts of Scopus-indexed, WoS-indexed, Open Access journals
- Agent tool `JournalRecommender`: 7 actions (search, verify, profile, recommend, history, stats) — all execute real DB queries and live API calls
- Use when: User asks "verify this journal", "find me a journal", "give me the history of Journal X", "is this predatory?"

## Drug Analysis Module
Full-featured molecular analysis with 3D visualization:
- **SMILES Input**: Text input with validation (RDKit), Copy, debounced property/3D updates.
- **3Dmol.js Viewer**: 7 render styles (Stick, Ball+Stick, Sphere, Cartoon, Surface, Chain, Charge). Rotate/zoom/pan. 3D conformer from RDKit ETKDG+MMFF.
- **Property Panel**: Realtime MW, LogP, TPSA, HBD, HBA, Rotatable Bonds, Lipinski Rule-of-5, hERG, AMES, pKa, BBB, melting point, druglikeness score.
- **Substructure Filters**: PAINS, Brenk, NIH alerts.
- **Bioisostere Optimization**: Mutagenesis strategies for lead optimization.
- **PubChem Search**: Type compound name → resolves to SMILES via PubChem PUG REST → auto-loads.
- **Export**: PNG (RDKit 2D), SVG (RDKit 2D), MOL file, SDF 3D via `/api/structure_export`.
- **Send To**: Cross-module SMILES injection to Docking and ADMET tabs.
- **History**: Last 10 molecules in localStorage with quick-reload.
- **Quick Load**: 6 drug examples (Aspirin, Caffeine, Ibuprofen, Glucose, Sildenafil, Paracetamol).
- **File Upload**: Parses .sdf, .mol, .pdb, .smi, .smiles.
- Backend APIs: `structure_3d` (conformer), `structure_export` (multi-format), `pubchem_lookup` (name→SMILES), `drug_properties` (extended properties).

## Vina/PDBQT Failure Prevention
Self-healing PDBQT pipeline:
- **Deep validation**: Checks charge column (71-76) and atom type column (78-79) on every ATOM/HETATM record before Vina
- **Auto-sanitizer**: Fixes blank charges → 0.00, replaces invalid atom types from element inference (C→C, O→OA, N→NA, H→HD, S→SA, etc.), pads short lines to 80 columns
- **3-layer defense**: Prepare validate → Run validate → Sanitize → Re-validate → Vina subprocess
- Vina `parse_pdbqt.cpp(69)` crash is now impossible — malformed PDBQT is detected and auto-fixed before reaching the binary

## Research Management System
Full research lifecycle management via `/api/research/management/`:
- **Save/Load Research State**: Persist research progress (topic, stage, tasks, progress 0.0-1.0)
- **Research Dashboard**: Comprehensive view including tasks, milestones, wet lab experiments, thesis progress
- **Thesis Milestone Tracking**: Track PhD milestones (proposal, literature review, experiments, defense) with status and deadlines
- **Wet Lab Coordination**: Track experiments (planned/running/completed), protocols, reagent inventory, timelines
- **Project Listing**: List all saved research projects with progress indicators
- **Cross-Session Persistence**: Research state survives container restarts (saved to `/a0/usr/projects/`)

## Progress Tracking
- **Task Management**: Create, update, complete research tasks with priority and status
- **Milestone Progress**: Track thesis milestones (proposal, lit review, experiments, defense)
- **Wet Lab Status**: Experiment status (planned/running/completed/failed), protocol management
- **Research Dashboard**: Real-time view of all active research projects

## Knowledge Base — Central Hub
The Knowledge Base is the SINGLE SOURCE OF TRUTH for all research data. ALL modules store their outputs here, and ALL output modules read from here.

**Storage Paths (CRITICAL):**
- `/a0/data/knowledge_base/{category}/` — Primary KB storage (categories: literature, deep_research, faculty, docking, drug_analysis, pharmacophore, qsar, statistics, clinical_trials, patents, notes, misc)
- `/a0/data/knowledge_base/index.json` — Master index file (must be updated when adding entries)
- `/a0/usr/knowledge/main/` — Framework knowledge files
- `/a0/usr/knowledge/custom/` — User/agent knowledge files (also scanned by vector DB)

**Data Flow IN (store with category):**
- Deep Research → `deep_research` category
- Literature Search → `literature` category
- Faculty CMD → `faculty` category
- Docking → `docking` category
- Drug Analysis → `drug_analysis` category
- Pharmacophore → `pharmacophore` category
- QSAR → `qsar` category
- Statistics → `statistics` category
- Clinical Trials → `clinical_trials` category
- Patents → `patents` category

**API Actions:** store, library, categories, query, reindex, status

**When to store data:**
- ALWAYS store research results after deep research or literature search
- ALWAYS store faculty materials after generation
- ALWAYS store analysis results after docking, QSAR, or pharmacophore
- Use `callJsonApi("knowledge", { action: "store", category, title, content, tags, source })`
- For bulk imports, use `action: "import_files"` with file array

## Internet-Based Features
The agent has FULL INTERNET ACCESS for:
- **Literature Search**: Live queries to PubMed, Semantic Scholar, Google Scholar, arXiv, Europe PMC, bioRxiv, Crossref, OpenAlex
- **Clinical Trials**: Live search of ClinicalTrials.gov (v2 API)
- **Patent Search**: Espacenet + Google Patents
- **Web Scraping**: Use search_engine tool for real-time web data (prices, news, latest research)
- **Journal Verification**: Live checks against Scopus, WoS, DOAJ, SCImago APIs
- **PubChem Lookup**: Live compound data from PubChem PUG REST API
- **Drug Properties**: Real-time calculation from SMILES using RDKit
- **Deep Research**: Collect thousands of papers from 5+ databases, scan for relevance, store to knowledge base
