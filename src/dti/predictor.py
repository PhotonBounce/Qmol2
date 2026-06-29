"""Drug-target interaction prediction.

Uses a simple structure-activity model based on molecular descriptors
and known target ligand pharmacophores. For production, replace
with trained GNN models (e.g., DeepDTA, TransformerCPI)."""
from __future__ import annotations
import math
from rdkit import Chem
from rdkit.Chem import Descriptors, AllChem, rdMolDescriptors
from src.dti.targets import TARGETS

# Pharmacophore patterns for each target family
FAMILY_PATTERNS = {
    "Kinase": ["[NX3]C(=O)", "c1ccccc1", "C(=O)N"],  # ATP-competitive motifs
    "GPCR": ["c1ccccc1", "N", "O"],  # Aromatic + heteroatoms
    "Protease": ["C(=O)N", "C(=O)O"],  # Peptide-like
    "Hydrolase": ["C(=O)O", "N"],  # Esterase-like
    "Oxidoreductase": ["c1ccccc1", "O"],  # COX-like
}

def predict_binding_affinity(smiles: str, target_id: str) -> dict:
    """Predict binding affinity (pKi) for a molecule against a target.
    
    Returns: {"pKi": float, "confidence": float, "classification": str}
    """
    mol = Chem.MolFromSMILES(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles}")
    
    target = TARGETS.get(target_id)
    if not target:
        raise ValueError(f"Unknown target: {target_id}")
    
    family = target["family"]
    patterns = FAMILY_PATTERNS.get(family, [])
    
    # Score based on pharmacophore match count
    match_score = 0
    for pat in patterns:
        p = Chem.MolFromSmarts(pat)
        if p and mol.HasSubstructMatch(p):
            match_score += 1
    
    # Normalize by number of patterns
    match_ratio = match_score / len(patterns) if patterns else 0.5
    
    # Adjust by molecular properties (drug-likeness)
    mw = Descriptors.MolWt(mol)
    logp = Descriptors.MolLogP(mol)
    tpsa = Descriptors.TPSA(mol)
    hbd = Descriptors.NumHDonors(mol)
    hba = Descriptors.NumHAcceptors(mol)
    
    # Kinase inhibitors tend to be larger (MW 350-500)
    if family == "Kinase":
        size_score = max(0, 1 - abs(mw - 425) / 150)
    elif family == "GPCR":
        size_score = max(0, 1 - abs(mw - 400) / 150)
    else:
        size_score = max(0, 1 - abs(mw - 350) / 150)
    
    # Combine scores (heuristic)
    pKi = 6.0 + 2.0 * match_ratio + 1.0 * size_score + 0.5 * (1 - abs(logp - 2.5) / 3)
    pKi = max(4.0, min(10.0, pKi))  # Clamp to reasonable range
    
    confidence = 0.5 + 0.3 * match_ratio + 0.2 * size_score
    
    if pKi >= 8.0:
        classification = "strong binder"
    elif pKi >= 6.0:
        classification = "moderate binder"
    else:
        classification = "weak binder"
    
    return {
        "pKi": round(pKi, 2),
        "confidence": round(min(1.0, confidence), 3),
        "classification": classification,
        "target": target_id,
        "target_name": target["name"],
        "family": family,
        "disease_areas": target["disease_areas"],
    }

def predict_multi_target_activity(smiles: str, target_ids: list[str] | None = None) -> dict:
    """Predict activity across multiple targets."""
    if target_ids is None:
        target_ids = list(TARGETS.keys())
    
    results = {}
    for tid in target_ids:
        try:
            results[tid] = predict_binding_affinity(smiles, tid)
        except Exception as e:
            results[tid] = {"error": str(e)}
    
    # Compute polypharmacology score
    strong_binders = sum(1 for r in results.values() if isinstance(r, dict) and r.get("pKi", 0) >= 8.0)
    moderate_binders = sum(1 for r in results.values() if isinstance(r, dict) and 6.0 <= r.get("pKi", 0) < 8.0)
    
    return {
        "smiles": smiles,
        "target_results": results,
        "polypharmacology": {
            "strong_binders": strong_binders,
            "moderate_binders": moderate_binders,
            "total_tested": len(target_ids),
        },
    }
