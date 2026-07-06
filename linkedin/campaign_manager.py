"""
Campaign Manager for Q-Mol LinkedIn Outreach
Orchestrates safe, sequential outreach with full logging.
"""
import time
import random
import sys
from typing import List, Dict, Optional
from datetime import datetime

from linkedin_messenger import LinkedInMessenger
from safety_config import OutreachTracker, check_operating_hours, MAX_DAILY_MESSAGES, MAX_DAILY_CONNECTIONS
from targets import TARGETS, get_targets_by_priority


class CampaignManager:
    """
    Manages a Q-Mol outreach campaign with strict safety controls.
    """

    def __init__(self, tracker: Optional[OutreachTracker] = None):
        self.messenger = LinkedInMessenger(tracker=tracker)
        self.tracker = tracker or OutreachTracker()

    def run_campaign(
        self,
        targets: Optional[List[Dict]] = None,
        max_messages: int = MAX_DAILY_MESSAGES,
        max_connections: int = MAX_DAILY_CONNECTIONS,
        dry_run: bool = False,
    ) -> Dict[str, any]:
        """
        Run a single campaign session.

        Args:
            targets: List of target dicts. Defaults to priority 1 targets.
            max_messages: Max messages to send this session.
            max_connections: Max connection requests this session.
            dry_run: If True, only generate messages without sending.

        Returns:
            Campaign report dict.
        """
        if not dry_run and not check_operating_hours():
            return {
                "status": "skipped",
                "reason": "Outside operating hours (9 AM - 6 PM, weekdays only).",
                "timestamp": datetime.now().isoformat(),
                "messages_sent": 0,
                "connections_sent": 0,
                "failed": 0,
                "skipped": 0,
            }

        targets = targets or get_targets_by_priority(min_priority=1)
        if not targets:
            return {"status": "error", "reason": "No targets provided."}

        results = {
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "dry_run": dry_run,
            "messages_sent": 0,
            "connections_sent": 0,
            "failed": 0,
            "skipped": 0,
            "details": [],
        }

        print("=" * 60)
        print("Q-MOL LINKEDIN OUTREACH CAMPAIGN")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
        print(f"Targets: {len(targets)}")
        print("=" * 60)

        for target in targets:
            # Check limits
            stats = self.tracker.get_today_count()
            if stats["message"] >= max_messages and stats["connection"] >= max_connections:
                print("[Q-MOL] All daily limits reached. Stopping campaign.")
                results["status"] = "paused_limits"
                break

            url = target["linkedin_url"]
            name = target["name"]
            target_type = target.get("target_type", "general")
            topic = target.get("topic", "drug discovery")
            company = target.get("company")

            # Skip already contacted
            if self.tracker.was_contacted(url, days=14):
                print(f"[Q-MOL] SKIP: Already contacted {name} recently.")
                results["skipped"] += 1
                continue

            print(f"\n[Q-MOL] Processing: {name} ({target_type}, {topic})")

            if dry_run:
                from message_templates import generate_message
                msg = generate_message(name=name, target_type=target_type, topic=topic, company=company)
                print(f"[Q-MOL] DRY RUN - would send:\n{'-'*40}\n{msg}\n{'-'*40}")
                results["messages_sent"] += 1
                continue

            # Attempt to send message (if already connected)
            result = self.messenger.send_message(
                profile_url=url,
                name=name,
                target_type=target_type,
                topic=topic,
                company=company,
            )

            if result["status"] == "sent":
                results["messages_sent"] += 1
                print(f"[Q-MOL] SUCCESS: Message sent to {name}")
            elif "not be connected" in (result.get("error") or ""):
                # Try connection request instead
                print(f"[Q-MOL] Not connected to {name}, trying connection request...")
                conn_result = self.messenger.send_connection_request(
                    profile_url=url,
                    name=name,
                    target_type=target_type,
                    topic=topic,
                    company=company,
                )
                if conn_result["status"] == "sent":
                    results["connections_sent"] += 1
                    print(f"[Q-MOL] SUCCESS: Connection request sent to {name}")
                else:
                    results["failed"] += 1
                    print(f"[Q-MOL] FAILED: {conn_result.get('error')}")
            else:
                results["failed"] += 1
                print(f"[Q-MOL] FAILED: {result.get('error')}")

            results["details"].append({
                "name": name,
                "url": url,
                "result": result,
            })

            # Human-like delay between targets
            delay = random.uniform(60, 180)
            print(f"[Q-MOL] Waiting {delay:.0f}s before next target...")
            time.sleep(delay)

        # Final stats
        final_stats = self.messenger.get_stats()
        results["stats"] = final_stats

        print("\n" + "=" * 60)
        print("CAMPAIGN COMPLETE")
        print(f"Messages sent: {results['messages_sent']}")
        print(f"Connections sent: {results['connections_sent']}")
        print(f"Failed: {results['failed']}")
        print(f"Skipped: {results['skipped']}")
        print(f"Total sent (all time): {final_stats['total_sent']}")
        print(f"Unique contacts: {final_stats['unique_contacts']}")
        print("=" * 60)

        return results

    def run_dry_run(self, targets: Optional[List[Dict]] = None) -> Dict[str, any]:
        """Run a dry-run campaign to preview messages without sending."""
        return self.run_campaign(targets=targets, dry_run=True)

    def send_single_message(self, profile_url: str, name: str, target_type: str = "general", topic: str = "drug discovery", company: Optional[str] = None) -> Dict:
        """Send a single message with full safety checks."""
        return self.messenger.send_message(
            profile_url=profile_url,
            name=name,
            target_type=target_type,
            topic=topic,
            company=company,
        )

    def send_single_connection(self, profile_url: str, name: str, target_type: str = "general", topic: str = "drug discovery", company: Optional[str] = None) -> Dict:
        """Send a single connection request with full safety checks."""
        return self.messenger.send_connection_request(
            profile_url=profile_url,
            name=name,
            target_type=target_type,
            topic=topic,
            company=company,
        )
