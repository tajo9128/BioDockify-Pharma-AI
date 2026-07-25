"""
Plant Database — medicinal plants with ethnopharmacological data.

Each entry: family, traditional use, active compounds, pharmacological activities.
"""

from typing import Dict, Any, List, Optional


PLANTS = {
    "evolvulus_alsinoides": {
        "common_name": "Shankhpushpi",
        "family": "Convolvulaceae",
        "traditional_use": "Nootropic, anxiolytic, memory enhancement (Ayurveda)",
        "active_compounds": ["Scopoletin", "Ursolic acid", "Quercetin", "Caffeic acid"],
        "pharmacological": "AChE inhibition, antioxidant, neuroprotective",
        "parts_used": "Whole plant",
        "reference": "Nahata et al., J Ethnopharmacol 2012"
    },
    "cinnamomum_verum": {
        "common_name": "Ceylon Cinnamon",
        "family": "Lauraceae",
        "traditional_use": "Anti-diabetic, digestive aid, anti-inflammatory",
        "active_compounds": ["Cinnamaldehyde", "Eugenol", "Cinnamic acid", "Linalool"],
        "pharmacological": "Anti-diabetic (insulin sensitivity), antimicrobial, antioxidant",
        "parts_used": "Bark, leaves",
        "reference": "Ranasinghe et al., BMC Complement Altern Med 2013"
    },
    "curcuma_longa": {
        "common_name": "Turmeric",
        "family": "Zingiberaceae",
        "traditional_use": "Anti-inflammatory, wound healing, digestive",
        "active_compounds": ["Curcumin", "Demethoxycurcumin", "Bisdemethoxycurcumin"],
        "pharmacological": "NF-κB inhibition, COX-2 inhibition, antioxidant",
        "parts_used": "Rhizome",
        "reference": "Hewlings & Kalman, Foods 2017"
    },
    "withania_somnifera": {
        "common_name": "Ashwagandha",
        "family": "Solanaceae",
        "traditional_use": "Adaptogen, stress relief, vitality (Ayurveda)",
        "active_compounds": ["Withanolide A", "Withaferin A", "Withanoside IV"],
        "pharmacological": "GABAergic, anti-cortisol, immunomodulatory",
        "parts_used": "Root, leaf",
        "reference": "Mikolai et al., J Int Soc Sports Nutr 2009"
    },
    "boswellia_serrata": {
        "common_name": "Indian Frankincense",
        "family": "Burseraceae",
        "traditional_use": "Anti-inflammatory, joint health (Ayurveda)",
        "active_compounds": ["Boswellic acid", "AKBA (3-O-acetyl-11-keto-β-boswellic acid)"],
        "pharmacological": "5-LOX inhibition, anti-inflammatory, anti-arthritic",
        "parts_used": "Resin/gum",
        "reference": "Siddiqui, Indian J Pharm Sci 2011"
    },
    "centella_asiatica": {
        "common_name": "Gotu Kola",
        "family": "Apiaceae",
        "traditional_use": "Wound healing, cognitive enhancement, longevity",
        "active_compounds": ["Asiaticoside", "Madecassoside", "Asiatic acid", "Madecassic acid"],
        "pharmacological": "Collagen synthesis, neuroprotective, anti-inflammatory",
        "parts_used": "Leaves",
        "reference": "Brinkhaus et al., Phytomedicine 2000"
    },
    "salix_alba": {
        "common_name": "White Willow Bark",
        "family": "Salicaceae",
        "traditional_use": "Analgesic, anti-inflammatory, antipyretic",
        "active_compounds": ["Salicin", "Salicylic acid", "Flavonoids"],
        "pharmacological": "COX inhibition (natural aspirin precursor)",
        "parts_used": "Bark",
        "reference": "Gao et al., J Tradit Complement Med 2020"
    },
    "gingko_biloba": {
        "common_name": "Ginkgo",
        "family": "Ginkgoaceae",
        "traditional_use": "Cognitive enhancement, peripheral circulation",
        "active_compounds": ["Ginkgolide A", "Ginkgolide B", "Bilobalide", "Flavonoids"],
        "pharmacological": "Neuroprotective, antiplatelet, antioxidant",
        "parts_used": "Leaves",
        "reference": "Tan et al., J Ethnopharmacol 2015"
    },
    "silybum_marianum": {
        "common_name": "Milk Thistle",
        "family": "Asteraceae",
        "traditional_use": "Liver protection, hepatoprotective",
        "active_compounds": ["Silymarin", "Silybin", "Isosilibinin"],
        "pharmacological": "Hepatoprotective, antioxidant, anti-inflammatory",
        "parts_used": "Seeds",
        "reference": "Federico et al., Molecules 2017"
    },
    "panax_ginseng": {
        "common_name": "Ginseng",
        "family": "Araliaceae",
        "traditional_use": "Adaptogen, vitality, cognitive enhancement",
        "active_compounds": ["Ginsenoside Rb1", "Ginsenoside Rg1", "Ginsenoside Rg3"],
        "pharmacological": "Immunomodulatory, anti-cancer, neuroprotective",
        "parts_used": "Root",
        "reference": "Liu et al., J Ginseng Res 2019"
    },
    "cannabis_sativa": {
        "common_name": "Hemp/Cannabis",
        "family": "Cannabaceae",
        "traditional_use": "Analgesic, anti-inflammatory, anxiolytic",
        "active_compounds": ["THC (Δ9-tetrahydrocannabinol)", "CBD (cannabidiol)", "CBG (cannabigerol)"],
        "pharmacological": "CB1/CB2 receptor agonism/antagonism, 5-HT1A agonism (CBD)",
        "parts_used": "Flowers, leaves, resin",
        "reference": "Mechoulam et al., Nat Rev Neurosci 2020"
    },
}


def list_plants() -> Dict[str, Any]:
    """List all plants in the database."""
    return {
        "status": "ok",
        "total": len(PLANTS),
        "plants": {k: v["common_name"] for k, v in PLANTS.items()},
    }


def get_plant(name: str) -> Dict[str, Any]:
    """Get detailed info about a plant by name or key."""
    q = name.lower().strip().replace(" ", "_")

    if q in PLANTS:
        return {"status": "ok", "plant": PLANTS[q], "key": q}

    # Fuzzy search by common name
    for key, plant in PLANTS.items():
        if q in plant["common_name"].lower().replace(" ", "_"):
            return {"status": "ok", "plant": plant, "key": key}

    available = list(PLANTS.keys())
    return {"status": "error", "error": f"Plant '{name}' not found. Available: {available}"}
