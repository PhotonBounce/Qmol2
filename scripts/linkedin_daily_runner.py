#!/usr/bin/env python3
"""
Q-Mol LinkedIn Daily Batch Runner
=================================
Runs the daily automation routine with optional scheduling.
Logs everything and sends alerts if issues occur.

Usage:
    # Run once immediately
    python linkedin_daily_runner.py --run-now

    # Schedule daily at 10:00 AM (via cron/task scheduler)
    python linkedin_daily_runner.py --schedule 10:00

    # Check what would run today (dry run)
    python linkedin_daily_runner.py --dry-run

    # View last run report
    python linkedin_daily_runner.py --report
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
DATA_DIR = PROJECT_DIR / "data" / "linkedin"
REPORT_FILE = DATA_DIR / "daily_run_report.json"
SCHEDULE_FILE = DATA_DIR / "schedule.json"
AUTOMATION_SCRIPT = PROJECT_DIR / "scripts" / "linkedin_safe_automation.py"


def ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_report() -> dict:
    if not REPORT_FILE.exists():
        return {"runs": [], "last_run": None, "total_successful_actions": 0}
    with open(REPORT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_report(report: dict):
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


def run_daily(dry_run: bool = False) -> dict:
    """Execute the daily automation routine and capture results."""
    ensure_dirs()
    report = load_report()

    run_record = {
        "timestamp": datetime.now().isoformat(),
        "dry_run": dry_run,
        "status": "started",
        "actions": {},
        "errors": [],
    }

    print(f"\n{'='*60}")
    print(f"Q-MOL LINKEDIN DAILY BATCH")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"{'='*60}\n")

    # Check WebBridge is running
    import requests
    try:
        resp = requests.get("http://127.0.0.1:10086/", timeout=5)
        print("✅ WebBridge daemon is running\n")
    except Exception:
        print("⚠️  WebBridge daemon not detected. Attempting to start...")
        # Try to start WebBridge
        webbridge_path = Path.home() / ".kimi-webbridge" / "bin" / "kimi-webbridge.exe"
        if webbridge_path.exists():
            try:
                subprocess.Popen([str(webbridge_path), "start"], shell=False)
                time.sleep(3)
                print("✅ WebBridge started\n")
            except Exception as e:
                print(f"❌ Could not start WebBridge: {e}")
                run_record["status"] = "failed"
                run_record["errors"].append(f"WebBridge not available: {e}")
                report["runs"].append(run_record)
                save_report(report)
                return run_record
        else:
            print("❌ WebBridge not found. Please start it manually.")
            run_record["status"] = "failed"
            run_record["errors"].append("WebBridge not found")
            report["runs"].append(run_record)
            save_report(report)
            return run_record

    # Run the automation script
    cmd = [sys.executable, str(AUTOMATION_SCRIPT), "--mode", "daily"]
    if dry_run:
        cmd.append("--dry-run")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1800,  # 30 minute max
        )
        output = result.stdout + result.stderr

        # Parse output for action counts
        actions_done = {
            "connections": output.count("Connection request sent"),
            "messages": output.count("Message sent"),
            "profile_views": output.count("Profile viewed"),
        }

        run_record["actions"] = actions_done
        run_record["output_snippet"] = output[-500:]  # last 500 chars

        if result.returncode == 0:
            run_record["status"] = "completed"
            total = sum(actions_done.values())
            report["total_successful_actions"] = report.get("total_successful_actions", 0) + total
            print(f"\n✅ Daily batch completed: {total} actions")
        else:
            run_record["status"] = "error"
            run_record["errors"].append(f"Exit code: {result.returncode}")
            print(f"\n⚠️ Daily batch exited with code {result.returncode}")

    except subprocess.TimeoutExpired:
        run_record["status"] = "timeout"
        run_record["errors"].append("Timeout after 30 minutes")
        print("\n❌ Daily batch timed out")
    except Exception as e:
        run_record["status"] = "failed"
        run_record["errors"].append(str(e))
        print(f"\n❌ Daily batch failed: {e}")

    report["runs"].append(run_record)
    report["last_run"] = run_record["timestamp"]

    # Keep only last 30 runs
    if len(report["runs"]) > 30:
        report["runs"] = report["runs"][-30:]

    save_report(report)

    print(f"\n{'='*60}")
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    return run_record


def print_report():
    """Print summary of recent runs."""
    report = load_report()

    print(f"\n{'='*60}")
    print(f"Q-MOL LINKEDIN DAILY RUN REPORT")
    print(f"{'='*60}")
    print(f"\nTotal Actions (all time): {report.get('total_successful_actions', 0)}")
    print(f"Last Run: {report.get('last_run', 'Never')}")

    runs = report.get("runs", [])
    if not runs:
        print("\nNo runs recorded yet.")
        return

    print(f"\nLast 7 Runs:")
    print(f"{'Date':<20} {'Status':<12} {'Conn':>6} {'Msg':>6} {'Views':>6}")
    print("-"*60)

    for run in runs[-7:]:
        ts = run.get("timestamp", "unknown")[:19]
        status = run.get("status", "unknown")
        acts = run.get("actions", {})
        print(
            f"{ts:<20} {status:<12} "
            f"{acts.get('connections', 0):>6} "
            f"{acts.get('messages', 0):>6} "
            f"{acts.get('profile_views', 0):>6}"
        )

    # Calculate weekly stats
    week_ago = datetime.now() - timedelta(days=7)
    week_runs = [r for r in runs if datetime.fromisoformat(r["timestamp"]) > week_ago]
    week_conn = sum(r.get("actions", {}).get("connections", 0) for r in week_runs)
    week_msg = sum(r.get("actions", {}).get("messages", 0) for r in week_runs)
    week_pv = sum(r.get("actions", {}).get("profile_views", 0) for r in week_runs)

    print(f"\n📅 LAST 7 DAYS SUMMARY:")
    print(f"  Connection requests: {week_conn}")
    print(f"  Messages sent:       {week_msg}")
    print(f"  Profile views:       {week_pv}")
    print(f"  Total actions:       {week_conn + week_msg + week_pv}")

    # Check for errors
    error_runs = [r for r in week_runs if r.get("status") not in ("completed", "started")]
    if error_runs:
        print(f"\n⚠️  Errors in last 7 days: {len(error_runs)}")
        for r in error_runs:
            print(f"  - {r['timestamp'][:19]}: {r.get('status')} - {r.get('errors', ['unknown'])[0]}")

    print(f"\n{'='*60}\n")


def setup_schedule(time_str: str):
    """Print instructions for setting up scheduled runs."""
    ensure_dirs()
    schedule = {"time": time_str, "enabled": True, "created": datetime.now().isoformat()}
    with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
        json.dump(schedule, f, indent=2)

    print(f"\n{'='*60}")
    print(f"SCHEDULE SETUP: Daily at {time_str}")
    print(f"{'='*60}\n")

    print("Windows Task Scheduler setup:")
    print(f"1. Open Task Scheduler (taskschd.msc)")
    print(f"2. Create Basic Task: 'Q-Mol LinkedIn Daily'")
    print(f"3. Trigger: Daily at {time_str}")
    print(f"4. Action: Start a program")
    print(f"5. Program: {sys.executable}")
    print(f"6. Arguments: {AUTOMATION_SCRIPT} --mode daily")
    print(f"7. Run whether user is logged on or not: NO (needs Chrome)")
    print(f"8. Run with highest privileges: NO")
    print()
    print("Alternative - Cron (if using WSL/Git Bash):")
    print(f"  0 10 * * * cd /d/Qmol-3 && python scripts/linkedin_safe_automation.py --mode daily")
    print()
    print("Alternative - Windows batch file:")
    batch_content = f"""@echo off
cd /d "D:\\Qmol-3"
python scripts\\linkedin_safe_automation.py --mode daily
"""
    batch_path = PROJECT_DIR / "scripts" / "linkedin_daily.bat"
    with open(batch_path, "w", encoding="utf-8") as f:
        f.write(batch_content)
    print(f"✅ Created: {batch_path}")
    print()
    print("RECOMMENDATION: Start with --dry-run for the first week!")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="Q-Mol LinkedIn Daily Batch Runner")
    parser.add_argument("--run-now", action="store_true", help="Run the daily batch immediately")
    parser.add_argument("--dry-run", action="store_true", help="Run in simulation mode")
    parser.add_argument("--report", action="store_true", help="Show run history report")
    parser.add_argument("--schedule", help="Set daily schedule time (e.g., 10:00)")

    args = parser.parse_args()
    ensure_dirs()

    if args.schedule:
        setup_schedule(args.schedule)
    elif args.report:
        print_report()
    elif args.run_now or args.dry_run:
        run_daily(dry_run=args.dry_run)
    else:
        print("Q-Mol LinkedIn Daily Runner")
        print("\nUsage:")
        print("  python linkedin_daily_runner.py --run-now        # Run now")
        print("  python linkedin_daily_runner.py --dry-run        # Simulate")
        print("  python linkedin_daily_runner.py --report         # View history")
        print("  python linkedin_daily_runner.py --schedule 10:00 # Setup schedule")


if __name__ == "__main__":
    main()
