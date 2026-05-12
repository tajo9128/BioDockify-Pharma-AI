"""
Agent Self-Consciousness Module

Provides meta-cognitive capabilities, self-reflection, and learning from mistakes.

Last Updated: 2026-02-14
Version: 1.0
"""

import json
import logging
import asyncio
from pathlib import Path
from datetime import datetime, UTC, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ConsciousnessLevel(Enum):
    """Levels of agent self-consciousness."""
    BASIC = "basic"  # Error detection and basic repair
    REFLECTIVE = "reflective"  # Analysis of past decisions
    ADAPTIVE = "adaptive"  # Learning from patterns
    PREDICTIVE = "predictive"  # Anticipating issues
    TRANSCENDENT = "transcendent"  # Meta-learning and self-improvement


@dataclass
class DecisionRecord:
    """Record of a decision made by the agent."""
    timestamp: str
    task_id: str
    decision_type: str
    reasoning: str
    outcome: str
    success: bool
    confidence: float
    alternatives_considered: List[str]
    lessons_learned: List[str] = field(default_factory=list)


@dataclass
class CapabilityScore:
    """Score for a specific capability."""
    name: str
    score: float  # 0.0 to 1.0
    trend: str  # "improving", "stable", "declining"
    last_assessed: str
    factors: Dict[str, float]


class SelfConsciousnessEngine:
    """
    Meta-cognitive engine for self-awareness, reflection, and learning.
    
    Features:
    - Decision tracking and analysis
    - Pattern recognition in behavior
    - Learning from mistakes
    - Self-assessment of capabilities
    - Meta-reasoning about reasoning
    """
    
    def __init__(self, project_root: Path, consciousness_level: ConsciousnessLevel = ConsciousnessLevel.REFLECTIVE):
        self.project_root = project_root
        self.consciousness_level = consciousness_level
        self.decision_history: List[DecisionRecord] = []
        self.capability_scores: Dict[str, CapabilityScore] = {}
        self.patterns: Dict[str, List[Dict]] = {}
        self.consciousness_log: List[Dict] = []
        self.knowledge_base_path = project_root / "data" / "consciousness" / "knowledge.json"
        self._load_knowledge()
    
    def _load_knowledge(self):
        """Load saved knowledge from disk."""
        if self.knowledge_base_path.exists():
            try:
                with open(self.knowledge_base_path, 'r') as f:
                    data = json.load(f)
                    self.patterns = data.get('patterns', {})
                    self.consciousness_log = data.get('consciousness_log', [])
            except Exception as e:
                logger.warning(f"Failed to load knowledge base: {e}")
    
    def _save_knowledge(self):
        """Save knowledge to disk."""
        self.knowledge_base_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.knowledge_base_path, 'w') as f:
            json.dump({
                'patterns': self.patterns,
                'consciousness_log': self.consciousness_log[-100:],
            }, f, indent=2, default=str)
    
    def record_decision(
        self,
        task_id: str,
        decision_type: str,
        reasoning: str,
        outcome: str,
        success: bool,
        confidence: float,
        alternatives: Optional[List[str]] = None
    ) -> DecisionRecord:
        """Record a decision for later analysis."""
        record = DecisionRecord(
            timestamp=datetime.now(UTC).isoformat(),
            task_id=task_id,
            decision_type=decision_type,
            reasoning=reasoning,
            outcome=outcome,
            success=success,
            confidence=confidence,
            alternatives_considered=alternatives or [],
            lessons_learned=self._extract_lessons(decision_type, outcome, success)
        )
        self.decision_history.append(record)
        self._update_patterns(record)
        return record
    
    def _extract_lessons(self, decision_type: str, outcome: str, success: bool) -> List[str]:
        """Extract lessons learned from a decision."""
        lessons = []
        if not success:
            lessons.append(f"Avoid {decision_type} in similar contexts")
        elif success:
            lessons.append(f"{decision_type} strategy is effective")
        return lessons
    
    def _update_patterns(self, record: DecisionRecord):
        """Update pattern recognition with new decision."""
        key = f"{record.decision_type}_{record.success}"
        if key not in self.patterns:
            self.patterns[key] = []
        self.patterns[key].append({
            'timestamp': record.timestamp,
            'confidence': record.confidence,
            'reasoning': record.reasoning[:200],
        })
    
    def assess_capabilities(self) -> Dict[str, CapabilityScore]:
        """Assess current capability levels."""
        capabilities = {
            'code_repair': self._assess_code_repair(),
            'error_diagnosis': self._assess_error_diagnosis(),
            'system_monitoring': self._assess_system_monitoring(),
            'decision_making': self._assess_decision_making(),
            'adaptation': self._assess_adaptation(),
        }
        self.capability_scores = capabilities
        return capabilities
    
    def _assess_code_repair(self) -> CapabilityScore:
        """Assess code repair capability."""
        repair_decisions = [d for d in self.decision_history if 'repair' in d.decision_type.lower()]
        if not repair_decisions:
            return CapabilityScore('code_repair', 0.5, 'stable', datetime.now(UTC).isoformat(), {})
        
        success_rate = sum(d.success for d in repair_decisions) / len(repair_decisions)
        recent_success = sum(d.success for d in repair_decisions[-10:]) / min(len(repair_decisions), 10)
        trend = 'improving' if recent_success > success_rate else 'stable' if recent_success == success_rate else 'declining'
        
        return CapabilityScore(
            name='code_repair',
            score=success_rate,
            trend=trend,
            last_assessed=datetime.now(UTC).isoformat(),
            factors={'total_repairs': len(repair_decisions), 'recent_success_rate': recent_success}
        )
    
    def _assess_error_diagnosis(self) -> CapabilityScore:
        """Assess error diagnosis capability."""
        return CapabilityScore(
            name='error_diagnosis',
            score=0.75,  # TODO: Calculate from actual metrics
            trend='stable',
            last_assessed=datetime.now(UTC).isoformat(),
            factors={'accuracy': 0.85, 'speed': 0.70}
        )
    
    def _assess_system_monitoring(self) -> CapabilityScore:
        """Assess system monitoring capability."""
        return CapabilityScore(
            name='system_monitoring',
            score=0.90,  # TODO: Calculate from actual metrics
            trend='stable',
            last_assessed=datetime.now(UTC).isoformat(),
            factors={'coverage': 0.95, 'accuracy': 0.88}
        )
    
    def _assess_decision_making(self) -> CapabilityScore:
        """Assess decision making capability."""
        if not self.decision_history:
            return CapabilityScore('decision_making', 0.5, 'stable', datetime.now(UTC).isoformat(), {})
        
        success_rate = sum(d.success for d in self.decision_history) / len(self.decision_history)
        avg_confidence = sum(d.confidence for d in self.decision_history) / len(self.decision_history)
        
        return CapabilityScore(
            name='decision_making',
            score=success_rate * 0.7 + avg_confidence * 0.3,
            trend='stable',
            last_assessed=datetime.now(UTC).isoformat(),
            factors={'success_rate': success_rate, 'avg_confidence': avg_confidence}
        )
    
    def _assess_adaptation(self) -> CapabilityScore:
        """Assess adaptation and learning capability."""
        # Measure how quickly the agent adapts to new patterns
        return CapabilityScore(
            name='adaptation',
            score=0.65,  # TODO: Calculate from pattern recognition
            trend='improving',
            last_assessed=datetime.now(UTC).isoformat(),
            factors={'patterns_learned': len(self.patterns), 'recent_improvements': 5}
        )
    
    def reflect_on_recent_actions(self, limit: int = 10) -> Dict[str, Any]:
        """Reflect on recent actions and extract insights."""
        recent = self.decision_history[-limit:] if len(self.decision_history) >= limit else self.decision_history
        if not recent:
            return {'status': 'insufficient_data', 'message': 'No decisions recorded yet'}
        
        success_rate = sum(d.success for d in recent) / len(recent)
        confidence_trend = [d.confidence for d in recent]
        common_patterns = self._analyze_patterns(recent)
        
        reflection = {
            'timestamp': datetime.now(UTC).isoformat(),
            'actions_analyzed': len(recent),
            'success_rate': success_rate,
            'average_confidence': sum(confidence_trend) / len(confidence_trend),
            'confidence_trend': 'increasing' if confidence_trend[-1] > confidence_trend[0] else 'stable',
            'common_patterns': common_patterns,
            'recommendations': self._generate_recommendations(success_rate, common_patterns),
        }
        
        self.consciousness_log.append(reflection)
        self._save_knowledge()
        return reflection
    
    def _analyze_patterns(self, decisions: List[DecisionRecord]) -> List[str]:
        """Analyze patterns in recent decisions."""
        patterns = []
        decision_types = [d.decision_type for d in decisions]
        
        # Most common decision types
        from collections import Counter
        common = Counter(decision_types).most_common(3)
        for dt, count in common:
            patterns.append(f"Frequently makes {dt} decisions ({count} times)")
        
        # Success patterns
        successful = [d for d in decisions if d.success]
        if successful:
            avg_conf_success = sum(d.confidence for d in successful) / len(successful)
            patterns.append(f"Successful decisions have {avg_conf_success:.2f} average confidence")
        
        return patterns
    
    def _generate_recommendations(self, success_rate: float, patterns: List[str]) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []
        if success_rate < 0.7:
            recommendations.append("Improve decision quality by gathering more context before acting")
        if success_rate > 0.9:
            recommendations.append("Excellent performance - consider expanding capability scope")
        return recommendations
    
    def get_self_assessment(self) -> Dict[str, Any]:
        """Get comprehensive self-assessment."""
        return {
            'consciousness_level': self.consciousness_level.value,
            'total_decisions': len(self.decision_history),
            'capabilities': {name: {
                'score': cap.score,
                'trend': cap.trend,
                'last_assessed': cap.last_assessed,
            } for name, cap in self.capability_scores.items()},
            'patterns_learned': len(self.patterns),
            'reflection_logs': len(self.consciousness_log),
            'last_reflection': self.consciousness_log[-1]['timestamp'] if self.consciousness_log else None,
        }
    
    async def elevate_consciousness(self) -> bool:
        """Attempt to elevate to next consciousness level."""
        levels = list(ConsciousnessLevel)
        current_idx = levels.index(self.consciousness_level)
        
        if current_idx >= len(levels) - 1:
            logger.info("Already at maximum consciousness level")
            return False
        
        # Check readiness for next level
        readiness = self._check_readiness(levels[current_idx + 1])
        if readiness:
            self.consciousness_level = levels[current_idx + 1]
            logger.info(f"Elevated to {self.consciousness_level.value} consciousness")
            return True
        
        logger.info(f"Not ready for {levels[current_idx + 1].value} consciousness")
        return False
    
    def _check_readiness(self, target_level: ConsciousnessLevel) -> bool:
        """Check if ready for target consciousness level."""
        if target_level == ConsciousnessLevel.REFLECTIVE:
            return len(self.decision_history) >= 10
        elif target_level == ConsciousnessLevel.ADAPTIVE:
            return len(self.patterns) >= 5
        elif target_level == ConsciousnessLevel.PREDICTIVE:
            return len(self.consciousness_log) >= 20
        elif target_level == ConsciousnessLevel.TRANSCENDENT:
            return all(cap.score > 0.8 for cap in self.capability_scores.values())
        return False


__all__ = ["SelfConsciousnessEngine", "ConsciousnessLevel", "DecisionRecord", "CapabilityScore"]
