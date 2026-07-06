"""
LinkedIn Message Automation for Q-Mol
Core WebBridge client for safe browser automation.
"""
import requests
import json
import time
import random
import os
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta


class LinkedInAutomationError(Exception):
    pass


class LinkedInBot:
    """
    Safe LinkedIn automation via Kimi WebBridge.
    Implements strict rate limiting and human-like behavior.
    """

    WEBBRIDGE_URL = "http://127.0.0.1:10086/command"
    SESSION_NAME = "qmol-linkedin-outreach"

    def __init__(
        self,
        daily_message_limit: int = 15,
        daily_connection_limit: int = 10,
        min_delay_seconds: float = 45.0,
        max_delay_seconds: float = 180.0,
        message_cooldown_minutes: int = 3,
    ):
        self.daily_message_limit = daily_message_limit
        self.daily_connection_limit = daily_connection_limit
        self.min_delay = min_delay_seconds
        self.max_delay = max_delay_seconds
        self.message_cooldown = message_cooldown_minutes
        self.last_action_time: Optional[datetime] = None
        self.actions_today = 0
        self.messages_today = 0
        self.connections_today = 0
        self._today = datetime.now().date()

    def _reset_counters_if_new_day(self):
        today = datetime.now().date()
        if today != self._today:
            self._today = today
            self.actions_today = 0
            self.messages_today = 0
            self.connections_today = 0
            print(f"[Q-MOL] New day: counters reset ({today})")

    def _random_delay(self, min_sec: Optional[float] = None, max_sec: Optional[float] = None):
        """Human-like randomized delay."""
        min_s = min_sec or self.min_delay
        max_s = max_sec or self.max_delay
        delay = random.uniform(min_s, max_s)
        if self.last_action_time:
            elapsed = (datetime.now() - self.last_action_time).total_seconds()
            if elapsed < delay:
                extra = delay - elapsed
                print(f"[Q-MOL] Waiting {extra:.1f}s...")
                time.sleep(extra)
        self.last_action_time = datetime.now()

    def _send_command(self, action: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Send a WebBridge command."""
        payload = {
            "action": action,
            "args": args,
            "session": self.SESSION_NAME,
        }
        try:
            resp = requests.post(
                self.WEBBRIDGE_URL,
                json=payload,
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            if not data.get("ok") and data.get("error"):
                raise LinkedInAutomationError(
                    f"WebBridge error: {data['error']}"
                )
            return data
        except requests.exceptions.ConnectionError:
            raise LinkedInAutomationError(
                "Cannot connect to WebBridge at 127.0.0.1:10086. "
                "Please start the daemon first."
            )

    def navigate(self, url: str, new_tab: bool = False) -> str:
        """Navigate to a URL."""
        self._reset_counters_if_new_day()
        result = self._send_command(
            "navigate",
            {"url": url, "newTab": new_tab, "group_title": "Q-Mol Outreach"},
        )
        time.sleep(random.uniform(2, 4))
        return result.get("url", url)

    def snapshot(self) -> Dict[str, Any]:
        """Get page accessibility tree."""
        return self._send_command("snapshot", {})

    def click(self, selector: str) -> Dict[str, Any]:
        """Click an element by @e ref or CSS selector."""
        self._random_delay(min_sec=1.5, max_sec=4)
        return self._send_command("click", {"selector": selector})

    def fill(self, selector: str, value: str) -> Dict[str, Any]:
        """Fill an input or contenteditable element."""
        self._random_delay(min_sec=1, max_sec=3)
        return self._send_command("fill", {"selector": selector, "value": value})

    def evaluate(self, code: str) -> Any:
        """Execute JS on the page."""
        result = self._send_command("evaluate", {"code": code})
        return result.get("value")

    def screenshot(self, path: Optional[str] = None) -> str:
        """Take a screenshot."""
        args = {}
        if path:
            args["path"] = path
        result = self._send_command("screenshot", args)
        return result.get("path", "")

    def list_tabs(self) -> List[Dict[str, Any]]:
        """List open tabs."""
        result = self._send_command("list_tabs", {})
        return result.get("tabs", [])

    def close_session(self) -> int:
        """Close all tabs in the session."""
        result = self._send_command("close_session", {})
        return result.get("closed", 0)

    def check_limits(self) -> bool:
        """Check if we've hit daily limits."""
        self._reset_counters_if_new_day()
        total = self.messages_today + self.connections_today
        limit = self.daily_message_limit + self.daily_connection_limit
        if total >= limit:
            print(
                f"[Q-MOL] DAILY LIMIT REACHED: {total}/{limit} "
                f"(messages: {self.messages_today}, connections: {self.connections_today})"
            )
            return False
        return True

    def wait_for_cooldown(self):
        """Ensure minimum time between messages."""
        if self.last_action_time:
            elapsed = (datetime.now() - self.last_action_time).total_seconds()
            cooldown = self.message_cooldown * 60
            if elapsed < cooldown:
                wait = cooldown - elapsed
                print(f"[Q-MOL] Cooldown: waiting {wait:.0f}s...")
                time.sleep(wait)

    def scroll_page(self, direction: str = "down", amount: int = 500):
        """Scroll the page like a human."""
        code = f"window.scrollBy({{top: {'-' if direction == 'up' else ''}{amount}, behavior: 'smooth'}})"
        self.evaluate(code)
        time.sleep(random.uniform(1, 3))
