"""Faculty Review Mode — automated manuscript quality scoring."""
import logging, re

log = logging.getLogger("review_checker")

# Rubric weights
WEIGHTS = {
    "citation_quality": 25,
    "imrad_structure": 15,
    "claim_support": 20,
    "logical_flow": 15,
    "completeness": 10,
    "language_quality": 10,
    "duplicate_check": 5,
}


def review_manuscript(content: str, title: str = "", sections: dict = None) -> dict:
    """
    Automated faculty-style manuscript review with scoring.

    Returns a publication readiness report with scores, issues, and recommendations.
    """
    sections = sections or {}
    all_text = f"{title}\n{content}"
    if sections:
        all_text += "\n" + "\n".join(sections.values())

    checks = {}

    # 1. Citation Quality
    checks["citation_quality"] = _check_citations(content)

    # 2. IMRaD Structure
    checks["imrad_structure"] = _check_imrad(content, sections)

    # 3. Claim Support
    checks["claim_support"] = _check_claims(content)

    # 4. Logical Flow
    checks["logical_flow"] = _check_flow(content, sections)

    # 5. Completeness
    checks["completeness"] = _check_completeness(content, sections)

    # 6. Language Quality
    checks["language_quality"] = _check_language(content)

    # 7. Duplicate Check
    checks["duplicate_check"] = _check_duplicates(content)

    # Compute weighted score
    total_score = sum(
        min(checks[k]["score"], WEIGHTS[k]) for k in WEIGHTS
    )
    max_score = sum(WEIGHTS.values())
    readiness = round(100 * total_score / max_score)

    # Generate summary
    issues = []
    recommendations = []
    for k, v in checks.items():
        for issue in v.get("issues", []):
            issues.append({"category": k, "issue": issue})
        for rec in v.get("recommendations", []):
            recommendations.append(rec)

    # Readiness level
    if readiness >= 85:
        level = "Publication Ready"
        verdict = "This manuscript meets publication standards. Minor polishing recommended before submission."
    elif readiness >= 65:
        level = "Needs Revision"
        verdict = "The manuscript requires targeted revisions before submission. Address the flagged issues."
    elif readiness >= 40:
        level = "Major Revision Required"
        verdict = "Significant revisions needed. Review each section carefully and address all flagged concerns."
    else:
        level = "Not Ready"
        verdict = "The manuscript requires substantial revision. Consider restructuring and strengthening the evidence base."

    return {
        "score": readiness,
        "max_score": 100,
        "level": level,
        "verdict": verdict,
        "checks": {k: {"score": min(v["score"], WEIGHTS[k]), "max": WEIGHTS[k], "details": v.get("details", v.get("status", ""))}
                   for k, v in checks.items()},
        "issues": issues[:15],
        "recommendations": recommendations[:10],
    }


def _check_citations(content: str) -> dict:
    # Count citation markers: [1], [1,2], (Author, Year), et al.
    bracket = len(re.findall(r'\[\d+(?:[,;]\s*\d+)*\]', content))
    author_year = len(re.findall(r'\([A-Z][a-z]+(?:\s+et\s+al\.)?,?\s*\d{4}\)', content))
    total = bracket + author_year
    score = min(25, total * 3) if total > 0 else 0
    issues = []
    if total == 0:
        issues.append("No citations found — add references to support claims")
    elif total < 5:
        issues.append(f"Only {total} citations — consider adding more supporting references")
    return {"score": score, "status": f"{total} citations detected", "issues": issues,
            "recommendations": ["Verify all citations against PubMed/CrossRef" if total > 0 else "Add citations to support claims"]}


def _check_imrad(content: str, sections: dict) -> dict:
    patterns = {
        "Introduction": r"(?i)introduction|background",
        "Methods": r"(?i)method|methodology|materials|experimental|procedure",
        "Results": r"(?i)result|finding|outcome",
        "Discussion": r"(?i)discussion|implication|interpretation",
        "Conclusion": r"(?i)conclusion|summary|future work",
    }
    found = []
    missing = []
    for section, pattern in patterns.items():
        if section.lower() in (k.lower() for k in sections.keys()) or re.search(pattern, content):
            found.append(section)
        else:
            missing.append(section)

    score = min(15, len(found) * 3)
    issues = []
    if missing:
        issues.append(f"Missing sections: {', '.join(missing)} — consider IMRaD structure")
    return {"score": score, "status": f"Found: {', '.join(found)}" if found else "No section structure detected",
            "issues": issues,
            "recommendations": [f"Add {', '.join(missing)} section(s)" if missing else "Structure follows IMRaD conventions"]}


def _check_claims(content: str) -> dict:
    unsupported = len(re.findall(r'(?i)(significantly|dramatically|remarkably|interestingly|surprisingly)', content))
    score = max(0, 20 - unsupported * 3)
    issues = []
    if unsupported:
        issues.append(f"{unsupported} subjective descriptors found — replace with quantitative statements")
    return {"score": score, "status": f"{unsupported} subjective terms" if unsupported else "Claims appear data-driven",
            "issues": issues,
            "recommendations": ["Replace subjective terms with numerical evidence" if unsupported else "Good claim-evidence balance"]}


def _check_flow(content: str, sections: dict) -> dict:
    paragraphs = [p.strip() for p in content.split("\n\n") if len(p.strip()) > 50]
    transitions = len(re.findall(r'(?i)(Furthermore|Moreover|Additionally|In contrast|Similarly|Conversely|Therefore|Consequently|However|Nevertheless|Thus|Hence|In addition|On the other hand)', content))
    score = min(15, transitions * 2 + len(paragraphs))
    issues = []
    if len(paragraphs) < 3:
        issues.append("Very few paragraphs — expand content")
    if transitions < 2:
        issues.append("Few transition phrases — improve logical flow between ideas")
    return {"score": score, "status": f"{transitions} transitions, {len(paragraphs)} paragraphs",
            "issues": issues,
            "recommendations": ["Add transition phrases between sections" if transitions < 3 else "Good logical flow"]}


def _check_completeness(content: str, sections: dict) -> dict:
    word_count = len(content.split())
    has_abstract = bool(re.search(r'(?i)abstract', content))
    has_keywords = bool(re.search(r'(?i)keywords|key words', content))
    has_references = bool(re.search(r'(?i)reference|bibliography', content))
    checks = sum([has_abstract, has_keywords, has_references, word_count > 500, word_count > 2000])
    score = min(10, checks * 2)
    issues = []
    if not has_abstract and not sections.get("abstract"):
        issues.append("Missing abstract")
    if word_count < 500:
        issues.append(f"Word count low ({word_count}) — expand content")
    return {"score": score, "status": f"{word_count} words, abstract={'yes' if has_abstract else 'no'}",
            "issues": issues,
            "recommendations": ["Add an abstract (150-250 words)" if not has_abstract else "Content length adequate"]}


def _check_language(content: str) -> dict:
    first_person = len(re.findall(r'\b(I |We |Our |My )', content))
    passive = len(re.findall(r'\b(was|were|is|are|been|being)\s+\w+ed\b', content))
    score = max(0, 10 - first_person * 2)
    issues = []
    if first_person > 3:
        issues.append(f"{first_person} first-person phrases — use passive voice or third person")
    return {"score": score, "status": f"{first_person} first-person phrases",
            "issues": issues,
            "recommendations": ["Use passive voice for methods section" if first_person > 2 else "Academic tone appropriate"]}


def _check_duplicates(content: str) -> dict:
    sentences = [s.strip() for s in re.split(r'[.!?]+', content) if len(s.strip()) > 30]
    seen = set()
    dups = 0
    for s in sentences:
        normalized = " ".join(s.lower().split()[:10])
        if normalized in seen:
            dups += 1
        seen.add(normalized)
    score = max(0, 5 - dups)
    issues = []
    if dups:
        issues.append(f"{dups} near-duplicate sentences — remove repetition")
    return {"score": score, "status": f"{dups} near-duplicates" if dups else "No duplicate sentences detected",
            "issues": issues,
            "recommendations": ["Remove repetitive sentences" if dups else "No significant duplication"]}
