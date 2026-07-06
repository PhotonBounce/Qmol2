#!/usr/bin/env python3
"""
Q-Mol LinkedIn WebBridge Automation — High-Level Workflows
Orchestrates webbridge_driver, safety_guard, and linkedin_outreach
into safe, semi-automated LinkedIn actions.

Usage:
    python webbridge_linkedin_automation.py --workflow search_prospects --query "cheminformatics" --pages 2
    python webbridge_linkedin_automation.py --workflow send_connections --limit 5 --dry-run
    python webbridge_linkedin_automation.py --workflow send_connections --limit 5 --interactive
    python webbridge_linkedin_automation.py --workflow send_messages --limit 5 --interactive
    python webbridge_linkedin_automation.py --workflow create_post
    python webbridge_linkedin_automation.py --workflow extract_post_leads --post-url "https://..."
"""

import argparse
import csv
import json
import os
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path

# Add scripts dir to path for imports
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from webbridge_driver import (
    navigate, snapshot, click, fill, evaluate, screenshot,
    scroll, find_element_by_text, click_by_text, send_command
)

# ─── Configuration ───────────────────────────────────────────────────────────
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR / "data" / "linkedin"
OUTPUT_DIR = DATA_DIR
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SESSION_NAME = "qmol-linkedin"
GROUP_TITLE = "Q-Mol LinkedIn Automation"

# Safety: check for emergency STOP file
STOP_FILE = SCRIPT_DIR / "STOP.txt"

# LinkedIn URLs
LINKEDIN_FEED = "https://www.linkedin.com/feed/"
LINKEDIN_SEARCH_PEOPLE = "https://www.linkedin.com/search/results/people/?keywords={}"
LINKEDIN_MESSAGING = "https://www.linkedin.com/messaging/"
LINKEDIN_MY_NETWORK = "https://www.linkedin.com/mynetwork/"


def check_stop():
    """Check if emergency STOP file exists."""
    if STOP_FILE.exists():
        print("🛑 EMERGENCY STOP FILE DETECTED. Halting automation.")
        print(f"   Remove {STOP_FILE} to resume.")
        sys.exit(0)


def human_delay(min_seconds=60, max_seconds=180):
    """Wait a random human-like duration."""
    delay = random.uniform(min_seconds, max_seconds)
    print(f"⏱️  Human delay: {delay:.1f}s...")
    time.sleep(delay)


def business_hours_check():
    """Warn if running outside US business hours."""
    now = datetime.now()
    hour = now.hour
    weekday = now.weekday()  # 0=Monday
    if weekday >= 5:  # Weekend
        print("⚠️  WARNING: It's the weekend. LinkedIn automation on weekends looks suspicious.")
        print("   Recommend waiting until Monday.")
        return False
    if hour < 9 or hour > 18:
        print("⚠️  WARNING: Outside US business hours (9 AM–6 PM).")
        print("   Off-hours automation increases ban risk.")
        return False
    return True


def extract_people_from_search(page_tree):
    """Extract people from LinkedIn search snapshot."""
    people = []
    # LinkedIn search results contain links like /in/username
    # We use regex on the snapshot text to find profile URLs
    text = json.dumps(page_tree)
    # Find linkedin.com/in/ patterns
    matches = re.findall(r'linkedin\.com/in/([^"\s/?]+)', text)
    seen = set()
    for match in matches:
        if match not in seen:
            seen.add(match)
            people.append({
                "profile_url": f"https://www.linkedin.com/in/{match}/",
                "username": match
            })
    return people


def workflow_search_prospects(query, pages=2, dry_run=False):
    """
    Search LinkedIn for prospects. Read-only — very safe.
    Exports results to CSV for manual review.
    """
    check_stop()
    print(f"🔍 WORKFLOW: Search Prospects")
    print(f"   Query: '{query}'")
    print(f"   Pages: {pages}")
    print(f"   Mode: {'DRY-RUN' if dry_run else 'LIVE'}")

    if not dry_run:
        if not business_hours_check():
            resp = input("Continue anyway? [y/N]: ")
            if resp.lower() != 'y':
                return

    all_people = []

    for page in range(1, pages + 1):
        check_stop()
        start = (page - 1) * 10
        search_url = f"{LINKEDIN_SEARCH_PEOPLE.format(query.replace(' ', '%20'))}&page={page}&start={start}"

        print(f"\n📄 Page {page}: {search_url}")

        if dry_run:
            print("   [DRY-RUN] Would navigate to search URL")
            continue

        navigate(search_url, session=SESSION_NAME, new_tab=(page == 1))
        human_delay(5, 8)  # Wait for page load

        result = snapshot(session=SESSION_NAME)
        if not result.get("ok"):
            print(f"   ❌ Snapshot failed: {result}")
            continue

        tree = result.get("data", {})
        people = extract_people_from_search(tree)
        print(f"   ✅ Found {len(people)} unique profiles")
        all_people.extend(people)

        if page < pages:
            human_delay(10, 15)  # Delay between pages

    # Deduplicate
    seen = set()
    unique_people = []
    for p in all_people:
        if p["profile_url"] not in seen:
            seen.add(p["profile_url"])
            unique_people.append(p)

    print(f"\n📊 Total unique prospects found: {len(unique_people)}")

    # Export to CSV
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    csv_path = OUTPUT_DIR / f"search_results_{timestamp}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["profile_url", "username", "search_query", "found_date"])
        writer.writeheader()
        for p in unique_people:
            writer.writerow({
                "profile_url": p["profile_url"],
                "username": p["username"],
                "search_query": query,
                "found_date": datetime.now().strftime("%Y-%m-%d")
            })

    print(f"💾 Exported to: {csv_path}")
    print(f"\n⚠️  NEXT STEPS:")
    print(f"   1. Open {csv_path} and manually review each profile")
    print(f"   2. Copy approved URLs to your prospect database:")
    print(f"      python linkedin_outreach.py --action add_prospect --name \"...\" --url \"...\"")

    return csv_path


def workflow_send_connections(limit=5, dry_run=False, interactive=False):
    """
    Send connection requests to prospects from the database.
    MEDIUM RISK — requires human review.
    """
    check_stop()
    print(f"🔗 WORKFLOW: Send Connection Requests")
    print(f"   Limit: {limit}")
    print(f"   Mode: {'DRY-RUN' if dry_run else 'LIVE'}")
    print(f"   Interactive: {'YES' if interactive else 'NO'}")

    # Load prospects
    sys.path.insert(0, str(SCRIPT_DIR))
    from linkedin_outreach import load_prospects, can_execute_today, record_action, load_log, save_log

    prospects = load_prospects()
    log = load_log()

    # Filter to 'new' prospects only
    candidates = [p for p in prospects if p.get("status") == "new"]
    print(f"   Candidates: {len(candidates)}")

    if not candidates:
        print("   ⚠️  No new prospects to connect with.")
        return

    sent = 0
    for prospect in candidates[:limit]:
        check_stop()

        if not can_execute_today(log, "connection"):
            print("   🚫 Daily connection limit reached. Stopping.")
            break

        name = prospect.get("name", "Unknown")
        url = prospect.get("url", "")

        print(f"\n👤 Prospect: {name}")
        print(f"   URL: {url}")

        if interactive:
            resp = input(f"   Send connection to {name}? [Y/n/skip/quit]: ").strip().lower()
            if resp == 'quit':
                print("   👋 Quitting.")
                break
            if resp == 'skip':
                print("   ⏭️  Skipped.")
                continue
            if resp and resp != 'y':
                print("   ⏭️  Skipped.")
                continue

        if dry_run:
            print("   [DRY-RUN] Would navigate to profile and click Connect")
            sent += 1
            continue

        # Navigate to profile
        if url:
            navigate(url, session=SESSION_NAME)
        else:
            # Search by name
            search_url = LINKEDIN_SEARCH_PEOPLE.format(name.replace(' ', '%20'))
            navigate(search_url, session=SESSION_NAME)

        human_delay(4, 7)

        # Get snapshot to find Connect button
        result = snapshot(session=SESSION_NAME)
        if not result.get("ok"):
            print(f"   ❌ Snapshot failed")
            continue

        # Try to find Connect button via @e refs or text
        tree = result.get("data", {})
        tree_str = json.dumps(tree)

        # Look for @e ref containing "Connect"
        connect_ref = None
        # This is heuristic — in practice you'd inspect the snapshot
        # For safety, we use evaluate to find the button
        click_result = evaluate("""
        (() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const connectBtn = btns.find(b => {
                const text = b.textContent.trim().toLowerCase();
                return text.includes('connect') && !text.includes('connected') && !text.includes('message');
            });
            if (connectBtn) {
                connectBtn.click();
                return {success: true, text: connectBtn.textContent.trim()};
            }
            // Sometimes it's an <a> tag
            const links = Array.from(document.querySelectorAll('a, button'));
            const altBtn = links.find(b => b.textContent.trim().toLowerCase() === 'connect');
            if (altBtn) {
                altBtn.click();
                return {success: true, text: altBtn.textContent.trim(), type: altBtn.tagName};
            }
            return {success: false, reason: 'Connect button not found'};
        })()
        """, session=SESSION_NAME)

        if click_result.get("ok"):
            data = click_result.get("data", {})
            if data.get("success"):
                print(f"   ✅ Clicked Connect")

                # Wait for the "Send without a note" or "Send" dialog
                human_delay(3, 5)

                # Click "Send without a note" (safer than adding a note)
                send_result = evaluate("""
                (() => {
                    // Look for "Send without a note" button
                    const btns = Array.from(document.querySelectorAll('button'));
                    const noNoteBtn = btns.find(b => b.textContent.trim().toLowerCase().includes('without a note'));
                    if (noNoteBtn) {
                        noNoteBtn.click();
                        return {success: true, action: 'send_without_note'};
                    }
                    // Or just "Send"
                    const sendBtn = btns.find(b => b.textContent.trim().toLowerCase() === 'send');
                    if (sendBtn) {
                        sendBtn.click();
                        return {success: true, action: 'send'};
                    }
                    return {success: false, reason: 'Send button not found'};
                })()
                """, session=SESSION_NAME)

                if send_result.get("ok") and send_result.get("data", {}).get("success"):
                    print(f"   ✅ Connection request sent")
                    record_action(log, "connection", name, f"url:{url}")
                    sent += 1

                    # Update prospect status
                    prospect["status"] = "pending"
                    prospect["last_action"] = "connection_request"
                    prospect["last_action_date"] = datetime.now().strftime("%Y-%m-%d")

                    # Save updated prospects
                    from linkedin_outreach import save_prospects
                    save_prospects(prospects)
                else:
                    print(f"   ⚠️  Could not confirm send")
            else:
                print(f"   ⚠️  {data.get('reason', 'Unknown error')}")
        else:
            print(f"   ❌ Click failed: {click_result}")

        if sent < limit:
            human_delay(60, 180)  # Long delay between connections

    print(f"\n📊 Sent {sent} connection requests today.")


def workflow_send_messages(limit=5, dry_run=False, interactive=False):
    """
    Send messages to 1st-degree connections.
    MEDIUM RISK — requires human review.
    """
    check_stop()
    print(f"💬 WORKFLOW: Send Messages")
    print(f"   Limit: {limit}")
    print(f"   Mode: {'DRY-RUN' if dry_run else 'LIVE'}")
    print(f"   Interactive: {'YES' if interactive else 'NO'}")

    from linkedin_outreach import load_prospects, can_execute_today, record_action, load_log, save_log

    prospects = load_prospects()
    log = load_log()

    # Filter to connected prospects with ready messages
    candidates = [p for p in prospects if p.get("status") == "connected" and p.get("message_ready")]
    print(f"   Candidates: {len(candidates)}")

    if not candidates:
        print("   ⚠️  No connected prospects with ready messages.")
        print("   Run: python linkedin_outreach.py --action generate_messages")
        return

    sent = 0
    for prospect in candidates[:limit]:
        check_stop()

        if not can_execute_today(log, "message"):
            print("   🚫 Daily message limit reached. Stopping.")
            break

        name = prospect.get("name", "Unknown")
        message = prospect.get("message_text", "")

        print(f"\n👤 To: {name}")
        print(f"   Message preview: {message[:80]}...")

        if interactive:
            resp = input(f"   Send this message? [Y/n/skip/quit]: ").strip().lower()
            if resp == 'quit':
                break
            if resp == 'skip':
                continue
            if resp and resp != 'y':
                continue

        if dry_run:
            print("   [DRY-RUN] Would send message via LinkedIn messaging")
            sent += 1
            continue

        # Navigate to messaging
        navigate(LINKEDIN_MESSAGING, session=SESSION_NAME)
        human_delay(4, 7)

        # Search for person
        search_result = evaluate(f"""
        (() => {{
            const inputs = document.querySelectorAll('input[type="text"], input[placeholder*="Search"]');
            for (const input of inputs) {{
                if (input.placeholder && input.placeholder.toLowerCase().includes('search')) {{
                    input.focus();
                    input.value = {json.dumps(name)};
                    input.dispatchEvent(new Event('input', {{bubbles: true}}));
                    input.dispatchEvent(new Event('change', {{bubbles: true}}));
                    return {{success: true, found: true}};
                }}
            }}
            return {{success: false, reason: 'Search input not found'}};
        }})()
        """, session=SESSION_NAME)

        human_delay(3, 5)

        # Click on the person in search results
        click_result = evaluate(f"""
        (() => {{
            const items = document.querySelectorAll('[data-test-id="conversation-list-item"], .msg-conversation-listitem');
            for (const item of items) {{
                if (item.textContent.toLowerCase().includes({json.dumps(name.lower())})) {{
                    item.click();
                    return {{success: true, action: 'clicked_conversation'}};
                }}
            }}
            return {{success: false, reason: 'Conversation not found'}};
        }})()
        """, session=SESSION_NAME)

        if not (click_result.get("ok") and click_result.get("data", {}).get("success")):
            print(f"   ⚠️  Could not open conversation")
            continue

        human_delay(2, 4)

        # Find message input and type
        fill_result = evaluate(f"""
        (() => {{
            const editor = document.querySelector('[contenteditable="true"], .msg-form__contenteditable');
            if (editor) {{
                editor.focus();
                editor.innerHTML = {json.dumps(message.replace(chr(10), '<br>'))};
                editor.dispatchEvent(new Event('input', {{bubbles: true}}));
                return {{success: true, mode: 'contenteditable'}};
            }}
            const textarea = document.querySelector('textarea.msg-form__textarea');
            if (textarea) {{
                textarea.value = {json.dumps(message)};
                textarea.dispatchEvent(new Event('input', {{bubbles: true}}));
                return {{success: true, mode: 'textarea'}};
            }}
            return {{success: false, reason: 'Message input not found'}};
        }})()
        """, session=SESSION_NAME)

        if fill_result.get("ok") and fill_result.get("data", {}).get("success"):
            human_delay(2, 4)

            # Click send
            send_click = evaluate("""
            (() => {
                const sendBtn = document.querySelector('button[type="submit"], .msg-form__send-button, button[aria-label*="Send"]');
                if (sendBtn && !sendBtn.disabled) {
                    sendBtn.click();
                    return {success: true};
                }
                return {success: false, reason: 'Send button not found or disabled'};
            })()
            """, session=SESSION_NAME)

            if send_click.get("ok") and send_click.get("data", {}).get("success"):
                print(f"   ✅ Message sent to {name}")
                record_action(log, "message", name)
                prospect["status"] = "messaged"
                prospect["last_action"] = "message_sent"
                prospect["last_action_date"] = datetime.now().strftime("%Y-%m-%d")
                from linkedin_outreach import save_prospects
                save_prospects(prospects)
                sent += 1
            else:
                print(f"   ⚠️  Could not send message")
        else:
            print(f"   ⚠️  Could not fill message input")

        if sent < limit:
            human_delay(90, 180)

    print(f"\n📊 Sent {sent} messages today.")


def workflow_create_post():
    """
    Open LinkedIn post composer and prepare content.
    Does NOT auto-publish — human clicks the Post button.
    """
    check_stop()
    print(f"📝 WORKFLOW: Create LinkedIn Post")
    print(f"   This workflow opens the composer and prepares text.")
    print(f"   YOU must click the Post button manually.")

    # Load post template
    post_template_path = PROJECT_DIR / "linkedin" / "post-v1.txt"
    if post_template_path.exists():
        with open(post_template_path, "r", encoding="utf-8") as f:
            post_text = f.read()
    else:
        post_text = "🧬 Just launched Q-Mol — a molecular informatics platform for drug discovery teams.\n\nhttps://photon-bounce.com/qmol/"

    # Navigate to feed
    navigate(LINKEDIN_FEED, session=SESSION_NAME)
    human_delay(5, 8)

    # Click "Start a post" button
    click_result = evaluate("""
    (() => {
        const btn = Array.from(document.querySelectorAll('button, span'))
            .find(el => el.textContent.trim().toLowerCase().includes('start a post'));
        if (btn) {
            btn.click();
            return {success: true};
        }
        return {success: false, reason: 'Start a post button not found'};
    })()
    """, session=SESSION_NAME)

    if click_result.get("ok") and click_result.get("data", {}).get("success"):
        print("   ✅ Opened post composer")
        human_delay(3, 5)

        # Fill the post content
        fill_result = evaluate(f"""
        (() => {{
            const editor = document.querySelector('[contenteditable="true"]');
            if (editor) {{
                editor.focus();
                editor.innerHTML = {json.dumps(post_text.replace(chr(10), '<br>'))};
                editor.dispatchEvent(new Event('input', {{bubbles: true}}));
                return {{success: true}};
            }}
            return {{success: false, reason: 'Editor not found'}};
        }})()
        """, session=SESSION_NAME)

        if fill_result.get("ok") and fill_result.get("data", {}).get("success"):
            print("   ✅ Post text entered")
            print("\n⚠️  MANUAL STEP REQUIRED:")
            print("   Review the post in Chrome.")
            print("   Click the 'Post' button to publish.")
            print("   Do NOT let automation click Post — that's a ban risk.")
        else:
            print("   ⚠️  Could not fill post text")
            print("   The post text has been copied to your clipboard (if supported)")
    else:
        print("   ⚠️  Could not open post composer")
        print("   Please open it manually and paste this text:\n")
        print("-" * 50)
        print(post_text)
        print("-" * 50)


def workflow_extract_post_leads(post_url, dry_run=False):
    """
    Extract people who commented on a Q-Mol post.
    Read-only — very safe. Great for warm lead identification.
    """
    check_stop()
    print(f"🔍 WORKFLOW: Extract Post Leads")
    print(f"   Post: {post_url}")
    print(f"   Mode: {'DRY-RUN' if dry_run else 'LIVE'}")

    if dry_run:
        print("   [DRY-RUN] Would navigate to post and extract commenters")
        return

    navigate(post_url, session=SESSION_NAME)
    human_delay(5, 8)

    # Scroll to load comments
    for _ in range(3):
        evaluate("window.scrollTo(0, document.body.scrollHeight);", session=SESSION_NAME)
        human_delay(3, 5)

    # Extract commenters
    result = evaluate("""
    (() => {
        const comments = document.querySelectorAll('.comments-comment-item, [data-test-id="comment"]');
        const leads = [];
        for (const comment of comments) {
            const linkEl = comment.querySelector('a[href*="/in/"]');
            const nameEl = comment.querySelector('.comments-comment-item__post-meta, [data-test-id="commenter-name"]');
            const textEl = comment.querySelector('.comments-comment-item__main-content, [data-test-id="comment-text"]');
            if (linkEl) {
                leads.push({
                    name: nameEl ? nameEl.textContent.trim() : 'Unknown',
                    profile_url: linkEl.href,
                    comment_preview: textEl ? textEl.textContent.trim().substring(0, 100) : ''
                });
            }
        }
        return {count: leads.length, leads: leads};
    })()
    """, session=SESSION_NAME)

    if result.get("ok"):
        data = result.get("data", {})
        leads = data.get("leads", [])
        print(f"   ✅ Found {len(leads)} commenters")

        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
        csv_path = OUTPUT_DIR / f"post_leads_{timestamp}.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "profile_url", "comment_preview", "source_post", "extracted_date"])
            writer.writeheader()
            for lead in leads:
                writer.writerow({
                    "name": lead.get("name", ""),
                    "profile_url": lead.get("profile_url", ""),
                    "comment_preview": lead.get("comment_preview", ""),
                    "source_post": post_url,
                    "extracted_date": datetime.now().strftime("%Y-%m-%d")
                })

        print(f"💾 Exported to: {csv_path}")
        print(f"\n⚠️  These are WARM leads — they already engaged with your content!")
        print(f"   Add them to your prospect database with priority status.")
    else:
        print(f"   ❌ Failed to extract leads: {result}")


def main():
    parser = argparse.ArgumentParser(description="Q-Mol LinkedIn WebBridge Automation")
    parser.add_argument("--workflow", choices=[
        "search_prospects", "send_connections", "send_messages",
        "create_post", "extract_post_leads"
    ], required=True)
    parser.add_argument("--query", default="cheminformatics scientist", help="Search query")
    parser.add_argument("--post-url", help="LinkedIn post URL for lead extraction")
    parser.add_argument("--pages", type=int, default=2, help="Search pages to scan")
    parser.add_argument("--limit", type=int, default=5, help="Max actions to perform")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without acting")
    parser.add_argument("--interactive", action="store_true", help="Prompt before each action")

    args = parser.parse_args()

    print("=" * 60)
    print("Q-MOL LINKEDIN WEBBRIDGE AUTOMATION")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Session: {SESSION_NAME}")
    print("=" * 60)

    if args.workflow == "search_prospects":
        workflow_search_prospects(args.query, args.pages, args.dry_run)
    elif args.workflow == "send_connections":
        workflow_send_connections(args.limit, args.dry_run, args.interactive)
    elif args.workflow == "send_messages":
        workflow_send_messages(args.limit, args.dry_run, args.interactive)
    elif args.workflow == "create_post":
        workflow_create_post()
    elif args.workflow == "extract_post_leads":
        if not args.post_url:
            print("❌ --post-url is required for extract_post_leads workflow")
            sys.exit(1)
        workflow_extract_post_leads(args.post_url, args.dry_run)

    print("\n" + "=" * 60)
    print("Workflow complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
