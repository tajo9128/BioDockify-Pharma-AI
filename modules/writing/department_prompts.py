"""Department-specific Pharma Thesis writing instructions for all 8 branches."""
from modules.thesis.structure import PharmaBranch

DEPARTMENT_PROMPTS = {
    PharmaBranch.PHARMACOLOGY: {
        "intro_focus": "Emphasis on disease models, drug-receptor interactions, signaling pathways, and therapeutic targets. Include WHO disease burden statistics and clinical relevance.",
        "methods_mandatory": "In vivo animal models (species, strain, ethical approval), in vitro assays (cell lines, reagents), molecular docking protocols (software, PDB IDs, parameters), statistical tests (n≥6 per group, ANOVA/Tukey).",
        "results_data": "Dose-response curves (IC50/EC50), binding affinities, behavioral scores, biochemical markers, histopathology images, molecular docking scores (kcal/mol) and interaction diagrams.",
        "discussion_mechanism": "Mechanism of action, binding site analysis, SAR relationships, physiological implications of observed effects, comparison with standard drugs.",
        "writing_style": "Use passive voice for methodology. Report p-values precisely. Mention animal ethics approval numbers. Use IUPAC nomenclature for drug names.",
        "citation_style": "Cite original pharmacology papers, NOT review articles, for key mechanisms. Minimum 40 citations for PhD thesis.",
    },
    PharmaBranch.PHARMACEUTICS: {
        "intro_focus": "Emphasis on drug delivery systems, formulation challenges, bioavailability issues, and controlled release. Include market analysis of current formulations.",
        "methods_mandatory": "Formulation preparation (method, excipients, equipment), characterization (particle size, zeta potential, SEM/TEM), dissolution testing (USP apparatus, media), stability studies (ICH guidelines).",
        "results_data": "Particle size distribution, entrapment efficiency (%), drug loading (%), in vitro release profiles (cumulative % vs time), release kinetics (zero-order, first-order, Higuchi, Korsmeyer-Peppas), stability data.",
        "discussion_mechanism": "Release mechanism, formulation optimization rationale, comparative analysis with marketed products, scale-up feasibility.",
        "writing_style": "Report specifications of equipment and chemicals (manufacturer, grade). Use USP terminology for dissolution testing. Include batch numbers.",
        "citation_style": "Cite recent formulation patents and industrial literature. Minimum 30 citations for PhD thesis.",
    },
    PharmaBranch.PHARMA_CHEMISTRY: {
        "intro_focus": "Emphasis on drug design, SAR studies, synthetic routes, molecular modeling, and computational chemistry. Include QSAR/pharmacophore background.",
        "methods_mandatory": "Synthetic schemes (yields, reagents, conditions), characterization (NMR, IR, Mass, CHN analysis, melting point), computational methods (software, force field, basis set), docking protocol (Vina, Glide, GOLD).",
        "results_data": "Compound characterization data, spectral peaks with assignments, docking scores and interaction energies, QSAR models (R², Q², RMSE), synthetic yields.",
        "discussion_mechanism": "SAR analysis, pharmacophore model interpretation, binding mode analysis, comparison with lead compounds, synthetic feasibility and drug-likeness.",
        "writing_style": "Use systematic IUPAC names. Report NMR data as δ ppm (multiplicity, J in Hz). Include elemental analysis results. Number all compounds.",
        "citation_style": "Cite original synthetic procedures. Use ACS style reference numbering. Minimum 35 citations for PhD thesis.",
    },
    PharmaBranch.PHARMACOGNOSY: {
        "intro_focus": "Emphasis on natural products, traditional medicine validation, phytochemical isolation, and herbal standardization. Include ethnopharmacological context.",
        "methods_mandatory": "Plant collection (voucher specimen, authentication), extraction (solvent, method, yield), phytochemical screening (qualitative tests), chromatographic separation (TLC, column, HPLC), spectroscopic characterization.",
        "results_data": "Extractive yields (%), phytochemical test results, chromatographic profiles (Rf values, retention times), isolated compound characterization, pharmacological activity results.",
        "discussion_mechanism": "Chemotaxonomic significance, structure-activity relationship of isolated compounds, traditional use validation, comparison with standard markers.",
        "writing_style": "Provide botanical names with authority. Include herbarium voucher numbers. Use standard pharmacognosy terminology for plant parts.",
        "citation_style": "Cite classical pharmacognosy texts and recent natural product journals. Minimum 30 citations for PhD thesis.",
    },
    PharmaBranch.CLINICAL_PHARMACY: {
        "intro_focus": "Emphasis on patient care, therapeutic outcomes, drug utilization, pharmacovigilance, and clinical guidelines. Include hospital/community setting context.",
        "methods_mandatory": "Study design (prospective/retrospective/observational), patient demographics, inclusion/exclusion criteria, sample size calculation, statistical plan, ethics approval (IEC number), consent forms.",
        "results_data": "Patient demographics table, clinical outcome measures (efficacy, safety endpoints), adverse drug reaction data, drug utilization metrics (DDD/100 bed-days), quality of life scores.",
        "discussion_mechanism": "Clinical significance vs. statistical significance, comparison with standard therapy, therapeutic guidelines alignment, cost-effectiveness implications.",
        "writing_style": "Write with patient-centric focus. No molecular mechanisms. Use clinical terminology. Report NNT/NNH where applicable.",
        "citation_style": "Cite clinical guidelines (NICE, IDSA, ASHP), landmark clinical trials, and recent meta-analyses. Use Vancouver referencing. Minimum 25 citations.",
    },
    PharmaBranch.REGULATORY: {
        "intro_focus": "Emphasis on regulatory frameworks (FDA, EMA, CDSCO), drug approval pathways, quality systems, and compliance. Include regulatory history of relevant products.",
        "methods_mandatory": "Regulatory documentation review, quality risk assessment (ICH Q9), analytical method validation (ICH Q2), stability study design (ICH Q1), dossier compilation strategy.",
        "results_data": "Regulatory pathway analysis, CMC documentation modules, quality control test results, stability study outcomes, compliance gap analysis.",
        "discussion_mechanism": "Regulatory strategy justification, comparative regulatory analysis (FDA vs EMA vs CDSCO), quality-by-design implementation, audit findings.",
        "writing_style": "Use regulatory terminology precisely (e.g., ANDA vs NDA vs 505(b)(2)). Include DMF references. Cite specific 21 CFR sections.",
        "citation_style": "Cite ICH guidelines, FDA guidance documents, pharmacopoeia (USP, IP, BP, EP). Include regulatory submissions as references where permissible.",
    },
    PharmaBranch.PHARMA_ANALYSIS: {
        "intro_focus": "Emphasis on analytical method development, validation, quality control, and instrumentation. Include current analytical challenges for the drug/matrix.",
        "methods_mandatory": "Instrument parameters (HPLC column, mobile phase, detection wavelength, flow rate), sample preparation (extraction, dilution), method validation parameters (ICH Q2: accuracy, precision, LOD, LOQ, linearity, robustness).",
        "results_data": "Chromatograms, calibration curves, validation tables (%RSD, recovery, LOD/LOQ), degradation study results (acid, base, oxidation, thermal, photolytic), assay results.",
        "discussion_mechanism": "Method optimization rationale, comparison with reported methods, force degradation pathways, stability-indicating nature, applicability for routine QC.",
        "writing_style": "Include all chromatographic conditions in detail for reproducibility. Report retention times with ±SD. Use pharmacopoeia terminology.",
        "citation_style": "Cite ICH guidelines, pharmacopoeia monographs, and reference analytical methods. Minimum 30 citations for PhD thesis.",
    },
    PharmaBranch.GENERAL: {
        "intro_focus": "General pharmaceutical research with broad scope. Adapt to the specific topic area.",
        "methods_mandatory": "Standard research methodology appropriate to the field.",
        "results_data": "Quantitative and qualitative research outputs.",
        "discussion_mechanism": "Compare findings with existing literature and draw appropriate conclusions.",
        "writing_style": "Standard academic pharma English with appropriate terminology.",
        "citation_style": "Cite relevant peer-reviewed literature. Minimum 25 citations.",
    },
}


def get_department_prompt(branch: PharmaBranch) -> dict:
    """Get the full department-specific writing prompt for a pharma branch."""
    return DEPARTMENT_PROMPTS.get(branch, DEPARTMENT_PROMPTS[PharmaBranch.GENERAL])


def build_doc_prompt(doc_type: str, degree: str, branch: PharmaBranch, topic: str) -> str:
    """
    Build a comprehensive document-generation prompt with department + degree context.

    doc_type: 'phd_thesis', 'mpharm_thesis', 'bpharm_thesis', 'pharmd_thesis',
              'review_article', 'research_paper', 'meta_analysis', 'case_study'
    """
    dp = get_department_prompt(branch)

    doc_templates = {
        "research_paper": {
            "structure": "IMRaD: Abstract → Introduction → Methods → Results → Discussion → Conclusion → References",
            "sections": ["Abstract (250 words)", "Introduction", "Materials and Methods", "Results", "Discussion", "Conclusion", "References"],
            "word_target": "4000-6000 words",
            "key_requirements": "Original research contribution, clearly stated hypothesis, reproducible methods, statistical rigor"
        },
        "review_article": {
            "structure": "Thematic: Abstract → Introduction → Thematic Sections → Critical Analysis → Future Directions → References",
            "sections": ["Abstract (200 words)", "Introduction & Background", "Thematic Review Sections (3-5)", "Critical Analysis & Research Gaps", "Future Perspectives", "References"],
            "word_target": "5000-8000 words",
            "key_requirements": "Comprehensive coverage, critical analysis not just summary, identification of research gaps, balanced perspective"
        },
        "phd_thesis": {
            "structure": "7 Chapters: Introduction → Literature Review → Gap & Objectives → Materials & Methods → Results → Discussion → Conclusion",
            "sections": ["Chapter 1: Introduction", "Chapter 2: Literature Review", "Chapter 3: Research Gap & Objectives", "Chapter 4: Materials & Methods", "Chapter 5: Results", "Chapter 6: Discussion", "Chapter 7: Summary & Conclusion"],
            "word_target": "40,000-60,000 words",
            "key_requirements": "Original contribution to knowledge, comprehensive literature review (40+ citations), rigorous methodology, critical discussion"
        },
        "mpharm_thesis": {
            "structure": "6 Chapters: Introduction → Literature Review → Materials & Methods → Results → Discussion → Conclusion",
            "sections": ["Chapter 1: Introduction", "Chapter 2: Literature Review", "Chapter 3: Materials & Methods", "Chapter 4: Results", "Chapter 5: Discussion", "Chapter 6: Conclusion"],
            "word_target": "25,000-35,000 words",
            "key_requirements": "Thorough experimental work, competent methodology, clear presentation of results, contextual discussion (20+ citations)"
        },
        "bpharm_thesis": {
            "structure": "5 Chapters: Introduction → Literature Review → Methodology → Results → Conclusion",
            "sections": ["Chapter 1: Introduction", "Chapter 2: Literature Review", "Chapter 3: Methodology", "Chapter 4: Results & Analysis", "Chapter 5: Conclusion"],
            "word_target": "10,000-15,000 words",
            "key_requirements": "Clear understanding of topic, literature-based or simple experimental work acceptable (10+ citations), proper formatting"
        },
        "pharmd_thesis": {
            "structure": "Clinical: Introduction → Literature Review → Methodology (Clinical) → Results → Discussion (Clinical) → Conclusion",
            "sections": ["Introduction & Background", "Literature Review", "Clinical Methodology", "Clinical Results", "Discussion", "Conclusion & Recommendations"],
            "word_target": "20,000-30,000 words",
            "key_requirements": "Clinical/patient focus, no molecular mechanisms, evidence-based practice emphasis, IRB/IEC ethics documentation (15+ citations)"
        },
    }

    dt = doc_templates.get(doc_type, doc_templates["review_article"])

    prompt = f"""You are writing a {doc_type.replace('_', ' ')} in the Department of {branch.value}.

TOPIC: {topic}
DEGREE LEVEL: {degree}
DOCUMENT STRUCTURE: {dt['structure']}
TARGET LENGTH: {dt['word_target']}
KEY REQUIREMENTS: {dt['key_requirements']}

--- DEPARTMENT WRITING GUIDELINES ---
INTRO FOCUS: {dp['intro_focus']}
METHODS: {dp['methods_mandatory']}
RESULTS/DATA: {dp['results_data']}
DISCUSSION: {dp['discussion_mechanism']}
WRITING STYLE: {dp['writing_style']}
CITATIONS: {dp['citation_style']}
---

SECTIONS TO GENERATE:
{chr(10).join(f"{i+1}. {s}" for i, s in enumerate(dt['sections']))}

INSTRUCTIONS:
- Follow the department-specific writing guidelines above.
- Adhere to the document structure exactly.
- Use formal academic pharma English with branch-appropriate terminology.
- Each section should meet the target length proportionally.
- Cite references in the required citation style for this department.

Write the complete {doc_type.replace('_', ' ')}:"""

    return prompt
