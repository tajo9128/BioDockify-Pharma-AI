"""
Pharma Thesis Structure & Templates (Master Framework)
Defines the branch-aware structure, strictly mapped to degree levels and pharmacy branches.
"""
from enum import Enum
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class DegreeType(str, Enum):
    B_PHARM = "B.Pharm"
    M_PHARM = "M.Pharm"
    PHD = "PhD"
    PHARM_D = "Pharm.D"

class PharmaBranch(str, Enum):
    PHARMACOLOGY = "Pharmacology"
    PHARMACEUTICS = "Pharmaceutics"
    PHARMA_CHEMISTRY = "Pharma Chemistry"
    PHARMACOGNOSY = "Pharmacognosy"
    CLINICAL_PHARMACY = "Clinical Pharmacy"
    REGULATORY = "Regulatory"
    PHARMA_ANALYSIS = "Pharma Analysis"
    GENERAL = "General"

class ChapterId(str, Enum):
    FRONT_MATTER = "front_matter"
    INTRODUCTION = "chapter_1"
    LITERATURE_REVIEW = "chapter_2"
    MATERIALS_METHODS = "chapter_3"
    RESULTS = "chapter_4"
    DISCUSSION = "chapter_5"
    CONCLUSION = "chapter_6"
    REFERENCES = "references"
    APPENDICES = "appendices"

class SectionRequirement(BaseModel):
    title: str
    description: str
    required_proofs: List[str] = []
    forbidden_content: List[str] = []
    branch_focus: Dict[PharmaBranch, str] = {}
    word_limit: Optional[int] = None

class ChapterTemplate(BaseModel):
    id: ChapterId
    title: str
    sections: List[SectionRequirement]
    global_rules: List[str] = []
    proof_type_required: str

# MASTER PHARMA THESIS DESIGN
THESIS_STRUCTURE: Dict[ChapterId, ChapterTemplate] = {
    ChapterId.FRONT_MATTER: ChapterTemplate(
        id=ChapterId.FRONT_MATTER,
        title="Front Matter",
        global_rules=[
            "NON-NEGOTIABLE and branch-independent",
            "Abstract cannot exceed word limit",
            "Abstract must contain results",
            "No citations in abstract"
        ],
        sections=[
            SectionRequirement(title="Title Page", description="Degree, branch, institution. Title must match objectives."),
            SectionRequirement(title="Declaration", description="Originality statement and student responsibility."),
            SectionRequirement(title="Certificate", description="Supervisor authentication."),
            SectionRequirement(title="Acknowledgement", description="Funding, guidance, lab support."),
            SectionRequirement(title="Abstract", description="Background, Objective, Methodology, Key results, Conclusion.", word_limit=300)
        ],
        proof_type_required="Administrative Documents"
    ),
    ChapterId.INTRODUCTION: ChapterTemplate(
        id=ChapterId.INTRODUCTION,
        title="Introduction (Context & Justification)",
        global_rules=["No results", "Citations mandatory", "Broad to narrow flow", "End with clear research objective"],
        sections=[
            SectionRequirement(title="Background of Disease", description="Context of the therapeutic area."),
            SectionRequirement(title="Epidemiology", description="Global and local burden stats."),
            SectionRequirement(title="Pathophysiology", description="Biological mechanism of the condition."),
            SectionRequirement(title="Existing Therapies", description="Current standard of care."),
            SectionRequirement(title="Limitations", description="Gaps in current treatment."),
            SectionRequirement(title="Need of Study", description="Specific justification for this research.")
        ],
        proof_type_required="WHO / Global Stats Citations"
    ),
    ChapterId.LITERATURE_REVIEW: ChapterTemplate(
        id=ChapterId.LITERATURE_REVIEW,
        title="Literature Review (Critical Analysis)",
        global_rules=["Must be comparative, not narrative", "Every subsection must end with a gap", "No methods or results"],
        sections=[
            SectionRequirement(title="Review of Disease", description="In-depth analysis of condition history."),
            SectionRequirement(title="Review of Drugs / Targets", description="Analysis of molecular targets or active agents."),
            SectionRequirement(title="Review of Experimental Models", description="Evaluation of previous models used."),
            SectionRequirement(title="Research Gaps", description="Summary of identified voids in knowledge.")
        ],
        proof_type_required="Indexed Journal Citations (Scopus/WoS)"
    ),
    ChapterId.MATERIALS_METHODS: ChapterTemplate(
        id=ChapterId.MATERIALS_METHODS,
        title="Materials and Methods (Reproducibility)",
        global_rules=["Past tense only", "Reproducible", "No interpretation", "Ethics approval mandatory where applicable"],
        sections=[
            SectionRequirement(title="Materials", description="Reagents, chemicals, biological sources."),
            SectionRequirement(title="Instruments", description="Models, manufacturers, settings."),
            SectionRequirement(title="Experimental Design", description="Step-by-step procedure."),
            SectionRequirement(title="Statistical Analysis", description="Software used, significance level.")
        ],
        proof_type_required="Reproducible Configs / Lab Protocols"
    ),
    ChapterId.RESULTS: ChapterTemplate(
        id=ChapterId.RESULTS,
        title="Results (Data Only)",
        global_rules=["No citations", "No discussion words", "Numerical data required", "Tables before graphs"],
        sections=[
            SectionRequirement(title="Tables", description="Structured data presentation."),
            SectionRequirement(title="Graphs", description="Visual trends and analysis."),
            SectionRequirement(title="Observations", description="Factual description of what was measured.")
        ],
        proof_type_required="Raw Metrics & Tables"
    ),
    ChapterId.DISCUSSION: ChapterTemplate(
        id=ChapterId.DISCUSSION,
        title="Discussion (Meaning & Comparison)",
        global_rules=["Explain 'why', not repeat results", "Compare with ≥2 studies", "Limit speculation"],
        sections=[
            SectionRequirement(title="Interpretation", description="Meaning of individual results."),
            SectionRequirement(title="Comparison with Literature", description="Aligning with previous work."),
            SectionRequirement(title="Mechanism Explanation", description="Biological or chemical explanation of outcomes.")
        ],
        proof_type_required="Literature Comparison Matrix"
    ),
    ChapterId.CONCLUSION: ChapterTemplate(
        id=ChapterId.CONCLUSION,
        title="Conclusion (Closure)",
        global_rules=["No new data", "Answer objectives", "Practical relevance"],
        sections=[
            SectionRequirement(title="Summary", description="High-level wrap-up of findings."),
            SectionRequirement(title="Significance", description="Impact on the field or patients."),
            SectionRequirement(title="Future Scope", description="Recommendations for follow-up studies.")
        ],
        proof_type_required="Logical Significance Statement"
    )
}

# Branch Specific Focal Points & Mandatory Requirements
BRANCH_DATA: Dict[PharmaBranch, Dict[str, Any]] = {
    PharmaBranch.PHARMACOLOGY: {
        "intro_focus": "Emphasis on disease models",
        "methods_mandatory": "Animal ethics / Cell line authentication",
        "results_data": "% inhibition, p-values, behavioral scores",
        "discussion_mechanism": True
    },
    PharmaBranch.PHARMACEUTICS: {
        "intro_focus": "Emphasis on dosage form relevance",
        "methods_mandatory": "Formulation composition / Scale-up params",
        "results_data": "Release profiles, zeta potential, loading efficiency",
        "discussion_mechanism": False  # Limited to physico-chemical
    },
    PharmaBranch.PHARMA_CHEMISTRY: {
        "intro_focus": "Emphasis on molecular target context",
        "methods_mandatory": "Reaction conditions / Purification methods",
        "results_data": "Yields, NMR/IR spectra, docking scores",
        "discussion_mechanism": True  # SAR focus
    },
    PharmaBranch.PHARMACOGNOSY: {
        "intro_focus": "Emphasis on traditional usage & botanical origin",
        "methods_mandatory": "Plant authentication (Herbal voucher No.)",
        "results_data": "Phytochemical screening, TLC/HPTLC profiles",
        "discussion_mechanism": True  # Bioactivity correlation
    },
    PharmaBranch.CLINICAL_PHARMACY: {
        "intro_focus": "Emphasis on patient burden & clinical guidelines",
        "methods_mandatory": "IEC approval / Patient consent forms",
        "results_data": "Patient outcomes, ADR counts, compliance stats",
        "discussion_mechanism": False  # Focus on outcomes
    },
    PharmaBranch.REGULATORY: {
        "intro_focus": "Emphasis on regulatory gap & compliance needs",
        "methods_mandatory": "Document sources / Guideline versions",
        "results_data": "Compliance matrices, audit findings",
        "discussion_mechanism": False
    },
    PharmaBranch.PHARMA_ANALYSIS: {
        "intro_focus": "Emphasis on analytical need & method gap",
        "methods_mandatory": "Validation parameters (ICH Q2)",
        "results_data": "Validation statistics (LOD, LOQ, precision)",
        "discussion_mechanism": False
    },
    PharmaBranch.GENERAL: {
        "intro_focus": "General pharmaceutical research context",
        "methods_mandatory": "Standard laboratory procedures / Documentation",
        "results_data": "Quantitative and qualitative metrics",
        "discussion_mechanism": True
    }
}

# PHARM.D SPECIFIC CLINICAL PROJECT DESIGN
PHARM_D_STRUCTURE: Dict[ChapterId, ChapterTemplate] = {
    ChapterId.FRONT_MATTER: ChapterTemplate(
        id=ChapterId.FRONT_MATTER,
        title="Front Matter (Pharm.D Mandatory)",
        global_rules=[
            "Abstract must mention study design",
            "Abstract must include patient number",
            "Ethics approval ID mandatory",
            "No chemical/mechanistic claims"
        ],
        sections=[
            SectionRequirement(title="Title Page", description="Clinical & outcome-focused title, degree, hospital affiliation."),
            SectionRequirement(title="Declaration", description="Original clinical work statement."),
            SectionRequirement(title="Certificate", description="Guide and Clinical Preceptor authentication."),
            SectionRequirement(title="Acknowledgement", description="Hospital staff and Ethics committee support."),
            SectionRequirement(title="Abstract", description="Background (clinical relevance), Objective, Study design, Key outcomes, Conclusion.", word_limit=350)
        ],
        proof_type_required="IEC Approval & Clinical Documents"
    ),
    ChapterId.INTRODUCTION: ChapterTemplate(
        id=ChapterId.INTRODUCTION,
        title="Chapter 1 – Introduction (Clinical Context)",
        global_rules=[
            "Focus on patient care",
            "No molecular mechanisms",
            "Cite guidelines: WHO, NICE, ICMR"
        ],
        sections=[
            SectionRequirement(title="Background of Disease", description="Clinical context of the condition."),
            SectionRequirement(title="Epidemiology", description="Disease burden and prevalence."),
            SectionRequirement(title="Pathophysiology", description="Clinical relevance only; no molecular detail."),
            SectionRequirement(title="Existing Treatment Guidelines", description="Current standard of care recommendations."),
            SectionRequirement(title="Drug-Related Problems", description="Clinical issues identified in current therapy."),
            SectionRequirement(title="Role of Clinical Pharmacist", description="Impact in this therapeutic area."),
            SectionRequirement(title="Need of the Study", description="Specific clinical justification.")
        ],
        proof_type_required="Clinical Guidelines Citations"
    ),
    ChapterId.LITERATURE_REVIEW: ChapterTemplate(
        id=ChapterId.LITERATURE_REVIEW,
        title="Chapter 2 – Literature Review (Clinical Evidence)",
        global_rules=[
            "Prefer RCTs, meta-analyses, cohort studies",
            "No animal studies",
            "Highlight safety, adherence, outcomes"
        ],
        sections=[
            SectionRequirement(title="Review of Disease Burden", description="Analysis of condition's clinical impact."),
            SectionRequirement(title="Review of Current Therapies", description="Evidence-based pharmacological review."),
            SectionRequirement(title="Review of Clinical Studies", description="Summarization of existing patient trials."),
            SectionRequirement(title="Review of Drug-Related Problems", description="Documentation of previous clinical issues."),
            SectionRequirement(title="Research Gaps", description="Identification of lack in clinical knowledge.")
        ],
        proof_type_required="Systematic Reviews & Meta-Analyses"
    ),
    ChapterId.MATERIALS_METHODS: ChapterTemplate(
        id=ChapterId.MATERIALS_METHODS,
        title="Chapter 3 – Methodology (Patient-Based)",
        global_rules=[
            "MANDATORY: IEC approval number",
            "MANDATORY: Patient consent & CRF",
            "No lab synthesis or formulation development"
        ],
        sections=[
            SectionRequirement(title="Study Design", description="Type of clinical study (e.g., Observational, Prospective)."),
            SectionRequirement(title="Study Site", description="Hospital / Clinical department."),
            SectionRequirement(title="Study Duration", description="Period of data collection."),
            SectionRequirement(title="Study Population", description="Inclusion/Exclusion criteria."),
            SectionRequirement(title="Data Collection Procedure", description="Step-by-step patient monitoring."),
            SectionRequirement(title="Outcome Measures", description="Parameters of success."),
            SectionRequirement(title="Ethical Considerations", description="Patient privacy and consent details.")
        ],
        proof_type_required="IEC Approval & CRF"
    ),
    ChapterId.RESULTS: ChapterTemplate(
        id=ChapterId.RESULTS,
        title="Chapter 4 – Results (Clinical Data)",
        global_rules=[
            "Tables first, graphs second",
            "Absolute numbers + percentages required",
            "No interpretation"
        ],
        sections=[
            SectionRequirement(title="Demographic Details", description="Patient age, gender, characteristics."),
            SectionRequirement(title="Disease Distribution", description="Prevalence in the studied population."),
            SectionRequirement(title="Prescribing Pattern Analysis", description="Medications actually administered."),
            SectionRequirement(title="Drug-Related Problems Identified", description="Medication errors / ADRs found."),
            SectionRequirement(title="Interventions by Clinical Pharmacist", description="Corrective actions taken."),
            SectionRequirement(title="Clinical Outcomes", description="Impact on patient health.")
        ],
        proof_type_required="CRF Data & Statistical Tables"
    ),
    ChapterId.DISCUSSION: ChapterTemplate(
        id=ChapterId.DISCUSSION,
        title="Chapter 5 – Discussion (Clinical Interpretation)",
        global_rules=[
            "Compare with ≥3 clinical studies",
            "Focus on patient safety & outcomes",
            "No mechanistic speculation or chemistry detail"
        ],
        sections=[
            SectionRequirement(title="Interpretation of Findings", description="Clinical meaning of the results."),
            SectionRequirement(title="Comparison with Previous Studies", description="Benchmarking against clinical literature."),
            SectionRequirement(title="Clinical Significance", description="Real-world impact on patient care."),
            SectionRequirement(title="Impact of Pharmacist Interventions", description="Evidence of clinical benefit.")
        ],
        proof_type_required="Clinical Comparison Matrix"
    ),
    ChapterId.CONCLUSION: ChapterTemplate(
        id=ChapterId.CONCLUSION,
        title="Chapter 6 – Conclusion and Recommendations",
        global_rules=[
            "Focus on rational drug use",
            "Highlight improved patient care"
        ],
        sections=[
            SectionRequirement(title="Summary of Findings", description="Concise wrap-up of clinical work."),
            SectionRequirement(title="Clinical Implications", description="Influence on future clinical practice."),
            SectionRequirement(title="Recommendations for Practice", description="Direct advice for hospital use.")
        ],
        proof_type_required="Policy / Practice Recommendations"
    )
}

def get_template(chapter_id: str, degree: DegreeType = DegreeType.PHD) -> Optional[ChapterTemplate]:
    try:
        cid = ChapterId(chapter_id)
        if degree == DegreeType.PHARM_D:
            return PHARM_D_STRUCTURE.get(cid)
        return THESIS_STRUCTURE.get(cid)
    except ValueError:
        return None

def get_branch_profile(branch: PharmaBranch) -> Dict[str, Any]:
    return BRANCH_DATA.get(branch, BRANCH_DATA[PharmaBranch.GENERAL])
