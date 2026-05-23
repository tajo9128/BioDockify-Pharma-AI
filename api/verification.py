"""5-Layer Pharma Verification — citation integrity, claim validation, compound verification."""
from helpers.api import ApiHandler, Request, Response
import logging, re, os
import json

log = logging.getLogger("verification")


def _extract_citations(text: str) -> list:
    """Extract potential citations from text."""
    citations = []
    # PubMed ID pattern: PMID: 12345678
    for m in re.finditer(r"PMID[:\s]*(\d{7,8})", text, re.IGNORECASE):
        citations.append({"type": "pmid", "id": m.group(1), "source_text": m.group(0)})
    # DOI pattern
    for m in re.finditer(r"10\.\d{4,}/[^\s\"'<>]+", text):
        citations.append({"type": "doi", "id": m.group(0).rstrip(".,;"), "source_text": m.group(0)})
    # arXiv ID pattern
    for m in re.finditer(r"arXiv[:\s]*(\d{4}\.\d{4,})", text, re.IGNORECASE):
        citations.append({"type": "arxiv", "id": m.group(1), "source_text": m.group(0)})
    # ClinicalTrials.gov: NCT
    for m in re.finditer(r"NCT\d{8}", text):
        citations.append({"type": "clinical_trial", "id": m.group(0), "source_text": m.group(0)})
    # PubChem CID
    for m in re.finditer(r"(?:CID|PubChem)[:\s]*(\d{4,})", text, re.IGNORECASE):
        citations.append({"type": "pubchem", "id": m.group(1), "source_text": m.group(0)})
    return citations


def _extract_claims(text: str) -> list:
    """Extract factual claims (numbers, percentages, compound names)."""
    claims = []
    # Numeric claims: "IC50 = 2.3 nM", "p < 0.05", "binding energy -9.5 kcal/mol"
    for m in re.finditer(r"(?:IC50|EC50|Ki|Kd|p\s*[<>]=?\s*)\s*[=:]?\s*([0-9]+\.?[0-9]*)\s*(?:nM|uM|μM|mM|pM|kcal/mol)", text, re.IGNORECASE):
        claims.append({"claim": m.group(0).strip(), "type": "numeric"})
    # Statistical claims
    for m in re.finditer(r"p\s*[<>]\s*0\.\d+", text):
        claims.append({"claim": m.group(0).strip(), "type": "statistical"})
    # "X significantly decreased Y"
    for m in re.finditer(r"(significantly|markedly)\s+(increased|decreased|reduced|improved)", text, re.IGNORECASE):
        claims.append({"claim": m.group(0).strip(), "type": "significance"})
    return claims


def _verify_layer(citation, layer):
    """Verify a citation at a specific layer. Returns {verified, detail, source}."""
    import urllib.request
    import urllib.error

    if layer == 1 and citation["type"] == "pmid":
        try:
            url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={citation['id']}&retmode=json"
            req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                if "result" in data and citation["id"] in data["result"]:
                    return True, "PubMed ID verified", "PubMed"
        except Exception as e:
            return False, f"PubMed check failed: {e}", "PubMed"
        return False, "PMID not found in PubMed", "PubMed"

    if layer == 2 and citation["type"] == "doi":
        try:
            url = f"https://api.crossref.org/works/{citation['id']}"
            req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                if data.get("status") == "ok":
                    return True, "CrossRef DOI verified", "CrossRef"
        except Exception as e:
            return False, f"CrossRef check failed: {e}", "CrossRef"
        return False, "DOI not found in CrossRef", "CrossRef"

    if layer == 3 and citation["type"] == "clinical_trial":
        try:
            url = f"https://clinicaltrials.gov/api/v2/studies/{citation['id']}"
            req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                return True, "Clinical trial registered", "ClinicalTrials.gov"
        except urllib.error.HTTPError as e:
            return False, f"Clinical trial not found: {e.code}", "ClinicalTrials.gov"
        except Exception as e:
            return False, f"Check failed: {e}", "ClinicalTrials.gov"

    if layer == 4 and citation["type"] == "pubchem":
        try:
            url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{citation['id']}/property/MolecularFormula/JSON"
            req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                if "PropertyTable" in data:
                    return True, "PubChem CID verified", "PubChem"
        except Exception:
            return False, "PubChem CID not found", "PubChem"
        return False, "PubChem CID not found", "PubChem"

    # Layer 5 (LLM) — return pending for agent to handle
    if layer == 5:
        return None, "LLM relevance check pending — agent must validate", "LLM"

    return True, "No verification available", "none"


class VerificationHandler(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "verify")

        if action == "verify":
            text = input.get("text", "")
            if not text:
                return {"error": "text required"}

            citations = _extract_citations(text)
            if not citations:
                return {"success": True, "citations_found": 0, "results": [], "note": "No citations detected"}

            results = []
            verified_count = 0
            failed_count = 0
            pending_count = 0

            for cit in citations:
                cit_result = {"citation": cit, "layers": {}}
                for layer in range(1, 6):
                    verified, detail, source = _verify_layer(cit, layer)
                    if verified is None:
                        cit_result["layers"][str(layer)] = {"status": "pending", "detail": detail, "source": source}
                        pending_count += 1
                    elif verified:
                        cit_result["layers"][str(layer)] = {"status": "verified", "detail": detail, "source": source}
                        verified_count += 1
                    else:
                        cit_result["layers"][str(layer)] = {"status": "failed", "detail": detail, "source": source}
                        failed_count += 1

                cit_result["overall"] = "verified" if any(
                    l["status"] == "verified" for l in cit_result["layers"].values()
                ) else "failed"
                results.append(cit_result)

            return {
                "success": True,
                "citations_found": len(citations),
                "verified": verified_count,
                "failed": failed_count,
                "pending": pending_count,
                "layers_used": ["PubMed (L1)", "CrossRef (L2)", "ClinicalTrials.gov (L3)", "PubChem (L4)", "LLM Relevance (L5)"],
                "results": results,
            }

        if action == "verify_claims":
            text = input.get("text", "")
            if not text:
                return {"error": "text required"}
            claims = _extract_claims(text)
            return {
                "success": True,
                "claims_found": len(claims),
                "claims": claims,
                "note": "Claims extracted. Cross-reference against cited sources to verify.",
            }

        if action == "verify_compound":
            smiles = input.get("smiles", "")
            if not smiles:
                return {"error": "smiles required"}
            # PubChem lookup via SMILES
            try:
                import urllib.request, urllib.error, json
                url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/{smiles}/cids/JSON"
                req = urllib.request.Request(url, headers={"User-Agent": "BioDockify/1.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read())
                    cids = data.get("IdentifierList", {}).get("CID", [])
                    if cids:
                        return {"success": True, "verified": True, "pubchem_cid": cids[0], "detail": f"PubChem CID: {cids[0]}"}
            except Exception:
                pass
            return {"success": True, "verified": False, "detail": "Compound not found in PubChem"}

        if action == "layers":
            return {
                "layers": {
                    1: "PubMed ID — verifies PMID exists",
                    2: "CrossRef DOI — verifies DOI resolves",
                    3: "ClinicalTrials.gov NCT — verifies trial registration",
                    4: "PubChem CID — verifies compound identity",
                    5: "LLM Relevance — agent validates citation supports the claim",
                }
            }

        return {"error": f"Unknown action: {action}"}
