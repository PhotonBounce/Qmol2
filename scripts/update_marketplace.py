#!/usr/bin/env python3
"""
Q-Mol Marketplace Auto-Updater
Updates marketplace.html with current molecule count from saas.sqlite
Run locally every 5 minutes via cron, or manually when needed.
"""

import sqlite3
import re
import os
from datetime import datetime

# Configuration
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'saas.sqlite')
MARKETPLACE_PATH = os.path.join(os.path.dirname(__file__), '..', 'marketplace.html')

def update_marketplace():
    """Read molecule count and update marketplace HTML"""
    
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return False
    
    if not os.path.exists(MARKETPLACE_PATH):
        print(f"Error: marketplace.html not found at {MARKETPLACE_PATH}")
        return False
    
    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Count total unique molecules
    cursor.execute("SELECT COUNT(DISTINCT smiles) FROM molecules")
    total = cursor.fetchone()[0] or 0
    
    # Count harvested molecules (mining bots)
    cursor.execute("SELECT COUNT(DISTINCT smiles) FROM molecules WHERE user_id IN (33,34,35,36,37,38,39,40,41,42)")
    harvested = cursor.fetchone()[0] or 0
    
    conn.close()
    
    # Read marketplace HTML
    with open(MARKETPLACE_PATH, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # Update molecule count in featured dataset (handle leading whitespace)
    html = re.sub(
        r"(\s*name:\s*'Q-Mol\s)[\d,]+(\sMolecule\sMega-Dataset'.*?count:)\s*\d+",
        r"\g<1>{:,}\g<2> {}".format(total, total),
        html,
        flags=re.DOTALL
    )
    
    # Update description text
    html = re.sub(
        r"\d{1,3}(?:,\d{3})*\s+unique\sdrug-like\smolecules",
        "{} unique drug-like molecules".format("{:,}".format(total)),
        html
    )
    html = re.sub(
        r"(\s*name:\s*'Q-Mol\s)[\d,]+(\sMolecule\sMega-Dataset'.*?count:)\s*\d+",
        r"\g<1>{:,}\g<2> {}".format(total, total),
        html,
        flags=re.DOTALL
    )
    html = re.sub(
        r"(name:\s*'Q-Mol\s[\d,]+\sMolecule\sMega-Dataset'.*?count:)\s*\d+",
        r"\1 {}".format(total),
        html,
        flags=re.DOTALL
    )
    
    # Update description text
    html = re.sub(
        r"\d{1,3}(?:,\d{3})*\s+unique\sdrug-like\smolecules",
        "{} unique drug-like molecules".format("{:,}".format(total)),
        html
    )
    
    # Write back
    with open(MARKETPLACE_PATH, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Updated marketplace: {total:,} molecules ({harvested:,} harvested by bots)")
    return True

if __name__ == '__main__':
    update_marketplace()
