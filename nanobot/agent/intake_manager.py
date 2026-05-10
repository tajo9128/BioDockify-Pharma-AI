"""
Project Intake Manager - BioDockify NanoBot
Handles user onboarding, workspace bootstrapping, and context seeding.
"""
import logging
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger("nanobot.intake")

class ProjectIntakeManager:
    """
    Onboards the user to a new research project.
    Bootstraps the workspace and seeds the initial scientific context.
    """
    
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.nanobot_root = workspace_root / "nanobot"
        self.nanobot_root.mkdir(parents=True, exist_ok=True)

    async def bootstrap_workspace(self, project_name: str, researcher_role: str) -> Dict[str, Any]:
        """
        Create the standard directory structure for a professional research project.
        """
        dirs = ["data/raw", "data/processed", "notebooks", "results", "temp", "literature"]
        created = []
        for d in dirs:
            path = self.workspace_root / d
            path.mkdir(parents=True, exist_ok=True)
            created.append(d)
        
        # Seed the README.md
        readme_path = self.workspace_root / "README.md"
        if not readme_path.exists():
            content = f"""# {project_name}
Automated Research Project managed by BioDockify.

**Researcher Role**: {researcher_role}
**Initialized**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

## Directory Structure
- `data/`: Raw and processed research data.
- `notebooks/`: Jupyter or script-based analysis.
- `results/`: Final outputs, tables, and figures.
- `literature/`: PDF papers and BibTeX files.
- `nanobot/`: System logs, snapshots, and audit trails.
"""
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(content)
        
        return {"status": "success", "directories": created, "readme": str(readme_path)}

    async def seed_project_context(self, 
                                   project_name: str, 
                                   goal: str, 
                                   methodology: Optional[str] = None) -> str:
        """
        Generate and save a project_context.json file.
        """
        context_path = self.nanobot_root / "project_context.json"
        
        context_data = {
            "project_name": project_name,
            "primary_goal": goal,
            "methodology": methodology,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "active",
            "checkpoints": []
        }
        
        try:
            with open(context_path, "w", encoding="utf-8") as f:
                json.dump(context_data, f, indent=2)
            return str(context_path)
        except Exception as e:
            logger.error(f"Failed to seed project context: {e}")
            return "error"

    def generate_onboarding_questions(self, spark: str) -> str:
        """
        A helper for the LLM to understand what questions to ask the user.
        """
        return f"""
The user provided a research idea: "{spark}"

To act as a Perfect Receptionist, clarify the following before involving Agent Zero:
1. What is the preferred academic title for this project?
2. Are there specific datasets the user wants to prioritize?
3. What is the desired output format (Paper Draft, Dataset, Simulation Results)?
4. Is there a specific deadline or conference target?
"""
