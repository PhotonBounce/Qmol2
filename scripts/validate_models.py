"""Validate trained models on known molecules."""
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT))

import numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem
import pickle
from scipy.spatial.distance import cdist

def _load_model(name):
    models_dir = Path("src/ml/models")
    pkl_path = models_dir / f"{name}_model.pkl"
    with open(pkl_path, "rb") as f:
        return pickle.load(f)

def _get_train_fps(name):
    models_dir = Path("src/ml/models")
    npy_path = models_dir / f"{name}_train_fps.npy"
    if npy_path.exists():
        return np.load(npy_path)
    return None

def _compute_confidence(fp, train_fps):
    if train_fps is None or len(train_fps) == 0:
        return 0.5
    fp = fp.reshape(1, -1)
    distances = cdist(fp, train_fps, metric='jaccard')[0]
    min_dist = np.min(distances)
    confidence = max(0.0, 1.0 - min_dist / 0.5)
    return round(float(confidence), 3)

# Inline feature extraction (must match src.ml.features exactly)
RDKIT_DESCRIPTOR_NAMES = [
    "MolWt", "MolLogP", "MolMR", "TPSA", "NumHDonors", "NumHAcceptors",
    "NumRotatableBonds", "NumAromaticRings", "NumSaturatedRings", "NumAliphaticRings",
    "NumHeteroatoms", "NumValenceElectrons", "NHOHCount", "NOCount", "RingCount",
    "NumAliphaticCarbocycles", "NumAliphaticHeterocycles", "NumAromaticCarbocycles",
    "NumAromaticHeterocycles", "NumSaturatedCarbocycles",
]

def extract_morgan_fp(smiles, n_bits=2048, radius=2):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles!r}")
    fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius=radius, nBits=n_bits)
    arr = np.zeros((n_bits,), dtype=np.float32)
    on_bits = fp.GetOnBits()
    if on_bits:
        arr[list(on_bits)] = 1.0
    return arr

def extract_rdkit_descriptors(smiles):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles!r}")
    values = []
    for name in RDKIT_DESCRIPTOR_NAMES:
        try:
            func = getattr(Descriptors, name)
            values.append(float(func(mol)))
        except Exception:
            values.append(float("nan"))
    arr = np.array(values, dtype=np.float32)
    arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
    return arr

def extract_features(smiles, mode="concat"):
    if mode == "morgan":
        return extract_morgan_fp(smiles)
    if mode == "descriptors":
        return extract_rdkit_descriptors(smiles)
    if mode == "concat":
        morgan = extract_morgan_fp(smiles)
        desc = extract_rdkit_descriptors(smiles)
        return np.concatenate([morgan, desc])
    raise ValueError(f"Unknown feature mode: {mode!r}")

def predict(smiles, property_name):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles}")
    
    X = extract_features(smiles, mode='concat').reshape(1, -1)
    
    model = _load_model(property_name)
    value = float(model.predict(X)[0])
    
    train_fps = _get_train_fps(property_name)
    confidence = _compute_confidence(X, train_fps)
    
    return {
        "value": value,
        "property": property_name,
        "smiles": smiles,
        "confidence": confidence,
        "in_domain": confidence > 0.6,
    }

def validate():
    print("=" * 60)
    print("Model Validation")
    print("=" * 60)
    
    test_cases = [
        ("CCO", "logs"),           # ethanol — very soluble
        ("c1ccccc1", "logs"),      # benzene — insoluble
        ("c1ccc2c(c1)CCN2", "herg"),  # indoline — check hERG
        ("CCN(CC)CC", "herg"),     # triethylamine analog
    ]
    
    for smiles, prop in test_cases:
        try:
            result = predict(smiles, prop)
            print(f"\n{smiles} -> {prop}:")
            print(f"  value: {result['value']:.3f}")
            print(f"  confidence: {result['confidence']}")
            print(f"  in_domain: {result['in_domain']}")
        except Exception as e:
            print(f"\n{smiles} -> {prop}: ERROR: {e}")
    
    print("\n" + "=" * 60)
    print("Chemical sense checks:")
    print("  - Ethanol (CCO) should have high logS (soluble in water)")
    print("  - Benzene (c1ccccc1) should have low logS (insoluble in water)")
    print("  - hERG predictions should be in pIC50 range 4-10")
    print("=" * 60)

if __name__ == "__main__":
    validate()
