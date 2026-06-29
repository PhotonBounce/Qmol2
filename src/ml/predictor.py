"""MLPredictor — ONNXRuntime-based inference engine with heuristic fallback.

- Loads ONNX models from disk (configurable via MODELS_DIR env var).
- Falls back to heuristic predictions if ONNX models are absent.
- Computes batch inference efficiently.
- Tracks applicability domain via Tanimoto similarity to training set representatives.

Usage:
    predictor = get_predictor()
    result = predictor.predict_single("CCO", model_id="aqueous_logs")
    batch = predictor.predict_batch(["CCO", "c1ccccc1"])
"""
from __future__ import annotations
import logging
import os
import warnings
from pathlib import Path
from typing import Any, List

import numpy as np

from src.ml import features, model_cards, applicability_domain
from src import predict as heuristic_module
from config import MODELS_DIR as CONFIG_MODELS_DIR

log = logging.getLogger(__name__)

# Default models directory: can be overridden by MODELS_DIR env var.
DEFAULT_MODELS_DIR = Path(__file__).parent / "models"
MODELS_DIR = Path(os.getenv("MODELS_DIR", str(CONFIG_MODELS_DIR) if CONFIG_MODELS_DIR.exists() else str(DEFAULT_MODELS_DIR)))

# Property name → ONNX filename mapping.
# Models are optional; missing files trigger heuristic fallback.
ONNX_MODEL_MAP = {
    "aqueous_logs": "logs_regressor.onnx",
    "bbb_probability": "bbb_classifier.onnx",
    "herg_risk": "herg_classifier.onnx",
    "gi_absorption": "gi_classifier.onnx",
    "sa_score_lite": "sa_regressor.onnx",
}


class MLPredictor:
    """Singleton-style ONNX inference engine.

    Attributes:
        sessions: dict mapping property_name -> onnxruntime.InferenceSession.
        available: set of property names with loaded ONNX models.
    """

    _instance: "MLPredictor | None" = None

    def __new__(cls) -> "MLPredictor":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self.sessions: dict[str, Any] = {}
        self.available: set[str] = set()
        self._feature_mode: dict[str, str] = {}
        self._load_models()

    def _load_models(self) -> None:
        """Attempt to load all ONNX models from MODELS_DIR."""
        try:
            import onnxruntime as ort
        except ImportError:
            warnings.warn(
                "onnxruntime not installed; all predictions will use heuristics.",
                stacklevel=2,
            )
            log.warning("onnxruntime not installed; ML predictions unavailable.")
            return

        # Prefer GPU EP if available, else CPU.
        providers = ort.get_available_providers()
        preferred = ["CUDAExecutionProvider", "ROCMExecutionProvider", "CPUExecutionProvider"]
        session_providers = [p for p in preferred if p in providers]
        if not session_providers:
            session_providers = ["CPUExecutionProvider"]

        for prop, filename in ONNX_MODEL_MAP.items():
            model_path = MODELS_DIR / filename
            if not model_path.exists():
                log.info("ONNX model not found: %s; will fallback for '%s'", model_path, prop)
                continue
            try:
                sess = ort.InferenceSession(str(model_path), providers=session_providers)
                self.sessions[prop] = sess
                self.available.add(prop)
                # Peek at the input name to determine feature mode.
                inp = sess.get_inputs()[0]
                if inp.shape[1] == 2048:
                    self._feature_mode[prop] = "morgan"
                elif inp.shape[1] == 20:
                    self._feature_mode[prop] = "descriptors"
                else:
                    self._feature_mode[prop] = "concat"
                log.info("Loaded ONNX model '%s' -> %s (input dim=%s)", prop, filename, inp.shape)
            except Exception as e:  # noqa: BLE001
                log.warning("Failed to load ONNX model '%s': %s", filename, e)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def predict_single(self, smiles: str, model_id: str | None = None) -> dict[str, Any]:
        """Predict a single molecule.

        Args:
            smiles: SMILES string.
            model_id: Property name, or None for full panel.

        Returns:
            If model_id is None: dict keyed by property name.
            If model_id is given: dict with value, confidence, in_domain, unit, model_version.
        """
        if model_id is None:
            return self.predict_all(smiles)

        return self._predict_one_property(smiles, model_id)

    def predict_all(self, smiles: str) -> dict[str, Any]:
        """Run the full prediction panel for a single molecule.

        Returns a dict keyed by property name, each containing
        value, confidence, in_domain, unit, model_version.
        """
        result: dict[str, Any] = {}
        for prop in ONNX_MODEL_MAP.keys():
            result[prop] = self._predict_one_property(smiles, prop)
        return result

    def predict_batch(self, smiles_list: List[str]) -> List[dict[str, Any]]:
        """Batch prediction for all properties.

        More efficient than looping predict_single because feature extraction
        and ONNX inference are vectorized.
        """
        if not smiles_list:
            return []

        # Pre-compute features for each mode once.
        features_by_mode: dict[str, np.ndarray] = {}
        for mode in {"morgan", "descriptors", "concat"}:
            try:
                features_by_mode[mode] = features.extract_batch_features(smiles_list, mode=mode)
            except Exception as e:  # noqa: BLE001
                log.warning("Batch feature extraction failed for mode=%s: %s", mode, e)
                features_by_mode[mode] = None  # type: ignore[assignment]

        results: List[dict[str, Any]] = []
        for idx, smiles in enumerate(smiles_list):
            mol_result: dict[str, Any] = {}
            for prop in ONNX_MODEL_MAP.keys():
                mol_result[prop] = self._predict_one_property(
                    smiles, prop, precomputed_features=features_by_mode, batch_idx=idx
                )
            results.append(mol_result)
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _predict_one_property(
        self,
        smiles: str,
        prop: str,
        precomputed_features: dict[str, np.ndarray] | None = None,
        batch_idx: int | None = None,
    ) -> dict[str, Any]:
        """Core prediction logic for a single property.

        Tries ONNX first; falls back to heuristics with a warning flag.
        """
        model_info = model_cards.get_model_info(prop)
        unit = model_info.get("unit", "")
        expected_r2 = model_info.get("expected_r2", None)

        # --- ONNX path -------------------------------------------------
        if prop in self.available and prop in self.sessions:
            try:
                return self._run_onnx(
                    smiles, prop, model_info, precomputed_features, batch_idx
                )
            except Exception as e:  # noqa: BLE001
                log.warning("ONNX inference failed for %s: %s; falling back to heuristics", prop, e)

        # --- Heuristic fallback -----------------------------------------
        return self._run_heuristic(smiles, prop, model_info)

    def _run_onnx(
        self,
        smiles: str,
        prop: str,
        model_info: dict[str, Any],
        precomputed_features: dict[str, np.ndarray] | None = None,
        batch_idx: int | None = None,
    ) -> dict[str, Any]:
        """Execute ONNX inference for a single property."""
        sess = self.sessions[prop]
        input_name = sess.get_inputs()[0].name
        mode = self._feature_mode.get(prop, "concat")

        # Get feature vector
        if precomputed_features is not None and batch_idx is not None and precomputed_features.get(mode) is not None:
            x = precomputed_features[mode][batch_idx : batch_idx + 1]
        else:
            x = features.extract_features(smiles, mode=mode).reshape(1, -1)

        # Run inference
        outputs = sess.run(None, {input_name: x})
        raw = outputs[0][0]

        # Post-process depending on model type
        model_type = model_info.get("model_type", "regressor")
        if model_type == "classifier":
            # Assume ONNX outputs probabilities or logits
            if raw.ndim >= 1 and raw.shape[0] > 1:
                # Multi-class: softmax
                probs = self._softmax(raw)
                pred_idx = int(np.argmax(probs))
                confidence = float(np.max(probs))
                value = model_info.get("class_labels", [str(i) for i in range(len(probs))])[pred_idx]
            else:
                # Binary: sigmoid
                prob = float(1 / (1 + np.exp(-raw)))
                confidence = max(prob, 1.0 - prob)
                value = bool(prob >= 0.5)
                # Map boolean to string if class labels exist
                if "class_labels" in model_info:
                    value = model_info["class_labels"][1 if value else 0]
        else:
            # Regressor
            value = float(raw)
            # Confidence = 1 - normalized error estimate (placeholder)
            # In production, replace with a calibrated uncertainty model.
            confidence = 0.85 if expected_r2 is not None else 0.50

        # Applicability domain
        ad_score = applicability_domain.compute_ad_score(smiles, prop)
        in_domain = ad_score >= 0.5

        return {
            "value": value,
            "confidence": round(confidence, 3),
            "in_domain": in_domain,
            "unit": unit,
            "model_version": model_info.get("model_version", "onnx-v1"),
            "source": model_info.get("source", "onnx"),
            "expected_r2": expected_r2,
        }

    def _run_heuristic(self, smiles: str, prop: str, model_info: dict[str, Any]) -> dict[str, Any]:
        """Run the legacy heuristic and wrap it in the new response schema."""
        try:
            heur = heuristic_module.predict_one(smiles)
            heur_dict = heur.to_dict()
        except Exception as e:  # noqa: BLE001
            log.error("Heuristic fallback failed for %s: %s", smiles, e)
            return {
                "value": None,
                "confidence": 0.0,
                "in_domain": False,
                "unit": model_info.get("unit", ""),
                "model_version": "heuristic-v1",
                "source": "heuristic",
                "warning": f"Heuristic fallback failed: {e}",
            }

        value = heur_dict.get(prop)
        # Heuristic confidence is lower because these are rule-based estimates.
        confidence = 0.45
        # Heuristics are coarse; flag out-of-domain unless very drug-like.
        in_domain = heur_dict.get("drug_like", False)

        return {
            "value": value,
            "confidence": confidence,
            "in_domain": in_domain,
            "unit": model_info.get("unit", ""),
            "model_version": "heuristic-v1",
            "source": "heuristic",
            "warning": "ONNX model not available; using heuristic fallback.",
            "expected_r2": None,
        }

    @staticmethod
    def _softmax(arr: np.ndarray) -> np.ndarray:
        """Numerically stable softmax."""
        exp_arr = np.exp(arr - np.max(arr))
        return exp_arr / np.sum(exp_arr)


# ------------------------------------------------------------------
# Singleton accessor
# ------------------------------------------------------------------

def get_predictor() -> MLPredictor:
    """Return the singleton MLPredictor instance."""
    return MLPredictor()
