"""Reviewer agent implementation with consistent error handling and type safety."""

from typing import Dict, Any, Optional
from .basic_reviewer import BasicReviewer, AgentError

DEFAULT_MAX_RETRIES = 3

generic_prompt = """

**Review the input item below and extract the specified keys as instructed:**

---

**Input Item:**  
<<${item}$>>

**Keys to Extract and Their Expected Formats:**  
<<${abstraction_keys}$>>

---

**Instructions:**  

Follow the detailed guidelines below for extracting the specified keys:  

<<${key_descriptions}$>>

---

${additional_context}$

${examples}$

"""


class AbstractionReviewer(BasicReviewer):
    generic_prompt: Optional[str] = generic_prompt
    input_description: str = "article title/abstract"
    abstraction_keys: Dict
    key_descriptions: Dict
    max_retries: int = DEFAULT_MAX_RETRIES

    def model_post_init(self, __context: Any) -> None:
        """Initialize after Pydantic model initialization."""
        try:
            assert self.reasoning == None, "Reasoning type should be None for AbstractionReviewer"
            self.response_format = self.abstraction_keys
            self.setup()
        except Exception as e:
            raise AgentError(f"Error initializing agent: {str(e)}")
