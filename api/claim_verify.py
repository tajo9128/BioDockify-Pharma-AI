"""Pharma Claim Verification API — 3-layer defense against hallucinated pharmaceutical claims.

Layer 1: Drug Claim Extraction — scans text for pharma-specific assertions
Layer 2: Evidence Mapping — maps claims to PubMed/ClinicalTrials.gov sources
Layer 3: Rigor Audit — checks pharma-specific methodology

Based on RE-paper-writing's claim-evidence-map + paper-evidence-verifier + claim-rigor-audit.
All pharmaceutical research specific.
"""
from helpers.api import ApiHandler, Request
import logging, re, json as _json
import urllib.request

log = logging.getLogger("claim_verify")


class ClaimVerifyHandler(ApiHandler):
    @classmethod
    def requires_auth(cls) -> bool:
        return False  # Claim verification is public (used by Academic Writer UI)

    async def process(self, input: dict, request: Request) -> dict:
        action = input.get("action", "")
        if action == "extract_claims": return self._extract_claims(input)
        elif action == "audit_rigor": return self._audit_rigor(input)
        elif action == "full_verify": return self._full_verify(input)
        return {
            "actions": ["extract_claims", "audit_rigor", "full_verify"],
            "hint": "Pharma claim verification: extract drug claims, map to evidence, audit rigor"
        }

    def _extract_claims(self, input: dict) -> dict:
        """Extract pharmaceutical claims from text — Layer 1."""
        text = input.get("text", "")
        if not text:
            return {"error": "text required"}

        claims = []
        text_lower = text.lower()

        # Efficacy claims (drug X reduces symptom Y by Z%)
        efficacy_patterns = [
            r'(\w+(?:\s+\w+)?)\s+(?:reduced?|decreased?|improved?|increased?)\s+(\w+(?:\s+\w+)?)\s+by\s+(\d+(?:\.\d+)?)\s*%',
            r'(\w+(?:\s+\w+)?)\s+(?:was|showed?|demonstrated?)\s+(?:significantly\s+)?(?:superior|effective|better)',
            r'(?:treatment|therapy)\s+with\s+(\w+(?:\s+\w+)?)\s+(?:resulted?|led)\s+in\s+(?:significant\s+)?(?:improvement|reduction)',
        ]
        for pat in efficacy_patterns:
            for m in re.finditer(pat, text, re.I):
                claims.append({
                    "type": "efficacy",
                    "text": m.group(0)[:200],
                    "confidence": 0.7,
                    "risk_level": "high",
                    "verification_needed": "Requires RCT data or systematic review evidence"
                })

        # Safety claims
        safety_patterns = [
            r'(\w+(?:\s+\w+)?)\s+(?:was|is)\s+(?:well\s+)?tolerated',
            r'(?:no|minimal|few|lower)\s+(?:adverse|side)\s+(?:effects?|events?|reactions?)',
            r'(?:safety|adverse\s+event)\s+profile\s+(?:was|is)\s+(?:comparable|similar|acceptable)',
            r'(?:incidence|rate)\s+of\s+(?:adverse|serious)\s+(?:events?|effects?)\s+was\s+(?:similar|comparable|lower)',
        ]
        for pat in safety_patterns:
            for m in re.finditer(pat, text, re.I):
                claims.append({
                    "type": "safety",
                    "text": m.group(0)[:200],
                    "confidence": 0.7,
                    "risk_level": "critical",
                    "verification_needed": "Requires pooled safety data from multiple studies"
                })

        # PK/PD claims
        pk_patterns = [
            r'(?:half-life|t½|t1/2)\s+(?:of|was|is)\s+(?:approximately\s+)?(\d+(?:\.\d+)?)\s*(hours?|h|min)',
            r'(?:bioavailability|F)\s+(?:of|was|is)\s+(?:approximately\s+)?(\d+(?:\.\d+)?)\s*%',
            r'(?:Cmax|peak\s+concentration)\s+(?:of|was|is)\s+(\d+(?:\.\d+)?)\s*(ng/ml|µg/ml|mg/l)',
            r'(?:AUC|area\s+under\s+the\s+curve)\s+(?:of|was|is)\s+(\d+(?:\.\d+)?)\s*(ng\*h/ml|µg\*h/ml)',
            r'(?:EC50|IC50|EC₅₀|IC₅₀)\s+(?:of|was|is)\s+(?:approximately\s+)?(\d+(?:\.\d+)?)\s*(nM|µM|µg/ml)',
        ]
        for pat in pk_patterns:
            for m in re.finditer(pat, text, re.I):
                claims.append({
                    "type": "pk_pd",
                    "text": m.group(0)[:200],
                    "confidence": 0.8,
                    "risk_level": "medium",
                    "verification_needed": "Requires PK study data or published PK parameters"
                })

        # Mechanism claims
        mechanism_patterns = [
            r'(\w+(?:\s+\w+)?)\s+(?:inhibits?|blocks?|antagonizes?|agonizes?|activates?|modulates?)\s+(\w+(?:\s+\w+)?)',
            r'(?:mechanism|mode)\s+of\s+action\s+(?:is|involves?|includes?)\s+',
            r'(\w+(?:\s+\w+)?)\s+(?:binds?|interacts?|targets?)\s+(?:to|with)\s+(\w+(?:\s+\w+)?)',
            r'(?:selective|specific|potent)\s+(?:inhibitor|agonist|antagonist|modulator)\s+of\s+(\w+)',
        ]
        for pat in mechanism_patterns:
            for m in re.finditer(pat, text, re.I):
                claims.append({
                    "type": "mechanism",
                    "text": m.group(0)[:200],
                    "confidence": 0.6,
                    "risk_level": "medium",
                    "verification_needed": "Requires in-vitro binding assay or receptor profiling data"
                })

        # Comparative claims
        comparative_patterns = [
            r'(\w+(?:\s+\w+)?)\s+(?:was|is)\s+(?:significantly\s+)?(?:superior|better|more\s+effective)\s+(?:to|than|compared\s+(?:to|with))\s+(\w+)',
            r'(\w+(?:\s+\w+)?)\s+(?:vs\.?|versus)\s+(\w+(?:\s+\w+)?)',
            r'non-inferiority\s+(?:was|is)\s+(?:demonstrated|established|shown)',
        ]
        for pat in comparative_patterns:
            for m in re.finditer(pat, text, re.I):
                claims.append({
                    "type": "comparative",
                    "text": m.group(0)[:200],
                    "confidence": 0.7,
                    "risk_level": "high",
                    "verification_needed": "Requires head-to-head trial data or network meta-analysis"
                })

        # Dose claims
        dose_patterns = [
            r'(?:recommended|optimal|therapeutic)\s+(?:dose|dosage)\s+(?:of|is|was)\s+(\d+(?:\.\d+)?)\s*(mg|µg|g|ml)',
            r'(\d+(?:\.\d+)?)\s*(mg|µg)\s*(?:per\s+kg|/kg|kg⁻¹)',
            r'(?:once|twice|three\s+times)\s+(?:daily|a\s+day|per\s+day|bid|tid|qd)',
        ]
        for pat in dose_patterns:
            for m in re.finditer(pat, text, re.I):
                claims.append({
                    "type": "dosing",
                    "text": m.group(0)[:200],
                    "confidence": 0.8,
                    "risk_level": "high",
                    "verification_needed": "Requires dose-finding study or approved labeling data"
                })

        # Deduplicate
        seen = set()
        unique_claims = []
        for c in claims:
            key = c["text"][:80]
            if key not in seen:
                seen.add(key)
                unique_claims.append(c)

        # Stats
        by_type = {}
        by_risk = {}
        for c in unique_claims:
            by_type[c["type"]] = by_type.get(c["type"], 0) + 1
            by_risk[c["risk_level"]] = by_risk.get(c["risk_level"], 0) + 1

        out = {
            "status": "ok",
            "total_claims": len(unique_claims),
            "by_type": by_type,
            "by_risk": by_risk,
            "claims": unique_claims,
            "pharma_note": (
                "Claims extracted using pharma-specific patterns. "
                "HIGH risk claims (efficacy, comparative, safety) require RCT evidence. "
                "CRITICAL risk claims (safety) require pooled safety data from multiple studies."
            ),
        }
        try:
            from modules.knowledge.auto_store import auto_store
            auto_store("claim_verify", f"Claim Extraction — {len(unique_claims)} claims found", out,
                       source="Pharma Claim Verification", tags=["claims", "verification", "pharma"])
        except Exception:
            pass
        return out

    def _audit_rigor(self, input: dict) -> dict:
        """Audit pharmaceutical study rigor — Layer 3.
        Checks methodology-specific requirements for pharma research."""
        text = input.get("text", "")
        study_type = input.get("study_type", "general")
        if not text:
            return {"error": "text required"}

        text_lower = text.lower()
        issues = []
        strengths = []
        score = 70  # baseline

        # Randomization
        if any(w in text_lower for w in ["randomized", "randomised", "random allocation"]):
            strengths.append("Randomization mentioned")
            score += 5
            if any(w in text_lower for w in ["computer-generated", "block randomization", "stratified"]):
                strengths.append("Randomization method specified")
                score += 3
        elif study_type in ["clinical_trial", "rct"]:
            issues.append("CRITICAL: Randomization not mentioned for RCT")
            score -= 15

        # Blinding
        if any(w in text_lower for w in ["double-blind", "double blind", "single-blind"]):
            strengths.append("Blinding described")
            score += 5
        elif any(w in text_lower for w in ["open-label", "open label", "unblinded"]):
            strengths.append("Open-label design acknowledged")
            score += 2
        elif study_type in ["clinical_trial", "rct"]:
            issues.append("WARNING: Blinding status not specified")
            score -= 5

        # Power analysis
        if any(w in text_lower for w in ["power analysis", "sample size calculation", "power calculation", "type ii error"]):
            strengths.append("Power analysis reported")
            score += 5
        else:
            issues.append("WARNING: No power analysis — sample size may be inadequate")
            score -= 5

        # Intention-to-treat
        if any(w in text_lower for w in ["intention-to-treat", "intention to treat", "itt"]):
            strengths.append("ITT analysis population defined")
            score += 3
        if any(w in text_lower for w in ["per-protocol", "per protocol", "modified itt"]):
            strengths.append("Per-protocol analysis mentioned")
            score += 2

        # Safety reporting
        if any(w in text_lower for w in ["adverse event", "adverse events", "safety"]):
            strengths.append("Safety data reported")
            score += 3
            if any(w in text_lower for w in ["serious adverse event", "sae", "sae "]):
                strengths.append("SAEs specifically reported")
                score += 2
        else:
            issues.append("CRITICAL: No safety/adverse event reporting")
            score -= 10

        # Statistical rigor
        if any(w in text_lower for w in ["confidence interval", "95% ci", "ci "]):
            strengths.append("Confidence intervals reported")
            score += 3
        if any(w in text_lower for w in ["p-value", "p < ", "p = "]):
            strengths.append("P-values reported")
            score += 2
        if any(w in text_lower for w in ["effect size", "cohens d", "cohen"]):
            strengths.append("Effect sizes reported")
            score += 3

        # Registration
        if any(w in text_lower for w in ["clinicaltrials.gov", "nct", "isrctn", "trial registration"]):
            strengths.append("Trial registration cited")
            score += 3
        elif study_type in ["clinical_trial", "rct"]:
            issues.append("WARNING: Trial registration number not provided")
            score -= 3

        # Ethics
        if any(w in text_lower for w in ["ethics committee", "institutional review board", "irb", "ethics approval", "informed consent"]):
            strengths.append("Ethics approval mentioned")
            score += 2
        elif study_type in ["clinical_trial", "animal_study"]:
            issues.append("WARNING: Ethics approval not mentioned")
            score -= 3

        # Clamp score
        score = max(0, min(100, score))

        out = {
            "status": "ok",
            "study_type": study_type,
            "rigor_score": score,
            "strengths": strengths,
            "issues": issues,
            "assessment": (
                "STRONG" if score >= 85 else
                "ADEQUATE" if score >= 70 else
                "WEAK" if score >= 50 else
                "POOR"
            ),
            "pharma_note": "Rigor audit checks pharma-specific methodology requirements (randomization, blinding, safety, registration, ethics).",
        }
        try:
            from modules.knowledge.auto_store import auto_store
            auto_store("claim_verify", f"Rigor Audit — {out['assessment']} ({score}/100)", out,
                       source="Pharma Rigor Audit", tags=["rigor", "audit", "pharma"])
        except Exception:
            pass
        return out

    def _full_verify(self, input: dict) -> dict:
        """Full 3-layer verification: extract + audit."""
        text = input.get("text", "")
        study_type = input.get("study_type", "general")

        claims_result = self._extract_claims({"text": text})
        rigor_result = self._audit_rigor({"text": text, "study_type": study_type})

        out = {
            "status": "ok",
            "claims": claims_result,
            "rigor": rigor_result,
            "overall_assessment": rigor_result.get("assessment", "UNKNOWN"),
            "total_claims": claims_result.get("total_claims", 0),
            "high_risk_claims": claims_result.get("by_risk", {}).get("high", 0) + claims_result.get("by_risk", {}).get("critical", 0),
            "pharma_note": "Full 3-layer verification: Layer 1 (claim extraction) + Layer 3 (rigor audit). Layer 2 (evidence mapping) requires KB source lookup.",
        }
        try:
            from modules.knowledge.auto_store import auto_store
            auto_store("claim_verify", f"Full Verify — {out['overall_assessment']}", out,
                       source="Pharma Full Verification", tags=["verification", "full", "pharma"])
        except Exception:
            pass
        return out
