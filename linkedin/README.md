# Q-Mol LinkedIn Message Automation

**Platform:** Q-Mol Molecular Dataset Marketplace  
**Website:** https://photon-bounce.com/qmol/  
**Owner:** Dmitriy Buchman  
**Crypto Wallet:** `0x75B30d0dE751D9628510f3cb273F09f7137f9E3F`

---

## What This System Does

This automation suite manages LinkedIn outreach for selling Q-Mol molecular datasets. It uses **Kimi WebBridge** to control the user's real Chrome browser (with Dmitriy's actual LinkedIn login session), sending personalized messages to researchers, pharma professionals, and biotech leads.

### Key Features
- **Human-like behavior**: Random delays (45–180s), natural message variations, scroll simulation
- **Strict safety limits**: Max 12 messages + 8 connections per day
- **Deduplication**: 14-day lookback prevents double-contacting
- **Accessibility-tree navigation**: Uses `@e` refs instead of brittle CSS selectors
- **Full audit logging**: Every action recorded in `outreach_log.json`
- **Operating hours guard**: Only runs 9 AM – 6 PM, weekdays
- **Dry-run mode**: Preview all messages before sending

---

## File Structure

```
D:/Qmol-3/
├── linkedin/
│   ├── __init__.py                 # Package marker
│   ├── linkedin_automation.py      # Core WebBridge client (LinkedInBot class)
│   ├── linkedin_messenger.py       # High-level messaging ops
│   ├── message_templates.py        # Q-Mol outreach copy (randomized)
│   ├── safety_config.py            # Rate limits, tracker, operating hours
│   ├── campaign_manager.py         # Campaign orchestration
│   └── targets.py                  # Pre-loaded prospect list
│
├── scripts/
│   ├── run_linkedin_outreach.py    # Main CLI runner
│   ├── check_stats.py              # View outreach statistics
│   ├── validate_setup.py           # Pre-flight checks
│   ├── campaign_scheduler.py       # Cron-compatible daily scheduler
│   ├── cpanel_integration.py       # cPanel API status checks
│   └── crypto_payment_check.py     # ETH wallet monitor
│
└── linkedin/
    └── outreach_log.json           # Auto-generated activity log
```

---

## Usage

### 1. Validate Setup
```bash
cd D:\Qmol-3\scripts
python validate_setup.py
```
Checks WebBridge daemon, Python modules, and directories.

### 2. Dry Run (Preview Messages)
```bash
python run_linkedin_outreach.py --dry-run
```
Generates all messages without sending. Review before live run.

### 3. Run Live Campaign
```bash
python run_linkedin_outreach.py --campaign
```
Sends messages/connections up to daily limits.

### 4. Send Single Message
```bash
python run_linkedin_outreach.py --message "https://linkedin.com/in/..." "Dr. Name" --type researcher --topic "computational chemistry"
```

### 5. Send Single Connection
```bash
python run_linkedin_outreach.py --connect "https://linkedin.com/in/..." "Name" --type pharma --topic "AI drug discovery"
```

### 6. Check Statistics
```bash
python check_stats.py
```

---

## Safety Configuration

| Setting | Value | Rationale |
|---------|-------|-----------|
| Max daily messages | 12 | LinkedIn flags >15–20/day |
| Max daily connections | 8 | Conservative to avoid limits |
| Min delay between actions | 45s | Human-like pacing |
| Max delay between actions | 180s | Randomized jitter |
| Message cooldown | 3–8 min | Prevents burst patterns |
| Operating hours | 9 AM – 6 PM | Only when humans are active |
| Weekend operation | Blocked | Less activity = more suspicious |
| Re-contact window | 14 days | Prevents spam |

---

## WebBridge Requirements

The daemon must be running before any automation:

```powershell
# Windows PowerShell
& "$env:USERPROFILE\.kimi-webbridge\bin\kimi-webbridge.exe" start
```

Endpoint: `http://127.0.0.1:10086`

---

## Target Segments

| Segment | Count | Example Companies |
|---------|-------|-------------------|
| Researchers | 9 | MIT, Stanford, Cambridge, UCSD, ETH |
| Pharma | 5 | Pfizer, Novartis, Roche, AstraZeneca, Merck |
| Biotech | 5 | Recursion, Atomwise, Schrödinger, Exscientia, insitro |
| CRO / Data | 2 | ChemDiv, Enamine |
| AI/ML Chemistry | 3 | DeepChem, Mila, Microsoft Research |

**Total:** 24 pre-loaded high-value prospects.

---

## cPanel Integration

Check website/domain status:
```bash
python cpanel_integration.py
```

Uses token: `cpanel photonb:OYOQ3JK7HI9C6CNO84T0RH8JUKHHIBZ1`

---

## Crypto Payment Monitor

Check ETH wallet for incoming payments:
```bash
python crypto_payment_check.py
```

Monitors: `0x75B30d0dE751D9628510f3cb273F09f7137f9E3F`

---

## Anti-Detection Measures

1. **Message uniqueness**: Every message is randomly assembled from template pools — no two are identical.
2. **Random delays**: Gaussian-like distribution between actions.
3. **Page scrolling**: Simulates human scroll behavior before messaging.
4. **Accessibility tree**: Uses semantic `@e` refs instead of CSS classes that change.
5. **Rate limiting**: Hard caps that cannot be exceeded.
6. **Time gating**: Only operates during business hours.
7. **Connection-first strategy**: If not connected, sends connection request with note instead.

---

## Mining Output

Q-Mol's mining bots currently produce **2,800+ molecules per week**, each with computed physicochemical properties ready for virtual screening.

---

## ⚠️ Disclaimer

LinkedIn actively detects automation. Even with these precautions:
- There is always a risk of account restriction
- Use at your own discretion
- Consider upgrading to LinkedIn Sales Navigator for higher limits
- Never exceed the configured limits

If LinkedIn shows a verification wall or CAPTCHA, the automation **immediately stops** and alerts the user.
