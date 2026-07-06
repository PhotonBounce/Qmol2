"""
LinkedIn Messenger — High-level messaging operations via WebBridge.
Handles navigating to profiles, finding message buttons, composing, and sending.
"""
import time
import random
import re
from typing import Optional, Dict, Any
from linkedin_automation import LinkedInBot, LinkedInAutomationError
from message_templates import generate_message, generate_connection_note
from safety_config import OutreachTracker, OutreachRecord, check_operating_hours
from datetime import datetime


class LinkedInMessenger:
    """
    High-level LinkedIn messenger with safety-first automation.
    Uses accessibility tree (@e refs) to avoid brittle CSS selectors.
    """

    def __init__(self, tracker: Optional[OutreachTracker] = None):
        self.bot = LinkedInBot(
            daily_message_limit=12,
            daily_connection_limit=8,
            min_delay_seconds=45,
            max_delay_seconds=180,
            message_cooldown_minutes=random.randint(3, 8),
        )
        self.tracker = tracker or OutreachTracker()

    def _find_in_snapshot(self, snapshot: Dict, pattern: str, role: Optional[str] = None) -> Optional[str]:
        """Find an @e ref by text pattern in the accessibility tree."""
        tree = snapshot.get("tree", "")
        lines = tree.split("\n")
        for line in lines:
            if pattern.lower() in line.lower():
                if role and role.lower() not in line.lower():
                    continue
                match = re.search(r"@e(\d+)", line)
                if match:
                    return f"@e{match.group(1)}"
        return None

    def _wait_for_element(self, pattern: str, role: Optional[str] = None, timeout: int = 15) -> Optional[str]:
        """Poll snapshot until element appears."""
        for _ in range(timeout):
            snap = self.bot.snapshot()
            ref = self._find_in_snapshot(snap, pattern, role)
            if ref:
                return ref
            time.sleep(1)
        return None

    def navigate_to_profile(self, profile_url: str) -> bool:
        """Navigate to a LinkedIn profile and verify load."""
        print(f"[Q-MOL] Navigating to: {profile_url}")
        self.bot.navigate(profile_url)
        time.sleep(random.uniform(3, 6))

        snap = self.bot.snapshot()
        tree = snap.get("tree", "")

        # Check for common LinkedIn profile indicators
        if "profile" in tree.lower() or "connect" in tree.lower() or "message" in tree.lower():
            print("[Q-MOL] Profile loaded successfully.")
            return True

        # Check for rate limit / verification wall
        if "verify" in tree.lower() or "captcha" in tree.lower() or "security" in tree.lower():
            print("[Q-MOL] WARNING: LinkedIn showing verification wall. STOPPING.")
            return False

        print("[Q-MOL] Profile may not have loaded fully. Proceeding with caution.")
        return True

    def send_message(self, profile_url: str, name: str, target_type: str, topic: str, company: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a personalized message to a LinkedIn connection.
        Returns result dict with status.
        """
        result = {"status": "failed", "error": None, "message": None}

        # Pre-flight checks
        if not check_operating_hours():
            result["error"] = "Outside operating hours or weekend."
            return result

        if not self.tracker.can_send_message():
            result["error"] = f"Daily message limit reached."
            return result

        if self.tracker.was_contacted(profile_url, days=14):
            result["error"] = "Already contacted this person within 14 days."
            return result

        # Generate message
        message_text = generate_message(
            name=name,
            target_type=target_type,
            topic=topic,
            company=company,
        )
        result["message"] = message_text

        # Navigate
        if not self.navigate_to_profile(profile_url):
            result["error"] = "Failed to load profile or verification wall detected."
            self._log(profile_url, name, "message", message_text, target_type, topic, "failed", result["error"])
            return result

        # Find and click Message button
        snap = self.bot.snapshot()
        msg_ref = self._find_in_snapshot(snap, "message", role="button")

        if not msg_ref:
            # Try alternate labels
            for label in ["send message", "messages", "messaging"]:
                msg_ref = self._find_in_snapshot(snap, label)
                if msg_ref:
                    break

        if not msg_ref:
            result["error"] = "Could not find Message button - may not be connected yet."
            self._log(profile_url, name, "message", message_text, target_type, topic, "failed", result["error"])
            return result

        print(f"[Q-MOL] Clicking Message button ({msg_ref})...")
        try:
            self.bot.click(msg_ref)
        except LinkedInAutomationError as e:
            result["error"] = f"Click failed: {e}"
            self._log(profile_url, name, "message", message_text, target_type, topic, "failed", result["error"])
            return result

        time.sleep(random.uniform(2, 5))

        # Find message input area (contenteditable or textarea)
        snap = self.bot.snapshot()
        input_ref = None

        # Try contenteditable first (LinkedIn's rich text editor)
        for pattern in ["Write a message", "message", "Type a message"]:
            input_ref = self._find_in_snapshot(snap, pattern)
            if input_ref:
                break

        if not input_ref:
            result["error"] = "Could not find message input field."
            self._log(profile_url, name, "message", message_text, target_type, topic, "failed", result["error"])
            return result

        print(f"[Q-MOL] Filling message ({input_ref})...")
        try:
            self.bot.fill(input_ref, message_text)
        except LinkedInAutomationError as e:
            result["error"] = f"Fill failed: {e}"
            self._log(profile_url, name, "message", message_text, target_type, topic, "failed", result["error"])
            return result

        time.sleep(random.uniform(2, 4))

        # Find and click Send
        snap = self.bot.snapshot()
        send_ref = self._find_in_snapshot(snap, "send", role="button")

        if not send_ref:
            # Try by aria or other patterns
            for pattern in ["send message", "submit"]:
                send_ref = self._find_in_snapshot(snap, pattern)
                if send_ref:
                    break

        if not send_ref:
            result["error"] = "Could not find Send button."
            self._log(profile_url, name, "message", message_text, target_type, topic, "failed", result["error"])
            return result

        print(f"[Q-MOL] Clicking Send ({send_ref})...")
        try:
            self.bot.click(send_ref)
        except LinkedInAutomationError as e:
            result["error"] = f"Send click failed: {e}"
            self._log(profile_url, name, "message", message_text, target_type, topic, "failed", result["error"])
            return result

        # Confirm sent
        time.sleep(random.uniform(2, 4))
        result["status"] = "sent"
        print(f"[Q-MOL] Message sent to {name}!")

        self._log(profile_url, name, "message", message_text, target_type, topic, "sent")
        return result

    def send_connection_request(self, profile_url: str, name: str, target_type: str, topic: str, company: Optional[str] = None) -> Dict[str, Any]:
        """Send a connection request with personalized note."""
        result = {"status": "failed", "error": None, "note": None}

        if not check_operating_hours():
            result["error"] = "Outside operating hours or weekend."
            return result

        if not self.tracker.can_send_connection():
            result["error"] = "Daily connection limit reached."
            return result

        if self.tracker.was_contacted(profile_url, days=30):
            result["error"] = "Already contacted this person within 30 days."
            return result

        note = generate_connection_note(name=name, target_type=target_type, topic=topic)
        result["note"] = note

        if not self.navigate_to_profile(profile_url):
            result["error"] = "Failed to load profile."
            self._log(profile_url, name, "connection", note, target_type, topic, "failed", result["error"])
            return result

        snap = self.bot.snapshot()
        connect_ref = self._find_in_snapshot(snap, "connect", role="button")

        if not connect_ref:
            # May already be connected
            msg_ref = self._find_in_snapshot(snap, "message", role="button")
            if msg_ref:
                result["error"] = "Already connected - use send_message instead."
                self._log(profile_url, name, "connection", note, target_type, topic, "failed", result["error"])
                return result
            result["error"] = "Could not find Connect button."
            self._log(profile_url, name, "connection", note, target_type, topic, "failed", result["error"])
            return result

        print(f"[Q-MOL] Clicking Connect ({connect_ref})...")
        try:
            self.bot.click(connect_ref)
        except LinkedInAutomationError as e:
            result["error"] = f"Connect click failed: {e}"
            self._log(profile_url, name, "connection", note, target_type, topic, "failed", result["error"])
            return result

        time.sleep(random.uniform(2, 4))

        # LinkedIn may show "Add a note" dialog
        snap = self.bot.snapshot()
        add_note_ref = self._find_in_snapshot(snap, "add a note")

        if add_note_ref:
            print("[Q-MOL] Clicking 'Add a note'...")
            self.bot.click(add_note_ref)
            time.sleep(random.uniform(1, 3))

            snap = self.bot.snapshot()
            text_ref = self._find_in_snapshot(snap, "textarea")
            if not text_ref:
                text_ref = self._find_in_snapshot(snap, "note")

            if text_ref:
                self.bot.fill(text_ref, note)
                time.sleep(random.uniform(1, 3))

                # Find and click Send
                snap = self.bot.snapshot()
                send_ref = self._find_in_snapshot(snap, "send", role="button")
                if send_ref:
                    self.bot.click(send_ref)
                    time.sleep(random.uniform(2, 4))

        result["status"] = "sent"
        print(f"[Q-MOL] Connection request sent to {name}!")
        self._log(profile_url, name, "connection", note, target_type, topic, "sent")
        return result

    def _log(self, url, name, action, message, target_type, topic, status, error=None):
        record = OutreachRecord(
            timestamp=datetime.now().isoformat(),
            action=action,
            linkedin_url=url,
            name=name,
            message_sent=message,
            target_type=target_type,
            topic=topic,
            status=status,
            error=error,
        )
        self.tracker.add(record)

    def get_stats(self) -> Dict[str, Any]:
        return self.tracker.get_stats()
