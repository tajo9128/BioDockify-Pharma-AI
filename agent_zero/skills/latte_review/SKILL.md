---
name: LatteReview (Systematic Review Automation)
description: |
  Automates systematic literature reviews using multi-agent AI workflows.
  Can perform title/abstract screening, full-text screening, and data abstraction.
author: Agent Zero Team (Integration of PouriaRouzrokh/LatteReview)
version: 1.0.0
---

# LatteReview Skill

This skill integrates the [LatteReview](https://github.com/PouriaRouzrokh/LatteReview) framework to allow Agent Zero to perform PhD-level systematic reviews.

## Capabilities

1.  **Screening**: Filter papers based on inclusion/exclusion criteria.
2.  **Scoring**: Verify relevance with confidence scores.
3.  **Abstraction**: Extract structured data points from papers.

## Usage in Agent Zero

```python
from agent_zero.skills.latte_review import get_latte_review
latte = get_latte_review()

# Define Criteria
inclusion = "Studies using AI for drug discovery in oncology."
exclusion = "Review articles, non-English papers."

# Run Screening
output_csv = latte.screen_papers(
    input_path="data/papers/candidates.csv", # Must have 'title' and 'abstract' columns
    inclusion_criteria=inclusion,
    exclusion_criteria=exclusion
)
print(f"Screening complete. Results saved to {output_csv}")
```

## Configuration

The skill uses `LiteLLM` under the hood. It will inherit the API keys from the Agent Zero environment (e.g., `OPENAI_API_KEY`, `GEMINI_API_KEY`).
