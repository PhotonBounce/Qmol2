# Runbook 03: Send Messages
## Q-Mol LinkedIn Automation — Safe Messaging Workflow

**Risk Level:** 🟡 MEDIUM (Outbound messages detected by LinkedIn)  
**Time Required:** 20–40 minutes  
**Daily Limit:** 20 soft / 25 hard  
**Output:** Updated prospect database, sent messages

---

## ⚠️ CRITICAL WARNINGS

1. **Only message 1st-degree connections.** Messaging 2nd/3rd degree is spam.
2. **Never send identical messages.** Every message must be personalized.
3. **Wait at least 90 seconds between messages.**
4. **Always use `--interactive` mode.** Review each message before sending.
5. **Include value in every message.** No hard sells.

---

## Prerequisites

1. Prospects with `status = connected`
2. Personalized messages generated (`python linkedin_outreach.py --action generate_messages`)
3. Safety guard shows green status
4. Business hours (9 AM–6 PM PDT, weekday)

---

## Step-by-Step

### Step 1: Check Safety Status

```powershell
cd D:\Qmol-3\scripts
python safety_guard.py --status
```

**Look for:**
- Messages today: 0/20 (soft) or less
- No STOP file active
- Within business hours

### Step 2: Export Ready Messages

```powershell
python linkedin_outreach.py --action execute_daily --limit 5
```

**Review the exported file:**
```powershell
notepad D:\Qmol-3\data\linkedin\ready_messages.txt
```

Check each message:
- Is it personalized with the prospect's name?
- Does it reference their work/title?
- Is the tone helpful, not salesy?
- Is the molecule count current?

### Step 3: Dry-Run Send

```powershell
python webbridge_linkedin_automation.py `
  --workflow send_messages `
  --limit 5 `
  --dry-run
```

### Step 4: Interactive Send (RECOMMENDED)

```powershell
python webbridge_linkedin_automation.py `
  --workflow send_messages `
  --limit 5 `
  --interactive
```

**What happens:**
1. Script loads the first connected prospect with a ready message
2. Displays:
   - Prospect name
   - Message preview (first 80 chars)
3. Prompts: `Send this message? [Y/n/skip/quit]`
4. If you type `Y`:
   - Navigates to LinkedIn messaging
   - Searches for the person
   - Opens conversation
   - Types the full message
   - Clicks Send
   - Records action in log
   - Waits 90–180 seconds before next
5. If you type `n` or `skip` → moves to next
6. If you type `quit` → stops immediately

### Step 5: Verify Sends

After completion:
```powershell
python linkedin_outreach.py --action status
```

Check:
- `messaged` count increased
- `connected` count decreased
- Daily log shows message actions

---

## Message Templates (from outreach-templates.txt)

### Value-First (Recommended for first message)

```
Hi {Name},

Saw your work on {topic}. I put together a free dataset of 50 drug-like 
molecules with ADMET descriptors — no PAINS, Lipinski-pass, QED > 0.6.

Grab it here: https://photon-bounce.com/qmol/app/ (free preview)

Also have a {molecule_count}+ molecule full dataset if you need more. 
Happy to chat.

Dmitriy
```

### Short & Direct (For busy prospects)

```
Hi {Name},

Built a tool that auto-curates compound libraries from PubChem — 
{molecule_count}+ molecules with RDKit descriptors, free trial.

https://photon-bounce.com/qmol/app/

If this saves you even an hour a week, it's worth it.

Dmitriy
```

### Follow-Up (After no response in 7 days)

```
Hi {Name},

Wanted to follow up on my last message about Q-Mol. No pressure at all — 
I know inboxes get full.

If compound library curation is something your team struggles with, 
happy to send over a sample dataset. Just reply and I'll get it over.

Best,
Dmitriy
```

---

## Crypto Payment Message (When Prospect Shows Interest)

**Only send AFTER they express interest.**

```
Great! You can pay securely with crypto. We accept ETH, BTC, SOL, TRON, 
BNB, Polygon, Linea, Base, Arbitrum, and Optimism.

Just go here: https://photon-bounce.com/qmol/pay-crypto.html

Select your network, send the $299 equivalent, and paste your transaction 
hash. The CSV dataset is emailed automatically within 5 minutes.

Wallet for direct payment: 0x75B30d0dE751D9628510f3cb273F09f7137f9E3F
```

---

## Safety Checklist Before Each Message

- [ ] Prospect is a 1st-degree connection
- [ ] Message is personalized (not copy-paste)
- [ ] Message provides value first (not a hard sell)
- [ ] No more than 20 messages sent today
- [ ] At least 90 seconds since last message
- [ ] LinkedIn has not shown any warnings

---

## File Outputs

| File | Description |
|------|-------------|
| `D:\Qmol-3\data\linkedin\ready_messages.txt` | Copy-paste friendly message list |
| `D:\Qmol-3\data\linkedin\prospects.csv` | Updated with `status = messaged` |
| `D:\Qmol-3\data\linkedin\outreach_log.json` | Message actions logged |

---

*Last updated: 2026-07-05*
