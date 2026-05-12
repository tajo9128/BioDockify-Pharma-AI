---
name: ScholarCopilot (Academic Writing Copilot)
description: |
  Intelligent assistant for text completion and citation suggestions based on ArXiv corpus.
author: Agent Zero Team (Integration of TIGER-AI-Lab/ScholarCopilot)
version: 1.0.0
---

# ScholarCopilot Skill

This skill integrates [ScholarCopilot](https://github.com/TIGER-AI-Lab/ScholarCopilot) to provide smart text completions and citation retrieval.

## Capabilities

1.  **Smart Completion**: Predict the next sentences in an academic paper context.
2.  **Citation Search**: Suggest relevant ArXiv papers based on the current writing context.

## Usage in Agent Zero

```python
from agent_zero.skills.scholar_copilot import get_scholar_copilot
copilot = get_scholar_copilot()

# Complete text
completion = copilot.complete("Large language models have revolutionized...")
print(f"Suggested text: {completion}")
```

## Note
Requires local model weights and ArXiv FAISS index.
