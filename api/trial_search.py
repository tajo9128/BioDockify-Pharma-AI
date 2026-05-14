from helpers.api import ApiHandler, Request
import urllib.request
import urllib.parse
import json
import re


class TrialSearch(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        query = input.get("query", "").strip()
        condition = input.get("condition", "").strip()
        status = input.get("status", "").strip()

        if not query and not condition:
            return {"error": "Drug name or condition required", "trials": []}

        # Build ClinicalTrials.gov API query
        terms = []
        if query:
            terms.append(urllib.parse.quote(query))
        if condition:
            terms.append(urllib.parse.quote(f"AREA[ConditionSearch] {condition}"))
        if status:
            status_map = {
                "recruiting": "AREA[OverallStatus] RECRUITING",
                "active": "AREA[OverallStatus] ACTIVE_NOT_RECRUITING",
                "completed": "AREA[OverallStatus] COMPLETED",
                "all": ""
            }
            if status in status_map and status_map[status]:
                terms.append(urllib.parse.quote(status_map[status]))

        expr = "+AND+".join(terms) if terms else urllib.parse.quote(query)
        fields = ["NCTId", "BriefTitle", "OverallStatus", "Phase", "LeadSponsorName",
                   "Condition", "BriefSummary", "StartDate", "CompletionDate", "LocationCountry"]

        url = (
            f"https://clinicaltrials.gov/api/query/study_fields?"
            f"expr={expr}&fields={','.join(fields)}&min_rnk=1&max_rnk=20&fmt=json"
        )

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/1.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read())
                studies = (data.get("StudyFieldsResponse", {})
                          .get("StudyFieldsList", []))

                trials = []
                for s in studies:
                    phases = [p for p in s.get("Phase", []) if p]
                    locations = list(set(
                        loc for loc in s.get("LocationCountry", []) if loc
                    ))
                    trials.append({
                        "nct_id": (s.get("NCTId") or [""])[0],
                        "title": (s.get("BriefTitle") or [""])[0],
                        "status": (s.get("OverallStatus") or [""])[0],
                        "phase": phases[0] if phases else "Not Specified",
                        "sponsor": (s.get("LeadSponsorName") or [""])[0],
                        "conditions": [c for c in s.get("Condition", []) if c],
                        "start_date": (s.get("StartDate") or [""])[0],
                        "completion_date": (s.get("CompletionDate") or [""])[0],
                        "locations": locations[:3],
                    })

                return {"trials": trials, "total": len(trials)}

        except Exception as e:
            return {"error": str(e), "trials": [], "message": "Could not reach ClinicalTrials.gov. Try asking the agent in chat to search instead."}
