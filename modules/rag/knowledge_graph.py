"""Knowledge Graph — extract entities and build relationships from KB entries.

Extracts:
- Drug names (from SMILES patterns, known drug names)
- Target names (proteins, receptors, enzymes)
- Disease names
- Journal names
- Plant species names

Builds edges when two entities co-occur in the same KB entry.
"""
import re
from typing import List, Dict, Any, Set, Tuple
from collections import defaultdict


# Common pharmaceutical entity patterns
DRUG_PATTERNS = [
    r'\b(aspirin|ibuprofen|metformin|atorvastatin|lisinopril|amlodipine|omeprazole|losartan|simvastatin|metoprolol)\b',
    r'\b([A-Z][a-z]+(?:mab|nib|lib|zumab|ximab|tinib|zole|pril|sartan|statin|olol|pine|ide|ine|ase))\b',
    r'\b(CC\(|c1ccc|OCC|NC\(|SC\()\S{5,50}\b',  # SMILES patterns
]

TARGET_PATTERNS = [
    r'\b(EGFR|HER2|VEGFR|PD-1|PD-L1|ALK|BRAF|MEK|mTOR|PI3K|AKT|JAK|STAT|MAPK|ERK|p38|CDK|HDAC|SIRT|COX-2?|LOX|ACE|AT1|HMG-CoA)\b',
    r'\b(COX-\d|5-LOX|P450|CYP\d+[A-Z]\d*|P-glycoprotein|hERG)\b',
    r'\b(receptor|kinase|enzyme|transporter|channel|reductase|transferase|hydrolase|oxidase)\b',
]

DISEASE_PATTERNS = [
    r"\b(Alzheimer'?s|Parkinson'?s|Huntington'?s|diabetes|cancer|leukemia|lymphoma|melanoma|glioblastoma|carcinoma|sarcoma)\b",
    r'\b(hypertension|atherosclerosis|asthma|arthritis|lupus|fibrosis|cirrhosis|hepatitis|pneumonia|tuberculosis)\b',
    r'\b(depression|schizophrenia|epilepsy|migraine|obesity|anemia|thrombosis|sepsis|infection)\b',
]

PLANT_PATTERNS = [
    r'\b(Ginkgo biloba|Curcuma longa|Bacopa monnieri|Withania somnifera|Huperzia serrata)\b',
    r'\b(Salvia officinalis|Melissa officinalis|Rosmarinus officinalis|Centella asiatica|Panax ginseng)\b',
    r'\b(Camellia sinensis|Vitis vinifera|Silybum marianum|Valeriana officinalis|Passiflora incarnata)\b',
    r'\b(Echinacea|Garlic|Ginger|Turmeric|Saw Palmetto|St. John\'s Wort|Kava)\b',
]


def extract_entities(text: str) -> Dict[str, List[str]]:
    """Extract pharmaceutical entities from text.
    
    Returns dict with entity types as keys and lists of found entities as values.
    """
    entities = {
        "drugs": set(),
        "targets": set(),
        "diseases": set(),
        "plants": set(),
    }

    text_upper = text.upper()

    # Extract drugs
    for pattern in DRUG_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for m in matches:
            if isinstance(m, tuple):
                m = m[0] if m[0] else m[1] if len(m) > 1 else ""
            if m and len(m) > 2:
                entities["drugs"].add(m.strip())

    # Extract targets
    for pattern in TARGET_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for m in matches:
            if isinstance(m, tuple):
                m = m[0]
            if m and len(m) > 1:
                entities["targets"].add(m.strip().upper())

    # Extract diseases
    for pattern in DISEASE_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for m in matches:
            if isinstance(m, tuple):
                m = m[0]
            if m and len(m) > 2:
                entities["diseases"].add(m.strip().title())

    # Extract plant species
    for pattern in PLANT_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for m in matches:
            if isinstance(m, tuple):
                m = m[0]
            if m and len(m) > 2:
                entities["plants"].add(m.strip().title())

    return {k: sorted(list(v)) for k, v in entities.items()}


def build_graph(entries: List[Dict]) -> Dict[str, Any]:
    """Build knowledge graph from KB entries.
    
    Args:
        entries: List of KB entry dicts with 'title', 'content', 'category' fields
    
    Returns:
        Graph dict with 'nodes' and 'edges' lists
    """
    nodes = {}  # id -> node dict
    edges = []  # list of edge dicts
    edge_set = set()  # dedup edges

    for entry in entries:
        text = f"{entry.get('title', '')} {entry.get('content', '')}"
        entities = extract_entities(text)
        entry_id = entry.get("id", "")

        # Add entity nodes
        for entity_type, entity_list in entities.items():
            for entity_name in entity_list:
                node_id = f"{entity_type}:{entity_name}"
                if node_id not in nodes:
                    nodes[node_id] = {
                        "id": node_id,
                        "label": entity_name,
                        "type": entity_type,
                        "count": 0,
                        "entries": [],
                    }
                nodes[node_id]["count"] += 1
                if entry_id and entry_id not in nodes[node_id]["entries"]:
                    nodes[node_id]["entries"].append(entry_id)

        # Add entry node
        if entry_id:
            entry_node_id = f"entry:{entry_id}"
            nodes[entry_node_id] = {
                "id": entry_node_id,
                "label": entry.get("title", "")[:40],
                "type": "entry",
                "category": entry.get("category", ""),
                "count": 1,
            }

            # Create edges between entry and its entities
            for entity_type, entity_list in entities.items():
                for entity_name in entity_list:
                    entity_id = f"{entity_type}:{entity_name}"
                    edge_key = tuple(sorted([entry_node_id, entity_id]))
                    if edge_key not in edge_set:
                        edge_set.add(edge_key)
                        edges.append({
                            "source": entry_node_id,
                            "target": entity_id,
                            "type": "contains",
                        })

        # Create edges between co-occurring entities
        all_entity_ids = []
        for entity_type, entity_list in entities.items():
            for entity_name in entity_list:
                all_entity_ids.append(f"{entity_type}:{entity_name}")

        for i in range(len(all_entity_ids)):
            for j in range(i + 1, len(all_entity_ids)):
                edge_key = tuple(sorted([all_entity_ids[i], all_entity_ids[j]]))
                if edge_key not in edge_set:
                    edge_set.add(edge_key)
                    edges.append({
                        "source": all_entity_ids[i],
                        "target": all_entity_ids[j],
                        "type": "co_occurs",
                    })

    return {
        "nodes": list(nodes.values()),
        "edges": edges,
        "stats": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "by_type": {t: sum(1 for n in nodes.values() if n.get("type") == t) for t in ["drugs", "targets", "diseases", "plants", "entry"]},
        },
    }
