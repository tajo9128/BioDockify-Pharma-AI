"""
Pharma Prompt Library for the BioDockify AI Engine.

Small local models (Bonsai-8B at 1-bit) respond far better with directive,
domain-anchored prompts than with raw user input. This library provides pharma-
specific templates that BioDockify's API handlers (writing.py, claim_verify.py,
md_lite.py, etc.) can prepend to user prompts — WITHOUT modifying Agent Zero
core prompt code.

Design rules:
  - Each template returns a plain string; the caller decides how to combine it
    with the user prompt and KB context block.
  - Templates are conservative: they tell the model to refuse rather than
    fabricate (critical for pharma safety / regulatory work).
  - Templates cite the ICH/FDA/EMA framework they assume, so outputs stay
    submission-aware.
  - The library is intentionally import-safe: no Flask, no Agent Zero, no I/O.

Usage:
    from modules.local_llm.pharma_prompts import PharmaPromptLibrary as P
    sys_prompt = P.system_preamble() + P.literature_review() + kb_context
"""

from typing import List


class PharmaPromptLibrary:
    """Pharmaceutical research prompt templates tuned for small local models.

    All methods are static and return strings. Pure functions, no I/O.
    """

    # ------------------------------------------------------------------ base
    @staticmethod
    def system_preamble() -> str:
        """Universal pharma preamble — always prepended first.

        Anchors the model as a pharma research assistant and sets the no-
        fabrication rule that matters most for safety/regulatory writing.
        """
        return (
            "You are the BioDockify AI Engine, a pharmaceutical research "
            "assistant. You serve a PhD-level researcher and must produce text "
            "suitable for regulatory and academic use.\n\n"
            "HARD RULES:\n"
            "1. NEVER fabricate citations, dosages, IC50 values, or trial "
            "results. If a specific number is not in the provided context, "
            "write [NOT IN CONTEXT] and stop.\n"
            "2. When unsure about a safety claim, say so explicitly. Do not "
            "hedge by inventing a plausible-sounding value.\n"
            "3. Distinguish in-vitro from in-vivo from clinical evidence. "
            "Never generalize a preclinical result to a clinical claim.\n"
            "4. Use ICH / FDA / EMA terminology where applicable "
            "(e.g., 'primary endpoint', 'ITT', 'bioequivalence', 'Cmax').\n"
            "5. Prefer Vancouver-style citations: [1], [2], …\n"
            "6. Mark any inference beyond the supplied context with [INFERENCE].\n"
        )

    # -------------------------------------------------------- research tasks
    @staticmethod
    def literature_review() -> str:
        return (
            "\nTASK: Literature review synthesis.\n"
            "Structure the answer as:\n"
            "  - Theme / subtopic heading\n"
            "  - Synthesized finding (with inline citations from the KB)\n"
            "  - Gaps or contradictions across sources\n"
            "  - Evidence level for each key claim (RCT > cohort > case > in-vitro)\n"
            "Do not list papers one-by-one; synthesize across them.\n"
        )

    @staticmethod
    def mechanism_of_action() -> str:
        return (
            "\nTASK: Mechanism-of-action (MOA) explanation.\n"
            "Cover, in this order:\n"
            "  1. Molecular target (receptor / enzyme / ion channel) and class\n"
            "  2. Binding / inhibition type (competitive, allosteric, "
            "irreversible) with Ki/IC50 if in context\n"
            "  3. Downstream pharmacodynamic cascade\n"
            "  4. Clinical translation (what the patient experiences)\n"
            "  5. Known resistance / polymorphism issues\n"
            "Flag any step that is inferred rather than measured.\n"
        )

    @staticmethod
    def docking_explanation() -> str:
        return (
            "\nTASK: Docking result interpretation.\n"
            "Treat the supplied docking scores (AutoDock Vina kcal/mol or "
            "equivalent) as relative rankings, NOT absolute affinities.\n"
            "Address:\n"
            "  - Which poses are chemically plausible (H-bonds, hydrophobic "
            "contacts, clashes)\n"
            "  - Score vs known reference ligand (if supplied)\n"
            "  - Whether the result justifies MD refinement or wet-lab validation\n"
            "  - Limitations: rigid receptor, no solvation, no entropy\n"
            "Never present a docking score as a binding constant.\n"
        )

    @staticmethod
    def admet_interpretation() -> str:
        return (
            "\nTASK: ADMET profile interpretation.\n"
            "For each ADMET axis actually present in the context, classify as "
            "Acceptable / Borderline / Poor and cite the metric:\n"
            "  - Absorption: logP, logS, Caco-2, %Human intestinal absorption\n"
            "  - Distribution: PPB, BBB permeability, VDss\n"
            "  - Metabolism: CYP450 substrates/inhibitors (1A2, 2C9, 2C19, 2D6, 3A4)\n"
            "  - Excretion: total clearance, half-life\n"
            "  - Toxicity: hERG, AMES mutagenicity, hepatotoxicity, skin sensitization\n"
            "Conclude with a single Go / Optimize / Drop recommendation and the "
            "specific property to fix first.\n"
        )

    @staticmethod
    def claim_verification() -> str:
        return (
            "\nTASK: Pharmaceutical claim verification.\n"
            "For each claim extracted from the text, return a JSON object:\n"
            "  {\n"
            "    \"claim\": \"...\",\n"
            "    \"type\": \"efficacy|safety|pk_pd|mechanism|comparative|dosing\",\n"
            "    \"verdict\": \"SUPPORTED|CONTRADICTED|INSUFFICIENT|HALLUCINATED\",\n"
            "    \"evidence\": \"[citation from KB or NOT IN CONTEXT]\",\n"
            "    \"confidence\": 0.0-1.0,\n"
            "    \"rigor_notes\": \"randomization / blinding / power / ITT issues\"\n"
            "  }\n"
            "A claim with NO supporting evidence in context is INSUFFICIENT, "
            "never SUPPORTED. A claim that contradicts the context is "
            "CONTRADICTED. A claim citing a study that does not appear in the "
            "KB is HALLUCINATED.\n"
        )

    @staticmethod
    def thesis_section(section_type: str = "methods") -> str:
        templates = {
            "methods": (
                "\nTASK: Thesis Methods section drafting.\n"
                "Use the IMRaD structure. For pharma work the Methods section "
                "must allow replication, so specify: compounds (source, "
                "purity), cell lines / animals (source, ethics approval "
                "number placeholder), assay protocol, instruments, statistical "
                "tests (with software + version), and pre-specified endpoints.\n"
            ),
            "results": (
                "\nTASK: Thesis Results section drafting.\n"
                "Report effect sizes with 95% CIs, NOT just p-values. Separate "
                "primary from secondary endpoints. Describe adverse events "
                "even if none occurred ('No treatment-related adverse events "
                "were observed').\n"
            ),
            "discussion": (
                "\nTASK: Thesis Discussion section drafting.\n"
                "Use the 5-paragraph pattern: (1) key finding, (2) vs prior "
                "literature, (3) mechanism, (4) clinical/scientific "
                "significance, (5) limitations. Do not repeat the Results.\n"
            ),
        }
        return templates.get(section_type, templates["methods"])

    @staticmethod
    def ich_compliance(study_type: str = "clinical_trial") -> str:
        """Return the reporting-guideline checklist prompt for a study type.

        study_type ∈ {clinical_trial, observational, systematic_review,
                       animal_study, case_report, bioequivalence}
        """
        mapping = {
            "clinical_trial": "CONSORT 2010 (25 items)",
            "observational": "STROBE (22 items)",
            "systematic_review": "PRISMA 2020 (27 items)",
            "animal_study": "ARRIVE 2.0 (20 items)",
            "case_report": "CARE",
            "bioequivalence": "ICH E3 + ICH M4S",
        }
        guideline = mapping.get(study_type, "CONSORT 2010")
        return (
            f"\nTASK: Reporting-guideline compliance check ({guideline}).\n"
            "Audit the supplied manuscript section-by-section against the "
            "guideline checklist. For each item, return:\n"
            "  - item_id and item_text\n"
            "  - status: PRESENT | PARTIAL | MISSING | NOT_APPLICABLE\n"
            "  - evidence (quote from manuscript or 'not found')\n"
            "  - patch_suggestion (concrete sentence to add, if MISSING/PARTIAL)\n"
            "Flag any safety-reporting item as CRITICAL if missing.\n"
        )

    # ----------------------------------------------------------- dispatch
    @staticmethod
    def for_task(task: str, **kwargs) -> str:
        """Convenience dispatcher. task ∈
        {'literature','moa','docking','admet','claims','thesis','ich','system'}.
        Unknown tasks return just the system preamble.
        """
        dispatch = {
            "system": PharmaPromptLibrary.system_preamble,
            "literature": PharmaPromptLibrary.literature_review,
            "moa": PharmaPromptLibrary.mechanism_of_action,
            "docking": PharmaPromptLibrary.docking_explanation,
            "admet": PharmaPromptLibrary.admet_interpretation,
            "claims": PharmaPromptLibrary.claim_verification,
            "thesis": lambda: PharmaPromptLibrary.thesis_section(kwargs.get("section", "methods")),
            "ich": lambda: PharmaPromptLibrary.ich_compliance(kwargs.get("study_type", "clinical_trial")),
        }
        fn = dispatch.get(task)
        if fn is None:
            return PharmaPromptLibrary.system_preamble()
        return fn()

    @staticmethod
    def available_tasks() -> List[str]:
        return ["system", "literature", "moa", "docking", "admet", "claims", "thesis", "ich"]
