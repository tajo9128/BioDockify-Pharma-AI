"""
BioDockify Writing Suite
=====================
Phase 4: Academic writing templates and article reviewer
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class ThesisSection:
    title: str
    description: str
    required: bool = True

THESIS_TEMPLATE = [
    ThesisSection("Abstract", "Summary of the entire thesis (250-300 words)", True),
    ThesisSection("Introduction", "Background, problem statement, research questions", True),
    ThesisSection("Literature Review", "Summary of existing research and gap analysis", True),
    ThesisSection("Methodology", "Research methods and experimental design", True),
    ThesisSection("Results", "Findings with data analysis", True),
    ThesisSection("Discussion", "Interpretation of results", True),
    ThesisSection("Conclusion", "Summary and future work", True),
    ThesisSection("References", "Bibliography in citation style", True),
]

REVIEW_TEMPLATE = """
# Article Review Template

## Summary
[One paragraph summarizing the main contribution]

## Strengths
- [Point 1]
- [Point 2]
- [Point 3]

## Weaknesses
- [Point 1]
- [Point 2]
- [Point 3]

## Specific Comments

### Introduction
[Comments on the introduction]

### Methodology
[Comments on methods]

### Results
[Comments on results]

### Discussion
[Comments on discussion]

## Minor Issues
- [Grammar/Style]
- [Formatting]

## Recommendation
- [ ] Accept
- [ ] Minor Revision
- [ ] Major Revision
- [ ] Reject

## Suggested Improvements
[Concrete suggestions for improvement]
"""

class AcademicWriter:
    """Helper for academic writing"""
    
    @staticmethod
    def get_thesis_template() -> List[Dict[str, str]]:
        """Get thesis structure template"""
        return [
            {"title": s.title, "description": s.description, "required": s.required}
            for s in THESIS_TEMPLATE
        ]
    
    @staticmethod
    def get_review_template() -> str:
        """Get article review template"""
        return REVIEW_TEMPLATE
    
    @staticmethod
    def format_reference(authors: List[str], year: int, title: str, journal: str, doi: str) -> str:
        """Format reference in standard style"""
        author_str = ", ".join(authors[:3])
        if len(authors) > 3:
            author_str += f" et al."
        return f"{author_str} ({year}). {title}. {journal}. DOI: {doi}"
    
    @staticmethod
    def generate_outline(topic: str, sections: int = 5) -> List[Dict[str, str]]:
        """Generate research paper outline"""
        return [
            {"section": f"Section {i+1}", "content": f"Content for {topic}", "words": 500}
            for i in range(sections)
        ]