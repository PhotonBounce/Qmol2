#!/usr/bin/env python3
"""
Q-Mol WebBridge Driver
Python interface for controlling Chrome via Kimi WebBridge.
Handles LinkedIn automation, browser actions, and screenshot capture.

Usage:
    python webbridge_driver.py --action navigate --url "https://linkedin.com"
    python webbridge_driver.py --action click --selector "button.submit"
    python webbridge_driver.py --action fill --selector "input.email" --value "test@example.com"
    python webbridge_driver.py --action screenshot --output linkedin.png
    python webbridge_driver.py --action scroll --amount 500
"""

import json
import requests
import time
import base64
import argparse
from pathlib import Path

WEBBRIDGE_URL = "http://127.0.0.1:10086/command"
DEFAULT_SESSION = "qmol-automation"


def send_command(action, args, session=DEFAULT_SESSION):
    """Send a command to the WebBridge daemon."""
    payload = {
        "action": action,
        "args": args,
        "session": session
    }
    try:
        resp = requests.post(WEBBRIDGE_URL, json=payload, timeout=20)
        return resp.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}


def navigate(url, session=DEFAULT_SESSION, new_tab=False):
    """Navigate to a URL."""
    result = send_command("navigate", {"url": url, "newTab": new_tab}, session)
    if result.get("ok"):
        print(f"✅ Navigated to: {url}")
    else:
        print(f"❌ Navigate failed: {result}")
    return result


def snapshot(session=DEFAULT_SESSION):
    """Get page snapshot."""
    return send_command("snapshot", {}, session)


def click(selector, session=DEFAULT_SESSION):
    """Click an element."""
    result = send_command("click", {"selector": selector}, session)
    if result.get("ok"):
        print(f"✅ Clicked: {selector}")
    else:
        print(f"❌ Click failed: {result}")
    return result


def fill(selector, value, session=DEFAULT_SESSION):
    """Fill an input field."""
    result = send_command("fill", {"selector": selector, "value": value}, session)
    if result.get("ok"):
        print(f"✅ Filled: {selector}")
    else:
        print(f"❌ Fill failed: {result}")
    return result


def evaluate(code, session=DEFAULT_SESSION):
    """Execute JavaScript."""
    return send_command("evaluate", {"code": code}, session)


def screenshot(output_path=None, session=DEFAULT_SESSION):
    """Take a screenshot."""
    result = send_command("screenshot", {}, session)
    if result.get("ok"):
        data = result.get("data", {})
        if data.get("path"):
            print(f"✅ Screenshot saved: {data['path']}")
            if output_path:
                # Copy to desired location
                import shutil
                shutil.copy(data["path"], output_path)
                print(f"✅ Copied to: {output_path}")
        return data
    else:
        print(f"❌ Screenshot failed: {result}")
    return result


def scroll(amount=500, session=DEFAULT_SESSION):
    """Scroll the page."""
    code = f"window.scrollTo(0, {amount});"
    return evaluate(code, session)


def find_element_by_text(text, session=DEFAULT_SESSION):
    """Find element by text content."""
    code = f"(() => {{ const all = document.querySelectorAll('*'); for (const el of all) {{ if (el.textContent && el.textContent.trim() === '{text}') {{ return {{found: true, tag: el.tagName, class: el.className?.substring(0,50)}}; }} }} return {{found: false}}; }})()"
    return evaluate(code, session)


def click_by_text(text, session=DEFAULT_SESSION):
    """Click element by text content."""
    code = f"(() => {{ const all = document.querySelectorAll('*'); for (const el of all) {{ if (el.textContent && el.textContent.trim() === '{text}') {{ el.click(); return 'CLICKED'; }} }} return 'NOT_FOUND'; }})()"
    return evaluate(code, session)


def linkedin_connect(name, session="linkedin-qmol"):
    """Send a LinkedIn connection request."""
    # Navigate to profile
    navigate(f"https://www.linkedin.com/search/results/people/?keywords={name.replace(' ', '%20')}", session)
    time.sleep(3)
    
    # Click Connect button
    result = click_by_text("Connect", session)
    if result.get("ok") and result.get("data", {}).get("value") == "CLICKED":
        time.sleep(2)
        # Send without note (safer)
        send_result = click_by_text("Send", session)
        print(f"Connection request sent to {name}")
        return send_result
    return result


def linkedin_send_message(name, message, session="linkedin-qmol"):
    """Send a LinkedIn message."""
    # Navigate to messaging
    navigate("https://www.linkedin.com/messaging/", session)
    time.sleep(2)
    
    # Search for person
    fill("input[placeholder*='Search']", name, session)
    time.sleep(2)
    
    # Click on person
    click_by_text(name, session)
    time.sleep(2)
    
    # Type message
    fill("[contenteditable=true]", message, session)
    time.sleep(1)
    
    # Send
    click_by_text("Send", session)
    print(f"Message sent to {name}")


def main():
    parser = argparse.ArgumentParser(description="Q-Mol WebBridge Driver")
    parser.add_argument("--action", choices=["navigate", "click", "fill", "screenshot", "scroll", "evaluate", "snapshot"], default="snapshot")
    parser.add_argument("--url", help="URL to navigate to")
    parser.add_argument("--selector", help="CSS selector")
    parser.add_argument("--value", help="Value to fill")
    parser.add_argument("--code", help="JavaScript code to execute")
    parser.add_argument("--amount", type=int, default=500, help="Scroll amount")
    parser.add_argument("--output", help="Screenshot output path")
    parser.add_argument("--session", default=DEFAULT_SESSION, help="WebBridge session name")
    
    args = parser.parse_args()
    
    if args.action == "navigate":
        navigate(args.url, args.session)
    elif args.action == "click":
        click(args.selector, args.session)
    elif args.action == "fill":
        fill(args.selector, args.value, args.session)
    elif args.action == "screenshot":
        screenshot(args.output, args.session)
    elif args.action == "scroll":
        scroll(args.amount, args.session)
    elif args.action == "evaluate":
        evaluate(args.code, args.session)
    elif args.action == "snapshot":
        result = snapshot(args.session)
        print(json.dumps(result, indent=2)[:500])


if __name__ == "__main__":
    main()
