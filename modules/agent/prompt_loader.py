"""
Agent Zero - Dynamic Prompt Loader
Loads prompts from external markdown files for easy customization.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger("prompt_loader")

# Default prompts directory
PROMPTS_DIR = Path(__file__).parent / "prompts"


class PromptLoader:
    """
    Loads and manages prompts from external files.
    Supports hot-reload and template variable substitution.
    """
    
    def __init__(self, prompts_dir: Optional[Path] = None):
        self.prompts_dir = prompts_dir or PROMPTS_DIR
        self._cache: Dict[str, str] = {}
        self._cache_times: Dict[str, datetime] = {}
        self._ensure_directory()
    
    def _ensure_directory(self):
        """Create prompts directory if it doesn't exist."""
        self.prompts_dir.mkdir(parents=True, exist_ok=True)
    
    def load(
        self,
        prompt_name: str,
        variables: Optional[Dict[str, str]] = None,
        force_reload: bool = False
    ) -> Optional[str]:
        """
        Load a prompt from file.
        
        Args:
            prompt_name: Name of the prompt (without .md extension)
            variables: Optional variables to substitute in the template
            force_reload: Force reload from disk even if cached
        
        Returns:
            The prompt content with variables substituted, or None if not found
        """
        file_path = self.prompts_dir / f"{prompt_name}.md"
        
        # Check if file exists
        if not file_path.exists():
            logger.debug(f"Prompt file not found: {file_path}")
            return None
        
        # Check cache freshness
        if not force_reload and prompt_name in self._cache:
            file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            if file_mtime <= self._cache_times.get(prompt_name, datetime.min):
                content = self._cache[prompt_name]
                return self._substitute_variables(content, variables)
        
        # Load from file
        try:
            content = file_path.read_text(encoding="utf-8")
            self._cache[prompt_name] = content
            self._cache_times[prompt_name] = datetime.now()
            logger.info(f"Loaded prompt: {prompt_name}")
            return self._substitute_variables(content, variables)
        except Exception as e:
            logger.error(f"Failed to load prompt {prompt_name}: {e}")
            return None
    
    def _substitute_variables(
        self,
        content: str,
        variables: Optional[Dict[str, str]] = None
    ) -> str:
        """Substitute template variables in the prompt."""
        if not variables:
            return content
        
        result = content
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"  # {{variable}}
            result = result.replace(placeholder, str(value))
        
        return result
    
    def list_prompts(self) -> list:
        """List all available prompt files."""
        if not self.prompts_dir.exists():
            return []
        return [f.stem for f in self.prompts_dir.glob("*.md")]
    
    def save(self, prompt_name: str, content: str) -> bool:
        """Save a prompt to file."""
        file_path = self.prompts_dir / f"{prompt_name}.md"
        try:
            file_path.write_text(content, encoding="utf-8")
            self._cache[prompt_name] = content
            self._cache_times[prompt_name] = datetime.now()
            logger.info(f"Saved prompt: {prompt_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to save prompt {prompt_name}: {e}")
            return False
    
    def clear_cache(self):
        """Clear the prompt cache."""
        self._cache.clear()
        self._cache_times.clear()


# Global loader instance
prompt_loader = PromptLoader()


def load_prompt(name: str, variables: Optional[Dict[str, str]] = None) -> Optional[str]:
    """Convenience function to load a prompt."""
    return prompt_loader.load(name, variables)


def get_system_prompt(variables: Optional[Dict[str, str]] = None) -> str:
    """
    Get the main system prompt.
    Falls back to embedded prompt if file not found.
    """
    prompt = prompt_loader.load("system", variables)
    if prompt:
        return prompt
    
    # Fallback to embedded prompt
    from .prompts import AGENT_ZERO_SYSTEM_PROMPT
    return AGENT_ZERO_SYSTEM_PROMPT


def get_constitution() -> str:
    """Get the agent constitution (preserved pharma research rules)."""
    prompt = prompt_loader.load("constitution")
    if prompt:
        return prompt
    
    # Fallback to embedded constitution
    from .prompts import PHARMA_RESEARCHER_PROMPT
    return PHARMA_RESEARCHER_PROMPT
