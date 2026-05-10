"""
Hybrid Skills Loader - Load skills from markdown files (NanoBot compatible).
"""
import os
import glob
import frontmatter
import logging
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class SkillsLoader:
    """
    Loads SKILL.md files and registers them as tools.
    """
    
    def __init__(self, agent):
        self.agent = agent
        self.skills_dir = Path(agent.config.workspace_path) / "skills"
        
    def load_all(self) -> Dict[str, Any]:
        """Load all skills from workspace."""
        if not self.skills_dir.exists():
            logger.info(f"Skills dir {self.skills_dir} does not exist.")
            return {}
            
        skills = {}
        # Find all SKILL.md files recursively
        for skill_file in self.skills_dir.rglob("SKILL.md"):
            try:
                skill = self._load_skill(skill_file)
                if skill:
                    skills[skill['name']] = skill
            except Exception as e:
                logger.error(f"Failed to load skill {skill_file}: {e}")
                
        logger.info(f"Loaded {len(skills)} skills.")
        return skills
        
    def _load_skill(self, path: Path) -> Dict[str, Any]:
        """Parse a single SKILL.md file."""
        post = frontmatter.load(path)
        metadata = post.metadata
        content = post.content
        
        name = metadata.get('name')
        description = metadata.get('description')
        
        if not name:
            logger.warning(f"Skill at {path} missing name")
            return None
            
        # Parse python code blocks for implementation
        # Simple extraction for now
        code = self._extract_code(content)
        
        return {
            "name": name,
            "description": description,
            "content": content,
            "code": code,
            "path": str(path)
        }
        
    def _extract_code(self, content: str) -> str:
        """Extract python code from markdown."""
        lines = content.split('\n')
        code_lines = []
        in_code = False
        
        for line in lines:
            if line.strip().startswith('```python'):
                in_code = True
                continue
            if line.strip().startswith('```') and in_code:
                in_code = False
                continue
                
            if in_code:
                code_lines.append(line)
                
        return "\n".join(code_lines)
