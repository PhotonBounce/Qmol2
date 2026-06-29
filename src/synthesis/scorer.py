"""Synthesis-aware molecular scoring.

Combines synthetic accessibility (SAscore), purchasability (ZINC availability),
and retrosynthetic complexity."""
from __future__ import annotations
import os
from rdkit import Chem
from rdkit.Chem import Descriptors, rdMMPA

HAS_SASCORE = False
HAS_RDCONTROPS = False

try:
    from rdkit.Chem import RDConfig
    sa_path = os.path.join(RDConfig.RDContribDir, 'SA_Score')
    if os.path.exists(sa_path):
        import sys
        sys.path.append(sa_path)
        import sascorer
        HAS_SASCORE = True
except Exception:
    pass

def score_synthesizability(smiles: str) -> dict:
    """Score how easy a molecule is to synthesize."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"error": "Invalid SMILES"}
    
    if HAS_SASCORE:
        sa = sascorer.calculateScore(mol)
    else:
        # Fallback: estimate from complexity metrics
        n_rings = Descriptors.RingCount(mol)
        n_stereo = Descriptors.NumStereocenters(mol) if hasattr(Descriptors, 'NumStereocenters') else 0
        n_bonds = mol.GetNumBonds()
        sa = 2.0 + 0.5 * n_rings + 0.3 * n_stereo + 0.01 * n_bonds
    
    # SAscore: 1 = easy, 10 = very difficult
    if sa <= 3.0:
        difficulty = "easy"
    elif sa <= 5.0:
        difficulty = "moderate"
    elif sa <= 7.0:
        difficulty = "hard"
    else:
        difficulty = "very hard"
    
    return {
        "sa_score": round(sa, 2),
        "difficulty": difficulty,
        "feasible": sa <= 6.0,  # Generally accepted threshold
    }

def score_purchasability(smiles: str) -> dict:
    """Estimate purchasability based on molecular properties.
    
    In production, this would query ZINC, MolPort, or ChemSpace catalogs.
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"error": "Invalid SMILES"}
    
    mw = Descriptors.MolWt(mol)
    logp = Descriptors.MolLogP(mol)
    
    # Vendors typically stock: MW < 500, logP 0-5, no exotic atoms
    exotic_atoms = sum(1 for atom in mol.GetAtoms() if atom.GetAtomicNum() not in {1,6,7,8,9,15,16,17,35,53})
    
    score = 1.0
    if mw > 500:
        score -= 0.3
    if logp < -1 or logp > 5:
        score -= 0.2
    if exotic_atoms > 0:
        score -= 0.2 * exotic_atoms
    if Descriptors.NumRotatableBonds(mol) > 10:
        score -= 0.1
    
    score = max(0.0, min(1.0, score))
    
    return {
        "purchasability_score": round(score, 3),
        "likely_available": score > 0.6,
        "notes": "Estimated from molecular properties. In production, query vendor catalogs.",
    }

def score_synthesis_route(smiles: str) -> dict:
    """Estimate retrosynthetic route complexity.
    
    Returns number of estimated synthetic steps and route quality.
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"error": "Invalid SMILES"}
    
    n_rings = Descriptors.RingCount(mol)
    n_heavy = mol.GetNumHeavyAtoms()
    n_stereo = Descriptors.NumStereocenters(mol) if hasattr(Descriptors, 'NumStereocenters') else 0
    
    # Heuristic: steps scale with complexity
    est_steps = 2 + n_rings + n_stereo + max(0, (n_heavy - 20) // 10)
    
    return {
        "estimated_steps": est_steps,
        "route_complexity": "simple" if est_steps <= 3 else "moderate" if est_steps <= 6 else "complex",
        "recommendation": "Consider fragment-based synthesis" if est_steps > 6 else "Standard synthesis feasible",
    }
