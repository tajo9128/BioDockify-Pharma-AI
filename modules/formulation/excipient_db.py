"""
Excipient Database — common pharmaceutical excipients by function.

Each entry: name, function, max_concentration, solubility, common_uses
"""

from typing import Dict, Any, List, Optional

EXCIPIENTS = {
    # Fillers / Diluents
    "microcrystalline_cellulose": {
        "name": "Microcrystalline Cellulose (MCC, Avicel)",
        "function": "Filler/Diluent",
        "max_concentration": "80%",
        "solubility": "Insoluble",
        "common_uses": "Tablet filler, binder, disintegrant",
        "notes": "Excellent flow properties, compactibility"
    },
    "lactose_monohydrate": {
        "name": "Lactose Monohydrate",
        "function": "Filler/Diluent",
        "max_concentration": "70%",
        "solubility": "Freely soluble",
        "common_uses": "Tablet filler, dry powder inhaler carrier",
        "notes": "Stable, compatible with most drugs; avoid with amines (Maillard)"
    },
    "mannitol": {
        "name": "Mannitol",
        "function": "Filler/Diluent",
        "max_concentration": "60%",
        "solubility": "Freely soluble",
        "common_uses": "Chewable tablets, lyophilized products",
        "notes": "Non-hygroscopic, sweet taste, stable"
    },
    # Binders
    "povidone_k30": {
        "name": "Povidone K30 (PVP K30)",
        "function": "Binder",
        "max_concentration": "10%",
        "solubility": "Freely soluble",
        "common_uses": "Wet granulation binder, film former",
        "notes": "Good binder strength, low toxicity"
    },
    "hydroxypropyl_methylcellulose": {
        "name": "HPMC (Hydroxypropyl Methylcellulose)",
        "function": "Binder/Coating",
        "max_concentration": "15%",
        "solubility": "Slowly soluble (grades vary)",
        "common_uses": "Controlled-release matrix, film coating, tablet binder",
        "notes": "Multiple viscosity grades: E5, E15, K4M, K100M"
    },
    # Disintegrants
    "croscarmellose_sodium": {
        "name": "Croscarmellose Sodium (CCS)",
        "function": "Disintegrant",
        "max_concentration": "5%",
        "solubility": "Insoluble (swells)",
        "common_uses": "Superdisintegrant for fast disintegration",
        "notes": "Works at low conc, effective in ODT formulations"
    },
    "sodium_starch_glycolate": {
        "name": "Sodium Starch Glycolate (SSG)",
        "function": "Disintegrant",
        "max_concentration": "8%",
        "solubility": "Insoluble (swells)",
        "common_uses": "Superdisintegrant, especially for granulation",
        "notes": "Works via swelling mechanism"
    },
    # Lubricants
    "magnesium_stearate": {
        "name": "Magnesium Stearate",
        "function": "Lubricant",
        "max_concentration": "2%",
        "solubility": "Insoluble",
        "common_uses": "Tablet lubricant, prevents sticking to punches",
        "notes": "Most used lubricant; can reduce dissolution at >1%"
    },
    "sodium_stearyl_fumarate": {
        "name": "Sodium Stearyl Fumarate (Pruv)",
        "function": "Lubricant",
        "max_concentration": "3%",
        "solubility": "Insoluble",
        "common_uses": "Alternative to Mg-stearate, less effect on dissolution",
        "notes": "Preferred when Mg-stearate delays dissolution"
    },
    # Coatings
    "opadry_ii": {
        "name": "Opadry II (HPMC-based coating)",
        "function": "Film Coating",
        "max_concentration": "8%",
        "solubility": "Water-soluble",
        "common_uses": "Film coating, moisture barrier, color coating",
        "notes": "Ready-to-use film coating system"
    },
    # Other
    "colloidal_silicon_dioxide": {
        "name": "Colloidal Silicon Dioxide (Aerosil)",
        "function": "Glidant",
        "max_concentration": "2%",
        "solubility": "Insoluble",
        "common_uses": "Flow improver for powder blends",
        "notes": "Improves powder flow, anti-caking agent"
    },
}


def get_excipients(function_filter: Optional[str] = None) -> Dict[str, Any]:
    """Get excipient database, optionally filtered by function.

    Args:
        function_filter: Filter by function (e.g., "Filler", "Binder", "Disintegrant")

    Returns:
        Dict with filtered excipients list
    """
    if function_filter:
        filtered = {k: v for k, v in EXCIPIENTS.items()
                    if function_filter.lower() in v["function"].lower()}
    else:
        filtered = EXCIPIENTS

    return {
        "status": "ok",
        "total": len(filtered),
        "function_filter": function_filter or "all",
        "excipients": filtered,
    }


def search_excipients(query: str) -> Dict[str, Any]:
    """Search excipient database by name, function, or use case.

    Args:
        query: Search term (name, function, or use case)

    Returns:
        Dict with matching excipients
    """
    q = query.lower()
    matches = {}
    for key, exc in EXCIPIENTS.items():
        searchable = f"{exc['name']} {exc['function']} {' '.join(exc.get('common_uses', '').split())}".lower()
        if q in searchable:
            matches[key] = exc

    return {
        "status": "ok",
        "query": query,
        "total": len(matches),
        "matches": matches,
    }
