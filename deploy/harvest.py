#!/usr/bin/env python3
"""Q-Mol Harvest Mode — Background data collection on local PC.

This script runs continuously on your local PC, fetching molecules from
PubChem and computing descriptors. It builds your local SQLite database
over time. No cloud needed. No API keys needed.

Usage:
    python deploy/harvest.py

Configure via environment variables:
    HARVEST_BATCH_SIZE=50       # Molecules per batch
    HARVEST_INTERVAL=300        # Seconds between batches
    HARVEST_MAX_HEAVY=20        # Max heavy atoms to include
"""
from __future__ import annotations
import os
import sys
import time
import logging
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from src import storage, compute
from src.pubchem import fetch_batch
import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("qmol.harvest")

BATCH_SIZE = int(os.getenv("HARVEST_BATCH_SIZE", "50"))
INTERVAL_SECONDS = int(os.getenv("HARVEST_INTERVAL", "300"))
MAX_HEAVY_ATOMS = int(os.getenv("HARVEST_MAX_HEAVY", "20"))
START_CID = int(os.getenv("HARVEST_START_CID", "1"))


def harvest_batch(start_cid: int, batch_size: int) -> tuple[int, int]:
    """Fetch and compute one batch of molecules. Returns (processed, next_cid)."""
    logger.info("Harvesting batch starting at CID %d (size=%d)", start_cid, batch_size)
    
    # Fetch from PubChem
    try:
        mols = fetch_batch(start_cid, batch_size)
    except Exception as exc:
        logger.error("Fetch failed: %s", exc)
        return 0, start_cid + batch_size
    
    if not mols:
        logger.info("No molecules returned. Moving to next batch.")
        return 0, start_cid + batch_size
    
    # Connect to DB
    conn = storage.connect(config.DB_PATH)
    processed = 0
    
    for mol in mols:
        try:
            if mol.get("num_heavy_atoms", 0) > MAX_HEAVY_ATOMS:
                continue
            
            # Compute descriptors
            row = compute.run(
                smiles=mol["smiles"],
                method="rdkit",
                basis="",
            )
            row["cid"] = mol["cid"]
            row["success"] = 1
            
            # Store
            storage.upsert(conn, row)
            processed += 1
            
        except Exception as exc:
            logger.warning("Failed to process CID %d: %s", mol.get("cid", "?"), exc)
    
    conn.close()
    logger.info("Batch complete: %d/%d molecules processed", processed, len(mols))
    return processed, start_cid + batch_size


def main():
    """Main harvest loop."""
    logger.info("=" * 50)
    logger.info("Q-Mol Harvest Mode")
    logger.info("=" * 50)
    logger.info("DB: %s", config.DB_PATH)
    logger.info("Batch size: %d", BATCH_SIZE)
    logger.info("Interval: %ds", INTERVAL_SECONDS)
    logger.info("Max heavy atoms: %d", MAX_HEAVY_ATOMS)
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 50)
    
    # Load state (last CID)
    state = storage.load_state(config.STATE_PATH)
    current_cid = state.get("last_cid", START_CID)
    total_processed = state.get("total_processed", 0)
    
    try:
        while True:
            processed, next_cid = harvest_batch(current_cid, BATCH_SIZE)
            total_processed += processed
            current_cid = next_cid
            
            # Save state
            storage.save_state(config.STATE_PATH, {
                "last_cid": current_cid,
                "total_processed": total_processed,
            })
            
            logger.info("Total harvested: %d molecules. Next CID: %d", total_processed, current_cid)
            logger.info("Sleeping %ds...", INTERVAL_SECONDS)
            time.sleep(INTERVAL_SECONDS)
            
    except KeyboardInterrupt:
        logger.info("\nHarvest stopped by user.")
        logger.info("Total molecules harvested: %d", total_processed)
        logger.info("Next start CID: %d", current_cid)


if __name__ == "__main__":
    main()
