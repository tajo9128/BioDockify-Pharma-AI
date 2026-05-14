from helpers.api import ApiHandler, Request
import urllib.request
import urllib.parse
import json
import re


class PatentSearch(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict:
        query = input.get("query", "").strip()
        if not query:
            return {"error": "Search query required", "patents": []}

        results = []

        # Try Espacenet API (free, no key)
        try:
            espacenet_url = (
                "https://worldwide.espacenet.com/3.2/rest-services/"
                f"published-data/search?q={urllib.parse.quote(query)}&format=json&maxResults=10"
            )
            req = urllib.request.Request(espacenet_url, headers={"User-Agent": "BioDockify/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
                for doc in data.get("ops:world-patent-data", {}).get("ops:document-list", {}).get("ops:document", []):
                    meta = doc.get("ops:document-metadata", {})
                    bib = meta.get("ops:document-bibliographic-data", {})
                    title_data = bib.get("ops:invention-title", {})
                    title = title_data.get("value", "") if isinstance(title_data, dict) else str(title_data)
                    pub_ref = bib.get("ops:publication-reference", {})
                    doc_num = pub_ref.get("ops:document-id", {}).get("ops:doc-number", "")
                    date = pub_ref.get("ops:document-id", {}).get("ops:date", "")
                    results.append({
                        "title": title or "Patent",
                        "number": doc_num,
                        "date": date,
                        "source": "Espacenet"
                    })
        except Exception:
            pass

        # Fallback: try Google Patents
        if not results:
            try:
                google_url = f"https://patents.google.com/?q={urllib.parse.quote(query)}&num=10"
                req = urllib.request.Request(google_url, headers={"User-Agent": "BioDockify/1.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    html = resp.read().decode("utf-8", errors="replace")
                    # Extract patent numbers from results
                    for m in re.finditer(r'(US|EP|WO|CN|JP)\d{6,12}[A-Z]?\d?', html):
                        num = m.group(0)
                        if num not in [p["number"] for p in results]:
                            results.append({
                                "title": f"Patent related to {query}",
                                "number": num,
                                "date": "",
                                "source": "Google Patents"
                            })
            except Exception:
                pass

        # If still nothing, return a helpful message
        if not results:
            return {
                "patents": [],
                "message": "No patents found via API. Ask the agent in chat to search patents using the browser tool.",
                "suggestion": 'Try: "Search patents for ' + query + ' using the browser"'
            }

        return {"patents": results[:10], "total": len(results)}
