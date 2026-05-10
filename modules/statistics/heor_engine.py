"""
BioDockify HEOR Engine (Pillar 40)
Health Economics & Outcomes Research module for calculating Cost-Effectiveness.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class ICERResult:
    icer: float
    cost_diff: float
    effect_diff: float
    interpretation: str
    dominant: bool = False
    dominated: bool = False

class HEOREngine:
    """
    BioDockify Health Economics Engine.
    """
    
    # Common Willingness-to-Pay (WTP) thresholds
    WTP_THRESHOLDS = {
        "US": 100000,   # $100k - $150k per QALY
        "UK": 30000,    # £20k - £30k per QALY (NICE)
        "EU": 50000     # €50k generic
    }

    def calculate_icer(self, 
                       cost_new: float, effect_new: float, 
                       cost_soc: float, effect_soc: float,
                       currency: str = "USD") -> ICERResult:
        """
        Calculate Incremental Cost-Effectiveness Ratio (ICER).
        
        Args:
            cost_new: Cost of new treatment
            effect_new: Effectiveness of new treatment (e.g., QALYs)
            cost_soc: Cost of Standard of Care
            effect_soc: Effectiveness of Standard of Care
            
        Returns:
            ICERResult object
        """
        delta_cost = cost_new - cost_soc
        delta_effect = effect_new - effect_soc
        
        # 1. Dominance Checks
        if delta_cost < 0 and delta_effect > 0:
            return ICERResult(0.0, delta_cost, delta_effect, "New treatment DOMINATES (Cheaper & More Effective)", dominant=True)
            
        if delta_cost > 0 and delta_effect < 0:
            return ICERResult(0.0, delta_cost, delta_effect, "New treatment is DOMINATED (More Expensive & Less Effective)", dominated=True)
            
        # 2. ICER Calculation
        if delta_effect == 0:
            return ICERResult(float('inf'), delta_cost, delta_effect, "No effectiveness gain.")
            
        icer = delta_cost / delta_effect
        
        # 3. Interpretation
        threshold = self.WTP_THRESHOLDS.get("US", 100000)
        if icer < threshold:
            interp = f"Cost-Effective (ICER ${icer:,.2f} < ${threshold:,.0f} WTP)"
        else:
            interp = f"Not Cost-Effective (ICER ${icer:,.2f} > ${threshold:,.0f} WTP)"
            
        return ICERResult(icer, delta_cost, delta_effect, interp)

    def budget_impact_analysis(self, 
                               target_pop: int, 
                               capture_rate: float, 
                               cost_per_patient: float) -> float:
        """
        Simple Budget Impact Model (BIM).
        Estimated total cost to payer over 1 year.
        """
        return target_pop * capture_rate * cost_per_patient
