"""Regulatory API - FDA/EMA guideline search and submission checklist."""
from helpers.api import ApiHandler, Request
import urllib.request
import urllib.parse
import json
import logging

logger = logging.getLogger("regulatory")


class RegulatorySearch(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        action = (input.get("action", "search") or "search").strip()

        if action == "search":
            return self._search(input)
        elif action == "checklist":
            return self._checklist(input)
        else:
            return {"actions": ["search", "checklist"]}

    def _search(self, input: dict) -> dict:
        query = (input.get("query", "") or "").strip()
        agency = (input.get("agency", "fda") or "fda").strip()

        if not query:
            return {"error": "Search query required"}

        results = []

        if agency == "fda":
            try:
                url = f"https://api.fda.gov/drug/label.json?search={urllib.parse.quote(query)}&limit=5"
                req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/1.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read())
                    for r in data.get("results", []):
                        results.append({
                            "title": r.get("openfda", {}).get("brand_name", [query])[0],
                            "source": "FDA",
                            "guideline": r.get("indications_and_usage", [""])[0][:300],
                            "id": r.get("id", ""),
                            "url": f"https://api.fda.gov/drug/label.json?search=id:{r.get('id','')}",
                        })
            except:
                results.append({
                    "title": query,
                    "source": "FDA (search via agent)",
                    "guideline": f"Search FDA guidelines for '{query}' via the agent chat for full access.",
                    "url": f"https://www.fda.gov/search?s={urllib.parse.quote(query)}",
                })

        if agency == "ema":
            results.append({
                "title": query,
                "source": "EMA",
                "guideline": f"Search EMA guidelines for '{query}' via the agent chat. EMA website: https://www.ema.europa.eu",
                "url": f"https://www.ema.europa.eu/en/search?search={urllib.parse.quote(query)}",
            })

        if not results:
            results.append({
                "title": query,
                "source": f"{agency.upper()}",
                "guideline": f"Ask the agent to search for '{query}' guidelines using the browser tool.",
                "url": "",
            })

        return {"query": query, "agency": agency.upper(), "results": results, "total": len(results)}

    def _checklist(self, input: dict) -> dict:
        submission_type = (input.get("type", "nda") or "nda").strip()

        checklists = {
            "nda": {
                "title": "New Drug Application (NDA) Checklist",
                "phases": [
                    {"phase": "Pre-IND Meeting", "items": ["Schedule meeting with FDA", "Prepare briefing document", "Submit meeting request (Form FDA-1571)", "Present development plan"], "estimated_time": "60 days"},
                    {"phase": "IND Application", "items": ["Complete Form FDA-1571", "Chemistry & Manufacturing data", "Pharmacology & Toxicology data", "Clinical protocols (Phase 1-3)", "Investigator brochure"], "estimated_time": "30 days"},
                    {"phase": "Clinical Trials", "items": ["Phase 1: Safety & dosing (20-100 subjects)", "Phase 2: Efficacy & side effects (100-300)", "Phase 3: Confirm efficacy, monitor AE (1000-3000)", "Submit annual reports (Form FDA-2252)"], "estimated_time": "2-5 years"},
                    {"phase": "NDA Submission", "items": ["Form FDA-356h application", "Full clinical study reports", "Safety updates (120-day)", "Proposed labeling", "Patent information (Form FDA-3542)", "Pediatric study requirements"], "estimated_time": "60 days"},
                    {"phase": "FDA Review", "items": ["60-day filing review", "120-day safety update", "Advisory committee meeting (if needed)", "Labeling negotiations", "Facility inspection (PAI)", "Risk Evaluation & Mitigation (REMS) if needed"], "estimated_time": "10-12 months"},
                ]
            },
            "anda": {
                "title": "Abbreviated New Drug Application (ANDA) Checklist",
                "phases": [
                    {"phase": "Pre-Submission", "items": ["Confirm reference listed drug (RLD)", "Patent certification (Para I-IV)", "Bioequivalence study design", "CMC documentation preparation"], "estimated_time": "3-6 months"},
                    {"phase": "ANDA Filing", "items": ["Form FDA-356h", "Basis for ANDA submission", "Bioequivalence data", "Chemistry & Manufacturing data", "Labeling comparison", "Patent certifications"], "estimated_time": "30 days"},
                    {"phase": "FDA Review", "items": ["Filing review (60 days)", "Bioequivalence review", "CMC review", "Labeling review", "Plant inspection"], "estimated_time": "10-12 months"},
                ]
            },
            "mua": {
                "title": "Marketing Authorization (EMA) Checklist",
                "phases": [
                    {"phase": "Pre-Submission", "items": ["Request EMA eligibility", "Appoint rapporteur/co-rapporteur", "Pre-submission meeting", "Prepare Module 1-5 (CTD format)"], "estimated_time": "6 months"},
                    {"phase": "MAA Submission", "items": ["Submit via eCTD", "Module 1: Administrative info", "Module 2: Quality overviews", "Module 3: Quality (CMC)", "Module 4: Nonclinical reports", "Module 5: Clinical reports"], "estimated_time": "14 months"},
                    {"phase": "CHMP Review", "items": ["Day 120: List of Questions", "Day 180: Joint Assessment Report", "Oral explanation (if needed)", "CHMP opinion", "EC decision (67 days)"], "estimated_time": "210 days"},
                ]
            },
        }

        checklist = checklists.get(submission_type, checklists["nda"])
        return {
            "type": submission_type.upper(),
            "title": checklist["title"],
            "phases": checklist["phases"],
            "total_phases": len(checklist["phases"]),
            "total_items": sum(len(p["items"]) for p in checklist["phases"]),
        }
