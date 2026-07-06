"""
Safety & Rate Limiting Configuration for LinkedIn Automation
These settings are CONSERVATIVE by design to protect the user's account.
"""
import json
import os
from datetime import datetime, date
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

# ─── Hard Limits (LinkedIn Safety) ───────────────────────────────────────────
# LinkedIn is aggressive about detecting automation. These limits are deliberately
# conservative. Violating them risks account restriction or ban.

MAX_DAILY_MESSAGES = 12          # Direct messages per day (conservative)
MAX_DAILY_CONNECTIONS = 8        # Connection requests per day (conservative)
MAX_DAILY_TOTAL_ACTIONS = 20     # Combined limit

MIN_DELAY_BETWEEN_ACTIONS = 45   # seconds
MAX_DELAY_BETWEEN_ACTIONS = 180  # seconds (3 minutes)

MIN_MESSAGE_COOLDOWN_MINUTES = 3  # minimum minutes between messages
MAX_MESSAGE_COOLDOWN_MINUTES = 8  # maximum minutes between messages

# Time windows (only operate during human hours)
OPERATING_HOURS_START = 9   # 9 AM local time
OPERATING_HOURS_END = 18    # 6 PM local time

# Days to avoid (weekends = less activity = more suspicious)
AVOID_WEEKENDS = True

# ─── Tracking Database ───────────────────────────────────────────────────────
LOG_FILE = os.path.join(os.path.dirname(__file__), "outreach_log.json")


@dataclass
class OutreachRecord:
    timestamp: str
    action: str          # "message" | "connection" | "view"
    linkedin_url: str
    name: str
    message_sent: str
    target_type: str
    topic: str
    status: str          # "sent" | "failed" | "pending"
    error: Optional[str] = None


class OutreachTracker:
    """Track all outreach to prevent double-sending and respect limits."""

    def __init__(self, log_file: str = LOG_FILE):
        self.log_file = log_file
        self.records: List[Dict] = self._load()

    def _load(self) -> List[Dict]:
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []

    def save(self):
        with open(self.log_file, "w", encoding="utf-8") as f:
            json.dump(self.records, f, indent=2, ensure_ascii=False)

    def add(self, record: OutreachRecord):
        self.records.append(asdict(record))
        self.save()

    def get_today_count(self) -> Dict[str, int]:
        today = date.today().isoformat()
        counts = {"message": 0, "connection": 0, "total": 0}
        for r in self.records:
            if r["timestamp"].startswith(today) and r["status"] == "sent":
                action = r.get("action", "")
                if action in counts:
                    counts[action] += 1
                counts["total"] += 1
        return counts

    def was_contacted(self, linkedin_url: str, days: int = 30) -> bool:
        """Check if we already contacted this person within N days."""
        cutoff = datetime.now().timestamp() - (days * 86400)
        for r in self.records:
            if r["linkedin_url"] == linkedin_url:
                ts = datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00"))
                if ts.timestamp() > cutoff:
                    return True
        return False

    def get_contact_history(self, linkedin_url: str) -> List[Dict]:
        return [r for r in self.records if r["linkedin_url"] == linkedin_url]

    def can_send_message(self) -> bool:
        counts = self.get_today_count()
        return counts["message"] < MAX_DAILY_MESSAGES

    def can_send_connection(self) -> bool:
        counts = self.get_today_count()
        return counts["connection"] < MAX_DAILY_CONNECTIONS

    def get_stats(self) -> Dict:
        total_sent = len([r for r in self.records if r["status"] == "sent"])
        total_failed = len([r for r in self.records if r["status"] == "failed"])
        unique_contacts = len(set(r["linkedin_url"] for r in self.records))
        today = self.get_today_count()
        return {
            "total_sent": total_sent,
            "total_failed": total_failed,
            "unique_contacts": unique_contacts,
            "today_messages": today["message"],
            "today_connections": today["connection"],
            "today_total": today["total"],
            "remaining_messages": MAX_DAILY_MESSAGES - today["message"],
            "remaining_connections": MAX_DAILY_CONNECTIONS - today["connection"],
        }


def check_operating_hours() -> bool:
    """Ensure we're only operating during reasonable human hours."""
    now = datetime.now()
    if AVOID_WEEKENDS and now.weekday() >= 5:
        return False
    if not (OPERATING_HOURS_START <= now.hour < OPERATING_HOURS_END):
        return False
    return True
