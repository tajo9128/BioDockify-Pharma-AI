import json
import logging
import threading
from datetime import datetime
from typing import List, Optional, Dict
from pathlib import Path
from .models import Hypothesis, HypothesisStatus, Evidence, EvidenceType

logger = logging.getLogger(__name__)

class HypothesisEngine:
    def __init__(self, storage_path: str = "data/hypotheses.json"):
        self.storage_path = Path(storage_path)
        self.hypotheses: Dict[str, Hypothesis] = {}
        self._load()

    def _load(self):
        if not self.storage_path.exists():
            return
        
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
                for h_data in data:
                    h = Hypothesis(**h_data)
                    self.hypotheses[h.id] = h
            logger.info(f"Loaded {len(self.hypotheses)} hypotheses.")
        except Exception as e:
            logger.error(f"Failed to load hypotheses: {e}")

    def _save(self):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = [h.model_dump(mode='json') for h in self.hypotheses.values()]
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save hypotheses: {e}")

    def create_hypothesis(self, statement: str, rationale: str) -> Hypothesis:
        h = Hypothesis(statement=statement, rationale=rationale)
        self.hypotheses[h.id] = h
        self._save()
        return h

    def get_hypothesis(self, id: str) -> Optional[Hypothesis]:
        return self.hypotheses.get(id)

    def list_hypotheses(self) -> List[Hypothesis]:
        return list(self.hypotheses.values())

    def update_status(self, id: str, status: HypothesisStatus):
        if id in self.hypotheses:
            self.hypotheses[id].status = status
            self.hypotheses[id].updated_at = datetime.now()
            self._save()

    def add_evidence(self, id: str, description: str, evidence_type: EvidenceType, source_id: str = None, confidence: float = 0.5):
        if id not in self.hypotheses:
            raise ValueError("Hypothesis not found")
        
        h = self.hypotheses[id]
        h.add_evidence(description, evidence_type, source_id, confidence=confidence)
        
        # Simple Logic Rule: If evidence accumulates, update confidence
        # In future: Use LLM to re-evaluate confidence based on evidence text
        self._recalc_confidence(h)
        self._save()
        return h

    def _recalc_confidence(self, h: Hypothesis):
        # Basic heuristic: 
        # Start at 0.1
        # +0.2 for each supporting
        # -0.2 for each contradicting
        score = 0.1
        for ev in h.evidence:
            if ev.type == EvidenceType.SUPPORTING:
                score += 0.2
            elif ev.type == EvidenceType.CONTRADICTING:
                score -= 0.2
        
        h.confidence_score = max(0.0, min(1.0, score))

    def generate_falsification_tests(self, id: str):
        """
        Placeholder for Agent Zero "Change My Mind" generator.
        Would call LLM to suggest experiments that verify/falsify this hypothesis.
        """
        pass

# Singleton
_engine_instance = None
_engine_lock = threading.Lock()

def get_hypothesis_engine():
    global _engine_instance
    with _engine_lock:
        if _engine_instance is None:
            _engine_instance = HypothesisEngine()
        return _engine_instance
