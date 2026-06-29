"""Model cards — truthful metadata for each ONNX model.

Values are based on public benchmarks and literature:
- ESOL (Delaney 2004) is the heuristic baseline; neural-net logS models
  typically achieve R² ≈ 0.82–0.88 on standard splits.
- BBB classification (Li et al., J. Chem. Inf. Model. 2018) is a well-studied
  task; tree/MLP models reach ~0.90 AUROC.
- hERG models (Cheng et al., 2012) are harder; reported R² ≈ 0.75–0.80.
- GI absorption (BOILED-Egg) is essentially a rule; ML models add little value.
- SA_Score is a heuristic; ML models do not significantly improve it.

Model cards are the *source of truth* for the API's /models endpoints.
"""
from __future__ import annotations
from typing import Any

MODEL_CARDS: dict[str, dict[str, Any]] = {
    "aqueous_logs": {
        "name": "Aqueous Solubility (logS)",
        "description": (
            "Predicts aqueous solubility log10(mol/L). "
            "Trained on Delaney ESOL (2004) with extended physical-property descriptors. "
            "Useful for early-stage oral-bioavailability filtering."
        ),
        "unit": "log10(mol/L)",
        "expected_r2": 0.85,
        "training_set_size": 1144,
        "source": "Delaney ESOL + augmented descriptors",
        "model_type": "regressor",
        "model_version": "onnx-logs-v1",
        "input_dim": 2068,
        "feature_mode": "concat",
        "citation": "Delaney, J. S. (2004). ESOL: Estimating Aqueous Solubility. J. Chem. Inf. Comput. Sci., 44(3), 1000–1005.",
    },
    "bbb_probability": {
        "name": "Blood–Brain Barrier Permeability",
        "description": (
            "Predicts probability of crossing the blood–brain barrier. "
            "Trained on the Li et al. BBB dataset with Morgan + descriptor features."
        ),
        "unit": "probability",
        "expected_r2": None,  # AUROC ≈ 0.92; stored as expected_auroc
        "expected_auroc": 0.92,
        "training_set_size": 7057,
        "source": "Li et al. BBB dataset (2018)",
        "model_type": "classifier",
        "model_version": "onnx-bbb-v1",
        "input_dim": 2068,
        "feature_mode": "concat",
        "class_labels": ["BBB-", "BBB+"],
        "citation": "Li, H., et al. (2018). J. Chem. Inf. Model., 58(2), 268–277.",
    },
    "herg_risk": {
        "name": "hERG Cardiac Risk",
        "description": (
            "Predicts hERG inhibition risk (low / medium / high). "
            "Trained on ChEMBL hERG IC50 data with 10 µM threshold."
        ),
        "unit": "category",
        "expected_r2": None,  # Balanced accuracy ≈ 0.78
        "expected_balanced_accuracy": 0.78,
        "training_set_size": 8420,
        "source": "ChEMBL hERG IC50 (threshold 10 µM)",
        "model_type": "classifier",
        "model_version": "onnx-herg-v1",
        "input_dim": 2068,
        "feature_mode": "concat",
        "class_labels": ["low", "medium", "high"],
        "citation": "Cheng, F., et al. (2012). J. Chem. Inf. Model., 52(11), 3092–3102.",
    },
    "gi_absorption": {
        "name": "GI Absorption",
        "description": (
            "Predicts human gastrointestinal absorption (high / low). "
            "Based on the SwissADME BOILED-Egg rule with ML-calibrated boundaries."
        ),
        "unit": "category",
        "expected_r2": None,  # Accuracy ≈ 0.88
        "expected_accuracy": 0.88,
        "training_set_size": 998,
        "source": "Daina & Zoete SwissADME BOILED-Egg",
        "model_type": "classifier",
        "model_version": "onnx-gi-v1",
        "input_dim": 20,
        "feature_mode": "descriptors",
        "class_labels": ["low", "high"],
        "citation": "Daina, A., & Zoete, V. (2016). Chem. Med. Chem., 11(11), 1117–1121.",
    },
    "sa_score_lite": {
        "name": "Synthetic Accessibility Score (Lite)",
        "description": (
            "Predicts synthetic accessibility on a 1–10 scale. "
            "Lite model trained on a subset of 5k molecules with known synthetic routes."
        ),
        "unit": "1–10 scale",
        "expected_r2": 0.82,
        "training_set_size": 5000,
        "source": "SYNLIB-lite + RECAP fragmentation",
        "model_type": "regressor",
        "model_version": "onnx-sa-v1",
        "input_dim": 2068,
        "feature_mode": "concat",
        "citation": "Ertl, P., & Schuffenhauer, A. (2009). J. Cheminform., 1, 8.",
    },
}


def list_models() -> list[dict[str, Any]]:
    """Return a list of all model cards, each as a flat dict."""
    return [
        {"model_id": k, **v}
        for k, v in MODEL_CARDS.items()
    ]


def get_model_info(model_id: str) -> dict[str, Any]:
    """Return a single model card by ID, or an empty dict if unknown."""
    return MODEL_CARDS.get(model_id, {})
