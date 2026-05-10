import json
import uuid
from pathlib import Path
from typing import Optional, Dict

class FigureManager:
    """
    Manages scientific figures and their metadata (reproducibility).
    Links a plot to the code that generated it.
    """
    
    def __init__(self, storage_dir: str = "data/figures"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.storage_dir / "figure_metadata.json"
        self.figures = self._load_metadata()
        
    def _load_metadata(self) -> Dict:
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        return {}
        
    def _save_metadata(self):
        with open(self.metadata_file, 'w') as f:
            json.dump(self.figures, f, indent=2)

    def register_figure(self, 
                        title: str, 
                        caption: str, 
                        code_snippet: str, 
                        image_path: str) -> str:
        """
        Register a new figure for tracking.
        """
        fig_id = str(uuid.uuid4())
        
        self.figures[fig_id] = {
            "id": fig_id,
            "title": title,
            "caption": caption,
            "code": code_snippet,
            "path": image_path,
            "timestamp": str(uuid.uuid1()) # Timestamp generic
        }
        self._save_metadata()
        return fig_id

    def get_figure(self, fig_id: str) -> Optional[Dict]:
        return self.figures.get(fig_id)

    def list_figures(self):
        return list(self.figures.values())
