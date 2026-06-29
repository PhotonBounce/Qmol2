"""Feature extraction for ML models.

Produces fixed-length numerical vectors from SMILES strings using:
- Morgan (ECFP4) fingerprints (2048-bit)
- RDKit 2D descriptors (top 20 canonical descriptors)

All vectors are numpy arrays of float32 for ONNXRuntime compatibility.
"""
from __future__ import annotations

import logging
from typing import List

import numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors, Crippen, Lipinski, rdMolDescriptors

log = logging.getLogger(__name__)

# Top 20 RDKit descriptors used in most ADMET training pipelines.
# Order is fixed and must match the training script.
RDKIT_DESCRIPTOR_NAMES = [
    "MolWt", "MolLogP", "MolMR", "TPSA", "NumHDonors", "NumHAcceptors",
    "NumRotatableBonds", "NumAromaticRings", "NumSaturatedRings", "NumAliphaticRings",
    "NumHeteroatoms", "NumValenceElectrons", "NHOHCount", "NOCount", "RingCount",
    "NumAliphaticCarbocycles", "NumAliphaticHeterocycles", "NumAromaticCarbocycles",
    "NumAromaticHeterocycles", "NumSaturatedCarbocycles",
]


def _descriptor_value(mol: Chem.Mol, name: str) -> float:
    """Safely get a single RDKit descriptor, returning NaN on failure."""
    try:
        func = getattr(Descriptors, name)
        return float(func(mol))
    except Exception:  # noqa: BLE001
        return float("nan")


def extract_morgan_fp(smiles: str, n_bits: int = 2048, radius: int = 2) -> np.ndarray:
    """Return a 2048-bit Morgan fingerprint as float32 np.ndarray.

    Args:
        smiles: Input SMILES.
        n_bits: Fingerprint length (default 2048).
        radius: Morgan radius (default 2 = ECFP4).

    Returns:
        float32 array of shape (n_bits,).
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles!r}")
    fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius=radius, nBits=n_bits)
    arr = np.zeros((n_bits,), dtype=np.float32)
    # Convert to list of ints, then assign
    on_bits = fp.GetOnBits()
    if on_bits:
        arr[list(on_bits)] = 1.0
    return arr


def extract_rdkit_descriptors(smiles: str) -> np.ndarray:
    """Return canonical RDKit 2D descriptors as float32 np.ndarray.

    Returns:
        float32 array of shape (len(RDKIT_DESCRIPTOR_NAMES),).
        NaN is used for descriptors that fail to compute.
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles!r}")
    values = [_descriptor_value(mol, name) for name in RDKIT_DESCRIPTOR_NAMES]
    return np.array(values, dtype=np.float32)


def extract_features(smiles: str, mode: str = "concat") -> np.ndarray:
    """Extract the complete feature vector for ML inference.

    Args:
        smiles: Input SMILES.
        mode: How to combine features.
            - "morgan": 2048-bit Morgan fingerprint only.
            - "descriptors": 20 RDKit descriptors only.
            - "concat": 2048 + 20 = 2068 vector (default).

    Returns:
        float32 np.ndarray.
    """
    if mode == "morgan":
        return extract_morgan_fp(smiles)
    if mode == "descriptors":
        return extract_rdkit_descriptors(smiles)
    if mode == "concat":
        morgan = extract_morgan_fp(smiles)
        desc = extract_rdkit_descriptors(smiles)
        return np.concatenate([morgan, desc])
    raise ValueError(f"Unknown feature mode: {mode!r}")


def extract_batch_features(smiles_list: List[str], mode: str = "concat") -> np.ndarray:
    """Extract features for a batch of molecules.

    Returns a 2D float32 array of shape (batch_size, n_features).
    Molecules that fail parsing are replaced with zero vectors and logged.
    """
    vectors = []
    for smi in smiles_list:
        try:
            vectors.append(extract_features(smi, mode=mode))
        except ValueError as e:
            log.warning("Feature extraction failed for %r: %s", smi, e)
            # Return zero vector of appropriate length as fallback
            n_features = 2048 if mode == "morgan" else 20 if mode == "descriptors" else 2068
            vectors.append(np.zeros(n_features, dtype=np.float32))
    return np.stack(vectors, axis=0)
