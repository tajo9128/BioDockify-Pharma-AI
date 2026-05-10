---
name: Achademio (Academic Writing Assistant)
description: |
  Improves research paper quality via academic rewriting, summarization, and proofreading.
author: Agent Zero Team (Integration of TajaKuzman/Achademio)
version: 1.0.0
---

# Achademio Skill

This skill integrates [Achademio](https://github.com/TajaKuzman/Achademio) to help Agent Zero refine academic prose.

## Capabilities

1.  **Academic Rewrite**: Transform informal text into eloquent academic style.
2.  **Slide Summarization**: Generate bullet points for presentation slides from research text.
3.  **Bullet-to-Paragraph**: Convert rough bullet points into cohesive academic paragraphs.
4.  **Proofreading**: Detect errors and suggest corrections with diff highlights.

## Usage in Agent Zero

```python
from agent_zero.skills.achademio import get_achademio
achademio = get_achademio()

# Rewrite text
refined = achademio.rewrite("AI is getting better at drug stuff.")
print(f"Academic Version: {refined}")
```
