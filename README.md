# BioDockify AI

**BioDockify AI** is a modified pharmaceutical research distribution built on top of [Agent Zero](https://github.com/agent0ai/agent-zero) — an open-source agentic framework created and maintained by [Jan Tomasek](https://github.com/Xrenel) and the Agent Zero team.

> **This is a fork/modification of Agent Zero.** BioDockify AI is not a standalone product. It is a customized rebranding and domain-specific tuning of the Agent Zero framework, adapted for pharmaceutical research and drug discovery use cases. All core framework functionality belongs to the Agent Zero project.

## Acknowledgments

We gratefully thank the **Agent Zero team** and the open-source community for making Agent Zero freely available under an open-source license. Their commitment to open, transparent, and modifiable AI software makes projects like BioDockify AI possible.

- **Original Project**: [github.com/agent0ai/agent-zero](https://github.com/agent0ai/agent-zero)
- **Original Author**: Jan Tomasek
- **License**: Open source — see the original Agent Zero repository for license details

## What BioDockify AI Adds

BioDockify AI layers extensive pharmaceutical research capabilities on top of Agent Zero:

### Sub-Agents (5 Specialized Agents)

| Agent | Role |
|-------|------|
| **Agent0** | Main brain - orchestrates all sub-agents and modules |
| **Researcher** | Deep research, literature synthesis, data analysis, web scraping |
| **Biostatistician** | Statistical analysis, clinical trials, hypothesis testing, PK/PD |
| **Writer** | Academic writing, thesis, papers from research data |
| **Hacker** | Content acquisition when blocked, technical tasks |

### Research Backend Modules

| Module | Capabilities |
|--------|-------------|
| **Statistics** | 70+ statistical methods - t-tests, ANOVA, regression, survival analysis, bioequivalence |
| **Literature** | 14+ sources - PubMed, Semantic Scholar, Europe PMC, Crossref, bioRxiv, OpenAlex |
| **WetLab** | Lab experiment tracking and coordination |
| **Thesis** | PhD thesis management and tracking |
| **Proactive Guidance** | Research phase suggestions and workflow optimization |
| **Auto Research Orchestrator** | Full research pipeline automation |
| **Faculty Materials** | Course materials and presentation generation |
| **Slides** | PowerPoint-style presentation generation |
| **Publication** | LaTeX export for academic papers |

### Frontend UI (6 Research Tool Modals)

| Modal | Capabilities |
|-------|-------------|
| **Research Tools** | Hub for all research tools |
| **Statistics** | 8 analysis types - Descriptive, T-Test, ANOVA, Correlation, Regression, Survival, Power Analysis, PK/PD |
| **Literature** | 8 databases - PubMed, Semantic Scholar, Europe PMC, Crossref, bioRxiv, PubChem, Scopus, Web of Science |
| **Thesis** | 6-chapter tracker with LaTeX export |
| **Slides** | 4 themes - Default, Scientific, Corporate, Creative |
| **Wet Lab** | Experiment tracking - PCR, ELISA, Western Blot, Cell Culture, FACS, Microscopy |
| **Knowledge** | Q/A knowledge base with JSON export |

### Frontend UI Features

- **BioDockify-branded sidebar** with Research Tools dropdown menu
- **Statistics modal** for quick analysis access
- **Dark/light theme** with teal/cyan (#00d4aa) accent colors
- **Docker Desktop-inspired** visual identity
- **DNA double-helix favicon**

## Quick Start

```bash
docker run -d -p 80:80 --name biodockify \
  -v biodockify_usr:/usr \
  tajo9128/biodockify-pharma-ai:latest
```

Or run with a specific version:

```bash
docker run -d -p 80:80 --name biodockify \
  -v biodockify_usr:/usr \
  tajo9128/biodockify-pharma-ai:v1.23
```

Then open [http://localhost](http://localhost) in your browser.

## Features (Inherited from Agent Zero)

- Multi-agent cooperation with subordinate delegation
- Browser automation and web research
- Code execution in Python, Node.js, and Bash
- Persistent memory and knowledge management
- File management and document querying
- Scheduled tasks and automation
- MCP (Model Context Protocol) client and server
- External REST API for programmatic access
- Plugin system with extensible architecture
- Project-based workspace isolation
- Time travel (chat history)
- Model configuration (OpenAI, Anthropic, local LLMs)
- Office document handling

## Agent Workflow

```
User Request
     ↓
Agent0 (Main Brain)
     ↓
├─→ Researcher ─→ Hacker (if blocked)
│         ↓
│    Biostatistician (stats)
│         ↓
└─→ Writer (output)
```

## Research Database Access

The Researcher agent has access to:

### Literature & Publications
- **PubMed** - Biomedical literature (NLM)
- **PubMed Central** - Full-text articles
- **Semantic Scholar** - AI-powered academic search
- **Europe PMC** - European literature archive
- **Crossref** - DOI metadata
- **bioRxiv** - Biology preprints
- **medRxiv** - Medicine preprints
- **OpenAlex** - Open research graph
- **Scopus** - Abstract/indexed literature (Elsevier)
- **Web of Science** - Citation index (Clarivate)

### Chemistry & Drugs
- **PubChem** - Chemical compounds (NIH)
- **ChEMBL** - Bioactivity data (EBI)
- **DrugBank** - Drug information

### Clinical & Research
- **ClinicalTrials.gov** - Clinical trials registry
- **ClinicalTrials.gov EU** - EU clinical trials

### Knowledge
- **SurfSense** - Knowledge graph storage

## License

This project is a modification of Agent Zero. See [Agent Zero repository](https://github.com/agent0ai/agent-zero) for original license.