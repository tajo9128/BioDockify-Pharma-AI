# BioDockify Pharma AI v7.0.0 — User Guide

## Complete Documentation: 28 Chapters + 4 Appendices

---

### Part I: Getting Started (Chapters 1-3)

| Ch | Title | Content |
|----|-------|---------|
| 1 | [Installation & Quick Start](01-installation-quick-start.md) | Docker Desktop setup, first launch, health verification, data persistence, backup |
| 2 | [Interface Navigation](02-interface-navigation.md) | Layout modes, toolbar, All Tools grid, module windows, keyboard shortcuts |
| 3 | [Molecule Editor](03-molecule-editor.md) | 3D view, properties, PAINS/Brenk filters, bioisostere optimization |

### Part II: Research Modules (Chapters 4-10)

| Ch | Title | Content |
|----|-------|---------|
| 4 | [Molecular Toolkit & Docking](04-molecular-toolkit-docking.md) | SwissADME, Vina+GNINA docking, consensus Z-score, ProLIF fingerprints, 3D analysis |
| 5 | [QSAR Modeler](05-qsar-modeler.md) | 9 ML models, feature selection, Williams Plot, read-across, batch prediction |
| 6 | [Pharmacophore](06-pharmacophore.md) | 13 actions, ZINCPharmer batch screen, LigandScout import, NCI types |
| 7 | [Journal Finder](07-journal-finder.md) | 36,145 journals, deep research, fake website detector, full dossier |
| 8 | [Academic Writer](08-academic-writer.md) | Paper, thesis, grant, regulatory, citations, lecture, slides |
| 9 | [Faculty Command Center](09-faculty-cmd.md) | Syllabus, lectures, assignments, plagiarism, slides |
| 10 | [Statistics Suite](10-statistics.md) | 20 analysis types, 8 charts, data transformation |

### Part III: System & Analysis (Chapters 11-15)

| Ch | Title | Content |
|----|-------|---------|
| 11 | [Knowledge Base](11-knowledge-base.md) | ChromaDB vector store, semantic search, knowledge graph |
| 12 | [System Administration](12-system-admin.md) | Health, backup, Docker commands, cloud deployment |
| 13 | [Benchmark Suite](13-benchmark.md) | System validation, dependency checks |
| 14 | [AI Agents & Chat](14-ai-agents-chat.md) | 4 sub-agents, chat commands, LLM providers |
| 15 | [Docker & Deployment](15-docker-deployment.md) | Architecture, volumes, ports, cloud deployment |

### Part IV: Technical Reference (Chapters 16-17)

| Ch | Title | Content |
|----|-------|---------|
| 16 | [Computational Methods](16-computational-methods.md) | Scoring functions, descriptors, pharmacophore features, drug property algorithms |
| 17 | [Plugin System](17-plugin-system.md) | Plugin architecture, discovery, frontend components, extensions |

### Part V: Tutorials (Chapters 18-21)

| Ch | Title | Content |
|----|-------|---------|
| 18 | [Tutorial: Virtual Screening](18-tutorial-virtual-screening.md) | End-to-end COX-2 flavonoid screening campaign |
| 19 | [Tutorial: QSAR Building](19-tutorial-qsar-building.md) | BBB permeability classifier with OECD validation |
| 20 | [Tutorial: Pharmacophore Design](20-tutorial-pharmacophore-design.md) | CDK2 inhibitor discovery via pharmacophore |
| 21 | [Tutorial: PhD Pipeline](21-tutorial-phd-pipeline.md) | Full research pipeline from question to publication |

### Part VI: Regulatory & Ethics (Chapters 22-23)

| Ch | Title | Content |
|----|-------|---------|
| 22 | [Regulatory Science](22-regulatory-science.md) | FDA/EMA, ICH guidelines, OECD QSAR principles, bioequivalence |
| 23 | [Research Integrity](23-research-integrity.md) | Hijacked journals, fake websites, AI disclosure, responsible use |

### Part VII: Reference (Chapters 24-28)

| Ch | Title | Content |
|----|-------|---------|
| 24 | [Quick Reference](24-quick-reference.md) | Keyboard shortcuts, SMILES cheatsheet, common PDB codes |
| 25 | [API Endpoint Table](25-api-endpoint-table.md) | Complete REST API reference for all modules |
| 26 | [References & Citations](26-references.md) | Academic references for all algorithms and methods |
| 27 | [Project Structure](27-project-structure.md) | Directory layout, Docker volumes, file organization |
| 28 | [Version History](28-version-history.md) | Release history, roadmap, contributing guide, citation |

### Appendices

| App | Title | Content |
|-----|-------|---------|
| A | [API Reference](appendix-a-api-reference.md) | Endpoint catalog with request/response formats |
| B | [Glossary](appendix-b-glossary.md) | 35 terms defined |
| C | [Troubleshooting](appendix-c-troubleshooting.md) | Problem-solution pairs by module |
| D | [Data Formats](appendix-d-data-formats.md) | SMILES, PDB, PDBQT, SDF, CSV, .pm specifications |

---

## Platform Info

| Property | Value |
|----------|-------|
| Version | v7.0.0 |
| Docker Image | `tajo9128/biodockify-pharma-ai:v7.0.0` |
| Tech Stack | Python 3.12+ · Flask · Alpine.js · RDKit · AutoDock Vina · GNINA |
| GitHub | https://github.com/tajo9128/BioDockify-Pharma-AI |
| Modules | 15 consolidated |
| API Endpoints | 60+ |
| Documentation | 28 chapters + 4 appendices |
