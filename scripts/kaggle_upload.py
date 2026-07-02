#!/usr/bin/env python3
"""Generate a Kaggle-ready dataset from your Q-Mol harvest.

Usage:
    python scripts/kaggle_upload.py --output-dir data/kaggle
    
Then zip the folder and upload to kaggle.com/datasets
"""
from __future__ import annotations
import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import harvest as _harvest


def generate_kaggle_dataset(output_dir: str, min_qed: float = 0.0):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    
    # Get all molecules from harvest DB
    conn = _harvest._connect()
    try:
        cur = conn.execute("SELECT * FROM molecules")
        rows = cur.fetchall()
    finally:
        conn.close()
    
    if not rows:
        print("No molecules in harvest DB. Run the miner first.")
        return
    
    # Write CSV
    csv_path = out / "molecules.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["cid", "smiles", "mw", "logp", "tpsa", "hbd", "hba", "qed", "lipinski_pass", "veber_pass", "pains_hit"])
        for row in rows:
            if row["qed"] >= min_qed:
                writer.writerow([row["cid"], row["smiles"], row["mw"], row["logp"], row["tpsa"], row["hbd"], row["hba"], row["qed"], row["lipinski_pass"], row["veber_pass"], row["pains_hit"]])
    
    # Write metadata
    meta = {
        "title": "Q-Mol Drug-Like Molecules",
        "subtitle": f"Curated molecular dataset with ADMET descriptors ({len(rows)} molecules)",
        "description": "Molecules harvested from PubChem with computed descriptors using RDKit. Includes QED, logP, TPSA, Lipinski rules, and PAINS filtering.",
        "keywords": ["cheminformatics", "molecular descriptors", "drug discovery", "ADMET", "virtual screening"],
        "license": "CC BY 4.0"
    }
    with open(out / "dataset-metadata.json", "w") as f:
        json.dump(meta, f, indent=2)
    
    print(f"Kaggle dataset ready: {out}")
    print(f"  CSV: {csv_path}")
    print(f"  Molecules: {len(rows)}")
    print(f"\nNext steps:")
    print(f"  1. Zip the folder: cd {out} && zip -r ../kaggle-dataset.zip .")
    print(f"  2. Upload to: https://www.kaggle.com/datasets")
    print(f"  3. Add thumbnail image (optional)")
    print(f"  4. Publish!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="data/kaggle", help="Output directory")
    parser.add_argument("--min-qed", type=float, default=0.0, help="Minimum QED filter")
    args = parser.parse_args()
    generate_kaggle_dataset(args.output_dir, args.min_qed)
