"""
Utility to check and display Q-Mol LinkedIn outreach statistics.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "linkedin"))

from safety_config import OutreachTracker


def main():
    tracker = OutreachTracker()
    stats = tracker.get_stats()

    print("\n+" + "-" * 56 + "+")
    print("|" + " Q-MOL LINKEDIN OUTREACH STATISTICS ".center(56) + "|")
    print("+" + "-" * 56 + "+")
    print(f"|  Total messages sent (all time):  {str(stats['total_sent']).rjust(24)}  |")
    print(f"|  Total failed:                     {str(stats['total_failed']).rjust(24)}  |")
    print(f"|  Unique contacts reached:          {str(stats['unique_contacts']).rjust(24)}  |")
    print("+" + "-" * 56 + "+")
    print(f"|  TODAY -- Messages:  {str(stats['today_messages']).rjust(4)}/{str(stats['today_messages'] + stats['remaining_messages']).ljust(4)}  |  Connections: {str(stats['today_connections']).rjust(3)}/{str(stats['today_connections'] + stats['remaining_connections']).ljust(3)}  |")
    print(f"|  Remaining today -- Messages: {str(stats['remaining_messages']).rjust(3)}  |  Connections: {str(stats['remaining_connections']).rjust(3)}  |")
    print("+" + "-" * 56 + "+")

    # Show last 10 contacts
    records = tracker.records[-10:] if len(tracker.records) >= 10 else tracker.records
    if records:
        print("\n  Recent activity:")
        print("  " + "-" * 54)
        for r in reversed(records):
            ts = r["timestamp"][:19]
            status = "OK" if r["status"] == "sent" else "FAIL"
            print(f"  {status} [{ts}] {r['action']:12} | {r['name'][:35]:35}")
        print("  " + "-" * 54)


if __name__ == "__main__":
    main()
