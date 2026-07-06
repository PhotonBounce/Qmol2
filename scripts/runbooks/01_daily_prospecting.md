# Runbook 01: Daily Prospecting Workflow
## Q-Mol LinkedIn Automation — Safe Lead Discovery

**Risk Level:** 🟢 LOW (Read-only browsing)  
**Time Required:** 20–30 minutes  
**Output:** CSV file of prospect URLs for manual review

---

## Prerequisites

1. WebBridge daemon running at `http://127.0.0.1:10086`
2. Dmitriy logged into LinkedIn in Chrome
3. `D:\Qmol-3\scripts\webbridge_linkedin_automation.py` exists

---

## Step-by-Step

### Step 1: Verify Safety Guard Status

```powershell
cd D:\Qmol-3\scripts
python safety_guard.py --status
```

**Expected:** All counts at 0, business hours OK, no STOP file.

### Step 2: Run Prospect Search (Dry-Run First)

```powershell
python webbridge_linkedin_automation.py `
  --workflow search_prospects `
  --query "computational chemist biotech" `
  --pages 2 `
  --dry-run
```

**What this does:** Simulates the search without opening Chrome.

### Step 3: Run Live Search

```powershell
python webbridge_linkedin_automation.py `
  --workflow search_prospects `
  --query "computational chemist biotech" `
  --pages 2
```

**What this does:**
1. Opens LinkedIn search in Chrome
2. Scans 2 pages of people results
3. Extracts unique profile URLs (`linkedin.com/in/username`)
4. Saves to `D:\Qmol-3\data\linkedin\search_results_YYYY-MM-DD_HHMM.csv`
5. Enforces 10–15 second delays between pages

### Step 4: Review Results

Open the CSV in Excel or VS Code:
```powershell
notepad D:\Qmol-3\data\linkedin\search_results_*.csv
```

For each profile URL:
- Open in Chrome and review the profile
- Check if they match the target persona:
  - Title: Scientist, Principal Scientist, Director, Founder, CTO
  - Company: Biotech, pharma, CRO, academic lab
  - Location: US, UK, Germany, Switzerland
- **Vet manually. Do not add everyone.**

### Step 5: Add Approved Prospects

For each approved prospect:
```powershell
python linkedin_outreach.py `
  --action add_prospect `
  --name "Jane Smith" `
  --title "Principal Scientist, Computational Chemistry" `
  --company "BioTech Inc" `
  --url "https://www.linkedin.com/in/janesmith/" `
  --location "Boston, MA"
```

### Step 6: Verify Database

```powershell
python linkedin_outreach.py --action status
```

**Expected:** New prospects show in status output.

---

## Recommended Search Queries (Rotate Daily)

| Day | Query | Rationale |
|-----|-------|-----------|
| Mon | `cheminformatics scientist` | Core audience |
| Tue | `computational chemistry virtual screening` | CADD focus |
| Wed | `medicinal chemistry CRO` | CRO buyers |
| Thu | `AI drug discovery machine learning` | ML startups |
| Fri | `RDKit Python drug design` | Technical users |

**Never run the same query twice in one week.** LinkedIn tracks repeated searches.

---

## Safety Notes

- ✅ **Safe:** Reading search results, extracting URLs
- ✅ **Safe:** Opening profiles one at a time to review
- ⚠️ **Risky:** Viewing 50+ profiles in a row without breaks
- 🚫 **Banned:** Using scripts to mass-view profiles

---

## Troubleshooting

**Search returns 0 results**
- LinkedIn may have changed the DOM. Update `extract_people_from_search()` in `webbridge_linkedin_automation.py`.
- Try a different query.

**WebBridge snapshot is empty**
- Page may still be loading. Increase initial delay from 5s to 10s.
- Check if LinkedIn shows a login page (session expired).

**CSV is empty**
- LinkedIn may be showing "People you may know" instead of search results.
- Ensure the search URL is correct and the query is not too narrow.

---

## File Outputs

| File | Description |
|------|-------------|
| `D:\Qmol-3\data\linkedin\search_results_*.csv` | Raw search results |
| `D:\Qmol-3\data\linkedin\prospects.csv` | Approved prospects database |
| `D:\Qmol-3\data\linkedin\outreach_log.json` | Action log |

---

*Last updated: 2026-07-05*
