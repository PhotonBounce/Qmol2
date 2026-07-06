"""
cPanel Integration for Q-Mol
Check website status, disk usage, and email via cPanel UAPI.
"""
import requests
import json
from typing import Dict, Optional

# cPanel credentials
CPANEL_HOST = "photon-bounce.com"
CPANEL_USER = "photonb"
CPANEL_TOKEN = "OYOQ3JK7HI9C6CNO84T0RH8JUKHHIBZ1"
BASE_URL = f"https://{CPANEL_HOST}:2083"

HEADERS = {
    "Authorization": f"cpanel {CPANEL_USER}:{CPANEL_TOKEN}",
}


def cpanel_uapi(module: str, function: str, params: Optional[Dict] = None) -> Dict:
    """Call cPanel UAPI endpoint."""
    url = f"{BASE_URL}/execute/{module}/{function}"
    try:
        resp = requests.get(url, headers=HEADERS, params=params or {}, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        return {"status": 0, "errors": [str(e)]}


def get_domain_info() -> Dict:
    """Get domain status and info."""
    return cpanel_uapi("DomainInfo", "list_domains")


def get_disk_usage() -> Dict:
    """Get disk usage statistics."""
    return cpanel_uapi("Quota", "get_local_quota")


def get_email_accounts() -> Dict:
    """List email accounts."""
    return cpanel_uapi("Email", "list_pops")


def get_last_login() -> Dict:
    """Get last login info."""
    return cpanel_uapi("LastLogin", "get_last_logins")


def check_website_online() -> bool:
    """Check if Q-Mol website is responding."""
    try:
        resp = requests.get("https://photon-bounce.com/qmol/", timeout=15)
        return resp.status_code == 200
    except requests.exceptions.RequestException:
        return False


def main():
    print("=" * 50)
    print("Q-MOL cPANEL STATUS CHECK")
    print("=" * 50)

    print("\n[1] Website status...")
    if check_website_online():
        print("  ✓ https://photon-bounce.com/qmol/ is ONLINE")
    else:
        print("  ✗ Website appears offline or unreachable")

    print("\n[2] Disk usage...")
    disk = get_disk_usage()
    if disk.get("status"):
        used = disk.get("bytes_used", 0)
        limit = disk.get("byte_limit", 1)
        pct = (used / limit) * 100 if limit else 0
        print(f"  Used: {used / 1024 / 1024:.1f} MB / {limit / 1024 / 1024:.1f} MB ({pct:.1f}%)")
    else:
        print(f"  Error: {disk.get('errors', ['Unknown'])}")

    print("\n[3] Domains...")
    domains = get_domain_info()
    if domains.get("status"):
        main = domains.get("data", {}).get("main_domain", "N/A")
        print(f"  Main domain: {main}")
        add_ons = domains.get("data", {}).get("addon_domains", [])
        if add_ons:
            print(f"  Addon domains: {', '.join(add_ons)}")
    else:
        print(f"  Error: {domains.get('errors', ['Unknown'])}")

    print("\n[4] Email accounts...")
    emails = get_email_accounts()
    if emails.get("status"):
        accounts = emails.get("data", [])
        print(f"  Found {len(accounts)} email account(s)")
        for acc in accounts[:5]:
            print(f"    - {acc.get('email', 'unknown')}")
    else:
        print(f"  Error: {emails.get('errors', ['Unknown'])}")

    print("\n" + "=" * 50)


if __name__ == "__main__":
    main()
