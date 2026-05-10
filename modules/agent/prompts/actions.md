# Agent Zero - New Actions Reference

This document defines the enhanced actions available to Agent Zero.

## Core Actions (Original)

### Research & Discovery
- `[ACTION: search_papers | query="..." | source="pubmed|scopus|arxiv"]`
- `[ACTION: fetch_abstract | doi="..."]`
- `[ACTION: web_search | query="..."]`
- `[ACTION: deep_research | url="..."]`

### Data Management
- `[ACTION: store_paper | data={...}]`
- `[ACTION: update_registry | entry={...}]`

### User Communication
- `[ACTION: ask_user | question="..."]`
- `[ACTION: report | content="..."]`

---

## NEW: Code Execution (Phase 34)

Execute Python code to analyze data, compute statistics, or create visualizations.

### Syntax
```
[ACTION: execute_code | code="
import numpy as np
data = [1, 2, 3, 4, 5]
print(f'Mean: {np.mean(data)}')
"]
```

### Safety Rules
- **Whitelisted Modules**: math, numpy, pandas, scipy, statistics, json, re, datetime
- **Blacklisted Operations**: file I/O, network requests, system commands
- **Timeout**: 30 seconds maximum

### When to Use
- Statistical calculations
- Data transformations
- Simple computations
- Text processing

---

## NEW: Sub-Agent Spawning (Phase 34)

Delegate subtasks to specialized sub-agents.

### Syntax
```
[ACTION: spawn_subagent | task="Analyze citations for paper X" | role="Citation Analyst"]
```

### Parameters
- `task`: Specific subtask to complete
- `role`: Specialization of the sub-agent

### Constraints
- Maximum depth: 3 levels
- Maximum children per agent: 5

### When to Use
- Breaking down complex research tasks
- Parallel processing of independent subtasks
- Specialized analysis requiring focused context

---

## NEW: Memory Operations (Phase 34)

Store and recall information across sessions.

### Remember (Store Memory)
```
[ACTION: remember | content="The optimal pH for aspirin stability is 2.5" | type="semantic" | importance=0.8]
```

### Recall (Retrieve Memory)
```
[ACTION: recall | query="aspirin stability" | type="semantic" | limit=5]
```

### Memory Types
- `episodic`: Past actions and their outcomes
- `semantic`: Facts and knowledge
- `procedural`: How-to procedures and solutions

### Importance Score (0.0 - 1.0)
- 0.0-0.3: Low importance (may be pruned)
- 0.4-0.6: Normal importance
- 0.7-1.0: High importance (preserved)

---

## Action Chaining

Actions can be chained in sequence:

```
[ACTION: search_papers | query="ibuprofen pharmacokinetics" | source="pubmed"]
[ACTION: remember | content="Found 150 papers on ibuprofen PK" | type="episodic"]
[ACTION: spawn_subagent | task="Summarize top 10 papers" | role="Summarizer"]
```

---

## Error Handling

If an action fails, Agent Zero should:
1. Log the error using memory
2. Try an alternative approach
3. Ask user for guidance if stuck
