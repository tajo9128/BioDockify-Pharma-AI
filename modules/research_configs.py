"""Research Department Configurations — department-specific milestones, databases, templates.

Each pharmaceutical department has different research workflows, milestones,
literature databases, and output types. This module provides configurations
for department-aware research management.
"""

DEPARTMENT_CONFIGS = {
    "pharma_chemistry": {
        "name": "Pharmaceutical Chemistry",
        "description": "Drug design, SAR studies, synthesis, molecular modeling",
        "milestones": [
            {"id": "target_id", "title": "Target Identification", "weight": 10, "description": "Identify biological target and validate druggability"},
            {"id": "lit_review", "title": "Literature Review", "weight": 15, "description": "Comprehensive review of SAR, QSAR, and docking studies"},
            {"id": "virtual_screen", "title": "Virtual Screening", "weight": 15, "description": "Molecular docking, pharmacophore modeling, QSAR predictions"},
            {"id": "hit_id", "title": "Hit Identification", "weight": 10, "description": "Identify lead compounds from screening"},
            {"id": "synthesis", "title": "Synthesis", "weight": 15, "description": "Synthesize lead compounds and analogs"},
            {"id": "assay", "title": "Biological Assay", "weight": 10, "description": "In vitro activity testing"},
            {"id": "sar_optimization", "title": "SAR Optimization", "weight": 10, "description": "Structure-activity relationship optimization"},
            {"id": "admet", "title": "ADMET Profiling", "weight": 5, "description": "Absorption, distribution, metabolism, excretion, toxicity"},
            {"id": "writing", "title": "Manuscript Writing", "weight": 5, "description": "Write and submit research paper"},
        ],
        "databases": ["pubmed", "scifinder", "reaxys", "chembl", "drugbank"],
        "kb_categories": ["literature", "docking", "drug_analysis", "qsar", "patents"],
        "output_types": ["paper", "patent", "sar_table", "molecular_library"],
    },
    "pharmacognosy": {
        "name": "Pharmacognosy",
        "description": "Natural products, phytochemicals, plant extracts, isolation",
        "milestones": [
            {"id": "plant_selection", "title": "Plant Selection", "weight": 10, "description": "Select plant species based on ethnomedical use or chemotaxonomy"},
            {"id": "lit_review", "title": "Literature Review", "weight": 10, "description": "Review phytochemistry and ethnopharmacology"},
            {"id": "collection", "title": "Plant Collection", "weight": 10, "description": "Botanical identification, collection, authentication"},
            {"id": "extraction", "title": "Extraction", "weight": 10, "description": "Prepare crude extracts (methanol, ethanol, hexane, etc.)"},
            {"id": "isolation", "title": "Compound Isolation", "weight": 15, "description": "Column chromatography, HPLC, fractionation"},
            {"id": "characterization", "title": "Structure Elucidation", "weight": 15, "description": "NMR, MS, IR, UV characterization of isolated compounds"},
            {"id": "bioassay", "title": "Bioassay", "weight": 10, "description": "Antimicrobial, antioxidant, cytotoxicity testing"},
            {"id": "mechanism", "title": "Mechanism of Action", "weight": 5, "description": "Molecular docking, pathway analysis"},
            {"id": "writing", "title": "Manuscript Writing", "weight": 5, "description": "Write and submit research paper"},
        ],
        "databases": ["pubmed", "napralert", "knapsack", "chemspider", "pubchem"],
        "kb_categories": ["literature", "docking", "drug_analysis", "pharmacophore"],
        "output_types": ["paper", "phytochemical_profile", "isolation_protocol"],
    },
    "pharmacology": {
        "name": "Pharmacology",
        "description": "Mechanism of action, PK/PD, toxicology, in vivo/in vitro studies",
        "milestones": [
            {"id": "hypothesis", "title": "Hypothesis Formation", "weight": 10, "description": "Define research hypothesis and objectives"},
            {"id": "lit_review", "title": "Literature Review", "weight": 15, "description": "Review mechanism of action, PK/PD, toxicology"},
            {"id": "invitro", "title": "In Vitro Studies", "weight": 15, "description": "Cell-based assays, receptor binding, enzyme inhibition"},
            {"id": "invivo", "title": "In Vivo Studies", "weight": 15, "description": "Animal models, dose-response, efficacy studies"},
            {"id": "pkpd", "title": "PK/PD Analysis", "weight": 10, "description": "Pharmacokinetic profiling, dose optimization"},
            {"id": "toxicology", "title": "Toxicology", "weight": 10, "description": "Acute/chronic toxicity, safety pharmacology"},
            {"id": "mechanism", "title": "Mechanism Elucidation", "weight": 10, "description": "Pathway analysis, biomarker identification"},
            {"id": "writing", "title": "Manuscript Writing", "weight": 5, "description": "Write and submit research paper"},
        ],
        "databases": ["pubmed", "drugbank", "chembl", "kegg", "reactome"],
        "kb_categories": ["literature", "docking", "statistics", "clinical_trials"],
        "output_types": ["paper", "pk_profile", "toxicology_report", "dose_response"],
    },
    "pharmaceutics": {
        "name": "Pharmaceutics",
        "description": "Formulation, drug delivery, stability studies",
        "milestones": [
            {"id": "formulation_design", "title": "Formulation Design", "weight": 15, "description": "Design formulation strategy (tablet, capsule, nanoparticle, etc.)"},
            {"id": "lit_review", "title": "Literature Review", "weight": 10, "description": "Review formulation approaches and excipients"},
            {"id": "preformulation", "title": "Preformulation Studies", "weight": 15, "description": "Solubility, stability, compatibility studies"},
            {"id": "optimization", "title": "Formulation Optimization", "weight": 15, "description": "DOE, response surface methodology"},
            {"id": "characterization", "title": "Characterization", "weight": 10, "description": "Particle size, zeta potential, morphology"},
            {"id": "stability", "title": "Stability Studies", "weight": 10, "description": "ICH guidelines, accelerated stability"},
            {"id": "scaleup", "title": "Scale-Up", "weight": 10, "description": "Pilot scale manufacturing"},
            {"id": "writing", "title": "Manuscript Writing", "weight": 5, "description": "Write and submit research paper"},
        ],
        "databases": ["pubmed", "fda_orange_book", "excipient_db"],
        "kb_categories": ["literature", "protocols", "data_files"],
        "output_types": ["paper", "formulation_spec", "stability_report"],
    },
    "clinical_pharmacy": {
        "name": "Clinical Pharmacy",
        "description": "Clinical trials, patient outcomes, drug safety",
        "milestones": [
            {"id": "protocol", "title": "Protocol Design", "weight": 15, "description": "Design clinical study protocol"},
            {"id": "irb", "title": "IRB Approval", "weight": 10, "description": "Submit and obtain IRB/ethics approval"},
            {"id": "enrollment", "title": "Patient Enrollment", "weight": 15, "description": "Recruit and enroll study participants"},
            {"id": "data_collection", "title": "Data Collection", "weight": 15, "description": "Collect clinical data, adverse events"},
            {"id": "analysis", "title": "Statistical Analysis", "weight": 15, "description": "Analyze outcomes, safety data"},
            {"id": "reporting", "title": "Reporting", "weight": 10, "description": "Write clinical study report"},
            {"id": "publication", "title": "Publication", "weight": 5, "description": "Submit manuscript for publication"},
        ],
        "databases": ["pubmed", "clinicaltrials", "cochrane", "embase"],
        "kb_categories": ["literature", "clinical_trials", "statistics"],
        "output_types": ["paper", "clinical_report", "safety_report"],
    },
}

DEPARTMENT_LIST = [
    {"id": k, "name": v["name"], "description": v["description"]}
    for k, v in DEPARTMENT_CONFIGS.items()
]


def get_department_config(department_id: str) -> dict:
    """Get configuration for a specific department."""
    return DEPARTMENT_CONFIGS.get(department_id, DEPARTMENT_CONFIGS["pharma_chemistry"])


def get_milestones(department_id: str) -> list:
    """Get milestone templates for a department."""
    config = get_department_config(department_id)
    return config.get("milestones", [])


def get_databases(department_id: str) -> list:
    """Get recommended databases for a department."""
    config = get_department_config(department_id)
    return config.get("databases", ["pubmed"])
