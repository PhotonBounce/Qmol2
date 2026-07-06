# Runbook 02: Send Connection Requests
## Q-Mol LinkedIn Automation — Safe Connection Workflow

**Risk Level:** 🟡 MEDIUM (Outbound actions detected by LinkedIn)  
**Time Required:** 15–30 minutes  
**Daily Limit:** 12 soft / 15 hard  
**Output:** Updated prospect database with status changes

---

## ⚠️ CRITICAL WARNINGS

1. **Never exceed 15 connection requests per day.** One over = potential restriction.
2. **Always use `--interactive` mode.** Let a human approve each request.
3. **Never add a note to the connection request.** LinkedIn flags templated notes.
4. **Wait at least 120 seconds between requests.**
5. **Only connect with people who match your target persona.**

---

## Prerequisites

1. Prospects already added to database (`status = new`)
2. Messages already generated (`python linkedin_outreach.py --action generate_messages`)
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
- Connections today: 0/12 (soft) or less
- No STOP file active
- Within business hours

### Step 2: Generate Messages (if not done)

```powershell
python linkedin_outreach.py --action generate_messages
```

This creates personalized messages for all `new` prospects.

### Step 3: Dry-Run Review

```powershell
python webbridge_linkedin_automation.py `
  --workflow send_connections `
  --limit 5 `
  --dry-run
```

**Review the output:**
- Does it show the right prospects?
- Are the names and URLs correct?
- Is the limit reasonable?

### Step 4: Interactive Send (RECOMMENDED)

```powershell
python webbridge_linkedin_automation.py `
  --workflow send_connections `
  --limit 5 `
  --interactive
```

**What happens:**
1. Script loads the first `new` prospect
2. Displays their name and URL
3. Prompts: `Send connection to [Name]? [Y/n/skip/quit]`
4. If you type `Y`:
   - Navigates to their profile
   - Waits 4–7 seconds
   - Finds and clicks "Connect"
   - Waits 3–5 seconds
   - Clicks "Send without a note"
   - Records action in log
   - Waits 60–180 seconds before next
5. If you type `n` or `skip` → moves to next
6. If you type `quit` → stops immediately

### Step 5: Verify Sends

After completion:
```powershell
python linkedin_outreach.py --action status
```

Check:
- `pending` count increased by number sent
- `new` count decreased
- Daily log shows connection actions

### Step 6: Manual Verification (Important!)

Open Chrome and check:
1. Go to `https://www.linkedin.com/mynetwork/invitation-manager/sent/`
2. Verify the requests appear
3. Verify NO notes were attached
4. If anything looks wrong, stop all automation for 48 hours

---

## Alternative: Fully Manual (Safest)

If you prefer zero automation risk:

```powershell
python linkedin_outreach.py --action execute_daily --limit 5
```

This exports ready-to-send data to:
`D:\Qmol-3\data\linkedin\ready_messages.txt`

Then manually:
1. Open each profile in Chrome
2. Click Connect
3. Click Send without a note
4. Wait 2–3 minutes
5. Repeat

---

## What To Do If LinkedIn Shows "Unusual Activity"

**STOP IMMEDIATELY.**

1. Do not send any more connections for 48 hours
2. Log in manually and browse normally for 30 minutes
3. Answer any security prompts
4. Reduce daily limit to 5 for the next week
5. If account is restricted, follow LinkedIn's recovery flow

---

## File Outputs

| File | Description |
|------|-------------|
| `D:\Qmol-3\data\linkedin\prospects.csv` | Updated with `status = pending` |
| `D:\Qmol-3\data\linkedin\outreach_log.json` | Connection actions logged |
| `D:\Qmol-3\data\linkedin\daily_counts.json` | Safety guard daily counts |

---

*Last updated: 2026-07-05*
