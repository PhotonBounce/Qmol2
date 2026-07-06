#!/usr/bin/env python3
"""
Q-Mol LinkedIn Prospect Manager
===============================
Manages the prospect database with LinkedIn safety in mind.
Integrates with the safe automation system.

Usage:
    # Add a single prospect
    python linkedin_prospect_manager.py add "John Doe" "Scientist" "Biotech Inc" "linkedin.com/in/johndoe" --location "Boston"

    # Import from CSV
    python linkedin_prospect_manager.py import prospects.csv

    # List prospects by status
    python linkedin_prospect_manager.py list --status new

    # Update prospect status
    python linkedin_prospect_manager.py update "linkedin.com/in/johndoe" --status connected

    # Generate personalized messages for all ready prospects
    python linkedin_prospect_manager.py generate-messages

    # Show pipeline stats
    python linkedin_prospect_manager.py stats

    # Export high-quality prospects for targeting
    python linkedin_prospect_manager.py export-hot --output hot_prospects.csv
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
DATA_DIR = PROJECT_DIR / "data" / "linkedin"
PROSPECTS_FILE = DATA_DIR / "prospects.csv"
MESSAGES_FILE = DATA_DIR / "generated_messages.json"

# Valid status transitions
VALID_STATUSES = [
    "new",           # Just added, no action taken
    "viewed",        # Profile viewed
    "pending",       # Connection request sent, waiting
    "connected",     # They accepted connection
    "messaged",      # First message sent
    "followed_up",   # Follow-up sent
    "responded",     # They replied
    "interested",    # Showed interest in product
    "purchased",     # Bought dataset
    "not_interested",# Declined
    "unreachable",   # Profile not found / left company
]


def ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_prospects() -> list[dict]:
    if not PROSPECTS_FILE.exists():
        return []
    with open(PROSPECTS_FILE, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def save_prospects(prospects: list[dict]):
    if not prospects:
        # Write empty file with headers
        with open(PROSPECTS_FILE, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "name", "title", "company", "url", "location",
                "status", "added_date", "last_updated", "notes",
                "message_template", "source", "priority"
            ])
            writer.writeheader()
        return

    fieldnames = list(prospects[0].keys())
    with open(PROSPECTS_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(prospects)


def normalize_url(url: str) -> str:
    """Normalize LinkedIn URL."""
    url = url.strip()
    if url.startswith("http"):
        return url
    if url.startswith("/in/"):
        return f"https://www.linkedin.com{url}"
    if url.startswith("in/"):
        return f"https://www.linkedin.com/{url}"
    return f"https://www.linkedin.com/in/{url}"


def get_priority(title: str, company: str) -> str:
    """Score prospect priority based on title/company."""
    title_lower = title.lower()
    company_lower = company.lower() if company else ""

    # High-value keywords
    high = ["founder", "ceo", "cto", "chief", "director", "head of", "principal"]
    medium = ["senior", "lead", "manager", "scientist", "researcher"]

    for h in high:
        if h in title_lower:
            return "high"
    for m in medium:
        if m in title_lower:
            return "medium"

    return "low"


def add_prospect(name: str, title: str, company: str, url: str,
                 location: str = "", notes: str = "", source: str = "manual"):
    """Add a new prospect."""
    ensure_dirs()
    prospects = load_prospects()

    normalized_url = normalize_url(url)

    # Check for duplicates
    for p in prospects:
        if p.get("url") == normalized_url or p.get("name", "").lower() == name.lower():
            print(f"⚠️  Prospect already exists: {name}")
            return False

    prospect = {
        "name": name,
        "title": title,
        "company": company,
        "url": normalized_url,
        "location": location,
        "status": "new",
        "added_date": datetime.now().strftime("%Y-%m-%d"),
        "last_updated": datetime.now().isoformat(),
        "notes": notes,
        "message_template": "value_first",
        "source": source,
        "priority": get_priority(title, company),
    }

    prospects.append(prospect)
    save_prospects(prospects)
    print(f"✅ Added: {name} ({title} @ {company}) [Priority: {prospect['priority']}]")
    return True


def import_csv(filepath: str):
    """Import prospects from CSV file."""
    ensure_dirs()
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return

    count = 0
    skipped = 0
    with open(filepath, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("name", "").strip()
            title = row.get("title", "").strip()
            company = row.get("company", "").strip()
            url = row.get("url", "").strip()

            if not name or not url:
                skipped += 1
                continue

            if add_prospect(name, title, company, url,
                          row.get("location", ""), row.get("notes", ""), "import"):
                count += 1

    print(f"\n{'='*40}")
    print(f"Import complete: {count} added, {skipped} skipped")
    print(f"{'='*40}")


def list_prospects(status: str = None, limit: int = 50):
    """List prospects with optional filter."""
    prospects = load_prospects()

    if status:
        prospects = [p for p in prospects if p.get("status") == status]

    print(f"\n{'='*80}")
    print(f"PROSPECTS ({len(prospects)} total)")
    print(f"{'='*80}")
    print(f"{'Name':<25} {'Title':<25} {'Status':<12} {'Priority':<8}")
    print("-"*80)

    for p in prospects[:limit]:
        name = p.get("name", "")[:24]
        title = p.get("title", "")[:24]
        stat = p.get("status", "new")[:11]
        pri = p.get("priority", "low")
        print(f"{name:<25} {title:<25} {stat:<12} {pri:<8}")

    if len(prospects) > limit:
        print(f"\n... and {len(prospects) - limit} more")
    print(f"{'='*80}\n")


def update_status(url_or_name: str, status: str, notes: str = ""):
    """Update a prospect's status."""
    if status not in VALID_STATUSES:
        print(f"❌ Invalid status. Valid: {', '.join(VALID_STATUSES)}")
        return

    prospects = load_prospects()
    found = False

    for p in prospects:
        if p.get("url") == normalize_url(url_or_name) or p.get("name") == url_or_name:
            old_status = p.get("status", "new")
            p["status"] = status
            p["last_updated"] = datetime.now().isoformat()
            if notes:
                p["notes"] = (p.get("notes", "") + "; " + notes).strip("; ")
            found = True
            print(f"✅ Updated: {p['name']}: {old_status} → {status}")
            break

    if found:
        save_prospects(prospects)
    else:
        print(f"❌ Prospect not found: {url_or_name}")


def generate_messages():
    """Generate personalized messages for all connected prospects."""
    from linkedin_safe_automation import generate_message

    ensure_dirs()
    prospects = load_prospects()
    messages = {}
    generated = 0

    for p in prospects:
        if p.get("status") == "connected":
            template = p.get("message_template", "value_first")
            msg = generate_message(p, template)
            messages[p["url"]] = {
                "name": p["name"],
                "message": msg,
                "generated_at": datetime.now().isoformat(),
            }
            generated += 1

    with open(MESSAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, indent=2)

    print(f"✅ Generated {generated} messages → {MESSAGES_FILE}")


def show_stats():
    """Show pipeline statistics."""
    prospects = load_prospects()

    if not prospects:
        print("\nNo prospects in database yet.\n")
        return

    status_counts = {}
    priority_counts = {}
    source_counts = {}

    for p in prospects:
        s = p.get("status", "new")
        status_counts[s] = status_counts.get(s, 0) + 1
        priority_counts[p.get("priority", "low")] = priority_counts.get(p.get("priority", "low"), 0) + 1
        source_counts[p.get("source", "manual")] = source_counts.get(p.get("source", "manual"), 0) + 1

    # Calculate conversion rates
    total = len(prospects)
    connected = status_counts.get("connected", 0) + status_counts.get("messaged", 0) + status_counts.get("responded", 0) + status_counts.get("interested", 0) + status_counts.get("purchased", 0)
    responded = status_counts.get("responded", 0) + status_counts.get("interested", 0) + status_counts.get("purchased", 0)
    interested = status_counts.get("interested", 0) + status_counts.get("purchased", 0)
    purchased = status_counts.get("purchased", 0)

    print(f"\n{'='*60}")
    print(f"Q-MOL LINKEDIN PIPELINE STATS")
    print(f"{'='*60}")
    print(f"\n📊 PROSPECTS BY STATUS:")
    for status in VALID_STATUSES:
        count = status_counts.get(status, 0)
        pct = count / total * 100 if total > 0 else 0
        bar = "█" * int(pct / 2)
        print(f"  {status:15s}: {count:>4} ({pct:>5.1f}%) {bar}")

    print(f"\n🎯 BY PRIORITY:")
    for pri in ["high", "medium", "low"]:
        count = priority_counts.get(pri, 0)
        print(f"  {pri.capitalize():8s}: {count}")

    print(f"\n📥 BY SOURCE:")
    for source, count in sorted(source_counts.items()):
        print(f"  {source}: {count}")

    print(f"\n📈 CONVERSION FUNNEL:")
    print(f"  Total Prospects:  {total}")
    print(f"  Connected:        {connected}  ({connected/total*100:.1f}% of total)")
    print(f"  Responded:        {responded}  ({responded/max(connected,1)*100:.1f}% of connected)")
    print(f"  Interested:       {interested}  ({interested/max(responded,1)*100:.1f}% of responded)")
    print(f"  Purchased:        {purchased}  (${purchased * 299} revenue @ $299)")

    print(f"\n{'='*60}\n")


def export_hot(output_path: str):
    """Export high-priority prospects ready for outreach."""
    prospects = load_prospects()
    hot = [
        p for p in prospects
        if p.get("priority") == "high"
        and p.get("status") in ["new", "connected"]
    ]

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=hot[0].keys() if hot else ["name", "title", "company", "url"])
        writer.writeheader()
        writer.writerows(hot)

    print(f"✅ Exported {len(hot)} hot prospects to: {output_path}")


def delete_prospect(url_or_name: str):
    """Remove a prospect from the database."""
    prospects = load_prospects()
    original_count = len(prospects)
    prospects = [
        p for p in prospects
        if not (p.get("url") == normalize_url(url_or_name) or p.get("name") == url_or_name)
    ]

    if len(prospects) < original_count:
        save_prospects(prospects)
        print(f"✅ Deleted prospect: {url_or_name}")
    else:
        print(f"❌ Prospect not found: {url_or_name}")


def main():
    parser = argparse.ArgumentParser(
        description="Q-Mol LinkedIn Prospect Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python linkedin_prospect_manager.py add "Jane Smith" "Scientist" "BioTech" "linkedin.com/in/janes"
  python linkedin_prospect_manager.py import leads.csv
  python linkedin_prospect_manager.py list --status new
  python linkedin_prospect_manager.py update "linkedin.com/in/janes" --status connected
  python linkedin_prospect_manager.py stats
        """,
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Add
    add_parser = subparsers.add_parser("add", help="Add a single prospect")
    add_parser.add_argument("name")
    add_parser.add_argument("title")
    add_parser.add_argument("company")
    add_parser.add_argument("url")
    add_parser.add_argument("--location", default="")
    add_parser.add_argument("--notes", default="")

    # Import
    import_parser = subparsers.add_parser("import", help="Import from CSV")
    import_parser.add_argument("filepath")

    # List
    list_parser = subparsers.add_parser("list", help="List prospects")
    list_parser.add_argument("--status", choices=VALID_STATUSES, help="Filter by status")
    list_parser.add_argument("--limit", type=int, default=50)

    # Update
    update_parser = subparsers.add_parser("update", help="Update prospect status")
    update_parser.add_argument("url_or_name")
    update_parser.add_argument("--status", required=True, choices=VALID_STATUSES)
    update_parser.add_argument("--notes", default="")

    # Generate messages
    subparsers.add_parser("generate-messages", help="Generate personalized messages")

    # Stats
    subparsers.add_parser("stats", help="Show pipeline statistics")

    # Export hot
    hot_parser = subparsers.add_parser("export-hot", help="Export high-priority prospects")
    hot_parser.add_argument("--output", default="hot_prospects.csv")

    # Delete
    del_parser = subparsers.add_parser("delete", help="Delete a prospect")
    del_parser.add_argument("url_or_name")

    args = parser.parse_args()
    ensure_dirs()

    if args.command == "add":
        add_prospect(args.name, args.title, args.company, args.url, args.location, args.notes)
    elif args.command == "import":
        import_csv(args.filepath)
    elif args.command == "list":
        list_prospects(args.status, args.limit)
    elif args.command == "update":
        update_status(args.url_or_name, args.status, args.notes)
    elif args.command == "generate-messages":
        generate_messages()
    elif args.command == "stats":
        show_stats()
    elif args.command == "export-hot":
        export_hot(args.output)
    elif args.command == "delete":
        delete_prospect(args.url_or_name)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
