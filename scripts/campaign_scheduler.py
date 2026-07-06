"""
Campaign Scheduler for Q-Mol LinkedIn Outreach
Can be called by cron or Windows Task Scheduler to run daily campaigns.
"""
import sys
import os
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "linkedin"))

from campaign_manager import CampaignManager
from safety_config import OutreachTracker, check_operating_hours


def run_scheduled_campaign():
    """
    Run a conservative daily campaign.
    Designed to be called once per day (e.g., via cron at 10:00 AM).
    """
    if not check_operating_hours():
        print("[Q-MOL SCHEDULER] Outside operating hours. Exiting.")
        return

    tracker = OutreachTracker()
    stats = tracker.get_stats()

    # If we've already hit limits today, skip
    if stats["today_total"] >= 20:
        print("[Q-MOL SCHEDULER] Daily limits already reached. Exiting.")
        return

    # Determine how many messages to send today
    remaining_msgs = stats["remaining_messages"]
    remaining_conns = stats["remaining_connections"]

    if remaining_msgs <= 0 and remaining_conns <= 0:
        print("[Q-MOL SCHEDULER] No remaining quota. Exiting.")
        return

    # Randomize batch size (don't always send max - looks suspicious)
    batch_msgs = random.randint(1, min(remaining_msgs, 5))
    batch_conns = random.randint(1, min(remaining_conns, 3))

    print(f"[Q-MOL SCHEDULER] Today: {batch_msgs} messages, {batch_conns} connections")

    cm = CampaignManager(tracker=tracker)
    from targets import get_targets_by_priority
    targets = get_targets_by_priority(min_priority=1)

    results = cm.run_campaign(
        targets=targets,
        max_messages=batch_msgs,
        max_connections=batch_conns,
        dry_run=False,
    )

    print(f"[Q-MOL SCHEDULER] Done: {results['messages_sent']} msgs, {results['connections_sent']} conns")


if __name__ == "__main__":
    run_scheduled_campaign()
