"""Applicability Domain (AD) scoring.

Computes a Tanimoto-based similarity score (0–1) between a query molecule
and a pre-computed set of training-set representatives (Morgan fingerprints).

Score interpretation:
    ≥ 0.70  — high confidence (query well inside training domain)
    0.50–0.70 — moderate confidence (near boundary)
    < 0.50  — low confidence / out-of-domain (extrapolation warning)

The AD module is intentionally lightweight. It stores fingerprints as a
compressed JSON file (models/ad_representatives.json) rather than loading
full training sets into memory.
"""
from __future__ import annotations
import json
import logging
import os
from pathlib import Path
from typing import Any

import numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem
from rdkit import DataStructs

from config import MODELS_DIR as CONFIG_MODELS_DIR

log = logging.getLogger(__name__)

DEFAULT_AD_DIR = Path(__file__).parent / "models"
AD_DIR = Path(os.getenv("MODELS_DIR", str(CONFIG_MODELS_DIR) if CONFIG_MODELS_DIR.exists() else str(DEFAULT_AD_DIR)))
AD_FILE = AD_DIR / "ad_representatives.json"

# In-memory cache
_ad_cache: dict[str, Any] = {}


def _load_ad_representatives(prop: str) -> list | None:
    """Load training-set representative fingerprints for a property."""
    cache_key = f"{prop}_reps"
    if cache_key in _ad_cache:
        return _ad_cache[cache_key]

    if not AD_FILE.exists():
        return None

    try:
        with open(AD_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        reps = data.get(prop, [])
        _ad_cache[cache_key] = reps
        return reps
    except Exception as e:  # noqa: BLE001
        log.warning("Could not load AD representatives for %s: %s", prop, e)
        return None


def compute_ad_score(smiles: str, prop: str) -> float:
    """Compute Tanimoto-based applicability domain score (0–1).

    The score is the maximum Tanimoto similarity between the query molecule
    and any pre-computed training-set representative. If no representatives
    are available, returns a conservative default (0.5).

    Args:
        smiles: Query SMILES.
        prop: Property name (e.g. 'aqueous_logs').

    Returns:
        float in [0, 1].
    """
    reps = _load_ad_representatives(prop)
    if not reps:
        # No AD data available — neutral score
        return 0.5

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return 0.0

    query_fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius=2, nBits=2048)

    max_sim = 0.0
    for rep in reps:
        try:
            # Representatives are stored as base64-encoded bit vectors
            rep_fp = DataStructs.CreateFromBitString(rep) if isinstance(rep, str) and set(rep).issubset({"0", "1"}) else None
            if rep_fp is None and isinstance(rep, str):
                # Try base64
                try:
                    rep_fp = DataStructs.ExplicitBitVect(2048)
                    rep_fp.FromBase64(rep)
                except Exception:  # noqa: BLE001
                    rep_fp = None
            if rep_fp is None:
                continue
            sim = DataStructs.TanimotoSimilarity(query_fp, rep_fp)
            if sim > max_sim:
                max_sim = sim
        except Exception:  # noqa: BLE001
            continue

    return round(float(max_sim), 3)


def compute_ad_score_batch(smiles_list: list[str], prop: str) -> list[float]:
    """Batch version of compute_ad_score."""
    return [compute_ad_score(s, prop) for s in smiles_list]
