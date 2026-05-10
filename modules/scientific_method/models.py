from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum
import uuid
from datetime import datetime

class HypothesisStatus(str, Enum):
    PROPOSED = "proposed"
    INVESTIGATING = "investigating"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUSPENDED = "suspended"

class EvidenceType(str, Enum):
    SUPPORTING = "supporting"
    CONTRADICTING = "contradicting"

class Evidence(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: str
    source_id: Optional[str] = None  # Link to Library File ID or External URL
    source_type: str = "paper" # paper, experiment, logical_inference
    confidence: float = 0.5 # 0.0 to 1.0
    added_at: datetime = Field(default_factory=datetime.now)

class Hypothesis(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    statement: str = Field(..., description="The core scientific claim")
    rationale: str = Field(..., description="Why this hypothesis was proposed")
    
    status: HypothesisStatus = HypothesisStatus.PROPOSED
    confidence_score: float = 0.0 # Dynamic score based on evidence

    evidence: List[Evidence] = []
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    tags: List[str] = []
    
    def add_evidence(self, description: str, type: EvidenceType, source_id: str = None, confidence: float = 0.5):
        # In a real engine, we'd adjust the hypothesis confidence here
        ev = Evidence(
            description=description,
            source_id=source_id,
            confidence=confidence
        )
        self.evidence.append(ev)
        self.updated_at = datetime.now()
        return ev
