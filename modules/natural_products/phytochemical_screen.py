"""
Phytochemical Screening Protocols — standard tests for 7 compound classes.

References: Harborne, Sofowora, Trease & Evans
"""

from typing import Dict, Any, List


PHYTOCHEMICAL_TESTS = {
    "alkaloids": {
        "compound_class": "Alkaloids",
        "reagents": ["Dragendorff's", "Mayer's", "Wagner's", "Hager's"],
        "procedure": "Add 1-2 drops of reagent to extract. Turbidity/precipitation = positive.",
        "expected_result": "Orange/red precipitate (Dragendorff), white precipitate (Mayer)",
        "reference": "Sofowora A. Medicinal Plants and Traditional Medicine in Africa. 1993"
    },
    "flavonoids": {
        "compound_class": "Flavonoids",
        "reagents": ["Shinoda test (Mg + HCl)", "Lead acetate", "Ferric chloride"],
        "procedure": "Add Mg turnings + conc HCl to extract. Pink/red/magenta color = positive.",
        "expected_result": "Pink to red coloration within 2-3 minutes",
        "reference": "Harborne JB. Phytochemical Methods. 3rd ed. 1998"
    },
    "tannins": {
        "compound_class": "Tannins",
        "reagents": ["Ferric chloride", "Gelatin", "Lead acetate"],
        "procedure": "Add 1% FeCl3 to extract. Blue-black = hydrolysable; green = condensed.",
        "expected_result": "Blue-black or green coloration",
        "reference": "Trease GE, Evans WC. Pharmacognosy. 15th ed. 2002"
    },
    "saponins": {
        "compound_class": "Saponins",
        "reagents": ["Frothing test (water)", "Liebermann-Burchard"],
        "procedure": "Shake extract vigorously with water. Persistent froth (>10 min) = positive.",
        "expected_result": "Persistent foam >2 cm for 10+ minutes",
        "reference": "Sofowora A. 1993"
    },
    "steroids": {
        "compound_class": "Steroids/Triterpenoids",
        "reagents": ["Liebermann-Burchard (acetic anhydride + H2SO4)", "Salkowski"],
        "procedure": "Add acetic anhydride + conc H2SO4. Green/blue = steroids; red/brown = triterpenoids.",
        "expected_result": "Green-blue ring (steroids) or red-brown (triterpenoids)",
        "reference": "Harborne JB. 1998"
    },
    "terpenoids": {
        "compound_class": "Terpenoids",
        "reagents": ["Salkowski test (CHCl3 + H2SO4)"],
        "procedure": "Add CHCl3 to extract, layer with H2SO4. Red-brown at interface = positive.",
        "expected_result": "Red-brown color at chloroform-sulfuric acid interface",
        "reference": "Trease GE, Evans WC. 2002"
    },
    "glycosides": {
        "compound_class": "Glycosides (cardiac)",
        "reagents": ["Keller-Killiani (acetic anhydride + H2SO4)", "Legal test (sodium nitroprusside)", "Kedde test (3,5-dinitrobenzoic acid)"],
        "procedure": "Kedde test: add 3,5-dinitrobenzoic acid in NaOH. Violet = positive for cardiac glycosides.",
        "expected_result": "Violet/purple coloration (Kedde), brown ring (Keller-Killiani)",
        "reference": "Evans WC. Trease and Evans' Pharmacognosy. 16th ed. 2009"
    },
}


def get_screening_protocol(compound_class: str) -> Dict[str, Any]:
    """Get phytochemical screening protocol for a specific compound class.

    Args:
        compound_class: One of: alkaloids, flavonoids, tannins, saponins,
                       steroids, terpenoids, glycosides

    Returns:
        Dict with reagents, procedure, expected result, reference
    """
    key = compound_class.lower().strip().replace(" ", "_")

    if key in PHYTOCHEMICAL_TESTS:
        return {"status": "ok", "protocol": PHYTOCHEMICAL_TESTS[key]}

    return {
        "status": "error",
        "error": f"Unknown compound class: '{compound_class}'. Available: {list(PHYTOCHEMICAL_TESTS.keys())}"
    }
