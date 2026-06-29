"""Quick sanity check: test model on ESOL data itself."""
import pandas as pd
import numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors
import pickle
from scipy.spatial.distance import cdist

# Inline feature extraction
RDKIT_DESCRIPTOR_NAMES = [
    "MolWt", "MolLogP", "MolMR", "TPSA", "NumHDonors", "NumHAcceptors",
    "NumRotatableBonds", "NumAromaticRings", "NumSaturatedRings", "NumAliphaticRings",
    "NumHeteroatoms", "NumValenceElectrons", "NHOHCount", "NOCount", "RingCount",
    "NumAliphaticCarbocycles", "NumAliphaticHeterocycles", "NumAromaticCarbocycles",
    "NumAromaticHeterocycles", "NumSaturatedCarbocycles",
]

def extract_features(smiles):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, 2048)
    arr = np.zeros((2048,), dtype=np.float32)
    on_bits = fp.GetOnBits()
    if on_bits:
        arr[list(on_bits)] = 1.0
    values = []
    for name in RDKIT_DESCRIPTOR_NAMES:
        try:
            func = getattr(Descriptors, name)
            values.append(float(func(mol)))
        except Exception:
            values.append(0.0)
    desc = np.array(values, dtype=np.float32)
    return np.concatenate([arr, desc])

# Load model
with open("src/ml/models/logs_model.pkl", "rb") as f:
    model = pickle.load(f)

# Test on a few ESOL molecules
df = pd.read_csv("data/esol.csv")
print("Testing on ESOL data:")
for i, row in df.head(10).iterrows():
    x = extract_features(row['smiles'])
    if x is not None:
        pred = model.predict(x.reshape(1, -1))[0]
        actual = row['measured log solubility in mols per litre']
        print(f"  {row['smiles'][:30]:30s} | pred={pred:7.3f} | actual={actual:7.3f} | err={abs(pred-actual):.3f}")

print("\nTesting on known simple molecules:")
test_mols = [
    ("CCO", "ethanol"),
    ("c1ccccc1", "benzene"),
    ("CC(=O)O", "acetic acid"),
    ("CCCCCCCC", "octane"),
]
for smiles, name in test_mols:
    x = extract_features(smiles)
    if x is not None:
        pred = model.predict(x.reshape(1, -1))[0]
        print(f"  {name:15s} | pred={pred:7.3f}")

# Test ONNX
print("\nTesting ONNX model:")
try:
    import onnxruntime as ort
    sess = ort.InferenceSession("src/ml/models/logs_regressor.onnx")
    input_name = sess.get_inputs()[0].name
    for smiles, name in test_mols:
        x = extract_features(smiles)
        if x is not None:
            pred = sess.run(None, {input_name: x.reshape(1, -1)})[0][0][0]
            print(f"  {name:15s} | onnx_pred={pred:7.3f}")
except Exception as e:
    print(f"  ONNX test failed: {e}")
