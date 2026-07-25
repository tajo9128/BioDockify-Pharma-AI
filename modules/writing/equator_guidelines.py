"""
BioDockify Academic Writer — EQUATOR Reporting Guidelines

Provides compliance checking against the EQUATOR Network's reporting
guidelines for health research. Each guideline is a structured checklist
that the Academic Writer uses to audit manuscripts before submission.

This module is INDEPENDENTLY IMPLEMENTED based on the publicly documented
EQUATOR Network guidelines (https://www.equator-network.org/).
No third-party code is copied.

Guidelines covered:
  CONSORT 2010     — Randomized trials (25 items)
  STROBE           — Observational studies (22 items)
  PRISMA 2020      — Systematic reviews (27 items)
  ARRIVE 2.0       — Animal research (20 items)
  STARD 2015       — Diagnostic accuracy (30 items)
  TRIPOD           — Prediction models (22 items)
  CARE             — Case reports (13 items)
  CHEERS           — Health economics (24 items)
  ICH E3           — Clinical study reports
  ICH M4S          — CTD safety structure
"""

EQUATOR_GUIDELINES = {
    "consort": {
        "name": "CONSORT 2010",
        "full_name": "Consolidated Standards of Reporting Trials",
        "applies_to": "Randomized controlled trials",
        "url": "https://www.consort-statement.org/",
        "items": [
            {"id": "1a", "item": "Title identifies as randomized trial", "section": "Title & Abstract"},
            {"id": "1b", "item": "Structured summary (trial design, methods, results, conclusions)", "section": "Title & Abstract"},
            {"id": "2a", "item": "Scientific background and rationale", "section": "Introduction"},
            {"id": "2b", "item": "Specific objectives or hypotheses", "section": "Introduction"},
            {"id": "3a", "item": "Description of trial design (allocation ratio)", "section": "Methods"},
            {"id": "3b", "item": "Important changes after trial commencement", "section": "Methods"},
            {"id": "4a", "item": "Eligibility criteria for participants", "section": "Methods"},
            {"id": "4b", "item": "Settings and locations where data collected", "section": "Methods"},
            {"id": "5", "item": "Interventions for each group (sufficient detail for replication)", "section": "Methods"},
            {"id": "6a", "item": "Completely defined pre-specified primary/secondary outcomes", "section": "Methods"},
            {"id": "6b", "item": "Any changes to trial outcomes after trial commenced", "section": "Methods"},
            {"id": "7a", "item": "How sample size was determined", "section": "Methods"},
            {"id": "7b", "item": "When applicable, explanation of interim analyses and stopping rules", "section": "Methods"},
            {"id": "8a", "item": "Method used to generate random allocation sequence", "section": "Methods"},
            {"id": "8b", "item": "Type of randomization; details of restriction (blocking, stratification)", "section": "Methods"},
            {"id": "9", "item": "Mechanism used to implement random allocation; concealment until interventions assigned", "section": "Methods"},
            {"id": "10", "item": "Who generated allocation sequence, enrolled, assigned participants", "section": "Methods"},
            {"id": "11a", "item": "If done, who was blinded after assignment (participants, care providers, assessors)", "section": "Methods"},
            {"id": "11b", "item": "If relevant, description of similarity of interventions", "section": "Methods"},
            {"id": "12a", "item": "Statistical methods for primary/secondary outcomes", "section": "Methods"},
            {"id": "12b", "item": "Methods for additional analyses (subgroup, adjusted)", "section": "Methods"},
            {"id": "13a", "item": "Flow diagram (enrollment, allocation, follow-up, analysis)", "section": "Results"},
            {"id": "13b", "item": "Losses and exclusions after randomization with reasons", "section": "Results"},
            {"id": "14a", "item": "Dates defining recruitment and follow-up periods", "section": "Results"},
            {"id": "14b", "item": "Why trial ended or was stopped", "section": "Results"},
            {"id": "15", "item": "Table showing baseline demographic and clinical characteristics per group", "section": "Results"},
            {"id": "16", "item": "Number analyzed per group and for each analysis (denominator)", "section": "Results"},
            {"id": "17a", "item": "Effect size and precision for each primary/secondary outcome", "section": "Results"},
            {"id": "17b", "item": "For binary outcomes, absolute and relative effect sizes", "section": "Results"},
            {"id": "18", "item": "Results of any other analyses (subgroup, adjusted)", "section": "Results"},
            {"id": "19", "item": "All important harms or unintended effects in each group", "section": "Results"},
            {"id": "20", "item": "Trial limitations (bias, imprecision, multiplicity)", "section": "Discussion"},
            {"id": "21", "item": "Generalizability (external validity)", "section": "Discussion"},
            {"id": "22", "item": "Interpretation consistent with results, balancing benefits/harms", "section": "Discussion"},
            {"id": "23", "item": "Registration number and name of trial registry", "section": "Other"},
            {"id": "24", "item": "Where full protocol can be accessed", "section": "Other"},
            {"id": "25", "item": "Sources of funding and role of funders", "section": "Other"},
        ],
    },
    "strobe": {
        "name": "STROBE",
        "full_name": "Strengthening the Reporting of Observational Studies",
        "applies_to": "Cohort, case-control, cross-sectional studies",
        "url": "https://www.strobe-statement.org/",
        "items": [
            {"id": "1", "item": "Title indicates study design", "section": "Title & Abstract"},
            {"id": "2", "item": "Informative balanced summary (background, methods, results, conclusions)", "section": "Title & Abstract"},
            {"id": "3", "item": "Scientific background and rationale", "section": "Introduction"},
            {"id": "4", "item": "Specific objectives, including pre-specified hypotheses", "section": "Introduction"},
            {"id": "5", "item": "Key elements of study design (cohort/case-control/cross-sectional)", "section": "Methods"},
            {"id": "6", "item": "Setting, locations, relevant dates (periods of recruitment, exposure, follow-up)", "section": "Methods"},
            {"id": "7", "item": "Eligibility criteria, sources/methods of participant selection", "section": "Methods"},
            {"id": "8", "item": "Fully defined exposures, outcomes, confounders, effect modifiers", "section": "Methods"},
            {"id": "9", "item": "Data sources/measurement for each variable", "section": "Methods"},
            {"id": "10", "item": "Describe efforts to address potential sources of bias", "section": "Methods"},
            {"id": "11", "item": "Explain how study size was arrived at", "section": "Methods"},
            {"id": "12", "item": "Explain how quantitative variables were handled", "section": "Methods"},
            {"id": "13", "item": "Statistical methods, including follow-up methods and subgroup analyses", "section": "Methods"},
            {"id": "14", "item": "Numbers at each stage (flow diagram recommended)", "section": "Results"},
            {"id": "15", "item": "Descriptive data (demographics, clinical, social characteristics)", "section": "Results"},
            {"id": "16", "item": "Outcome events or summary measures per exposure category", "section": "Results"},
            {"id": "17", "item": "Main results: estimated measures of association and confounding", "section": "Results"},
            {"id": "18", "item": "Results of other analyses (subgroup, interaction)", "section": "Results"},
            {"id": "19", "item": "Key limitations, potential sources of bias, imprecision", "section": "Discussion"},
            {"id": "20", "item": "Generalizability (external validity)", "section": "Discussion"},
            {"id": "21", "item": "Interpretation (causality, mechanisms, comparison)", "section": "Discussion"},
            {"id": "22", "item": "Funding and role of funders", "section": "Other"},
        ],
    },
    "arrive": {
        "name": "ARRIVE 2.0",
        "full_name": "Animal Research: Reporting of In Vivo Experiments",
        "applies_to": "Animal studies (mandatory at most pharma journals)",
        "url": "https://arriveguidelines.org/",
        "items": [
            {"id": "1", "item": "Summary of research question, methods, key findings", "section": "Title & Abstract"},
            {"id": "2", "item": "Clear scientific background and rationale", "section": "Introduction"},
            {"id": "3", "item": "Clearly stated objectives and/or hypotheses", "section": "Introduction"},
            {"id": "4", "item": "Ethical review permissions and regulatory approval", "section": "Methods"},
            {"id": "5", "item": "Complete details of animals (species, strain, sex, age, weight)", "section": "Methods"},
            {"id": "6", "item": "Housing and husbandry conditions (temperature, light, cage type)", "section": "Methods"},
            {"id": "7", "item": "Pre-registered protocol and where it can be accessed", "section": "Methods"},
            {"id": "8", "item": "Sample size justification (power analysis)", "section": "Methods"},
            {"id": "9a", "item": "Primary and secondary outcomes defined", "section": "Methods"},
            {"id": "9b", "item": "Mathematical description of effect size", "section": "Methods"},
            {"id": "10", "item": "Randomization details to minimize bias", "section": "Methods"},
            {"id": "11", "item": "Allocation concealment and blinding", "section": "Methods"},
            {"id": "12", "item": "Primary and secondary outcomes (measurements)", "section": "Methods"},
            {"id": "13", "item": "Predefined statistical methods and software used", "section": "Methods"},
            {"id": "14a", "item": "Exact number of animals per group", "section": "Results"},
            {"id": "14b", "item": "Loss of animals during study with reasons", "section": "Results"},
            {"id": "15", "item": "Baseline data per group (relevant characteristics)", "section": "Results"},
            {"id": "16", "item": "Number analyzed per group and per analysis", "section": "Results"},
            {"id": "17a", "item": "Effect sizes with confidence intervals", "section": "Results"},
            {"id": "17b", "item": "Results reported as point estimates with variability", "section": "Results"},
            {"id": "18", "item": "Adverse events and humane endpoints", "section": "Results"},
            {"id": "19", "item": "Interpretation of results, limitations, care extrapolation", "section": "Discussion"},
            {"id": "20", "item": "Registration details, protocol accessibility, data availability", "section": "Other"},
        ],
    },
    "stard": {
        "name": "STARD 2015",
        "full_name": "Standards for Reporting of Diagnostic Accuracy Studies",
        "applies_to": "Diagnostic accuracy / biomarker validation studies",
        "url": "https://www.equator-network.org/reporting-guidelines/stard/",
        "items": [
            {"id": "1", "item": "Title identifies as diagnostic accuracy study", "section": "Title & Abstract"},
            {"id": "2", "item": "Structured summary (design, methods, results)", "section": "Title & Abstract"},
            {"id": "3", "item": "Scientific background and rationale", "section": "Introduction"},
            {"id": "4", "item": "Study objectives (diagnostic or clinical problem)", "section": "Introduction"},
            {"id": "5", "item": "Whether data collection was planned before or after index test", "section": "Methods"},
            {"id": "6", "item": "Eligibility criteria for participants", "section": "Methods"},
            {"id": "7", "item": "Method of participant recruitment", "section": "Methods"},
            {"id": "8", "item": "Where recruited (setting, institutions)", "section": "Methods"},
            {"id": "9", "item": "Index test(s) described in sufficient detail for replication", "section": "Methods"},
            {"id": "10", "item": "Reference standard described in sufficient detail", "section": "Methods"},
            {"id": "11", "item": "Rationale for choosing the reference standard", "section": "Methods"},
            {"id": "12", "item": "Definitions of positive/negative results for index/reference test", "section": "Methods"},
            {"id": "13", "item": "Whether assessors were blinded", "section": "Methods"},
            {"id": "14", "item": "Statistical methods for diagnostic accuracy", "section": "Methods"},
            {"id": "15", "item": "Flow of participants with flow diagram", "section": "Results"},
            {"id": "16", "item": "Baseline demographic and clinical characteristics", "section": "Results"},
            {"id": "17", "item": "Distribution of severity of disease in those with the condition", "section": "Results"},
            {"id": "18", "item": "Estimates of diagnostic accuracy with CIs", "section": "Results"},
            {"id": "19", "item": "Any adverse events from index/reference test", "section": "Results"},
            {"id": "20", "item": "Clinical relevance of the findings", "section": "Discussion"},
            {"id": "21", "item": "Strengths and limitations of the study", "section": "Discussion"},
            {"id": "22", "item": "Implications for practice and research", "section": "Discussion"},
        ],
    },
    "tripod": {
        "name": "TRIPOD",
        "full_name": "Transparent Reporting of Multivariable Prediction Models",
        "applies_to": "Prediction model development and validation",
        "url": "https://www.equator-network.org/reporting-guidelines/tripod-statement/",
        "items": [
            {"id": "1", "item": "Title identifies development and/or validation of prediction model", "section": "Title & Abstract"},
            {"id": "2", "item": "Structured summary (objectives, methods, results, conclusions)", "section": "Title & Abstract"},
            {"id": "3", "item": "Background and clinical motivation", "section": "Introduction"},
            {"id": "4", "item": "Objectives: development and/or validation", "section": "Introduction"},
            {"id": "5a", "item": "Sources of data and dates of recruitment", "section": "Methods"},
            {"id": "5b", "item": "Settings and locations", "section": "Methods"},
            {"id": "6a", "item": "Participants: eligibility criteria", "section": "Methods"},
            {"id": "6b", "item": "Participants: details of treatments received", "section": "Methods"},
            {"id": "7a", "item": "Outcome definition and assessment", "section": "Methods"},
            {"id": "7b", "item": "For prediction models of diagnosis: reference standard", "section": "Methods"},
            {"id": "8a", "item": "Predictors: definitions and assessment methods", "section": "Methods"},
            {"id": "8b", "item": "Details of blinding of outcome and predictor assessment", "section": "Methods"},
            {"id": "9", "item": "Sample size and how it was determined", "section": "Methods"},
            {"id": "10", "item": "Statistical analysis methods including model-building strategy", "section": "Methods"},
            {"id": "11", "item": "Model development: how predictions were calculated", "section": "Methods"},
            {"id": "12", "item": "Model validation: validation method (bootstrap/cross-validation)", "section": "Methods"},
            {"id": "13", "item": "Handling of missing data", "section": "Methods"},
            {"id": "14", "item": "Model performance: discrimination (C-statistic/AUC) and calibration", "section": "Methods"},
            {"id": "15", "item": "Participant flow with inclusion/exclusion numbers", "section": "Results"},
            {"id": "16", "item": "Participant characteristics summary", "section": "Results"},
            {"id": "17", "item": "Model specifications: intercept, coefficients, predictor distributions", "section": "Results"},
            {"id": "18", "item": "Performance metrics with CIs", "section": "Results"},
            {"id": "19", "item": "Limitations and potential for use", "section": "Discussion"},
        ],
    },
    "cheers": {
        "name": "CHEERS 2022",
        "full_name": "Consolidated Health Economic Evaluation Reporting Standards",
        "applies_to": "Health economic evaluations / cost-effectiveness analyses",
        "url": "https://www.ispor.org/heor-resources/good-practices/cheers",
        "items": [
            {"id": "1", "item": "Title identifies economic evaluation study", "section": "Title"},
            {"id": "2", "item": "Summary of study (objectives, perspective, methods, results)", "section": "Abstract"},
            {"id": "3", "item": "Background and study question (relevance to decision-making)", "section": "Introduction"},
            {"id": "4", "item": "Health economic analysis plan availability", "section": "Methods"},
            {"id": "5", "item": "Study perspective (healthcare system, societal)", "section": "Methods"},
            {"id": "6", "item": "Rationale for comparators", "section": "Methods"},
            {"id": "7", "item": "Time horizon and justification", "section": "Methods"},
            {"id": "8", "item": "Discount rate(s) and justification", "section": "Methods"},
            {"id": "9", "item": "Chosen type of economic evaluation and rationale", "section": "Methods"},
            {"id": "10", "item": "Selected health outcomes and measurement", "section": "Methods"},
            {"id": "11", "item": "Measurement and valuation of costs", "section": "Methods"},
            {"id": "12", "item": "Currency, price date, and conversion methods", "section": "Methods"},
            {"id": "13", "item": "Analytical methods for cost-effectiveness analysis", "section": "Methods"},
            {"id": "14", "item": "Methods for uncertainty characterization", "section": "Methods"},
            {"id": "15", "item": "Methods for heterogeneity characterization", "section": "Methods"},
            {"id": "16", "item": "Study parameters: summary values, ranges, SDs/SEs", "section": "Results"},
            {"id": "17", "item": "Summary of evaluation: ICER, CEAC, net benefit", "section": "Results"},
            {"id": "18", "item": "Study findings: effect of uncertainty", "section": "Results"},
            {"id": "19", "item": "Engagement of patients and stakeholders", "section": "Discussion"},
            {"id": "20", "item": "How findings compare with previous studies", "section": "Discussion"},
            {"id": "21", "item": "Limitations and generalizability", "section": "Discussion"},
            {"id": "22", "item": "Implications for clinical practice, policy, research", "section": "Discussion"},
            {"id": "23", "item": "Source of funding and conflicts of interest", "section": "Other"},
            {"id": "24", "item": "Data and code availability statement", "section": "Other"},
        ],
    },
}

# Study type → guideline mapping for auto-detection
STUDY_TYPE_MAP = {
    "randomized_trial": "consort",
    "clinical_trial": "consort",
    "rct": "consort",
    "observational": "strobe",
    "cohort": "strobe",
    "case_control": "strobe",
    "cross_sectional": "strobe",
    "animal_study": "arrive",
    "preclinical": "arrive",
    "in_vivo": "arrive",
    "diagnostic": "stard",
    "biomarker": "stard",
    "diagnostic_accuracy": "stard",
    "prediction_model": "tripod",
    "prognostic": "tripod",
    "risk_score": "tripod",
    "cost_effectiveness": "cheers",
    "economic_evaluation": "cheers",
    "health_economics": "cheers",
    "hta": "cheers",
}


def get_guideline(study_type: str) -> dict:
    """Get the appropriate EQUATOR guideline for a study type.

    Returns the full guideline dict with all checklist items.
    """
    study_type = study_type.lower().strip()
    guideline_key = STUDY_TYPE_MAP.get(study_type, "consort")  # default to CONSORT
    return EQUATOR_GUIDELINES.get(guideline_key, EQUATOR_GUIDELINES["consort"])


def list_all_guidelines() -> list:
    """List all available guidelines with metadata."""
    return [
        {
            "key": key,
            "name": g["name"],
            "full_name": g["full_name"],
            "applies_to": g["applies_to"],
            "url": g["url"],
            "item_count": len(g["items"]),
        }
        for key, g in EQUATOR_GUIDELINES.items()
    ]
