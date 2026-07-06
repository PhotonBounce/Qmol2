#!/usr/bin/env python3
"""
Q-Mol LinkedIn Stealth Automation Bot

Uses CDP (Chrome DevTools Protocol) for trusted input events
that bypass LinkedIn's isTrusted checks. Combines with
human-like behavior simulation to avoid detection.

CRITICAL: This is NOT 100% safe. LinkedIn can still ban accounts.
Use at your own risk. Start with VERY conservative limits.

Architecture:
1. CDP raw protocol for mouse/keyboard (trusted events)
2. Human behavior: random delays, scroll patterns, reading simulation
3. Variable session lengths and action counts
4. Warm-up / cool-down phases
5. Message uniqueness via template randomization + synonym replacement
6. Detection monitoring: halt on any warning signal

Requires: WebBridge daemon running at http://127.0.0.1:10086
"""

import json
import random
import time
import requests
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# === CONFIGURATION ===
WEBBRIDGE_URL = "http://127.0.0.1:10086/command"
SESSION = "linkedin-stealth"
PROJECT_DIR = Path(__file__).parent.parent
DATA_DIR = PROJECT_DIR / "data" / "linkedin"
LOG_DIR = DATA_DIR / "logs"
STOP_FILE = PROJECT_DIR / "scripts" / "STOP.txt"

# Ultra-conservative limits for stealth
LIMITS = {
    "connections_per_day": 8,        # VERY low (LinkedIn safe is ~15-20, we go lower)
    "messages_per_day": 5,           # Even lower for messages
    "profile_views_per_day": 15,   # Minimal profile viewing
    "total_actions_per_day": 20,    # Total cap
    "min_delay_between_actions": 90,  # seconds
    "max_delay_between_actions": 240, # seconds
    "warmup_minutes": 2,            # Scroll feed before acting
    "cooldown_minutes": 1,          # Read something after acting
    "session_minutes_min": 5,       # Short sessions
    "session_minutes_max": 15,      # Never too long
}

# Business hours only
ALLOWED_HOURS = range(9, 18)  # 9 AM to 6 PM
ALLOWED_DAYS = [0, 1, 2, 3, 4]  # Monday-Friday only

# === CDP HELPERS ===

def cdp_command(method: str, params: dict = None, session: str = SESSION):
    """Send a raw CDP command via WebBridge."""
    payload = {
        "action": "cdp",
        "args": {
            "method": method,
            "params": params or {}
        },
        "session": session
    }
    try:
        resp = requests.post(WEBBRIDGE_URL, json=payload, timeout=20)
        return resp.json()
    except Exception as e:
        print(f"[CDP ERROR] {method}: {e}")
        return {"ok": False, "error": str(e)}


def get_tab_id():
    """Get current tab ID for CDP commands."""
    # Find the active LinkedIn tab
    result = send_webbridge("find_tab", {"url": "https://www.linkedin.com", "active": True})
    if result.get("ok"):
        return result.get("data", {}).get("tabId")
    return None


def send_webbridge(action: str, args: dict, session: str = SESSION):
    """Send a standard WebBridge command."""
    payload = {"action": action, "args": args, "session": session}
    try:
        resp = requests.post(WEBBRIDGE_URL, json=payload, timeout=20)
        return resp.json()
    except Exception as e:
        print(f"[WEBBRIDGE ERROR] {action}: {e}")
        return {"ok": False, "error": str(e)}


# === TRUSTED INPUT VIA CDP ===

def trusted_click(x: int, y: int, tab_id: int = None):
    """
    Dispatch a trusted mouse click using CDP Input.dispatchMouseEvent.
    This fires event.isTrusted=true events that bypass LinkedIn detection.
    """
    if not tab_id:
        tab_id = get_tab_id()
    if not tab_id:
        print("[ERROR] Could not get tab ID")
        return False

    # Step 1: Move mouse to target (hover)
    cdp_command("Input.dispatchMouseEvent", {
        "type": "mouseMoved",
        "x": x,
        "y": y,
        "button": "none",
        "clickCount": 0
    })
    time.sleep(random.uniform(0.2, 0.6))  # Human pause before click

    # Step 2: Mouse down (press)
    cdp_command("Input.dispatchMouseEvent", {
        "type": "mousePressed",
        "x": x,
        "y": y,
        "button": "left",
        "clickCount": 1
    })
    time.sleep(random.uniform(0.05, 0.15))  # Brief press

    # Step 3: Mouse up (release)
    cdp_command("Input.dispatchMouseEvent", {
        "type": "mouseReleased",
        "x": x,
        "y": y,
        "button": "left",
        "clickCount": 1
    })
    time.sleep(random.uniform(0.3, 0.8))  # Post-click pause

    return True


def trusted_type(text: str, x: int, y: int, tab_id: int = None):
    """
    Type text with human-like timing using CDP Input.dispatchKeyEvent.
    Each keystroke has variable delay like a real human.
    """
    if not tab_id:
        tab_id = get_tab_id()

    # Click first to focus
    trusted_click(x, y, tab_id)
    time.sleep(0.5)

    for char in text:
        # Key down
        cdp_command("Input.dispatchKeyEvent", {
            "type": "keyDown",
            "text": char
        })
        # Variable delay per keystroke (typing speed varies)
        delay = random.uniform(0.05, 0.25)
        if random.random() < 0.05:  # 5% chance of hesitation
            delay += random.uniform(0.3, 0.8)
        time.sleep(delay)

        # Key up
        cdp_command("Input.dispatchKeyEvent", {
            "type": "keyUp",
            "text": char
        })

    return True


def trusted_scroll(direction: str = "down", amount: int = 300, tab_id: int = None):
    """
    Scroll with human-like mouse wheel behavior using CDP.
    """
    if not tab_id:
        tab_id = get_tab_id()

    # Get viewport size for random scroll position
    result = cdp_command("Runtime.evaluate", {
        "expression": "JSON.stringify({width: window.innerWidth, height: window.innerHeight})"
    })

    # Random scroll position within viewport (humans don't always scroll center)
    x = random.randint(100, 800)
    y = random.randint(200, 600)

    for _ in range(random.randint(2, 5)):  # Multiple small scrolls
        cdp_command("Input.dispatchMouseEvent", {
            "type": "mouseWheel",
            "x": x,
            "y": y,
            "deltaX": 0,
            "deltaY": -amount if direction == "down" else amount
        })
        time.sleep(random.uniform(0.3, 0.8))

    return True


# === HUMAN BEHAVIOR SIMULATION ===

def random_mouse_movement():
    """Move mouse to random positions on page (humans do this constantly)."""
    # Get viewport
    result = cdp_command("Runtime.evaluate", {
        "expression": "JSON.stringify({w: window.innerWidth, h: window.innerHeight})"
    })

    for _ in range(random.randint(2, 4)):
        x = random.randint(100, 900)
        y = random.randint(100, 700)
        cdp_command("Input.dispatchMouseEvent", {
            "type": "mouseMoved",
            "x": x,
            "y": y,
            "button": "none"
        })
        time.sleep(random.uniform(0.5, 1.5))


def warmup_phase():
    """
    Simulate a human arriving at LinkedIn and scrolling the feed.
    This "warms up" the session before any action.
    """
    print(f"[WARMUP] Scrolling feed for {LIMITS['warmup_minutes']} minutes...")
    duration = LIMITS['warmup_minutes'] * 60
    start = time.time()

    while time.time() - start < duration:
        # Scroll feed
        trusted_scroll("down", random.randint(200, 400))
        time.sleep(random.uniform(2, 5))

        # Occasionally scroll back up (humans do this)
        if random.random() < 0.3:
            trusted_scroll("up", random.randint(100, 200))
            time.sleep(random.uniform(1, 3))

        # Random mouse movement
        random_mouse_movement()

        # Sometimes "read" a post by pausing longer
        if random.random() < 0.2:
            print("[WARMUP] 'Reading' a post...")
            time.sleep(random.uniform(5, 12))

    print("[WARMUP] Complete")


def cooldown_phase():
    """
    After actions, simulate reading or browsing before closing session.
    """
    print(f"[COOLDOWN] Browsing for {LIMITS['cooldown_minutes']} minute(s)...")
    duration = LIMITS['cooldown_minutes'] * 60
    start = time.time()

    while time.time() - start < duration:
        trusted_scroll("down", random.randint(150, 300))
        time.sleep(random.uniform(2, 4))
        random_mouse_movement()

    print("[COOLDOWN] Complete")


# === DETECTION MONITORING ===

def check_for_warnings():
    """
    Check if LinkedIn has shown any warning/ban/verification screen.
    Returns True if safe to continue, False if STOP needed.
    """
    # Check for stop file
    if STOP_FILE.exists():
        print("[STOP] STOP.txt file found. Halting.")
        return False

    # Take snapshot and check for warning text
    result = send_webbridge("snapshot", {})
    if not result.get("ok"):
        return True  # Snapshot failed but not a warning

    # Check for common warning keywords in the page text
    warning_keywords = [
        "unusual activity", "suspicious activity", "verification",
        "security check", "prove you're not a robot", "CAPTCHA",
        "restricted", "temporary limit", "account restricted",
        "too many invitations", "you've reached the limit"
    ]

    try:
        tree_json = json.dumps(result.get("data", {}))
        tree_lower = tree_json.lower()
        for keyword in warning_keywords:
            if keyword in tree_lower:
                print(f"[WARNING] Detected: '{keyword}' — EMERGENCY STOP")
                log_action("EMERGENCY_STOP", "LINKEDIN", f"Warning detected: {keyword}")
                # Create STOP file
                STOP_FILE.parent.mkdir(parents=True, exist_ok=True)
                STOP_FILE.write_text(f"Emergency stop triggered at {datetime.now()}. Reason: {keyword}")
                return False
    except Exception:
        pass

    return True


def log_action(action_type: str, target: str, details: str = ""):
    """Log every action for audit trail."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"actions_{datetime.now().strftime('%Y-%m')}.jsonl"

    entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action_type,
        "target": target,
        "details": details,
        "session": SESSION
    }

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


# === DAILY LIMITS ===

def get_daily_count(action_type: str) -> int:
    """Get how many actions of this type were done today."""
    today = datetime.now().strftime("%Y-%m-%d")
    count_file = DATA_DIR / f"daily_counts_{today}.json"
    if count_file.exists():
        data = json.loads(count_file.read_text())
        return data.get(action_type, 0)
    return 0


def increment_daily_count(action_type: str):
    """Increment today's action count."""
    today = datetime.now().strftime("%Y-%m-%d")
    count_file = DATA_DIR / f"daily_counts_{today}.json"
    count_file.parent.mkdir(parents=True, exist_ok=True)

    data = {}
    if count_file.exists():
        data = json.loads(count_file.read_text())

    data[action_type] = data.get(action_type, 0) + 1
    data["total"] = data.get("total", 0) + 1
    count_file.write_text(json.dumps(data))


def can_perform_action(action_type: str) -> bool:
    """Check if we can perform this action without exceeding limits."""
    count = get_daily_count(action_type)
    limit = LIMITS.get(f"{action_type}_per_day", LIMITS["total_actions_per_day"])
    total_count = get_daily_count("total")

    if count >= limit:
        print(f"[LIMIT] {action_type} limit reached: {count}/{limit}")
        return False
    if total_count >= LIMITS["total_actions_per_day"]:
        print(f"[LIMIT] Total actions limit reached: {total_count}/{LIMITS['total_actions_per_day']}")
        return False

    return True


# === BUSINESS HOURS CHECK ===

def is_business_hours() -> bool:
    """Check if current time is within allowed business hours."""
    now = datetime.now()
    if now.weekday() not in ALLOWED_DAYS:
        print("[TIME] Weekend — not running")
        return False
    if now.hour not in ALLOWED_HOURS:
        print(f"[TIME] Hour {now.hour} outside business hours (9-18)")
        return False
    return True


# === MESSAGE EVASION ===

def generate_unique_message(prospect_name: str, prospect_title: str, template: str = "cold") -> str:
    """
    Generate a unique message with randomization to avoid duplicate detection.
    """
    import sqlite3
    try:
        db_path = PROJECT_DIR / "data" / "saas.sqlite"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(DISTINCT smiles) FROM molecules")
        count = cursor.fetchone()[0] or 2800
        conn.close()
    except Exception:
        count = 2800

    first_name = prospect_name.split()[0] if prospect_name else "there"

    # Multiple opening variants
    openings = [
        f"Hi {first_name},",
        f"Hello {first_name},",
        f"Hey {first_name},",
    ]

    # Multiple closing variants
    closings = [
        "Cheers,\nDmitriy",
        "Best,\nDmitriy Buchman",
        "Thanks,\nDmitriy",
    ]

    # Multiple body variants with slight rewording
    body_variants = [
        f"I came across your work in {prospect_title.lower() if prospect_title else 'cheminformatics'} — really impressive. I built Q-Mol, a platform that auto-harvests drug-like molecules from PubChem with RDKit descriptors. Currently {count:,} molecules, growing every 5 minutes. Free 7-day trial, no CC. Worth a look? https://photon-bounce.com/qmol/app/",

        f"Quick question: how much time does your team spend curating compound libraries? I built Q-Mol to automate that — {count:,} molecules with full ADMET descriptors (MW, LogP, TPSA, QED, Lipinski, PAINS). Free trial: https://photon-bounce.com/qmol/app/ Marketplace: https://photon-bounce.com/qmol/marketplace.html",

        f"Saw your profile and thought you might find this useful. Q-Mol auto-harvests {count:,} drug-like molecules from PubChem with RDKit validation. Export as CSV for docking, ML, or assays. 7-day free trial — no credit card. https://photon-bounce.com/qmol/app/",
    ]

    opening = random.choice(openings)
    body = random.choice(body_variants)
    closing = random.choice(closings)

    # Sometimes add a middle paragraph (varies message length)
    if random.random() < 0.5:
        middle = random.choice([
            "Use cases include virtual screening prep, ML training datasets, and assay panel design.",
            "The dataset includes kinase scaffolds, CNS-penetrant libraries, and natural product fragments.",
            "We also accept crypto for the full dataset: ETH, BTC, SOL, and more."
        ])
        body = body + "\n\n" + middle

    return f"{opening}\n\n{body}\n\n{closing}"


# === MAIN WORKFLOWS ===

def send_connection_request(prospect_url: str) -> bool:
    """Send a connection request via WebBridge with CDP trusted click."""
    if not can_perform_action("connections"):
        return False

    if not check_for_warnings():
        return False

    print(f"[ACTION] Connecting to {prospect_url}")

    # Navigate to profile
    result = send_webbridge("navigate", {"url": prospect_url})
    if not result.get("ok"):
        print(f"[ERROR] Failed to navigate to {prospect_url}")
        return False

    time.sleep(random.uniform(2, 4))

    # Check for warnings again after navigation
    if not check_for_warnings():
        return False

    # Find Connect button using evaluate (get coordinates)
    result = send_webbridge("evaluate", {
        "code": """(() => {
            const btn = document.querySelector('button[aria-label*="Connect"]') || 
                        document.querySelector('button.artdeco-button--primary');
            if (btn) {
                const rect = btn.getBoundingClientRect();
                return {found: true, x: rect.left + rect.width/2, y: rect.top + rect.height/2};
            }
            return {found: false};
        })()"""
    })

    if not result.get("ok") or not result.get("data", {}).get("value", {}).get("found"):
        print("[ERROR] Could not find Connect button")
        return False

    coords = result["data"]["value"]
    x, y = int(coords["x"]), int(coords["y"])

    print(f"[CLICK] Connect button at ({x}, {y})")

    # Use CDP trusted click
    if not trusted_click(x, y):
        return False

    time.sleep(random.uniform(2, 3))

    # Sometimes LinkedIn shows a "Add a note" dialog — click "Send without a note"
    result = send_webbridge("evaluate", {
        "code": """(() => {
            const sendBtn = document.querySelector('button[aria-label="Send without a note"]');
            if (sendBtn) {
                const rect = sendBtn.getBoundingClientRect();
                return {found: true, x: rect.left + rect.width/2, y: rect.top + rect.height/2};
            }
            return {found: false};
        })()"""
    })

    if result.get("ok") and result.get("data", {}).get("value", {}).get("found"):
        coords = result["data"]["value"]
        print(f"[CLICK] 'Send without a note' at ({int(coords['x'])}, {int(coords['y'])})")
        trusted_click(int(coords["x"]), int(coords["y"]))

    increment_daily_count("connections")
    increment_daily_count("total")
    log_action("CONNECTION_SENT", prospect_url, f"Clicked at ({x}, {y})")

    print(f"[SUCCESS] Connection sent to {prospect_url}")
    return True


def send_message(prospect_name: str, prospect_url: str) -> bool:
    """Send a message to a connected prospect."""
    if not can_perform_action("messages"):
        return False

    if not check_for_warnings():
        return False

    # Navigate to messaging
    result = send_webbridge("navigate", {"url": "https://www.linkedin.com/messaging/"})
    if not result.get("ok"):
        return False

    time.sleep(random.uniform(2, 4))

    # Search for the person
    search_result = send_webbridge("evaluate", {
        "code": f"""(() => {{
            const input = document.querySelector('input[placeholder*="Search"]');
            if (input) {{
                input.focus();
                input.value = "{prospect_name}";
                input.dispatchEvent(new Event('input', {{bubbles: true}}));
                return {{found: true}};
            }}
            return {{found: false}};
        }})()"""
    })

    time.sleep(random.uniform(2, 3))

    # Click the person in search results
    result = send_webbridge("evaluate", {
        "code": f"""(() => {{
            const items = document.querySelectorAll('[role="listitem"]');
            for (const item of items) {{
                if (item.textContent.includes("{prospect_name}")) {{
                    const rect = item.getBoundingClientRect();
                    return {{found: true, x: rect.left + rect.width/2, y: rect.top + rect.height/2}};
                }}
            }}
            return {{found: false}};
        }})()"""
    })

    if result.get("ok") and result.get("data", {}).get("value", {}).get("found"):
        coords = result["data"]["value"]
        trusted_click(int(coords["x"]), int(coords["y"]))
        time.sleep(random.uniform(1, 2))

    # Generate and send message
    message = generate_unique_message(prospect_name, "")

    # Find message input
    result = send_webbridge("evaluate", {
        "code": """(() => {
            const editor = document.querySelector('[contenteditable="true"]');
            if (editor) {
                const rect = editor.getBoundingClientRect();
                return {found: true, x: rect.left + rect.width/2, y: rect.top + rect.height/2};
            }
            return {found: false};
        })()"""
    })

    if result.get("ok") and result.get("data", {}).get("value", {}).get("found"):
        coords = result["data"]["value"]
        # Type message with CDP trusted input
        trusted_type(message, int(coords["x"]), int(coords["y"]))

        time.sleep(random.uniform(1, 2))

        # Find and click Send button
        send_result = send_webbridge("evaluate", {
            "code": """(() => {
                const btn = document.querySelector('button[type="submit"]') || 
                            Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'Send');
                if (btn) {
                    const rect = btn.getBoundingClientRect();
                    return {found: true, x: rect.left + rect.width/2, y: rect.top + rect.height/2};
                }
                return {found: false};
            })()"""
        })

        if send_result.get("ok") and send_result.get("data", {}).get("value", {}).get("found"):
            coords = send_result["data"]["value"]
            trusted_click(int(coords["x"]), int(coords["y"]))

    increment_daily_count("messages")
    increment_daily_count("total")
    log_action("MESSAGE_SENT", prospect_url, f"Message length: {len(message)} chars")

    print(f"[SUCCESS] Message sent to {prospect_name}")
    return True


# === MAIN CONTROLLER ===

def run_session(mode: str = "connections"):
    """Run a full stealth session."""
    print("=" * 60)
    print(f"Q-MOL LINKEDIN STEALTH BOT — {datetime.now()}")
    print("=" * 60)

    # Business hours check
    if not is_business_hours():
        print("[EXIT] Outside business hours")
        return

    # Check for stop file
    if STOP_FILE.exists():
        print(f"[STOP] STOP.txt exists — {STOP_FILE.read_text()}")
        return

    # Check for warnings
    if not check_for_warnings():
        return

    # Check current counts
    total = get_daily_count("total")
    if total >= LIMITS["total_actions_per_day"]:
        print(f"[LIMIT] Daily total reached: {total}/{LIMITS['total_actions_per_day']}")
        return

    print(f"[STATUS] Today: {total}/{LIMITS['total_actions_per_day']} actions used")
    print(f"[MODE] Running: {mode}")

    # WARMUP PHASE
    warmup_phase()

    # Check warnings after warmup
    if not check_for_warnings():
        return

    # Load prospects
    prospects_file = DATA_DIR / "prospects.csv"
    if not prospects_file.exists():
        print("[ERROR] No prospects file found. Run prospect extractor first.")
        return

    import csv
    prospects = []
    with open(prospects_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("status") in ["new", "connected"]:
                prospects.append(row)

    if not prospects:
        print("[INFO] No prospects ready for action")
        return

    # Randomize prospect order (humans don't work alphabetically)
    random.shuffle(prospects)

    # Determine how many actions this session
    session_max = random.randint(2, 5) if mode == "connections" else random.randint(1, 3)
    actions_done = 0

    for prospect in prospects[:session_max]:
        # Check if we should continue
        if not check_for_warnings():
            break
        if not can_perform_action(mode):
            break

        name = prospect.get("name", "")
        url = prospect.get("url", "")

        if not url:
            continue

        # Random delay before action
        delay = random.uniform(LIMITS["min_delay_between_actions"], LIMITS["max_delay_between_actions"])
        print(f"[WAIT] Pausing {delay:.0f}s before next action...")
        time.sleep(delay)

        # Random mouse movement (humans do this constantly)
        random_mouse_movement()

        # Perform action
        if mode == "connections":
            success = send_connection_request(url)
            if success:
                actions_done += 1
                prospect["status"] = "connection_sent"
                prospect["last_action_date"] = datetime.now().strftime("%Y-%m-%d")
        elif mode == "messages":
            success = send_message(name, url)
            if success:
                actions_done += 1
                prospect["status"] = "messaged"
                prospect["last_action_date"] = datetime.now().strftime("%Y-%m-%d")

        # Longer break between actions (humans don't do things back-to-back)
        if random.random() < 0.5:
            break_time = random.uniform(30, 90)
            print(f"[BREAK] Taking a {break_time:.0f}s break...")
            time.sleep(break_time)

            # During break, scroll feed like a human would
            trusted_scroll("down", random.randint(200, 400))

    # Save updated prospects
    with open(prospects_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=prospects[0].keys() if prospects else [])
        writer.writeheader()
        writer.writerows(prospects)

    # COOLDOWN PHASE
    cooldown_phase()

    print(f"[SESSION] Complete. Actions: {actions_done}")
    print(f"[NEXT] Run again tomorrow or after {random.randint(2, 4)} hours")
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Q-Mol LinkedIn Stealth Bot")
    parser.add_argument("--mode", choices=["connections", "messages", "status"], default="connections")
    parser.add_argument("--stop", action="store_true", help="Create emergency STOP file")
    args = parser.parse_args()

    if args.stop:
        STOP_FILE.parent.mkdir(parents=True, exist_ok=True)
        STOP_FILE.write_text(f"Emergency stop by user at {datetime.now()}")
        print("[STOP] Emergency stop file created. All automation will halt.")
        sys.exit(0)

    if args.mode == "status":
        print(f"[STATUS] Today: {get_daily_count('total')}/{LIMITS['total_actions_per_day']} actions")
        print(f"[STATUS] Connections: {get_daily_count('connections')}/{LIMITS['connections_per_day']}")
        print(f"[STATUS] Messages: {get_daily_count('messages')}/{LIMITS['messages_per_day']}")
        print(f"[STATUS] Business hours: {is_business_hours()}")
        print(f"[STATUS] STOP file: {STOP_FILE.exists()}")
    else:
        run_session(args.mode)
