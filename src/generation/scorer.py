"""Multi-objective scoring for molecular optimization.

Provides pre-built objective functions that return a desirability score
in [0, 1] for common ADMET / drug-likeness properties.
"""
from __future__ import annotations

from typing import Callable

from rdkit import Chem
from rdkit.Chem import Descriptors, QED, Lipinski


def multi_objective_score(
    mol: Chem.Mol,
    objectives: dict[str, Callable[[Chem.Mol], float]],
    weights: dict[str, float] | None = None,
) -> dict:
    """Score a molecule against multiple objectives.

    Returns
    -------
    dict
        {
            "total": float,
            "scores": dict[str, float],
            "desirability": float,
        }
    """
    scores = {}
    for name, scorer in objectives.items():
        scores[name] = scorer(mol)

    if weights:
        total = sum(scores[k] * weights.get(k, 1.0) for k in scores)
        normalized_weights = sum(weights.get(k, 1.0) for k in scores)
    else:
        total = sum(scores.values())
        normalized_weights = len(scores)

    desirability = total / normalized_weights if normalized_weights > 0 else 0.0

    return {
        "total": total,
        "scores": scores,
        "desirability": desirability,
    }


# ------------------------------------------------------------------
# Pre-built objective factories (all return scorers in [0, 1])
# ------------------------------------------------------------------

def logp_objective(target: float, tolerance: float = 0.5) -> Callable[[Chem.Mol], float]:
    """Desirability for logP (clipped to [0, 1])."""
    def scorer(mol: Chem.Mol) -> float:
        logp = Descriptors.MolLogP(mol)
        return max(0.0, 1.0 - abs(logp - target) / tolerance)
    return scorer


def mw_objective(target: float, tolerance: float = 50.0) -> Callable[[Chem.Mol], float]:
    """Desirability for molecular weight (clipped to [0, 1])."""
    def scorer(mol: Chem.Mol) -> float:
        mw = Descriptors.MolWt(mol)
        return max(0.0, 1.0 - abs(mw - target) / tolerance)
    return scorer


def qed_objective() -> Callable[[Chem.Mol], float]:
    """Return QED (already in [0, 1])."""
    def scorer(mol: Chem.Mol) -> float:
        return QED.qed(mol)
    return scorer


def tpsa_objective(target: float, tolerance: float = 20.0) -> Callable[[Chem.Mol], float]:
    """Desirability for TPSA (clipped to [0, 1])."""
    def scorer(mol: Chem.Mol) -> float:
        tpsa = Descriptors.TPSA(mol)
        return max(0.0, 1.0 - abs(tpsa - target) / tolerance)
    return scorer


def synthesizability_objective() -> Callable[[Chem.Mol], float]:
    """SAscore desirability (clipped to [0, 1]).

    Falls back to 0.5 if the RDKit SAscore contrib module is not installed.
    """
    def scorer(mol: Chem.Mol) -> float:
        try:
            from rdkit.Chem import RDConfig
            import os
            sa_path = os.path.join(RDConfig.RDContribDir, "SA_Score")
            if os.path.exists(sa_path):
                import sys
                if sa_path not in sys.path:
                    sys.path.append(sa_path)
                import sascorer
                sa = sascorer.calculateScore(mol)
                return max(0.0, 1.0 - sa / 10.0)
        except Exception:
            pass
        return 0.5
    return scorer


def lipinski_objective() -> Callable[[Chem.Mol], float]:
    """Return 1.0 if the molecule passes Lipinski's Rule of Five, else 0.0."""
    def scorer(mol: Chem.Mol) -> float:
        violations = 0
        if Descriptors.MolWt(mol) > 500:
            violations += 1
        if Descriptors.MolLogP(mol) > 5:
            violations += 1
        if Descriptors.NumHDonors(mol) > 5:
            violations += 1
        if Descriptors.NumHAcceptors(mol) > 10:
            violations += 1
        return 1.0 if violations <= 1 else 0.0
    return scorer
