#!/usr/bin/env python3
"""
Q-Mol LinkedIn Outreach Manager
Manages prospect database, message generation, and action scheduling.
Runs on your PC via cron. Safe rate limits built in.

Usage:
    python linkedin_outreach.py --action add_prospect --name "John Doe" --title "Scientist" --url "linkedin.com/in/..."
    python linkedin_outreach.py --action generate_messages
    python linkedin_outreach.py --action execute_daily --limit 5
    python linkedin_outreach.py --action status
"""

import csv
import json
import os
import random
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Config
PROJECT_DIR = Path(__file__).parent.parent
DATA_DIR = PROJECT_DIR / "data" / "linkedin"
PROSPECTS_FILE = DATA_DIR / "prospects.csv"
LOG_FILE = DATA_DIR / "outreach_log.json"
TEMPLATES_FILE = PROJECT_DIR / "linkedin" / "outreach-templates.txt"
WEBBRIDGE_URL = "http://127.0.0.1:10086/command"
LINKEDIN_SESSION = "linkedin-qmol"

# LinkedIn safety limits
DAILY_CONNECTION_LIMIT = 15
DAILY_MESSAGE_LIMIT = 25
MIN_DELAY_SECONDS = 30
MAX_DELAY_SECONDS = 120

# Message templates
TEMPLATES = {
    "warm_intro": """Hi {name},

I came across your work on {topic} — really interesting approach to {detail}.

I recently built Q-Mol, a platform that auto-harvests drug-like molecules from PubChem with RDKit descriptors (Lipinski, QED, PAINS, etc). We're at {molecule_count}+ molecules and growing every 5 minutes.

The idea is to cut down manual curation time for compound libraries. Free 7-day trial, no CC required.

Worth a look? → https://photon-bounce.com/qmol/app/

Cheers,
Dmitriy""",

    "cold_outreach": """Hi {name},

Quick question: how much time does your team spend curating compound libraries for screening campaigns?

I built Q-Mol to automate that — it harvests drug-like molecules from PubChem with full ADMET descriptors (MW, LogP, TPSA, QED, Lipinski pass, PAINS hits). Currently {molecule_count}+ molecules, auto-growing.

Use cases we've seen:
- Virtual screening prep (export CSV for docking)
- ML training datasets (filtered by QED, no PAINS)
- Assay panel design (CNS-penetrant subsets, kinase scaffolds)

Free trial: https://photon-bounce.com/qmol/app/
Marketplace: https://photon-bounce.com/qmol/marketplace.html

Any feedback would be appreciated — especially on what filters you'd want.

Best,
Dmitriy Buchman""",

    "value_first": """Hi {name},

Saw your post about {topic}. I put together a free dataset of 50 drug-like molecules with ADMET descriptors that might be useful for your workflow — no PAINS, Lipinski-pass, QED > 0.6.

Grab it here: https://photon-bounce.com/qmol/app/ (free preview, no signup)

Also have a {molecule_count}+ molecule full dataset if you need more. Happy to chat.

Dmitriy""",

    "short_direct": """Hi {name},

Built a tool that auto-curates compound libraries from PubChem — {molecule_count}+ molecules with RDKit descriptors, free trial.

https://photon-bounce.com/qmol/app/

If this saves you even an hour a week, it's worth it.

Dmitriy"""
}


def ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def get_molecule_count():
    """Get current molecule count from the API or local DB."""
    try:
        import sqlite3
        db_path = PROJECT_DIR / "data" / "saas.sqlite"
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(DISTINCT smiles) FROM molecules")
            count = cursor.fetchone()[0] or 0
            conn.close()
            return count
    except Exception:
        pass
    return 2800  # fallback


def load_prospects():
    """Load prospects from CSV."""
    if not PROSPECTS_FILE.exists():
        return []
    with open(PROSPECTS_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def save_prospects(prospects):
    """Save prospects to CSV."""
    if not prospects:
        return
    fieldnames = list(prospects[0].keys())
    with open(PROSPECTS_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(prospects)


def load_log():
    """Load outreach log."""
    if not LOG_FILE.exists():
        return {"actions": [], "daily_counts": {}}
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_log(log):
    """Save outreach log."""
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)


def can_execute_today(log, action_type):
    """Check if we haven't exceeded daily limits."""
    today = datetime.now().strftime("%Y-%m-%d")
    daily = log.get("daily_counts", {}).get(today, {})
    count = daily.get(action_type, 0)
    limit = DAILY_CONNECTION_LIMIT if action_type == "connection" else DAILY_MESSAGE_LIMIT
    return count < limit


def record_action(log, action_type, prospect_name, details=""):
    """Record an action in the log."""
    today = datetime.now().strftime("%Y-%m-%d")
    if today not in log.get("daily_counts", {}):
        log["daily_counts"][today] = {}
    if action_type not in log["daily_counts"][today]:
        log["daily_counts"][today][action_type] = 0
    log["daily_counts"][today][action_type] += 1
    
    log["actions"].append({
        "timestamp": datetime.now().isoformat(),
        "type": action_type,
        "prospect": prospect_name,
        "details": details
    })
    save_log(log)


def generate_personalized_message(prospect, template_name="cold_outreach"):
    """Generate a personalized message for a prospect."""
    template = TEMPLATES.get(template_name, TEMPLATES["cold_outreach"])
    
    # Extract topic from title/company if available
    topic = prospect.get("topic", "your screening work")
    detail = prospect.get("detail", "compound library curation")
    
    # Try to infer from title
    title = prospect.get("title", "").lower()
    if "dock" in title or "virtual" in title:
        topic = "virtual screening"
        detail = "docking pipeline optimization"
    elif "ml" in title or "ai" in title or "machine learning" in title:
        topic = "ML for drug discovery"
        detail = "training dataset preparation"
    elif "medicinal" in title:
        topic = "medicinal chemistry"
        detail = "SAR and compound optimization"
    elif "cadd" in title:
        topic = "CADD"
        detail = "computational hit identification"
    
    molecule_count = get_molecule_count()
    
    message = template.format(
        name=prospect.get("name", "there").split()[0],
        topic=topic,
        detail=detail,
        molecule_count=f"{molecule_count:,}"
    )
    
    return message


def add_prospect(name, title, company, url, location="", notes=""):
    """Add a new prospect to the database."""
    ensure_dirs()
    prospects = load_prospects()
    
    # Check if already exists
    for p in prospects:
        if p.get("url") == url or p.get("name") == name:
            print(f"Prospect already exists: {name}")
            return False
    
    prospect = {
        "name": name,
        "title": title,
        "company": company,
        "url": url,
        "location": location,
        "notes": notes,
        "status": "new",  # new → connected → messaged → responded → interested → purchased
        "added_date": datetime.now().strftime("%Y-%m-%d"),
        "message_template": "cold_outreach",
        "last_action": "",
        "last_action_date": ""
    }
    prospects.append(prospect)
    save_prospects(prospects)
    print(f"Added prospect: {name} ({title} at {company})")
    return True


def generate_all_messages():
    """Generate personalized messages for all prospects that need them."""
    ensure_dirs()
    prospects = load_prospects()
    generated = 0
    
    for prospect in prospects:
        if prospect.get("status") in ["new", "connected"] and not prospect.get("message_ready"):
            template = prospect.get("message_template", "cold_outreach")
            message = generate_personalized_message(prospect, template)
            prospect["message_ready"] = "true"
            prospect["message_text"] = message
            generated += 1
    
    if generated > 0:
        save_prospects(prospects)
    print(f"Generated {generated} personalized messages")
    return generated


def print_status():
    """Print current outreach status."""
    ensure_dirs()
    prospects = load_prospects()
    log = load_log()
    today = datetime.now().strftime("%Y-%m-%d")
    daily = log.get("daily_counts", {}).get(today, {})
    
    # Count by status
    status_counts = {}
    for p in prospects:
        status = p.get("status", "new")
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print("\n" + "="*50)
    print("Q-MOL LINKEDIN OUTREACH STATUS")
    print("="*50)
    print(f"\nTotal Prospects: {len(prospects)}")
    print(f"Today's Actions: {sum(daily.values())}")
    print(f"  - Connections: {daily.get('connection', 0)}/{DAILY_CONNECTION_LIMIT}")
    print(f"  - Messages: {daily.get('message', 0)}/{DAILY_MESSAGE_LIMIT}")
    print(f"\nBy Status:")
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")
    print(f"\nMolecule Count: {get_molecule_count():,}")
    print(f"\nProspects needing attention:")
    for p in prospects:
        if p.get("status") == "new" and not p.get("message_ready"):
            print(f"  - {p['name']} ({p['title']})")
    print("="*50 + "\n")


def export_ready_messages():
    """Export messages ready to send to a copy-paste friendly file."""
    ensure_dirs()
    prospects = load_prospects()
    output_file = DATA_DIR / "ready_messages.txt"
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("Q-MOL LINKEDIN MESSAGES READY TO SEND\n")
        f.write("="*60 + "\n\n")
        
        for p in prospects:
            if p.get("status") == "connected" and p.get("message_ready"):
                f.write(f"TO: {p['name']}\n")
                f.write(f"URL: {p['url']}\n")
                f.write(f"TITLE: {p['title']}\n")
                f.write("-"*40 + "\n")
                f.write(p.get("message_text", "") + "\n")
                f.write("\n" + "="*60 + "\n\n")
    
    print(f"Exported ready messages to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Q-Mol LinkedIn Outreach Manager")
    parser.add_argument("--action", choices=[
        "add_prospect", "generate_messages", "execute_daily",
        "status", "export_ready", "bulk_add"
    ], default="status")
    parser.add_argument("--name", help="Prospect name")
    parser.add_argument("--title", help="Prospect title")
    parser.add_argument("--company", help="Prospect company")
    parser.add_argument("--url", help="LinkedIn URL")
    parser.add_argument("--location", default="", help="Location")
    parser.add_argument("--notes", default="", help="Notes")
    parser.add_argument("--limit", type=int, default=5, help="Daily action limit")
    parser.add_argument("--file", help="CSV file for bulk import")
    
    args = parser.parse_args()
    
    ensure_dirs()
    
    if args.action == "add_prospect":
        if not args.name or not args.url:
            print("Error: --name and --url required")
            sys.exit(1)
        add_prospect(args.name, args.title or "", args.company or "", args.url, args.location, args.notes)
    
    elif args.action == "generate_messages":
        generate_all_messages()
    
    elif args.action == "execute_daily":
        # This would connect to WebBridge - for now, generate messages and export
        generate_all_messages()
        export_ready_messages()
        print(f"\n{args.limit} actions ready to execute. Copy messages from ready_messages.txt and send via LinkedIn.")
    
    elif args.action == "export_ready":
        export_ready_messages()
    
    elif args.action == "bulk_add":
        if not args.file or not os.path.exists(args.file):
            print("Error: --file required for bulk import")
            sys.exit(1)
        with open(args.file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                add_prospect(
                    row.get("name", ""),
                    row.get("title", ""),
                    row.get("company", ""),
                    row.get("url", ""),
                    row.get("location", ""),
                    row.get("notes", "")
                )
                count += 1
        print(f"Bulk added {count} prospects")
    
    elif args.action == "status":
        print_status()


if __name__ == "__main__":
    main()
