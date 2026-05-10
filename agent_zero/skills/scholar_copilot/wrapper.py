"""
ScholarCopilot Integration Wrapper
"""
import os
import sys
from typing import Optional, List, Dict, Any, Tuple
from loguru import logger
from pathlib import Path
import threading

# Path to the cloned repo
COPILOT_DIR = Path(os.path.abspath(__file__)).parent.parent.parent.parent / "_external" / "ScholarCopilot" / "run_demo"

class ScholarCopilotSkill:
    """
    Skill wrapper for ScholarCopilot academic writing assistance.
    """
    def __init__(self, device: str = "cpu"):
        self.device = device
        self.model = None
        self.tokenizer = None
        self.index = None
        self.lookup_indices = None
        self.meta_data = None
        self.citation_map = None
        
        # We don't load everything on init to save memory/speed
        # Users should call .load() explicitly if they want the local model.
        
    def _ensure_path(self):
        if str(COPILOT_DIR) not in sys.path:
            sys.path.insert(0, str(COPILOT_DIR))

    def load(self, model_path: str, index_dir: str, meta_data_path: str, citation_map_path: str):
        """Load model weights and FAISS index."""
        self._ensure_path()
        try:
            import scholar_copilot_model as scm
            import torch
            
            self.model, self.tokenizer = scm.load_model(model_path, self.device)
            self.index, self.lookup_indices = scm.load_faiss_index(index_dir)
            self.meta_data = scm.load_meta_data(meta_data_path)
            self.citation_map = scm.load_citation_map_data(citation_map_path)
            
            logger.info("ScholarCopilot model and index loaded successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to load ScholarCopilot: {e}")
            return False

    def complete_text(self, prefix: str) -> str:
        """Complete the current sentence/paragraph."""
        if not self.model:
            return "Error: ScholarCopilot model not loaded. Call .load() first."
            
        import scholar_copilot_model as scm
        import torch
        
        # Preprocess
        processed_input = scm.preprocess_input_text(prefix)
        
        # Generate
        content, cite_rep = scm.single_complete_step(self.model, self.tokenizer, self.device, processed_input)
        
        # If citation is suggested, we could retrieve it here, 
        # but for simple completion we just return the text.
        return content

    def search_citations(self, cite_rep: Any, top_k: int = 5) -> List[Dict]:
        """Search for citations based on a citation representation tensor."""
        if not self.index or cite_rep is None:
            return []
            
        import scholar_copilot_model as scm
        results = scm.retrieve_reference(self.index, self.lookup_indices, cite_rep, top_k=top_k)
        
        output = []
        for idx, dist in results:
            if idx in self.meta_data:
                output.append({
                    "id": idx,
                    "title": self.meta_data[idx].get("title"),
                    "score": float(dist),
                    "paper_id": self.meta_data[idx].get("paper_id")
                })
        return output

# Singleton
_copilot_instance = None
_copilot_lock = threading.Lock()

def get_scholar_copilot() -> ScholarCopilotSkill:
    global _copilot_instance
    with _copilot_lock:
        if not _copilot_instance:
            _copilot_instance = ScholarCopilotSkill()
    return _copilot_instance
