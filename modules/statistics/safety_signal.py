"""
BioDockify Safety Signal Engine (Pillar 32)
Calculates Odds Ratios and Confidence Intervals for Adverse Event monitoring.
"""

import math
from typing import Dict, Any, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class SafetySignal:
    odds_ratio: float
    ci_lower: float
    ci_upper: float
    p_value: float = 0.0 # Placeholder for Fisher's Exact
    signal_detected: bool = False

class SafetySignalDetector:
    """
    Detects safety signals in clinical trial data.
    """
    
    def calculate_odds_ratio(self, a: int, b: int, c: int, d: int) -> SafetySignal:
        """
        Calculate Odds Ratio for a 2x2 contingency table.
        
           | Event | No Event
        ---|-------|---------
        Trt|   a   |    b
        Ctl|   c   |    d
        
        OR = (a*d) / (b*c)
        """
        # Haldane-Anscombe correction for zero cells
        if a == 0 or b == 0 or c == 0 or d == 0:
            a += 0.5; b += 0.5; c += 0.5; d += 0.5
            
        odds_ratio = (a * d) / (b * c)
        
        # Log Odds Standard Error
        log_or = math.log(odds_ratio)
        se_log_or = math.sqrt(1/a + 1/b + 1/c + 1/d)
        
        # 95% Confidence Interval
        ci_lower = math.exp(log_or - 1.96 * se_log_or)
        ci_upper = math.exp(log_or + 1.96 * se_log_or)
        
        # Signal Detection: Lower CI > 1.0 implies significant risk increase
        is_signal = ci_lower > 1.0
        
        return SafetySignal(odds_ratio, ci_lower, ci_upper, signal_detected=is_signal)

    def generate_forest_plot_data(self, ae_data: Dict[str, Dict[str, int]]) -> Dict[str, Any]:
        """
        Process multiple AEs and return data structure for Forest Plot.
        ae_data format: {"Headache": {"a": 10, "b": 90, "c": 5, "d": 95}, ...}
        """
        results = {}
        for ae_name, counts in ae_data.items():
            res = self.calculate_odds_ratio(
                counts['a'], counts['b'], counts['c'], counts['d']
            )
            results[ae_name] = {
                "OR": round(res.odds_ratio, 2),
                "95% CI": f"{res.ci_lower:.2f} - {res.ci_upper:.2f}",
                "Signal": "⚠️" if res.signal_detected else "✅"
            }
        return results
