"""
Q-Mol LinkedIn Outreach — Main Runner Script
USAGE:
    python run_linkedin_outreach.py --dry-run          # Preview messages
    python run_linkedin_outreach.py --campaign         # Run full campaign
    python run_linkedin_outreach.py --message "URL" "Name" --type researcher --topic "computational chemistry"
    python run_linkedin_outreach.py --connect "URL" "Name" --type pharma --topic "AI drug discovery"
    python run_linkedin_outreach.py --stats            # Show outreach statistics
    python run_linkedin_outreach.py --follow-up "URL" "Name"  # Send follow-up
"""
import sys
import os

# Ensure linkedin/ modules are importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "linkedin"))

from campaign_manager import CampaignManager
from safety_config import OutreachTracker
from message_templates import generate_follow_up
from linkedin_messenger import LinkedInMessenger
from targets import TARGETS, get_targets_by_priority


def show_stats():
    tracker = OutreachTracker()
    stats = tracker.get_stats()
    print("\n" + "=" * 50)
    print("Q-MOL LINKEDIN OUTREACH STATISTICS")
    print("=" * 50)
    print(f"Total messages sent (all time):  {stats['total_sent']}")
    print(f"Total failed:                     {stats['total_failed']}")
    print(f"Unique contacts reached:          {stats['unique_contacts']}")
    print(f"Today messages:                   {stats['today_messages']} / {stats['today_messages'] + stats['remaining_messages']}")
    print(f"Today connections:                {stats['today_connections']} / {stats['today_connections'] + stats['remaining_connections']}")
    print(f"Remaining messages today:         {stats['remaining_messages']}")
    print(f"Remaining connections today:      {stats['remaining_connections']}")
    print("=" * 50)


def main():
    args = sys.argv[1:]

    if not args:
        print(__doc__)
        sys.exit(0)

    tracker = OutreachTracker()
    cm = CampaignManager(tracker=tracker)

    if args[0] == "--stats":
        show_stats()
        return

    if args[0] == "--dry-run":
        print("[Q-MOL] Running DRY RUN campaign...")
        targets = get_targets_by_priority(min_priority=1)
        results = cm.run_dry_run(targets=targets)
        print(f"\nDry-run complete. Would send {results['messages_sent']} messages.")
        return

    if args[0] == "--campaign":
        print("[Q-MOL] Starting LIVE outreach campaign...")
        targets = get_targets_by_priority(min_priority=1)
        results = cm.run_campaign(targets=targets, dry_run=False)
        print(f"\nCampaign complete: {results['messages_sent']} messages, {results['connections_sent']} connections.")
        return

    if args[0] == "--message" and len(args) >= 3:
        url = args[1]
        name = args[2]
        target_type = "general"
        topic = "drug discovery"
        company = None
        i = 3
        while i < len(args):
            if args[i] == "--type" and i + 1 < len(args):
                target_type = args[i + 1]
                i += 2
            elif args[i] == "--topic" and i + 1 < len(args):
                topic = args[i + 1]
                i += 2
            elif args[i] == "--company" and i + 1 < len(args):
                company = args[i + 1]
                i += 2
            else:
                i += 1

        result = cm.send_single_message(url, name, target_type, topic, company)
        print(f"Result: {result['status']}")
        if result.get("error"):
            print(f"Error: {result['error']}")
        return

    if args[0] == "--connect" and len(args) >= 3:
        url = args[1]
        name = args[2]
        target_type = "general"
        topic = "drug discovery"
        company = None
        i = 3
        while i < len(args):
            if args[i] == "--type" and i + 1 < len(args):
                target_type = args[i + 1]
                i += 2
            elif args[i] == "--topic" and i + 1 < len(args):
                topic = args[i + 1]
                i += 2
            elif args[i] == "--company" and i + 1 < len(args):
                company = args[i + 1]
                i += 2
            else:
                i += 1

        result = cm.send_single_connection(url, name, target_type, topic, company)
        print(f"Result: {result['status']}")
        if result.get("error"):
            print(f"Error: {result['error']}")
        return

    if args[0] == "--follow-up" and len(args) >= 3:
        url = args[1]
        name = args[2]
        msg = generate_follow_up(name, days_since_first=7)
        print(f"[Q-MOL] Follow-up message for {name}:\n{'-'*40}\n{msg}\n{'-'*40}")
        # Optionally send via messenger
        messenger = LinkedInMessenger(tracker=tracker)
        result = messenger.send_message(url, name, "general", "drug discovery")
        print(f"Result: {result['status']}")
        return

    print("Unknown command. Usage:")
    print(__doc__)


if __name__ == "__main__":
    main()
