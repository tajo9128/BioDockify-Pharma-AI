"""Reviewer agent implementation with consistent error handling and type safety."""

from typing import List, Dict, Any, Optional
from .basic_reviewer import BasicReviewer, AgentError

DEFAULT_MAX_RETRIES = 3

generic_prompt = """

**Review the input item below and complete the scoring task as instructed:**

---

**Input item:**
<<${item}$>>

**Scoring task:**
<<${scoring_task}$>>

---

**Instructions:**

1. **Score** the input item using only the values in this set: ${scoring_set}$.
2. Follow these rules when determining your score: <<${scoring_rules}$>>.
3. After assigning a score, report your certainty level as a value between **0** (not certain at all) and **100** (completely certain).
4. Report your certainty level after you assigned a score.

---

${reasoning}$

${additional_context}$

${examples}$

"""


class ScoringReviewer(BasicReviewer):
    generic_prompt: Optional[str] = generic_prompt
    response_format: Dict[str, Any] = {"reasoning": str, "score": int, "certainty": int}
    input_description: str = "article title/abstract"
    scoring_task: Optional[str] = None
    scoring_set: List[int] = [1, 2]
    scoring_rules: str = "Your scores should follow the defined schema."
    reasoning: str = "brief"
    max_retries: int = DEFAULT_MAX_RETRIES

    def model_post_init(self, __context: Any) -> None:
        """Initialize after Pydantic model initialization."""
        try:
            assert self.reasoning != None, "Reasoning type cannot be None for ScoringReviewer"
            self.setup()
        except Exception as e:
            raise AgentError(f"Error initializing agent: {str(e)}")
