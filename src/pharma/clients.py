"""
BioDockify Pharma Databases
=========================
Phase 3: Pharma/Biotech database connectors
"""

import os
import logging
import httpx
from typing import List, Dict, Any, Optional

logger = logging.getLogger("pharma")

class ChEMBLClient:
    """ChEMBL database client"""
    BASE_URL = "https://www.ebi.ac.uk/chembl/api/data"
    
    async def search_molecule(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for molecules by name"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/molecule.json",
                    params={"molecule_name__icontains": query, "limit": limit}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    results = []
                    for mol in data.get("molecules", []):
                        mol_data = mol.get("molecule_properties", {})
                        results.append({
                            "chembl_id": mol.get("molecule_chembl_id"),
                            "name": mol_data.get("preferred_name", ""),
                            "synonyms": mol_data.get("synonyms", ""),
                            "formula": mol_data.get("full_mwt", ""),
                            "source": "ChEMBL"
                        })
                    return results
        except Exception as e:
            logger.error(f"ChEMBL search error: {e}")
            return []
    
    async def get_molecule(self, chembl_id: str) -> Optional[Dict]:
        """Get molecule details by ChEMBL ID"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(f"{self.BASE_URL}/molecule/{chembl_id}.json")
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.error(f"ChEMBL get error: {e}")
            return None

class UniProtClient:
    """UniProt protein database client"""
    BASE_URL = "https://rest.uniprot.org/uniprotkb"
    
    async def search_protein(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for proteins"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/search",
                    params={"query": query, "size": limit, "format": "json"}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    results = []
                    for prot in data.get("results", []):
                        primary = prot.get("primaryAccession", "")
                        protein = prot.get("proteinDescription", {})
                        genes = prot.get("genes", [])
                        
                        names = []
                        if protein.get("recommendedName"):
                            names.append(protein["recommendedName"].get("fullName", {}).get("value", ""))
                        
                        results.append({
                            "uniprot_id": primary,
                            "name": names[0] if names else "",
                            "gene": genes[0].get("geneName", {}).get("value", "") if genes else "",
                            "organism": prot.get("organism", {}).get("scientificName", ""),
                            "source": "UniProt"
                        })
                    return results
        except Exception as e:
            logger.error(f"UniProt search error: {e}")
            return []

class PubChemClient:
    """PubChem database client"""
    BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    
    async def search_compound(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for compounds"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/compound/name/{query}/JSON",
                    params={"MaximumRows": limit}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    results = []
                    for prop in data.get("PropertyTable", {}).get("Properties", []):
                        results.append({
                            "cid": prop.get("CID"),
                            "name": prop.get("Title", ""),
                            "formula": prop.get("MolecularFormula", ""),
                            "weight": prop.get("MolecularWeight", ""),
                            "source": "PubChem"
                        })
                    return results
        except Exception as e:
            logger.error(f"PubChem search error: {e}")
            return []

class PDBClient:
    """PDB (Protein Data Bank) client"""
    BASE_URL = "https://data.rcsb.org/rest/v1"
    
    async def search_structure(self, query: str, limit: int = 10) -> List[Dict]:
        """Search PDB structures"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/core/dac",
                    params={"q": {"type": "terminal", "value": query}, "from": "rcsb_entry", "size": limit}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    results = []
                    for hit in data.get("hits", []):
                        results.append({
                            "pdb_id": hit.get("identifier", {}).get("value", ""),
                            "title": hit.get("title", ""),
                            "source": "PDB"
                        })
                    return results
        except Exception as e:
            logger.error(f"PDB search error: {e}")
            return []

async def search_pharma_databases(
    query: str,
    sources: List[str] = ["chembl", "uniprot", "pubchem"]
) -> Dict[str, List[Dict]]:
    """Search multiple pharma databases"""
    results = {}
    
    if "chembl" in sources:
        client = ChEMBLClient()
        results["chembl"] = await client.search_molecule(query)
    
    if "uniprot" in sources:
        client = UniProtClient()
        results["uniprot"] = await client.search_protein(query)
    
    if "pubchem" in sources:
        client = PubChemClient()
        results["pubchem"] = await client.search_compound(query)
    
    if "pdb" in sources:
        client = PDBClient()
        results["pdb"] = await client.search_structure(query)
    
    return results