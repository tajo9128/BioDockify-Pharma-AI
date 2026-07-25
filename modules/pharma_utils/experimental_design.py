"""
Experimental Design — DOE (Design of Experiments).

Full factorial, fractional factorial, Taguchi designs for pharma R&D.
"""

import numpy as np
from typing import Dict, Any, List, Optional


def full_factorial(factors: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate a full factorial design.
    
    Args:
        factors: List of dicts with 'name' and 'levels' keys
            Example: [{"name": "Temperature", "levels": [20, 40, 60]}, 
                      {"name": "Pressure", "levels": [1, 2]}]
    
    Returns:
        Dict with design matrix and metadata
    """
    if not factors:
        return {"status": "error", "error": "Provide at least one factor"}
    
    factor_names = [f["name"] for f in factors]
    factor_levels = [f["levels"] for f in factors]
    
    # Generate all combinations
    from itertools import product
    combinations = list(product(*factor_levels))
    
    # Create design matrix
    design = []
    for i, combo in enumerate(combinations):
        row = {"run": i + 1}
        for j, name in enumerate(factor_names):
            row[name] = combo[j]
        design.append(row)
    
    total_runs = len(design)
    
    return {
        "status": "ok",
        "design_type": "Full Factorial",
        "factors": len(factors),
        "levels": [len(f["levels"]) for f in factors],
        "total_runs": total_runs,
        "factor_names": factor_names,
        "design": design,
        "interpretation": f"Full factorial: {len(factors)} factors, {total_runs} runs. Every combination tested.",
        "reference": "Montgomery DC. Design and Analysis of Experiments. 10th ed. Wiley; 2020."
    }


def fractional_factorial(factors: int, resolution: int = 3) -> Dict[str, Any]:
    """Generate a fractional factorial design (2^(k-p)).
    
    Args:
        factors: Number of factors (k)
        resolution: Design resolution (III, IV, V)
    
    Returns:
        Dict with design matrix and aliasing structure
    """
    if factors < 3:
        return {"status": "error", "error": "Need at least 3 factors for fractional factorial"}
    
    # For 2^(k-p) designs, we use a base design and extend
    # Simplified: generate a 2^(k-1) half-fraction
    base_runs = 2 ** (factors - 1)
    
    # Generate base design (first k-1 factors)
    from itertools import product
    base_levels = list(product([0, 1], repeat=factors - 1))
    
    # Add kth factor as interaction of first two (standard half-fraction)
    design = []
    for i, row in enumerate(base_levels):
        row_list = list(row)
        # Last factor = XOR of first two factors (standard construction)
        row_list.append(row_list[0] ^ row_list[1])
        design.append(row_list)
    
    # Create factor names
    factor_names = [f"X{i+1}" for i in range(factors)]
    
    design_rows = []
    for i, row in enumerate(design):
        row_dict = {"run": i + 1}
        for j, name in enumerate(factor_names):
            row_dict[name] = row[j]
        design_rows.append(row_dict)
    
    return {
        "status": "ok",
        "design_type": f"Fractional Factorial 2^({factors}-1)",
        "factors": factors,
        "total_runs": base_runs,
        "resolution": f"Resolution {'III' if resolution == 3 else 'IV' if resolution == 4 else 'V'}",
        "factor_names": factor_names,
        "design": design_rows,
        "interpretation": f"Half-fraction: {factors} factors in {base_runs} runs. Main effects aliased with 2-factor interactions (Resolution III).",
        "reference": "Montgomery DC. Design and Analysis of Experiments. 10th ed."
    }


def taguchi_design(factors: int, levels: int = 2) -> Dict[str, Any]:
    """Generate a Taguchi orthogonal array design.
    
    Args:
        factors: Number of factors
        levels: Number of levels per factor (2 or 3)
    
    Returns:
        Dict with Taguchi design matrix
    """
    # Standard Taguchi arrays (simplified)
    if levels == 2 and factors <= 7:
        # L8(2^7) Taguchi array
        array = [
            [0,0,0,0,0,0,0],
            [0,0,0,1,1,1,1],
            [0,1,1,0,0,1,1],
            [0,1,1,1,1,0,0],
            [1,0,1,0,1,0,1],
            [1,0,1,1,0,1,0],
            [1,1,0,0,1,1,0],
            [1,1,0,1,0,0,1],
        ]
        runs = 8
    elif levels == 2 and factors <= 15:
        # L16(2^15) Taguchi array
        array = [
            [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,1,1,1,1,1,1,1,1],
            [0,0,0,1,1,1,1,0,0,0,0,1,1,1,1],
            [0,0,0,1,1,1,1,1,1,1,1,0,0,0,0],
            [0,1,1,0,0,1,1,0,0,1,1,0,0,1,1],
            [0,1,1,0,0,1,1,1,1,0,0,1,1,0,0],
            [0,1,1,1,1,0,0,0,0,1,1,1,1,0,0],
            [0,1,1,1,1,0,0,1,1,0,0,0,0,1,1],
            [1,0,1,0,1,0,1,0,1,0,1,0,1,0,1],
            [1,0,1,0,1,0,1,1,0,1,0,1,0,1,0],
            [1,0,1,1,0,1,0,0,1,0,1,1,0,1,0],
            [1,0,1,1,0,1,0,1,0,1,0,0,1,0,1],
            [1,1,0,0,1,1,0,0,1,1,0,0,1,1,0],
            [1,1,0,0,1,1,0,1,0,0,1,1,0,0,1],
            [1,1,0,1,0,0,1,0,1,1,0,1,0,0,1],
            [1,1,0,1,0,0,1,1,0,0,1,0,1,1,0],
        ]
        runs = 16
    else:
        return {"status": "error", "error": f"Unsupported: {factors} factors, {levels} levels. Use 2-15 factors with 2 levels."}
    
    # Take only the columns for our factors
    factor_names = [f"X{i+1}" for i in range(factors)]
    
    design = []
    for i, row in enumerate(array):
        row_dict = {"run": i + 1}
        for j, name in enumerate(factor_names):
            row_dict[name] = row[j] if j < len(row) else 0
        design.append(row_dict)
    
    return {
        "status": "ok",
        "design_type": f"Taguchi L{runs}({factors})",
        "factors": factors,
        "levels": levels,
        "total_runs": runs,
        "factor_names": factor_names,
        "design": design,
        "interpretation": f"Taguchi L{runs}: {factors} factors in {runs} runs. Orthogonal array for robust parameter design.",
        "reference": "Taguchi G. Introduction to Quality Engineering. 1986."
    }
