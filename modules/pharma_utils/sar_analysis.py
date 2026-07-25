"""
SAR (Structure-Activity Relationship) Analysis.

Generates SAR tables from compound libraries with activity data.
"""

import numpy as np
from typing import Dict, Any, List, Optional


def generate_sar_table(
    compounds: List[Dict[str, Any]],
    activity_col: str = "IC50_nM",
    structure_col: str = "SMILES",
    name_col: str = "Name",
) -> Dict[str, Any]:
    """Generate an SAR table from compound data.
    
    Args:
        compounds: List of dicts with structure, activity, and name
            Example: [{"Name": "Aspirin", "SMILES": "CC(=O)OC1=CC=CC=C1C(O)=O", "IC50_nM": 100}]
        activity_col: Column name for activity data
        structure_col: Column name for SMILES/structure
        name_col: Column name for compound name
    
    Returns:
        Dict with SAR table and analysis
    """
    if not compounds or len(compounds) < 2:
        return {"status": "error", "error": "Need at least 2 compounds for SAR analysis"}
    
    # Extract data
    names = [c.get(name_col, f"Compound_{i}") for i, c in enumerate(compounds)]
    activities = [c.get(activity_col, 0) for c in compounds]
    smiles = [c.get(structure_col, "") for c in compounds]
    
    # Calculate relative activity
    min_activity = min(activities) if activities else 1
    max_activity = max(activities) if activities else 1
    
    sar_rows = []
    for i, comp in enumerate(compounds):
        activity = activities[i]
        # Relative activity vs most potent compound
        relative = min_activity / activity if activity > 0 else 0
        
        # Activity class
        if activity <= 10:
            activity_class = "Highly Active"
        elif activity <= 100:
            activity_class = "Active"
        elif activity <= 1000:
            activity_class = "Moderate"
        else:
            activity_class = "Weak"
        
        sar_rows.append({
            "compound": names[i],
            "smiles": smiles[i],
            "activity": activity,
            "activity_unit": "nM" if "IC50" in activity_col or "EC50" in activity_col else "",
            "activity_class": activity_class,
            "relative_activity": round(relative, 2),
            "potency_rank": i + 1,  # Will be overwritten after sorting
        })
    
    # Sort by activity (most potent first)
    sar_rows.sort(key=lambda x: x["activity"])
    
    # Re-rank
    for i, row in enumerate(sar_rows):
        row["potency_rank"] = i + 1
    
    # SAR insights
    activities_sorted = [r["activity"] for r in sar_rows]
    range_fold = max(activities_sorted) / min(activities_sorted) if min(activities_sorted) > 0 else 0
    
    return {
        "status": "ok",
        "activity_column": activity_col,
        "total_compounds": len(sar_rows),
        "most_potent": sar_rows[0]["compound"] if sar_rows else None,
        "least_potent": sar_rows[-1]["compound"] if sar_rows else None,
        "potency_range_fold": round(range_fold, 1),
        "mean_activity": round(float(np.mean(activities_sorted)), 2),
        "median_activity": round(float(np.median(activities_sorted)), 2),
        "sar_table": sar_rows,
        "interpretation": f"SAR spans {range_fold:.1f}-fold potency range. {sar_rows[0]['compound']} is most potent ({sar_rows[0]['activity']} nM).",
        "reference": "Structure-Activity Relationship analysis for lead optimization"
    }
