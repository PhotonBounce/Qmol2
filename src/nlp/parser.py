"""Parse natural language chemistry queries into structured API calls.

Examples:
- "find molecules like aspirin with good BBB penetration" 
  → {"endpoint": "similarity", "query": "CC(=O)Oc1ccccc1C(=O)O", "filters": {"bbb": ">0.7"}}
- "generate 50 molecules similar to caffeine with logP < 2"
  → {"endpoint": "generate", "seed": "CN1C=NC2=C1C(=O)N(C(=O)N2C)", "n": 50, "filters": {"logP": "<2"}}
- "what's the solubility of ibuprofen?"
  → {"endpoint": "predict", "smiles": "CC(C)Cc1ccc(C(C)C(=O)O)cc1", "properties": ["logS"]}
"""
from __future__ import annotations
import re
from typing import Any

# Known molecule name → SMILES mapping (expandable)
MOLECULE_NAMES = {
    "aspirin": "CC(=O)Oc1ccccc1C(=O)O",
    "caffeine": "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",
    "ibuprofen": "CC(C)Cc1ccc(C(C)C(=O)O)cc1",
    "paracetamol": "CC(=O)Nc1ccc(O)cc1",
    "acetaminophen": "CC(=O)Nc1ccc(O)cc1",
    "ethanol": "CCO",
    "benzene": "c1ccccc1",
    "glucose": "C(C1C(C(C(C(O1)O)O)O)O)O",
    "morphine": "CN1CC[C@]23c4c5ccc(O)c4O[C@H]2[C@@H](O)C=C[C@H]3[C@H]1C5",
    "penicillin": "CC1(C)SC2C(NC(=O)Cc3ccccc3)C(=O)N2C1C(=O)O",
}

def _resolve_molecule(name: str) -> str | None:
    """Resolve a molecule name to SMILES."""
    return MOLECULE_NAMES.get(name.lower().strip())

def _extract_number(query: str) -> int:
    """Extract a number from the query (e.g., '50 molecules')."""
    match = re.search(r'(\d+)', query)
    return int(match.group(1)) if match else 10

def _extract_property_filters(query: str) -> dict[str, str]:
    """Extract property filters like 'logP < 2', 'MW > 300'."""
    filters = {}
    # Match patterns like "logP < 2", "MW > 300", "solubility > 0.5"
    pattern = re.compile(r'(\w+)\s*([<>]=?)\s*([\d.]+)', re.IGNORECASE)
    for match in pattern.finditer(query):
        prop = match.group(1).lower()
        op = match.group(2)
        val = match.group(3)
        filters[prop] = f"{op}{val}"
    return filters

def _extract_property_requests(query: str) -> list[str]:
    """Extract which properties are being asked about."""
    properties = []
    prop_keywords = {
        "solubility": ["solubility", "logS", "aqueous"],
        "logp": ["logP", "lipophilicity"],
        "bbb": ["BBB", "blood-brain", "brain penetration"],
        "herg": ["hERG", "cardiac", "QT"],
        "toxicity": ["toxicity", "toxic", "mutagenic", "AMES"],
        "mw": ["molecular weight", "MW", "mass"],
        "qed": ["QED", "drug-likeness", "drug-like"],
    }
    q_lower = query.lower()
    for prop, keywords in prop_keywords.items():
        if any(kw in q_lower for kw in keywords):
            properties.append(prop)
    return properties

def parse_query(query: str) -> dict[str, Any]:
    """Parse a natural language query into an API call specification.
    
    Returns a dict with: endpoint, params, description
    """
    q_lower = query.lower().strip()
    
    # Check for similarity queries
    if any(w in q_lower for w in ["like", "similar to", "analog of", "derivative of"]):
        # Extract molecule name
        for name, smiles in MOLECULE_NAMES.items():
            if name in q_lower:
                return {
                    "endpoint": "similarity",
                    "params": {"query_smiles": smiles, "top_k": _extract_number(query)},
                    "filters": _extract_property_filters(query),
                    "description": f"Find molecules similar to {name}",
                }
        return {"endpoint": "similarity", "params": {}, "description": "Similarity search"}
    
    # Check for generation queries
    if any(w in q_lower for w in ["generate", "create", "design", "make"]):
        for name, smiles in MOLECULE_NAMES.items():
            if name in q_lower:
                return {
                    "endpoint": "generate",
                    "params": {"seed_smiles": [smiles], "n": _extract_number(query)},
                    "filters": _extract_property_filters(query),
                    "description": f"Generate molecules similar to {name}",
                }
        return {"endpoint": "generate", "params": {}, "description": "De novo generation"}
    
    # Check for property prediction queries
    if any(w in q_lower for w in ["what is", "what's", "predict", "calculate", "compute"]):
        for name, smiles in MOLECULE_NAMES.items():
            if name in q_lower:
                props = _extract_property_requests(query)
                return {
                    "endpoint": "predict",
                    "params": {"smiles": [smiles], "properties": props},
                    "description": f"Predict properties of {name}",
                }
        return {"endpoint": "predict", "params": {}, "description": "Property prediction"}
    
    # Check for optimization queries
    if any(w in q_lower for w in ["optimize", "improve", "better", "lead optimization"]):
        for name, smiles in MOLECULE_NAMES.items():
            if name in q_lower:
                return {
                    "endpoint": "optimize",
                    "params": {"smiles": smiles, "target_property": "QED"},
                    "description": f"Optimize {name}",
                }
        return {"endpoint": "optimize", "params": {}, "description": "Molecular optimization"}
    
    # Default: compute all properties
    for name, smiles in MOLECULE_NAMES.items():
        if name in q_lower:
            return {
                "endpoint": "compute",
                "params": {"smiles": [smiles]},
                "description": f"Compute descriptors of {name}",
            }
    
    return {
        "endpoint": "compute",
        "params": {"smiles": ["c1ccccc1"]},  # default
        "description": "Default compute",
    }
