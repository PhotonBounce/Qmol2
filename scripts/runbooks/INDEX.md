# Q-Mol LinkedIn Automation — Runbook Index

**Project:** Q-Mol Molecular Dataset Sales Platform  
**Owner:** Dmitriy Buchman  
**Date:** 2026-07-05  
**Safety Level:** 🟡 MEDIUM — Always use `--interactive` mode for outbound actions

---

## Quick Reference

| I want to... | Run this | Risk | File |
|-------------|----------|------|------|
| Find new prospects | `python webbridge_linkedin_automation.py --workflow search_prospects --query "..."` | 🟢 Low | [01_daily_prospecting.md](01_daily_prospecting.md) |
| Send connection requests | `python webbridge_linkedin_automation.py --workflow send_connections --limit 5 --interactive` | 🟡 Medium | [02_send_connections.md](02_send_connections.md) |
| Send messages | `python webbridge_linkedin_automation.py --workflow send_messages --limit 5 --interactive` | 🟡 Medium | [03_send_messages.md](03_send_messages.md) |
| Create a LinkedIn post | `python webbridge_linkedin_automation.py --workflow create_post` | 🟢 Low | [04_create_post.md](04_create_post.md) |
| Check safety status | `python safety_guard.py --status` | — | — |
| Emergency stop | `python safety_guard.py --stop` | — | — |
| Resume after stop | `python safety_guard.py --resume` | — | — |

---

## Daily Workflow (Recommended)

### Morning (9–10 AM)
1. Check safety status: `python safety_guard.py --status`
2. If Monday/Thursday: Run prospect search ([01](01_daily_prospecting.md))
3. Review and approve new prospects

### Midday (12–2 PM)
4. If Tuesday/Friday: Send connection requests ([02](02_send_connections.md))
5. Use `--interactive` mode

### Afternoon (3–5 PM)
6. If Wednesday: Send messages to existing connections ([03](03_send_messages.md))
7. Or create a post ([04](04_create_post.md))

---

## File Map

```
D:\Qmol-3\
├── linkedin\
│   ├── WEBBRIDGE_GUIDE.md          ← Main guide (start here)
│   ├── outreach-templates.txt      ← Message templates
│   ├── prospect-search-strategy.txt ← Search queries & targets
│   └── post-v1.txt                 ← LinkedIn post template
│
├── scripts\
│   ├── webbridge_driver.py         ← Low-level WebBridge client
│   ├── safety_guard.py             ← Rate limit enforcer
│   ├── linkedin_outreach.py        ← Prospect & message manager
│   ├── webbridge_linkedin_automation.py ← High-level workflows
│   ├── runbooks\
│   │   ├── INDEX.md                ← This file
│   │   ├── 01_daily_prospecting.md ← Find leads
│   │   ├── 02_send_connections.md  ← Connect safely
│   │   ├── 03_send_messages.md     ← Message safely
│   │   └── 04_create_post.md       ← Create posts
│   └── STOP.txt                    ← Emergency stop (create to halt)
│
└── data\linkedin\
    ├── prospects.csv               ← Prospect database
    ├── outreach_log.json           ← Action history
    ├── daily_counts.json           ← Safety guard counts
    ├── search_results_*.csv        ← Search outputs
    ├── ready_messages.txt          ← Messages ready to send
    └── post_leads_*.csv            ← Commenter leads
```

---

## Safety Rules (Memorize These)

1. **Max 15 connections/day** (soft: 12)
2. **Max 25 messages/day** (soft: 20)
3. **Wait 120s between connections, 90s between messages**
4. **Only run during business hours (9 AM–6 PM PDT)**
5. **Always use `--interactive` for outbound actions**
6. **If LinkedIn warns you, STOP for 48 hours**
7. **Create `STOP.txt` to halt all automation instantly**

---

## Emergency Contacts / Actions

| Situation | Action |
|-----------|--------|
| Account restricted | Stop all automation. Log in manually. Wait 48h. |
| CAPTCHA appears | STOP. Do NOT solve it with automation. |
| "Unusual activity" warning | Stop. Browse manually for 30 min. Reduce limits 50%. |
| Want to halt everything | `python safety_guard.py --stop` or create `STOP.txt` |
| WebBridge not responding | `& "$env:USERPROFILE\.kimi-webbridge\bin\kimi-webbridge.exe" start` |

---

*For the full technical guide, see [D:\Qmol-3\linkedin\WEBBRIDGE_GUIDE.md](../linkedin/WEBBRIDGE_GUIDE.md)*
