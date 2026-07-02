#!/usr/bin/env python3
"""Direct harvest — bypasses API auth and rate limits.

This script directly calls the Q-Mol compute/harvest modules
without going through the HTTP API. No API key needed. No rate limits.
Harvests as fast as your CPU can process molecules.

Usage:
    python scripts/harvest_direct.py --count 1000
    python scripts/harvest_direct.py --count 5000 --output data/harvest_bulk.sqlite
"""
from __future__ import annotations
import argparse
import sys
import time
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.compute import compute_molecule
from src import harvest as _harvest

LIBRARY = {
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
        "c1ccc(cc1)S(=O)(=O)N", "C1CCOC1", "C1CCNCC1", "C1CNC1",
        "O=C1NC=NC2=CC=CC=C12",
    ],
    "natural": [
        "C1=CC(=O)C=CC1=O", "CC1=CC(=O)CC(C)(C)C1", "C1CC2CCC3C(C2C1)CC(C3)C",
        "C1=COC=C1", "C1=CC=CC=C1O", "CC(C)=CCC=C(C)C",
        "C1=CC=C(C=C1)C2=CC=CC=C2", "C1=CC2=C(C=C1O)OCO2",
        "C1=C(C=C(C=C1O)O)O", "CC(C)C1=CC=C(C=C1)O",
    ],
    "fragments": [
        "CCO", "CC(=O)O", "CC(C)O", "c1ccncc1", "C1CCCCC1", "CCN", "CC(C)=O",
        "CC(=O)NC", "c1ccccc1O", "c1ccccc1N",
    ],
}


def generate_random_smiles():
    """Generate a simple, more chemistry-valid SMILES."""
    # Simpler approach: small carbon chains with occasional heteroatoms
    core = random.choice([
        "CCO", "CCN", "CCS", "CC(=O)O", "CC(=O)N", "c1ccccc1", "C1CCCCC1",
        "C1CCNCC1", "C1CCOC1", "c1ccncc1", "c1ccc(C)cc1", "CC(C)C",
        "CCC", "CCCC", "C=CC", "C#CC", "CC=CC", "c1ccc(O)cc1",
        "c1ccc(N)cc1", "c1ccc(Cl)cc1", "c1ccc(F)cc1", "CCc1ccccc1",
    ])
    # Append a small random fragment
    tail = random.choice([
        "", "C", "N", "O", "CC", "CN", "CO", "Cl", "F", "Br",
        "C(=O)O", "C(=O)N", "OH", "NH2", "CH3", "C2H5",
    ])
    s = core + tail
    # Sometimes wrap in ring
    if random.random() < 0.3:
        s = "C1" + s + "C1"
    return s


def get_pool():
    """Get all molecules from the library."""
    pool = []
    for cat in LIBRARY.values():
        pool.extend(cat)
    random.shuffle(pool)
    return pool


def harvest_one(smi: str) -> bool:
    """Compute and store one molecule."""
    try:
        result = compute_molecule(cid=-1, smiles=smi)
        if result and result.success:
            desc = result.to_dict()
            _harvest.ingest(smi, desc, source_endpoint="/compute-direct")
            return True
    except Exception as e:
        pass
    return False


def main():
    parser = argparse.ArgumentParser(description="Direct molecule harvester")
    parser.add_argument("--count", type=int, default=100, help="Number of molecules to harvest")
    parser.add_argument("--output", type=str, default=None, help="Output DB path (default: data/harvest.sqlite)")
    parser.add_argument("--random", action="store_true", help="Include random generated molecules")
    args = parser.parse_args()

    if args.output:
        _harvest.DEFAULT_DB = Path(args.output)

    print(f"Direct Harvest: Target {args.count} molecules")
    print(f"Database: {_harvest.DEFAULT_DB}")
    print("-" * 40)

    pool = get_pool()
    # Extend pool with random molecules (improved generator)
    if args.random:
        for _ in range(args.count):
            pool.append(generate_random_smiles())
        random.shuffle(pool)
    
    # If pool is smaller than target, just loop it
    while len(pool) < args.count:
        pool.extend(pool)
    random.shuffle(pool)

    start = time.time()
    success = 0
    failed = 0

    for i in range(args.count):
        smi = pool[i % len(pool)] if i < len(pool) else generate_random_smiles()
        ok = harvest_one(smi)
        if ok:
            success += 1
        else:
            failed += 1

        if (i + 1) % 10 == 0 or i == args.count - 1:
            elapsed = time.time() - start
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            print(f"  {i+1}/{args.count} | Success: {success} | Failed: {failed} | Rate: {rate:.1f}/sec")

    print("-" * 40)
    stats = _harvest.stats()
    print(f"Total in DB: {stats['total_molecules']}")
    print(f"Unique: {stats['unique_by_inchikey']}")
    print(f"Lipinski pass: {stats['lipinski_pass']}")
    print(f"High QED: {stats['qed_good']}")
    print(f"Done in {time.time() - start:.1f} seconds")


if __name__ == "__main__":
    main()
