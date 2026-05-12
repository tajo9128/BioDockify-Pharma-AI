"""
Achademio Integration Wrapper
"""
import os
import sys
from typing import Optional, List, Dict, Any
from loguru import logger
from pathlib import Path
import threading
try:
    from redlines import Redlines
    REDLINES_AVAILABLE = True
except ImportError:
    REDLINES_AVAILABLE = False

# we don't need to import Achademio as it's a streamlit app with functions using openai.
# instead, we reimplement the logic using LiteLLM to stay consistent with other skills.

class AchademioSkill:
    """
    Skill wrapper for Achademio academic writing assistance.
    """
    def __init__(self):
        self.default_model = os.getenv("ACHADEMIO_MODEL", "gpt-4o-mini")
        try:
            import litellm
            self.litellm = litellm
        except ImportError:
            logger.warning("litellm not installed. Achademio skill requires litellm.")
            self.litellm = None

    def _call_llm(self, bot_role: str, user_prompt: str) -> str:
        """Helper to call LLM via LiteLLM."""
        if not self.litellm:
             return "Error: litellm not available."
        
        try:
            response = self.litellm.completion(
                model=self.default_model,
                messages=[
                    {"role": "system", "content": bot_role},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return f"Error: {e}"

    def rewrite_academic(self, text: str) -> str:
        """Rewrite text in academic style."""
        bot_role = "You are AChatdemio, a bot that helps young researchers to write better research papers. You respond in a clear, concise and academic style."
        user_prompt = f"Rewrite the following text, delimited by triple backticks, in academic style: ```{text}```"
        return self._call_llm(bot_role, user_prompt)

    def bullets_to_paragraph(self, bullets: str) -> str:
        """Convert bullet points to a cohesive academic paragraph."""
        bot_role = "You are AChatdemio, a bot that helps young researchers to write better research papers. You respond in a clear, concise and academic style."
        user_prompt = f"Provide one paragraph of text from the following bullet point list, delimited by triple backticks: ```{bullets}```"
        return self._call_llm(bot_role, user_prompt)

    def text_to_slides(self, text: str) -> str:
        """Prepare text for PowerPoint slides as bullet points."""
        bot_role = "You are AChatdemio, a bot that helps young researchers to write better research papers. You respond in a clear, concise and academic style."
        user_prompt = f"Prepare text for powerpoint slides in form of bullet points from the following text, delimited by triple backticks. The bullet points should summarize the provided texts in a few sentences. End each sentence with a dot. Text: ```{text}```"
        return self._call_llm(bot_role, user_prompt)

    def proofread(self, text: str) -> Dict[str, Any]:
        """Proofread text and find errors."""
        bot_role = "You are AChatdemio, a bot that helps young researchers to write better research papers. You respond in a clear, concise and academic style."
        user_prompt = f"Find errors in the following text, delimited by triple backticks: ```{text}```. Only output the errors and suggest how they should be corrected."
        
        corrections = self._call_llm(bot_role, user_prompt)
        
        result = {
            "corrections": corrections,
            "diff_markdown": None
        }
        
        # If we want to show a visual diff, we'd need the full rewritten text too.
        # Achademio app shows Redlines diff between original and 'response'.
        # Let's get the rewritten version for diffing if redlines is available.
        if REDLINES_AVAILABLE:
            rewritten = self.rewrite_academic(text)
            diff = Redlines(text, rewritten)
            result["diff_markdown"] = diff.output_markdown
            result["rewritten_text"] = rewritten
            
        return result

# Singleton
_achademio_instance = None
_achademio_lock = threading.Lock()

def get_achademio() -> AchademioSkill:
    global _achademio_instance
    with _achademio_lock:
        if not _achademio_instance:
            _achademio_instance = AchademioSkill()
    return _achademio_instance
