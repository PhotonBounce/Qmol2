"""ML prediction package for Q-Mol.

Exports the public API for ONNX-based ADMET predictions with
applicability-domain scoring and graceful heuristic fallback.
"""
from __future__ import annotations
from typing import Any

from src.ml.predictor import get_predictor, MLPredictor
from src.ml.model_cards import list_models, get_model_info


def predict_single(smiles: str, model_id: str | None = None) -> dict[str, Any]:
    """Predict a single molecule.

    Args:
        smiles: SMILES string.
        model_id: Specific model to run, or None for the full panel.

    Returns:
        dict with value, confidence, in_domain, unit, model_version.
    """
    predictor = get_predictor()
    return predictor.predict_single(smiles, model_id=model_id)


def predict_all(smiles: str) -> dict[str, Any]:
    """Run the full ML prediction panel for a single molecule.

    Returns a dict keyed by property name (e.g. 'aqueous_logs').
    Each value is a dict with value, confidence, in_domain, unit, model_version.
    """
    predictor = get_predictor()
    return predictor.predict_all(smiles)


__all__ = [
    "predict_all",
    "predict_single",
    "list_models",
    "get_model_info",
    "get_predictor",
    "MLPredictor",
]
