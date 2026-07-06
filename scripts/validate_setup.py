"""
Validate Q-Mol LinkedIn automation setup.
Checks WebBridge, Python deps, and directory structure.
"""
import sys
import os
import requests

WEBBRIDGE_URL = "http://127.0.0.1:10086/command"


def check_webbridge() -> bool:
    """Check if WebBridge daemon is responding."""
    print("Checking WebBridge daemon...")
    try:
        resp = requests.post(
            WEBBRIDGE_URL,
            json={"action": "list_tabs", "args": {}, "session": "qmol-test"},
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("ok"):
                print("  [OK] WebBridge daemon is running")
                return True
        print(f"  [FAIL] WebBridge returned: {resp.status_code}")
        return False
    except requests.exceptions.ConnectionError:
        print("  [FAIL] Cannot connect to WebBridge at 127.0.0.1:10086")
        print("    Start it with:")
        print("    & $env:USERPROFILE\\.kimi-webbridge\\bin\\kimi-webbridge.exe start")
        return False


def check_modules() -> bool:
    """Check that all required modules are importable."""
    print("Checking Python modules...")
    linkedin_dir = os.path.join(os.path.dirname(__file__), "..", "linkedin")
    sys.path.insert(0, linkedin_dir)

    all_ok = True
    modules = [
        "linkedin_automation",
        "linkedin_messenger",
        "message_templates",
        "safety_config",
        "campaign_manager",
        "targets",
    ]
    for mod in modules:
        try:
            __import__(mod)
            print(f"  [OK] {mod}")
        except Exception as e:
            print(f"  [FAIL] {mod}: {e}")
            all_ok = False
    return all_ok


def check_directories() -> bool:
    """Check required directories exist."""
    print("Checking directories...")
    dirs = [
        "D:/Qmol-3/scripts",
        "D:/Qmol-3/linkedin",
    ]
    all_ok = True
    for d in dirs:
        if os.path.isdir(d):
            print(f"  [OK] {d}")
        else:
            print(f"  [MISSING] {d}")
            all_ok = False
    return all_ok


def main():
    print("=" * 50)
    print("Q-MOL LINKEDIN AUTOMATION SETUP VALIDATOR")
    print("=" * 50)

    results = []
    results.append(("WebBridge", check_webbridge()))
    results.append(("Modules", check_modules()))
    results.append(("Directories", check_directories()))

    print("\n" + "=" * 50)
    if all(r[1] for r in results):
        print("ALL CHECKS PASSED -- Ready for outreach!")
    else:
        print("SOME CHECKS FAILED -- Fix issues before running.")
    print("=" * 50)


if __name__ == "__main__":
    main()
