#!/usr/bin/env python3
"""
Q-Mol Safety Guard — Rate Limit Enforcer for LinkedIn Automation
Prevents account bans by enforcing strict daily limits and business-hour rules.

Usage:
    python safety_guard.py --status
    python safety_guard.py --action connect --prospect "John Doe" --dry-run
    python safety_guard.py --action connect --prospect "John Doe"
    python safety_guard.py --action message --prospect "Jane Smith"
    python safety_guard.py --stop
    python safety_guard.py --resume
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# ─── Configuration ───────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR / "data" / "linkedin"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Log files
LOG_FILE = DATA_DIR / "safety_guard_log.json"
DAILY_COUNT_FILE = DATA_DIR / "daily_counts.json"
STOP_FILE = SCRIPT_DIR / "STOP.txt"

# Hard limits (absolute maximum — never exceed)
HARD_LIMITS = {
    "connection": 15,
    "message": 25,
    "profile_view": 50,
    "post_engagement": 20,
}

# Soft limits (recommended for long-term safety)
SOFT_LIMITS = {
    "connection": 12,
    "message": 20,
    "profile_view": 30,
    "post_engagement": 15,
}

# Minimum delays between actions (seconds)
MIN_DELAYS = {
    "connection": 120,
    "message": 90,
    "profile_view": 30,
    "post_engagement": 60,
    "search": 10,
    "snapshot": 3,
}

# Business hours (Pacific Time — adjust if needed)
BUSINESS_HOURS = {"start": 9, "end": 18}
WEEKEND_DAYS = [5, 6]  # Saturday, Sunday

# Cooldown after hitting soft limit (hours)
COOLDOWN_HOURS = 24


def get_today_str():
    return datetime.now().strftime("%Y-%m-%d")


def load_daily_counts():
    """Load today's action counts."""
    if not DAILY_COUNT_FILE.exists():
        return {}
    with open(DAILY_COUNT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Only return today's data
    today = get_today_str()
    return data.get(today, {})


def save_daily_count(action_type):
    """Increment and save daily count for an action."""
    today = get_today_str()
    data = {}
    if DAILY_COUNT_FILE.exists():
        with open(DAILY_COUNT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    if today not in data:
        data[today] = {}
    if action_type not in data[today]:
        data[today][action_type] = 0
    data[today][action_type] += 1
    with open(DAILY_COUNT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_log():
    """Load the safety guard log."""
    if not LOG_FILE.exists():
        return {"actions": [], "violations": [], "stops": []}
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_log(log):
    """Save the safety guard log."""
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)


def log_action(log, action_type, prospect, result, details=""):
    """Log an action to the safety guard log."""
    log["actions"].append({
        "timestamp": datetime.now().isoformat(),
        "action_type": action_type,
        "prospect": prospect,
        "result": result,
        "details": details,
    })
    save_log(log)


def check_stop():
    """Check if emergency STOP file exists."""
    if STOP_FILE.exists():
        print("🛑 EMERGENCY STOP FILE IS ACTIVE.")
        print(f"   File: {STOP_FILE}")
        print("   Remove this file to resume automation.")
        return True
    return False


def create_stop():
    """Create emergency STOP file."""
    STOP_FILE.write_text("EMERGENCY STOP\nCreated: " + datetime.now().isoformat())
    print("🛑 EMERGENCY STOP FILE CREATED.")
    print(f"   Location: {STOP_FILE}")
    print("   All automation scripts will halt.")


def remove_stop():
    """Remove emergency STOP file."""
    if STOP_FILE.exists():
        STOP_FILE.unlink()
        print("✅ Emergency STOP file removed. Automation can resume.")
    else:
        print("ℹ️  No STOP file found.")


def check_business_hours():
    """Check if current time is within business hours."""
    now = datetime.now()
    weekday = now.weekday()
    hour = now.hour

    is_weekend = weekday in WEEKEND_DAYS
    in_hours = BUSINESS_HOURS["start"] <= hour <= BUSINESS_HOURS["end"]

    warnings = []
    if is_weekend:
        warnings.append("It's the weekend. LinkedIn automation on weekends is risky.")
    if not in_hours:
        warnings.append(f"Current time ({hour}:00) is outside business hours ({BUSINESS_HOURS['start']}-{BUSINESS_HOURS['end']}).")

    return len(warnings) == 0, warnings


def check_rate_limit(action_type, use_soft_limits=True):
    """
    Check if an action is allowed under current rate limits.
    Returns (allowed: bool, reason: str, current_count: int, limit: int)
    """
    counts = load_daily_counts()
    current = counts.get(action_type, 0)
    limits = SOFT_LIMITS if use_soft_limits else HARD_LIMITS
    limit = limits.get(action_type, 999)

    if current >= HARD_LIMITS.get(action_type, 999):
        return False, f"HARD LIMIT REACHED: {current}/{HARD_LIMITS[action_type]} {action_type}s today", current, HARD_LIMITS[action_type]

    if use_soft_limits and current >= SOFT_LIMITS.get(action_type, 999):
        return False, f"SOFT LIMIT REACHED: {current}/{SOFT_LIMITS[action_type]} {action_type}s today. Wait {COOLDOWN_HOURS}h or use --force-hard-limit", current, SOFT_LIMITS[action_type]

    return True, "OK", current, limit


def enforce_delay(action_type):
    """Enforce minimum delay for an action type."""
    delay = MIN_DELAYS.get(action_type, 60)
    print(f"⏱️  Enforcing {delay}s delay...")
    time.sleep(delay)


def print_status():
    """Print current safety status."""
    counts = load_daily_counts()
    today = get_today_str()
    ok, warnings = check_business_hours()
    stopped = check_stop()

    print("\n" + "=" * 60)
    print("Q-MOL SAFETY GUARD STATUS")
    print("=" * 60)
    print(f"\n📅 Today: {today}")
    print(f"🕐 Time: {datetime.now().strftime('%H:%M:%S')}")
    print(f"🛑 Emergency Stop: {'ACTIVE' if stopped else 'Not active'}")
    print(f"\n📊 Daily Counts:")
    print(f"   {'Action':<20} {'Today':>6} {'Soft':>6} {'Hard':>6} {'Status':>10}")
    print(f"   {'-'*56}")
    for action in HARD_LIMITS:
        current = counts.get(action, 0)
        soft = SOFT_LIMITS[action]
        hard = HARD_LIMITS[action]
        if current >= hard:
            status = "🚫 HARD"
        elif current >= soft:
            status = "⚠️  SOFT"
        else:
            status = "✅ OK"
        print(f"   {action:<20} {current:>6} {soft:>6} {hard:>6} {status:>10}")

    print(f"\n⏱️  Minimum Delays:")
    for action, delay in MIN_DELAYS.items():
        print(f"   {action:<20} {delay}s")

    print(f"\n🕐 Business Hours: {BUSINESS_HOURS['start']}:00–{BUSINESS_HOURS['end']}:00 PDT")
    if not ok:
        print(f"\n⚠️  WARNINGS:")
        for w in warnings:
            print(f"   - {w}")
    else:
        print(f"\n✅ Within business hours.")

    print("=" * 60 + "\n")


def guard_action(action_type, prospect="", dry_run=False, force_hard_limit=False):
    """
    Main guard function. Call this before ANY LinkedIn action.
    Returns True if action is allowed, False if blocked.
    """
    print(f"\n🛡️  SAFETY GUARD CHECK: {action_type}")
    print(f"   Prospect: {prospect or 'N/A'}")
    print(f"   Dry run: {dry_run}")

    # Check STOP file
    if check_stop():
        return False

    # Check business hours (warn but don't block unless strict mode)
    ok, warnings = check_business_hours()
    if not ok:
        for w in warnings:
            print(f"   ⚠️  {w}")

    # Check rate limits
    use_soft = not force_hard_limit
    allowed, reason, current, limit = check_rate_limit(action_type, use_soft)
    print(f"   Count: {current}/{limit}")

    if not allowed:
        print(f"   🚫 BLOCKED: {reason}")
        log = load_log()
        log["violations"].append({
            "timestamp": datetime.now().isoformat(),
            "action_type": action_type,
            "prospect": prospect,
            "reason": reason,
        })
        save_log(log)
        return False

    print(f"   ✅ ALLOWED: {reason}")

    if dry_run:
        print(f"   [DRY-RUN] Would execute {action_type}")
        return True

    # Enforce delay
    enforce_delay(action_type)

    # Record the action
    save_daily_count(action_type)
    log = load_log()
    log_action(log, action_type, prospect, "allowed")

    return True


def main():
    parser = argparse.ArgumentParser(description="Q-Mol Safety Guard")
    parser.add_argument("--action", choices=[
        "status", "connect", "message", "profile_view", "post_engagement",
        "stop", "resume", "check"
    ], default="status")
    parser.add_argument("--prospect", default="", help="Prospect name")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without acting")
    parser.add_argument("--force-hard-limit", action="store_true", help="Use hard limits instead of soft")

    args = parser.parse_args()

    if args.action == "status":
        print_status()

    elif args.action == "stop":
        create_stop()

    elif args.action == "resume":
        remove_stop()

    elif args.action == "check":
        # Just run a general check
        print_status()
        if check_stop():
            sys.exit(1)
        ok, warnings = check_business_hours()
        if not ok:
            print("\n⚠️  Outside business hours. Proceed with caution.")

    elif args.action in ("connect", "message", "profile_view", "post_engagement"):
        allowed = guard_action(args.action, args.prospect, args.dry_run, args.force_hard_limit)
        sys.exit(0 if allowed else 1)


if __name__ == "__main__":
    main()
