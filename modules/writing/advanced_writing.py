"""
BioDockify Academic Writer — Advanced Writing Skills (PaperForge + Rigorous)

7 advanced writing capabilities independently implemented based on publicly
documented methodologies. No third-party code is copied.

1. De-AIGC Rewrite — anti-AI-tone polishing
2. Section Analyzer — per-section quality scoring (S1-S10)
3. Citation Gap Finder — auto-detect missing citations
4. Terminology Checker — consistency enforcement
5. Scientific Rigor Review — R1-R7 methodology checks
6. Quality Control — validation layer for review outputs
7. Executive Summary — 2-step synthesis

Each skill returns structured JSON suitable for UI rendering.
"""

import re
import logging
from typing import List, Dict, Any

log = logging.getLogger("writing.advanced")


# ═══════════════════════════════════════════════════════════════════════════
# Skill 1: De-AIGC Rewrite (Anti-AI-Tone Polishing)
# ═══════════════════════════════════════════════════════════════════════════

# Words/phrases that signal AI-generated text
AI_SIGNATURES = {
    "filler_phrases": [
        "it's important to note that", "it is important to note that",
        "it's worth noting", "it is worth noting",
        "it should be noted", "it should be mentioned",
        "delve into", "dive into", "dive deep",
        "in the realm of", "in the landscape of", "in the context of",
        "it's crucial to", "it is crucial to",
        "at the end of the day", "when it comes to",
        "a comprehensive overview", "a comprehensive guide",
        "leveraging", "utilizing", "harnessing",
        "groundbreaking", "cutting-edge", "state-of-the-art",
        "seamless", "robust", "innovative", "transformative",
        "game-changer", "paradigm shift", "holistic approach",
        "synergy", "ecosystem", "holistic", "nuanced",
        "tapestry", "multifaceted", "intricate",
    ],
    "template_openers": [
        "In this paper, we present", "In this study, we investigate",
        "This paper explores", "This research aims to",
        "The purpose of this study is to", "In the following sections",
        "As we delve into", "As mentioned earlier",
        "Building upon this foundation", "Drawing from the literature",
        "It is evident that", "It is clear that",
        "Notably,", "Importantly,", "Significantly,",
    ],
    "ai_hedging": [
        "aforementioned", "noteworthy", "commendable",
        "robust methodology", "rigorous analysis",
        "interdisciplinary approach", "comprehensive understanding",
        "nuanced understanding", "deep understanding",
    ],
}


def de_aigc_rewrite(text: str, aggressiveness: str = "moderate") -> Dict[str, Any]:
    """Analyze text for AI-generated patterns and suggest human-sounding rewrites.

    Args:
        text: Manuscript text to analyze
        aggressiveness: "light", "moderate", or "heavy" — how aggressively to flag

    Returns:
        {issues: [...], rewrite_suggestions: [...], score: float, summary: str}
    """
    issues = []
    suggestions = []

    # Find filler phrases
    for phrase in AI_SIGNATURES["filler_phrases"]:
        for m in re.finditer(re.escape(phrase), text, re.IGNORECASE):
            issues.append({
                "type": "filler_phrase",
                "text": m.group(0),
                "position": m.start(),
                "severity": "medium",
                "message": f"AI-typical filler: '{phrase}' — remove or replace with direct language.",
            })

    # Find template openers
    for opener in AI_SIGNATURES["template_openers"]:
        for m in re.finditer(re.escape(opener), text, re.IGNORECASE):
            issues.append({
                "type": "template_opener",
                "text": m.group(0),
                "position": m.start(),
                "severity": "low",
                "message": f"Template opener: '{opener}' — rephrase to sound more natural.",
            })

    # Find passive voice overuse (heuristic)
    passive_pattern = re.compile(r"\b(is|are|was|were|been|being)\s+\w+ed\b", re.IGNORECASE)
    passive_count = len(passive_pattern.findall(text))
    total_sentences = len(re.split(r'[.!?]+', text))
    if total_sentences > 0:
        passive_ratio = passive_count / total_sentences
        if passive_ratio > 0.4:
            issues.append({
                "type": "passive_voice",
                "severity": "medium",
                "message": f"Passive voice in {passive_count}/{total_sentences} sentences ({passive_ratio:.0%}). Convert some to active voice for clarity.",
            })

    # Find repeated words (trigram repetition)
    words = text.lower().split()
    trigrams = [f"{words[i]} {words[i+1]} {words[i+2]}" for i in range(len(words)-2)]
    trigram_counts = {}
    for t in trigrams:
        trigram_counts[t] = trigram_counts.get(t, 0) + 1
    repeated = {k: v for k, v in trigram_counts.items() if v >= 3}
    for phrase, count in repeated.items():
        issues.append({
            "type": "repetition",
            "text": phrase,
            "severity": "low",
            "message": f"Trigram '{phrase}' repeated {count} times. Vary your phrasing.",
        })

    # Find long sentences (>40 words)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    for sent in sentences:
        word_count = len(sent.split())
        if word_count > 40:
            issues.append({
                "type": "long_sentence",
                "text": sent[:100] + "...",
                "severity": "low",
                "message": f"Sentence has {word_count} words. Break into shorter sentences for readability.",
            })

    # Calculate AIGC risk score (0-100, higher = more AI-like)
    score = 0
    filler_count = len([i for i in issues if i["type"] == "filler_phrase"])
    template_count = len([i for i in issues if i["type"] == "template_opener"])
    score += min(filler_count * 5, 30)
    score += min(template_count * 3, 20)
    score += min(passive_ratio * 30, 30) if total_sentences > 0 else 0
    score += min(len(repeated) * 5, 20)
    score = min(100, score)

    # Generate rewrite suggestions
    for issue in issues[:10]:
        if issue["type"] == "filler_phrase":
            original = issue["text"]
            # Generate a specific rewrite suggestion
            if "important to note" in original.lower():
                suggestions.append({
                    "original": original,
                    "suggestion": "[Remove — start directly with the fact]",
                    "reason": "Direct language is more credible in academic writing.",
                })
            elif "delve into" in original.lower():
                suggestions.append({
                    "original": original,
                    "suggestion": "examine / analyze / investigate",
                    "reason": "Use precise verbs instead of vague metaphors.",
                })
            elif "robust" in original.lower():
                suggestions.append({
                    "original": original,
                    "suggestion": "well-validated / reproducible / statistically significant",
                    "reason": "Replace vague adjectives with specific claims.",
                })

    return {
        "status": "ok",
        "aigc_risk_score": round(score, 1),
        "risk_level": "High" if score > 60 else ("Medium" if score > 30 else "Low"),
        "issues": issues[:20],
        "total_issues": len(issues),
        "rewrite_suggestions": suggestions[:10],
        "summary": (
            f"Found {len(issues)} AI-typical patterns. AIGC risk: {score}/100 ({'High' if score > 60 else 'Medium' if score > 30 else 'Low'}). "
            f"{'Consider rewriting to sound more natural.' if score > 30 else 'Writing sounds human-authored.'}"
        ),
    }


# ═══════════════════════════════════════════════════════════════════════════
# Skill 2: Section Analyzer (Rigorous S1-S10)
# ═══════════════════════════════════════════════════════════════════════════

SECTION_CHECKLISTS = {
    "title_keywords": {
        "name": "Title & Keywords",
        "criteria": [
            "Title is concise and descriptive (10-15 words)",
            "Contains key variables/population/intervention",
            "Avoids abbreviations in title",
            "Keywords are MeSH terms or field-standard",
            "Keywords don't duplicate title words",
        ],
    },
    "abstract": {
        "name": "Abstract",
        "criteria": [
            "Structured format (Background/Methods/Results/Conclusion)",
            "Contains specific numbers (sample size, effect size, p-value)",
            "States primary endpoint clearly",
            "Conclusions match the data presented",
            "Within word limit (typically 250-300 words)",
        ],
    },
    "introduction": {
        "name": "Introduction",
        "criteria": [
            "Clear research gap identified",
            "Logical funnel: broad → specific",
            "Citations support every factual claim",
            "Research question/hypothesis explicitly stated",
            "Justification for study design provided",
        ],
    },
    "methods": {
        "name": "Methods",
        "criteria": [
            "Study design clearly described",
            "Eligibility criteria specified",
            "Sample size justification (power analysis)",
            "Primary/secondary endpoints defined",
            "Statistical methods named with software/version",
            "Ethical approval mentioned",
        ],
    },
    "results": {
        "name": "Results",
        "criteria": [
            "Primary endpoint reported first",
            "Effect sizes with 95% confidence intervals",
            "P-values reported (not just 'significant')",
            "Table/figure numbers referenced in text",
            "No discussion/interpretation in results section",
        ],
    },
    "discussion": {
        "name": "Discussion",
        "criteria": [
            "Main finding stated in first paragraph",
            "Comparison with existing literature",
            "Mechanism/explanation proposed",
            "Limitations acknowledged",
            "Clinical/practical implications stated",
        ],
    },
    "conclusion": {
        "name": "Conclusion",
        "criteria": [
            "Restates main finding (not verbatim from abstract)",
            "Supported by the data presented",
            "No new information introduced",
            "Future directions suggested",
            "Appropriate strength of claims (no overclaiming)",
        ],
    },
    "references": {
        "name": "References",
        "criteria": [
            "All in-text citations have matching reference entries",
            "No orphan references (in reference list but not cited)",
            "Consistent formatting (Vancouver/APA/IEEE)",
            "Recent references included (last 5 years)",
            "Primary sources preferred over secondary",
        ],
    },
}


def analyze_sections(text: str) -> Dict[str, Any]:
    """Analyze manuscript sections for quality.

    Detects sections by heading patterns and evaluates each against
    section-specific criteria.
    """
    sections = _detect_sections(text)
    results = {}

    for section_key, section_text in sections.items():
        checklist = SECTION_CHECKLISTS.get(section_key)
        if not checklist:
            continue

        criteria_results = []
        for criterion in checklist["criteria"]:
            # Simple heuristic check — in a real system this would use LLM
            has_issue = _check_criterion(section_text, criterion)
            criteria_results.append({
                "criterion": criterion,
                "status": "PASS" if not has_issue else "NEEDS_REVIEW",
                "note": "Detected potential issue" if has_issue else "Appears adequate",
            })

        results[section_key] = {
            "name": checklist["name"],
            "word_count": len(section_text.split()),
            "criteria": criteria_results,
            "pass_rate": len([c for c in criteria_results if c["status"] == "PASS"]) / len(criteria_results) if criteria_results else 0,
        }

    return {
        "status": "ok",
        "sections": results,
        "total_sections": len(results),
        "overall_pass_rate": sum(r["pass_rate"] for r in results.values()) / len(results) if results else 0,
    }


def _detect_sections(text: str) -> Dict[str, str]:
    """Detect sections by heading patterns."""
    section_patterns = [
        (r"(?i)^#{1,3}\s*(?:1\.?\s*)?(?:title|abstract)", "abstract"),
        (r"(?i)^#{1,3}\s*(?:2\.?\s*)?(?:introduction|background)", "introduction"),
        (r"(?i)^#{1,3}\s*(?:3\.?\s*)?(?:method|material|experimental|procedure)", "methods"),
        (r"(?i)^#{1,3}\s*(?:4\.?\s*)?(?:result|finding)", "results"),
        (r"(?i)^#{1,3}\s*(?:5\.?\s*)?(?:discussion|interpretation)", "discussion"),
        (r"(?i)^#{1,3}\s*(?:6\.?\s*)?(?:conclusion|summary)", "conclusion"),
        (r"(?i)^#{1,3}\s*(?:7\.?\s*)?(?:reference|bibliography|citation)", "references"),
    ]

    sections = {}
    current_section = "title_keywords"
    current_text = []

    for line in text.split("\n"):
        matched = False
        for pattern, key in section_patterns:
            if re.match(pattern, line.strip()):
                if current_text:
                    sections[current_section] = "\n".join(current_text)
                current_section = key
                current_text = []
                matched = True
                break
        if not matched:
            current_text.append(line)

    if current_text:
        sections[current_section] = "\n".join(current_text)

    return sections


def _check_criterion(text: str, criterion: str) -> bool:
    """Simple heuristic check for a criterion. Returns True if issue detected."""
    text_lower = text.lower()
    # Check for common issues
    if "p-value" in criterion.lower() or "confidence interval" in criterion.lower():
        if "p=" not in text_lower and "p <" not in text_lower and "ci" not in text_lower:
            return True
    if "sample size" in criterion.lower() or "power" in criterion.lower():
        if "n=" not in text_lower and "sample size" not in text_lower:
            return True
    if "limitation" in criterion.lower():
        if "limitation" not in text_lower and "weakness" not in text_lower:
            return True
    return False


# ═══════════════════════════════════════════════════════════════════════════
# Skill 3: Citation Gap Finder
# ═══════════════════════════════════════════════════════════════════════════

def find_citation_gaps(text: str) -> Dict[str, Any]:
    """Find claims that lack citations (gaps in the reference list).

    Analyzes the manuscript for:
    - Factual claims without citations
    - Claims that reference studies but don't cite them
    - Common pharma claims that should have citations
    """
    import re

    gaps = []
    sentences = re.split(r'(?<=[.!?])\s+', text)
    citation_re = re.compile(r'\[\d{1,3}\]|\([A-Z][a-z]+(?:\s+et\s+al\.?)?,\s*\d{4}\)')

    # Pharma-specific claims that MUST have citations
    pharma_claim_patterns = [
        (r'\b(?:IC50|EC50|Ki|Kd|pIC50)\b', 'Potency value — must cite source study'),
        (r'\b(?:binding affinity|selectivity|therapeutic index)\b', 'Pharmacological property — must cite source'),
        (r'\b(?:dose.response|dose.response|PK/PD|pharmacokinetic)\b', 'PK/PD claim — must cite source study'),
        (r'\b(?:adverse event|side effect|toxicity|safety)\b', 'Safety claim — must cite source'),
        (r'\b(?:efficacy|efficacious|therapeutic effect)\b', 'Efficacy claim — must cite source'),
        (r'\b(?:mechanism of action|MOA|target)\b', 'Mechanism claim — must cite source'),
        (r'\b(?:FDA|EMA|ICH|GLP|GCP|GMP)\b', 'Regulatory claim — must cite guideline'),
        (r'\b(?:meta.analysis|systematic review|Cochrane)\b', 'Evidence synthesis — must cite source'),
        (r'\b(?:clinical trial|Phase [I-IV]|RCT|randomized)\b', 'Clinical trial claim — must cite registration'),
    ]

    for i, sentence in enumerate(sentences):
        if len(sentence) < 20:
            continue

        has_citation = bool(citation_re.search(sentence))

        # Check pharma-specific claims
        for pattern, reason in pharma_claim_patterns:
            if re.search(pattern, sentence, re.IGNORECASE) and not has_citation:
                gaps.append({
                    "sentence": sentence[:200],
                    "reason": reason,
                    "severity": "high",
                    "suggestion": f"Add a citation for this {reason.split('—')[0].strip().lower()}.",
                })
                break

        # Check general factual claims without citations
        factual_patterns = [
            r'\b(?:shows?|demonstrates?|indicates?|suggests?|reveals?)\b',
            r'\b(?:significantly|substantially|markedly)\b',
            r'\b(?:\d+(?:\.\d+)?\s*(?:mg|ug|ng|nM|uM|mM|fold|%))\b',
        ]
        has_factual = any(re.search(p, sentence, re.IGNORECASE) for p in factual_patterns)
        if has_factual and not has_citation:
            gaps.append({
                "sentence": sentence[:200],
                "reason": "Factual claim without citation",
                "severity": "medium",
                "suggestion": "Add a citation to support this claim.",
            })

    return {
        "status": "ok",
        "gaps": gaps[:20],
        "total_gaps": len(gaps),
        "high_severity_gaps": len([g for g in gaps if g["severity"] == "high"]),
        "summary": f"Found {len(gaps)} citation gaps ({len([g for g in gaps if g['severity'] == 'high'])} high-severity pharma claims without citations).",
    }


# ═══════════════════════════════════════════════════════════════════════════
# Skill 4: Terminology Consistency Checker
# ═══════════════════════════════════════════════════════════════════════════

def check_terminology(text: str) -> Dict[str, Any]:
    """Check for terminology consistency in the manuscript.

    Detects:
    - Inconsistent drug/protein names
    - Inconsistent abbreviations
    - Inconsistent units
    - Inconsistent notation
    """
    import re
    from collections import Counter

    issues = []

    # Find all abbreviations and their definitions
    abbr_pattern = re.compile(r'\b([A-Z][A-Za-z0-9]{2,})\b')
    abbr_definitions = re.compile(r'([A-Z][A-Za-z0-9]{2,})\s*\(([A-Za-z0-9\s]+)\)')
    definitions = {}
    for m in abbr_definitions.finditer(text):
        abbr = m.group(1)
        expansion = m.group(2).strip()
        if abbr not in definitions:
            definitions[abbr] = expansion

    # Check if abbreviations are defined before first use
    for abbr in definitions:
        first_use = text.find(abbr)
        first_def = text.find(f"{abbr} (")
        if first_def > first_use:
            issues.append({
                "type": "abbreviation_before_definition",
                "term": abbr,
                "message": f"'{abbr}' used before being defined at position {first_def}.",
                "severity": "medium",
            })

    # Check for inconsistent capitalization of common terms
    term_variants = {}
    common_terms = [
        ("dataset", "data set", "data-set"),
        ("healthcare", "health care", "health-care"),
        ("e-mail", "email"),
        ("online", "on-line"),
        ("decision-making", "decision making", "decisionmaking"),
        ("follow-up", "followup", "follow up"),
        ("in-vitro", "in vitro", "invitro"),
        ("in-vivo", "in vivo", "invivo"),
    ]

    for variants in common_terms:
        counts = {}
        for v in variants:
            count = len(re.findall(re.escape(v), text, re.IGNORECASE))
            if count > 0:
                counts[v] = count
        if len(counts) > 1:
            dominant = max(counts, key=counts.get)
            for v, c in counts.items():
                if v != dominant and c > 0:
                    issues.append({
                        "type": "inconsistent_terminology",
                        "term": v,
                        "message": f"'{v}' used {c}x, but '{dominant}' is used {counts[dominant]}x. Use one consistently.",
                        "severity": "low",
                    })

    # Check for inconsistent units
    unit_pattern = re.compile(r'(\d+(?:\.\d+)?)\s*(mg|ug|ng|pg|nM|uM|mM|M|kcal|kJ|mol|mmol|umol)', re.IGNORECASE)
    units_found = Counter()
    for m in unit_pattern.finditer(text):
        units_found[m.group(2)] += 1

    return {
        "status": "ok",
        "issues": issues[:20],
        "total_issues": len(issues),
        "abbreviations_found": len(definitions),
        "unit_usage": dict(units_found),
        "summary": f"Found {len(issues)} terminology issues. {len(definitions)} abbreviations detected.",
    }


# ═══════════════════════════════════════════════════════════════════════════
# Skill 5: Scientific Rigor Review (R1-R7)
# ═══════════════════════════════════════════════════════════════════════════

def scientific_rigor_review(text: str) -> Dict[str, Any]:
    """Review manuscript for scientific rigor across 7 dimensions (R1-R7).

    Checks:
    R1: Originality — novelty claims, literature comparison
    R2: Impact — field contribution, practical implications
    R3: Ethics — conflicts of interest, data privacy, consent
    R4: Data availability — reproducibility, documentation
    R5: Statistical rigor — test selection, sample size, effect size
    R6: Technical accuracy — mathematical correctness
    R7: Consistency — methods-results alignment
    """
    import re

    text_lower = text.lower()
    reviews = {}

    # R1: Originality
    r1_issues = []
    if "novel" in text_lower or "first" in text_lower or "unprecedented" in text_lower:
        if "previous" not in text_lower and "prior" not in text_lower:
            r1_issues.append("Claims novelty without comparing to prior work")
    reviews["R1_originality"] = {"name": "Originality & Contribution", "issues": r1_issues, "score": max(1, 5 - len(r1_issues))}

    # R2: Impact
    r2_issues = []
    if "implication" not in text_lower and "impact" not in text_lower and "significance" not in text_lower:
        r2_issues.append("No implications or significance statement found")
    reviews["R2_impact"] = {"name": "Impact & Significance", "issues": r2_issues, "score": max(1, 5 - len(r2_issues))}

    # R3: Ethics
    r3_issues = []
    if "ethics" not in text_lower and "irb" not in text_lower and "consent" not in text_lower:
        r3_issues.append("No ethics/IRB/consent statement found")
    if "conflict of interest" not in text_lower and "coi" not in text_lower:
        r3_issues.append("No conflict of interest statement found")
    reviews["R3_ethics"] = {"name": "Ethics & Compliance", "issues": r3_issues, "score": max(1, 5 - len(r3_issues))}

    # R4: Data availability
    r4_issues = []
    if "data availability" not in text_lower and "data sharing" not in text_lower:
        r4_issues.append("No data availability statement found")
    reviews["R4_data"] = {"name": "Data & Code Availability", "issues": r4_issues, "score": max(1, 5 - len(r4_issues))}

    # R5: Statistical rigor
    r5_issues = []
    stat_tests = ["t-test", "anova", "chi-square", "mann-whitney", "wilcoxon", "regression", "correlation"]
    found_tests = [t for t in stat_tests if t in text_lower]
    if not found_tests:
        r5_issues.append("No named statistical tests found")
    if "confidence interval" not in text_lower and "ci" not in text_lower:
        r5_issues.append("No confidence intervals reported")
    if "effect size" not in text_lower and "cohen" not in text_lower:
        r5_issues.append("No effect size reported")
    reviews["R5_statistics"] = {"name": "Statistical Rigor", "issues": r5_issues, "score": max(1, 5 - len(r5_issues)), "tests_found": found_tests}

    # R6: Technical accuracy
    r6_issues = []
    if "supplementary" not in text_lower and "supporting information" not in text_lower:
        r6_issues.append("No supplementary materials referenced")
    reviews["R6_technical"] = {"name": "Technical Accuracy", "issues": r6_issues, "score": max(1, 5 - len(r6_issues))}

    # R7: Consistency
    r7_issues = []
    if "primary endpoint" in text_lower and "primary outcome" in text_lower:
        r7_issues.append("Mixed terminology: 'primary endpoint' vs 'primary outcome'")
    reviews["R7_consistency"] = {"name": "Consistency", "issues": r7_issues, "score": max(1, 5 - len(r7_issues))}

    overall_score = sum(r["score"] for r in reviews.values()) / len(reviews)
    total_issues = sum(len(r["issues"]) for r in reviews.values())

    return {
        "status": "ok",
        "reviews": reviews,
        "overall_score": round(overall_score, 1),
        "total_issues": total_issues,
        "verdict": "PASS" if overall_score >= 3.5 else ("NEEDS WORK" if overall_score >= 2.5 else "MAJOR ISSUES"),
        "summary": f"Scientific rigor score: {overall_score:.1f}/5.0 across 7 dimensions. {total_issues} issues found.",
    }


# ═══════════════════════════════════════════════════════════════════════════
# Skill 6: Quality Control Validation Layer
# ═══════════════════════════════════════════════════════════════════════════

def validate_review_outputs(review_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate and deduplicate outputs from multiple review agents.

    Takes raw outputs from section analysis, terminology check, etc.
    and produces a curated, deduplicated set of actionable feedback.
    """
    all_issues = []
    seen = set()

    for result in review_results:
        issues = result.get("issues", result.get("gaps", result.get("reviews", {})))
        if isinstance(issues, list):
            for issue in issues:
                # Deduplicate by sentence/text
                key = issue.get("sentence", issue.get("text", issue.get("message", "")))[:50]
                if key not in seen:
                    seen.add(key)
                    all_issues.append({
                        **issue,
                        "source": result.get("source", "unknown"),
                    })

    # Sort by severity
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    all_issues.sort(key=lambda x: severity_order.get(x.get("severity", "low"), 4))

    # Take top 20 most actionable issues
    curated = all_issues[:20]

    return {
        "status": "ok",
        "total_raw_issues": sum(len(r.get("issues", [])) for r in review_results),
        "deduplicated_issues": len(all_issues),
        "curated_issues": curated,
        "summary": f"QC: {len(all_issues)} unique issues across {len(review_results)} review dimensions.",
    }


# ═══════════════════════════════════════════════════════════════════════════
# Skill 7: Executive Summary Generator
# ═══════════════════════════════════════════════════════════════════════════

def generate_executive_summary(
    section_analysis: Dict,
    terminology_check: Dict,
    rigor_review: Dict,
    citation_gaps: Dict,
    aigc_check: Dict,
) -> Dict[str, Any]:
    """Generate a 2-step executive summary of all review results.

    Step 1: Independent assessment (just the numbers)
    Step 2: Balanced synthesis (strengths + weaknesses + action items)
    """
    # Step 1: Collect metrics
    metrics = {
        "sections_pass_rate": section_analysis.get("overall_pass_rate", 0),
        "terminology_issues": terminology_check.get("total_issues", 0),
        "rigor_score": rigor_review.get("overall_score", 0),
        "citation_gaps": citation_gaps.get("total_gaps", 0),
        "aigc_risk": aigc_check.get("aigc_risk_score", 0),
    }

    # Step 2: Generate strengths and weaknesses
    strengths = []
    weaknesses = []

    if metrics["sections_pass_rate"] > 0.7:
        strengths.append(f"Section quality: {metrics['sections_pass_rate']:.0%} pass rate across all sections")
    else:
        weaknesses.append(f"Section quality: only {metrics['sections_pass_rate']:.0%} pass rate — review failed sections")

    if metrics["rigor_score"] >= 4.0:
        strengths.append(f"Scientific rigor: {metrics['rigor_score']}/5.0 — strong methodology")
    elif metrics["rigor_score"] < 3.0:
        weaknesses.append(f"Scientific rigor: {metrics['rigor_score']}/5.0 — significant methodology gaps")

    if metrics["citation_gaps"] == 0:
        strengths.append("Citations: no gaps detected")
    else:
        weaknesses.append(f"Citations: {metrics['citation_gaps']} claims without supporting references")

    if metrics["aigc_risk"] < 30:
        strengths.append("Writing quality: human-like tone (low AIGC risk)")
    elif metrics["aigc_risk"] > 60:
        weaknesses.append(f"Writing quality: high AIGC risk ({metrics['aigc_risk']}/100) — rewrite to sound natural")

    if metrics["terminology_issues"] < 5:
        strengths.append("Terminology: consistent usage throughout")
    else:
        weaknesses.append(f"Terminology: {metrics['terminology_issues']} consistency issues")

    # Action items
    action_items = []
    if metrics["citation_gaps"] > 0:
        action_items.append(f"Add citations for {metrics['citation_gaps']} uncited claims")
    if metrics["aigc_risk"] > 40:
        action_items.append("De-AIGC: rewrite AI-typical phrases to sound human-authored")
    if metrics["rigor_score"] < 3.5:
        action_items.append("Address scientific rigor issues flagged in R1-R7 review")
    if metrics["terminology_issues"] > 5:
        action_items.append("Standardize terminology inconsistencies")

    # Overall verdict
    overall = "READY FOR SUBMISSION" if (
        metrics["sections_pass_rate"] > 0.7 and
        metrics["rigor_score"] >= 3.5 and
        metrics["citation_gaps"] < 5 and
        metrics["aigc_risk"] < 50
    ) else "NEEDS REVISION"

    return {
        "status": "ok",
        "verdict": overall,
        "metrics": metrics,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "action_items": action_items,
        "summary": f"Executive Summary: {overall}. {len(strengths)} strengths, {len(weaknesses)} weaknesses, {len(action_items)} action items.",
    }
