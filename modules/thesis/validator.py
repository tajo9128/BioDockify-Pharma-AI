"""
Pharma Thesis Validator (Master Framework)
Checks for branch-specific proof existence and enforces strict academic rules.
"""
import logging
import os
import json
import re
from enum import Enum
from typing import Dict, List, Any, Optional

from modules.thesis.structure import ChapterId, PharmaBranch, DegreeType, get_branch_profile, THESIS_STRUCTURE

logger = logging.getLogger("thesis.validator")

class ProofStatus(str, Enum):
    VALID = "valid"
    MISSING = "missing"
    INCOMPLETE = "incomplete"
    FORBIDDEN = "forbidden"

class ThesisValidator:
    def __init__(self, project_root: str = "."):
        self.project_root = project_root

    def validate_chapter_readiness(self, chapter_id: str, branch: PharmaBranch = PharmaBranch.GENERAL, degree: DegreeType = DegreeType.PHD) -> Dict[str, Any]:
        """
        Check if the system has enough data and follows rules for the requested chapter.
        """
        logger.info(f"Validating {chapter_id} for {branch} ({degree})...")
        
        chapter_enum = ChapterId(chapter_id)
        template = THESIS_STRUCTURE.get(chapter_enum)
        profile = get_branch_profile(branch)
        
        if chapter_enum == ChapterId.INTRODUCTION:
            min_cite = 10 if degree == DegreeType.PHD else 5
            if degree == DegreeType.PHARM_D:
                return self._check_citations_available(min_count=min_cite, focus="Clinical Guidelines")
            return self._check_citations_available(min_count=min_cite)
            
        elif chapter_enum == ChapterId.LITERATURE_REVIEW:
            min_cite = 30 if degree == DegreeType.PHD else 15
            if degree == DegreeType.PHARM_D:
                return self._check_citations_available(min_count=min_cite, focus="RCTs/Meta-Analyses")
            return self._check_citations_available(min_count=min_cite)
            
        elif chapter_enum == ChapterId.MATERIALS_METHODS:
            # Branch-specific mandatory checks
            mandatory = profile.get("methods_mandatory", "")
            
            # MANDATORY for Pharm.D
            if degree == DegreeType.PHARM_D:
                ethics_check = self._check_files_exist(["iec_approval.pdf", "patient_consent.pdf", "crf_template.pdf"], any_one=False)
                if ethics_check["status"] != "valid":
                    return {"status": "blocked", "message": "MISSING MANDATORY PHARM.D PROOFS: IEC Approval, Patient Consent, and CRF are required."}
            
            status = self._check_files_exist(["protocol.json", "methods.md", "ethics.pdf"], any_one=True)
            if mandatory and "ethics" in mandatory.lower() and degree != DegreeType.PHARM_D:
                # Strict check for ethics if Pharmacology or Clinical (non-Pharm.D)
                ethics_check = self._check_files_exist(["ethics_approval.pdf", "iec_approval.pdf"], any_one=True)
                if ethics_check["status"] != "valid":
                    return {"status": "blocked", "message": f"MISSING MANDATORY PROOF: {mandatory}"}
            return status
            
        elif chapter_enum == ChapterId.RESULTS:
            if degree == DegreeType.PHARM_D:
                return self._check_files_exist(["clinical_data.json", "patient_stats.csv"], any_one=True)
            # Branch-specific data checks
            expected_data = profile.get("results_data", "")
            return self._check_files_exist(["results.json", "analysis.csv", "metrics.json"], any_one=True)
            
        elif chapter_enum == ChapterId.DISCUSSION:
            # Dependency check
            results = self.validate_chapter_readiness(ChapterId.RESULTS.value, branch, degree)
            if results['status'] != 'valid':
                return {"status": "missing", "message": "Discussion requires completed Results first."}
            return {"status": "valid", "proofs": ["results"]}
            
        return {"status": "valid", "message": "General validation passed."}

    def validate_content_strict(self, chapter_id: str, text: str, branch: PharmaBranch = PharmaBranch.GENERAL, degree: DegreeType = DegreeType.PHD) -> List[str]:
        """
        Perform strict NLP/RegEx checks on generated content to ensure no rule violations.
        Returns a list of violations.
        """
        violations = []
        chapter_enum = ChapterId(chapter_id)
        
        # Rule 1: No results in Introduction or Literature Review
        if chapter_enum in [ChapterId.INTRODUCTION, ChapterId.LITERATURE_REVIEW]:
            if re.search(r"results|findings|observed that|significant p-value|table \d", text, re.I):
                violations.append("FORBIDDEN CONTENT: Results/findings mentioned in Intro/Lit Review.")
        
        # Rule 2: No citations in Results or Abstract
        if chapter_enum in [ChapterId.RESULTS, ChapterId.FRONT_MATTER]:
            if "[" in text or "(" in text and re.search(r"\d{4}", text):
                # Simple heuristic for citations
                if chapter_enum == ChapterId.RESULTS or "Abstract" in text:
                    violations.append("STRICT RULE: No citations allowed in Results or Abstract.")

        # Rule 3: Pharm.D Clinical Enforcement
        if degree == DegreeType.PHARM_D:
            if re.search(r"molecular mechanism|binding site|docking|chemical synthesis|formulation optimization", text, re.I):
                violations.append("PHARM.D VIOLATION: Clinical project cannot include mechanistic/synthetic claims.")
            
            if chapter_enum == ChapterId.FRONT_MATTER and "Abstract" in text:
                if not re.search(r"study design|patient number|ethics", text, re.I):
                    violations.append("PHARM.D VIOLATION: Abstract must mention study design, patient count, and ethics approval.")

        # Rule 4: Branch Specific Constraints
        profile = get_branch_profile(branch)
        if chapter_enum == ChapterId.DISCUSSION and not profile.get("discussion_mechanism"):
            if degree != DegreeType.PHD: # allow PhD more leeway
                if re.search(r"molecular mechanism|pathway|binding site", text, re.I):
                    violations.append(f"STRICT RULE for {branch.value}: Discussion focus must remain on outcomes, not mechanisms.")

        return violations

    def _check_citations_available(self, min_count: int = 5, focus: str = "General") -> Dict[str, Any]:
        try:
            from modules.library.store import library_store
            files = library_store.list_files()
            if len(files) >= min_count:
                 return {"status": "valid", "proof_count": len(files), "focus_applied": focus}
            return {
                "status": "missing", 
                "message": f"Insufficient {focus} literature. Need {min_count} papers, found {len(files)}.",
                "current_count": len(files)
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _check_files_exist(self, filenames: List[str], any_one: bool = False) -> Dict[str, Any]:
        found = []
        missing = []
        search_paths = [self.project_root, os.path.join(self.project_root, "data"), os.path.join(self.project_root, "outputs")]
        
        for fname in filenames:
            is_found = False
            for path in search_paths:
                if os.path.exists(os.path.join(path, fname)):
                    found.append(fname)
                    is_found = True
                    break
            if not is_found:
                missing.append(fname)
        
        if any_one:
            if found: return {"status": "valid", "found": found}
            return {"status": "missing", "missing_items": missing}
        else:
            if not missing: return {"status": "valid", "found": found}
            return {"status": "missing", "missing_items": missing}

thesis_validator = ThesisValidator()
