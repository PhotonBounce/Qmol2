# Runbook 04: Create LinkedIn Post
## Q-Mol LinkedIn Automation — Post Creation Workflow

**Risk Level:** 🟢 LOW (Opens composer, human publishes)  
**Time Required:** 10–15 minutes  
**Output:** LinkedIn post about Q-Mol published

---

## Why This Is Safe

This workflow **does NOT auto-publish**. It:
1. Opens the LinkedIn post composer
2. Enters the post text
3. Stops — you manually click "Post"

LinkedIn cannot detect automation if the final publish action is human.

---

## Prerequisites

1. WebBridge running
2. Dmitriy logged into LinkedIn
3. `D:\Qmol-3\linkedin\post-v1.txt` exists (template)

---

## Step-by-Step

### Step 1: Create or Update Post Content

Edit the template:
```powershell
notepad D:\Qmol-3\linkedin\post-v1.txt
```

**Current post template:**
```
🧬 Just launched Q-Mol — a molecular informatics platform for drug discovery teams.

After watching researchers spend hours manually curating compound libraries, 
I built something that automates the hard part.

Here's what Q-Mol does in 30 seconds:

→ Mines {molecule_count}+ drug-like molecules from PubChem with RDKit-validated descriptors
→ Filters by Lipinski, Veber, PAINS, QED score — all client-side
→ Exports datasets as CSV for docking, ML, or assay prep
→ Marketplace for buying curated datasets (instant download)

The dataset auto-grows every 5 minutes via 10 parallel mining bots.

Free 7-day trial. No credit card.

Built with: SQLite, vanilla JS, PHP, Python, RDKit

If you're in cheminformatics, CRO, or early-stage pharma — this might save you a day a week.

🔗 Web App: https://photon-bounce.com/qmol/app/
🔗 Marketplace: https://photon-bounce.com/qmol/marketplace.html

#cheminformatics #drugdiscovery #molecules #saas #biotech #pharma #rdkit #machinelearning #compchem
```

**Update the molecule count** before posting:
```powershell
cd D:\Qmol-3\scripts
python -c "from linkedin_outreach import get_molecule_count; print(get_molecule_count())"
```

Replace `{molecule_count}` with the actual number.

### Step 2: Run the Post Creation Workflow

```powershell
cd D:\Qmol-3\scripts
python webbridge_linkedin_automation.py --workflow create_post
```

**What happens:**
1. Navigates to LinkedIn feed
2. Waits 5–8 seconds
3. Clicks "Start a post" button
4. Waits 3–5 seconds
5. Enters the post text into the editor
6. Prints: "MANUAL STEP REQUIRED: Review the post in Chrome. Click the 'Post' button to publish."

### Step 3: Manually Publish

1. Look at Chrome — the post composer should be open with text filled in
2. **Review the post carefully**
3. Add any images if desired (drag and drop)
4. Click the **Post** button

**Do NOT let automation click Post.**

---

## Posting Schedule (Recommended)

| Day | Content Type | Goal |
|-----|-------------|------|
| Monday | Product update / feature launch | Awareness |
| Wednesday | Industry insight / thought leadership | Authority |
| Friday | Customer story / use case | Social proof |

**Frequency:** 2–3 posts per week maximum.

**Best times:** Tuesday–Thursday, 8–10 AM PDT.

---

## Post Ideas for Q-Mol

### 1. Data Drop Post
```
📊 Dataset drop: 100 drug-like molecules, Lipinski-pass, QED > 0.7, no PAINS.

CSV ready for docking or ML training. Free download — no signup.

[Link to marketplace]
```

### 2. Behind the Scenes
```
⚙️ How Q-Mol mines molecules: 10 parallel bots → PubChem API → RDKit descriptors → SQLite.

Every 5 minutes, another molecule joins the dataset.

Currently at {molecule_count} and counting.
```

### 3. Pain Point + Solution
```
❌ Manual compound library curation: 4 hours
✅ Q-Mol auto-harvest: 30 seconds

Same filters (Lipinski, Veber, PAINS, QED). Same CSV export. Zero manual work.

Free trial → [link]
```

### 4. Crypto Payment Announcement
```
🪙 Q-Mol now accepts crypto payments.

ETH, BTC, SOL, TRON, BNB, Polygon, Linea, Base, Arbitrum, Optimism.

Buy curated molecular datasets with your preferred chain.

Wallet: 0x75B30d0dE751D9628510f3cb273F09f7137f9E3F

Marketplace → [link]
```

---

## Hashtag Strategy

**Always include (rotate):**
- `#cheminformatics` (core)
- `#drugdiscovery` (broad)
- `#molecules` (visual)
- `#biotech` (industry)
- `#pharma` (industry)

**Sometimes include:**
- `#rdkit` (technical)
- `#machinelearning` (ML audience)
- `#compchem` (computational chemistry)
- `#saas` (startup community)
- `#virtualscreening` (use case)

**Never use more than 5 hashtags.** LinkedIn's algorithm deprioritizes hashtag spam.

---

## After Publishing

### Track Engagement

1. Wait 24–48 hours
2. Note who liked, commented, or shared
3. Add commenters to prospect database as WARM leads:
   ```powershell
   python linkedin_outreach.py --action add_prospect --name "..." --url "..." --notes "Commented on post 2026-07-05"
   ```

### Extract Leads from Comments

```powershell
python webbridge_linkedin_automation.py `
  --workflow extract_post_leads `
  --post-url "https://www.linkedin.com/feed/update/..."
```

This exports commenters to a CSV for easy import.

---

## File Outputs

| File | Description |
|------|-------------|
| `D:\Qmol-3\linkedin\post-v1.txt` | Current post template |
| `D:\Qmol-3\data\linkedin\post_leads_*.csv` | Commenter leads from posts |

---

*Last updated: 2026-07-05*
