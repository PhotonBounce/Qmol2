# Q-Mol LinkedIn WebBridge Automation Guide
## Safety-First Browser Automation for Molecular Dataset Sales

**Version:** 1.0.0  
**Date:** 2026-07-05  
**Author:** Q-Mol Automation Team  
**WebBridge Endpoint:** `http://127.0.0.1:10086`  
**User:** Dmitriy Buchman (already logged into LinkedIn in Chrome)

---

## Table of Contents

1. [Safety First — Read This](#1-safety-first--read-this)
2. [Architecture Overview](#2-architecture-overview)
3. [Quick Start](#3-quick-start)
4. [Core Scripts Reference](#4-core-scripts-reference)
5. [Daily Workflows](#5-daily-workflows)
6. [Troubleshooting](#6-troubleshooting)
7. [Rate Limits & Anti-Ban Rules](#7-rate-limits--anti-ban-rules)

---

## 1. Safety First — Read This

LinkedIn aggressively detects and bans automated behavior. **One mistake can get Dmitriy’s account restricted or permanently banned.**

### The Golden Rules

| Rule | Why It Matters |
|------|----------------|
| **Never exceed 15 connection requests per day** | LinkedIn flags accounts sending 20+ per day |
| **Never exceed 25 messages per day** | Message spam triggers immediate review |
| **Wait 45–180 seconds between any action** | Rapid-fire clicks = bot signature |
| **Only run during US business hours (9 AM–6 PM PDT)** | Off-hours activity looks automated |
| **Never send identical messages** | Duplicate content is a ban trigger |
| **Always use `snapshot()` before clicking** | CSS selectors break; accessibility trees survive |
| **Never automate profile views in bulk** | LinkedIn tracks view→connect ratios |
| **If you see a CAPTCHA, STOP immediately** | Continuing = automatic restriction |
| **Always keep a human in the loop** | Semi-automated, never fully unattended |

### What Gets Accounts Banned
- Sending 50+ connections in one sitting
- Copy-paste identical messages to 10+ people
- Using browser extensions that inject scripts into LinkedIn
- Logging in from a new IP/device after automation
- Automating endorsements, skill recommendations, or "reacting" to posts

### What Is Safe
- Opening LinkedIn in the already-logged-in Chrome tab
- Taking snapshots to read the page structure
- Clicking elements found via `@e` accessibility refs (human-like)
- Sending **pre-approved**, personalized messages one at a time
- Scheduling posts via LinkedIn’s native scheduler (not automation)

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Your Windows PC                          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Chrome    │◄──►│ WebBridge   │◄──►│  Python     │     │
│  │  (logged in │    │  Daemon     │    │  Scripts    │     │
│  │  as Dmitriy)│    │ :10086      │    │  (this dir) │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│         ▲                                              │     │
│         └──────────────────────────────────────────────┘     │
│                    (no headless browser — REAL Chrome)       │
└─────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴──────────┐
                    ▼                    ▼
            ┌──────────────┐    ┌──────────────┐
            │  LinkedIn    │    │ Q-Mol Data   │
            │  (LinkedIn   │    │ (prospects,  │
            │   sees real  │    │  messages,   │
            │   Chrome)    │    │  logs)       │
            └──────────────┘    └──────────────┘
```

**Why this is safer than Selenium/Puppeteer:**
- LinkedIn sees a **real Chrome browser** with Dmitriy’s real cookies, localStorage, and fingerprint
- No `navigator.webdriver` flag
- No headless detection vectors
- The WebBridge daemon injects minimal, event-level interactions

---

## 3. Quick Start

### Step 1: Verify WebBridge is Running

```powershell
# PowerShell
curl.exe -s http://127.0.0.1:10086/command `
  -H "Content-Type: application/json" `
  -d '{"action":"list_tabs","args":{},"session":"qmol-test"}'
```

If you get `Connection refused`, start the daemon:
```powershell
& "$env:USERPROFILE\.kimi-webbridge\bin\kimi-webbridge.exe" start
```

### Step 2: Test with a Safe Snapshot

```powershell
$body = '{"action":"navigate","args":{"url":"https://www.linkedin.com/feed/","newTab":true,"group_title":"Q-Mol Automation"},"session":"qmol-linkedin"}'
$tmp = "$env:TEMP\wb-test-$((Get-Random)).json"
$body | Out-File -Encoding utf8 -FilePath $tmp
curl.exe -s -X POST http://127.0.0.1:10086/command -H "Content-Type: application/json" --data-binary "@$tmp"
Remove-Item $tmp
```

Wait 5 seconds, then snapshot:
```powershell
$body = '{"action":"snapshot","args":{},"session":"qmol-linkedin"}'
$tmp = "$env:TEMP\wb-snap-$((Get-Random)).json"
$body | Out-File -Encoding utf8 -FilePath $tmp
curl.exe -s -X POST http://127.0.0.1:10086/command -H "Content-Type: application/json" --data-binary "@$tmp"
Remove-Item $tmp
```

### Step 3: Run a Safety-Guarded Action

```bash
cd D:\Qmol-3\scripts
python safety_guard.py --action snapshot --dry-run
```

---

## 4. Core Scripts Reference

### 4.1 `webbridge_driver.py` — Low-Level Browser Control

**Location:** `D:\Qmol-3\scripts\webbridge_driver.py`

Already exists. Provides:
- `navigate(url)` — open a page
- `snapshot()` — read accessibility tree (find `@e` refs)
- `click(selector)` — click an element
- `fill(selector, value)` — type into input/contenteditable
- `evaluate(code)` — run JavaScript
- `screenshot(path)` — capture viewport
- `scroll(amount)` — scroll the page

**Usage pattern:**
```python
from webbridge_driver import navigate, snapshot, click, fill

navigate("https://www.linkedin.com/messaging/", session="qmol-linkedin")
time.sleep(random.uniform(3, 6))
result = snapshot(session="qmol-linkedin")
# Look for @e refs in the tree, then click
time.sleep(random.uniform(45, 120))  # CRITICAL: human delay
```

### 4.2 `safety_guard.py` — Rate Limit Enforcer

**Location:** `D:\Qmol-3\scripts\safety_guard.py`

**This is your safety net.** Every automation script must route through this.

Features:
- Daily connection cap (default: 12, hard max: 15)
- Daily message cap (default: 20, hard max: 25)
- Minimum delay between actions (default: 60s)
- Business-hours-only enforcement
- Action logging with timestamps
- Dry-run mode (simulate without sending)
- Emergency STOP file (`D:\Qmol-3\scripts\STOP.txt`)

**Usage:**
```bash
# Check status
python safety_guard.py --status

# Dry-run a connection request
python safety_guard.py --action connect --prospect "John Doe" --dry-run

# Actually send (only if under limits)
python safety_guard.py --action connect --prospect "John Doe"

# Emergency stop (creates STOP.txt)
python safety_guard.py --stop
```

### 4.3 `linkedin_outreach.py` — Prospect & Message Manager

**Location:** `D:\Qmol-3\scripts\linkedin_outreach.py`

Already exists. Manages:
- Prospect CSV database (`D:\Qmol-3\data\linkedin\prospects.csv`)
- Personalized message generation from templates
- Outreach log (`D:\Qmol-3\data\linkedin\outreach_log.json`)
- Daily action tracking

**Usage:**
```bash
# View dashboard
python linkedin_outreach.py --action status

# Add a prospect
python linkedin_outreach.py --action add_prospect --name "Jane Smith" --title "Principal Scientist" --company "BioTech Inc" --url "https://linkedin.com/in/janesmith"

# Generate personalized messages for all new prospects
python linkedin_outreach.py --action generate_messages

# Export ready-to-send messages (human copy-paste workflow)
python linkedin_outreach.py --action execute_daily --limit 5
```

### 4.4 `webbridge_linkedin_automation.py` — High-Level Automation

**Location:** `D:\Qmol-3\scripts\webbridge_linkedin_automation.py`

Orchestrates WebBridge + Safety Guard + Outreach Manager into safe, semi-automated workflows.

**Key Workflows:**

| Workflow | Description | Safety Level |
|----------|-------------|--------------|
| `search_prospects` | Runs a LinkedIn search, exports names/URLs to CSV | Safe — read-only |
| `send_connections` | Sends connection requests from prospect list | Medium — requires human review |
| `send_messages` | Sends messages to 1st-degree connections | Medium — requires human review |
| `create_post` | Assists with post creation (does NOT auto-publish) | Safe — human clicks publish |
| `extract_post_leads` | Reads comments on a Q-Mol post for warm leads | Safe — read-only |

**Usage:**
```bash
# Search for prospects (safe, read-only)
python webbridge_linkedin_automation.py --workflow search_prospects --query "cheminformatics scientist" --pages 2

# Review connection requests before sending
python webbridge_linkedin_automation.py --workflow send_connections --limit 5 --dry-run

# Actually send (with safety guard enforced)
python webbridge_linkedin_automation.py --workflow send_connections --limit 5

# Extract leads from post comments
python webbridge_linkedin_automation.py --workflow extract_post_leads --post-url "https://linkedin.com/feed/..."
```

---

## 5. Daily Workflows

### Workflow A: Prospecting (Read-Only, Very Safe)

**Goal:** Find 10–15 new prospects per day.

```bash
cd D:\Qmol-3\scripts

# Step 1: Run a search
python webbridge_linkedin_automation.py --workflow search_prospects --query "computational chemist biotech" --pages 3

# Step 2: Review results in generated CSV
# D:\Qmol-3\data\linkedin\search_results_YYYY-MM-DD.csv

# Step 3: Manually vet each profile, copy approved URLs
# Step 4: Add approved prospects to database
python linkedin_outreach.py --action add_prospect --name "..." --title "..." --company "..." --url "..."
```

**Why this is safe:** Zero outbound actions. LinkedIn sees normal browsing.

### Workflow B: Connection Requests (Medium Risk, Human Review Required)

**Goal:** Send 5–12 connection requests per day.

```bash
# Step 1: Generate personalized messages
python linkedin_outreach.py --action generate_messages

# Step 2: Review in dry-run mode (shows exactly what will happen)
python webbridge_linkedin_automation.py --workflow send_connections --limit 5 --dry-run

# Step 3: Manually review each prospect in Chrome
# Open their profile, verify they are a good fit

# Step 4: Send one by one with human delays
python webbridge_linkedin_automation.py --workflow send_connections --limit 5 --interactive
```

**The `--interactive` flag:**
- Shows each prospect
- Pauses and asks: `[Y/n/skip]` for each
- Enforces 60–180 second delay between sends
- Stops if STOP.txt exists
- Stops if daily limit reached

### Workflow C: Messaging 1st-Degree Connections (Medium Risk)

**Goal:** Send 5–10 messages per day to existing connections.

```bash
# Step 1: Export ready messages
python linkedin_outreach.py --action execute_daily --limit 5

# Step 2: Read the exported file
# D:\Qmol-3\data\linkedin\ready_messages.txt

# Step 3: Use WebBridge to send one at a time (semi-automated)
python webbridge_linkedin_automation.py --workflow send_messages --limit 5 --interactive
```

### Workflow D: Post Creation (Safe)

**Goal:** Create a LinkedIn post about Q-Mol.

```bash
# Step 1: Open LinkedIn post composer
python webbridge_linkedin_automation.py --workflow create_post

# Step 2: Script opens the composer, copies the post text to clipboard
# Step 3: You paste and click "Post" manually
```

---

## 6. Troubleshooting

### WebBridge Daemon Not Responding

```powershell
# Check if running
curl.exe -s http://127.0.0.1:10086/command -H "Content-Type: application/json" -d '{"action":"list_tabs","args":{},"session":"test"}'

# Start it
& "$env:USERPROFILE\.kimi-webbridge\bin\kimi-webbridge.exe" start

# If still failing, check the help page:
# https://www.kimi.com/features/webbridge
```

### LinkedIn Shows "Unusual Activity" Warning

**STOP ALL AUTOMATION IMMEDIATELY.**

1. Do not log in from any other device for 24 hours
2. Do not send any connection requests for 48 hours
3. Log in manually, browse normally for 30 minutes
4. Answer the security questions if prompted
5. Resume automation at 50% of normal limits for 1 week

### Element Not Found (`@e` ref missing)

LinkedIn’s DOM changes frequently. Always use `snapshot()` first:

```python
result = snapshot(session="qmol-linkedin")
print(json.dumps(result, indent=2)[:2000])
# Look for the element's @e ref in the output
```

If no `@e` ref exists, use `evaluate()` with a robust selector:

```python
code = """
(() => {
  const btn = Array.from(document.querySelectorAll('button'))
    .find(b => b.textContent.trim().includes('Connect'));
  if (btn) { btn.click(); return 'CLICKED'; }
  return 'NOT_FOUND';
})()
"""
evaluate(code, session="qmol-linkedin")
```

### Screenshot Shows Login Page (Session Expired)

If Dmitriy is logged out:
1. Manually log in via Chrome
2. Do NOT automate the login process — that is a high-risk action
3. Resume automation after confirming the feed loads

---

## 7. Rate Limits & Anti-Ban Rules

### Hard Limits (Never Exceed)

| Action | Daily Max | Min Delay Between |
|--------|-----------|-------------------|
| Connection requests | 15 | 120 seconds |
| Messages sent | 25 | 90 seconds |
| Profile views | 50 | 30 seconds |
| Post engagements (likes/comments) | 20 | 60 seconds |
| Searches | Unlimited (read-only) | 10 seconds |
| Snapshots/screenshots | Unlimited | 3 seconds |

### Soft Limits (Recommended for Long-Term Safety)

| Action | Daily Target | Min Delay Between |
|--------|--------------|-------------------|
| Connection requests | 8–12 | 180 seconds |
| Messages sent | 10–15 | 120 seconds |
| Profile views | 20–30 | 45 seconds |

### Weekly Cadence

| Day | Activity | Count |
|-----|----------|-------|
| Monday | Prospecting search | 15 new prospects |
| Tuesday | Send connection requests | 8–10 |
| Wednesday | Message new connections | 5–8 |
| Thursday | Prospecting search | 15 new prospects |
| Friday | Send connection requests | 8–10 |
| Saturday | Rest or post content | — |
| Sunday | Rest | — |

### Emergency Stop

Create a file at `D:\Qmol-3\scripts\STOP.txt` with any content.
All automation scripts check for this file before every action.

```powershell
# Emergency stop
"STOP" | Out-File -FilePath "D:\Qmol-3\scripts\STOP.txt" -Encoding utf8

# Resume automation
Remove-Item "D:\Qmol-3\scripts\STOP.txt"
```

---

## Appendix A: Project Context

- **Product:** Q-Mol molecular dataset platform
- **Website:** https://photon-bounce.com/qmol/
- **App:** https://photon-bounce.com/qmol/app/
- **Marketplace:** https://photon-bounce.com/qmol/marketplace.html
- **Crypto Wallet:** `0x75B30d0dE751D9628510f3cb273F09f7137f9E3F`
- **Mining Bots:** 10 parallel bots producing 2,800+ molecules
- **Dataset Growth:** ~1 molecule every 5 minutes
- **cPanel API:** `cpanel photonb:OYOQ3JK7HI9C6CNO84T0RH8JUKHHIBZ1`

## Appendix B: File Index

| File | Purpose |
|------|---------|
| `D:\Qmol-3\linkedin\WEBBRIDGE_GUIDE.md` | This document |
| `D:\Qmol-3\scripts\webbridge_driver.py` | Low-level WebBridge client |
| `D:\Qmol-3\scripts\safety_guard.py` | Rate limit enforcer |
| `D:\Qmol-3\scripts\linkedin_outreach.py` | Prospect & message manager |
| `D:\Qmol-3\scripts\webbridge_linkedin_automation.py` | High-level automation workflows |
| `D:\Qmol-3\scripts\runbooks\01_daily_prospecting.md` | Step-by-step prospecting guide |
| `D:\Qmol-3\scripts\runbooks\02_send_connections.md` | Safe connection request workflow |
| `D:\Qmol-3\scripts\runbooks\03_send_messages.md` | Message sending workflow |
| `D:\Qmol-3\scripts\runbooks\04_create_post.md` | LinkedIn post creation guide |
| `D:\Qmol-3\linkedin\outreach-templates.txt` | Message templates |
| `D:\Qmol-3\linkedin\prospect-search-strategy.txt` | Search strategy |
| `D:\Qmol-3\linkedin\post-v1.txt` | Sample LinkedIn post |

---

**Remember: When in doubt, slow down. A restricted LinkedIn account is worth $0 in pipeline.**
