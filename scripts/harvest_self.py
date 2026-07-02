"""Self-harvesting script — populate the Q-Mol database with test molecules.

This script submits a diverse set of molecules to the local API
to populate the harvest database before going live to users.
"""
from __future__ import annotations
import json
import urllib.request
import time
import random

API_BASE = "http://127.0.0.1:8000/v1"
API_KEY = "qmol_c1b08958fe62d8c8aba7fc11"  # Get this from /signup first

MOLECULES = {
    "drugs": [
        "CC(=O)Oc1ccccc1C(=O)O", "CC(C)Cc1ccc(cc1)C(C)C(=O)O",
        "CN1C=NC2=C1C(=O)N(C(=O)N2C)C", "CCN(CC)C(=O)C1(c2ccccc2)CCCCC1",
        "CN1C2CCC1CC(C2)OC(=O)C(CO)c3ccccc3",
        "COc1ccc2ncnc(Nc3ccc(F)c(Cl)c3)c2c1",
        "Cc1ccc(C)c(Oc2ccccc2)c1", "CC(C)NCC(O)COc1ccccc1",
        "C[C@H]1C[C@@H](C(=O)Nc2ccc(Cl)c(C(F)(F)F)c2)N(C)C1",
        "COc1ccc2nc(N3CCN(C)CC3)nc(C)c2c1",
    ],
    "scaffolds": [
        "c1ccccc1", "c1ccc2ccccc2c1", "c1ccc2ncncc2c1",
        "c1ccc2c(c1)[nH]c1ccccc12", "c1c[nH]cn1",
        "c1ccc(cc1)S(=O)(=O)N", "C1CCOC1", "C1CCNCC1",
        "C1CNC1", "O=C1NC=NC2=CC=CC=C12",
    ],
    "fragments": [
        "CCO", "CC(=O)O", "CC(C)O", "c1ccncc1",
        "C1CCCCC1", "CCN", "CC(C)=O", "CC(=O)NC",
        "c1ccccc1O", "c1ccccc1N",
    ],
    "natural_products": [
        "C1=CC(=O)C=CC1=O", "CC1=CC(=O)CC(C)(C)C1",
        "C1CC2CCC3C(C2C1)CC(C3)C", "C1=COC=C1",
        "C1=CC=CC=C1O", "CC(C)=CCC=C(C)C",
        "C1=CC=C(C=C1)C2=CC=CC=C2", "C1=CC2=C(C=C1O)OCO2",
        "C1=C(C=C(C=C1O)O)O", "CC(C)C1=CC=C(C=C1)O",
    ],
    "synthetic_accessibility": [
        "c1ccc(cc1)c2ccccc2", "CC(C)(C)C", "C1CC1",
        "C1CCC(CC1)C2CCCCC2", "C=Cc1ccccc1", "CC#N",
        "C1CCOC1", "c1ccc(cc1)C(=O)O", "c1ccc(cc1)C=O",
        "c1ccc(cc1)N=O",
    ],
}

HEADERS = {
    "Content-Type": "application/json",
    "x-api-key": API_KEY,
}


def _post(endpoint: str, data: dict) -> dict:
    req = urllib.request.Request(
        f"{API_BASE}{endpoint}",
        data=json.dumps(data).encode(),
        headers=HEADERS,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return {"error": e.code, "detail": body}
    except Exception as e:
        return {"error": str(e)}


def main():
    print("=" * 60)
    print("  Q-Mol Self-Harvesting")
    print("=" * 60)
    
    total = 0
    successes = 0
    
    for category, smiles_list in MOLECULES.items():
        print(f"\n[Category: {category}] {len(smiles_list)} molecules")
        for smi in smiles_list:
            endpoint = random.choice(["/compute", "/screen", "/predict", "/similarity"])
            
            if endpoint == "/compute":
                result = _post("/compute", {"smiles": [smi]})
            elif endpoint == "/screen":
                result = _post("/screen", {"smiles": [smi]})
            elif endpoint == "/predict":
                result = _post("/predict", {"smiles": [smi]})
            else:
                result = _post("/similarity", {"smiles": smi, "neighbors": 5})
            
            total += 1
            if "error" not in result:
                successes += 1
            else:
                print(f"  FAIL: {smi[:30]}... -> {result.get('error', 'unknown')}")
            
            time.sleep(0.05)
        
        print(f"  Done: {category}")
    
    print(f"\n{'='*60}")
    print(f"Total submitted: {total}")
    print(f"Successful: {successes}")
    print(f"Failed: {total - successes}")
    print(f"{'='*60}")
    
    # Check harvest stats with admin token (from .env)
    print("\n[Harvest Stats]")
    try:
        import os, dotenv
        dotenv.load_dotenv()
        admin = os.getenv("QMOL_ADMIN_TOKEN", "")
        if not admin:
            admin = "admin"
        req = urllib.request.Request(
            f"{API_BASE}/harvest/stats",
            headers={"x-admin-token": admin},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            stats = json.loads(resp.read().decode())
            for k, v in stats.items():
                print(f"  {k}: {v}")
    except Exception as e:
        print(f"  Stats: {e}")
    
    print("\nDone. Database populated.")


if __name__ == "__main__":
    main()
