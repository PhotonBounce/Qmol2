# Q-Mol LinkedIn Automation Suite
## Safety-First Outreach System for Molecular Dataset Sales

**Created:** July 5, 2026  
**Platform:** https://photon-bounce.com/qmol/  
**Owner:** Dmitriy Buchman  
**Wallet:** 0x75B30d0dE751D9628510f3cb273F09f7137f9E3F

---

## 🎯 What This System Does

Automates LinkedIn outreach for Q-Mol (molecular dataset sales platform) while prioritizing **account safety above all else**. The system:

- Manages prospect database (cheminformatics, pharma, CROs)
- Sends connection requests with human-like delays
- Delivers personalized messages to 1st-degree connections
- Tracks pipeline from "new" → "purchased"
- Monitors daily/weekly limits with circuit breaker
- Provides fallback manual copy-paste mode

---

## 📁 File Structure

```
D:\Qmol-3\
├── linkedin\
│   ├── LINKEDIN_SAFETY_GUIDE.md      ← Comprehensive safety research
│   ├── outreach-templates.txt         ← Message templates (existing)
│   ├── post-v1.txt                    ← LinkedIn post template (existing)
│   ├── prospect-search-strategy.txt   ← Search strategy (existing)
│   └── sample_prospects.csv           ← Import template
│
├── scripts\
│   ├── linkedin_safe_automation.py    ← MAIN automation controller
│   ├── linkedin_daily_runner.py       ← Daily batch scheduler
│   ├── linkedin_prospect_manager.py   ← Prospect database manager
│   ├── linkedin_daily.bat             ← Windows one-click runner
│   └── webbridge_driver.py            ← Low-level WebBridge driver (existing)
│
└── data\linkedin\                      ← Created on first run
    ├── prospects.csv                  ← Your prospect database
    ├── safety_audit.json              ← Action log & health metrics
    ├── action_log.json                ← Detailed action history
    ├── ready_messages.txt             ← Manual copy-paste fallback
    ├── generated_messages.json        ← Auto-generated messages
    └── daily_run_report.json          ← Run history
```

---

## 🚀 Quick Start

### 1. Ensure WebBridge is Running

WebBridge controls your real Chrome browser (Dmitriy is already logged into LinkedIn).

```powershell
# Check if running
$resp = Invoke-WebRequest -Uri "http://127.0.0.1:10086/" -Method GET

# If not running, start it:
& "$env:USERPROFILE\.kimi-webbridge\bin\kimi-webbridge.exe" start
```

### 2. Add Prospects

```bash
# Add one prospect
python scripts/linkedin_prospect_manager.py add "Jane Smith" "Scientist" "BioTech Inc" "linkedin.com/in/janesmith" --location "Boston"

# Or import from CSV
python scripts/linkedin_prospect_manager.py import my_leads.csv
```

**CSV format for import:**
```csv
name,title,company,url,location,notes
Jane Smith,Scientist,BioTech Inc,linkedin.com/in/janesmith,Boston,Met at conference
John Doe,Director CADD,PharmaCorp,linkedin.com/in/johndoe,San Diego,High priority
```

### 3. Check Status

```bash
python scripts/linkedin_safe_automation.py --mode status
```

### 4. Run Daily Routine (DRY RUN FIRST!)

```bash
# Simulate without sending anything
python scripts/linkedin_safe_automation.py --mode daily --dry-run

# Live run (when you're ready)
python scripts/linkedin_safe_automation.py --mode daily
```

Or double-click `scripts/linkedin_daily.bat` on Windows.

### 5. View Reports

```bash
python scripts/linkedin_daily_runner.py --report
```

---

## ⚠️ Safety Limits (Hard-Coded)

| Action | Daily Max | Weekly Max | Min Delay |
|--------|-----------|------------|-----------|
| Connection Requests | 15 | 75 | 45-180s |
| Messages | 20 | - | 45-180s |
| Profile Views | 30 | - | 30-90s |
| **Total Actions** | **50** | - | - |

- Active hours only: 09:00 - 18:00 local time
- Random delays between actions (never fixed intervals)
- 10% chance of extra 60-120s pause
- Automatic 14-day cooldown if any warning detected

**These limits are CONSERVATIVE** — well below LinkedIn's detection thresholds.

---

## 📋 Available Commands

### Main Automation (`linkedin_safe_automation.py`)

```bash
--mode status           # Show dashboard
--mode health_check     # Check if safe to run
--mode daily            # Run full daily routine
--mode connect          # Send connection requests
--mode message          # Send messages
--mode profile_views    # View profiles (warm-up)
--mode export           # Export ready messages for manual sending
--dry-run               # Simulate without sending
--batch-size N          # Override batch size (still capped by safety limits)
```

### Prospect Manager (`linkedin_prospect_manager.py`)

```bash
add NAME TITLE COMPANY URL [--location LOC] [--notes NOTES]
import FILEPATH
list [--status STATUS] [--limit N]
update URL_OR_NAME --status STATUS [--notes NOTES]
generate-messages
stats
export-hot [--output FILE]
delete URL_OR_NAME
```

### Daily Runner (`linkedin_daily_runner.py`)

```bash
--run-now               # Execute immediately
--dry-run               # Simulate
--report                # Show run history
--schedule HH:MM        # Setup scheduled time
```

---

## 🔒 Safety Features

1. **Circuit Breaker** — Stops all automation if:
   - Daily limits reached
   - Outside active hours
   - Recent warning detected (14-day cooldown)
   - Weekly connection cap reached

2. **Human-Like Behavior** — Randomized timing, scrolling, pauses

3. **Real Browser** — Uses Chrome via WebBridge (not headless/detection-prone)

4. **No URLs in Connection Requests** — Connection requests sent WITHOUT notes (safest)

5. **Audit Trail** — Every action logged with timestamp, target, and details

6. **Automatic Health Monitoring** — Tracks acceptance rates and warns if < 30%

---

## 🛑 Emergency Procedures

### If LinkedIn Shows a Warning

1. **STOP IMMEDIATELY** — All automation halts automatically
2. Switch to 100% manual for 2 weeks
3. Post organic content, comment, like posts
4. After 2 weeks, resume at 50% volume

### If Account Restricted

1. Do NOT create new account
2. Submit appeal: https://www.linkedin.com/help/linkedin/ask
3. Wait 1-2 weeks for response
4. If restored, stay at 5 actions/day for 1 month

### Manual Fallback

If automation is paused, use exported messages:

```bash
python scripts/linkedin_safe_automation.py --mode export
# Then copy-paste from data/linkedin/ready_messages.txt
```

---

## 📊 Tracking Conversions

Pipeline stages: `new` → `viewed` → `pending` → `connected` → `messaged` → `followed_up` → `responded` → `interested` → `purchased`

```bash
# View pipeline stats
python scripts/linkedin_prospect_manager.py stats
```

---

## 🔄 Scheduling (Windows)

### Option 1: Task Scheduler
1. Open Task Scheduler (`taskschd.msc`)
2. Create Basic Task → "Q-Mol LinkedIn Daily"
3. Trigger: Daily at 10:00 AM
4. Action: Start `D:\Qmol-3\scripts\linkedin_daily.bat`
5. **Important:** Set "Run only when user is logged on" (Chrome needs GUI)

### Option 2: Cron (WSL/Git Bash)
```bash
# Edit crontab
crontab -e

# Add line:
0 10 * * * cd /d/Qmol-3 && python scripts/linkedin_safe_automation.py --mode daily
```

---

## 🧪 Testing

Always test with `--dry-run` first:

```bash
# Full simulation
python scripts/linkedin_safe_automation.py --mode daily --dry-run

# Test just connections
python scripts/linkedin_safe_automation.py --mode connect --batch-size 3 --dry-run

# Test just messages
python scripts/linkedin_safe_automation.py --mode message --batch-size 2 --dry-run
```

---

## 📞 Support

- **WebBridge issues:** https://www.kimi.com/features/webbridge
- **LinkedIn restrictions:** https://www.linkedin.com/help/linkedin/ask
- **Q-Mol platform:** https://photon-bounce.com/qmol/

---

*Last updated: 2026-07-05*  
*Safety limits verified against: ConnectSafely 2026, SalesTarget.ai, Dux-Soup, FirstTouch*
