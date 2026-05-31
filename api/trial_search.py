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

        # Build ClinicalTrials.gov API v2 query
        search_term = query or condition

        # Map status filter
        status_param = ""
        if status:
            status_map = {
                "recruiting": "RECRUITING",
                "active": "ACTIVE_NOT_RECRUITING",
                "completed": "COMPLETED",
            }
            if status in status_map:
                status_param = f"&filter.overallStatus={status_map[status]}"

        # Fields to retrieve
        fields = "NCTId,BriefTitle,OverallStatus,Phase,LeadSponsorName,Condition,BriefSummary,StartDate,CompletionDate,LocationCountry"

        url = (
            f"https://clinicaltrials.gov/api/v2/studies"
            f"?query.term={urllib.parse.quote(search_term)}"
            f"&pageSize=20"
            f"&fields={fields}"
            f"{status_param}"
            f"&format=json"
        )

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/1.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read())

            studies = data.get("studies", [])

            trials = []
            for s in studies:
                proto = s.get("protocolSection", {})
                ident = proto.get("identificationModule", {})
                status_mod = proto.get("statusModule", {})
                design = proto.get("designModule", {})
                sponsors = proto.get("sponsorCollaboratorsModule", {})
                conditions_mod = proto.get("conditionsModule", {})
                contacts = proto.get("contactsLocationsModule", {})

                phases = design.get("phases", [])
                phase = phases[0] if phases else "Not Specified"

                lead_sponsor = sponsors.get("leadSponsor", {}).get("name", "")

                conditions = conditions_mod.get("conditions", [])

                locations = []
                locs = contacts.get("locations", [])
                for loc in locs[:3]:
                    country = loc.get("country", "")
                    if country:
                        locations.append(country)

                trials.append({
                    "nct_id": ident.get("nctId", ""),
                    "title": ident.get("briefTitle", ""),
                    "status": status_mod.get("overallStatus", ""),
                    "phase": phase,
                    "sponsor": lead_sponsor,
                    "conditions": conditions,
                    "start_date": status_mod.get("startDateStruct", {}).get("date", ""),
                    "completion_date": status_mod.get("completionDateStruct", {}).get("date", ""),
                    "locations": list(set(locations))[:3],
                })

            return {"trials": trials, "total": len(trials)}

        except Exception as e:
            return {"error": str(e), "trials": [], "message": "Could not reach ClinicalTrials.gov. Try asking the agent in chat to search instead."}
