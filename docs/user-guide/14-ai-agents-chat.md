# Chapter 14: AI Agents & Chat Interface

## 14.1 Overview
BioDockify uses a multi-agent cooperation model where 4 specialized sub-agents handle different research domains.

### Access Path
**Chat panel** (left side in Chat/Split mode)

---

## 14.2 The 4 Sub-Agents

| Agent | Specialization | Tools |
|-------|---------------|-------|
| **Researcher** | Literature search, knowledge synthesis | 10 databases, ChromaDB, web search |
| **Biostatistician** | Statistical analysis, data interpretation | 20 analysis types, 8 charts |
| **Writer** | Academic writing, formatting, citations | Paper, thesis, grant, slides |
| **Hacker** | Code execution, data processing, system tasks | Terminal, file I/O, Python |

---

## 14.3 How Agents Cooperate

1. User sends request via chat
2. Main orchestrator analyzes intent
3. Dispatches to appropriate sub-agent(s)
4. Sub-agents execute and return results
5. Orchestrator synthesizes final response

---

## 14.4 Chat Commands

| Command | Action |
|---------|--------|
| "Dock aspirin against COX-2" | Opens Molecular Toolkit, runs docking |
| "Run QSAR on this CSV" | Opens QSAR Modeler, processes dataset |
| "Find a journal for my paper" | Opens Journal Finder |
| "Write a literature review on CRISPR" | Opens Academic Writer |
| "Analyze this data" | Opens Statistics |
| "Check this molecule" | Opens Molecule Editor |

---

## 14.5 LLM Provider Configuration

| Provider | Setup |
|----------|-------|
| OpenRouter | Set `OPENROUTER_API_KEY` in `.env` |
| OpenAI | Set `OPENAI_API_KEY` |
| Anthropic | Set `ANTHROPIC_API_KEY` |
| Ollama | Run Ollama locally, set `OLLAMA_HOST` |

---

## 14.6 Agent Memory

- **Session memory**: Current conversation context
- **Knowledge base**: ChromaDB vector store (persistent)
- **Cross-run evolution**: Ebbinghaus 30-day decay model
- **Project context**: Per-project memory isolation
