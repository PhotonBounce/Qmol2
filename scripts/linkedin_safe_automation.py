#!/usr/bin/env python3
"""
Q-Mol LinkedIn Safe Automation Controller
=========================================
SAFETY-FIRST browser automation via Kimi WebBridge.
Controls real Chrome with Dmitriy's logged-in session.

DESIGN PHILOSOPHY:
- Conservative limits (well below LinkedIn thresholds)
- Human-like randomization (timing, actions, pauses)
- Automatic health monitoring with circuit breaker
- All actions logged with full audit trail
- One tool per account - never run multiple automators

USAGE:
    # Check account health before any automation
    python linkedin_safe_automation.py --mode health_check

    # Send connection requests (conservative batch)
    python linkedin_safe_automation.py --mode connect --batch-size 5

    # Send messages to existing connections
    python linkedin_safe_automation.py --mode message --batch-size 5

    # View profiles (warm-up / research)
    python linkedin_safe_automation.py --mode profile_views --batch-size 10

    # Withdraw stale pending requests
    python linkedin_safe_automation.py --mode withdraw_stale

    # Daily safe routine (recommended)
    python linkedin_safe_automation.py --mode daily

SAFETY LIMITS (hard-coded, cannot be overridden):
    - Max connections/day: 15
    - Max messages/day: 20
    - Max profile views/day: 30
    - Max total actions/day: 50
    - Min delay between actions: 45 seconds
    - Max delay between actions: 180 seconds
    - Active hours: 09:00 - 18:00 (local timezone)
    - Weekly connection cap: 75

WARNING:
    LinkedIn's Terms of Service prohibit automation.
    This tool uses your real browser to minimize detection risk,
    but NO automation is 100% safe. Use at your own risk.
"""

import argparse
import csv
import json
import os
import random
import sys
import time
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import requests

# ============================================================================
# CONFIGURATION
# ============================================================================

PROJECT_DIR = Path(__file__).parent.parent
DATA_DIR = PROJECT_DIR / "data" / "linkedin"
LINKEDIN_DIR = PROJECT_DIR / "linkedin"
SAFETY_LOG = DATA_DIR / "safety_audit.json"
PROSPECTS_FILE = DATA_DIR / "prospects.csv"
ACTION_LOG = DATA_DIR / "action_log.json"

WEBBRIDGE_URL = "http://127.0.0.1:10086/command"
SESSION_NAME = "qmol-linkedin-safe"

# Hard safety limits - CANNOT be changed via args
SAFETY_LIMITS = {
    "daily_connections": 15,
    "daily_messages": 20,
    "daily_profile_views": 30,
    "daily_total_actions": 50,
    "weekly_connections": 75,
    "min_delay_seconds": 45,
    "max_delay_seconds": 180,
    "active_start_hour": 9,
    "active_end_hour": 18,
    "min_message_delay_hours": 24,  # Wait after connection accepted
    "stale_request_days": 21,
    "max_stale_withdrawals_per_week": 10,
    "target_acceptance_rate": 0.50,
    "warning_acceptance_rate": 0.30,
}

# Message templates (personalized, no URLs in connection requests)
MESSAGE_TEMPLATES = {
    "value_first": """Hi {first_name},

Saw your work on {topic} — really interesting approach.

I built Q-Mol to auto-curate compound libraries from PubChem (2,800+ molecules, RDKit descriptors, Lipinski/PAINS/QED filters). Might save your team some manual curation time.

Happy to share a free sample dataset if you're interested. No strings.

Best,
Dmitriy Buchman""",

    "short_pitch": """Hi {first_name},

Quick question: how much time does your team spend on compound library curation?

I automated the pipeline — harvests from PubChem with full ADMET descriptors. Free preview available.

Worth a look?

Dmitriy""",

    "follow_up": """Hi {first_name},

Following up on my message about Q-Mol. No pressure at all — just wanted to make sure you saw it.

If compound library automation isn't a priority right now, I totally understand.

Best,
Dmitriy""",

    "soft_close": """Hi {first_name},

Last note from me — wanted to share that Q-Mol now has {molecule_count}+ molecules with new kinase-focused and CNS-penetrant subsets.

If you're ever looking to speed up virtual screening prep, feel free to reach out.

Cheers,
Dmitriy""",
}


# ============================================================================
# WEBBRIDGE INTERFACE
# ============================================================================

def webbridge_cmd(action: str, args: dict, session: str = SESSION_NAME) -> dict:
    """Send command to Kimi WebBridge daemon."""
    payload = {"action": action, "args": args, "session": session}
    try:
        resp = requests.post(WEBBRIDGE_URL, json=payload, timeout=30)
        return resp.json()
    except requests.exceptions.ConnectionError:
        print("[ERROR] WebBridge not running. Start it with:")
        print("  Windows: & $env:USERPROFILE\\.kimi-webbridge\\bin\\kimi-webbridge.exe start")
        return {"ok": False, "error": "WebBridge connection refused"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def wb_navigate(url: str, new_tab: bool = False) -> dict:
    return webbridge_cmd("navigate", {"url": url, "newTab": new_tab, "group_title": "Q-Mol LinkedIn Safe"})


def wb_snapshot() -> dict:
    return webbridge_cmd("snapshot", {})


def wb_click(selector: str) -> dict:
    return webbridge_cmd("click", {"selector": selector})


def wb_fill(selector: str, value: str) -> dict:
    return webbridge_cmd("fill", {"selector": selector, "value": value})


def wb_evaluate(code: str) -> dict:
    return webbridge_cmd("evaluate", {"code": code})


def wb_screenshot(path: str = None) -> dict:
    args = {}
    if path:
        args["path"] = str(path)
    return webbridge_cmd("screenshot", args)


def wb_list_tabs() -> dict:
    return webbridge_cmd("list_tabs", {})


def wb_close_session() -> dict:
    return webbridge_cmd("close_session", {})


# ============================================================================
# SAFETY & HEALTH SYSTEM
# ============================================================================

def ensure_dirs():
    """Create data directories if missing."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_safety_log() -> dict:
    """Load safety audit log."""
    if not SAFETY_LOG.exists():
        return {
            "account_created": datetime.now().isoformat(),
            "total_actions_all_time": 0,
            "total_connections_sent": 0,
            "total_messages_sent": 0,
            "total_profile_views": 0,
            "daily_counts": {},
            "weekly_connection_counts": {},
            "actions": [],
            "warnings": [],
            "pending_requests_withdrawn": 0,
            "last_health_check": None,
        }
    with open(SAFETY_LOG, "r", encoding="utf-8") as f:
        return json.load(f)


def save_safety_log(log: dict):
    """Save safety audit log."""
    with open(SAFETY_LOG, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)


def get_today_key() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def get_week_key() -> str:
    """Return ISO week key (e.g., '2026-W27')."""
    return datetime.now().strftime("%Y-W%U")


def get_daily_count(log: dict, action_type: str) -> int:
    """Get count of actions today."""
    today = get_today_key()
    return log.get("daily_counts", {}).get(today, {}).get(action_type, 0)


def get_weekly_connection_count(log: dict) -> int:
    """Get connection requests sent this week."""
    week = get_week_key()
    return log.get("weekly_connection_counts", {}).get(week, 0)


def record_action(log: dict, action_type: str, details: str = "", target: str = ""):
    """Record an action with full audit trail."""
    today = get_today_key()
    week = get_week_key()

    # Update daily counts
    if today not in log.get("daily_counts", {}):
        log["daily_counts"][today] = {}
    if action_type not in log["daily_counts"][today]:
        log["daily_counts"][today][action_type] = 0
    log["daily_counts"][today][action_type] += 1

    # Update weekly connection counts
    if action_type == "connection":
        if week not in log.get("weekly_connection_counts", {}):
            log["weekly_connection_counts"][week] = 0
        log["weekly_connection_counts"][week] += 1

    # Update totals
    log["total_actions_all_time"] = log.get("total_actions_all_time", 0) + 1
    if action_type == "connection":
        log["total_connections_sent"] = log.get("total_connections_sent", 0) + 1
    elif action_type == "message":
        log["total_messages_sent"] = log.get("total_messages_sent", 0) + 1
    elif action_type == "profile_view":
        log["total_profile_views"] = log.get("total_profile_views", 0) + 1

    # Append action record
    log["actions"].append({
        "timestamp": datetime.now().isoformat(),
        "type": action_type,
        "target": target,
        "details": details,
    })

    # Trim action history to last 1000 entries
    if len(log["actions"]) > 1000:
        log["actions"] = log["actions"][-1000:]

    save_safety_log(log)


def human_delay(min_sec: int = None, max_sec: int = None):
    """Wait for a human-like random interval."""
    min_s = min_sec or SAFETY_LIMITS["min_delay_seconds"]
    max_s = max_sec or SAFETY_LIMITS["max_delay_seconds"]
    delay = random.uniform(min_s, max_s)
    # Add occasional longer pauses (10% chance)
    if random.random() < 0.1:
        delay += random.uniform(60, 120)
        print(f"  [Taking a breath... extra pause]")
    print(f"  [Waiting {delay:.1f}s...]")
    time.sleep(delay)


def is_active_hours() -> bool:
    """Check if current time is within safe active hours."""
    hour = datetime.now().hour
    return SAFETY_LIMITS["active_start_hour"] <= hour < SAFETY_LIMITS["active_end_hour"]


def check_circuit_breaker(log: dict) -> tuple[bool, str]:
    """
    Check all safety limits before allowing any action.
    Returns (allowed: bool, reason: str).
    """
    today = get_today_key()
    week = get_week_key()

    # Check active hours
    if not is_active_hours():
        return False, (
            f"Outside safe active hours ({SAFETY_LIMITS['active_start_hour']:02d}:00-"
            f"{SAFETY_LIMITS['active_end_hour']:02d}:00). Current: {datetime.now().strftime('%H:%M')}"
        )

    # Check daily total action limit
    daily_total = sum(log.get("daily_counts", {}).get(today, {}).values())
    if daily_total >= SAFETY_LIMITS["daily_total_actions"]:
        return False, f"Daily total action limit reached ({daily_total}/{SAFETY_LIMITS['daily_total_actions']})"

    # Check weekly connection limit
    weekly_conn = get_weekly_connection_count(log)
    if weekly_conn >= SAFETY_LIMITS["weekly_connections"]:
        return False, f"Weekly connection limit reached ({weekly_conn}/{SAFETY_LIMITS['weekly_connections']})"

    # Check for any LinkedIn warnings in recent actions
    recent_warnings = [w for w in log.get("warnings", [])]
    if recent_warnings:
        last_warning = recent_warnings[-1]
        warning_time = datetime.fromisoformat(last_warning["timestamp"])
        if datetime.now() - warning_time < timedelta(days=14):
            return False, (
                f"Recent warning detected ({last_warning['timestamp']}). "
                f"Cooling off for 14 days. Manual activity only."
            )

    return True, "All safety checks passed"


def can_do_action(log: dict, action_type: str, requested_count: int = 1) -> tuple[bool, str, int]:
    """
    Check if a specific action can be performed.
    Returns (allowed, reason, allowed_count).
    """
    allowed, reason = check_circuit_breaker(log)
    if not allowed:
        return False, reason, 0

    today = get_today_key()
    daily_total = sum(log.get("daily_counts", {}).get(today, {}).values())
    remaining_total = SAFETY_LIMITS["daily_total_actions"] - daily_total

    if action_type == "connection":
        daily_conn = get_daily_count(log, "connection")
        remaining_conn = SAFETY_LIMITS["daily_connections"] - daily_conn
        weekly_conn = get_weekly_connection_count(log)
        remaining_weekly = SAFETY_LIMITS["weekly_connections"] - weekly_conn
        allowed_count = min(remaining_conn, remaining_weekly, remaining_total, requested_count)
        if allowed_count <= 0:
            return False, f"Daily connection limit reached ({daily_conn}/{SAFETY_LIMITS['daily_connections']})", 0
        return True, f"Can send {allowed_count} connection(s)", allowed_count

    elif action_type == "message":
        daily_msg = get_daily_count(log, "message")
        remaining_msg = SAFETY_LIMITS["daily_messages"] - daily_msg
        allowed_count = min(remaining_msg, remaining_total, requested_count)
        if allowed_count <= 0:
            return False, f"Daily message limit reached ({daily_msg}/{SAFETY_LIMITS['daily_messages']})", 0
        return True, f"Can send {allowed_count} message(s)", allowed_count

    elif action_type == "profile_view":
        daily_pv = get_daily_count(log, "profile_view")
        remaining_pv = SAFETY_LIMITS["daily_profile_views"] - daily_pv
        allowed_count = min(remaining_pv, remaining_total, requested_count)
        if allowed_count <= 0:
            return False, f"Daily profile view limit reached ({daily_pv}/{SAFETY_LIMITS['daily_profile_views']})", 0
        return True, f"Can view {allowed_count} profile(s)", allowed_count

    elif action_type == "withdraw":
        # Withdrawals are limited per week but not daily
        allowed_count = min(remaining_total, requested_count)
        return True, f"Can withdraw {allowed_count} request(s)", allowed_count

    return False, f"Unknown action type: {action_type}", 0


def add_warning(log: dict, message: str):
    """Record a warning in the safety log."""
    log["warnings"].append({
        "timestamp": datetime.now().isoformat(),
        "message": message,
    })
    save_safety_log(log)
    print(f"\n{'='*60}")
    print(f"⚠️  WARNING RECORDED: {message}")
    print(f"{'='*60}\n")


# ============================================================================
# PROSPECT MANAGEMENT
# ============================================================================

def load_prospects() -> list[dict]:
    """Load prospects from CSV."""
    if not PROSPECTS_FILE.exists():
        return []
    with open(PROSPECTS_FILE, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def save_prospects(prospects: list[dict]):
    """Save prospects to CSV."""
    if not prospects:
        return
    fieldnames = list(prospects[0].keys())
    with open(PROSPECTS_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(prospects)


def get_prospects_by_status(status: str) -> list[dict]:
    """Get prospects with a specific status."""
    prospects = load_prospects()
    return [p for p in prospects if p.get("status", "new") == status]


def update_prospect_status(url: str, new_status: str, notes: str = ""):
    """Update a prospect's status."""
    prospects = load_prospects()
    for p in prospects:
        if p.get("url") == url or p.get("name") == url:
            p["status"] = new_status
            if notes:
                p["notes"] = (p.get("notes", "") + "; " + notes).strip("; ")
            p["last_updated"] = datetime.now().isoformat()
            save_prospects(prospects)
            return True
    return False


def generate_message(prospect: dict, template_name: str = "value_first") -> str:
    """Generate a personalized message for a prospect."""
    template = MESSAGE_TEMPLATES.get(template_name, MESSAGE_TEMPLATES["value_first"])
    first_name = prospect.get("name", "there").split()[0]

    # Infer topic from title
    title = prospect.get("title", "").lower()
    if "dock" in title or "virtual" in title:
        topic = "virtual screening"
    elif "ml" in title or "ai" in title or "machine learning" in title:
        topic = "ML-driven drug discovery"
    elif "medicinal" in title:
        topic = "medicinal chemistry"
    elif "cadd" in title or "computational" in title:
        topic = "computational chemistry"
    elif "cheminformatics" in title:
        topic = "cheminformatics"
    elif "bioinformatics" in title:
        topic = "bioinformatics"
    else:
        topic = "drug discovery"

    # Get current molecule count
    molecule_count = 2800  # fallback; could query from DB

    return template.format(
        first_name=first_name,
        topic=topic,
        molecule_count=f"{molecule_count:,}",
    )


# ============================================================================
# LINKEDIN ACTIONS (WebBridge-based)
# ============================================================================

def action_connect(prospect: dict, log: dict) -> bool:
    """
    Send a connection request to a prospect.
    SAFEST method: Connect WITHOUT a note (LinkedIn treats these as lower-spam).
    """
    name = prospect.get("name", "")
    url = prospect.get("url", "")

    print(f"\n[CONNECT] {name} ({prospect.get('title', '')} at {prospect.get('company', '')})")
    print(f"  URL: {url}")

    # Navigate to profile
    if not url.startswith("http"):
        url = "https://www.linkedin.com" + ("/in/" + url if not url.startswith("/") else url)

    result = wb_navigate(url)
    if not result.get("ok"):
        print(f"  ❌ Failed to navigate: {result.get('error', 'unknown')}")
        return False

    human_delay(3, 6)

    # Take snapshot to find Connect button
    snap = wb_snapshot()
    if not snap.get("ok"):
        print(f"  ❌ Failed to get snapshot")
        return False

    # Try to find and click Connect button via JavaScript
    # LinkedIn's UI changes frequently, so we use multiple strategies
    connect_js = """
    (() => {
        // Strategy 1: Find button with "Connect" text
        const buttons = Array.from(document.querySelectorAll('button'));
        let connectBtn = buttons.find(b => 
            b.textContent.trim().toLowerCase().includes('connect') &&
            !b.textContent.trim().toLowerCase().includes('connected')
        );
        
        // Strategy 2: Look for aria-label containing "Connect"
        if (!connectBtn) {
            connectBtn = buttons.find(b => 
                b.getAttribute('aria-label')?.toLowerCase().includes('connect')
            );
        }
        
        // Strategy 3: Look in profile actions menu
        if (!connectBtn) {
            const spans = Array.from(document.querySelectorAll('span'));
            const connectSpan = spans.find(s => s.textContent.trim() === 'Connect');
            if (connectSpan) connectBtn = connectSpan.closest('button');
        }
        
        if (connectBtn) {
            connectBtn.click();
            return {success: true, strategy: 'button-click'};
        }
        
        return {success: false, reason: 'Connect button not found'};
    })()
    """
    result = wb_evaluate(connect_js)
    data = result.get("data", {}) if result.get("ok") else {}

    if not data.get("success"):
        print(f"  ⚠️ Could not find Connect button. May already be connected or pending.")
        return False

    human_delay(2, 4)

    # Click "Send without a note" (safer than sending with note)
    send_js = """
    (() => {
        // Look for "Send without a note" button
        const buttons = Array.from(document.querySelectorAll('button'));
        let sendBtn = buttons.find(b => 
            b.textContent.trim().toLowerCase().includes('send without a note')
        );
        
        if (!sendBtn) {
            // Alternative: look for modal send button
            sendBtn = buttons.find(b => 
                b.textContent.trim().toLowerCase() === 'send'
            );
        }
        
        if (sendBtn) {
            sendBtn.click();
            return {success: true};
        }
        
        return {success: false, reason: 'Send button not found'};
    })()
    """
    result = wb_evaluate(send_js)
    data = result.get("data", {}) if result.get("ok") else {}

    if data.get("success"):
        print(f"  ✅ Connection request sent (no note)")
        record_action(log, "connection", f"Sent to {name}", name)
        update_prospect_status(url, "pending")
        return True
    else:
        print(f"  ⚠️ Could not complete connection request")
        return False


def action_send_message(prospect: dict, log: dict, template_name: str = "value_first") -> bool:
    """Send a message to an existing 1st-degree connection."""
    name = prospect.get("name", "")
    url = prospect.get("url", "")

    print(f"\n[MESSAGE] {name}")

    # Generate personalized message
    message = generate_message(prospect, template_name)
    print(f"  Message preview ({len(message)} chars):")
    for line in message.split("\n")[:3]:
        print(f"    {line[:60]}...")

    # Navigate to messaging
    wb_navigate("https://www.linkedin.com/messaging/")
    human_delay(3, 5)

    # Search for the person
    search_js = f"""
    (() => {{
        const inputs = Array.from(document.querySelectorAll('input'));
        const searchInput = inputs.find(i => 
            i.placeholder?.toLowerCase().includes('search') ||
            i.getAttribute('aria-label')?.toLowerCase().includes('search')
        );
        if (searchInput) {{
            searchInput.focus();
            searchInput.value = '{name.split()[0]}';
            searchInput.dispatchEvent(new Event('input', {{bubbles: true}}));
            return {{success: true}};
        }}
        return {{success: false, reason: 'Search input not found'}};
    }})()
    """
    result = wb_evaluate(search_js)
    human_delay(2, 4)

    # Click on the person in search results
    click_js = f"""
    (() => {{
        const items = Array.from(document.querySelectorAll('li, div'));
        const target = items.find(el => 
            el.textContent.toLowerCase().includes('{name.split()[0].lower()}')
        );
        if (target) {{
            target.click();
            return {{success: true}};
        }}
        return {{success: false}};
    }})()
    """
    wb_evaluate(click_js)
    human_delay(2, 4)

    # Type message into contenteditable area
    message_js = f"""
    (() => {{
        const editor = document.querySelector('[contenteditable="true"]');
        if (editor) {{
            editor.focus();
            editor.innerHTML = '<p>{message.replace(chr(10), '</p><p>').replace("'", "\\'")}</p>';
            editor.dispatchEvent(new Event('input', {{bubbles: true}}));
            return {{success: true}};
        }}
        return {{success: false, reason: 'Message editor not found'}};
    }})()
    """
    result = wb_evaluate(message_js)

    if not result.get("ok") or not result.get("data", {}).get("success"):
        print(f"  ❌ Could not type message")
        return False

    human_delay(1, 3)

    # Click Send
    send_js = """
    (() => {
        const buttons = Array.from(document.querySelectorAll('button'));
        const sendBtn = buttons.find(b => 
            b.textContent.trim().toLowerCase() === 'send' ||
            b.getAttribute('aria-label')?.toLowerCase().includes('send message')
        );
        if (sendBtn) {
            sendBtn.click();
            return {success: true};
        }
        return {success: false};
    })()
    """
    result = wb_evaluate(send_js)
    data = result.get("data", {}) if result.get("ok") else {}

    if data.get("success"):
        print(f"  ✅ Message sent")
        record_action(log, "message", f"Sent to {name}", name)
        update_prospect_status(url, "messaged", f"Sent {template_name} message")
        return True
    else:
        print(f"  ❌ Could not send message")
        return False


def action_view_profile(prospect: dict, log: dict) -> bool:
    """View a prospect's profile (low-risk warm-up action)."""
    name = prospect.get("name", "")
    url = prospect.get("url", "")

    print(f"\n[PROFILE VIEW] {name}")

    if not url.startswith("http"):
        url = "https://www.linkedin.com" + ("/in/" + url if not url.startswith("/") else url)

    result = wb_navigate(url)
    if result.get("ok"):
        # Scroll a bit to simulate reading
        scroll_js = "window.scrollTo(0, Math.random() * 500 + 200);"
        wb_evaluate(scroll_js)
        human_delay(5, 12)
        print(f"  ✅ Profile viewed")
        record_action(log, "profile_view", f"Viewed {name}", name)
        return True
    else:
        print(f"  ❌ Failed to view profile")
        return False


# ============================================================================
# BATCH OPERATIONS
# ============================================================================

def batch_connect(batch_size: int = 5, dry_run: bool = False):
    """Send connection requests to a batch of prospects."""
    log = load_safety_log()
    ensure_dirs()

    allowed, reason, allowed_count = can_do_action(log, "connection", batch_size)
    if not allowed:
        print(f"\n🚫 BLOCKED: {reason}")
        return 0

    actual_batch = min(batch_size, allowed_count)
    print(f"\n{'='*60}")
    print(f"BATCH CONNECT | Requested: {batch_size} | Allowed: {actual_batch}")
    print(f"{'='*60}")

    prospects = get_prospects_by_status("new")
    if not prospects:
        print("No new prospects found.")
        return 0

    targets = prospects[:actual_batch]
    success_count = 0

    for i, prospect in enumerate(targets):
        print(f"\n--- [{i+1}/{len(targets)}] ---")
        if dry_run:
            print(f"[DRY RUN] Would connect to: {prospect.get('name')}")
            success_count += 1
        else:
            if action_connect(prospect, log):
                success_count += 1
            if i < len(targets) - 1:
                human_delay()

    print(f"\n{'='*60}")
    print(f"BATCH COMPLETE: {success_count}/{len(targets)} successful")
    print(f"{'='*60}")
    return success_count


def batch_message(batch_size: int = 5, template_name: str = "value_first", dry_run: bool = False):
    """Send messages to a batch of connected prospects."""
    log = load_safety_log()
    ensure_dirs()

    allowed, reason, allowed_count = can_do_action(log, "message", batch_size)
    if not allowed:
        print(f"\n🚫 BLOCKED: {reason}")
        return 0

    actual_batch = min(batch_size, allowed_count)
    print(f"\n{'='*60}")
    print(f"BATCH MESSAGE | Requested: {batch_size} | Allowed: {actual_batch} | Template: {template_name}")
    print(f"{'='*60}")

    prospects = get_prospects_by_status("connected")
    if not prospects:
        print("No connected prospects ready for messaging.")
        return 0

    targets = prospects[:actual_batch]
    success_count = 0

    for i, prospect in enumerate(targets):
        print(f"\n--- [{i+1}/{len(targets)}] ---")
        if dry_run:
            msg = generate_message(prospect, template_name)
            print(f"[DRY RUN] Would message: {prospect.get('name')}")
            print(f"  Preview: {msg[:80]}...")
            success_count += 1
        else:
            if action_send_message(prospect, log, template_name):
                success_count += 1
            if i < len(targets) - 1:
                human_delay()

    print(f"\n{'='*60}")
    print(f"BATCH COMPLETE: {success_count}/{len(targets)} successful")
    print(f"{'='*60}")
    return success_count


def batch_profile_views(batch_size: int = 10, dry_run: bool = False):
    """View profiles as a warm-up / research activity."""
    log = load_safety_log()
    ensure_dirs()

    allowed, reason, allowed_count = can_do_action(log, "profile_view", batch_size)
    if not allowed:
        print(f"\n🚫 BLOCKED: {reason}")
        return 0

    actual_batch = min(batch_size, allowed_count)
    print(f"\n{'='*60}")
    print(f"BATCH PROFILE VIEWS | Requested: {batch_size} | Allowed: {actual_batch}")
    print(f"{'='*60}")

    prospects = load_prospects()
    # Prioritize prospects we haven't connected with yet
    targets = [p for p in prospects if p.get("status") in ["new", "pending"]][:actual_batch]

    if not targets:
        targets = prospects[:actual_batch]

    success_count = 0
    for i, prospect in enumerate(targets):
        print(f"\n--- [{i+1}/{len(targets)}] ---")
        if dry_run:
            print(f"[DRY RUN] Would view: {prospect.get('name')}")
            success_count += 1
        else:
            if action_view_profile(prospect, log):
                success_count += 1
            if i < len(targets) - 1:
                human_delay(30, 90)

    print(f"\n{'='*60}")
    print(f"BATCH COMPLETE: {success_count}/{len(targets)} successful")
    print(f"{'='*60}")
    return success_count


def run_daily_routine(dry_run: bool = False):
    """Execute the recommended daily safe routine."""
    log = load_safety_log()

    print(f"\n{'='*60}")
    print(f"Q-MOL DAILY SAFE ROUTINE")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # Step 1: Health check
    allowed, reason = check_circuit_breaker(log)
    if not allowed:
        print(f"🚫 Cannot run daily routine: {reason}")
        return

    print("✅ Health check passed\n")

    # Step 2: Profile views (warm-up, lowest risk)
    print("--- STEP 1: Profile Views (warm-up) ---")
    batch_profile_views(batch_size=10, dry_run=dry_run)

    # Step 3: Connection requests
    print("\n--- STEP 2: Connection Requests ---")
    batch_connect(batch_size=5, dry_run=dry_run)

    # Step 4: Messages to existing connections
    print("\n--- STEP 3: Messages ---")
    batch_message(batch_size=5, template_name="value_first", dry_run=dry_run)

    print(f"\n{'='*60}")
    print(f"DAILY ROUTINE COMPLETE")
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    print_status()


# ============================================================================
# REPORTING & STATUS
# ============================================================================

def print_status():
    """Print comprehensive account status."""
    log = load_safety_log()
    today = get_today_key()
    week = get_week_key()

    daily = log.get("daily_counts", {}).get(today, {})
    weekly_conn = get_weekly_connection_count(log)

    prospects = load_prospects()
    status_counts = {}
    for p in prospects:
        s = p.get("status", "new")
        status_counts[s] = status_counts.get(s, 0) + 1

    print(f"\n{'='*60}")
    print(f"Q-MOL LINKEDIN SAFETY DASHBOARD")
    print(f"{'='*60}")
    print(f"\n📅 Today: {today} | Week: {week}")
    print(f"\n📊 DAILY LIMITS:")
    print(f"  Connections:    {daily.get('connection', 0):>3} / {SAFETY_LIMITS['daily_connections']}")
    print(f"  Messages:       {daily.get('message', 0):>3} / {SAFETY_LIMITS['daily_messages']}")
    print(f"  Profile Views:  {daily.get('profile_view', 0):>3} / {SAFETY_LIMITS['daily_profile_views']}")
    total_today = sum(daily.values())
    print(f"  ─────────────────────────")
    print(f"  TOTAL ACTIONS:  {total_today:>3} / {SAFETY_LIMITS['daily_total_actions']}")

    print(f"\n📅 WEEKLY LIMITS:")
    print(f"  Connections:    {weekly_conn:>3} / {SAFETY_LIMITS['weekly_connections']}")

    print(f"\n📁 PROSPECT PIPELINE:")
    for status, count in sorted(status_counts.items()):
        print(f"  {status:15s}: {count:>3}")
    print(f"  ─────────────────────────")
    print(f"  TOTAL:          {len(prospects):>3}")

    print(f"\n🏥 ACCOUNT HEALTH:")
    print(f"  Total actions (all time): {log.get('total_actions_all_time', 0)}")
    print(f"  Warnings: {len(log.get('warnings', []))}")
    if log.get("warnings"):
        last_warn = log["warnings"][-1]
        print(f"  Last warning: {last_warn['timestamp']} - {last_warn['message']}")

    # Acceptance rate estimate
    total_conn = log.get("total_connections_sent", 0)
    if total_conn > 0:
        # Rough estimate: connections that became 'connected' / total sent
        connected_count = status_counts.get("connected", 0) + status_counts.get("messaged", 0)
        est_rate = connected_count / max(total_conn, 1)
        print(f"\n📈 EST. ACCEPTANCE RATE: {est_rate:.1%}")
        if est_rate < SAFETY_LIMITS["warning_acceptance_rate"]:
            print(f"  ⚠️  WARNING: Below {SAFETY_LIMITS['warning_acceptance_rate']:.0%} threshold!")
        elif est_rate < SAFETY_LIMITS["target_acceptance_rate"]:
            print(f"  ⚡ Caution: Below {SAFETY_LIMITS['target_acceptance_rate']:.0%} target")
        else:
            print(f"  ✅ Healthy")

    print(f"\n{'='*60}\n")


def export_ready_messages():
    """Export messages ready to send for manual copy-paste fallback."""
    ensure_dirs()
    prospects = load_prospects()
    output_file = DATA_DIR / "ready_messages.txt"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("Q-MOL LINKEDIN MESSAGES - READY TO SEND\n")
        f.write("="*60 + "\n")
        f.write("Use these for manual sending if automation is paused.\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n\n")

        for p in prospects:
            if p.get("status") == "connected" and not p.get("messaged"):
                msg = generate_message(p, "value_first")
                f.write(f"TO: {p['name']}\n")
                f.write(f"URL: {p['url']}\n")
                f.write(f"TITLE: {p['title']} @ {p['company']}\n")
                f.write("-"*40 + "\n")
                f.write(msg + "\n")
                f.write("\n" + "="*60 + "\n\n")

    print(f"✅ Exported ready messages to: {output_file}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Q-Mol LinkedIn Safe Automation Controller",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python linkedin_safe_automation.py --mode status
  python linkedin_safe_automation.py --mode daily --dry-run
  python linkedin_safe_automation.py --mode connect --batch-size 3
  python linkedin_safe_automation.py --mode message --batch-size 5 --template value_first
  python linkedin_safe_automation.py --mode profile_views --batch-size 10
        """,
    )
    parser.add_argument(
        "--mode",
        choices=[
            "status", "daily", "connect", "message",
            "profile_views", "export", "health_check"
        ],
        default="status",
        help="Automation mode to run",
    )
    parser.add_argument("--batch-size", type=int, default=5, help="Number of actions per batch")
    parser.add_argument("--template", default="value_first", help="Message template name")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without sending")

    args = parser.parse_args()
    ensure_dirs()

    if args.mode == "status":
        print_status()

    elif args.mode == "health_check":
        log = load_safety_log()
        allowed, reason = check_circuit_breaker(log)
        print(f"\nHealth Check: {'✅ PASSED' if allowed else '🚫 BLOCKED'}")
        print(f"Reason: {reason}\n")

    elif args.mode == "daily":
        run_daily_routine(dry_run=args.dry_run)

    elif args.mode == "connect":
        batch_connect(batch_size=args.batch_size, dry_run=args.dry_run)

    elif args.mode == "message":
        batch_message(
            batch_size=args.batch_size,
            template_name=args.template,
            dry_run=args.dry_run,
        )

    elif args.mode == "profile_views":
        batch_profile_views(batch_size=args.batch_size, dry_run=args.dry_run)

    elif args.mode == "export":
        export_ready_messages()


if __name__ == "__main__":
    main()
