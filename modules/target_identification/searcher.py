"""Target Identification — search disease-target associations via public APIs.

Sources: OpenTargets Platform, UniProt, ChEMBL (via REST).
Falls back to curated local knowledge when API is unavailable.
"""
import logging
import json
import urllib.request
import urllib.error
from typing import Dict, List, Optional

log = logging.getLogger("target_identification.searcher")

OPENTARGETS_API = "https://api.platform.opentargets.org/api/v4"
CHEMBL_API = "https://www.ebi.ac.uk/chembl/api/data"
UNIPROT_API = "https://rest.uniprot.org/uniprotkb"

CURATED_TARGETS = {
    "cancer": [
        {"gene": "EGFR", "name": "Epidermal Growth Factor Receptor", "uniprot": "P00533",
         "score": 0.95, "druggability": "high", "known_drugs": ["Gefitinib", "Erlotinib", "Osimertinib"]},
        {"gene": "BRAF", "name": "Serine/threonine-protein kinase B-raf", "uniprot": "P15056",
         "score": 0.92, "druggability": "high", "known_drugs": ["Vemurafenib", "Dabrafenib"]},
        {"gene": "TP53", "name": "Tumor protein p53", "uniprot": "P04637",
         "score": 0.88, "druggability": "low", "known_drugs": []},
        {"gene": "KRAS", "name": "GTPase KRas", "uniprot": "P01116",
         "score": 0.90, "druggability": "medium", "known_drugs": ["Sotorasib", "Adagrasib"]},
        {"gene": "HER2", "name": "Receptor tyrosine-protein kinase erbB-2", "uniprot": "P04626",
         "score": 0.93, "druggability": "high", "known_drugs": ["Trastuzumab", "Lapatinib"]},
    ],
    "alzheimer": [
        {"gene": "APP", "name": "Amyloid-beta precursor protein", "uniprot": "P05067",
         "score": 0.88, "druggability": "medium", "known_drugs": ["Aducanumab", "Lecanemab"]},
        {"gene": "BACE1", "name": "Beta-secretase 1", "uniprot": "P56817",
         "score": 0.82, "druggability": "high", "known_drugs": []},
        {"gene": "MAPT", "name": "Microtubule-associated protein tau", "uniprot": "P10636",
         "score": 0.80, "druggability": "low", "known_drugs": []},
        {"gene": "APOE", "name": "Apolipoprotein E", "uniprot": "P02649",
         "score": 0.78, "druggability": "low", "known_drugs": []},
    ],
    "diabetes": [
        {"gene": "GLP1R", "name": "Glucagon-like peptide 1 receptor", "uniprot": "P43220",
         "score": 0.95, "druggability": "high", "known_drugs": ["Semaglutide", "Liraglutide"]},
        {"gene": "DPP4", "name": "Dipeptidyl peptidase 4", "uniprot": "P27487",
         "score": 0.90, "druggability": "high", "known_drugs": ["Sitagliptin", "Saxagliptin"]},
        {"gene": "SGLT2", "name": "Sodium-glucose co-transporter 2", "uniprot": "P31639",
         "score": 0.88, "druggability": "high", "known_drugs": ["Dapagliflozin", "Empagliflozin"]},
        {"gene": "PPARG", "name": "Peroxisome proliferator-activated receptor gamma", "uniprot": "P37231",
         "score": 0.82, "druggability": "high", "known_drugs": ["Rosiglitazone", "Pioglitazone"]},
    ],
    "inflammation": [
        {"gene": "TNF", "name": "Tumor necrosis factor", "uniprot": "P01375",
         "score": 0.95, "druggability": "high", "known_drugs": ["Adalimumab", "Infliximab"]},
        {"gene": "JAK1", "name": "Janus kinase 1", "uniprot": "P23458",
         "score": 0.90, "druggability": "high", "known_drugs": ["Tofacitinib", "Baricitinib"]},
        {"gene": "IL6", "name": "Interleukin-6", "uniprot": "P05231",
         "score": 0.88, "druggability": "high", "known_drugs": ["Tocilizumab", "Sarilumab"]},
        {"gene": "COX2", "name": "Cyclooxygenase 2 (PTGS2)", "uniprot": "P35354",
         "score": 0.85, "druggability": "high", "known_drugs": ["Celecoxib", "Etoricoxib"]},
    ],
    "cardiovascular": [
        {"gene": "PCSK9", "name": "Proprotein convertase subtilisin/kexin type 9", "uniprot": "Q8NBP7",
         "score": 0.92, "druggability": "high", "known_drugs": ["Evolocumab", "Alirocumab"]},
        {"gene": "ACE", "name": "Angiotensin-converting enzyme", "uniprot": "P12821",
         "score": 0.90, "druggability": "high", "known_drugs": ["Lisinopril", "Enalapril"]},
        {"gene": "HMGCR", "name": "HMG-CoA reductase", "uniprot": "P04035",
         "score": 0.95, "druggability": "high", "known_drugs": ["Atorvastatin", "Rosuvastatin"]},
    ],
    "infection": [
        {"gene": "3CLpro", "name": "3C-like proteinase (SARS-CoV-2)", "uniprot": "P0DTD1",
         "score": 0.92, "druggability": "high", "known_drugs": ["Nirmatrelvir"]},
        {"gene": "RdRp", "name": "RNA-dependent RNA polymerase", "uniprot": "P0DTD1",
         "score": 0.88, "druggability": "high", "known_drugs": ["Remdesivir", "Molnupiravir"]},
        {"gene": "HIV-PR", "name": "HIV protease", "uniprot": "P03366",
         "score": 0.95, "druggability": "high", "known_drugs": ["Ritonavir", "Darunavir"]},
    ],
}

GENE_DATABASE = {}
for disease, targets in CURATED_TARGETS.items():
    for t in targets:
        GENE_DATABASE[t["gene"].upper()] = {**t, "diseases": [disease]}


def _api_get(url: str, timeout: int = 8) -> Optional[Dict]:
    """Safe GET request with timeout and error handling."""
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, OSError) as e:
        log.debug(f"API request failed: {url} — {e}")
        return None


def search_by_disease(disease_query: str, limit: int = 10) -> Dict:
    """Search targets associated with a disease.

    First tries OpenTargets API, falls back to curated local database.
    """
    disease_lower = disease_query.lower().strip()

    # Try OpenTargets search
    ot_url = f"{OPENTARGETS_API}/graphql"
    # Use simple REST endpoint for disease search
    search_url = f"{OPENTARGETS_API}/search?q={urllib.request.quote(disease_query)}&size=5&entity=disease"
    api_result = _api_get(search_url)

    if api_result and api_result.get("data"):
        diseases = api_result["data"]
        if diseases:
            disease_id = diseases[0].get("id", "")
            assoc_url = f"{OPENTARGETS_API}/disease/{disease_id}/associations?size={limit}"
            assoc_data = _api_get(assoc_url)
            if assoc_data and assoc_data.get("data"):
                targets = []
                for row in assoc_data["data"][:limit]:
                    target = row.get("target", {})
                    targets.append({
                        "gene": target.get("approvedSymbol", "Unknown"),
                        "name": target.get("approvedName", ""),
                        "uniprot": target.get("proteinIds", [{}])[0].get("id", "") if target.get("proteinIds") else "",
                        "score": round(row.get("score", 0), 3),
                        "druggability": "unknown",
                        "known_drugs": [],
                        "source": "OpenTargets",
                    })
                return {
                    "query": disease_query,
                    "source": "OpenTargets API",
                    "disease_id": disease_id,
                    "disease_name": diseases[0].get("name", disease_query),
                    "num_targets": len(targets),
                    "targets": targets,
                }

    # Fallback to curated database
    matches = []
    for key, targets in CURATED_TARGETS.items():
        if disease_lower in key or key in disease_lower:
            matches = targets
            break

    if not matches:
        for key, targets in CURATED_TARGETS.items():
            if any(word in disease_lower for word in key.split()):
                matches = targets
                break

    if matches:
        results = []
        for t in matches[:limit]:
            results.append({**t, "source": "curated"})
        return {
            "query": disease_query,
            "source": "curated database",
            "num_targets": len(results),
            "targets": results,
        }

    return {
        "query": disease_query,
        "source": "none",
        "num_targets": 0,
        "targets": [],
        "message": f"No targets found for '{disease_query}'. Try: cancer, alzheimer, diabetes, inflammation, cardiovascular, infection",
    }


def search_by_gene(gene_symbol: str) -> Dict:
    """Look up a gene/target by symbol. Returns target info + associated diseases."""
    gene_upper = gene_symbol.upper().strip()

    # Try UniProt
    uni_url = f"{UNIPROT_API}/search?query=gene_exact:{gene_upper}+AND+organism_id:9606&format=json&size=1"
    api_result = _api_get(uni_url)

    if api_result and api_result.get("results"):
        entry = api_result["results"][0]
        protein_name = entry.get("proteinDescription", {}).get("recommendedName", {}).get("fullName", {}).get("value", "")
        uniprot_id = entry.get("primaryAccession", "")
        gene_names = [g.get("geneName", {}).get("value", "") for g in entry.get("genes", [])]

        return {
            "query": gene_symbol,
            "source": "UniProt",
            "gene": gene_upper,
            "name": protein_name,
            "uniprot": uniprot_id,
            "gene_names": gene_names,
            "organism": "Homo sapiens",
            "found": True,
        }

    # Fallback to curated
    if gene_upper in GENE_DATABASE:
        info = GENE_DATABASE[gene_upper]
        return {
            "query": gene_symbol,
            "source": "curated database",
            "found": True,
            **info,
        }

    return {
        "query": gene_symbol,
        "source": "none",
        "found": False,
        "message": f"Gene '{gene_symbol}' not found. Check the symbol or try a disease search.",
    }


def get_target_details(gene_symbol: str) -> Dict:
    """Get detailed target information including druggability, pathways, compounds.

    Aggregates from multiple sources (ChEMBL, UniProt, local).
    """
    gene_upper = gene_symbol.upper().strip()
    result = {
        "gene": gene_upper,
        "source": "aggregated",
    }

    # Local info
    if gene_upper in GENE_DATABASE:
        local = GENE_DATABASE[gene_upper]
        result.update({
            "name": local["name"],
            "uniprot": local["uniprot"],
            "druggability": local["druggability"],
            "known_drugs": local["known_drugs"],
            "diseases": local["diseases"],
        })

    # Try ChEMBL for bioactivity data
    chembl_url = f"{CHEMBL_API}/target/search.json?q={gene_upper}&limit=1"
    chembl_result = _api_get(chembl_url)

    if chembl_result and chembl_result.get("targets"):
        target = chembl_result["targets"][0]
        chembl_id = target.get("target_chembl_id", "")
        result["chembl_id"] = chembl_id
        result["target_type"] = target.get("target_type", "")
        result["organism"] = target.get("organism", "")

        if chembl_id:
            activities_url = f"{CHEMBL_API}/activity.json?target_chembl_id={chembl_id}&limit=5&pchembl_value__isnull=false"
            act_data = _api_get(activities_url)
            if act_data and act_data.get("activities"):
                result["chembl_activities"] = [{
                    "compound": a.get("molecule_chembl_id", ""),
                    "type": a.get("standard_type", ""),
                    "value": a.get("standard_value", ""),
                    "units": a.get("standard_units", ""),
                    "pic50": a.get("pchembl_value", ""),
                } for a in act_data["activities"][:5]]

    if "name" not in result:
        gene_info = search_by_gene(gene_upper)
        if gene_info.get("found"):
            result["name"] = gene_info.get("name", "")
            result["uniprot"] = gene_info.get("uniprot", "")

    return result
