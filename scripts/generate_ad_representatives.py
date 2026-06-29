"""Generate ad_representatives.json from training fingerprints."""
from pathlib import Path
import json
import numpy as np
from rdkit import DataStructs

def generate_ad_representatives():
    models_dir = Path("src/ml/models")
    ad_file = models_dir / "ad_representatives.json"
    
    ad_data = {}
    
    for prop, key in [("logs", "aqueous_logs"), ("herg", "herg_risk")]:
        npy_path = models_dir / f"{prop}_train_fps.npy"
        if not npy_path.exists():
            print(f"Skipping {prop}: no training fingerprints found")
            continue
        
        train_fps = np.load(npy_path)
        # Extract Morgan fingerprints (first 2048 columns)
        morgan_fps = train_fps[:, :2048].astype(np.uint8)
        
        # Sample up to 500 representatives for efficiency
        n = len(morgan_fps)
        if n > 500:
            indices = np.random.choice(n, 500, replace=False)
            morgan_fps = morgan_fps[indices]
        
        # Convert to base64-encoded bit vectors
        reps = []
        for fp in morgan_fps:
            bv = DataStructs.ExplicitBitVect(2048)
            for i, bit in enumerate(fp):
                if bit:
                    bv.SetBit(i)
            reps.append(bv.ToBase64())
        
        ad_data[key] = reps
        print(f"Generated {len(reps)} AD representatives for {key}")
    
    with open(ad_file, "w", encoding="utf-8") as f:
        json.dump(ad_data, f, indent=2)
    
    print(f"Saved AD representatives to {ad_file}")

if __name__ == "__main__":
    generate_ad_representatives()
